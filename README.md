# Kazi Sasa Public Sector Viewer — PS_2 Phase 3C

This package implements **Phase 3C — Role identity reconciliation** for the existing `PS_2` GitHub Pages repo.

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


## Phase 3A hotfix

A PSCIMS live refresh exposed ASP.NET `javascript:__doPostBack(...)` detail links. These are now sanitised and replaced with the official PSCIMS active-adverts page before validation. See `docs/PHASE_3A_PSCIMS_POSTBACK_HOTFIX.md`.


## Phase 3B — Latest-role ingestion hardening

Phase 3B keeps `PS_2` as the canonical repo and focuses on yielding visible progress from each refresh:

- PSCIMS official active adverts are refreshed live.
- KSG portal roles are refreshed live when reachable and remain `needs_review` until official linkage is reconfirmed.
- MyGov/GAA discovery tries the current GAA job-adverts node and legacy MyGov paths instead of failing on a single 404.
- Expired roles are marked `expired`, so they are hidden from Open roles by default.
- `last_run_report.json` and feed `meta.change_summary` now show new, updated, expired and unchanged role counts.

Run locally:

```bat
VERIFY_PHASE_3B.cmd
```

Run refresh:

```bat
python scripts
efresh_public_sector_feed.py --collect-central
```


## Phase 3B local verification note

`VERIFY_PHASE_3B.cmd` treats `pytest` as optional on Windows. Core feed and scope checks remain strict. If `pytest` is not installed, parser tests are skipped locally; install dependencies with `python -m pip install -r requirements.txt` to run them.

## Phase 3C — Role identity reconciliation

Phase 3C fixes refresh reporting after live KSG ingestion. A refreshed role can now keep a stable `identity.canonical_key` even when the scraper-generated row `id` changes. The change summary now distinguishes genuinely new roles from refreshed existing roles.

New artifacts:

```text
scripts/role_identity.py
scripts/verify_phase3c.py
VERIFY_PHASE_3C.cmd
data/role_identity_map.json
data/discovery_review_queue.json
data/discovery_review_summary.json
docs/PHASE_3C_ROLE_IDENTITY_RECONCILIATION.md
```

Run local verification:

```bat
VERIFY_PHASE_3C.cmd
```

Important push behaviour: `PUSH_TO_GITHUB.cmd` now avoids overwriting live-generated feed/report files from GitHub Actions with stale local snapshots. Push the code, then run the GitHub Action to refresh data.


## Phase 3D — KSG import reliability and discovery promotion workbench

Phase 3D adds:

- a GitHub Actions-safe KSG collector import path;
- `scripts/__init__.py` so package imports are stable;
- a workflow import smoke test for KSG;
- `scripts/discovery_promoter.py`;
- `data/discovery_promotion_candidates.json`;
- `data/discovery_promotion_summary.json`;
- `data/reviewed_promotions.json` template;
- a viewer upgrade so the Discovery tab shows promotion candidates as well as raw discovery rows.

Discovery candidates remain outside the Open roles feed until manually reviewed and confirmed.

Run locally:

```bat
VERIFY_PHASE_3D.cmd
```

Then push and run the GitHub Action.


## Phase 3D dependency hotfix

`VERIFY_PHASE_3D.cmd` now checks for required scraper dependencies (`beautifulsoup4` and `requests`) and installs `requirements.txt` automatically if they are missing. This prevents the local Windows verification failure `ModuleNotFoundError: No module named 'bs4'`.
