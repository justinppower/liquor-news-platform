# Decision 001: Hugo (Static Site Generator) Over WordPress

**Date:** 2026-04-05
**Status:** Accepted
**Decider:** Justin Power + Claude (architect)

## Context

The market analysis document recommended WordPress as the CMS. After evaluating against the project's core principles (low/no cost, modular, replicable, scalable), we reconsidered.

## Decision

Use **Hugo** (static site generator) deployed to **GitHub Pages** with **Cloudflare** CDN instead of WordPress.

## Rationale

### Why NOT WordPress:
- **Hosting cost**: WordPress requires a server ($25-45/mo for managed hosting). Hugo + GitHub Pages = $0/mo
- **Security surface**: WordPress is the #1 target for web attacks. Plugins require constant updates. Static sites have zero server-side attack surface
- **Performance**: Static HTML served via CDN is 10-50x faster than dynamic PHP/MySQL
- **Vendor lock-in**: WordPress themes and plugins create tight coupling. Hugo templates are plain HTML/Go templates
- **Replication complexity**: Spinning up a new WordPress site means provisioning a new server, database, and plugin stack. Hugo = copy config, deploy

### Why Hugo:
- **Zero hosting cost**: GitHub Pages is free for public repos. Cloudflare free tier for CDN and SSL
- **Speed**: Builds 10,000 pages in under 10 seconds. Fastest SSG available
- **Content as files**: Markdown files in a folder. No database. Easy to version control, backup, and replicate
- **RSS built-in**: Hugo generates RSS feeds natively from content
- **Taxonomy system**: Tags, categories, and custom taxonomies out of the box - maps perfectly to our content pillars
- **Theme system**: Hugo's theme inheritance model matches our _base + vertical-specific override pattern exactly
- **Go templates**: Powerful templating without a JavaScript build step
- **Single binary**: No dependency hell. One binary handles everything

### Trade-offs accepted:
- **No admin UI**: Content is managed via Git, not a web dashboard. For a 1-2 person team, this is fine. If a non-technical editor joins later, we can add Decap CMS (formerly Netlify CMS) as a Git-based admin UI - still free
- **No built-in comments**: Use Disqus (free) or utterances (GitHub-based, free) if needed later
- **No plugin ecosystem**: We build what we need as Hugo modules or standalone scripts. This is actually an advantage for replication - no plugin compatibility issues

## Cost Comparison

| Item | WordPress | Hugo + GitHub Pages |
|------|-----------|-------------------|
| Hosting | $25-45/mo | $0/mo |
| SSL | Included or $10/mo | Free (Cloudflare) |
| CDN | $10-20/mo extra | Free (Cloudflare) |
| Theme | $59-199 one-time | Custom (we build it) |
| Plugins | $0-200/yr | N/A |
| Database | Included in hosting | None needed |
| **Year 1 total** | **$420-840+** | **$0-15** (domain only) |

## Consequences

- All content authored in Markdown
- Deployment via `git push` triggers GitHub Actions build
- RSS integration handled by scripts that generate Markdown files from feeds
- Ad slots rendered as Hugo partials reading from config
- Newsletter signup via embedded form (Mailchimp/Beehiiv) - no server needed
