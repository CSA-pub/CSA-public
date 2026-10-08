# CSA — Sample Preview

Human-readable preview of the free sample (snapshot `2026.10`). Machine-readable
CSVs live in [`samples/`](samples/); full field documentation in
[`DATA_DICTIONARY.md`](DATA_DICTIONARY.md).

The sample is the **150 nearest-term forward catalysts** across **47 listed
sponsors** and **106 assets** — curated to clean, single-sponsor drug
assets. (This v1 sample is scoped to active Phase-3 readouts; the full snapshot
spans event types, phases and therapeutic areas.)

## Forward catalysts (`samples/catalyst_calendar_sample.csv`)

| event_date | ticker | asset | event_type | confidence | nct_id |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-10-19 | BMY | deucravacitinib | READOUT | medium | NCT05617677 |
| 2026-10-20 | BIIB | litifilimab | READOUT | medium | NCT05531565 |
| 2026-10-26 | NVS | inclisiran | READOUT | medium | NCT05360446 |
| 2026-10-28 | MRK | belzutifan | READOUT | medium | NCT05239728 |
| 2026-10-30 | PFE | binimetinib | READOUT | medium | NCT04657991 |
| 2026-10-30 | PFE | encorafenib | READOUT | medium | NCT04657991 |
| 2026-10-31 | OLMA | palazestrant | READOUT | medium | NCT06016738 |
| 2026-10-31 | LLY | retatrutide | READOUT | medium | NCT06297603 |
| 2026-10-31 | OGN | tapinarof | READOUT | medium | NCT05172726 |
| 2026-11-30 | CGON | cretostimogene grenadenorepvec | READOUT | medium | NCT06111235 |
| 2026-11-30 | NAMS | obicetrapib | READOUT | medium | NCT05202509 |
| 2026-11-30 | LLY | retatrutide | READOUT | medium | NCT06662383 |

Each row also carries `event_window` (the date as originally disclosed),
`date_precision`, `source` (`sec_8k` / `clinicaltrials`), and a `source_url` back
to the ClinicalTrials.gov study or SEC filing.

## Asset linkage (`samples/asset_master_sample.csv`)

The rows behind the catalysts — how each asset resolves to a trial, a sponsor, and
a listed ticker:

| asset | nct_id | phase | status | sponsor_raw | company_name | ticker |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| deucravacitinib | NCT04772079 | PHASE3 | RECRUITING | Bristol-Myers Squibb | BRISTOL MYERS SQUIBB CO | BMY |
| litifilimab | NCT04895241 | PHASE3 | ACTIVE_NOT_RECRUITING | Biogen | BIOGEN INC. | BIIB |
| inclisiran | NCT04765657 | PHASE3 | ACTIVE_NOT_RECRUITING | Novartis Pharmaceuticals | NOVARTIS AG | NVS |

*(illustrative subset — see the CSV for all 440 linkage rows)*

---

The full snapshot adds the `regulatory_events` table (FDA approvals/applications),
both catalyst channels across more event types, and the complete **2,202-catalyst**
calendar — see the [README](README.md#pricing) for access.

*CSA is data, not investment advice.*
