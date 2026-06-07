#!/usr/bin/env python3
"""
Package Store RSS Aggregator.

Daily run:
1. Fetch RSS from data/sources.json feeds
2. Classify each item into a pillar via keyword match
3. Build/update homepage hero, sidebar, story grid + each pillar page
4. Generate one stub HTML page per story under /{pillar}/{slug}/ with
   headline, dek, source attribution, "Read at source" link
5. Output to _build/ which gets tarred and committed as site-bundle.b64

The static brand chrome (header, footer, masthead, nav, CSS, voice docs, pages
that aren't dynamic — about, advertise, marketplace, newsletter, contact,
privacy, 404, sample article) is copied verbatim from the existing site folder.
"""
import json
import os
import re
import sys
import time
import html
import shutil
import hashlib
import unicodedata
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).parent.parent
BUILD = Path(os.environ.get("PACKAGE_STORE_BUILD_DIR", str(ROOT / "_build")))
DATA = ROOT / "data" / "sources.json"
ARCHIVE = ROOT / "data" / "archive.json"

# Number of stories to keep per pillar in the rolling feed
PER_PILLAR_LIMIT = 300
# Max age of stories to include (days)
MAX_AGE_DAYS = 120
# Today reference for dates (UTC)
NOW = datetime.now(timezone.utc)


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text[:80] or "story"


def parse_rss(url: str, timeout: int = 25):
    """Minimal RSS/Atom parser using stdlib only (no feedparser dep)."""
    try:
        req = Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; PackageStoreBot/1.0; +https://packagestoretx.com)"
        })
        with urlopen(req, timeout=timeout) as r:
            raw = r.read()
    except (URLError, HTTPError, TimeoutError, ConnectionResetError) as e:
        print(f"  FAIL: {url} ({type(e).__name__})", file=sys.stderr)
        return []

    text = raw.decode("utf-8", errors="ignore")
    items = []

    # RSS 2.0 <item>
    for match in re.finditer(r"<item[\s>](.+?)</item>", text, re.DOTALL | re.IGNORECASE):
        block = match.group(1)
        items.append(_extract_block(block, is_atom=False))

    # Atom <entry>
    if not items:
        for match in re.finditer(r"<entry[\s>](.+?)</entry>", text, re.DOTALL | re.IGNORECASE):
            block = match.group(1)
            items.append(_extract_block(block, is_atom=True))

    return [i for i in items if i and i.get("title") and i.get("link")]


def _extract_block(block: str, is_atom: bool):
    def tag(name, default=""):
        m = re.search(fr"<{name}[\s>](.*?)</{name}>", block, re.DOTALL | re.IGNORECASE)
        if not m:
            return default
        val = m.group(1).strip()
        # Strip CDATA
        cdata = re.match(r"<!\[CDATA\[(.*?)\]\]>", val, re.DOTALL)
        if cdata:
            val = cdata.group(1)
        return html.unescape(val).strip()

    title = tag("title")
    if is_atom:
        # Atom uses <link href="..."/>
        m = re.search(r'<link[^>]*href="([^"]+)"', block)
        link = m.group(1) if m else ""
        date_str = tag("published") or tag("updated")
    else:
        link = tag("link")
        date_str = tag("pubDate") or tag("dc:date")

    description = tag("description") or tag("summary") or tag("content")
    # Strip HTML from description
    description = re.sub(r"<[^>]+>", "", description)
    description = re.sub(r"\s+", " ", description).strip()
    if len(description) > 280:
        description = description[:280].rsplit(" ", 1)[0] + "…"

    pub = parse_date(date_str)
    return {
        "title": title,
        "link": link,
        "description": description,
        "published": pub.isoformat() if pub else None,
        "published_dt": pub,
    }


def parse_date(s: str):
    if not s:
        return None
    fmts = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    s = s.strip().replace("GMT", "+0000").replace("UTC", "+0000")
    for f in fmts:
        try:
            d = datetime.strptime(s, f)
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d
        except (ValueError, TypeError):
            continue
    return None



