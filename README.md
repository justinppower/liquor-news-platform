# Modular News Platform System

A config-driven, component-based news platform architecture designed for replication across verticals. First deployment: U.S. Liquor & Alcohol News with Texas market focus.

## Architecture Principles

1. **Config-driven** - No vertical-specific values hardcoded. Every site-specific detail lives in `config/site.config.json`
2. **Component-based** - Each feature (RSS, ads, newsletter, SEO) is an independent module in `components/`
3. **Theme-separated** - Visual layer is decoupled from logic. Themes live in `themes/` and reference config values
4. **Registry-tracked** - Every component is registered in `.registry/manifest.json` with version, status, and dependencies
5. **Sprint-built** - Each component is built, deployed, tested, and documented before the next begins

## Folder Structure

```
liquor-news-platform/
  config/                    # All configuration files
    site.config.json         # Master site config (swap this to replicate)
    rss-feeds.json           # RSS feed sources (per-vertical)
    ad-slots.json            # Ad placement definitions
    content-pillars.json     # Editorial categories
  components/                # Independent, reusable modules
    rss-engine/              # RSS aggregation + content queue
    ad-system/               # Ad placement and management
    newsletter-engine/       # Email capture + distribution
    content-queue/           # Standardized content pipeline
    analytics-dashboard/     # Traffic + content metrics
    seo-engine/              # SEO automation + schema markup
    social-scheduler/        # Social media post scheduling
  themes/                    # Visual layer
    _base/                   # Base theme (shared across verticals)
    liquor-news/             # Vertical-specific overrides
  docs/                      # All documentation
    decisions/               # Decision log (why X over Y)
    sprints/                 # Sprint plans and retrospectives
    architecture/            # System architecture docs
    runbooks/                # How-to guides for operations
  scripts/                   # Build, deploy, and utility scripts
  tests/                     # Component tests and health checks
  .registry/                 # Component registry
    manifest.json            # Master component manifest
```

## Replication Guide

To launch a new vertical:
1. Copy `config/site.config.json` and update for new vertical
2. Create new theme in `themes/[vertical-name]/` extending `_base`
3. Update `config/rss-feeds.json` with vertical-specific sources
4. Update `config/content-pillars.json` with editorial categories
5. Deploy using the same component stack

## First Vertical: LiquorNewsUSA

- Domain: (pending from Justin)
- Target: U.S. alcohol industry + Texas market focus
- Dual audience: industry professionals + consumers
- Daily publishing cadence: 3-5 pieces/day
