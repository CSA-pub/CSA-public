"""
generate_seo_pages.py — CSA programmatic-SEO page generator.

Builds static, index-ready landing pages from the free sample so search engines
can surface specific queries (e.g. "mezigdomide phase 3 readout date",
"PFE clinical-stage catalysts 2026"):

  - catalysts/<asset>.html   one forward-catalyst detail page per drug asset
  - sponsors/<ticker>.html   one hub page per listed sponsor, grouping its assets
  - sitemap.xml              regenerated with every URL (clean, extensionless)

Each page carries full SEO meta (canonical + self-referencing hreflang, OpenGraph),
JSON-LD (Dataset / CollectionPage + BreadcrumbList + ItemList), the CSA
clinical-instrument design, and the "data, not investment advice" notice.

    python scripts/generate_seo_pages.py

Reads samples/catalyst_calendar_sample.csv + samples/asset_master_sample.csv;
no dependencies beyond the standard library.
"""

import csv
import html
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seo_common import fit_title, fit_desc, write_sitemap, related_block

SITE = "https://csa.dataengineered.io"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAL_CSV = os.path.join(ROOT, "samples", "catalyst_calendar_sample.csv")
MAS_CSV = os.path.join(ROOT, "samples", "asset_master_sample.csv")
CAT_DIR = os.path.join(ROOT, "catalysts")
SPON_DIR = os.path.join(ROOT, "sponsors")

FONTS = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600"
         "&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap")

_SUFFIX = {"plc", "inc", "co", "corp", "llc", "lp", "ltd", "ag", "sa", "nv", "ab",
           "asa", "se", "spa", "as", "kgaa", "pbc", "us", "usa", "nk", "se"}


def slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(text).lower())
    return text.strip("-")


def esc(text) -> str:
    return html.escape(str(text if text is not None else "").strip())


def pretty_company(name: str) -> str:
    """Display-only title-casing that keeps corporate suffixes/acronyms upper."""
    out = []
    for w in str(name).split():
        core = w.strip(".,")
        if core.lower() in _SUFFIX:
            out.append(core.upper() + ("." if w.endswith(".") else ""))
        elif core.isupper() and len(core) <= 4:
            out.append(w)  # already an acronym, leave it
        else:
            out.append(w.capitalize())
    return " ".join(out) or name


def quarter_of(date_str):
    """'2026-07-18' -> 'Q3 2026'. Empty/unparseable input returns ''."""
    m = re.match(r"^(\d{4})-(\d{2})-\d{2}$", (date_str or "").strip())
    if not m:
        return ""
    year, month = int(m.group(1)), int(m.group(2))
    return f"Q{(month - 1) // 3 + 1} {year}"


def primary_condition(conditions):
    """First listed condition, trimmed -- used only to match records, never displayed
    in place of the record's own text."""
    conditions = (conditions or "").strip()
    if not conditions:
        return ""
    return (conditions.split(";")[0] if ";" in conditions else conditions).strip()


def pad_related(items, pool, index_of, self_key, href_of, label_of, minimum=3):
    """Top up `items` (list of (href, label, reason_or_None)) to at least `minimum`
    entries by walking outward from the record's own position in `pool` (sorted by
    display name), alternating previous/next and wrapping around. Only used when the
    field-based related items fall short -- the padding links are real neighbouring
    records, never invented, just labelled by their (real) adjacency rather than a
    shared field."""
    if len(items) >= minimum:
        return items
    have = {href for href, _, _ in items}
    n = len(pool)
    i = index_of[self_key]
    dist = 1
    while len(items) < minimum and dist < n:
        for j in (i - dist, i + dist):
            if len(items) >= minimum:
                break
            cand = pool[j % n]
            href = href_of(cand)
            if href in have:
                continue
            items.append((href, label_of(cand), "neighbouring record"))
            have.add(href)
        dist += 1
    return items


