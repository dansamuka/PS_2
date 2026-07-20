# Kazi Sasa Public Sector Viewer — PS_2 Phase 3

This package implements **Phase 3 — Central government collectors** for the existing `PS_2` GitHub Pages repo.

The project remains:

- **national-only** — county government / county PSB sources remain excluded;
- **all role families** — no filtering down to customer service or admin only;
- **accuracy-first** — the viewer shows verified/open roles and keeps discovery-only items separate until reviewed;
- **existing-repo first** — `PUSH_TO_GITHUB.cmd` updates `https://github.com/dansamuka/PS_2.git` instead of creating a new repo.

## What Phase 3 adds

- `scripts/collectors/pscims.py` — official PSCIMS active-adverts collector.
- `scripts/collectors/mygov.py` — MyGov/GAA job-adverts discovery collector.
- `scripts/collectors/official_page_monitor.py` — central PSC/public-service page source-health monitor.
- `scripts/collectors/_common.py` — shared fetch/normalise helpers.
- `data/discovery_queue.json` — MyGov/GAA discovery items requiring review before entering the live feed.
- `data/central_source_health.json` — reachability/source-health checks for central sources.
- `data/central_collector_report.json` — collector run report.
- `scripts/verify_phase3.py` and `VERIFY_PHASE_3.cmd`.
- GitHub Actions now runs the central collectors using `--collect-central`.

## Current feed state

- Active vacancies retained: **43**
- Registered national sources: **239**
- County sources excluded: **yes**
- All role families included: **yes**
- View-original role links: **43 / 43**

The current bundled feed retains the existing verified PSCIMS/KSG snapshot. When run on GitHub Actions or a machine with internet access, Phase 3 can refresh PSCIMS and write MyGov/GAA discovery items.

## Accuracy policy

- PSCIMS rows can enter `vacancies[]` as **official** central public-service vacancies.
- MyGov/GAA rows enter `data/discovery_queue.json` first because many are PDF/discovery notices and must be cross-checked with the hiring institution before being treated as open vacancies.
- If a live source fails, the refresh script preserves the existing validated feed rather than overwriting it with empty data.
- Gmail/WhatsApp/payment-request adverts are not allowed into the open feed.

## Local validation

```bat
VERIFY_PHASE_3.cmd
```

Or manually:

```bat
python scripts\validate_public_sector_feed.py data\public_sector_feed.json --registry data\source_registry.json
python scripts\verify_phase3.py
```

## Run Phase 3 refresh locally

Normalise existing feed only:

```bat
python scripts\refresh_public_sector_feed.py
```

Run live central collectors:

```bat
python scripts\refresh_public_sector_feed.py --collect-central
```

If the machine has no internet, the collector report will show source errors but the existing feed will be preserved.

## Push to existing GitHub repo

```bat
PUSH_TO_GITHUB.cmd
```

Default repo:

```text
https://github.com/dansamuka/PS_2.git
```

Expected GitHub Pages URL:

```text
https://dansamuka.github.io/PS_2/
```

## Next phase

Phase 4 should implement ministry and state-department monitors using the official registry and common page patterns such as `/careers`, `/vacancies`, `/jobs`, `/opportunities`, `/downloads`, and `/media-centre`.
