#!/usr/bin/env python3
"""Phase 3D checks: KSG import reliability and discovery promotion workbench readiness."""
from __future__ import annotations

import importlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def fail(msg):
    print("ERROR:", msg)
    return 1


def _import_or_report(module_name: str):
    try:
        return importlib.import_module(module_name), None
    except ModuleNotFoundError as exc:
        missing = exc.name or str(exc)
        if missing in {"bs4", "requests"}:
            return None, (
                f"missing required Python package `{missing}`. "
                "Run `python -m pip install -r requirements.txt` and retry."
            )
        return None, f"could not import {module_name}: {exc}"
    except Exception as exc:
        return None, f"could not import {module_name}: {type(exc).__name__}: {exc}"


def can_import_ksg_from_repo_root():
    sys.path.insert(0, str(ROOT))
    importlib.invalidate_caches()
    mod, error = _import_or_report("scripts.collectors.ksg")
    if error:
        return False, error
    return hasattr(mod, "collect"), None


def can_import_ksg_from_scripts_path():
    # Mimics `python scripts/refresh_public_sector_feed.py`, where sys.path[0]
    # is usually the scripts directory and collectors is imported as top-level.
    sys.path.insert(0, str(ROOT / "scripts"))
    importlib.invalidate_caches()
    mod, error = _import_or_report("collectors.ksg")
    if error:
        return False, error
    return hasattr(mod, "collect"), None


def main():
    if not (ROOT / "scripts" / "__init__.py").exists():
        return fail("missing scripts/__init__.py")
    ok, err = can_import_ksg_from_repo_root()
    if not ok:
        return fail(err or "cannot import scripts.collectors.ksg from repo root")
    ok, err = can_import_ksg_from_scripts_path()
    if not ok:
        return fail(err or "cannot import collectors.ksg from scripts path")

    feed = load(DATA / "public_sector_feed.json")
    report = load(DATA / "last_run_report.json")
    promo = load(DATA / "discovery_promotion_candidates.json")
    promo_summary = load(DATA / "discovery_promotion_summary.json")
    reviewed = load(DATA / "reviewed_promotions.json")
    if "Phase 3D" not in str(feed.get("meta", {}).get("implementation_phase", "")):
        return fail("feed meta does not identify Phase 3D")
    if "Phase 3D" not in str(report.get("implementation_phase", "")):
        return fail("last_run_report does not identify Phase 3D")
    if promo.get("version") != "3D.1":
        return fail("discovery_promotion_candidates version must be 3D.1")
    if promo_summary.get("candidates_total") != promo.get("generated_count"):
        return fail("promotion summary count does not match candidates file")
    if "reviewed" not in reviewed:
        return fail("reviewed_promotions.json must contain reviewed[]")
    for item in promo.get("candidates", [])[:200]:
        if item.get("can_enter_open_feed") is not False:
            return fail("promotion candidate is allowed into open feed without review")
        if not item.get("needs_manual_review"):
            return fail("promotion candidate missing manual review flag")
    print("OK: Phase 3D KSG import and discovery-promotion workbench checks passed.")
    print(f"Vacancies: {len(feed.get('vacancies', []))}")
    print(f"Discovery promotion candidates: {promo.get('generated_count', 0)}")
    print(f"Ready for manual confirmation: {promo.get('ready_for_manual_confirmation', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