def sponsor_prose(company_disp, ticker, items, c_by_asset, m_by_asset):
    """Unique, data-derived summary of a sponsor's forward-catalyst footprint, built
    only from its own rows (catalyst count, phase mix, next readout, confidence mix,
    tracked indications). Only emits clauses for fields that are actually populated
    -- empty fields are omitted, never faked. One fixed sentence structure per fact;
    uniqueness across sponsors comes from the differing field values themselves, not
    from varied wording."""
    all_assets = sorted({a for a, *_ in items})
    all_cats = [c for a in all_assets for c in c_by_asset[a]]
    n_cats = len(all_cats)
    n_assets = len(all_assets)
    phases = []
    for _a, _slug, _c, _nxt, phase in items:
        lbl = (phase or "").replace("PHASE", "Phase ").strip()
        if lbl and lbl not in phases:
            phases.append(lbl)

    nxt = items[0][3]
    window = (nxt.get("event_window") or nxt.get("event_date") or "").strip()
    precision = (nxt.get("date_precision") or "").strip()
    etype = (nxt.get("event_type") or "").strip()

    cat_word = "catalyst" if n_cats == 1 else "catalysts"
    asset_word = "asset" if n_assets == 1 else "assets"
    s1 = f"CSA tracks {n_cats} forward {esc(cat_word)} for {esc(company_disp)} across {n_assets} clinical-stage {esc(asset_word)}"
    if phases:
        s1 += f", spanning {', '.join(esc(p) for p in phases)}"
    s1 += "."

    s2 = f"The nearest is a {esc(etype).lower()} expected {esc(window)}"
    if precision:
        s2 += f" ({esc(precision)} precision)"
    s2 += "."

    sentences = [s1, s2]

    conf_counts = Counter((c.get("confidence") or "").strip() for c in all_cats
                          if (c.get("confidence") or "").strip())
    if conf_counts:
        parts = [f"{n} {esc(c).lower()}" for c, n in sorted(conf_counts.items(), key=lambda kv: (-kv[1], kv[0]))]
        sentences.append(f"Confidence across its tracked catalysts breaks down as {', '.join(parts)}.")

    indications = []
    for a in all_assets:
        for m in m_by_asset.get(a, []):
            cond = primary_condition(m.get("conditions"))
            if cond and cond not in indications:
                indications.append(cond)
    if indications:
        shown = indications[:3]
        s4 = f"Tracked indications include {', '.join(esc(x) for x in shown)}"
        if len(indications) > 3:
            s4 += f", and {len(indications) - 3} more"
        s4 += "."
        sentences.append(s4)

    return f'<p class="sub" style="margin-top:20px;max-width:74ch;line-height:1.7;color:var(--ink-2);">{" ".join(sentences)}</p>'


def catalyst_prose(asset, cats, nxt, ticker, company_disp, phase_lbl, status, conditions, nct, etype, mrows):
    """Unique, data-derived summary of an asset's forward catalyst + trial context."""
    n = len(cats)
    trials = len({(m.get("nct_id") or "").strip() for m in mrows if (m.get("nct_id") or "").strip()})
    window = (nxt.get("event_window") or nxt.get("event_date") or "").strip()
    precision = (nxt.get("date_precision") or "").strip()
    conf = (nxt.get("confidence") or "").strip()
    p = (f"{esc(asset)} is a clinical-stage drug asset sponsored by {esc(company_disp)}, "
         f"listed as {esc(ticker)}.")
    cat_word = "catalyst" if n == 1 else "catalysts"
    p += f" CSA tracks {n} forward {cat_word} for it — the nearest is a {esc(etype).lower()} expected {esc(window)}"
    extras = []
    if precision:
        extras.append(f"{esc(precision)} precision")
    if conf:
        extras.append(f"{esc(conf)} confidence")
    if extras:
        p += f" ({', '.join(extras)})"
    if nct:
        p += f", tied to trial {esc(nct)}"
    p += "."
    detail = []
    if phase_lbl and phase_lbl != "clinical-stage":
        detail.append(f"in {esc(phase_lbl)}")
    if status:
        detail.append(f"currently {esc(status).lower().replace('_', ' ')}")
    if detail:
        s = f" The asset is {' and '.join(detail)}"
        if conditions:
            cond = conditions.split(";")[0].strip() if ";" in conditions else conditions
            s += f", studied in {esc(cond[:120])}"
        s += "."
        p += s
    if trials > 1:
        p += f" It appears across {trials} tracked trials in the CSA sample."
    return f'<p class="sub" style="margin-top:20px;max-width:74ch;line-height:1.7;color:var(--ink-2);">{p}</p>'


