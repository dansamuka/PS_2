# Phase 3B — Latest-role Ingestion Hardening

## Purpose

Phase 3B is the first role-yielding hardening phase after the central-source foundation. It does not expand to dozens of ministries/parastatals yet. It makes the currently enabled sources genuinely refreshable and explains whether the feed changed.

## Implemented

- Added `scripts/collectors/ksg.py` to refresh KSG portal roles live when reachable.
- Reworked `scripts/collectors/mygov.py` to try the current GAA job-adverts node plus legacy MyGov paths.
- Preserved MyGov/GAA as discovery-only: results go to `data/discovery_queue.json`, not open roles.
- Added expired-role marking so expired records are hidden from Open roles by default.
- Added `meta.change_summary` to `data/public_sector_feed.json` and `public_sector_feed.json`.
- Added `change_summary` to `data/last_run_report.json`.
- Added `scripts/verify_phase3b.py` and `VERIFY_PHASE_3B.cmd`.
- Updated GitHub Actions to validate Phase 3B after every scheduled/manual refresh.

## Meaningful progress expected per run

Every successful refresh should now report:

- `new_roles`
- `updated_roles`
- `expired_roles`
- `unchanged_roles`
- `discovery_items`
- source-health checks

If no roles change, the system should say so explicitly rather than appearing broken.

## Accuracy rules retained

- PSCIMS official rows may enter open roles.
- KSG rows remain `needs_review` until official linkage is reconfirmed.
- MyGov/GAA remains discovery-only until the hiring institution is verified.
- Gmail/WhatsApp/payment-request adverts are not allowed into open vacancies.
- County coverage remains excluded.