# Only keep alcohol/drinks-trade items (filters out food, soda, tea, sports drinks, etc.)
RELEVANT = [
    "wine", "winery", "winerie", "vineyard", "vintage", "champagne", "prosecco", "rose", "rose",
    "sommelier", "beer", "brewer", "brewery", "brewerie", "brewing", "ipa", "lager", " ale", "ales",
    "stout", "pilsner", "cider", "spirit", "whiskey", "whisky", "bourbon", "scotch", " rye", "tequila",
    "mezcal", "vodka", " gin", "gins", "rum", "cognac", "brandy", "liqueur", "cocktail", "distiller",
    "distillery", "distillerie", "distilling", "abv", "proof", "cask", "barrel", "bottle", "rtd",
    "ready-to-drink", "seltzer", "sake", "vermouth", "aperitif", "aperitivo", "amaro", "bitters",
    "tabc", "ttb", "three-tier", "distributor", "on-premise", "off-premise", "on-prem", "off-prem",
    "package store", "liquor", "alcohol", "malt", "agave", "bartender", "winemaker", "drinks", "drinking",
    "pinot", "cabernet", "chardonnay", "merlot", "riesling", "nebbiolo", "sauvignon", "syrah", "grenache",
    "bordeaux", "burgundy", "napa", "sparkling wine", "anejo", "rioja", "non-alcoholic", "low-abv", "spirits",
]


def is_relevant(item) -> bool:
    hay = (item.get("title", "") + " " + item.get("description", "")).lower()
    return any(k in hay for k in RELEVANT)


def classify(item, classifier: dict, default: str) -> str:
    haystack = (item["title"] + " " + item["description"]).lower()
    for pillar, keywords in classifier.items():
        if not keywords:
            continue
        for kw in keywords:
            if kw in haystack:
                return pillar
    return default


def fetch_all(cfg) -> list:
    print(f"=== Fetching {len(cfg['feeds'])} feeds ===")
    all_items = []
    for feed in cfg["feeds"]:
        print(f"  → {feed['name']}")
        items = parse_rss(feed["url"])
        for it in items:
            it["source"] = feed["name"]
            it["source_id"] = feed["id"]
            it["pillar"] = classify(it, cfg["classifier"], feed["default_pillar"])
        all_items.extend(items)
        print(f"      {len(items)} items")
    # Topic filter: drinks/alcohol only
    before = len(all_items)
    all_items = [i for i in all_items if is_relevant(i)]
    print(f"  topic filter: kept {len(all_items)}/{before} drinks items")
    # Filter by age
    cutoff = NOW - timedelta(days=MAX_AGE_DAYS)
    fresh = [i for i in all_items if i.get("published_dt") and i["published_dt"] >= cutoff]
    fresh.sort(key=lambda x: x["published_dt"], reverse=True)
    # Deduplicate by slug
    seen, deduped = set(), []
    for it in fresh:
        s = slugify(it["title"])
        if s in seen:
            continue
        seen.add(s)
        it["slug"] = s
        deduped.append(it)
    print(f"=== Total: {len(deduped)} unique fresh items ===")
    return deduped


def short_date(dt: datetime) -> str:
    return dt.strftime("%b %-d") if dt else ""


def kicker_for(item) -> str:
    src = (item.get("source") or "").lower()
    if "shanken" in src or "spirits" in src or "drinks business" in src:
        return "Industry"
    if "vinepair" in src:
        return "Culture"
    if "texas" in src:
        return "Texas"
    if "brewbound" in src:
        return "Beer"
    if "punch" in src or "imbibe" in src:
        return "Drinks"
    return "News"


# =====================
# TEMPLATES
# =====================

CSS_HREF = "/assets/css/brand.css"
GOOGLE_FONTS = (
    '<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700;9..144,900'
    '&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
)


