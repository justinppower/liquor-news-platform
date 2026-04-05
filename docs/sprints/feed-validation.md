# RSS Feed Validation Results

**Date:** 2026-04-05
**Sprint:** 1 - RSS Engine + Content Queue

## Operational Feeds (16/27)

| Feed | Tier | Status | Entries |
|------|------|--------|---------|
| BevNET | Tier 1 Trade | OK | 20 |
| Brewbound | Tier 1 Trade | OK | 20 |
| The Spirits Business | Tier 1 Trade | OK | 30 |
| The Drinks Business | Tier 1 Trade | OK | 30 |
| SevenFifty Daily | Tier 1 Trade | OK | 10 |
| VinePair | Tier 2 Enthusiast | OK | 55 |
| Punch | Tier 2 Enthusiast | OK | 10 |
| Imbibe Magazine | Tier 2 Enthusiast | OK | 5 |
| The Bourbon Review | Tier 2 Enthusiast | OK | 10 |
| Craft Spirits Magazine | Tier 2 Enthusiast | OK | 10 |
| Shanken News Daily | Tier 3 Wire | OK | 6 |
| Texas Monthly | Tier 4 Regional | OK | 25 |
| Eater Dallas | Tier 4 Regional | OK | 10 |
| Eater Houston | Tier 4 Regional | OK | 10 |
| Eater Austin | Tier 4 Regional | OK | 10 |
| DISCUS | Tier 5 Regulatory | OK | 7 |

## Non-Operational Feeds (6/27)

| Feed | Tier | Issue | Action |
|------|------|-------|--------|
| PR Newswire | Tier 3 Wire | Syntax error - no valid RSS | Replace or scrape |
| TABC News | Tier 4 Regional | Invalid XML token | Needs scraper (Sprint 3+) |
| Dallas Morning News | Tier 4 Regional | Paywall / invalid XML | Needs scraper or drop |
| Houston Chronicle | Tier 4 Regional | Paywall / invalid XML | Needs scraper or drop |
| NABCA News | Tier 5 Regulatory | No RSS available | Needs scraper (Sprint 3+) |
| TTB News | Tier 5 Regulatory | Invalid XML token | Needs scraper (Sprint 3+) |

## Google Alerts (5 - Pending Setup)

These feeds need Google Alerts configured with RSS output. Justin will need to set these up with his Google account and paste the feed URLs into `config/rss-feeds.json`.

- Texas distillery
- bourbon release
- TABC
- liquor law Texas
- spirits M&A

## First Fetch Results

- **109 articles** matched keyword filters from 16 feeds
- **99 articles** skipped (no keyword match)
- **6 feed errors** (expected - non-operational feeds)
- **Dedup verified** - second run produced 0 new articles
- Articles distributed across: industry-news, new-releases, texas-beat, culture-lifestyle, regulation-policy

## Changes from Sprint 0

- Replaced Beverage Industry feed with SevenFifty Daily (better coverage)
- Replaced Whisky Advocate with Imbibe Magazine (working RSS)
- Replaced BusinessWire with Shanken News Daily (better industry coverage)
- Fixed BevNET URL: `/rss/news` -> `/feed`
- Fixed Brewbound URL: `/rss/news` -> `/feed`
- Fixed Craft Spirits URL: `craftspiritmag.com` -> `craftspiritsmag.com`
