import json
import re
import logging

from app.models import MasterCategoryMapping
from openai import OpenAI

from django.conf import settings
from django.utils.text import slugify

logger = logging.getLogger("ai_variation") 

client = OpenAI(api_key=settings.OPEN_AI_KEY)

def success_response(data, message = None):
    return {"status": True, "data":data, "message":message}

def error_response(message):
    return {"status": False, "message":message}

def generate_variation_with_gpt(title, short_desc, desc, prompt_text, meta_title=None, slug=None, portal_name=None):
    """
    Generate rephrased version of news fields using GPT.
    Always tries to parse JSON safely.
    Handles:
      - dict responses
      - list responses
      - nested dicts (e.g. {'dxbnewsnetwork.com': {...}})
    Returns (title, short_desc, desc, meta_title, slug) or None if failed.
    """
    logger.info("Started AI generation for portal: %s", portal_name)


    user_content = f"""
    Rewrite the following news content for the portal
    Each portal must have a unique variation of the rewritten content.

    Rules:
    - Preserve all HTML tags, attributes, styles, images, links, lists, and formatting inside the description.
    - Rewrite the textual content for: title, short_description, description, and meta_title.
    - The short_description must be a concise 1–2 sentence less than 160 characters summary of the rewritten description.
    - Generate a new slug as a clean, URL-safe version of the rewritten meta_title (lowercase, hyphen separated).
    - Ensure wording differs slightly for each portal, but keep meaning intact.
    - Do not remove, add, or modify any HTML structure.

    Return ONLY valid JSON with keys: title, short_description, description, meta_title, slug.

    {{
        "title": "{title}",
        "short_description": "{short_desc}",
        "description": "{desc}",
        "meta_title": "{meta_title or title}",
        "slug": "{slug or slugify(meta_title or title)}",
        "portal_name": "{portal_name or ''}"
    }}
    """


    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "developer", "content": prompt_text},
                {"role": "user", "content": user_content}
            ],
        )

        content = response.output_text.strip()
        logger.info("Raw GPT response (first 500 chars): %s", content[:500])

        # ---- Safe JSON Parsing ----
        try:
            data = json.loads(content)
        except json.JSONDecodeError:

            import re
            match = re.search(r"\{.*\}|\[.*\]", content, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
            else:
                raise ValueError("No valid JSON structure in GPT response")

        # ---- Handle Lists ----
        if isinstance(data, list):
            logger.warning("GPT returned list for %s — using first item", portal_name)
            data = data[0] if data else {}

        # ---- Handle Nested Dicts (e.g., {"dxbnewsnetwork.com": {...}}) ----
        elif isinstance(data, dict) and len(data.keys()) >= 1:
            # If the only key is not a known field, treat it as nested
            first_key = list(data.keys())[0]
            if first_key not in ["title", "short_description", "description", "meta_title", "slug"]:
                logger.warning("GPT returned nested dict for %s — using inner value under key %s", portal_name, first_key)
                data = data[first_key]

        # ---- Final Validation ----
        required_keys = ["title", "short_description", "description", "meta_title", "slug"]

        if not all(k in data and data[k] for k in required_keys):
            raise ValueError(f"Missing or empty keys in GPT response: {data}")

        logger.info("Successfully generated AI variation for %s", portal_name)

        return (
            data.get("title", title),
            data.get("short_description", short_desc),
            data.get("description", desc),
            data.get("meta_title", meta_title or title),
            data.get("slug", slug or slugify(meta_title or title)),
        )


    except Exception as e:
        logger.exception("AI generation failed for %s: %s", portal_name, str(e))
        return None
    
def get_portals_from_assignment(assignment):
    """
    Given a UserCategoryGroupAssignment, return all (portal, portal_category) pairs.
    """
    portals = []

    # Case 1: Assignment is for a single master_category
    if assignment.master_category:
        mappings = MasterCategoryMapping.objects.filter(
            master_category=assignment.master_category
        ).select_related("portal_category__portal")
        for mapping in mappings:
            portals.append((mapping.portal_category.portal, mapping.portal_category))

    # Case 2: Assignment is for a group (iterate over its master categories)
    if assignment.group:
        for mc in assignment.group.master_categories.all():
            mappings = MasterCategoryMapping.objects.filter(
                master_category=mc
            ).select_related("portal_category__portal")
            for mapping in mappings:
                portals.append((mapping.portal_category.portal, mapping.portal_category))

    return portals
