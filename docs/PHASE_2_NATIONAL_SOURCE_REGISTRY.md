# Phase 2 — National Source Registry Expansion

Generated: 2026-07-20T09:30:40+03:00

## Purpose

Phase 2 expands the source universe for the Kazi Sasa public-sector radar without adding county coverage. The project now focuses on national government, MDAs, state departments, parastatals/SAGAs, commissions, public universities, national public hospitals, public training/research institutions, public funds/authorities, and clearly government-related companies.

## Source basis

The registry is structured around official national directories and public governance references:

- Government of Kenya ministries directory: https://gok.kenya.go.ke/ministries
- Government of Kenya agencies directory: https://gok.kenya.go.ke/agencies
- State Corporations Advisory Committee: https://www.scac.go.ke/
- PSCIMS active adverts: https://pscims.publicservice.go.ke/jobs/ActiveJobsAdverts.aspx

## Current Phase 2 counts

```json
{
  "central_psc": 4,
  "constitutional_commissions": 12,
  "government_advertising_agency": 1,
  "government_funds_authorities": 7,
  "government_linked_companies": 3,
  "independent_offices": 4,
  "judiciary_parliament": 4,
  "ministries": 23,
  "national_health_agencies": 3,
  "public_hospitals": 5,
  "public_training_and_tvet": 5,
  "public_training_institution": 2,
  "public_universities": 38,
  "regulators": 24,
  "research_institutions": 4,
  "sagas_state_corporations": 50,
  "source_registry": 3,
  "state_departments": 47
}
```

Total registered sources: **239**

## What is working now

- Existing actual vacancy feed retained.
- 43 vacancies still validate.
- Source registry is national-only.
- County source coverage is excluded.
- All job families remain in scope.
- View-original links remain mandatory and present in all current vacancy records.

## What is not yet implemented

- Registry-only entries are not live collectors.
- Many sources need exact vacancy/careers URL confirmation before activation.
- Phase 3 must build stronger central collectors for PSCIMS/PSC/MyGov.
- Parastatal/ministry direct scrapers should not be enabled until URL confirmation and validation rules exist.

## Accuracy stance

A source being registered does not mean it is currently scraped. Only enabled sources with successful fetch status should be treated as active data sources. This avoids pretending to have complete coverage before collectors are proven.