def base_head(title, description, canonical):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="canonical" href="{canonical}">
<link rel="icon" type="image/svg+xml" href="/assets/logos/PackageStore_Favicon.svg">
<meta name="theme-color" content="#0A0A0A">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canonical}">
<meta property="og:site_name" content="Package Store.">
<meta property="og:image" content="https://packagestoretx.com/assets/img/og-default.jpg">
<meta name="twitter:card" content="summary_large_image">
{GOOGLE_FONTS}
<link rel="stylesheet" href="{CSS_HREF}">
</head>
<body>"""


def topbar(active_home=False):
    return f"""
<div class="topbar">
  <div class="container">
    <div class="topbar-left">
      {'<span>Home</span>' if active_home else '<a href="/">Home</a>'}
      <span class="hide-mobile">{NOW.strftime("%A · %B %-d, %Y")}</span>
    </div>
    <div class="topbar-right">
      <a href="/newsletter/">Weekly Digest</a>
      <a href="/marketplace/">Marketplace</a>
      <a href="/advertise/">Advertise</a>
    </div>
  </div>
</div>
"""


def masthead(big=False):
    if big:
        return f"""
<header class="masthead">
  <div class="container">
    <div class="masthead-eyebrow">U.S. Drinks Trade · Vol. I</div>
    <div class="wordmark">PACKAGE STORE<span class="stop">.</span></div>
    <div class="tagline">America's drinks trade</div>
    <div class="masthead-meta">
      <span>News</span>
      <span>Analysis</span>
      <span>Marketplace</span>
    </div>
  </div>
</header>
"""
    return """
<header class="masthead compact">
  <div class="container">
    <a href="/" style="text-decoration:none; color:inherit;">
      <div class="wordmark">PACKAGE STORE<span class="stop">.</span></div>
    </a>
  </div>
</header>
"""


def nav_pillars():
    return """
<nav class="pillars">
  <div class="container">
    <a href="/pillars/industry-news/">Industry News</a>
    <a href="/pillars/texas-beat/">Texas Beat</a>
    <a href="/pillars/regulation-policy/">Regulation</a>
    <a href="/pillars/new-releases/">New Releases</a>
    <a href="/pillars/culture-lifestyle/">Culture</a>
    <a href="/pillars/data-trends/">Data &amp; Trends</a>
    <a href="/marketplace/">Marketplace</a>
  </div>
</nav>
"""


def footer():
    return """
<footer class="site-footer">
  <div class="container">
    <div class="footer-grid">
      <div>
        <div class="footer-wordmark">PACKAGE STORE<span class="stop">.</span></div>
        <p class="footer-blurb">Daily news, analysis, and the marketplace for America's drinks trade. Independent. Trade-first. Texas-anchored.</p>
      </div>
      <div>
        <h4>Sections</h4>
        <ul>
          <li><a href="/pillars/industry-news/">Industry News</a></li>
          <li><a href="/pillars/texas-beat/">Texas Beat</a></li>
          <li><a href="/pillars/regulation-policy/">Regulation</a></li>
          <li><a href="/pillars/new-releases/">New Releases</a></li>
          <li><a href="/pillars/culture-lifestyle/">Culture</a></li>
          <li><a href="/pillars/data-trends/">Data &amp; Trends</a></li>
        </ul>
      </div>
      <div>
        <h4>Marketplace</h4>
        <ul>
          <li><a href="/marketplace/">Browse listings</a></li>
          <li><a href="/marketplace/#list">List your store</a></li>
          <li><a href="/marketplace/#buyer">Buyer registration</a></li>
        </ul>
      </div>
      <div>
        <h4>About</h4>
        <ul>
          <li><a href="/about/">About us</a></li>
          <li><a href="/advertise/">Advertise</a></li>
          <li><a href="/newsletter/">Newsletter</a></li>
          <li><a href="/contact/">Contact</a></li>
          <li><a href="/privacy/">Privacy</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-meta">
      <span>© 2026 Package Store. All rights reserved.</span>
      <span>Built in Texas · Read everywhere.</span>
    </div>
  </div>
