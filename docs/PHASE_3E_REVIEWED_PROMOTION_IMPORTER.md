# Phase 3E — Reviewed Promotion Importer

Phase 3E converts the Phase 3D discovery workbench into a safe promotion workflow.

It does **not** auto-publish MyGov/GAA discovery items. Instead, it adds:

- `scripts/promotion_importer.py` — validates and imports manually reviewed records;
- `scripts/review_batch.py` — builds a high-priority manual review batch from promotion candidates;
- `data/reviewed_promotions.json` — the only place where approved discovery records are entered;
- `data/manual_review_batch_1.json/.csv/.md` — review pack for the next batch;
- `data/promotion_import_report.json` — shows added/rejected/duplicate reviewed records;
- `VERIFY_PHASE_3E.cmd` — full local verification.

## Promotion rule

A discovery item enters `vacancies[]` only when a human-reviewed record has:

- exact role title;
- hiring institution;
- original official PDF/source URL;
- deadline;
- official application URL or instructions;
- no payment requirement;
- no Gmail/WhatsApp-only application route;
- all manual checks marked true.

## Workflow

1. Run the GitHub Action to refresh discovery candidates.
2. Run or review `data/manual_review_batch_1.csv`.
3. Confirm roles from original PDFs/sources.
4. Add approved records to `data/reviewed_promotions.json`.
5. Run `python scripts/refresh_public_sector_feed.py` or the GitHub Action.
6. Verified reviewed records will enter the open feed.

## Why this matters

This phase creates a controlled bridge from discovery to open roles. It avoids the unsafe pattern of treating every public advert/PDF as a live job without confirming deadline, application channel and institution.
