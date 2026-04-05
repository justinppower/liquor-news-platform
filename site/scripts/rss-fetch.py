#!/usr/bin/env python3
"""
RSS Feed Aggregator - Modular News Platform
============================================
Fetches, filters, deduplicates, and queues RSS content from configured feeds.
Generates Hugo-compatible Markdown files with frontmatter.

This script is designed to be reusable across verticals.
All vertical-specific config comes from config/rss-feeds.json and config/site.config.json.

Usage:
    python scripts/rss-fetch.py                    # Normal run
    python scripts/rss-fetch.py --dry-run          # Preview without writing files
    python scripts/rss-fetch.py --validate-feeds   # Test which feeds are reachable

Runs via GitHub Actions on a 30-minute cron schedule.
"""

import html
import json
import os
import re
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import feedparser
except ImportError:
    print("ERROR: feedparser not installed. Run: pip install feedparser")
    exit(1)

try:
    from dateutil import parser as dateparser
except ImportError:
    dateparser = None

# --- Configuration ---

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = PROJECT_ROOT.parent / "config"
CONTENT_DIR = PROJECT_ROOT / "content" / "queue"
DATA_DIR = PROJECT_ROOT / "data"
SEEN_URLS_FILE = DATA_DIR / "seen-urls.json"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("rss-engine")


def load_config():
    """Load RSS feeds config and site config."""
    feeds_path = CONFIG_DIR / "rss-feeds.json"
    site_path = CONFIG_DIR / "site.config.json"

    if not feeds_path.exists():
        logger.error(f"RSS feeds config not found: {feeds_path}")
        return None, None

    with open(feeds_path, "r") as f:
        feeds_config = json.load(f)

    site_config = {}
    if site_path.exists():
        with open(site_path, "r") as f:
            site_config = json.load(f)

    return feeds_config, site_config


def load_seen_urls():
    """Load previously seen article URLs for deduplication."""
    if SEEN_URLS_FILE.exists():
        with open(SEEN_URLS_FILE, "r") as f:
            return json.load(f)
    return {"urls": {}, "last_cleanup": datetime.now(timezone.utc).isoformat()}


def save_seen_urls(seen_data):
    """Save seen URLs to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SEEN_URLS_FILE, "w") as f:
        json.dump(seen_data, f, indent=2)


def cleanup_seen_urls(seen_data, window_hours=72):
    """Remove URLs older than the dedup window."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    cutoff_str = cutoff.isoformat()

    original_count = len(seen_data["urls"])
    seen_data["urls"] = {
        url: ts for url, ts in seen_data["urls"].items()
        if ts > cutoff_str
    }
    removed = original_count - len(seen_data["urls"])
    if removed > 0:
        logger.info(f"Cleaned up {removed} expired URLs from dedup cache")

    seen_data["last_cleanup"] = datetime.now(timezone.utc).isoformat()
    return seen_data


def matches_keywords(text, keywords):
    """Check if text contains any of the configured keywords."""
    if not keywords:
        return True
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def slugify(text):
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text[:80].rstrip('-')


def determine_pillar(entry, feed_config, site_config):
    """Map a feed entry to a content pillar based on feed category and keywords."""
    category = feed_config.get("category", "")

    pillar_map = {
        "trade": "industry-news",
        "press_release": "industry-news",
        "enthusiast": "new-releases",
        "culture": "culture-lifestyle",
        "regulatory": "regulation-policy",
        "regional": "texas-beat",
        "alert": "industry-news",
    }

    # Check for Texas-specific content
    title = entry.get("title", "")
    summary = entry.get("summary", "")
    combined = f"{title} {summary}".lower()

    texas_keywords = ["texas", "tabc", "dallas", "houston", "austin", "san antonio", "fort worth"]
    if any(kw in combined for kw in texas_keywords):
        return "texas-beat"

    return pillar_map.get(category, "industry-news")


def generate_markdown(entry, feed_config, pillar):
    """Generate Hugo-compatible Markdown from an RSS entry."""
    title = html.unescape(entry.get("title", "Untitled").strip())
    link = entry.get("link", "")
    summary = entry.get("summary", "")

    # Clean HTML from summary and decode entities
    summary_clean = html.unescape(re.sub(r'<[^>]+>', '', summary).strip())
    if len(summary_clean) > 300:
        summary_clean = summary_clean[:297] + "..."

    # Parse date
    published = entry.get("published", "")
    if published and dateparser:
        try:
            dt = dateparser.parse(published)
            date_str = dt.strftime("%Y-%m-%dT%H:%M:%S%z")
        except Exception:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    else:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    # Build frontmatter
    safe_title = title.replace('"', "'")
    safe_desc = summary_clean[:160].replace('"', "'")
    source_name = feed_config.get("name", "Unknown")
    pillar_display = pillar.replace("-", " ").title()
    tags_json = json.dumps(feed_config.get("keywords_boost", []))

    frontmatter = f"""---
title: "{safe_title}"
date: {date_str}
draft: true
pillars: ["{pillar}"]
tags: {tags_json}
categories: ["{pillar_display}"]
author: "RSS Feed"
description: "{safe_desc}"
source_url: "{link}"
source_name: "{source_name}"
article_type: "news_brief"
auto_generated: true
---

{summary_clean}

*Source: [{source_name}]({link})*
"""
    return frontmatter