</footer>
</body>
</html>"""


# =====================
# PAGE BUILDERS
# =====================

def article_path(item):
    return f"/{item['pillar']}/{item['slug']}/"


def build_article_stub(item, out_dir: Path):
    """Per-item landing page: headline, dek, source attribution, read-at-source link."""
    title = item["title"]
    description = item["description"] or f"From {item['source']}: {title}"
    pillar = item["pillar"]
    pub = item.get("published_dt")
    date_display = pub.strftime("%B %-d, %Y") if pub else ""

    path = article_path(item)
    canonical = f"https://packagestoretx.com{path}"

    body = f"""
<article class="prose">
  <div class="prose-byline" style="margin-top: 32px;">
    <span style="color: var(--bourbon); font-weight: 700;">{html.escape(pillar.replace("-", " ").title())}</span><br>
    Source: {html.escape(item['source'])} · {date_display}
  </div>
  <h1 style="font-family: 'Fraunces', serif; font-weight: 900; font-size: clamp(32px, 5vw, 52px); letter-spacing: -0.025em; line-height: 1.08; margin: 24px 0;">{html.escape(title)}</h1>
  <p class="lede">{html.escape(description)}</p>
  <p style="margin-top: 40px;">
    <a href="{html.escape(item['link'])}" target="_blank" rel="noopener" class="btn btn-primary" style="text-decoration: none;">Read the full story at {html.escape(item['source'])} →</a>
  </p>
  <p style="font-size: 13px; color: var(--mute); margin-top: 40px; padding-top: 24px; border-top: 1px solid var(--line);">
    This is an aggregated headline. Full reporting and analysis lives at the source. Package Store credits and links the original publication on every aggregated story. See our <a href="/about/">editorial standards</a> for how we handle sourcing.
  </p>
</article>
"""

    page = base_head(f"{title} · Package Store.", description, canonical) + topbar() + masthead() + nav_pillars() + body + footer()

    out = out_dir / path.strip("/") / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)


def build_pillar(pillar_id, pillar_meta, items, cfg, out_dir: Path):
    rows = ""
    for it in items[:PER_PILLAR_LIMIT]:
        pub = it.get("published_dt")
        date = short_date(pub) if pub else ""
        rows += f"""
        <div class="pillar-row">
          <div class="date">{date}</div>
          <div class="body">
            <div class="item-kicker" style="font-size:10px; letter-spacing:2px; text-transform:uppercase; color:var(--bourbon); font-weight:700; margin-bottom:4px;">{kicker_for(it)}</div>
            <a href="{article_path(it)}"><h3>{html.escape(it['title'])}</h3></a>
            <div class="src">{html.escape(it['source'])}</div>
          </div>
        </div>"""

    body = f"""
<section class="page-hero">
  <div class="container">
    <div class="eyebrow">The desk · {len(items)} stories · Updated {NOW.strftime("%B %-d, %Y")}</div>
    <h1>{pillar_meta['h1']}</h1>
    <p class="lede">{pillar_meta['lede']}</p>
  </div>
</section>

<div class="container" style="padding: 48px 0 80px;">
  <div class="pillar-block">
    <div class="pillar-block-head">
      <h2>Latest</h2>
      <span style="font-size:11px; letter-spacing:3px; text-transform:uppercase; color:var(--mute); font-weight:600;">Refreshed daily</span>
    </div>
    <div class="pillar-rows">
      {rows}
    </div>
  </div>
</div>

<section class="newsletter-band">
  <div class="narrow">
    <div class="eyebrow">Weekly Digest</div>
    <h2>{pillar_meta['name']} in your inbox every Friday.</h2>
    <p>The week's top stories from this desk and the rest of the trade. Five-minute read.</p>
    <form class="newsletter-form" action="https://packagestoretx.com/newsletter/subscribe" method="post">
      <input type="email" name="email" placeholder="Your email" required>
      <button type="submit">Subscribe</button>
    </form>
    <div class="fine">No spam. Unsubscribe anytime.</div>
  </div>
