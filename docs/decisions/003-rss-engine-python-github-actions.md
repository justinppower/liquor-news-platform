# Decision 003: Python RSS Engine Running on GitHub Actions

**Date:** 2026-04-05
**Status:** Accepted
**Decider:** Justin Power + Claude (architect)

## Context

Need an automated RSS aggregation system that fetches feeds, filters by keyword, deduplicates, and creates draft content for the Hugo site. Must be free to run.

## Decision

Build the RSS engine as a **Python script** triggered by **GitHub Actions** on a cron schedule (every 30 minutes).

## Rationale

### Why Python:
- `feedparser` library is battle-tested for RSS parsing
- Simple keyword filtering and deduplication logic
- Can write Markdown files directly to the Hugo content folder
- Easy to extend with AI summarization later
- Justin's team can read and modify Python more easily than Go

### Why GitHub Actions cron:
- Free scheduled execution (every 30 min = ~1,440 runs/month, well within free tier)
- No server to maintain
- Logs and error reporting built in
- Can be triggered manually for testing
- Same CI/CD platform as the site deploy

### Workflow:
1. GitHub Actions cron triggers `scripts/rss-fetch.py` every 30 minutes
2. Script reads `config/rss-feeds.json` for feed URLs and keywords
3. Fetches all feeds, filters by keyword, deduplicates against existing content
4. Generates Markdown files in `content/queue/` with frontmatter (title, source, date, pillar, status: draft)
5. If `config.rss.auto_draft` is true, also commits to `content/[pillar]/` as drafts
6. Commits new content files and pushes (triggers Hugo rebuild via separate action)

### Deduplication strategy:
- Store seen article URLs in `data/seen-urls.json`
- 72-hour window (configurable via `config.rss.dedup_window_hours`)
- Match on URL and title similarity (fuzzy match threshold: 85%)

## Trade-offs

- **No real-time**: 30-minute delay is acceptable for a news aggregation site. Not a live trading platform.
- **GitHub Actions minutes**: At 30-min intervals, ~1,440 runs/month. Each run ~1-2 minutes. Total: ~2,000 minutes. Fits in free tier for public repos.
- **No persistent database**: Using JSON file for dedup state. Fine for our scale. If we hit thousands of articles, we can migrate to SQLite (still file-based, still free).

## Cost

$0/mo
