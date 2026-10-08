"""
generate_seo_pages.py — CSA programmatic-SEO page generator.

Builds static, index-ready landing pages from the free sample so search engines
can surface specific queries (e.g. "mezigdomide phase 3 readout date",
"PFE phase 3 catalysts 2026"):

  - catalysts/<asset>.html   one forward-catalyst detail page per drug asset
  - sponsors/<ticker>.html   one hub page per listed sponsor, grouping its assets
  - catalysts/, sponsors/    the directory hubs (scripts/generate_hubs.py, run from here)
  - index.html               the homepage sample-calendar rows, linked to their pages
  - functions/_middleware.js the active retired-URL redirects (from scripts/redirects.json)
  - sitemap.xml              regenerated with every URL (clean, extensionless), last, so
                             every lastmod sees the pages this run wrote

A catalyst or sponsor page whose asset left the sample is deleted in the same run, so
the page set always equals the sample: never delete these pages by hand. A retired URL
with a true successor (a renamed or merged asset) is listed in scripts/redirects.json;
the generator records the renames its own curation rules make there, and activates a
rule only while its target page exists and its source page does not.

Each page carries full SEO meta (canonical + self-referencing hreflang, OpenGraph),
JSON-LD (Dataset / CollectionPage + BreadcrumbList + ItemList), the CSA
clinical-instrument design, and the "data, not investment advice" notice.

    python scripts/generate_seo_pages.py [--force-prune]

Reads samples/catalyst_calendar_sample.csv + samples/asset_master_sample.csv, and
data/sponsor_summary.json (per-ticker counts from the full snapshot, written by csa-poc
scripts/build_sample.py; optional). No dependencies beyond the standard library.
"""

import csv
import datetime
import html
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seo_common import fit_title, fit_desc, write_sitemap, related_block, DESC_MAX
import generate_hubs

SITE = "https://csa.dataengineered.io"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAL_CSV = os.path.join(ROOT, "samples", "catalyst_calendar_sample.csv")
MAS_CSV = os.path.join(ROOT, "samples", "asset_master_sample.csv")
SUMMARY_JSON = os.path.join(ROOT, "data", "sponsor_summary.json")
REDIRECTS_JSON = os.path.join(ROOT, "scripts", "redirects.json")
MIDDLEWARE_JS = os.path.join(ROOT, "functions", "_middleware.js")
INDEX_HTML = os.path.join(ROOT, "index.html")
CAT_DIR = os.path.join(ROOT, "catalysts")
SPON_DIR = os.path.join(ROOT, "sponsors")

# phase label when the trial record has no phase
NO_PHASE = "clinical"

# Sample curation, mirrored from csa-poc scripts/build_sample.py (_ALIASES, _DOSE_QUALIFIERS,
# _NOT_AN_ASSET_TOKENS, _SAMPLE_BACKBONE): keep both copies in step. samples/ are
# byte-identical copies of the upstream sample, so an edition built before a rule existed
# upstream still carries the rows; applying the same rules here keeps them off the site
# either way. "rina" is the name older editions wrote for "rina s" (its "s" was dropped
# as noise), so it is aliased here too.
_ALIASES = {"rina s": "rinatabart sesutecan", "rina": "rinatabart sesutecan",
            "lorlatanib": "lorlatinib"}
_DOSE_QUALIFIERS = {"higher", "lower", "high", "low"}
_NOT_AN_ASSET_TOKENS = {"rescue", "supportive", "measures", "investigator", "choice",
                        "standard", "lymphodepletion", "placebo", "medication", "medications", "care",
                        "intensity", "chemotherapy"}
_SAMPLE_BACKBONE = {"calcium levofolinate", "levofolinate", "granulocyte colony stimulating factor",
                    "filgrastim", "pegfilgrastim"}

# the homepage sample-calendar rows live between these markers in index.html
TABLE_BEGIN = "<!-- BEGIN:sample-calendar -->"
TABLE_END = "<!-- END:sample-calendar -->"
TABLE_ROWS = 8

# the active redirect map lives between these markers in functions/_middleware.js
REDIRECTS_BEGIN = "// BEGIN:redirects"
REDIRECTS_END = "// END:redirects"

FONTS = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600"
         "&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap")

_SUFFIX = {"plc", "inc", "co", "corp", "llc", "lp", "ltd", "ag", "sa", "nv", "ab",
           "asa", "se", "spa", "as", "kgaa", "pbc", "us", "usa", "nk", "se"}


def slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(text).lower())
    return text.strip("-")


def esc(text) -> str:
    return html.escape(str(text if text is not None else "").strip())


def data(value) -> str:
    """A data value (asset, sponsor, ticker, NCT id, CSV enum, condition, disclosed
    window) inside page copy: translate="no" keeps it verbatim in the localized copies
    made by scripts/i18n_common.py, which translate only the words around it."""
    return f'<span translate="no">{esc(value)}</span>'


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


def format_phase(phase_raw):
    """'PHASE2;PHASE3' -> 'Phase 2/3'; 'PHASE3' -> 'Phase 3'; '' -> ''. Only reformats
    the raw semicolon-delimited value already in the record -- never fabricates or
    drops a phase, and never repeats the 'Phase' word per segment."""
    parts = [p.strip() for p in (phase_raw or "").split(";") if p.strip()]
    if not parts:
        return ""
    nums = [re.sub(r"(?i)^phase\s*", "", p) for p in parts]
    return "Phase " + "/".join(nums)


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


def all_conditions(conditions):
    """Every listed condition, trimmed, in record order."""
    return [c.strip() for c in (conditions or "").split(";") if c.strip()]


def site_asset_name(name):
    """The sample's asset name after the curation rules mirrored from csa-poc, or None
    when the row is a study arm or a standard-of-care backbone rather than a drug asset."""
    n = re.sub(r"\s+", " ", str(name or "")).strip().lower()
    n = _ALIASES.get(n, n)
    toks = [t for t in n.split() if t not in _DOSE_QUALIFIERS]
    if not toks or any(t in _NOT_AN_ASSET_TOKENS for t in toks):
        return None
    n = " ".join(toks)
    return None if n in _SAMPLE_BACKBONE else n


