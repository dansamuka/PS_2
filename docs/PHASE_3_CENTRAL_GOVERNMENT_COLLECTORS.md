# Phase 3 — Central Government Collectors

## Objective

Implement the first live collector layer for central national-government recruitment sources while preserving the accuracy-first principle.

## Implemented collectors

| Collector | File | Output | Confidence |
|---|---|---|---|
| PSCIMS active adverts | `scripts/collectors/pscims.py` | `vacancies[]` | official |
| MyGov/GAA job adverts | `scripts/collectors/mygov.py` | `data/discovery_queue.json` | official discovery / needs review |
| PSC/public-service page monitor | `scripts/collectors/official_page_monitor.py` | `data/central_source_health.json` | source health only |

## Why MyGov is discovery-only

MyGov/GAA publishes public-sector job-advert PDFs and advert notices, but those notices must often be cross-checked with the hiring institution or official application portal. Therefore Phase 3 stores MyGov rows in `discovery_queue.json` instead of pushing them directly into the live vacancies list.

## Refresh commands

```bash
python scripts/refresh_public_sector_feed.py --collect-central
python scripts/validate_public_sector_feed.py data/public_sector_feed.json --registry data/source_registry.json
python scripts/verify_phase3.py
```

## Safety behaviour

- Existing vacancies are preserved if central collectors fail.
- PSCIMS rows replace previous PSCIMS rows only when fresh rows are successfully collected.
- Open vacancies must have `links.view_original_url`.
- County sources remain excluded.
- All role families remain in scope.

## New artifacts

- `data/discovery_queue.json`
- `data/central_source_health.json`
- `data/central_collector_report.json`
- `VERIFY_PHASE_3.cmd`
- `scripts/verify_phase3.py`
- `scripts/tests/test_phase3_collectors.py`