def fetch_feeds(feeds_config, site_config, seen_data, dry_run=False):
    """Main feed fetching loop."""
    rss_config = site_config.get("rss", {})
    keyword_filters = rss_config.get("keyword_filters", [])
    max_items = rss_config.get("max_items_per_feed", 20)

    all_feeds = []
    for tier_key, tier_feeds in feeds_config.get("feeds", {}).items():
        all_feeds.extend(tier_feeds)

    new_articles = 0
    skipped_seen = 0
    skipped_filter = 0
    feed_errors = 0

    for feed_config in all_feeds:
        url = feed_config.get("url", "")
        name = feed_config.get("name", "Unknown")

        if not url:
            logger.debug(f"Skipping {name}: no URL configured")
            continue

        logger.info(f"Fetching: {name}")
        try:
            parsed = feedparser.parse(url)

            if parsed.bozo and not parsed.entries:
                logger.warning(f"Feed error for {name}: {parsed.bozo_exception}")
                feed_errors += 1
                continue

            for entry in parsed.entries[:max_items]:
                link = entry.get("link", "")
                title = entry.get("title", "")

                # Dedup check
                if link in seen_data["urls"]:
                    skipped_seen += 1
                    continue

                # Keyword filter
                combined_text = f"{title} {entry.get('summary', '')}"
                if keyword_filters and not matches_keywords(combined_text, keyword_filters):
                    skipped_filter += 1
                    continue

                # Determine pillar
                pillar = determine_pillar(entry, feed_config, site_config)

                # Generate markdown
                markdown = generate_markdown(entry, feed_config, pillar)
                slug = slugify(title)
                filename = f"{slug}.md"

                if not dry_run:
                    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
                    filepath = CONTENT_DIR / filename
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(markdown)
                    logger.info(f"  Created: {filename} [{pillar}]")
                else:
                    logger.info(f"  [DRY RUN] Would create: {filename} [{pillar}]")

                # Mark as seen
                seen_data["urls"][link] = datetime.now(timezone.utc).isoformat()
                new_articles += 1

        except Exception as e:
            logger.error(f"Error fetching {name}: {e}")
            feed_errors += 1

    logger.info(f"\n--- RSS Fetch Summary ---")
    logger.info(f"New articles: {new_articles}")
    logger.info(f"Skipped (seen): {skipped_seen}")
    logger.info(f"Skipped (no keyword match): {skipped_filter}")
    logger.info(f"Feed errors: {feed_errors}")

    return new_articles


def validate_feeds(feeds_config):
    """Test which feeds are reachable."""
    all_feeds = []
    for tier_key, tier_feeds in feeds_config.get("feeds", {}).items():
        all_feeds.extend(tier_feeds)

    results = []
    for feed_config in all_feeds:
        url = feed_config.get("url", "")
        name = feed_config.get("name", "Unknown")

        if not url:
            results.append({"name": name, "status": "NO_URL", "entries": 0})
            continue

        try:
            parsed = feedparser.parse(url)
            entry_count = len(parsed.entries)
            status = "OK" if entry_count > 0 else "EMPTY"
            if parsed.bozo:
                status = "BOZO" if entry_count > 0 else "ERROR"
            results.append({"name": name, "status": status, "entries": entry_count})
        except Exception as e:
            results.append({"name": name, "status": f"ERROR: {e}", "entries": 0})

    logger.info("\n--- Feed Validation Results ---")
    for r in results:
        icon = "OK" if r["status"] == "OK" else "!!"
        logger.info(f"  [{icon}] {r['name']}: {r['status']} ({r['entries']} entries)")

    ok_count = sum(1 for r in results if r["status"] == "OK")
    logger.info(f"\n{ok_count}/{len(results)} feeds operational")
    return results


if __name__ == "__main__":
    import sys

    dry_run = "--dry-run" in sys.argv
    validate_only = "--validate-feeds" in sys.argv

    feeds_config, site_config = load_config()
    if not feeds_config:
        logger.error("Could not load config. Exiting.")
        exit(1)

    if validate_only:
        validate_feeds(feeds_config)
        exit(0)

    seen_data = load_seen_urls()
    seen_data = cleanup_seen_urls(seen_data, window_hours=site_config.get("rss", {}).get("dedup_window_hours", 72))

    new_count = fetch_feeds(feeds_config, site_config, seen_data, dry_run=dry_run)

    if not dry_run:
        save_seen_urls(seen_data)

    logger.info("Done.")
