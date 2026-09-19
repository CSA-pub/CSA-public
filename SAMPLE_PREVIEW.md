# CSA — Sample Preview

Human-readable preview of the free sample (snapshot `2026.09`). Machine-readable
CSVs live in [`samples/`](samples/); full field documentation in
[`DATA_DICTIONARY.md`](DATA_DICTIONARY.md).

The sample is the **150 nearest-term forward catalysts** across **48 listed
sponsors** and **107 assets** — curated to clean, single-sponsor, clinical-stage
assets. (This v1 sample is scoped to active Phase-3 readouts; the full snapshot
spans event types, phases and therapeutic areas.)

## Forward catalysts (`samples/catalyst_calendar_sample.csv`)

| event_date | ticker | asset | event_type | confidence | nct_id |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-09-27 | BIIB | litifilimab | READOUT | medium | NCT04961567 |
| 2026-09-28 | MLTX | sonelokimab | READOUT | medium | NCT06768671 |
| 2026-09-30 | AZN | datopotamab deruxtecan | READOUT | medium | NCT06417814 |
| 2026-09-30 | BIIB | litifilimab | READOUT | medium | NCT04895241 |
| 2026-09-30 | AZN | monalizumab | READOUT | medium | NCT05221840 |
| 2026-09-30 | AZN | oleclumab | READOUT | medium | NCT05221840 |
| 2026-09-30 | JAZZ | zanidatamab | READOUT | medium | NCT05152147 |
| 2026-10-19 | BMY | deucravacitinib | READOUT | medium | NCT05617677 |
| 2026-10-20 | BIIB | litifilimab | READOUT | medium | NCT05531565 |
| 2026-10-26 | NVS | inclisiran | READOUT | medium | NCT05360446 |
| 2026-10-28 | MRK | belzutifan | READOUT | medium | NCT05239728 |
| 2026-10-30 | PFE | binimetinib | READOUT | medium | NCT04657991 |

Each row also carries `event_window` (the date as originally disclosed),
`date_precision`, `source` (`sec_8k` / `clinicaltrials`), and a `source_url` back
to the ClinicalTrials.gov study or SEC filing.

## Asset linkage (`samples/asset_master_sample.csv`)

The rows behind the catalysts — how each asset resolves to a trial, a sponsor, and
a listed ticker:

| asset | nct_id | phase | status | sponsor_raw | company_name | ticker |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| litifilimab | NCT04895241 | PHASE3 | ACTIVE_NOT_RECRUITING | Biogen | BIOGEN INC. | BIIB |
| sonelokimab | NCT06641076 | PHASE3 | ACTIVE_NOT_RECRUITING | MoonLake Immunotherapeutics AG | MoonLake Immunotherapeutics | MLTX |
| datopotamab deruxtecan | NCT05104866 | PHASE3 | ACTIVE_NOT_RECRUITING | AstraZeneca | ASTRAZENECA PLC | AZN |

*(illustrative subset — see the CSV for all 450 linkage rows)*

---

The full snapshot adds the `regulatory_events` table (FDA approvals/applications),
both catalyst channels across more event types, and the complete **2,221-catalyst**
calendar — see the [README](README.md#pricing) for access.

*CSA is data, not investment advice.*