CSS = """
:root{
  --ground:#0B1315;--surface:#101A1C;--surface-2:#162325;
  --ink:#E7EEED;--ink-2:#9BABAA;--ink-3:#758484;
  --line:#213032;--accent:#2BB3A8;--accent-bright:#48D2C6;
  --warn:#D69A3A;--warn-bg:#26200F;--risk:#DB6857;
  --font-sans:'IBM Plex Sans',system-ui,-apple-system,sans-serif;
  --font-mono:'IBM Plex Mono',ui-monospace,'SFMono-Regular',monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--font-sans);background:var(--ground);color:var(--ink);line-height:1.6;padding-bottom:64px;-webkit-font-smoothing:antialiased}
.mono{font-family:var(--font-mono)}
.container{max-width:1000px;margin:0 auto;padding:0 24px}
a{color:inherit}
header{border-bottom:1px solid var(--line);background:var(--surface);padding:15px 0;position:sticky;top:0;z-index:5}
.nav{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.brand{font-weight:700;font-size:1.14rem;text-decoration:none;color:var(--ink);letter-spacing:-.01em;display:flex;align-items:center}
.brand .accent{color:var(--accent)}
.brand-tag{font-family:var(--font-mono);font-size:.54rem;text-transform:uppercase;letter-spacing:.16em;color:var(--ink-3);border-left:1px solid var(--line);padding-left:11px;margin-left:11px}
.navlinks a{font-family:var(--font-mono);font-size:.66rem;text-transform:uppercase;letter-spacing:.1em;color:var(--ink-2);text-decoration:none;margin-left:18px}
.navlinks a:hover{color:var(--accent)}
.crumbs{font-family:var(--font-mono);font-size:.63rem;color:var(--ink-3);margin:22px 0 0;letter-spacing:.04em}
.crumbs a{color:var(--ink-2);text-decoration:none}
.crumbs a:hover{color:var(--accent)}
.eyebrow{font-family:var(--font-mono);font-size:.63rem;letter-spacing:.2em;text-transform:uppercase;color:var(--accent);font-weight:600}
.hero{padding:34px 0 30px;border-bottom:1px solid var(--line)}
h1{font-size:2.35rem;font-weight:700;letter-spacing:-.022em;margin:12px 0 6px;text-wrap:balance}
.sub{color:var(--ink-2);font-size:1.03rem}
.sub b{color:var(--ink);font-weight:600}
.badges{display:flex;gap:9px;flex-wrap:wrap;margin-top:20px}
.badge{font-family:var(--font-mono);font-size:.62rem;text-transform:uppercase;letter-spacing:.07em;padding:5px 10px;border:1px solid var(--line);border-radius:4px;color:var(--ink-2);white-space:nowrap}
.badge.accent{color:var(--accent);border-color:rgba(43,179,168,.4)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-top:30px}
@media(max-width:760px){.grid2{grid-template-columns:1fr}}
.card{background:var(--surface);border:1px solid var(--line);border-radius:9px;padding:22px}
.card h3{font-size:.68rem;font-family:var(--font-mono);text-transform:uppercase;letter-spacing:.15em;color:var(--ink-3);margin-bottom:14px;font-weight:600}
.row{display:flex;justify-content:space-between;gap:16px;padding:10px 0;border-bottom:1px dashed var(--line)}
.row:last-child{border-bottom:none}
.k{color:var(--ink-2);font-size:.9rem}
.v{font-family:var(--font-mono);font-weight:500;text-align:right;font-variant-numeric:tabular-nums}
.v.accent{color:var(--accent)}
.btn{display:inline-block;font-family:var(--font-mono);font-size:.67rem;text-transform:uppercase;letter-spacing:.1em;padding:9px 15px;border:1px solid var(--line);border-radius:5px;color:var(--ink);text-decoration:none;transition:border-color .2s,color .2s;font-weight:500}
.btn:hover{border-color:var(--accent);color:var(--accent)}
.btn.primary{background:var(--accent);color:#04100F;border-color:var(--accent);font-weight:600}
.btn.primary:hover{background:var(--accent-bright);color:#04100F}
.statbar{display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin-top:26px}
@media(max-width:600px){.statbar{grid-template-columns:1fr}}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:9px;padding:16px;text-align:center}
.stat .n{font-family:var(--font-mono);font-size:1.5rem;font-weight:600;color:var(--accent);font-variant-numeric:tabular-nums}
.stat .l{font-size:.79rem;color:var(--ink-3);margin-top:3px}
.assetgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:17px;margin-top:32px}
.acard{background:var(--surface);border:1px solid var(--line);border-radius:9px;padding:18px;transition:border-color .2s,transform .2s}
.acard:hover{border-color:var(--accent);transform:translateY(-2px)}
.acard a.name{text-decoration:none;color:var(--ink);font-weight:600;font-size:1.08rem}
.acard a.name:hover{color:var(--accent)}
.acard .meta{display:flex;justify-content:space-between;font-family:var(--font-mono);font-size:.78rem;color:var(--ink-2);margin-top:12px;padding-top:12px;border-top:1px dashed var(--line);font-variant-numeric:tabular-nums}
.tbl{width:100%;border-collapse:collapse;margin-top:8px;font-size:.86rem}
.tbl th,.tbl td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line)}
.tbl th{font-family:var(--font-mono);font-size:.6rem;text-transform:uppercase;letter-spacing:.1em;color:var(--ink-3);font-weight:600}
.tbl td{font-family:var(--font-mono);font-variant-numeric:tabular-nums;color:var(--ink-2)}
.advice{display:flex;gap:12px;margin-top:34px;padding:15px 18px;border:1px solid rgba(214,154,58,.4);border-radius:8px;background:var(--warn-bg)}
.advice .mk{color:var(--warn);font-weight:700;font-family:var(--font-mono)}
.advice p{font-size:.85rem;color:var(--ink-2)}
.advice b{color:var(--ink)}
.cta{margin-top:36px;text-align:center;padding:30px 20px;border:1px solid var(--line);border-radius:10px;background:var(--surface)}
.cta p{color:var(--ink-2);margin-bottom:16px}
footer{margin-top:52px;border-top:1px solid var(--line);padding:26px 0;text-align:center;color:var(--ink-3);font-size:.84rem}
footer a{color:var(--accent);text-decoration:none}
.related{margin-top:32px;padding-top:22px;border-top:1px solid var(--line)}
.related h2{font-family:var(--font-mono);font-size:.68rem;text-transform:uppercase;letter-spacing:.15em;color:var(--ink-3);font-weight:600;margin-bottom:12px}
.related ul{list-style:none;display:flex;flex-wrap:wrap;gap:9px 14px}
.related li{font-size:.88rem}
.related a{color:var(--accent);text-decoration:none}
.related a:hover{text-decoration:underline}
.related-why{color:var(--ink-3);font-size:.9em}
"""


