# Decision 002: GitHub Pages + Cloudflare Over Paid Hosting

**Date:** 2026-04-05
**Status:** Accepted
**Decider:** Justin Power + Claude (architect)

## Context

Need hosting that is free or near-free, reliable, fast, and easy to replicate for additional verticals.

## Decision

- **Primary hosting**: GitHub Pages (free for public repos, free for private repos on Pro plan at $4/mo if needed)
- **CDN + SSL + DNS**: Cloudflare free tier
- **CI/CD**: GitHub Actions (free for public repos, 2000 min/mo free for private)

## Rationale

### GitHub Pages:
- $0/mo for unlimited bandwidth on public repos
- Automatic HTTPS
- Direct integration with GitHub Actions for build pipeline
- Custom domain support
- 100GB/mo bandwidth (more than enough for a new publication)

### Cloudflare Free Tier:
- DNS management
- Free SSL certificate
- CDN with global edge caching
- DDoS protection
- Page rules for caching optimization
- Analytics (basic)

### GitHub Actions:
- Trigger Hugo build on every push to main
- Build time for Hugo sites: ~10-30 seconds
- Free tier: 2,000 minutes/month (private) or unlimited (public)
- Handles our deploy pipeline entirely

## Architecture

```
[Git Push] -> [GitHub Actions: Hugo Build] -> [GitHub Pages: Static Files] -> [Cloudflare CDN] -> [User]
```

## Scaling Path

If we hit GitHub Pages limits (100GB/mo bandwidth, ~100K unique visitors/month):
- Migrate to Cloudflare Pages (free, 500 builds/mo, unlimited bandwidth)
- Or Vercel free tier (100GB bandwidth)
- Or Netlify free tier (100GB bandwidth)

All accept Hugo output. Migration = changing the deploy target in GitHub Actions. Zero code changes.

## Cost

| Service | Monthly Cost |
|---------|-------------|
| GitHub Pages | $0 |
| Cloudflare Free | $0 |
| GitHub Actions | $0 |
| Domain (annual) | ~$12/yr = $1/mo |
| **Total** | **~$1/mo** |
