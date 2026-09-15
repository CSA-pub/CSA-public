#!/usr/bin/env python3
"""Generate the /catalysts and /sponsors directory hubs.

Both content directories shipped with no index page and no inbound links
from anywhere on the site, so all 158 pages were orphaned: present in the
sitemap, but unreachable by following links from the homepage. Google had
crawled none of them.

This builds one directory page per content type and writes the homepage
link block between its BEGIN/END markers.

Each entry's label is taken verbatim from the target page's own <h1> and
<title>, so the hubs restate what those pages already say and assert no
new relationship. In particular the hubs deliberately do NOT link a
catalyst to its sponsor: that asset-to-ticker linkage is precision-first
(a wrong link is worse than a missed one) and a directory page is not the
place to introduce one.

Run from the repo root:  python scripts/generate_hubs.py
"""

import html as htmllib
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seo_common import fit_title

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
SITEMAP = ROOT / "sitemap.xml"
BASE = "https://csa.dataengineered.io"

BEGIN = "<!-- BEGIN:hub-browse -->"
END = "<!-- END:hub-browse -->"

SECTIONS = [
    {
        "slug": "catalysts",
        "h1": "Catalyst directory",
        # title is fit via seo_common.fit_title once the entry count (n) is known --
        # see build_section() -- so it stays <=60 chars instead of the fixed string
        # this used to be ("Catalyst Directory — Every Tracked Clinical-Stage
        # Readout | CSA", 63 chars, over budget).
        "title_options": lambda n: [f"{n} clinical-stage catalysts", "catalyst directory"],
        "desc": ("Every forward clinical and regulatory catalyst tracked by CSA, each linked "
                 "to its own source-linked record. Not investment advice."),
        "lede": ("One page per tracked forward catalyst. Each record carries the trial phase, "
                 "event type, expected date, date confidence, NCT id and the source it was "
                 "derived from."),
        "label": "tracked catalysts",
    },
    {
        "slug": "sponsors",
        "h1": "Sponsor directory",
        "title_options": lambda n: [f"{n} sponsors", "directory"],
        "desc": ("Every listed sponsor tracked by CSA, each with its forward clinical-stage "
                 "catalysts and pipeline. Not investment advice."),
        "lede": ("One page per listed sponsor, with the forward catalysts tracked against it. "
                 "Every asset-to-ticker linkage is verified against the trial record before "
                 "it is published."),
        "label": "listed sponsors",
    },
]

STYLE = """*{box-sizing:border-box;margin:0;padding:0}
:root{--ground:#0B1315;--surface:#101A1C;--ink:#E7EEED;--ink-2:#9BABAA;--ink-3:#758484;
--line:#213032;--accent:#2BB3A8;
--font-sans:'IBM Plex Sans',system-ui,-apple-system,sans-serif;
--font-mono:'IBM Plex Mono',ui-monospace,'SFMono-Regular',monospace}
body{font-family:var(--font-sans);background:var(--ground);color:var(--ink);line-height:1.6;
padding-bottom:64px;-webkit-font-smoothing:antialiased}
.container{max-width:1000px;margin:0 auto;padding:0 24px}
a{color:inherit}
header{border-bottom:1px solid var(--line);background:var(--surface);padding:15px 0;
position:sticky;top:0;z-index:5}
.nav{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.brand{font-weight:700;font-size:1.14rem;text-decoration:none;color:var(--ink);
letter-spacing:-.01em;display:flex;align-items:center}
.brand-tag{font-family:var(--font-mono);font-size:.54rem;text-transform:uppercase;
letter-spacing:.16em;color:var(--ink-3);border-left:1px solid var(--line);
padding-left:11px;margin-left:11px}
.navlinks a{font-family:var(--font-mono);font-size:.66rem;text-transform:uppercase;
letter-spacing:.1em;color:var(--ink-2);text-decoration:none;margin-left:18px}
.navlinks a:hover{color:var(--accent)}
.crumbs{font-family:var(--font-mono);font-size:.63rem;color:var(--ink-3);margin:22px 0 0;
letter-spacing:.04em}
.crumbs a{color:var(--ink-2);text-decoration:none}
.crumbs a:hover{color:var(--accent)}
.eyebrow{font-family:var(--font-mono);font-size:.63rem;letter-spacing:.2em;
text-transform:uppercase;color:var(--accent);font-weight:600}
.hero{padding:34px 0 30px;border-bottom:1px solid var(--line)}
h1{font-size:2.35rem;font-weight:700;letter-spacing:-.022em;margin:12px 0 6px;text-wrap:balance}
.sub{color:var(--ink-2);font-size:1.03rem;max-width:68ch}
.count{font-family:var(--font-mono);font-size:.66rem;text-transform:uppercase;
letter-spacing:.1em;color:var(--ink-3);margin-top:18px}
.dirlist{list-style:none;margin:26px 0 0;padding:0;display:grid;
grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:1px;background:var(--line);
border:1px solid var(--line);border-radius:9px;overflow:hidden}
.dirlist li{background:var(--surface);padding:0}
.dirlist a{display:block;padding:13px 16px;text-decoration:none}
.dirlist a:hover{background:var(--ground)}
.dirlist a:hover .n{color:var(--accent)}
.n{display:block;font-weight:600;font-size:.95rem;letter-spacing:-.005em}
.d{display:block;font-family:var(--font-mono);font-size:.66rem;color:var(--ink-3);
margin-top:3px;letter-spacing:.03em}
.advice{font-family:var(--font-mono);font-size:.64rem;color:var(--ink-3);margin-top:28px;
letter-spacing:.04em;border-top:1px solid var(--line);padding-top:18px}
footer{border-top:1px solid var(--line);margin-top:40px;padding:26px 0;color:var(--ink-3);
font-size:.86rem}
footer a{color:var(--ink-2)}"""

