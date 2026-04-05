# Sprint Roadmap - Modular News Platform

**Project:** LiquorNewsUSA (First Vertical)
**Sprint Duration:** 1 week each
**Start Date:** 2026-04-05
**Methodology:** Build small, deploy, test, document, next

---

## Sprint 0: Foundation (Current - Week of Apr 5)
**Goal:** Architecture, config, scaffolding. No visible features yet.

| Task | Status | Deliverable |
|------|--------|-------------|
| Project folder structure | Done | `/liquor-news-platform/` tree |
| Master config schema | Done | `config/site.config.json` + supporting configs |
| Component registry | Done | `.registry/manifest.json` |
| Tech stack decisions | Done | `docs/decisions/001-003` |
| Sprint roadmap | Done | This document |
| Hugo site scaffold | Pending | Working Hugo site that builds locally |
| Base theme scaffold | Pending | `themes/_base/` with layout templates |
| GitHub repo + Actions | Pending | CI/CD pipeline deploying to GitHub Pages |
| Documentation | Pending | Architecture docs, memory files |

**Deploy target:** Empty site live at domain with "Coming Soon" page
**Test:** `hugo build` succeeds, GitHub Actions deploys, site loads via Cloudflare

---

## Sprint 1: RSS Engine + Content Queue (Week of Apr 12)
**Goal:** Automated content ingestion from RSS feeds

| Task | Deliverable |
|------|-------------|
| Python RSS fetcher script | `scripts/rss-fetch.py` |
| Feed parser with keyword filtering | Reads `config/rss-feeds.json`, filters by keywords |
| Deduplication engine | `data/seen-urls.json` + fuzzy title matching |
| Markdown generator | Creates Hugo-compatible `.md` files with frontmatter |
| Content queue folder | `content/queue/` for editorial review |
| GitHub Actions cron job | `.github/workflows/rss-fetch.yml` - runs every 30 min |
| Health check script | `tests/rss-engine-health.sh` |
| Feed validation | Test all 32 feeds, document which are live vs need fallbacks |

**Deploy target:** RSS engine running on schedule, generating draft content
**Test:** Cron fires, feeds parse, Markdown files appear in repo, no duplicates

---

## Sprint 2: Base Theme + Liquor News Theme (Week of Apr 19)
**Goal:** Professional news site layout, mobile-responsive, ad-slot ready

| Task | Deliverable |
|------|-------------|
| Base theme layouts | `themes/_base/layouts/` - home, single, list, taxonomy |
| Homepage: hero + grid + sidebar | News-magazine layout per market analysis spec |
| Article page template | Full article with byline, date, tags, share buttons, ad slots |
| Category page template | Filtered views per content pillar |
| Texas Spotlight section | Dedicated homepage band for regional content |
| Mobile responsive | All layouts work on 320px+ screens |
| Ad slot partials | Hugo partials for each IAB placement from `ad-slots.json` |
| Liquor News color/font overrides | `themes/liquor-news/` extending base |
| Breaking news ticker | Horizontal scroll bar for latest alerts |

**Deploy target:** Full site layout live with seed content from Sprint 1
**Test:** Lighthouse score 90+, all ad slots render, mobile works

---

## Sprint 3: SEO Engine + Ad System (Week of Apr 26)
**Goal:** Search-optimized, ad-revenue ready

| Task | Deliverable |
|------|-------------|
| SEO meta tags automation | Auto-generate title, description, OG tags from config |
| Schema markup (JSON-LD) | NewsArticle, Organization, WebSite, BreadcrumbList |
| Sitemap generation | Hugo built-in sitemap + custom news sitemap |
| robots.txt | Config-driven via Hugo template |
| Google AdSense integration | Ad slots populated with AdSense code |
| Ad slot lazy loading | Lazy load below-fold ads for performance |
| Sponsored content template | Labeled native ad format |
| Google Analytics 4 setup | Tracking code + basic event configuration |
| Google Search Console | Verify ownership, submit sitemap |

**Deploy target:** SEO-optimized site with live ad placements
**Test:** Schema validation passes, ads render, GA4 tracking fires

---

## Sprint 4: Newsletter Engine (Week of May 3)
**Goal:** Email capture and automated digest

| Task | Deliverable |
|------|-------------|
| Signup form component | Reusable embedded form (Beehiiv or Mailchimp) |
| Dedicated signup landing page | `/newsletter/` with value proposition |
| In-article signup CTA | Mid-article and end-of-article prompts |
| Popup/slide-in trigger | Scroll-based or exit-intent signup prompt |
| Weekly digest template | Automated email pulling top articles from the week |
| Newsletter sponsor slot | Ad placement in digest header |
| Welcome email sequence | 3-email onboarding for new subscribers |

**Deploy target:** Working newsletter signup capturing real emails
**Test:** Signup flow works, confirmation email sends, digest generates

---

## Sprint 5: Social + Analytics Dashboard (Week of May 10)
**Goal:** Social distribution and content performance tracking

| Task | Deliverable |
|------|-------------|
| Social meta tags | Twitter Card + OG tags per article |
| Auto-post script | Python script generating social posts from new content |
| Social post templates | Config-driven post format per platform |
| Buffer/Hootsuite integration | Or custom posting via platform APIs |
| Content metrics dashboard | HTML dashboard showing posts/day, top articles, traffic |
| Publishing cadence tracker | Are we hitting 3-5 posts/day? |
| RSS feed output | Hugo-generated RSS for readers + syndication |
| UptimeRobot monitoring | Free uptime check every 5 minutes |

**Deploy target:** Social posts auto-generated, dashboard accessible
**Test:** New article triggers social drafts, dashboard loads with data

---

## Sprint 6: Content Seeding + Launch Prep (Week of May 17)
**Goal:** 15-20 seed articles, all systems tested, soft launch

| Task | Deliverable |
|------|-------------|
| Seed 15-20 articles across all pillars | Real content covering each pillar |
| About / Mission page | Editorial mission, team bio |
| Advertise With Us page | Media kit, audience stats, rate card, contact form |
| Events calendar page | Texas tastings, festivals, trade shows |
| Contact page | Press inquiries, advertising, tips |
| Full system integration test | RSS -> Queue -> Publish -> Social -> Newsletter |
| Performance audit | Lighthouse, WebPageTest, mobile speed |
| Launch checklist | Pre-launch verification document |

**Deploy target:** Fully operational site ready for public launch
**Test:** End-to-end flow works, all pages load, all components healthy

---

## Post-Launch Sprints (Month 2+)

| Sprint | Focus |
|--------|-------|
| Sprint 7 | Content velocity - ramp to 3-5 posts/day |
| Sprint 8 | SEO optimization based on Search Console data |
| Sprint 9 | Direct advertiser outreach + media kit refinement |
| Sprint 10 | Community features (comments, events submissions) |
| Sprint 11 | Data visualizations + infographic templates |
| Sprint 12 | Second vertical evaluation + replication test |
