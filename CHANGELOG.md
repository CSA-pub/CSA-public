# Changelog

All notable changes to the CSA (Clinical-Stage Asset Intelligence) snapshots.

> The dataset is refreshed monthly, so live figures move between snapshots. A
> count-claim gate asserts the corpus counts against the shopfront on every build,
> so the advertised numbers and the shipped data can never silently diverge.

## Site update — 2026-10-08

Fixes for the Google Search Console page-indexing report (697 URLs "Discovered – currently not indexed", 40 "Crawled – currently not indexed", 17 "Not found (404)"), shipped with edition 2026.10 below.

- **Translated pages trimmed to the homepage and the 404 page.** The catalyst, sponsor and directory pages were also published in Spanish, German, French and Brazilian Portuguese: 628 of the sitemap's 790 URLs, on a domain live since 2026-09-05. They are English-only now, so the sitemap lists 160 URLs (156 English pages plus the four translated homepages). A former translated catalyst, sponsor or directory URL gets a 301 to its English page while that page exists (568 of the 628); the 60 whose English page was retired return 404 like it. The redirect lifts itself if a translation is published again.
- **Retired pages are removed by the generator.** `scripts/generate_seo_pages.py` deletes a catalyst or sponsor page whose asset left the sample (it refuses to delete more than a third of either directory, and checks everything before writing), and also writes the directory hubs, the homepage sample table and the sitemap (last, so its dates see the hubs) in the same run. Only forward catalysts are shown: a date that has passed is dropped. Retired URLs with a true successor redirect (301) from `functions/_middleware.js`, from a table kept in `scripts/redirects.json`: `eftilagimod-alpha` → `eftilagimod-alfa`, `ritlecitinib-higher`/`-lower` → `ritlecitinib`, `rina` → `rinatabart-sesutecan`, `lorlatanib` → `lorlatinib`. Pages with no successor return 404, as Google recommends: this update retires 15 (the 7 below, and 8 whose catalysts left the 2026.10 sample: elecoglipron, monalizumab, oleclumab, rilvegostomig, telisotuzumab adizutecan, tirzepatide, zanidatamab, sponsor JAZZ).
- **Non-drug rows off the site.** Study arms and standard-of-care backbones (rescue medications, supportive care measures, platinum investigator choice, standard lymphodepletion, G-CSF, calcium levofolinate) no longer get a catalyst page; sponsor KYTX, whose only row was one of them, no longer gets a sponsor page. The generator applies the same rules as the free sample's curation upstream.
- **Richer catalyst and sponsor pages.** Catalyst pages list every trial the sample links to the asset (phase, status, primary completion, arm role, lead sponsor, conditions, linked to ClinicalTrials.gov) and the other tracked assets in the same trials. Sponsor pages add the sponsor's counts in the current full snapshot (forward catalysts, assets, trials, catalysts by year; counts only, from `data/sponsor_summary.json`), the trials behind its assets, every condition studied, and links to sponsors with trials in the same conditions.
- **Wording.** Pages no longer call every asset "clinical-stage", and the trial, not the asset, is "in Phase 3" (many tracked assets are approved drugs in a Phase 3 trial for a new indication). The per-page call to action states the snapshot's scope instead of its headline counts, which stay on the homepage: a catalyst page changes only when its own data does, and a sponsor page when its own data or full-snapshot counts do.
- **Homepage sample table** is generated from the sample: catalysts at least a month out, each linked to its catalyst and sponsor page (it showed hand-copied rows, three already past and one "rescue medications").

## 2026.10 — 2026-10-06

- Monthly refresh (CI run 2026-10-06); the precision gate passed with 0 cross-molecule
  merges. Published on the shopfront 2026-10-08.
- **2,202** forward catalysts (2,221 in 2026.09), **955** of them linked to **126** listed
  sponsors (124); **1,881** resolved assets (1,890); **603** tradeable core (597);
  **2,332** trials (2,331).
- Free sample rebuilt: 150 nearest-term ticker-linked catalysts from 2026-10-19,
  47 sponsors, 106 assets. Its curation now drops non-drug study arms (rescue medications,
  supportive care measures, platinum investigator choice, standard lymphodepletion) and
  standard-of-care backbones (G-CSF, calcium levofolinate), folds dose arms
  (ritlecitinib higher / lower → ritlecitinib) and fixes two misnamed assets
  (rina → rinatabart sesutecan, the full name of Rina-S; lorlatanib → lorlatinib).

## Site update — 2026-10-01

- **Sitemap dates follow page content**: `scripts/seo_common.py` (shared by the DataEngineered sites) dates each sitemap entry by the last commit that changed the page itself. It compares pages without line-ending differences and without the markup the translation build owns (language alternates and the header and footer language menus), and skips commits that only moved that markup, so regenerating an unchanged page keeps its date instead of taking the day of the run. No page or sitemap change in this update (2026-10-01).

