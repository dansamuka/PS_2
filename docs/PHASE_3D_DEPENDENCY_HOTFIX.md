# Phase 3D Dependency Hotfix

Local Windows verification failed when `scripts.collectors.ksg` imported `BeautifulSoup` because `beautifulsoup4` was not installed in the local Python environment.

This hotfix updates:

- `VERIFY_PHASE_3D.cmd` to install `requirements.txt` automatically when required packages are missing.
- `PUSH_TO_GITHUB.cmd` to run the same dependency bootstrap before validation.
- `scripts/verify_phase3d.py` to report missing packages cleanly instead of printing a Python traceback.

GitHub Actions already runs `pip install -r requirements.txt`, so this fix mainly improves local Windows execution.

Manual fallback:

```bat
python -m pip install -r requirements.txt
VERIFY_PHASE_3D.cmd
```
