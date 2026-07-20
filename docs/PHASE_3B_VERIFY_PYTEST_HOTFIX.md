# Phase 3B Verify Hotfix — Optional Pytest Handling

The previous Windows verifier treated missing `pytest` as a hard failure even after the core feed validator, Phase 3 verifier, and Phase 3B verifier had all passed.

This hotfix changes `VERIFY_PHASE_3B.cmd` so parser tests run when `pytest` is installed, but are skipped with a clear note when it is not installed.

Core Phase 3B verification remains strict:

```bat
python scripts\validate_public_sector_feed.py data\public_sector_feed.json --registry data\source_registry.json
python scripts\verify_phase3.py
python scripts\verify_phase3b.py
```

Optional parser tests can be run with:

```bat
python -m pip install -r requirements.txt
python -m pytest -q scripts\tests
```
