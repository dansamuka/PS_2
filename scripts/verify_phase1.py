#!/usr/bin/env python3
"""Phase 1 local smoke checks for the PS_2 public-sector viewer package."""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
for rel in ["index.html", "kenya_public_sector_viewer.html", "data/public_sector_feed.json", "data/source_registry.json", "PUSH_TO_GITHUB.cmd"]:
    if not (ROOT / rel).exists():
        print(f"ERROR: missing {rel}")
        sys.exit(1)
feed = json.loads((ROOT / "data/public_sector_feed.json").read_text(encoding="utf-8"))
reg = json.loads((ROOT / "data/source_registry.json").read_text(encoding="utf-8"))
problems = []
for s in reg.get("sources", []):
    blob = " ".join(str(s.get(k, "")) for k in ("source_id", "source_group", "owner_type", "name")).lower()
    if any(x in blob for x in ("county_psb", "county_assembly", "county_government")):
        problems.append("county source in registry: " + str(s.get("source_id")))
for s in feed.get("source_status", []):
    blob = " ".join(str(s.get(k, "")) for k in ("id", "source_class", "owner", "name")).lower()
    if any(x in blob for x in ("county_psb", "county_assembly", "county_government")):
        problems.append("county source in feed source_status: " + str(s.get("id")))
for v in feed.get("vacancies", []):
    if not v.get("links", {}).get("view_original_url"):
        problems.append("missing view original: " + v.get("id", "<missing>"))
if feed.get("meta", {}).get("scope") != "national_government_and_government_related_only":
    problems.append("meta.scope is not national_government_and_government_related_only")
if feed.get("meta", {}).get("role_scope") != "all_job_families":
    problems.append("meta.role_scope is not all_job_families")
if "https://github.com/dansamuka/PS_2.git" not in (ROOT / "PUSH_TO_GITHUB.cmd").read_text(encoding="utf-8"):
    problems.append("PUSH_TO_GITHUB.cmd does not default to PS_2")
if problems:
    for p in problems:
        print("ERROR:", p)
    sys.exit(1)
print("OK: Phase 1 smoke checks passed.")
print(f"Vacancies: {len(feed.get('vacancies', []))}")
print(f"Sources registered: {len(reg.get('sources', []))}")
print(f"View-original links: {sum(1 for v in feed.get('vacancies', []) if v.get('links', {}).get('view_original_url'))}")
