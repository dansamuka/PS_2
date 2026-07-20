# Phase 1 — Existing Repo Stabilisation

## Objective

Stabilise the existing `PS_2` GitHub Pages repository as the canonical deployment target for the Kazi Sasa Kenya National Public Sector Vacancy Viewer.

## Scope implemented

- `PUSH_TO_GITHUB.cmd` targets `https://github.com/dansamuka/PS_2.git` by default.
- The package can be pushed into the existing repo instead of creating a new repo.
- `index.html` remains the GitHub Pages entry point.
- `data/public_sector_feed.json` remains the canonical feed loaded by the viewer.
- `public_sector_feed.json` is kept as a root-level feed copy.
- Every active vacancy includes `links.view_original_url`.
- County source coverage placeholders were removed.
- Existing actual open-role rows were retained.
- All job families remain in scope.

## Counts after Phase 1

- Active vacancies: 43
- Registered national/government-related sources: 47
- County source placeholders removed: 47
- Vacancies with `View original role` links: 43 / 43

## In scope

- PSC/PSCIMS
- MDAs
- ministries and state departments
- parastatals/SAGAs/state corporations
- constitutional commissions
- independent offices
- Judiciary/Parliament service bodies
- public universities and national training/research bodies
- national public hospitals/health agencies
- all role families

## Out of scope

- county public service boards
- county governments
- county assemblies
- ward/sub-county/local county-only roles

## Important distinction

A duty station such as `Mombasa` or `Nairobi` may still appear in a vacancy because national institutions advertise posts in different locations. That is not county-source coverage.

## Validation

Use:

```bat
VERIFY_PHASE_1.cmd
```

Or:

```bat
py scripts\validate_public_sector_feed.py data\public_sector_feed.json --registry data\source_registry.json
```

## Next phase

Phase 2 should expand the national source registry and collector foundation. The first concrete build should implement:

1. stronger PSCIMS collector;
2. PSC adverts/PDF collector;
3. MyGov/GAA discovery collector;
4. source-health reports;
5. national/parastatal registry enrichment.