## Site update — 2026-09-29

- **Visit counts**: Cloudflare Web Analytics adds its cookie-free page-view beacon to every page, but the Content-Security-Policy in `_headers` let browsers run scripts from this site only, so they refused the beacon and no visits were counted since Web Analytics was switched on (2026-09-05). The policy now also allows the beacon script (`https://static.cloudflareinsights.com`, `script-src`) and the address it reports to (`https://cloudflareinsights.com`, `connect-src`). No other source is added.

## Repository update — 2026-09-28

- **README**: the free-sample paragraph said the 150 nearest-term catalysts span 50 listed sponsors; they span 48 (distinct tickers in `samples/catalyst_calendar_sample.csv`), as the "What's inside" table and the quick-start output already said. Sample files unchanged (2026-09-28).

## Site update — 2026-09-28

- **Repository files off the website**: the translation catalogs (`/locales/`), the build scripts (`/scripts/`), `i18n.config.json`, `README.md`, `vercel.json` and the dotfiles belong to this repository, not to the website, but the site served them as plain files. They now answer the site's normal 404 page (also when requested as `/locales%2Fes.json` or `//locales/es.json`) and stay available here on GitHub. Pages, data files, samples, `llms.txt` and the sitemap are unchanged (2026-09-28).

## Site update — 2026-09-27

- **Translated Dataset markup**: on the Spanish, German, French and Portuguese pages the Dataset structured data now names its English original in `sameAs` (next to any existing `sameAs` links), so dataset search can tie the language copies to one canonical entry. English pages and all visible text are unchanged (2026-09-27).
- **Section links**: a link to a homepage section (`#pricing`, `#calendar`, `#contact`, ...) now lands with the section heading clear of the sticky header at every width, including phones where the nav wraps to two rows, and an arrival from another page lands on its section again once the web fonts and the language menu have settled. A small shared script right after the header does this (`scripts/section_links.py`, on the English and the four translated homepages); it never moves the page after the visitor has scrolled, and no visible text changes (2026-09-27).

## Site update — 2026-09-20

- **Sale attribution**: every Stripe buy link carries `?client_reference_id=<brand>_<lang>_<surface>` (`home` / `landing`); the i18n build swaps the language token per locale and the delivery worker prints the id in the order email. Stripe does not store UTM parameters, so this is the only per-page attribution that reaches the order record (2026-09-20).

## 2026.09 — 2026-09-19

- First refresh since 2026.07 (the August and September runs failed on an SEC EDGAR
  user-agent block, fixed 2026-09-15).
- **Precision correction.** 2026.07 contained wrong sponsor→ticker links: a fuzzy
  name-matching fallback linked non-listed sponsors to unrelated issuers (e.g. Dana-Farber
  Cancer Institute → DANA Inc), and trial readouts could inherit the ticker of another
  company running a different trial of the same drug. Fuzzy matching is removed (verified
  subsidiaries are curated aliases) and every readout now carries its own trial sponsor's
  ticker, or NULL when that sponsor is not listed. Audited: 0 readouts attributed to a
  non-sponsor ticker.
- **2,221** forward catalysts, **955** of them linked to **124** listed sponsors (2026.07
  reported 2,103 across 139 sponsors, a figure that included rows with no ticker and the
  wrong links above); **1,890** resolved assets; **597** tradeable core; **2,331** trials.
- Free sample rebuilt: 150 nearest-term ticker-linked catalysts from 2026-09-27,
  48 sponsors, 107 assets.

## 2026.07 — 2026-07-19

- Initial public snapshot.
- **2,103** forward catalysts across **139** listed sponsors, keyed to **1,841**
  resolved assets; **627** of them the sponsor's own asset linked to a listed
  ticker ("tradeable core"); **2,268** trials resolved.
- **v1 scope:** active, industry-sponsored, Phase-3 interventional trials in
  cardiometabolic, oncology and immunology. Phase 2 and more therapeutic areas are
  the documented monthly expansion.
- **Dual-channel catalysts:** `sec_8k` (SEC 8-K disclosure text) + `clinicaltrials`
  (active late-phase protocol primary-completion). Every row carries its `source`,
  a `confidence` grade, a `date_precision`, and a `source_url`.
- **Precision:** assets keyed to FDA active-moiety UNII sets with a
  moiety-consistency guard — audited to **0 cross-molecule merges**; uncertain
  pairs held for review, never auto-merged.
- Free 150-catalyst sample published on
  [Kaggle](https://www.kaggle.com/datasets/dataengineered/csa-clinical-stage-asset-intelligence-sample)
  (with a [starter notebook](https://www.kaggle.com/code/dataengineered/csa-clinical-stage-asset-intelligence-starter))
  and [Hugging Face](https://huggingface.co/datasets/Ichlibitiche/csa-clinical-stage-asset-intelligence-sample).

Full dataset & updates: [csa.dataengineered.io](https://csa.dataengineered.io)
