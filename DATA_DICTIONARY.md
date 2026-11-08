# CSA — Data Dictionary

Field reference for CSA (Clinical-Stage Asset Intelligence), snapshot `2026.11`.
The free sample (`samples/`) uses the columns below. The full dataset ships the
same fields in CSV and JSON, plus a `regulatory_events` table and a scope
manifest.

## `catalyst_calendar` — the forward catalyst calendar

One row per upcoming catalyst, linked to a drug asset and its listed sponsor.

| Column | Type | Description |
| :--- | :--- | :--- |
| `event_date` | date | Catalyst date (ISO `YYYY-MM-DD`). For imprecise sources it is pinned to the **end** of the disclosed period — see `date_precision`. |
| `ticker` | string | Primary US-listed stock ticker of the asset's sponsor. |
| `asset` | string | Normalized, INN-like name of the clinical-stage drug asset. |
| `event_type` | enum | Catalyst category. v1 rows are `READOUT` (scheduled trial data readout); the schema also defines `PDUFA` (FDA action date), `ADCOMM`, `CRL` and `APPROVAL_DECISION`, and v1 contains none of them. |
| `event_window` | string | The event date/window as registered or disclosed (e.g. `Jun 30, 2027` for a day-precise date, `Nov 2026` for a month). |
| `date_precision` | enum | Granularity of `event_date`: `day` · `month` · `quarter` · `half` · `year`. |
| `confidence` | enum | Date confidence grade: `high` · `medium` · `low`. Phase 3 protocol estimates are graded `medium`; `high` marks a company-disclosed exact date and `low` a Phase 2 estimate. |
| `source` | enum | Origin channel: `clinicaltrials` (protocol primary-completion estimate — the channel behind v1's calendar) or `sec_8k` (date parsed from SEC 8-K disclosure text). |
| `nct_id` | string | ClinicalTrials.gov identifier for the underlying trial, when the catalyst is trial-derived. |
| `source_url` | string | Direct link to the primary source (ClinicalTrials.gov study or SEC filing) for re-verification. |

## `asset_master` — the asset ↔ trial ↔ sponsor ↔ ticker linkage

The rows behind each catalyst: how an asset resolves to a trial, a sponsor, and a
listed ticker.

| Column | Type | Description |
| :--- | :--- | :--- |
| `asset` | string | Normalized, INN-like name of the clinical-stage drug asset. |
| `nct_id` | string | ClinicalTrials.gov identifier for the trial. |
| `phase` | string | Trial phase (e.g. `PHASE3`). |
| `status` | string | Trial recruitment status (e.g. `RECRUITING`, `ACTIVE_NOT_RECRUITING`). |
| `primary_completion` | date | Estimated primary completion date of the trial (ISO). |
| `conditions` | string | Medical condition(s) the trial targets. |
| `arm_role` | string | Role of the asset in the trial (e.g. `experimental`). |
| `sponsor_raw` | string | Lead sponsor name exactly as recorded on ClinicalTrials.gov. |
| `company_name` | string | Resolved listed parent company for the sponsor. |
| `ticker` | string | Primary US-listed stock ticker of the sponsor. |

## `regulatory_events` — FDA events (full dataset)

FDA regulatory events matched to the resolved assets: `asset`,
`application_number` (NDA/BLA), `fda_sponsor` (sponsor of record), `event_type`,
`status`, `date`.

## Sources & collection methodology

**Sources** (all U.S. Government / public domain — see [`SOURCES.md`](SOURCES.md)):
- **ClinicalTrials.gov** (NLM API v2) — trial protocols, phases, statuses, sponsors, conditions, and primary-completion dates.
- **openFDA / Drugs@FDA** — approval status, application numbers, sponsor of record.
- **SEC EDGAR** — the issuer ↔ ticker/CIK registry used to resolve sponsors to listed companies.
- **FDA GSRS / UNII** — the active-moiety substance registry used to key each asset.

**Collection methodology**
1. **Trial pull (ClinicalTrials.gov).** A structural sweep of active, industry-sponsored, Phase-3 interventional trials in the covered therapeutic areas, plus seed-term expansion. Each study retains a re-verifiable `source_url`.
2. **Active-moiety resolution (GSRS/UNII).** Every asset mention is keyed to its FDA-registered active-moiety UNII set. Assets are clustered by moiety, then a consistency guard splits any cluster that would span two complete moieties — **0 cross-molecule merges**; fuzzy matches never auto-merge, uncertain pairs are held for review.
3. **Sponsor → listed ticker.** Lead sponsors are resolved through acquisitions to the primary US listing.
4. **Readout catalysts.** `clinicaltrials` — active Phase 3 protocol primary-completion dates, credited only to the sponsor's own experimental-arm asset; standard-of-care backbone agents in combination arms are excluded. Each row carries `confidence` and `date_precision`.

**Update frequency: monthly** (snapshot `2026.11`). On every build a count-claim gate recomputes the headline counts from the packaged files and fails the build if they differ from the snapshot's own `scope_manifest.json`, so the archive always matches its manifest. The figures on the website are updated by hand after each edition, so for a few days after a refresh they can trail the latest snapshot.

## Notes

- **Precision over recall.** A wrong asset↔ticker link is the costly error; CSA holds uncertain pairs for review rather than merging them.
- **Dates are estimates, not guarantees.** Protocol primary-completion dates routinely slip — hence the `confidence` and `date_precision` columns and a `source_url` on every row.
- **Redistribution-clean.** No license-encumbered source (DrugBank, ChEMBL, MedDRA) is used.

Full dataset: **[csa.dataengineered.io](https://csa.dataengineered.io)** · Questions or corrections: csa@dataengineered.io

*CSA is data, not investment advice.*