PAGE = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <meta name="description" content="{desc}" />
  <meta name="robots" content="index, follow, max-image-preview:large" />
  <meta name="theme-color" content="#0B1315" />
  <link rel="canonical" href="{base}/{slug}/" />
  <link rel="alternate" hreflang="en" href="{base}/{slug}/" />
  <link rel="alternate" hreflang="x-default" href="{base}/{slug}/" />
  <link rel="icon" href="../favicon.svg" type="image/svg+xml" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{desc}" />
  <meta property="og:url" content="{base}/{slug}/" />
  <meta property="og:type" content="website" />
  <meta property="og:image" content="{base}/og-image.png" />
  <meta name="twitter:card" content="summary_large_image" />
  <script type="application/ld+json">
  {{"@context": "https://schema.org", "@type": "CollectionPage", "name": {jname}, "description": {jdesc}, "url": "{base}/{slug}/", "isPartOf": {{"@type": "WebSite", "name": "CSA", "url": "{base}"}}, "publisher": {{"@type": "Organization", "name": "DataEngineered", "url": "{base}"}}}}
  </script>
  <style>
{style}
  </style>
</head>
<body>
  <header>
    <div class="container nav">
      <a href="/" class="brand">CSA<span class="brand-tag">Clinical-Stage Asset Intelligence</span></a>
      <div class="navlinks">
        <a href="/#calendar">Catalyst calendar</a>
        <a href="/#pricing">Get the data</a>
      </div>
    </div>
  </header>

  <div class="container">
    <p class="crumbs"><a href="/">CSA</a> &rsaquo; {h1}</p>
  </div>

  <section class="hero">
    <div class="container">
      <p class="eyebrow">Directory</p>
      <h1>{h1}</h1>
      <p class="sub">{lede}</p>
      <p class="count">{n} {label}</p>
    </div>
  </section>

  <main class="container">
    <ul class="dirlist">
{items}
    </ul>
    <p class="advice">Informational data derived from public trial registries. Not investment advice.</p>
  </main>

  <footer>
    <div class="container">
      <p>CSA &mdash; Clinical-Stage Asset Intelligence &middot; <a href="/#pricing">Full snapshot ($499)</a> &middot; <a href="/">csa.dataengineered.io</a></p>
      <div class="catalog-line" style="text-align:center; margin-top:14px; font-size:0.85rem; opacity:0.85;"><a href="https://dataengineered.io/">Part of the DataEngineered catalog &rarr;</a> &middot; <a href="https://dataengineered.io/about">About</a> &middot; <a href="https://dataengineered.io/terms">Terms</a> &middot; <a href="https://dataengineered.io/privacy">Privacy</a> &middot; <a href="https://dataengineered.io/refund-policy">Refund policy</a></div>
    </div>
  </footer>
