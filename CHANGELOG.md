# Changelog

All notable changes to the CSA (Clinical-Stage Asset Intelligence) snapshots.

> The dataset is refreshed monthly, so live figures move between snapshots. A
> count-claim gate asserts the corpus counts against the shopfront on every build,
> so the advertised numbers and the shipped data can never silently diverge.

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
