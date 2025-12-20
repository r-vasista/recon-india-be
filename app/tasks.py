from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from app.models import (
    MasterNewsPost, NewsDistribution, PortalPrompt, Portal, PortalCategory, NewsPublishTask
)
from user.models import (
    PortalUserMapping
)
from .utils import generate_variation_with_gpt
from django.utils.text import slugify
import requests, time
import logging
logger = logging.getLogger("news_publish")

User = get_user_model()


@shared_task(bind=True)
def publish_master_news(self, news_post_id, user_id, mappings_data):
    """
    Celery task to publish one MasterNewsPost to many portals.
    mappings_data example:
        {
            "portal_id": 1,
            "portal_category_id": 5,
            "use_default": False
        }
    """
    logger = logging.getLogger("news_publish")
    task_id = self.request.id

    logger.info(f"[{task_id}] Task started for news_post={news_post_id}")

    # --- Fetch task record ---
    task_record = NewsPublishTask.objects.filter(task_id=task_id).first()
    if task_record:
        task_record.status = "STARTED"
        task_record.save()

    try:
        # -------- Load Post & User --------
        news_post = MasterNewsPost.objects.get(id=news_post_id)
        user = User.objects.get(id=user_id)
    except Exception as e:
        logger.error(f"[{task_id}] Error loading user/news_post: {e}")

        if task_record:
            task_record.status = "FAILURE"
            task_record.save()

        return {"success": False, "error": str(e)}

    results = []

    # ======================================================
    # ============  LOOP OVER ALL PORTAL MAPPINGS ===========
    # ======================================================
    for mapping in mappings_data:
        portal_id = mapping["portal_id"]
        portal_category_id = mapping["portal_category_id"]
        use_default = mapping["use_default"]

        try:
            portal = Portal.objects.get(id=portal_id)
            portal_category = PortalCategory.objects.get(id=portal_category_id)
        except Exception as e:
            logger.error(f"[{task_id}] Invalid portal/category mapping: {e}")
            results.append({
                "portal_id": portal_id,
                "success": False,
                "response": f"Invalid mapping: {e}"
            })
            continue

        logger.info(f"[{task_id}] Publishing to {portal.name} ({portal_category.name})")

        # -------- Create / Fetch Distribution --------
        dist, _ = NewsDistribution.objects.get_or_create(
            news_post=news_post,
            portal=portal,
            defaults={
                "portal_category": portal_category,
                "master_category": news_post.master_category,
                "status": "PENDING",
                "started_at": timezone.now(),
            }
        )

        # Skip previously successful
        if dist.status == "SUCCESS":
            results.append({
                "portal": portal.name,
                "category": portal_category.name,
                "success": True,
                "response": "Already published"
            })
            continue

        start_time = time.perf_counter()

        # =======================================================
        # ===================== AI GENERATION ====================
        # =======================================================
        try:
            if use_default:
                ai_title = news_post.title
                ai_short = news_post.short_description
                ai_content = news_post.content
                ai_meta = news_post.meta_title or news_post.title
                ai_slug = news_post.slug
            else:
                portal_prompt = (
                    PortalPrompt.objects.filter(portal=portal, is_active=True).first()
                    or PortalPrompt.objects.filter(portal__isnull=True, is_active=True).first()
                )
                prompt_text = portal_prompt.prompt_text if portal_prompt else ""

                ai_title, ai_short, ai_content, ai_meta, ai_slug = generate_variation_with_gpt(
                    news_post.title,
                    news_post.short_description,
                    news_post.content,
                    prompt_text,
                    news_post.meta_title,
                    news_post.slug,
                    portal_name=portal.name,
                )
        except Exception as e:
            error_msg = f"AI failed: {str(e)}"
            logger.error(f"[{task_id}] {error_msg}")

            dist.status = "FAILED"
            dist.response_message = error_msg
            dist.completed_at = timezone.now()
            dist.save()

            results.append({
                "portal": portal.name,
                "category": portal_category.name,
                "success": False,
                "response": error_msg
            })
            continue

        # =======================================================
        # ================= PORTAL USER MAPPING ==================
        # =======================================================
        portal_user = PortalUserMapping.objects.filter(
            user=user,
            portal=portal,
            status="MATCHED"
        ).first()

        if not portal_user:
            msg = "Portal user not mapped"
            logger.error(f"[{task_id}] {msg}")

            dist.status = "FAILED"
            dist.response_message = msg
            dist.completed_at = timezone.now()
            dist.save()

            results.append({
                "portal": portal.name,
                "success": False,
                "response": msg,
            })
            continue

        # =======================================================
        # ===================== PAYLOAD ==========================
        # =======================================================
        payload = {
            "post_cat": portal_category.external_id,
            "post_title": ai_title,
            "post_short_des": ai_short,
            "post_des": ai_content,
            "meta_title": ai_meta,
            "slug": ai_slug,
            "post_tag": news_post.post_tag or "",
            "author": portal_user.portal_user_id,
            "Event_date": (news_post.Event_date or timezone.now().date()).isoformat(),
            "Eventend_date": (news_post.Event_end_date or timezone.now().date()).isoformat(),
            "schedule_date": (news_post.schedule_date or timezone.now()).isoformat(),
            "is_active": int(bool(news_post.is_active)),
            "Event": int(bool(news_post.Event)),
            "Head_Lines": int(bool(news_post.Head_Lines)),
            "articles": int(bool(news_post.articles)),
            "trending": int(bool(news_post.trending)),
            "BreakingNews": int(bool(news_post.BreakingNews)),
            "post_status": news_post.counter or 0,
        }

        files = {"post_image": open(news_post.post_image.path, "rb")} if news_post.post_image else None

        # =======================================================
        # =================== SEND TO PORTAL =====================
        # =======================================================
        portal_news_id = None

        try:
            api_url = f"{portal.base_url}/api/create-news/"
            response = requests.post(api_url, data=payload, files=files, timeout=90)
            success = response.status_code in [200, 201]
            msg = response.text

            if success:
                try:
                    resp_json = response.json()
                    portal_news_id = resp_json.get("data", {}).get("id")
                except:
                    pass

        except Exception as e:
            success = False
            msg = str(e)

        # =======================================================
        # ====================== UPDATE DB ========================
        # =======================================================
        dist.status = "SUCCESS" if success else "FAILED"
        dist.response_message = msg
        dist.ai_title = ai_title
        dist.ai_short_description = ai_short
        dist.ai_content = ai_content
        dist.ai_meta_title = ai_meta
        dist.ai_slug = ai_slug
        dist.portal_news_id = portal_news_id
        dist.time_taken = round(time.perf_counter() - start_time, 2)
        dist.completed_at = timezone.now()
        dist.save()

        results.append({
            "portal": portal.name,
            "category": portal_category.name,
            "success": success,
            "response": msg
        })

    # =======================================================
    # ================ FINAL TASK STATE UPDATE ==============
    # =======================================================
    if task_record:
        # any failed = FAILURE
        # if any(r["success"] is False for r in results):
        #     task_record.status = "FAILURE"
        # else:
        task_record.status = "SUCCESS"
        task_record.save()

    logger.info(f"[{task_id}] Completed publishing")

    return {"success": True, "results": results}