def format_enum(value):
    """'ACTIVE_NOT_RECRUITING' -> 'Active, not recruiting'; 'active_comparator' ->
    'Active comparator'. Display only; the record's own value, reworded."""
    v = (value or "").strip().lower().replace("_", " ")
    v = v.replace("active not recruiting", "active, not recruiting")
    return v[:1].upper() + v[1:]


def ct_link(nct):
    """An NCT id linked to its ClinicalTrials.gov record."""
    nct = (nct or "").strip()
    if not nct:
        return "&mdash;"
    return (f'<a href="https://clinicaltrials.gov/study/{esc(nct)}" target="_blank" rel="noopener" '
            f'style="color:var(--accent)" translate="no">{esc(nct)}</a>')


def trials_table(rows, catalyst_ncts=(), asset_col=None):
    """The trial rows behind an asset (or a sponsor's assets), one row per trial, oldest
    primary completion first. `catalyst_ncts` marks the trials a tracked catalyst comes
    from: NCT ids, or (asset, NCT id) pairs when one table mixes assets. `asset_col` maps an asset name to its page href to add a linked Asset column."""
    trs = []
    for m in rows:
        nct = (m.get("nct_id") or "").strip()
        mark = (' <span class="tag">catalyst</span>'
                if nct in catalyst_ncts or (m.get("asset"), nct) in catalyst_ncts else "")
        conds = "; ".join(all_conditions(m.get("conditions")))
        conds_disp = esc(conds[:90] + ("…" if len(conds) > 90 else "")) if conds else "&mdash;"
        cells = []
        if asset_col is not None:
            a = m["asset"]
            cells.append(f'<td><a href="{esc(asset_col[a])}" style="color:var(--ink)" translate="no">{esc(a)}</a></td>')
        cells += [
            f"<td>{ct_link(nct)}{mark}</td>",
            f'<td translate="no">{esc(format_phase(m.get("phase"))) or "&mdash;"}</td>',
            f'<td translate="no">{esc(format_enum(m.get("status"))) or "&mdash;"}</td>',
            f'<td translate="no">{esc(m.get("primary_completion")) or "&mdash;"}</td>',
            f'<td translate="no">{esc(format_enum(m.get("arm_role"))) or "&mdash;"}</td>',
            f'<td translate="no">{esc(m.get("sponsor_raw")) or "&mdash;"}</td>',
            f'<td class="wrap" title="{esc(conds)}" translate="no">{conds_disp}</td>',
        ]
        trs.append("<tr>" + "".join(cells) + "</tr>")
    head_cells = (["Asset"] if asset_col is not None else []) + [
        "Trial", "Phase", "Status", "Primary completion", "Role", "Lead sponsor", "Condition(s)"]
    ths = "".join(f"<th>{h}</th>" for h in head_cells)
    return (f'<div class="tblwrap"><table class="tbl"><thead><tr>{ths}</tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table></div>')


def by_completion(rows):
    """Trial rows sorted by primary completion (blank last), then NCT id."""
    return sorted(rows, key=lambda m: ((m.get("primary_completion") or "9999"), m.get("nct_id") or ""))


def pad_related(items, pool, index_of, self_key, href_of, label_of, minimum=3):
    """Top up `items` (list of (href, label, reason_or_None)) to at least `minimum`
    entries by walking outward from the record's own position in `pool` (sorted by
    display name), alternating previous/next and wrapping around. Only used when the
    field-based related items fall short -- the padding links are real neighbouring
    records, never invented, just labelled by their (real) adjacency rather than a
    shared field."""
    if len(items) >= minimum:
        return items
    have = {item[0] for item in items}
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
            items.append((href, label_of(cand), "neighbouring record", False))
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
        lbl = format_phase(phase)
        if lbl and lbl not in phases:
            phases.append(lbl)

    nxt = items[0][3]
    window = (nxt.get("event_window") or nxt.get("event_date") or "").strip()
    precision = (nxt.get("date_precision") or "").strip()
    etype = (nxt.get("event_type") or "").strip()

    cat_word = "catalyst" if n_cats == 1 else "catalysts"
    asset_word = "asset" if n_assets == 1 else "assets"
    s1 = f"CSA tracks {n_cats} forward {esc(cat_word)} for {data(company_disp)} across {n_assets} {esc(asset_word)}"
    if phases:
        s1 += f", spanning {', '.join(esc(p) for p in phases)}"
    s1 += "."

    s2 = f"The nearest is a {data(etype.lower())} expected {data(window)}"
    if precision:
        s2 += f" ({data(precision)} precision)"
    s2 += "."

    sentences = [s1, s2]

    conf_counts = Counter((c.get("confidence") or "").strip() for c in all_cats
                          if (c.get("confidence") or "").strip())
    if conf_counts:
        parts = [f"{n} {data(c.lower())}" for c, n in sorted(conf_counts.items(), key=lambda kv: (-kv[1], kv[0]))]
        sentences.append(f"Confidence across its tracked catalysts breaks down as {', '.join(parts)}.")

    indications = []
    for a in all_assets:
        for m in m_by_asset.get(a, []):
            cond = primary_condition(m.get("conditions"))
            if cond and cond not in indications:
                indications.append(cond)
    if indications:
        shown = indications[:3]
        s4 = f"Tracked indications include {', '.join(data(x) for x in shown)}"
        if len(indications) > 3:
            s4 += f", and {len(indications) - 3} more"
        s4 += "."
        sentences.append(s4)

    # one <span> per sentence: each optional clause is its own translation segment
    body = " ".join(f"<span>{x}</span>" for x in sentences)
    return f'<p class="sub" style="margin-top:20px;max-width:74ch;line-height:1.7;color:var(--ink-2);">{body}</p>'