</section>
"""

    page = (
        base_head(
            f"{pillar_meta['name']} · Package Store.",
            pillar_meta["lede"],
            f"https://packagestoretx.com/pillars/{pillar_id}/",
        )
        + topbar()
        + masthead()
        + nav_pillars()
        + body
        + footer()
    )

    out = out_dir / "pillars" / pillar_id / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)


def build_homepage(by_pillar, cfg, out_dir: Path):
    industry = by_pillar.get("industry-news", [])
    hero = industry[0] if industry else None
    other_industry = industry[1:7]
    breaking = industry[:3]

    breaking_html = " ".join(
        f'<a href="{article_path(it)}">{html.escape(it["title"][:80])}</a>'
        for it in breaking
    )

    sidebar_items = []
    for p in ["texas-beat", "regulation-policy", "data-trends", "industry-news"]:
        if by_pillar.get(p):
            sidebar_items.append((p, by_pillar[p][0]))
        if len(sidebar_items) >= 4:
            break

    sidebar_html = ""
    for p_id, it in sidebar_items:
        pub = it.get("published_dt")
        sidebar_html += f"""
          <li>
            <div class="item-kicker">{cfg['pillars'][p_id]['name']}</div>
            <a href="{article_path(it)}"><div class="item-title">{html.escape(it['title'])}</div></a>
            <div class="item-meta">{html.escape(it['source'])} · {short_date(pub)}</div>
          </li>"""

    feed_grid = ""
    feed_items = []
    for p in ["industry-news", "new-releases", "culture-lifestyle", "texas-beat", "regulation-policy", "data-trends"]:
        if by_pillar.get(p):
            feed_items.append(by_pillar[p][0])
    seen = set()
    feed_items_uniq = []
    for it in feed_items:
        if it["slug"] not in seen:
            feed_items_uniq.append(it)
            seen.add(it["slug"])
        if len(feed_items_uniq) >= 6:
            break
    if hero:
        feed_items_uniq = [it for it in feed_items_uniq if it["slug"] != hero["slug"]]

    for it in feed_items_uniq[:6]:
        pub = it.get("published_dt")
        feed_grid += f"""
    <article class="story-card">
      <div class="kicker">{cfg['pillars'][it['pillar']]['name']}</div>
      <a href="{article_path(it)}"><h3>{html.escape(it['title'])}</h3></a>
      <p class="dek">{html.escape(it['description'][:140])}</p>
      <div class="meta">{html.escape(it['source'])} · {short_date(pub)}</div>
    </article>"""

    pillar_blocks_html = ""
    pillar_pairs = [("texas-beat", "regulation-policy"), ("data-trends", "culture-lifestyle")]
    for left_id, right_id in pillar_pairs:
        block_inner = ""
        for pid in (left_id, right_id):
            pmeta = cfg["pillars"][pid]
            items = by_pillar.get(pid, [])[:3]
            rows = ""
            for it in items:
                pub = it.get("published_dt")
                rows += f"""
        <div class="pillar-row">
          <div class="date">{short_date(pub)}</div>
          <div class="body">
            <a href="{article_path(it)}"><h3>{html.escape(it['title'])}</h3></a>
            <div class="src">{html.escape(it['source'])}</div>
          </div>
        </div>"""
            block_inner += f"""
    <div class="pillar-block">
      <div class="pillar-block-head">
        <h2>{pmeta['name']}</h2>
        <a href="/pillars/{pid}/">All {pmeta['name'].split()[0].lower()} →</a>
      </div>
      <div class="pillar-rows">
        {rows}
      </div>
    </div>"""
        pillar_blocks_html += f"""
  <div class="story-grid two">
{block_inner}
  </div>"""

    hero_html = ""
    if hero:
        pub = hero.get("published_dt")
        hero_html = f"""
      <article class="hero-lead">
        <div class="kicker">{cfg['pillars'][hero['pillar']]['name']}</div>
        <h1><a href="{article_path(hero)}">{html.escape(hero['title'])}</a></h1>
        <p class="dek">{html.escape(hero['description'])}</p>
        <div class="byline">Via {html.escape(hero['source'])} · {short_date(pub)}</div>
      </article>"""

    body = f"""
