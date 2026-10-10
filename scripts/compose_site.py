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
        return ((BROKERAGE / "news-chrome-header.html").read_text(encoding="utf-8"),
                (BROKERAGE / "news-chrome-footer.html").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


HS, HE = "<!--pstx-head-->", "<!--/pstx-head-->"
FS, FE = "<!--pstx-foot-->", "<!--/pstx-foot-->"
CSSLINK = '<link rel="stylesheet" href="/news-chrome.css">'


def add_chrome(text: str) -> str:
    """Idempotent: strips any earlier back bar or chrome, then injects the current one."""
    text = text.replace(BACKBAR, "")
    text = re.sub(re.escape(HS) + r".*?" + re.escape(HE), "", text, flags=re.S)
    text = re.sub(re.escape(FS) + r".*?" + re.escape(FE), "", text, flags=re.S)
    text = text.replace(CSSLINK, "")
    ch = _chrome()
    if not ch or "<body" not in text:
        if "<body" in text:
            text = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + BACKBAR, text, count=1)
        return text
    head, foot = ch
    text = text.replace("</head>", CSSLINK + "</head>", 1)
    text = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + HS + head + HE, text, count=1)
    i = text.rfind("</body>")
    if i != -1:
        text = text[:i] + FS + foot + FE + text[i:]
    return text


def rewrite_css(text: str) -> str:
    return CSSURL.sub(lambda m: m.group(1) + rewrite_url(m.group(2)), text)


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
    pages = sorted(p.name for p in BROKERAGE.glob("*.html") if p.name != "404.html" and not p.name.startswith("news-chrome"))
    urls = "".join(
        f"<url><loc>{DOMAIN}/{'' if p == 'index.html' else p}</loc></url>" for p in pages
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
    (build / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n")
    (build / ".nojekyll").write_text("")
    (build / ".composed").write_text("")
    print(f"composed: brokerage at /, {n} news files rewritten under {PREFIX}/")


if __name__ == "__main__":
    compose(Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "_build").resolve())