def catalyst_prose(asset, cats, nxt, ticker, company_disp, phase_lbl, status, conditions, nct, etype, mrows):
    """Unique, data-derived summary of an asset's forward catalyst + trial context."""
    n = len(cats)
    trials = len({(m.get("nct_id") or "").strip() for m in mrows if (m.get("nct_id") or "").strip()})
    window = (nxt.get("event_window") or nxt.get("event_date") or "").strip()
    precision = (nxt.get("date_precision") or "").strip()
    conf = (nxt.get("confidence") or "").strip()
    # no "clinical-stage": many tracked assets are already approved and in Phase 3 for a
    # new indication, and the sample carries no approval status to tell them apart
    sentences = [f"{data(asset)} is a drug asset sponsored by {data(company_disp)}, "
                 f"listed as {data(ticker)}."]
    cat_word = "catalyst" if n == 1 else "catalysts"
    p = f"CSA tracks {n} forward {cat_word} for it — the nearest is a {data(etype.lower())} expected {data(window)}"
    extras = []
    if precision:
        extras.append(f"{data(precision)} precision")
    if conf:
        extras.append(f"{data(conf)} confidence")
    if extras:
        p += f" ({', '.join(extras)})"
    if nct:
        p += f", tied to trial {data(nct)}"
    p += "."
    sentences.append(p)
    detail = []
    if phase_lbl and phase_lbl != NO_PHASE:
        detail.append(f"in {esc(phase_lbl)}")
    if status:
        detail.append(f"currently {data(status.lower().replace('_', ' '))}")
    if detail:
        # phase and status belong to the catalyst's trial, not to the asset (an approved
        # drug can be in a Phase 3 trial for a new indication)
        s = f"{'That trial' if nct else 'Its catalyst trial'} is {' and '.join(detail)}"
        if conditions:
            cond = conditions.split(";")[0].strip() if ";" in conditions else conditions
            s += f", studying {data(cond[:120])}"
        s += "."
        sentences.append(s)
    if trials > 1:
        sentences.append(f"It appears across {trials} tracked trials in the CSA sample.")
    # one <span> per sentence: each optional clause is its own translation segment
    body = " ".join(f"<span>{x}</span>" for x in sentences)
    return f'<p class="sub" style="margin-top:20px;max-width:74ch;line-height:1.7;color:var(--ink-2);">{body}</p>'


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
.tblwrap{overflow-x:auto;margin-top:8px}
.tblwrap .tbl{margin-top:0}
.tblwrap .tbl td{white-space:nowrap}
.tbl td.wrap{white-space:normal;min-width:180px}
.tag{font-family:var(--font-mono);font-size:.56rem;text-transform:uppercase;letter-spacing:.08em;color:var(--accent);border:1px solid rgba(43,179,168,.4);border-radius:3px;padding:1px 5px;margin-left:6px;vertical-align:middle}
.note{color:var(--ink-3);font-size:.84rem;margin-top:12px}
.note a{color:var(--accent);text-decoration:none}
.note a:hover{text-decoration:underline}
.chips{display:flex;flex-wrap:wrap;gap:7px;margin-top:4px}
.chip{font-size:.8rem;color:var(--ink-2);border:1px solid var(--line);border-radius:4px;padding:3px 8px}
.full .statbar{margin-top:6px}
@media(max-width:600px){.full .statbar{grid-template-columns:repeat(3,1fr);gap:8px}.full .stat{padding:12px 4px}.full .stat .n{font-size:1.2rem}}
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
      <div class="catalog-line" style="text-align:center; margin-top:14px; font-size:0.85rem; opacity:0.85;"><a href="https://dataengineered.io/">Part of the DataEngineered catalog &rarr;</a> &middot; <a href="https://dataengineered.io/about">About</a> &middot; <a href="https://dataengineered.io/terms">Terms</a> &middot; <a href="https://dataengineered.io/privacy">Privacy</a> &middot; <a href="https://dataengineered.io/refund-policy">Refund policy</a></div>
    </div>
  </footer>
</body>
</html>"""

# The per-page call to action states the snapshot's scope, never its counts: a count in
# every page changed all of them (and their sitemap lastmod) at each monthly edition. The
# headline counts live once, on the homepage, which the edition update already edits.
SCOPE_LINE = ("The full snapshot covers active, industry-sponsored Phase 3 trials in "
              "cardiometabolic, oncology and immunology. Every forward catalyst carries its date, "
              "confidence grade and source link, and is linked to its sponsor's ticker when the "
              "sponsor is a listed company.")


def load_sponsor_summary():
    """data/sponsor_summary.json -> (as_of, {ticker: counts}); ("", {}) when absent."""
    if not os.path.isfile(SUMMARY_JSON):
        return "", {}
    with open(SUMMARY_JSON, encoding="utf-8") as f:
        doc = json.load(f)
    return str(doc.get("as_of") or ""), doc.get("sponsors") or {}


def full_snapshot_panel(company_disp, ticker, counts):
    """The sponsor's footprint in the full (paid) snapshot: counts only, from
    data/sponsor_summary.json. Empty when the ticker has no entry. The edition date is
    left out on purpose: it would change every sponsor page each month, where these
    counts change only when the sponsor's own footprint does."""
    if not counts:
        return ""
    stats = []
    for key, one, many in (("forward_catalysts", "Forward catalyst", "Forward catalysts"),
                           ("assets", "Asset", "Assets"), ("trials", "Trial", "Trials")):
        v = counts.get(key)
        if isinstance(v, int) and v > 0:
            stats.append(f'<div class="stat"><div class="n">{v}</div><div class="l">{one if v == 1 else many}</div></div>')
    years = counts.get("catalysts_by_year") or {}
    year_chips = "".join(f'<span class="chip"><span translate="no">{esc(y)}</span> &middot; {int(n)}</span>'
                         for y, n in sorted(years.items()))
    year_html = (f'<p class="note" style="margin-top:16px">Forward catalysts by year</p>'
                 f'<div class="chips">{year_chips}</div>') if year_chips else ""
    return f"""
      <div class="card full" style="margin-top:22px">
        <h3>{data(ticker)} in the full snapshot</h3>
        <p class="k">The free sample on this page is a slice. In the current full CSA snapshot, {data(company_disp)} has:</p>
        <div class="statbar">{"".join(stats)}</div>
        {year_html}
        <p class="note">Every catalyst in the snapshot comes with its date, date confidence and source link.</p>
      </div>"""


