# Changelog

All notable changes to the CSA (Clinical-Stage Asset Intelligence) snapshots.

> The dataset is refreshed monthly, so live figures move between snapshots. A
> count-claim gate asserts the corpus counts against the shopfront on every build,
> so the advertised numbers and the shipped data can never silently diverge.

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
  [Kaggle](https://www.kaggle.com/datasets/ahtiticheamine/csa-clinical-stage-asset-intelligence-sample)
  (with a [starter notebook](https://www.kaggle.com/code/ahtiticheamine/csa-clinical-stage-asset-intelligence-starter))
  and [Hugging Face](https://huggingface.co/datasets/Ichlibitiche/csa-clinical-stage-asset-intelligence-sample).

Full dataset & updates: [csa-public.pages.dev](https://csa-public.pages.dev)