</body>
</html>
"""


def text_of(pattern, source):
    m = re.search(pattern, source, re.S)
    if not m:
        return ""
    return htmllib.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()


def read_entry(path):
    """Pull the display name and a short descriptor from the page itself."""
    src = path.read_text(encoding="utf-8", errors="replace")
    name = text_of(r"<h1[^>]*>(.*?)</h1>", src)
    title = text_of(r"<title[^>]*>(.*?)</title>", src)
    # "<name> — <descriptor> | CSA"  ->  descriptor
    desc = ""
    if "|" in title:
        title = title.rsplit("|", 1)[0].strip()
    for dash in ("—", "-"):
        if dash in title:
            desc = title.split(dash, 1)[1].strip()
            break
    if not name:
        name = path.stem
    return {"slug": path.stem, "name": name, "desc": desc}


def build_section(sec):
    d = ROOT / sec["slug"]
    pages = sorted(p for p in d.glob("*.html") if p.stem != "index")
    if not pages:
        sys.exit("no pages found in %s/" % sec["slug"])

    entries = [read_entry(p) for p in pages]
    entries.sort(key=lambda e: e["name"].lower())
    n = len(entries)

    items = []
    for e in entries:
        d_html = ('<span class="d">%s</span>' % htmllib.escape(e["desc"])) if e["desc"] else ""
        items.append(
            '      <li><a href="%s"><span class="n">%s</span>%s</a></li>'
            % (htmllib.escape(e["slug"]), htmllib.escape(e["name"]), d_html)
        )

    # <title> and og:title share this one value (the PAGE template inserts {title}
    # into both), so they can't drift out of sync.
    title = fit_title(sec["h1"], sec["title_options"](n), "CSA")

    page = PAGE.format(
        base=BASE,
        slug=sec["slug"],
        title=htmllib.escape(title),
        desc=htmllib.escape(sec["desc"]),
        jname='"%s"' % sec["h1"],
        jdesc='"%s"' % sec["desc"].replace('"', "'"),
        h1=sec["h1"],
        lede=sec["lede"],
        label=sec["label"],
        n=len(entries),
        style=STYLE,
        items="\n".join(items),
    )
    (d / "index.html").write_text(page, encoding="utf-8", newline="")
    return len(entries)


def update_homepage(counts):
    """Link both directories from the end of the catalyst-calendar section.

    The sample table there already promises the full corpus, so the links
    belong with it. They are not added to the sticky nav, which is already
    full, and not as a new numbered section, which would break the 01..05
    plate numbering the page uses.
    """
    src = INDEX.read_text(encoding="utf-8")
    block = (
        '{begin}\n'
        '      <p style="color:var(--ink-2); max-width:60ch; margin:26px 0 14px; font-size:.95rem;">'
        'Every tracked catalyst and every listed sponsor has its own source-linked page.</p>\n'
        '      <div class="cta-group">\n'
        '        <a class="btn btn-outline" href="/catalysts/">Catalyst directory ({c})</a>\n'
        '        <a class="btn btn-outline" href="/sponsors/">Sponsor directory ({s})</a>\n'
        '      </div>\n'
        '      {end}'
    ).format(begin=BEGIN, end=END, c=counts["catalysts"], s=counts["sponsors"])

    if BEGIN in src and END in src:
        src = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END),
                     lambda _: block, src, flags=re.DOTALL)
    else:
        anchor = "    </div>\n  </section>\n\n  <!-- 04 · Pricing -->"
        if anchor not in src:
            sys.exit("could not find the end of the #calendar section")
        src = src.replace(anchor, block + "\n" + anchor, 1)
    INDEX.write_text(src, encoding="utf-8", newline="")


def update_sitemap(counts):
    """No-op: scripts/generate_seo_pages.py now writes the whole sitemap (via
    seo_common.write_sitemap), including the /catalysts/ and /sponsors/ hub
    URLs with a git-derived lastmod. Kept as a function (rather than removed)
    so main() doesn't need to change, and so a caller running only this script
    gets a clear no-op instead of a missing-attribute error."""
    return []


def main():
    counts = {}
    for sec in SECTIONS:
        counts[sec["slug"]] = build_section(sec)
        print("wrote %s/index.html -- %d entries" % (sec["slug"], counts[sec["slug"]]))
    update_homepage(counts)
    print("homepage nav block updated")
    added = update_sitemap(counts)
    print("sitemap: %s" % (", ".join(added) if added else "already present"))


if __name__ == "__main__":
    main()
