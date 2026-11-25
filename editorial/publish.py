#!/usr/bin/env python3
"""Prepare one weekday's approved articles in a separate site checkout."""

import argparse
from collections import defaultdict
from datetime import date, datetime
from html import escape, unescape
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo


EDITORIAL = Path(__file__).resolve().parent
BASE = "https://rushlo.com/"
LIMIT = 2
TOPICS = {
    "channels": "Distributor Channels",
    "sales-ai": "AI for Sales Teams",
    "business-ai": "Everyday AI for Small Business",
    "leadership": "Sales Leadership & Accounts",
    "process": "Pricing & Sales Operations",
}
IMAGE_ALTS = {
    "warehouse": "Shelves and conveyors in a distribution warehouse",
    "channel": "A forklift operator handles a pallet at a delivery truck",
    "meeting": "Colleagues review notes at a worktable",
    "territories": "Colored pins mark locations on a territory map",
    "process": "Conveyors and storage bins at a distribution facility",
}
SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
MARKER = re.compile(r"<!-- jbr-editorial slug=(" + SLUG + r") published=(\d{4}-\d{2}-\d{2}) -->")
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def read_text(path):
    return path.read_text(encoding="utf-8")


def iso_date(value):
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError(f"Expected a YYYY-MM-DD date, got {value!r}")
    return parsed


def load_queue():
    rows = json.loads(read_text(EDITORIAL / "queue.json"))
    if not isinstance(rows, list):
        raise ValueError("queue.json must contain a list")
    seen = set()
    for row in rows:
        for field in ("date", "slug", "title", "description", "topic", "image", "label"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"Queue item has an empty or missing {field}")
        slug = row["slug"]
        if not re.fullmatch(SLUG, slug) or slug in seen:
            raise ValueError(f"Invalid or duplicate article slug: {slug}")
        if row["topic"] not in TOPICS or row["image"] not in IMAGE_ALTS:
            raise ValueError(f"Unknown Insights topic or image for {slug}")
        iso_date(row["date"])
        seen.add(slug)
    return sorted(rows, key=lambda row: row["date"])  # Preserve queue order for a single date.


def published_dates(site):
    dates = {}
    for page in site.glob("*.html"):
        match = MARKER.search(read_text(page))
        if match:
            slug, published = match.groups()
            if slug != page.stem:
                raise ValueError(f"Queue marker does not match filename: {page.name}")
            dates[slug] = iso_date(published)
    return dates


def wrap_tables(body):
    """Apply the site's responsive table layout while preserving authored wrappers."""
    wrapped_divs = []

    def replace(match):
        if match["div"] is not None:
            classes = re.search(r"""\sclass\s*=\s*["']([^"']*)["']""", match["div"], re.I)
            wrapped_divs.append(bool(classes and "guide-table" in classes[1].split()))
            return match[0]
        if match["end_div"]:
            if wrapped_divs:
                wrapped_divs.pop()
            return match[0]
        if any(wrapped_divs):
            return match[0]
        table = match["table"]
        widths = []
        for row in re.findall(r"<tr\b[^>]*>(.*?)</tr\s*>", table, re.I | re.S):
            columns = 0
            for cell in re.findall(r"<t[dh]\b[^>]*>", row, re.I):
                span = re.search(r"""\scolspan\s*=\s*["']?(\d+)""", cell, re.I)
                columns += max(1, int(span[1])) if span else 1
            widths.append(columns)
        attributes = 'class="guide-table"'
        if max(widths, default=0) >= 4:
            caption = re.search(r"<caption\b[^>]*>(.*?)</caption\s*>", table, re.I | re.S)
            name = unescape(re.sub(r"<[^>]*>", "", caption[1])).strip() if caption else ""
            label = f"{name} (scrollable table)" if name else "Scrollable article table"
            attributes = f'class="guide-table wide" role="region" aria-label="{escape(label)}" tabindex="0"'
        return f"<div {attributes}>\n{table}\n</div>"

    blocks = r"<div\b(?P<div>[^>]*)>|(?P<end_div></div\s*>)|(?P<table><table\b[^>]*>.*?</table\s*>)"
    return re.sub(blocks, replace, body, flags=re.I | re.S)


