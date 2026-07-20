# Phase 3D — KSG import hotfix and discovery promotion workbench

Phase 3D has two purposes:

1. **Fix KSG live refresh in GitHub Actions.** The Phase 3C workflow could import PSCIMS and GAA/MyGov, but KSG failed in the GitHub runner with `No module named '_common'`. Phase 3D makes `scripts.collectors.ksg` import-safe in both execution modes used by the project.
2. **Turn GAA/MyGov discovery into a reviewable promotion workbench.** Discovery items still do not enter the open roles feed automatically. Instead, the system prepares structured promotion candidates with missing-field checks and review actions.

## New/updated files

```text
scripts/__init__.py
scripts/discovery_promoter.py
scripts/verify_phase3d.py
scripts/tests/test_phase3d_imports_and_promotion.py
VERIFY_PHASE_3D.cmd
data/discovery_promotion_candidates.json
data/discovery_promotion_summary.json
data/reviewed_promotions.json
```

## Accuracy policy

Discovery records from GAA/MyGov are treated as official discovery leads, not verified open roles. A candidate can only be promoted after a human reviewer confirms:

- hiring institution;
- exact role title(s);
- deadline;
- number of vacancies where available;
- requirements;
- official application channel;
- no payment, free-email, WhatsApp-only or fake application route.

## Expected GitHub Action result

The next workflow run should show:

```text
ksg_jobapplications: records_seen > 0, records_emitted > 0, error: null
mygov_government_advertising_agency: discovery items emitted
promotion_candidates: populated from discovery review queue
```

If GAA/MyGov discovery remains at 120 records, the promotion workbench should generate candidate rows from those items and separate those that are ready for manual confirmation from those requiring extraction or review.