def panel_counts(full, n_cats, n_assets, n_trials, years):
    """`full` when it can sit next to this sample without contradicting it, else {}. The
    summary and the sample are copied together each edition, but a full-snapshot count
    below the sample's own (in total, per year or in trials) would read as the slice being
    bigger than the whole, so the panel is left out until they agree."""
    if not full:
        return {}
    fy = full.get("catalysts_by_year") or {}
    short = [k for k, v in (("forward_catalysts", n_cats), ("assets", n_assets), ("trials", n_trials))
             if full.get(k, 0) < v]
    short += [f"{y} catalysts" for y, n in sorted(years.items()) if fy.get(y, 0) < n]
    return {} if short else full


def load_redirects():
    """scripts/redirects.json as {old path: new path}. A missing file while the middleware
    still serves redirects means the record was lost: stop rather than silently drop them."""
    if os.path.isfile(REDIRECTS_JSON):
        with open(REDIRECTS_JSON, encoding="utf-8") as f:
            return json.load(f)
    with open(MIDDLEWARE_JS, encoding="utf-8") as f:
        js = f.read()
    m = re.search(r"const REDIRECTS = (\{.*?\});", js, re.S)
    if m and json.loads(m.group(1)):
        sys.exit(f"{REDIRECTS_JSON} is missing but {MIDDLEWARE_JS} serves redirects; restore it from git")
    return {}


def write_redirects(rules, renames, generated_paths):
    """Record this run's curation `renames` ({old path: new path}) in `rules` (from
    scripts/redirects.json; the current run wins over an older rule, and a reversed pair
    replaces its opposite), save them, and write the active ones into
    functions/_middleware.js. Rules are stored as recorded; chains are followed only when
    activating: a rule is active while its source is not a page this run wrote and its
    chain reaches one that is. Returns (active, inactive)."""
    rules = dict(rules)
    for old, new in renames.items():
        rules[old] = new
        if rules.get(new) == old:
            del rules[new]
    rules = {s: t for s, t in rules.items() if s != t}
    with open(REDIRECTS_JSON, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(dict(sorted(rules.items())), indent=1) + "\n")

    active = {}
    for src in sorted(rules):
        if src in generated_paths:
            continue
        seen, tgt = {src}, rules[src]
        while tgt not in generated_paths and tgt in rules and tgt not in seen:
            seen.add(tgt)
            tgt = rules[tgt]
        if tgt in generated_paths and tgt != src:
            active[src] = tgt
    inactive = {s: t for s, t in sorted(rules.items()) if s not in active}
    with open(MIDDLEWARE_JS, encoding="utf-8") as f:
        js = f.read()
    start, end = js.find(REDIRECTS_BEGIN), js.find(REDIRECTS_END)
    line_end = js.index("\n", start) + 1  # keep the BEGIN line (and its comment) as written
    block = "const REDIRECTS = " + json.dumps(active, indent=2) + ";\n"
    with open(MIDDLEWARE_JS, "w", encoding="utf-8", newline="\n") as f:
        f.write(js[:line_end] + block + js[end:])
    return active, inactive


def stale_pages(directory, planned, force):
    """The *.html pages in `directory` (index.html, the hub, aside) that this run will not
    write. Refuses, unless forced, when that is more than a third of the pages there before
    the run: a broken or truncated sample must not wipe the site. Called before any page
    is written, so a refusal leaves the site untouched."""
    existing = sorted(f for f in os.listdir(directory) if f.endswith(".html") and f != "index.html")
    stale = [f for f in existing if f not in planned]
    if existing and len(stale) > len(existing) / 3 and not force:
        sys.exit(f"refusing to delete {len(stale)} of {len(existing)} pages in {directory} "
                 f"(more than a third); check the sample, or rerun with --force-prune")
    return stale


def check_markers():
    """Exit before anything is written when a generated block has lost its markers."""
    for path, begin, end in ((MIDDLEWARE_JS, REDIRECTS_BEGIN, REDIRECTS_END),
                             (INDEX_HTML, TABLE_BEGIN, TABLE_END)):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        start, stop = text.find(begin), text.find(end)
        if start < 0 or stop < start:
            sys.exit(f"{path}: missing the {begin} / {end} markers")


