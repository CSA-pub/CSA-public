# CSA — Sources & Upstream Licenses

Every record in CSA traces to a public, redistribution-clean source. Each catalyst
row carries a `source` channel and a `source_url` so any fact can be re-verified.
CSA deliberately uses **no license-encumbered source** (DrugBank, ChEMBL, MedDRA).

| Source | URL | License | Contributes |
| :--- | :--- | :--- | :--- |
| ClinicalTrials.gov (NLM, API v2) | clinicaltrials.gov | Public domain — US federal work (17 U.S.C. § 105) | Trial protocols: phase, status, sponsor, conditions, arms, primary-completion dates |
| openFDA / Drugs@FDA | open.fda.gov / accessdata.fda.gov | Public domain — US federal work | Approval status, application numbers (NDA/BLA), sponsor of record |
| SEC EDGAR | sec.gov/edgar | Public domain — US federal work | 8-K disclosure text → company-stated catalyst dates; issuer ↔ ticker |
| FDA GSRS / UNII | gsrs.ncats.nih.gov / fdasis.nlm.nih.gov | Public domain — US federal work | Active-moiety substance registry (UNII) used to key each asset |

## How each row is attributed

- **`source = clinicaltrials`** — the catalyst is an active late-phase protocol
  primary-completion date from ClinicalTrials.gov. `source_url` links the study.
- **`source = sec_8k`** — the catalyst date was disclosed by the company in an SEC
  8-K filing. `source_url` links the filing.

The asset↔sponsor↔ticker linkage is derived by CSA from the above: assets are
keyed to their FDA-registered **active-moiety UNII set** (GSRS), and sponsors are
resolved through acquisitions to their **primary US listing**.

## Reuse

All four primary sources are **U.S. Government / public domain**, so the underlying
facts carry no attribution obligation. The **linkage, active-moiety resolution, and
catalyst compilation are DataEngineered's own work**; the free sample and this
documentation are licensed **CC-BY-NC-4.0** (see [`LICENSE`](LICENSE)). Attribution
to *CSA — Clinical-Stage Asset Intelligence (csa-public.pages.dev)* is appreciated.

*CSA is data, not investment advice.*