def article_page(site, template, row, today):
    slug, image = row["slug"], row["image"]
    body = read_text(EDITORIAL / "ready" / f"{slug}.html").strip()
    if not body or re.search(r"</?(?:html|head|body|article|main|h1)\b", body, re.I):
        raise ValueError(f"{slug} needs an article body fragment")
    body = wrap_tables(body)
    for size in (800, 1600):
        if not (site / f"assets/images/{image}-{size}.webp").is_file():
            raise ValueError(f"Missing {image}-{size}.webp for {slug}")
    # Keep the site's analytics, navigation, author note and footer. Build every
    # article-specific field separately so the shell cannot leak another story.
    start = template[:template.index("<title>")]
    stylesheet = re.search(r'<link\b[^>]*href="assets/site\.css(?:\?[^"]*)?"[^>]*>', template)
    if not stylesheet:
        raise ValueError("Article shell is missing the site's stylesheet")
    navigation = template[template.index('<script defer src="assets/site.js'):template.index('<main id="main">')]
    footer = template[template.index('<div class="author-note">'):]
    graph_start = template.index('<script type="application/ld+json">') + len('<script type="application/ld+json">')
    graph = json.loads(template[graph_start:template.index("</script>", graph_start)])["@graph"]
    article = next(node for node in graph if node["@type"] == "Article")
    crumb = next(node for node in graph if node["@type"] == "BreadcrumbList")
    url = f"{BASE}{slug}.html"
    image_url = f"{BASE}assets/images/{image}-1600.webp"
    topic = TOPICS[row["topic"]]
    published = today.isoformat()
    article.update(headline=row["title"], description=row["description"], image=[image_url],
                   datePublished=published, dateModified=published, articleSection=topic,
                   mainEntityOfPage={"@type": "WebPage", "@id": url})
    crumb["itemListElement"][-1].update(name=row["title"], item=url)
    schema = json.dumps({"@context": "https://schema.org", "@graph": [article, crumb]},
                        ensure_ascii=False, indent=2).replace("<", "\\u003c")
    title, description = escape(row["title"]), escape(row["description"])
    alt, topic = escape(IMAGE_ALTS[image]), escape(topic)
    display_date = f"{today:%B} {today.day}, {today.year}"
    return f"""{start}<title>{title} | JBR</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="JBR">
<meta property="og:title" content="{title} | JBR">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{image_url}">
<meta property="og:image:alt" content="{alt}">
<meta name="twitter:card" content="summary_large_image">
{stylesheet[0]}
<link rel="stylesheet" href="assets/insight-guides.css">
<script type="application/ld+json">
{schema}
</script>
{navigation}<main id="main">
<!-- jbr-editorial slug={slug} published={published} -->
<section class="section white">
<article class="wrap article">
<div class="eyebrow">Insights / {topic}</div>
<h1>{title}</h1>
<div class="article-meta article-byline">By <a href="about.html#josh-rushlo">Josh Rushlo</a> · JBR Insights · {topic} · <time datetime="{published}">{display_date}</time></div>
<figure class="article-figure">
  <img fetchpriority="high" srcset="assets/images/{image}-800.webp 800w, assets/images/{image}-1600.webp 1600w" sizes="(max-width: 936px) calc(100vw - 36px), 900px" src="assets/images/{image}-1600.webp" alt="{alt}" width="1600" height="800" decoding="async">
</figure>
{body}
{footer}"""