def update_homepage_table(asset_meta, today, horizon):
    """Rewrite the homepage sample-calendar rows from the sample: each tracked asset's
    nearest catalyst on or after `horizon` (a month past the run, so the rows stay ahead
    of the calendar until the next edition regenerates them; on or after `today` if that
    leaves too few), TABLE_ROWS of them spread across the whole date range (one per
    ticker where possible), each linked to its catalyst and sponsor page. Every cell is a
    data value (translate="no"), so the localized homepages need no new translations."""
    def nearest_from(day):
        rows = []
        for asset, meta in asset_meta.items():
            nxt = next((c for c in meta["cats"] if c["event_date"] >= day), None)
            if nxt:
                rows.append((nxt["event_date"], asset, nxt, meta))
        return sorted(rows, key=lambda x: (x[0], x[1]))

    upcoming = nearest_from(horizon)
    if len(upcoming) < TABLE_ROWS:
        upcoming = nearest_from(today)
    if not upcoming:
        sys.exit("no upcoming catalyst in the sample for the homepage table")
    k = min(TABLE_ROWS, len(upcoming))
    picks, tickers = [], set()
    for i in range(k):
        want = round(i * (len(upcoming) - 1) / (k - 1)) if k > 1 else 0
        # nearest not-yet-picked row to the evenly spaced position, preferring a new ticker
        order = sorted(range(len(upcoming)), key=lambda j: (abs(j - want), j))
        cand = [j for j in order if j not in picks]
        j = next((j for j in cand if upcoming[j][3]["ticker"] not in tickers), cand[0])
        picks.append(j)
        tickers.add(upcoming[j][3]["ticker"])
    rows = []
    for j in sorted(picks):
        date, asset, nxt, meta = upcoming[j]
        etype = (nxt.get("event_type") or "").strip()
        pill = "pdufa" if etype.upper() == "PDUFA" else "readout"
        label = etype.upper() if etype.upper() == "PDUFA" else etype.title()
        rows.append(
            f'            <tr><td class="mono" translate="no">{esc(date)}</td>'
            f'<td><a class="tk" href="/sponsors/{slugify(meta["ticker"])}" translate="no">{esc(meta["ticker"])}</a></td>'
            f'<td translate="no"><a class="asset" href="/catalysts/{meta["slug"]}">{esc(asset)}</a></td>'
            f'<td><span class="pill {pill}" translate="no">{esc(label)}</span></td>'
            f'<td class="mono" translate="no">{esc(nxt.get("event_window") or date)}</td>'
            f'<td class="conf" translate="no">{esc(nxt.get("confidence"))}</td></tr>')
    with open(INDEX_HTML, encoding="utf-8") as f:
        src = f.read()
    start, end = src.find(TABLE_BEGIN), src.find(TABLE_END)
    if start < 0 or end < start:
        sys.exit(f"index.html: missing the {TABLE_BEGIN} / {TABLE_END} markers")
    src = src[:start + len(TABLE_BEGIN)] + "\n" + "\n".join(rows) + "\n            " + src[end:]
    with open(INDEX_HTML, "w", encoding="utf-8", newline="") as f:
        f.write(src)
    return len(rows)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    force_prune = "--force-prune" in argv
    # "today" decides which catalysts are still forward; CSA_AS_OF=YYYY-MM-DD pins it
    try:
        today_d = datetime.date.fromisoformat(os.environ.get("CSA_AS_OF") or datetime.date.today().isoformat())
    except ValueError:
        sys.exit(f"CSA_AS_OF must be YYYY-MM-DD, got {os.environ.get('CSA_AS_OF')!r}")
    today = today_d.isoformat()
    os.makedirs(CAT_DIR, exist_ok=True)
    os.makedirs(SPON_DIR, exist_ok=True)

    with open(CAL_CSV, encoding="utf-8") as f:
        cal_raw = [r for r in csv.DictReader(f) if r.get("asset") and r.get("ticker")]
    with open(MAS_CSV, encoding="utf-8") as f:
        master_raw = [r for r in csv.DictReader(f) if r.get("asset")]
    if not cal_raw:
        sys.exit(f"{CAL_CSV} has no catalyst rows")

    # curation (site_asset_name): drop study arms and backbones, merge dose arms, fix
    # names. `renamed` keeps raw -> curated so the old page URL can redirect.
    renamed, dropped = {}, set()

    def curate(rows):
        out = []
        for r in rows:
            name = site_asset_name(r["asset"])
            if name is None:
                dropped.add(r["asset"])
                continue
            if name != r["asset"]:
                renamed[r["asset"]] = name
            out.append(dict(r, asset=name))
        return out

    cal, master = curate(cal_raw), curate(master_raw)
    # forward catalysts only: a date that has passed is no longer "next" or "expected"
    # (an asset left with none is retired below like any other that left the sample)
    past = [c for c in cal if c["event_date"] < today]
    cal = [c for c in cal if c["event_date"] >= today]

    # master rows grouped by asset (for trial/sponsor enrichment), one per trial: the
    # sample repeats an asset-trial pair once per arm, and a merged dose arm repeats it
    # again; the first row is the one the pages always used
    m_by_asset = defaultdict(list)
    seen_trials = set()
    for m in master:
        key = (m["asset"], (m.get("nct_id") or "").strip())
        if key in seen_trials:
            continue
        seen_trials.add(key)
        m_by_asset[m["asset"]].append(m)

    # catalysts grouped by asset; a merged dose arm can repeat the same catalyst
    c_by_asset = defaultdict(list)
    seen_cats = set()
    for c in cal:
        key = (c["asset"], c["event_date"], c.get("event_type"), c.get("nct_id"))
        if key in seen_cats:
            continue
        seen_cats.add(key)
        c_by_asset[c["asset"]].append(c)

    # trial -> the tracked assets in it (pages link the others as co-studied assets)
    assets_by_nct = defaultdict(set)
    for a, rows in m_by_asset.items():
        if a in c_by_asset:
            for m in rows:
                if (m.get("nct_id") or "").strip():
                    assets_by_nct[m["nct_id"].strip()].add(a)
    # every tracked asset needs its trial rows; a truncated asset_master would silently
    # strip the trial, sponsor and condition content from every page
    missing = sorted(set(c_by_asset) - set(m_by_asset))
    if not c_by_asset or len(missing) > 0.1 * len(c_by_asset):
        sys.exit(f"{MAS_CSV}: {len(missing)} of {len(c_by_asset)} tracked assets have no trial rows; "
                 f"check the sample")
    summary_as_of, summary = load_sponsor_summary()

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
        phase_lbl = format_phase(phase) if phase else NO_PHASE
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

    # ---- every check before the first write ----------------------------------
    planned_cat = {f"{m['slug']}.html" for m in asset_meta.values()}
    planned_spon = {f"{slugify(m['ticker'])}.html" for m in asset_meta.values()}
    stale_cat = stale_pages(CAT_DIR, planned_cat, force_prune)
    stale_spon = stale_pages(SPON_DIR, planned_spon, force_prune)
    check_markers()
    rules = load_redirects()

    # ---- asset detail pages -------------------------------------------------
    written_cat, written_spon = set(), set()
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
        if phase_lbl and phase_lbl != NO_PHASE:
            desc_tail.append(phase_lbl)
        desc_tail.append(f"sponsored by {company_disp}" if company_disp == ticker
                          else f"sponsored by {company_disp} ({ticker})")
        if confidence:
            desc_tail.append(f"{confidence} confidence")
        # Reserve room for the disclaimer suffix so fit_desc's cut never lands
        # inside it (it was truncating mid-word, or dropping it outright).
        suffix = " Not investment advice."
        desc_text = f"{etype.lower()} for {asset} expected {window}, {', '.join(desc_tail)}."
        desc = esc(fit_desc(desc_text, DESC_MAX - len(suffix)) + suffix)

        # related: reciprocal link to the sponsor, up to 2 same-indication assets,
        # up to 2 same-quarter-readout assets, capped at 5, padded to >=3 with
        # real name-order neighbours if the CSV doesn't offer enough matches, then
        # the catalyst directory hub.
        related_items = [(f"../sponsors/{slugify(ticker)}", f"{company_disp} ({ticker})", "sponsor", False)]
        used_assets = {asset}
        cond = meta["condition"]
        added = 0
        if cond:
            for a2, m2 in asset_meta.items():
                if added >= 2:
                    break
                if a2 in used_assets or m2["condition"].lower() != cond.lower():
                    continue
                related_items.append((f"../catalysts/{m2['slug']}", a2, m2["condition"], False))
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
                related_items.append((f"../catalysts/{m2['slug']}", a2, q, False))
                used_assets.add(a2)
                added += 1
        related_items = related_items[:5]
        related_items = pad_related(related_items, assets_by_name, asset_pos, asset,
                                     lambda a2: f"../catalysts/{asset_meta[a2]['slug']}", lambda a2: a2)
        related_items.append(("../catalysts/", "All tracked catalysts", None))
        related_html = related_block(related_items, "Related catalysts and sponsor", limit=None)
        # a shared-indication reason is a condition name (data), not site copy
        for _h, _l, why, *_ in related_items:
            if why and why not in ("sponsor", "neighbouring record") and not re.fullmatch(r"Q\d \d{4}", why):
                related_html = related_html.replace(
                    f'<span class="related-why">— {html.escape(why)}</span>',
                    f'<span class="related-why">— <span translate="no">{html.escape(why)}</span></span>')

        ct = nxt.get("event_type", ""); cd = nxt.get("event_date", "")
        ld_dataset = {
            "@context": "https://schema.org", "@type": "Dataset",
            "name": f"{asset} ({ticker}) forward catalyst record",
            "description": (f"Forward clinical/regulatory catalyst for {asset}, "
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
                f"<tr><td>{esc(c['event_date'])}</td><td translate=\"no\">{esc(c.get('event_type'))}</td>"
                f"<td translate=\"no\">{esc(c.get('confidence'))}</td>"
                f"<td><a href=\"{esc(c.get('source_url'))}\" target=\"_blank\" rel=\"noopener\" style=\"color:var(--accent)\" translate=\"no\">{esc(c.get('nct_id'))}</a></td></tr>"
                for c in cats)
            rows_html = f"""
      <div class="card" style="margin-top:22px">
        <h3>All tracked catalysts for {data(asset)}</h3>
        <div class="tblwrap"><table class="tbl"><thead><tr><th>Date</th><th>Event</th><th>Confidence</th><th>Trial</th></tr></thead>
        <tbody>{trs}</tbody></table></div>
      </div>"""

        # every trial the sample links to this asset, not just the catalyst's own: shown
        # when there is more than the one trial the cards above already describe
        cat_ncts = {(c.get("nct_id") or "").strip() for c in cats}
        trials_html = ""
        if len(mrows) > 1:
            trials_html = f"""
      <div class="card" style="margin-top:22px">
        <h3>Trials for {data(asset)} in the CSA sample</h3>
        {trials_table(by_completion(mrows), cat_ncts)}
        <p class="note">Each trial links to its ClinicalTrials.gov record; primary completion dates are as registered there.</p>
      </div>"""
        # other tracked assets studied in the same trials (combinations, multi-drug studies)
        co = []
        for m in by_completion(mrows):
            nct_m = (m.get("nct_id") or "").strip()
            others = sorted(assets_by_nct.get(nct_m, set()) - {asset})
            if others:
                links = ", ".join(f'<a href="../catalysts/{asset_meta[o]["slug"]}" translate="no">{esc(o)}</a>' for o in others)
                co.append(f"<span>{data(nct_m)}: {links}</span>")
        co_html = (f'\n    <p class="note">Other tracked assets in the same trials &mdash; {"; ".join(co)}.</p>'
                   if co else "")

        cond_disp = esc(conditions[:160] + ("…" if len(conditions) > 160 else "")) if conditions else "&mdash;"
        body = f"""<body>
{NAV}
  <main class="container">
    <div class="crumbs"><a href="/">Home</a> / <a href="../sponsors/{slugify(ticker)}" translate="no">{esc(company_disp)} ({esc(ticker)})</a> / <span translate="no">{esc(asset)}</span></div>
    <section class="hero">
      <span class="eyebrow">Forward catalyst &middot; {data(ticker)}</span>
      <h1 translate="no">{esc(asset)}</h1>
      <p class="sub">Sponsor <b translate="no">{esc(company_disp)}</b> &middot; listed as <b translate="no">{esc(ticker)}</b></p>
      <div class="badges">
        <span class="badge accent" translate="no">{esc(etype)}</span>
        <span class="badge">{esc(phase_lbl)}</span>
        <span class="badge">Confidence: {data(nxt.get('confidence'))}</span>
        <span class="badge">Source: {data(nxt.get('source'))}</span>
      </div>
    </section>
    {catalyst_prose(asset, cats, nxt, ticker, company_disp, phase_lbl, status, conditions, nct, etype, mrows)}
    <div class="grid2">
      <div class="card">
        <h3>Next catalyst</h3>
        <div class="row"><span class="k">Event type</span><span class="v accent" translate="no">{esc(etype)}</span></div>
        <div class="row"><span class="k">Expected date</span><span class="v" translate="no">{esc(nxt.get('event_date'))}</span></div>
        <div class="row"><span class="k">As disclosed</span><span class="v" translate="no">{esc(nxt.get('event_window'))}</span></div>
        <div class="row"><span class="k">Date precision</span><span class="v" translate="no">{esc(nxt.get('date_precision'))}</span></div>
        <div class="row"><span class="k">Confidence</span><span class="v" translate="no">{esc(nxt.get('confidence'))}</span></div>
        <div style="margin-top:18px">
          <a class="btn" href="{esc(nxt.get('source_url'))}" target="_blank" rel="noopener">Verify at source &rarr;</a>
        </div>
      </div>
      <div class="card">
        <h3>Trial &amp; sponsor</h3>
        <div class="row"><span class="k">Trial (NCT)</span><span class="v" translate="no">{esc(nct) or '&mdash;'}</span></div>
        <div class="row"><span class="k">Phase</span><span class="v" translate="no">{esc(phase) or '&mdash;'}</span></div>
        <div class="row"><span class="k">Status</span><span class="v" translate="no">{esc(status) or '&mdash;'}</span></div>
        <div class="row"><span class="k">Lead sponsor</span><span class="v" translate="no">{esc(mrow.get('sponsor_raw')) or '&mdash;'}</span></div>
        <div class="row"><span class="k">Listed as</span><span class="v accent" translate="no">{esc(ticker)}</span></div>
        <div class="row"><span class="k">Condition(s)</span><span class="v" style="max-width:58%" translate="no">{cond_disp}</span></div>
      </div>
    </div>{co_html}
{rows_html}{trials_html}
{ADVICE}
    <div class="cta">
      <p>This page is one record from the free CSA sample. {SCOPE_LINE}</p>
      <a class="btn primary" href="/#pricing">Get the full dataset &mdash; $499 &rarr;</a>
      &nbsp;
      <a class="btn" href="../sponsors/{slugify(ticker)}">More {data(ticker)} catalysts</a>
    </div>
    {related_html}
  </main>
{FOOTER}"""

        page = head(title, desc, url, "article", [ld_dataset, ld_crumbs]) + "\n" + body
        with open(os.path.join(CAT_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
            f.write(page)
        written_cat.add(f"{slug}.html")
        sitemap_entries.append((url, os.path.join(CAT_DIR, f"{slug}.html"), "monthly", "0.8"))

    # ---- sponsor pass 1: precompute every sponsor's metadata up front, for the
    # same reason as the asset pass 1 above (related blocks need to compare one
    # sponsor's fields against every other sponsor's) --------------------------
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

    # every condition each sponsor's tracked assets are studied in (case-folded key ->
    # first spelling seen), for the indication list and the same-indication sponsor links
    sponsor_conditions = {}
    for ticker, smeta in sponsor_meta.items():
        conds = {}
        for a, *_ in smeta["items"]:
            for m in m_by_asset.get(a, []):
                for cnd in all_conditions(m.get("conditions")):
                    conds.setdefault(cnd.lower(), cnd)
        sponsor_conditions[ticker] = conds

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
                                   ["catalysts & pipeline", "catalysts"], "CSA"))
        used_sponsor_titles.add(title)

        phases = []
        for _a, _slug, _c, _nxt, phase in items:
            lbl = format_phase(phase)
            if lbl and lbl not in phases:
                phases.append(lbl)
        cat_word = "catalyst" if n_cats == 1 else "catalysts"
        asset_word = "asset" if n_assets == 1 else "assets"
        desc_raw = f"{n_cats} forward {cat_word} tracked for {company_disp} ({ticker}) across {n_assets} {asset_word}"
        if phases:
            desc_raw += f" in {', '.join(phases)}"
        desc_raw += f", nearest readout {nearest}."
        # Reserve room for the disclaimer suffix so fit_desc's cut never lands
        # inside it (it was truncating mid-word, or dropping it outright).
        suffix = " Not investment advice."
        desc = esc(fit_desc(desc_raw, DESC_MAX - len(suffix)) + suffix)

        prose_html = sponsor_prose(company_disp, ticker, items, c_by_asset, m_by_asset)

        # related: every one of this sponsor's own catalysts (uncapped, per the
        # brief), up to 3 sponsors with a tracked trial in one of the same conditions,
        # up to 2 sponsors with a readout in the same quarter, padded to >=3 with real
        # name-order neighbours if needed, then the sponsor hub.
        related_items = [(f"../catalysts/{slug2}", a2, (format_phase(phase2) or None), False)
                          for a2, slug2, _c2, _n2, phase2 in items]
        used_tickers = {ticker}
        own_conds = sponsor_conditions[ticker]
        shared = []
        for t2 in sponsors_by_name:
            if t2 == ticker:
                continue
            common = sorted(set(own_conds) & set(sponsor_conditions[t2]))
            if common:
                shared.append((-len(common), sponsor_pos[t2], t2, own_conds[common[0]]))
        for _n, _p, t2, cond in sorted(shared)[:3]:
            related_items.append((f"../sponsors/{slugify(t2)}", f"{sponsor_meta[t2]['company_disp']} ({t2})", cond, False))
            used_tickers.add(t2)
        q = smeta["quarter"]
        added = 0
        if q:
            for t2, sm2 in sponsor_meta.items():
                if added >= 2:
                    break
                if t2 in used_tickers or sm2["quarter"] != q:
                    continue
                related_items.append((f"../sponsors/{slugify(t2)}", f"{sm2['company_disp']} ({t2})", q, False))
                used_tickers.add(t2)
                added += 1
        related_items = pad_related(related_items, sponsors_by_name, sponsor_pos, ticker,
                                     lambda t2: f"../sponsors/{slugify(t2)}",
                                     lambda t2: f"{sponsor_meta[t2]['company_disp']} ({t2})")
        related_items.append(("../sponsors/", "All sponsors", None))
        related_html = related_block(related_items, "Related sponsors and catalysts", limit=None)
        # a shared-condition reason is a condition name (data), not site copy
        for _h, _l, why, *_ in related_items:
            if why and not re.fullmatch(r"Q\d \d{4}", why) and why not in ("neighbouring record",) \
                    and not why.startswith("Phase "):
                related_html = related_html.replace(
                    f'<span class="related-why">— {html.escape(why)}</span>',
                    f'<span class="related-why">— <span translate="no">{html.escape(why)}</span></span>')

        # the trials behind this sponsor's tracked assets, and every condition they cover
        spon_rows = by_completion([dict(m, asset=a) for a, *_ in items for m in m_by_asset.get(a, [])])
        # (asset, trial) pairs: a trial can hold one asset's catalyst and another's comparator arm
        spon_ncts = {(a, (c.get("nct_id") or "").strip()) for a, *_ in items for c in c_by_asset[a]}
        asset_hrefs = {a: f"../catalysts/{slug2}" for a, slug2, *_ in items}
        n_trials = len({(m.get("nct_id") or "").strip() for m in spon_rows})
        trial_word = "trial" if n_trials == 1 else "trials"
        other_sponsor = any((m.get("ticker") or "").strip() != ticker for m in spon_rows)
        comparator = any((m.get("arm_role") or "").strip() != "experimental" for m in spon_rows)
        trials_scope = (", including trials another sponsor runs and trials where the asset is not the experimental arm"
                        if other_sponsor and comparator else
                        ", including trials another sponsor runs" if other_sponsor else
                        ", including trials where the asset is not the experimental arm" if comparator else "")
        spon_trials_html = f"""
      <div class="card" style="margin-top:22px">
        <h3>{n_trials} {trial_word} behind these assets</h3>
        {trials_table(spon_rows, spon_ncts, asset_col=asset_hrefs)}
        <p class="note">Every trial the CSA sample links to {data(ticker)}'s tracked assets{trials_scope}.</p>
      </div>""" if spon_rows else ""
        cond_names = list(own_conds.values())
        indications_html = (f"""
      <div class="card" style="margin-top:22px">
        <h3>Conditions studied</h3>
        <div class="chips">{"".join(f'<span class="chip" translate="no">{esc(cnd)}</span>' for cnd in cond_names[:40])}</div>{f'<p class="note">and {len(cond_names) - 40} more.</p>' if len(cond_names) > 40 else ""}
      </div>""") if cond_names else ""
        # the summary can be a newer edition than the sample; a full-snapshot count below
        # the sample's own would read as a contradiction, so the panel waits for the sync
        years = Counter(c["event_date"][:4] for a, *_ in items for c in c_by_asset[a])
        full = panel_counts(summary.get(ticker) or {}, n_cats, n_assets, n_trials, years)
        if summary.get(ticker) and not full:
            print(f"note: {ticker} full-snapshot panel skipped: data/sponsor_summary.json "
                  f"({summary_as_of}) counts are below this sample's own; copy both from one edition")
        full_html = full_snapshot_panel(company_disp, ticker, full)

        cards = ""
        for asset, slug, _c, nxt, phase in items:
            phase_lbl = format_phase(phase) or NO_PHASE
            cards += f"""
        <div class="acard">
          <a class="name" href="../catalysts/{slug}" translate="no">{esc(asset)}</a>
          <div class="meta"><span>{data(nxt.get('event_type'))} &middot; {esc(phase_lbl)}</span><span>{esc(nxt.get('event_date'))}</span></div>
        </div>"""

        ld_collection = {
            "@context": "https://schema.org", "@type": "CollectionPage",
            "name": f"{company_disp} ({ticker}) — forward catalysts",
            "description": (f"Forward trial catalysts for listed sponsor {company_disp} ({ticker}): "
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
    <div class="crumbs"><a href="/">Home</a> / <span translate="no">{esc(company_disp)} ({esc(ticker)})</span></div>
    <section class="hero">
      <span class="eyebrow">Sponsor pipeline &middot; {data(ticker)}</span>
      <h1 translate="no">{esc(company_disp)}</h1>
      <p class="sub">Forward trial catalysts linked to <b translate="no">{esc(ticker)}</b></p>
      <div class="statbar">
        <div class="stat"><div class="n">{n_cats}</div><div class="l">Tracked catalysts (sample)</div></div>
        <div class="stat"><div class="n">{n_assets}</div><div class="l">Tracked assets (sample)</div></div>
        <div class="stat"><div class="n">{esc(nearest)}</div><div class="l">Nearest catalyst</div></div>
      </div>
    </section>
    {prose_html}
    <div class="assetgrid">{cards}
    </div>
{full_html}{spon_trials_html}{indications_html}
{ADVICE}
    <div class="cta">
      <p>This sponsor's catalysts are a slice of the free CSA sample. {SCOPE_LINE}</p>
      <a class="btn primary" href="/#pricing">Get the full dataset &mdash; $499 &rarr;</a>
    </div>
    {related_html}
  </main>
{FOOTER}"""

        page = head(title, desc, url, "website", [ld_collection, ld_crumbs, ld_list]) + "\n" + body
        with open(os.path.join(SPON_DIR, f"{slugify(ticker)}.html"), "w", encoding="utf-8") as f:
            f.write(page)
        written_spon.add(f"{slugify(ticker)}.html")
        sitemap_entries.append((url, os.path.join(SPON_DIR, f"{slugify(ticker)}.html"), "monthly", "0.9"))

    # ---- retire pages whose asset or sponsor left the sample ------------------
    for directory, stale in ((CAT_DIR, stale_cat), (SPON_DIR, stale_spon)):
        for f in stale:
            os.remove(os.path.join(directory, f))
    retired = [f"catalysts/{f}" for f in stale_cat] + [f"sponsors/{f}" for f in stale_spon]

    # ---- redirects: renames made by the curation rules, plus scripts/redirects.json --
    generated_paths = ({"/", "/catalysts/", "/sponsors/"}
                       | {f"/catalysts/{f[:-5]}" for f in written_cat}
                       | {f"/sponsors/{f[:-5]}" for f in written_spon})
    renames = {f"/catalysts/{slugify(raw)}": f"/catalysts/{asset_meta[new]['slug']}"
               for raw, new in renamed.items()
               if new in asset_meta and slugify(raw) != asset_meta[new]["slug"]}
    active, inactive = write_redirects(rules, renames, generated_paths)

    # ---- hubs and homepage, then the sitemap last so its lastmod sees them -----
    counts = {sec["slug"]: generate_hubs.build_section(sec) for sec in generate_hubs.SECTIONS}
    generate_hubs.update_homepage(counts)
    horizon = (today_d + datetime.timedelta(days=35)).isoformat()
    n_rows = update_homepage_table(asset_meta, today, horizon)
    n = write_sitemap(ROOT, sitemap_entries)

    print(f"Generated {len(c_by_asset)} catalyst pages + {len(by_ticker)} sponsor hubs; "
          f"sitemap has {n} URLs.")
    if past:
        print(f"skipped {len(past)} catalyst row(s) dated before {today}")
    if dropped:
        print(f"curation dropped {len(dropped)} non-asset name(s): {', '.join(sorted(dropped))}")
    if renamed:
        print("curation renamed: " + ", ".join(f"{a} -> {b}" for a, b in sorted(renamed.items())))
    print(f"retired {len(retired)} page(s)" + (f": {', '.join(retired)}" if retired else ""))
    print(f"redirects: {len(active)} active, {len(inactive)} inactive (target gone or source back)")
    print(f"hubs: {counts['catalysts']} catalysts, {counts['sponsors']} sponsors; "
          f"homepage table: {n_rows} rows (upcoming as of {today})")


if __name__ == "__main__":
    main()
