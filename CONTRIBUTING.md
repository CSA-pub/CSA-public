# Contributing to CSA

Thanks for your interest! This repository is the **public showcase** for CSA
(Clinical-Stage Asset Intelligence) — it holds a free sample, documentation, and a
starter notebook. The data pipeline itself is not open source, so contributions
here focus on **data quality, docs, and examples**.

## Ways to help

### 🐛 Report a data issue
Spotted a wrong asset↔ticker link, a mis-attributed catalyst, or a slipped date in
the sample? Open an issue with:
- the `asset` and `ticker` (and `nct_id` if trial-derived),
- what's wrong and what it should be,
- ideally the `source_url` so we can re-verify.

**Linkage errors are the highest priority** — a wrong asset↔ticker link is the
costly error CSA is built to avoid, so please flag it immediately.

### ✏️ Improve docs or examples
Typos, clearer explanations, or a better `examples/load_sample.py` / notebook are
welcome via pull request.

### 💡 Request a field, area, or phase
Want a column, therapeutic area, or trial phase the v1 snapshot doesn't cover yet?
Open an issue describing the use case — it helps prioritize the monthly expansion
and informs custom builds.

## Correction or removal requests

To request a record be corrected, email **roasterdb@proton.me** (or open an issue).

## Pull request guidelines

- Keep PRs focused and describe the *why*.
- Docs/examples only — please don't add pipeline/scraping code here.
- Data changes to the sample should preserve the schema in
  [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md).

## Licensing of contributions

By contributing, you agree that your contributions to the sample and docs are
licensed under **CC-BY-NC-4.0**, the same license as this repository (see
[`LICENSE`](LICENSE)).

Questions? **roasterdb@proton.me** · full dataset: [csa-public.pages.dev](https://csa-public.pages.dev)

*CSA is data, not investment advice.*
