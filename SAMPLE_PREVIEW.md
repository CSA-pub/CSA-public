# CSA — Sample Preview

Human-readable preview of the free sample (snapshot `2026.11`). Machine-readable
CSVs live in [`samples/`](samples/); full field documentation in
[`DATA_DICTIONARY.md`](DATA_DICTIONARY.md).

The sample is the **150 nearest-term forward catalysts** across **44 listed
sponsors** and **104 assets** — curated to clean, single-sponsor drug
assets. (The full snapshot has the same v1 scope, active Phase-3 trial readouts in
cardiometabolic, oncology and immunology, without the sample's single-sponsor curation.)

## Forward catalysts (`samples/catalyst_calendar_sample.csv`)

| event_date | ticker | asset | event_type | confidence | nct_id |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-11-30 | CGON | cretostimogene grenadenorepvec | READOUT | medium | NCT06111235 |
| 2026-11-30 | NAMS | obicetrapib | READOUT | medium | NCT05202509 |
| 2026-11-30 | LLY | retatrutide | READOUT | medium | NCT06662383 |
| 2026-12-01 | VNDA | tradipitant | READOUT | medium | NCT07446439 |
| 2026-12-02 | PFE | ritlecitinib | READOUT | medium | NCT07029711 |
| 2026-12-23 | AZN | benralizumab | READOUT | medium | NCT05692180 |
| 2026-12-26 | INCY | povorcitinib | READOUT | medium | NCT06212999 |
| 2026-12-30 | PFE | vepdegestrant | READOUT | medium | NCT05909397 |
| 2026-12-31 | PFE | axitinib | READOUT | medium | NCT05059522 |
| 2026-12-31 | VTRS | cenerimod | READOUT | medium | NCT05672576 |
| 2026-12-31 | IONS | donidalorsen | READOUT | medium | NCT05392114 |
| 2026-12-31 | PFE | lorlatinib | READOUT | medium | NCT05059522 |

Each row also carries `event_window` (the date as originally disclosed),
`date_precision`, `source` (`clinicaltrials`: a ClinicalTrials.gov protocol date),
and a `source_url` back to the ClinicalTrials.gov study.

## Asset linkage (`samples/asset_master_sample.csv`)

The rows behind the catalysts — how each asset resolves to a trial, a sponsor, and
a listed ticker:

| asset | nct_id | phase | status | sponsor_raw | company_name | ticker |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| cretostimogene grenadenorepvec | NCT04452591 | PHASE3 | ACTIVE_NOT_RECRUITING | CG Oncology, Inc. | CG Oncology, Inc. | CGON |
| obicetrapib | NCT05202509 | PHASE3 | ACTIVE_NOT_RECRUITING | NewAmsterdam Pharma | NewAmsterdam Pharma Co N.V. | NAMS |
| retatrutide | NCT06260722 | PHASE3 | ACTIVE_NOT_RECRUITING | Eli Lilly and Company | ELI LILLY & Co | LLY |

*(illustrative subset — see the CSV for all 444 linkage rows)*

---

The full snapshot adds the `regulatory_events` table (FDA approval events matched to
the assets) and the complete **2,237-catalyst** calendar — see the [README](README.md#pricing) for access.

*CSA is data, not investment advice.*
