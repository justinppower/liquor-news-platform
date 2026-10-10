#!/usr/bin/env python3
"""Compose the packagestoretx.com site.

Root (/)      -> Package Store TX brokerage site, from brokerage/
/news/        -> the RSS news site produced by aggregate.py

Run after aggregate.py has filled the build dir. Works in place:
    python scripts/compose_site.py _build
The news pages are written with root-absolute links (/pillars/..., /assets/...),
so every root-absolute URL in them is rewritten to live under /news/.
Old news links to pages that never existed (/about/, /marketplace/ ...) are
pointed at the matching brokerage page instead of a 404.
"""
import re
import sys
import shutil
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROKERAGE = ROOT / "brokerage"
DOMAIN = "https://packagestoretx.com"
PREFIX = "/news"

# news links that pointed at pages with no file behind them -> brokerage pages
REMAP = {
    "/about/": "/about.html",
    "/contact/": "/contact.html",
    "/privacy/": "/privacy.html",
    "/advertise/": "/contact.html",
    "/newsletter/": "/contact.html",
    "/marketplace/#list": "/value.html",
    "/marketplace/#buyer": "/buy.html",
    "/marketplace/": "/buy.html",
}

BACKBAR = (
    '<div style="background:#13243b;color:#fff;font:600 14px/1.4 \'Public Sans\',Arial,sans-serif;'
    'padding:10px 16px;text-align:center">'
    '<a href="/" style="color:#f0b35e;text-decoration:none">&larr; Package Store TX</a>'
    ' &middot; <a href="/value.html" style="color:#fff">What&#39;s my store worth?</a>'
    ' &middot; <a href="/terms.html" style="color:#cfd9e4">Terms</a>'
    ' &middot; <a href="/disclaimers.html" style="color:#cfd9e4">Disclaimers</a></div>'
)


def rewrite_url(url: str) -> str:
    if url in REMAP:
        return REMAP[url]
    if url.startswith("//") or not url.startswith("/"):
        return url
    if url == PREFIX or url.startswith(PREFIX + "/"):
        return url
    return PREFIX + url


ATTR = re.compile(r'(\b(?:href|src|action|content)=")(/[^"]*)(")')
CSSURL = re.compile(r'(url\(\s*["\']?)(/[^)"\']*)')


def rewrite_html(text: str) -> str:
    text = ATTR.sub(lambda m: m.group(1) + rewrite_url(m.group(2)) + m.group(3), text)
    text = CSSURL.sub(lambda m: m.group(1) + rewrite_url(m.group(2)), text)
    # absolute URLs on our own domain (canonical, og:url, sitemap)
    text = re.sub(
        re.escape(DOMAIN) + r'(/[^"<\s]*)?',
        lambda m: DOMAIN + rewrite_url(m.group(1) or "/"),
        text,
    )
    return add_chrome(text)


def _chrome():
    """Main-site header, footer and CSS for news pages, written by the brokerage build."""
    try:
        head = (BROKERAGE / "news-chrome-head.html").read_text(encoding="utf-8") if (BROKERAGE / "news-chrome-head.html").exists() else CSSLINK
        return ((BROKERAGE / "news-chrome-header.html").read_text(encoding="utf-8"),
                (BROKERAGE / "news-chrome-footer.html").read_text(encoding="utf-8"), head)
    except FileNotFoundError:
        return None


HS, HE = "<!--pstx-head-->", "<!--/pstx-head-->"
TS, TE = "<!--pstx-tags-->", "<!--/pstx-tags-->"
FS, FE = "<!--pstx-foot-->", "<!--/pstx-foot-->"
CSSLINK = '<link rel="stylesheet" href="/news-chrome.css">'


def add_chrome(text: str) -> str:
    """Idempotent: strips any earlier back bar or chrome, then injects the current one."""
    text = text.replace(BACKBAR, "")
    text = re.sub(re.escape(HS) + r".*?" + re.escape(HE), "", text, flags=re.S)
    text = re.sub(re.escape(FS) + r".*?" + re.escape(FE), "", text, flags=re.S)
    text = re.sub(re.escape(TS) + r".*?" + re.escape(TE), "", text, flags=re.S)
    text = text.replace(CSSLINK, "")
    ch = _chrome()
    if not ch or "<body" not in text:
        if "<body" in text:
            text = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + BACKBAR, text, count=1)
        return text
    head, foot, tags = ch
    text = text.replace("</head>", TS + tags + TE + "</head>", 1)
    text = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + HS + head + HE, text, count=1)
    i = text.rfind("</body>")
    if i != -1:
        text = text[:i] + FS + foot + FE + text[i:]
    return text


def rewrite_css(text: str) -> str:
    return CSSURL.sub(lambda m: m.group(1) + rewrite_url(m.group(2)), text)


def clean_news_sitemap(path: Path):
    """Keep only /news/ URLs (old remapped links pointed at main-site pages) and drop duplicates."""
    if not path.exists():
        return
    t = path.read_text(encoding="utf-8")
    seen = set()

    def keep(m):
        loc = re.search(r"<loc>([^<]+)</loc>", m.group(0))
        u = loc.group(1).strip() if loc else ""
        if not u.startswith(DOMAIN + PREFIX + "/") or u in seen:
            return ""
        seen.add(u)
        return m.group(0)

    t = re.sub(r"<url>.*?</url>\s*", keep, t, flags=re.S)
    path.write_text(t, encoding="utf-8")