<div class="breaking-bar">
  <div class="container">
    <span class="tag">Breaking</span>
    <div class="ticker">
      {breaking_html}
    </div>
  </div>
</div>

<section class="hero">
  <div class="container">
    <div class="hero-grid">
      {hero_html}
      <aside class="hero-aside">
        <h3>Today's Headlines</h3>
        <ul>
          {sidebar_html}
        </ul>
      </aside>
    </div>
  </div>
</section>

<section class="container">
  <div class="section-head">
    <h2>The desk this week</h2>
    <a href="/pillars/industry-news/">All industry news →</a>
  </div>

  <div class="story-grid">
    {feed_grid}
  </div>
</section>

<section class="marketplace-band">
  <div class="container">
    <div class="marketplace-band-grid">
      <div>
        <div class="eyebrow">The Marketplace · Coming soon</div>
        <h2>Buying or selling a Texas package store?</h2>
        <p>The only marketplace built inside an editorial brand. Listings written like journalism, with the numbers up front. Verified owners. Real revenue. Real margins. Real buyer flow.</p>
        <div class="actions">
          <a href="/marketplace/" class="btn btn-primary">See the marketplace</a>
          <a href="/marketplace/#list" class="btn btn-ghost">List your store</a>
        </div>
      </div>
      <div class="listing-mock">
        <span class="tag">Texas · Off-Premise</span>
        <h3>Established Package Store, Harris County</h3>
        <div class="sub">TABC Permit P · 22 years operating · Owner retiring</div>
        <div class="stats">
          <div class="stat"><div class="stat-label">Annual Rev</div><div class="stat-value">$2.4M</div></div>
          <div class="stat"><div class="stat-label">Sq Ft</div><div class="stat-value">4,800</div></div>
          <div class="stat"><div class="stat-label">Margin</div><div class="stat-value">31%</div></div>
        </div>
        <div class="price">$1.85M</div>
      </div>
    </div>
  </div>
</section>

<section class="container">
  {pillar_blocks_html}
</section>

<section class="newsletter-band">
  <div class="narrow">
    <div class="eyebrow">Weekly Digest · Friday</div>
    <h2>The week, in five minutes.</h2>
    <p>The top stories from the U.S. drinks trade, with the analysis our desk thinks is worth your time. Delivered every Friday at 11 AM ET. Free forever.</p>
    <form class="newsletter-form" action="https://packagestoretx.com/newsletter/subscribe" method="post">
      <input type="email" name="email" placeholder="Your email" required>
      <button type="submit">Subscribe</button>
    </form>
    <div class="fine">No spam. Unsubscribe anytime.</div>
  </div>
