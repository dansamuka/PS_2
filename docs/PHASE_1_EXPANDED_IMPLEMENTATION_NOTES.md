# Phase 1 Expanded Implementation Notes

Generated: 2026-07-20T08:56:35+03:00

## Implemented from the expansion spec

1. Source universe registry: `data/source_registry.json`.
2. Coverage registry and coverage dashboard data: `data/coverage_registry.json` and `data/source_status.json`.
3. Controlled taxonomy: `data/public_sector_taxonomy.json`.
4. Stronger validator enforcing production feed rules, original-role links, official-domain checks and fake-advert triggers.
5. Viewer enhancement: role cards and details now include **View original role** links.
6. Feed contract enhancement: each vacancy has `links.view_original_url` and `provenance[]`.
7. Active actual snapshot retained: 43 vacancies from the previously validated PSCIMS/KSG snapshot.
8. All 47 counties are represented as coverage placeholders requiring official URL confirmation before enabling.
9. Central PSCIMS and MyGov/GAA are explicitly prioritised in the source hierarchy.
10. Rejected/high-risk adverts remain outside the main open-role feed.

## Not yet implemented

- Full PSCIMS detail-page scraper.
- MyGov/GAA PDF parser.
- Live county PSB collectors.
- SAGA/state corporation and commission collectors.
- Public university/hospital/TVET collectors.
- Manual review promotion workflow.
- Link checker using live HTTP requests in CI.

## Next phase

Proceed to **Phase 2 — Core official collectors**:

- PSCIMS active advert/detail collector.
- MyGov/GAA job advert and PDF discovery collector.
- Dedupe between PSCIMS/MyGov/institution pages.
- Live link checking for visible top roles.
