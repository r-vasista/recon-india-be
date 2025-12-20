import feedparser
from datetime import datetime
from .models import NewsArticle, NewsSourceFeed
from django.utils.timezone import make_aware
import json

import feedparser
import time
import json
from datetime import datetime
from django.utils import timezone
from .models import NewsArticle, NewsSourceFeed


def fetch_and_store_dynamic_rss_data():
    """Fetch and store articles from dynamic RSS feeds safely"""

    rss_feeds = NewsSourceFeed.objects.all()

    for feed in rss_feeds:
        source_feed_url = feed.rss_url
        source = feed.source

        feed_data = feedparser.parse(source_feed_url)

        for entry in feed_data.entries:

            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            summary = getattr(entry, "summary", "") or ""
            content = ""

            if hasattr(entry, "content") and entry.content:
                content = entry.content[0].get("value", "")

            # ✅ SAFE published date parse
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime.fromtimestamp(
                    time.mktime(entry.published_parsed),
                    tz=timezone.get_current_timezone()
                )
            else:
                published = timezone.now()

            author = getattr(entry, "author", None)

            # ✅ Image detection from all possible formats
            image_url = None

            if "media_thumbnail" in entry:
                image_url = entry.media_thumbnail[0].get("url")

            elif "media_content" in entry:
                image_url = entry.media_content[0].get("url")

            elif "image" in entry:
                image_url = entry.image.get("href")

            tags = entry.get("tags", [])
            tags_json = json.dumps([tag["term"] for tag in tags]) if tags else None

            guid = entry.get("id") or entry.get("guid") or link

            # ✅ Duplicate protection
            if NewsArticle.objects.filter(guid=guid).exists():
                continue

            NewsArticle.objects.create(
                title=title,
                link=link,
                summary=summary,
                content=content,
                published_at=published,
                source_feed=feed,
                guid=guid,
                author=author,
                image_url=image_url,
                tags=tags_json,
            )

        print(f"✅ Fetched and stored from: {source.name} - {feed.section_name}")