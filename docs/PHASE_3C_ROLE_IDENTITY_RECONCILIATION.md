# Phase 3C — Role Identity Reconciliation

Phase 3C fixes the main reporting weakness discovered after Phase 3B: live KSG refreshes produced new row IDs, so the system counted refreshed existing roles as brand-new roles and marked the old snapshot rows as removed.

## What Phase 3C adds

- Stable canonical role identity using institution, title, deadline, location and advert number where available.
- `identity.canonical_key` on every vacancy.
- `data/role_identity_map.json` for traceability from volatile row IDs to stable role identities.
- Reconciled change reporting:
  - `genuine_new_roles`
  - `updated_roles`
  - `identity_reconciled_roles`
  - `refreshed_existing_roles`
  - `genuine_removed_roles`
- KSG generic listing filter so non-role page headings such as “Advertised Vacancies...” do not appear as vacancies.
- `data/discovery_review_queue.json` and `data/discovery_review_summary.json` so GAA/MyGov discovery items can be manually triaged toward promotion into verified/open roles.

## Why this matters

A scraper refresh can change technical IDs without the underlying job changing. Phase 3C therefore compares canonical job identities instead of raw `id` fields. This makes the refresh banner and `last_run_report.json` more honest.

## Promotion policy for discovery items

GAA/MyGov discovery items are not automatically promoted into open vacancies. A discovery item must first pass manual review:

1. Open the original GAA/MyGov page or PDF.
2. Confirm the hiring institution.
3. Confirm the official application channel.
4. Extract deadline, requirements and vacancy count.
5. Reject if the channel is Gmail/WhatsApp/payment-based or not officially supported.

## Local verification

```bat
VERIFY_PHASE_3C.cmd
```

## Live refresh

```bat
python scripts\refresh_public_sector_feed.py --collect-central
```

## Expected result after GitHub Action

The next successful action should report true role movement, for example:

```text
Genuine new roles: 0
Identity-reconciled roles: many KSG rows if IDs changed
Discovery review items: number of GAA/MyGov discovery records
```

This prepares the project for the next role-yielding phase: reviewing/promoting central advert discovery items into verified open roles.