def head(title, desc, url, og_type, jsonld_blocks):
    ld = "\n".join(
        '  <script type="application/ld+json">\n  ' + json.dumps(b, ensure_ascii=False) + "\n  </script>"
        for b in jsonld_blocks
    )
    return f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <meta name="description" content="{desc}" />
  <meta name="robots" content="index, follow, max-image-preview:large" />
  <meta name="theme-color" content="#0B1315" />
  <link rel="canonical" href="{url}" />
  <link rel="alternate" hreflang="en" href="{url}" />
  <link rel="alternate" hreflang="x-default" href="{url}" />
  <link rel="icon" href="../favicon.svg" type="image/svg+xml" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{desc}" />
  <meta property="og:url" content="{url}" />
  <meta property="og:type" content="{og_type}" />
  <meta property="og:image" content="{SITE}/og-image.png" />
  <meta name="twitter:card" content="summary_large_image" />
{ld}
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="{FONTS}" rel="stylesheet" media="print" onload="this.media='all'">
  <noscript><link href="{FONTS}" rel="stylesheet"></noscript>
  <style>{CSS}</style>
</head>"""


NAV = """  <header>
    <div class="container nav">
      <a href="/" class="brand">CSA<span class="brand-tag">Clinical-Stage Asset Intelligence</span></a>
      <div class="navlinks">
        <a href="/#calendar">Catalyst calendar</a>
        <a href="/#pricing">Get the data</a>
      </div>
    </div>
  </header>"""

ADVICE = """      <div class="advice">
        <span class="mk">!</span>
        <p><b>Data, not investment advice.</b> CSA is information, not a recommendation to buy, sell or hold any security. Estimated catalyst dates routinely slip and are graded by confidence &mdash; verify against the source link before acting.</p>
      </div>"""

FOOTER = """  <footer>
    <div class="container">
      <p>CSA &mdash; Clinical-Stage Asset Intelligence &middot; <a href="/#pricing">Full snapshot ($499)</a> &middot; <a href="/">csa.dataengineered.io</a></p>
    </div>
  </footer>
