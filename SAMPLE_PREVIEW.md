# CSA — Sample Preview

Human-readable preview of the free sample (snapshot `2026.07`). Machine-readable
CSVs live in [`samples/`](samples/); full field documentation in
[`DATA_DICTIONARY.md`](DATA_DICTIONARY.md).

The sample is the **150 nearest-term forward catalysts** across **50 listed
sponsors** and **108 assets** — curated to clean, single-sponsor, clinical-stage
assets. (This v1 sample is scoped to active Phase-3 readouts; the full snapshot
spans event types, phases and therapeutic areas.)

## Forward catalysts (`samples/catalyst_calendar_sample.csv`)

| event_date | ticker | asset | event_type | confidence | nct_id |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-07-18 | BMY | mezigdomide | READOUT | medium | NCT05552976 |
| 2026-07-25 | BMY | deucravacitinib | READOUT | medium | NCT04036435 |
| 2026-07-27 | REGN | fianlimab | READOUT | medium | NCT05608291 |
| 2026-07-31 | HRMY | pitolisant | READOUT | medium | NCT06366464 |
| 2026-07-31 | LXRX | sotagliflozin | READOUT | medium | NCT06481891 |
| 2026-07-31 | JAZZ | zanidatamab | READOUT | medium | NCT05152147 |
| 2026-08-01 | MRK | tulisokibart | READOUT | medium | NCT06052059 |
| 2026-08-24 | AZN | camizestrant | READOUT | medium | NCT04711252 |
| 2026-08-30 | PFE | elranatamab | READOUT | medium | NCT06152575 |
| 2026-08-31 | PHVS | deucrictibant | READOUT | medium | NCT06669754 |
| 2026-08-31 | SBFM | lerotinib | READOUT | medium | NCT04415853 |
| 2026-08-31 | SLGL | patidegib | READOUT | medium | NCT06050122 |

Each row also carries `event_window` (the date as originally disclosed),
`date_precision`, `source` (`sec_8k` / `clinicaltrials`), and a `source_url` back
to the ClinicalTrials.gov study or SEC filing.

## Asset linkage (`samples/asset_master_sample.csv`)

The rows behind the catalysts — how each asset resolves to a trial, a sponsor, and
a listed ticker:

| asset | nct_id | phase | status | sponsor_raw | company_name | ticker |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| mezigdomide | NCT05519085 | PHASE3 | RECRUITING | Celgene | BRISTOL MYERS SQUIBB CO | BMY |
| fianlimab | NCT05352672 | PHASE3 | ACTIVE_NOT_RECRUITING | Regeneron Pharmaceuticals | REGENERON PHARMACEUTICALS, INC. | REGN |
| zanidatamab | NCT05152147 | PHASE3 | ACTIVE_NOT_RECRUITING | Jazz Pharmaceuticals | Jazz Pharmaceuticals plc | JAZZ |

*(illustrative subset — see the CSV for all 464 linkage rows)*

---

The full snapshot adds the `regulatory_events` table (FDA approvals/applications),
both catalyst channels across more event types, and the complete **2,103-catalyst**
calendar — see the [README](README.md#pricing) for access.

*CSA is data, not investment advice.*