def update_insights(index, rows):
    by_topic = defaultdict(list)
    for row in rows:
        filename = row["slug"] + ".html"
        if f'href="{filename}"' not in index:
            by_topic[row["topic"]].append(
                f'<a class="insight-index-item" href="{filename}"><small>{escape(row["label"])}</small>'
                f'<h3>{escape(row["title"])}</h3><p>{escape(row["description"])}</p></a>'
            )
    for topic, cards in by_topic.items():
        section = re.search(rf'<section\b[^>]*\bid="{topic}"[^>]*>.*?</section>', index, re.S)
        if not section:
            raise ValueError(f"Missing Insights section: {topic}")
        marker = '<div class="insight-index-list">'
        if section[0].count(marker) != 1:
            raise ValueError(f"Missing or ambiguous Insights card list: {topic}")
        position = section.start() + section[0].index(marker) + len(marker)
        index = index[:position] + "\n" + "\n".join(cards) + index[position:]
    return index


def update_sitemap(source, rows, today):
    root = ET.fromstring(source)
    ns = "{" + SITEMAP_NS + "}"
    if root.tag != ns + "urlset":
        raise ValueError("Unexpected sitemap root")
    ET.register_namespace("", SITEMAP_NS)
    urls = root.findall(ns + "url")
    by_loc = {node.findtext(ns + "loc"): node for node in urls}
    if None in by_loc or len(by_loc) != len(urls):
        raise ValueError("Sitemap contains missing or duplicate URLs")
    for path in ["insights.html"] + [row["slug"] + ".html" for row in rows]:
        address = BASE + path
        node = by_loc.get(address)
        if node is None:
            node = ET.SubElement(root, ns + "url")
            node.tail = "\n"
            ET.SubElement(node, ns + "loc").text = address
        lastmod = node.find(ns + "lastmod")
        if lastmod is None:
            lastmod = ET.SubElement(node, ns + "lastmod")
        lastmod.text = today.isoformat()
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def prepare(site, today, dry_run):
    if site == EDITORIAL.parent or not (site / "CNAME").is_file() or read_text(site / "CNAME").strip() != "rushlo.com":
        raise ValueError("--site must point to a separate checkout of rushlo.com")
    result = {"date": today.isoformat(), "dry_run": dry_run, "articles": [], "changed_paths": []}
    if today.weekday() >= 5:
        return dict(result, status="weekend")
    rows = load_queue()
    published = published_dates(site)
    available = max(0, LIMIT - sum(value == today for value in published.values()))
    due = [row for row in rows if row["date"] <= today.isoformat() and row["slug"] not in published]
    selected = due[:available]
    if not selected:
        return dict(result, status="daily_limit" if due else "nothing_due")
    pages = {}
    template = read_text(site / "how-to-fix-the-sales-to-operations-handoff.html")
    for row in selected:
        name = row["slug"] + ".html"
        if (site / name).exists():
            raise ValueError(f"Refusing to replace an existing page without matching queue marker: {name}")
        pages[name] = article_page(site, template, row, today)
    updates = {"insights.html": update_insights(read_text(site / "insights.html"), selected),
               "sitemap.xml": update_sitemap(read_text(site / "sitemap.xml"), selected, today)}
    changes = dict(updates, **pages)
    if not dry_run:
        # The caller publishes these files with a single fast-forward commit.
        # Install the two indexes before the new pages (the completion markers)
        # so a locally interrupted preparation can safely be replayed.
        with TemporaryDirectory(dir=site) as stage_name:
            stage = Path(stage_name)
            for name, contents in changes.items():
                (stage / name).write_text(contents, encoding="utf-8")
            for name in updates:
                (stage / name).replace(site / name)
            for name in pages:
                (site / name).hardlink_to(stage / name)
    return dict(result, status="prepared", articles=[row["slug"] for row in selected],
                changed_paths=list(changes))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True, type=Path, help="Separate checkout of current production main")
    parser.add_argument("--date", type=iso_date, help="Override the Chicago date for an isolated rehearsal")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the release without writing files")
    args = parser.parse_args()
    today = args.date or datetime.now(ZoneInfo("America/Chicago")).date()
    try:
        report = prepare(args.site.resolve(), today, args.dry_run)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration, ET.ParseError) as error:
        print(json.dumps({"status": "error", "date": today.isoformat(), "error": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