</section>
"""

    page = (
        base_head("Package Store. America's drinks trade.",
                  "Daily news, analysis, and the marketplace for America's drinks business.",
                  "https://packagestoretx.com/")
        + topbar(active_home=True)
        + masthead(big=True)
        + nav_pillars()
        + body
        + footer()
    )
    (out_dir / "index.html").write_text(page)


def build_sitemap(items, cfg, out_dir: Path):
    urls = [
        '<url><loc>https://packagestoretx.com/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>',
        '<url><loc>https://packagestoretx.com/about/</loc><changefreq>monthly</changefreq><priority>0.6</priority></url>',
        '<url><loc>https://packagestoretx.com/advertise/</loc><changefreq>monthly</changefreq><priority>0.7</priority></url>',
        '<url><loc>https://packagestoretx.com/contact/</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>',
        '<url><loc>https://packagestoretx.com/newsletter/</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>',
        '<url><loc>https://packagestoretx.com/marketplace/</loc><changefreq>weekly</changefreq><priority>0.9</priority></url>',
        '<url><loc>https://packagestoretx.com/privacy/</loc><changefreq>yearly</changefreq><priority>0.3</priority></url>',
    ]
    for p in cfg["pillars"]:
        urls.append(f'<url><loc>https://packagestoretx.com/pillars/{p}/</loc><changefreq>daily</changefreq><priority>0.9</priority></url>')
    for it in items:
        urls.append(f'<url><loc>https://packagestoretx.com{article_path(it)}</loc><changefreq>weekly</changefreq><priority>0.6</priority></url>')

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n  ' + "\n  ".join(urls) + "\n</urlset>\n"
    (out_dir / "sitemap.xml").write_text(xml)


def copy_static(out_dir: Path):
    """Copy non-dynamic files from the existing site into _build/."""
    keep = [
        "assets", "404.html", "robots.txt", "CNAME", ".nojekyll",
        "favicon.ico", "about", "advertise", "contact", "marketplace",
        "newsletter", "privacy", "article",
    ]
    for name in keep:
        src = ROOT / name
        if not src.exists():
            continue
        dst = out_dir / name
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)



def load_archive():
    if not ARCHIVE.exists():
        return []
    try:
        raw = json.loads(ARCHIVE.read_text())
    except Exception:
        return []
    out = []
    for it in raw:
        dt = parse_date(it.get("published") or "")
        if not dt:
            continue
        it["published_dt"] = dt
        out.append(it)
    return out


def save_archive(items):
    serial = []
    for it in items:
        pub = it.get("published_dt")
        serial.append({
            "title": it.get("title", ""),
            "link": it.get("link", ""),
            "description": it.get("description", ""),
            "published": pub.isoformat() if pub else it.get("published"),
            "source": it.get("source", ""),
            "source_id": it.get("source_id", ""),
            "pillar": it.get("pillar", "industry-news"),
            "slug": it.get("slug", ""),
        })
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVE.write_text(json.dumps(serial, ensure_ascii=False))


def merge_archive(fresh):
    """Merge freshly fetched items with the persisted archive so content compounds across runs."""
    archive = load_archive()
    cutoff = NOW - timedelta(days=MAX_AGE_DAYS)
    by_slug = {}
    for it in archive + fresh:
        dt = it.get("published_dt")
        if not dt or dt < cutoff:
            continue
        slug = it.get("slug") or slugify(it.get("title", ""))
        if not slug:
            continue
        it["slug"] = slug
        by_slug[slug] = it
    merged = list(by_slug.values())
    merged.sort(key=lambda x: x["published_dt"], reverse=True)
    save_archive(merged)
    print(f"=== Archive merged: {len(fresh)} fresh + {len(archive)} archived -> {len(merged)} total ===")
    return merged


def main():
    cfg = json.loads(DATA.read_text())
    if BUILD.exists():
        shutil.rmtree(BUILD, ignore_errors=True)
    BUILD.mkdir(parents=True, exist_ok=True)

    items = fetch_all(cfg)
    items = merge_archive(items)
    if not items:
        print("WARN: no items (fresh + archive empty). Aborting (no destructive build).", file=sys.stderr)
        sys.exit(1)

    # Bucket items by pillar
    by_pillar = {}
    for it in items:
        by_pillar.setdefault(it["pillar"], []).append(it)
    for p in by_pillar:
        by_pillar[p] = by_pillar[p][:PER_PILLAR_LIMIT]

    print(f"=== Building {len(items)} stories across {len(by_pillar)} pillars ===")
    for p, lst in by_pillar.items():
        print(f"  {p}: {len(lst)}")

    # Copy static chrome
    copy_static(BUILD)

    # Build per-item stub pages
    for it in items:
        build_article_stub(it, BUILD)

    # Build pillar pages
    for p_id, p_meta in cfg["pillars"].items():
        build_pillar(p_id, p_meta, by_pillar.get(p_id, []), cfg, BUILD)

    # Build homepage
    build_homepage(by_pillar, cfg, BUILD)

    # Build sitemap
    build_sitemap(items, cfg, BUILD)

    print(f"=== Done. _build/ has {sum(1 for _ in BUILD.rglob('*') if _.is_file())} files ===")


if __name__ == "__main__":
    main()
