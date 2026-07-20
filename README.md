# Kazi Sasa — Kenya Public Sector Vacancy Viewer (Expanded Phase 1)

This repository implements the **Phase 1 — Registry and Quality Foundation** from the public-sector coverage expansion spec.

It is a private, accuracy-first viewer and feed package for Kenya public-sector roles. The HTML viewer does not scrape websites directly. The Python scripts normalize and validate `public_sector_feed.json`, and future collector phases should add PSCIMS detail scraping, MyGov/GAA PDF parsing, county PSB collectors, SAGA/commission collectors, and public-university/hospital collectors.

## What is included now

- `index.html` / `kenya_public_sector_viewer.html` — searchable standalone viewer.
- `public_sector_feed.json` and `data/public_sector_feed.json` — active actual snapshot carried forward from PSCIMS and KSG portal data.
- `data/source_registry.json` — registry covering active sources plus the broader source universe: PSCIMS, MyGov/GAA, KSG, 47 counties, commissions, SAGAs/state corporations, universities and hospitals.
- `data/coverage_registry.json` — coverage dashboard data.
- `data/public_sector_taxonomy.json` — controlled job-family taxonomy.
- `data/source_status.json` — source-health dashboard data.
- `data/rejected_watchlist.json` — scam/high-risk watchlist.
- `scripts/validate_public_sector_feed.py` — stronger accuracy validator.
- `scripts/refresh_public_sector_feed.py` — Phase 1 normalizer preserving actual rows and adding view/provenance links.
- `.github/workflows/refresh-public-sector-feed.yml` — GitHub Actions refresh/validate workflow.
- `PUSH_TO_GITHUB.cmd` — one-click GitHub push helper.

## View original role link

Every vacancy now includes:

```json
"links": {
  "view_original_url": "https://...",
  "view_original_label": "View role on original site"
}
```

The viewer shows a **View original role** link on role cards and in the detail panel.

## Validate locally

```bat
py scriptsalidate_public_sector_feed.py data\public_sector_feed.json --registry data\source_registry.json
```

## Refresh/normalize locally

```bat
py scriptsefresh_public_sector_feed.py
py scriptsalidate_public_sector_feed.py data\public_sector_feed.json --registry data\source_registry.json
```

## Push to GitHub

```bat
PUSH_TO_GITHUB.cmd
```

## Current limitation

This package implements the expanded registry/quality foundation. It does **not yet claim near-complete live scraping**. It retains the current actual snapshot and prepares the repo for the next phases: PSCIMS detail collector, MyGov/GAA parser, county coverage, SAGA/commission collectors and public institution collectors.