</body>
</html>"""


def main():
    os.makedirs(CAT_DIR, exist_ok=True)
    os.makedirs(SPON_DIR, exist_ok=True)

    with open(CAL_CSV, encoding="utf-8") as f:
        cal = [r for r in csv.DictReader(f) if r.get("asset") and r.get("ticker")]
    with open(MAS_CSV, encoding="utf-8") as f:
        master = [r for r in csv.DictReader(f) if r.get("asset")]

    # master rows grouped by asset (for trial/sponsor enrichment)
    m_by_asset = defaultdict(list)
    for m in master:
        m_by_asset[m["asset"]].append(m)

    # catalysts grouped by asset
    c_by_asset = defaultdict(list)
    for c in cal:
        c_by_asset[c["asset"]].append(c)

    sitemap_entries = [
        (SITE + "/", os.path.join(ROOT, "index.html"), "weekly", "1.0"),
        (SITE + "/catalysts/", os.path.join(CAT_DIR, "index.html"), "weekly", "0.9"),
        (SITE + "/sponsors/", os.path.join(SPON_DIR, "index.html"), "weekly", "0.9"),
    ]
    used_slugs = {}

    # ---- pass 1: precompute every asset's metadata up front. The related block
    # on each page compares one asset against every other, so all of it has to be
    # known before any page is written. ------------------------------------------
    asset_meta = {}
    for asset, cats in c_by_asset.items():
        cats = sorted(cats, key=lambda c: c["event_date"])
        nxt = cats[0]
        ticker = nxt["ticker"].strip()
        slug = slugify(asset)
        if slug in used_slugs and used_slugs[slug] != asset:
            slug = f"{slug}-{slugify(ticker)}"
        used_slugs[slug] = asset

        # enrich from master: prefer the row matching the next catalyst's trial
        mrows = m_by_asset.get(asset, [])
        mrow = next((m for m in mrows if m.get("nct_id") == nxt.get("nct_id")), mrows[0] if mrows else {})
        company = mrow.get("company_name", "").strip() or ticker
        company_disp = pretty_company(company)
        phase = (mrow.get("phase") or "").strip()
        status = (mrow.get("status") or "").strip()
        conditions = (mrow.get("conditions") or "").strip()
        nct = nxt.get("nct_id", "").strip()
        phase_lbl = phase.replace("PHASE", "Phase ") if phase else "clinical-stage"
        etype = nxt.get("event_type", "").strip() or "catalyst"

        asset_meta[asset] = {
            "cats": cats, "nxt": nxt, "ticker": ticker, "slug": slug,
            "mrows": mrows, "mrow": mrow, "company_disp": company_disp,
            "phase": phase, "phase_lbl": phase_lbl, "status": status,
            "conditions": conditions, "nct": nct, "etype": etype,
            "condition": primary_condition(conditions),
            "quarter": quarter_of(nxt.get("event_date")),
        }

    assets_by_name = sorted(asset_meta.keys(), key=lambda a: a.lower())
    asset_pos = {a: i for i, a in enumerate(assets_by_name)}
    used_titles = set()

    # ---- asset detail pages -------------------------------------------------
    asset_index = {}  # asset -> (slug, ticker, next catalyst)
    for asset, meta in asset_meta.items():
        cats, nxt, ticker, slug = meta["cats"], meta["nxt"], meta["ticker"], meta["slug"]
        mrows, mrow, company_disp = meta["mrows"], meta["mrow"], meta["company_disp"]
        phase, phase_lbl, status = meta["phase"], meta["phase_lbl"], meta["status"]
        conditions, nct, etype = meta["conditions"], meta["nct"], meta["etype"]
        url = f"{SITE}/catalysts/{slug}"
        asset_index[asset] = (slug, ticker, company_disp, nxt, phase)

        # title: try the entity as-is, then disambiguate with the NCT id on a
        # (rare) collision after truncation/rounding, so every title stays unique.
        title = esc(fit_title(asset, [f"{phase_lbl} catalyst ({ticker})", f"{phase_lbl} catalyst", "catalyst"], "CSA"))
        if title in used_titles and nct:
            title = esc(fit_title(f"{asset} ({nct})",
                                   [f"{phase_lbl} catalyst ({ticker})", f"{phase_lbl} catalyst", "catalyst"], "CSA"))
        used_titles.add(title)

        # description: lead with the most distinctive fact (event type + expected
        # date), then phase / sponsor+ticker / confidence, all from this row only.
        window = (nxt.get("event_window") or nxt.get("event_date") or "").strip()
        confidence = (nxt.get("confidence") or "").strip()
        desc_tail = []
        if phase_lbl and phase_lbl != "clinical-stage":
            desc_tail.append(phase_lbl)
        desc_tail.append(f"sponsored by {company_disp} ({ticker})")
        if confidence:
            desc_tail.append(f"{confidence} confidence")
        desc = esc(fit_desc(f"{etype.lower()} for {asset} expected {window}, {', '.join(desc_tail)}. "
                             "Not investment advice."))

        # related: reciprocal link to the sponsor, up to 2 same-indication assets,
        # up to 2 same-quarter-readout assets, capped at 5, padded to >=3 with
        # real name-order neighbours if the CSV doesn't offer enough matches, then
        # the catalyst directory hub.
        related_items = [(f"../sponsors/{slugify(ticker)}", f"{company_disp} ({ticker})", "sponsor")]
        used_assets = {asset}
        cond = meta["condition"]
        added = 0
        if cond:
            for a2, m2 in asset_meta.items():
                if added >= 2:
                    break
                if a2 in used_assets or m2["condition"].lower() != cond.lower():
                    continue
                related_items.append((f"../catalysts/{m2['slug']}", a2, m2["condition"]))
                used_assets.add(a2)
                added += 1
        q = meta["quarter"]
        added = 0
        if q:
            for a2, m2 in asset_meta.items():
                if added >= 2:
                    break
                if a2 in used_assets or m2["quarter"] != q:
                    continue
                related_items.append((f"../catalysts/{m2['slug']}", a2, q))
                used_assets.add(a2)
                added += 1
        related_items = related_items[:5]
        related_items = pad_related(related_items, assets_by_name, asset_pos, asset,
                                     lambda a2: f"../catalysts/{asset_meta[a2]['slug']}", lambda a2: a2)
        related_items.append(("../catalysts/", "All tracked catalysts", None))
        related_html = related_block(related_items, "Related catalysts and sponsor", limit=None)

        ct = nxt.get("event_type", ""); cd = nxt.get("event_date", "")
        ld_dataset = {
            "@context": "https://schema.org", "@type": "Dataset",
            "name": f"{asset} ({ticker}) forward catalyst record",
            "description": (f"Forward clinical/regulatory catalyst for the clinical-stage asset {asset}, "
                            f"linked to listed sponsor {company_disp} ({ticker}): {etype} on {cd} from trial {nct}."),
            "url": url,
            "creator": {"@type": "Organization", "name": "DataEngineered", "url": SITE},
            "license": "https://creativecommons.org/licenses/by-nc/4.0/",
            "isAccessibleForFree": True,
            "variableMeasured": ["asset name", "listed ticker", "lead sponsor", "trial phase",
                                 "trial status", "catalyst event type", "catalyst date",
                                 "date confidence", "NCT id", "source URL"],
        }
        ld_crumbs = {
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                {"@type": "ListItem", "position": 2, "name": f"{company_disp} ({ticker})",
                 "item": f"{SITE}/sponsors/{slugify(ticker)}"},
                {"@type": "ListItem", "position": 3, "name": asset, "item": url},
            ],
        }

        # multi-catalyst table
        rows_html = ""
        if len(cats) > 1:
            trs = "".join(
                f"<tr><td>{esc(c['event_date'])}</td><td>{esc(c.get('event_type'))}</td>"
                f"<td>{esc(c.get('confidence'))}</td>"
                f"<td><a href=\"{esc(c.get('source_url'))}\" target=\"_blank\" rel=\"noopener\" style=\"color:var(--accent)\">{esc(c.get('nct_id'))}</a></td></tr>"
                for c in cats)
            rows_html = f"""
      <div class="card" style="margin-top:22px">
        <h3>All tracked catalysts for {esc(asset)}</h3>
        <table class="tbl"><thead><tr><th>Date</th><th>Event</th><th>Confidence</th><th>Trial</th></tr></thead>
        <tbody>{trs}</tbody></table>
      </div>"""

        cond_disp = esc(conditions[:160] + ("…" if len(conditions) > 160 else "")) if conditions else "&mdash;"
        body = f"""<body>
{NAV}
  <main class="container">
    <div class="crumbs"><a href="/">Home</a> / <a href="../sponsors/{slugify(ticker)}">{esc(company_disp)} ({esc(ticker)})</a> / <span>{esc(asset)}</span></div>
    <section class="hero">
      <span class="eyebrow">Forward catalyst &middot; {esc(ticker)}</span>
      <h1>{esc(asset)}</h1>
      <p class="sub">Sponsor <b>{esc(company_disp)}</b> &middot; listed as <b>{esc(ticker)}</b></p>
      <div class="badges">
        <span class="badge accent">{esc(etype)}</span>
        <span class="badge">{esc(phase_lbl)}</span>
        <span class="badge">Confidence: {esc(nxt.get('confidence'))}</span>
        <span class="badge">Source: {esc(nxt.get('source'))}</span>
      </div>
    </section>
    {catalyst_prose(asset, cats, nxt, ticker, company_disp, phase_lbl, status, conditions, nct, etype, mrows)}
    <div class="grid2">
      <div class="card">
        <h3>Next catalyst</h3>
        <div class="row"><span class="k">Event type</span><span class="v accent">{esc(etype)}</span></div>
        <div class="row"><span class="k">Expected date</span><span class="v">{esc(nxt.get('event_date'))}</span></div>
        <div class="row"><span class="k">As disclosed</span><span class="v">{esc(nxt.get('event_window'))}</span></div>
        <div class="row"><span class="k">Date precision</span><span class="v">{esc(nxt.get('date_precision'))}</span></div>
        <div class="row"><span class="k">Confidence</span><span class="v">{esc(nxt.get('confidence'))}</span></div>
        <div style="margin-top:18px">
          <a class="btn" href="{esc(nxt.get('source_url'))}" target="_blank" rel="noopener">Verify at source &rarr;</a>
        </div>
      </div>
      <div class="card">
        <h3>Trial &amp; sponsor</h3>
        <div class="row"><span class="k">Trial (NCT)</span><span class="v">{esc(nct) or '&mdash;'}</span></div>
        <div class="row"><span class="k">Phase</span><span class="v">{esc(phase) or '&mdash;'}</span></div>
        <div class="row"><span class="k">Status</span><span class="v">{esc(status) or '&mdash;'}</span></div>
        <div class="row"><span class="k">Lead sponsor</span><span class="v">{esc(mrow.get('sponsor_raw')) or '&mdash;'}</span></div>
        <div class="row"><span class="k">Listed as</span><span class="v accent">{esc(ticker)}</span></div>
        <div class="row"><span class="k">Condition(s)</span><span class="v" style="max-width:58%">{cond_disp}</span></div>
      </div>
    </div>
{rows_html}
{ADVICE}
    <div class="cta">
      <p>This is one row of the free CSA sample. The full snapshot carries <b>2,103 forward catalysts</b> across <b>139 listed sponsors</b>.</p>
      <a class="btn primary" href="/#pricing">Get the full dataset &mdash; $499 &rarr;</a>
      &nbsp;
      <a class="btn" href="../sponsors/{slugify(ticker)}">More {esc(ticker)} catalysts</a>
    </div>
    {related_html}
  </main>
{FOOTER}"""

        page = head(title, desc, url, "article", [ld_dataset, ld_crumbs]) + "\n" + body
        with open(os.path.join(CAT_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
            f.write(page)
        sitemap_entries.append((url, os.path.join(CAT_DIR, f"{slug}.html"), "monthly", "0.8"))

    # ---- pass 1: sponsor metadata, precomputed the same way as assets ----------
    by_ticker = defaultdict(list)
    for asset, (slug, ticker, company_disp, nxt, phase) in asset_index.items():
        by_ticker[ticker].append((asset, slug, company_disp, nxt, phase))

    sponsor_meta = {}
    for ticker, items in by_ticker.items():
        items = sorted(items, key=lambda x: x[3]["event_date"])
        company_disp = items[0][2]
        nearest_date = items[0][3]["event_date"]
        sponsor_meta[ticker] = {
            "items": items, "company_disp": company_disp,
            "nearest_date": nearest_date, "quarter": quarter_of(nearest_date),
        }

    sponsors_by_name = sorted(sponsor_meta.keys(), key=lambda t: sponsor_meta[t]["company_disp"].lower())
    sponsor_pos = {t: i for i, t in enumerate(sponsors_by_name)}
    used_sponsor_titles = set()

    # ---- sponsor hub pages --------------------------------------------------
    for ticker, smeta in sponsor_meta.items():
        items = smeta["items"]
        company_disp = smeta["company_disp"]
        n_assets = len({a for a, *_ in items})
        n_cats = sum(len(c_by_asset[a]) for a, *_ in items)
        nearest = smeta["nearest_date"]
        url = f"{SITE}/sponsors/{slugify(ticker)}"

        title = esc(fit_title(company_disp, [f"({ticker}) catalysts & pipeline", f"({ticker}) catalysts", "catalysts"], "CSA"))
        if title in used_sponsor_titles:
            title = esc(fit_title(f"{company_disp} ({ticker})",
                                   [f"catalysts & pipeline", "catalysts"], "CSA"))
        used_sponsor_titles.add(title)

        phases = []
        for _a, _slug, _c, _nxt, phase in items:
            lbl = (phase or "").replace("PHASE", "Phase ").strip()
            if lbl and lbl not in phases:
                phases.append(lbl)
        cat_word = "catalyst" if n_cats == 1 else "catalysts"
        asset_word = "asset" if n_assets == 1 else "assets"
        desc_raw = f"{n_cats} forward {cat_word} tracked for {company_disp} ({ticker}) across {n_assets} {asset_word}"
        if phases:
            desc_raw += f" in {', '.join(phases)}"
        desc_raw += f", nearest readout {nearest}. Not investment advice."
        desc = esc(fit_desc(desc_raw))

        prose_html = sponsor_prose(company_disp, ticker, items, c_by_asset, m_by_asset)

        # related: every one of this sponsor's own catalysts (uncapped, per the
        # brief), up to 2 sponsors with a readout in the same quarter, padded to
        # >=3 with real name-order neighbours if needed, then the sponsor hub.
        related_items = [(f"../catalysts/{slug2}", a2, ((phase2 or "").replace("PHASE", "Phase ").strip() or None))
                          for a2, slug2, _c2, _n2, phase2 in items]
        used_tickers = {ticker}
        q = smeta["quarter"]
        added = 0
        if q:
            for t2, sm2 in sponsor_meta.items():
                if added >= 2:
                    break
                if t2 in used_tickers or sm2["quarter"] != q:
                    continue
                related_items.append((f"../sponsors/{slugify(t2)}", f"{sm2['company_disp']} ({t2})", q))
                used_tickers.add(t2)
                added += 1
        related_items = pad_related(related_items, sponsors_by_name, sponsor_pos, ticker,
                                     lambda t2: f"../sponsors/{slugify(t2)}",
                                     lambda t2: f"{sponsor_meta[t2]['company_disp']} ({t2})")
        related_items.append(("../sponsors/", "All sponsors", None))
        related_html = related_block(related_items, "Related sponsors and catalysts", limit=None)

        cards = ""
        for asset, slug, _c, nxt, phase in items:
            phase_lbl = (phase or "").replace("PHASE", "Phase ") or "clinical-stage"
            cards += f"""
        <div class="acard">
          <a class="name" href="../catalysts/{slug}">{esc(asset)}</a>
          <div class="meta"><span>{esc(nxt.get('event_type'))} &middot; {esc(phase_lbl)}</span><span>{esc(nxt.get('event_date'))}</span></div>
        </div>"""

        ld_collection = {
            "@context": "https://schema.org", "@type": "CollectionPage",
            "name": f"{company_disp} ({ticker}) — clinical-stage catalysts",
            "description": (f"Forward clinical-stage catalysts for listed sponsor {company_disp} ({ticker}): "
                            f"{n_cats} tracked catalysts across {n_assets} assets."),
            "url": url,
        }
        ld_crumbs = {
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                {"@type": "ListItem", "position": 2, "name": f"{company_disp} ({ticker})", "item": url},
            ],
        }
        ld_list = {
            "@context": "https://schema.org", "@type": "ItemList",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": asset,
                 "url": f"{SITE}/catalysts/{slug}"}
                for i, (asset, slug, _c, _n, _p) in enumerate(items)
            ],
        }

        body = f"""<body>
{NAV}
  <main class="container">
    <div class="crumbs"><a href="/">Home</a> / <span>{esc(company_disp)} ({esc(ticker)})</span></div>
    <section class="hero">
      <span class="eyebrow">Sponsor pipeline &middot; {esc(ticker)}</span>
      <h1>{esc(company_disp)}</h1>
      <p class="sub">Forward clinical-stage catalysts linked to <b>{esc(ticker)}</b></p>
      <div class="statbar">
        <div class="stat"><div class="n">{n_cats}</div><div class="l">Tracked catalysts (sample)</div></div>
        <div class="stat"><div class="n">{n_assets}</div><div class="l">Clinical-stage assets</div></div>
        <div class="stat"><div class="n">{esc(nearest)}</div><div class="l">Nearest catalyst</div></div>
      </div>
    </section>
    {prose_html}
    <div class="assetgrid">{cards}
    </div>
{ADVICE}
    <div class="cta">
      <p>This sponsor's catalysts are a slice of the free CSA sample. The full snapshot spans <b>139 listed sponsors</b> and <b>2,103 forward catalysts</b>.</p>
      <a class="btn primary" href="/#pricing">Get the full dataset &mdash; $499 &rarr;</a>
    </div>
    {related_html}
  </main>
{FOOTER}"""

        page = head(title, desc, url, "website", [ld_collection, ld_crumbs, ld_list]) + "\n" + body
        with open(os.path.join(SPON_DIR, f"{slugify(ticker)}.html"), "w", encoding="utf-8") as f:
            f.write(page)
        sitemap_entries.append((url, os.path.join(SPON_DIR, f"{slugify(ticker)}.html"), "monthly", "0.9"))

    # ---- sitemap ------------------------------------------------------------
    n = write_sitemap(ROOT, sitemap_entries)

    print(f"Generated {len(c_by_asset)} catalyst pages + {len(by_ticker)} sponsor hubs; "
          f"sitemap has {n} URLs.")


if __name__ == "__main__":
    main()