def redirect_stub(target: str) -> str:
    """Instant redirect page Google treats as a permanent move (meta refresh 0 plus canonical)."""
    url = DOMAIN + target
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<title>Moved</title><link rel="canonical" href="{url}">'
        f'<meta http-equiv="refresh" content="0; url={target}">'
        f'<script>location.replace({target!r} + location.search + location.hash)</script>'
        f'</head><body><p>This page has moved to <a href="{target}">{url}</a>.</p></body></html>'
    )


def write_legacy_redirects(build: Path) -> int:
    """The news site used to live at the root. Every old root URL now redirects to its /news/ home."""
    news = build / PREFIX.strip("/")
    n = 0
    for f in news.rglob("index.html"):
        rel = f.relative_to(news)
        if rel == Path("index.html"):
            continue
        dst = build / rel
        if dst.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        target = PREFIX + "/" + rel.parent.as_posix() + "/"
        dst.write_text(redirect_stub(target), encoding="utf-8")
        n += 1
    for old, new in REMAP.items():
        if "#" in old or not old.endswith("/"):
            continue
        dst = build / old.strip("/") / "index.html"
        if dst.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(redirect_stub(new), encoding="utf-8")
        n += 1
    return n


REGISTRY = ROOT / "data" / "published_urls.json"


def expired_article_redirects(build: Path) -> int:
    """Articles drop out of the rolling feed after MAX_AGE_DAYS. Keep every URL ever published alive
    by redirecting expired ones (at /news/... and the old root path) to their section page."""
    news = build / PREFIX.strip("/")
    pillars_dir = news / "pillars"
    current = set()
    for f in news.glob("*/*/index.html"):
        rel = f.parent.relative_to(news).as_posix()
        if not rel.startswith("pillars/"):
            current.add(rel)
    known = set(json.loads(REGISTRY.read_text())) if REGISTRY.exists() else set()
    known |= current
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(sorted(known), indent=0) + "\n")
    n = 0
    for rel in sorted(known - current):
        pillar = rel.split("/")[0]
        target = f"{PREFIX}/pillars/{pillar}/" if (pillars_dir / pillar).exists() else f"{PREFIX}/"
        for dst in (news / rel / "index.html", build / rel / "index.html"):
            if dst.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(redirect_stub(target), encoding="utf-8")
            n += 1
    return n


def compose(build: Path):
    if not BROKERAGE.exists():
        sys.exit(f"brokerage/ not found at {BROKERAGE}")
    if (build / ".composed").exists():
        print("already composed, skipping")
        return
    tmp = build.parent / (build.name + "_news_tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    build.rename(tmp)
    build.mkdir(parents=True)
    news = build / "news"
    shutil.copytree(tmp, news)
    shutil.rmtree(tmp)

    n = 0
    for f in news.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix == ".html":
            f.write_text(rewrite_html(f.read_text(encoding="utf-8")), encoding="utf-8")
            n += 1
            continue
        if f.suffix == ".xml":
            t = f.read_text(encoding="utf-8")
            t = ATTR.sub(lambda m: m.group(1) + rewrite_url(m.group(2)) + m.group(3), t)
            t = re.sub(re.escape(DOMAIN) + r'(/[^"<\s]*)?', lambda m: DOMAIN + rewrite_url(m.group(1) or "/"), t)
            f.write_text(t, encoding="utf-8")
            n += 1
        elif f.suffix == ".css":
            f.write_text(rewrite_css(f.read_text(encoding="utf-8")), encoding="utf-8")
            n += 1
    # the news sitemap lives at /news/sitemap.xml; root sitemap indexes both
    for item in BROKERAGE.iterdir():
        dst = build / item.name
        if item.is_dir():
            shutil.copytree(item, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dst)
    clean_news_sitemap(news / "sitemap.xml")
    pages = sorted(p.name for p in BROKERAGE.glob("*.html") if p.name != "404.html" and not p.name.startswith("news-chrome"))
    today = __import__("datetime").date.today().isoformat()
    urls = "".join(
        f"<url><loc>{DOMAIN}/{'' if p == 'index.html' else p}</loc><lastmod>{today}</lastmod></url>" for p in pages
    )
    (build / "sitemap-main.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n'
    )
    (build / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<sitemap><loc>{DOMAIN}/sitemap-main.xml</loc></sitemap>"
        f"<sitemap><loc>{DOMAIN}/news/sitemap.xml</loc></sitemap>"
        "</sitemapindex>\n"
    )
    (build / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /news-chrome-\nSitemap: {DOMAIN}/sitemap.xml\n")
    print(f"legacy redirects: {write_legacy_redirects(build)}")
    print(f"expired article redirects: {expired_article_redirects(build)}")
    (build / ".nojekyll").write_text("")
    (build / ".composed").write_text("")
    print(f"composed: brokerage at /, {n} news files rewritten under {PREFIX}/")


if __name__ == "__main__":
    compose(Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "_build").resolve())
