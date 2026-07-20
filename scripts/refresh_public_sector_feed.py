#!/usr/bin/env python3
"""Kazi Sasa public-sector feed refresh / normalization runner.

Phase 3 adds central-government collectors:
- PSCIMS active adverts -> official live vacancies when reachable.
- MyGov/GAA job adverts -> discovery queue only, not live vacancies until institution/source is verified.
- PSC/public-service reference pages -> source-health monitoring.

Accuracy-first behaviour:
- If a live collector fails, existing validated vacancies are preserved.
- The script never overwrites a good feed with an empty result.
- County coverage remains out of scope.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
EAT = dt.timezone(dt.timedelta(hours=3))
NOW = dt.datetime.now(EAT).isoformat(timespec="seconds")


def load(path, default=None):
    p = pathlib.Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def write(path, obj):
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _is_http_url(value):
    return isinstance(value, str) and value.lower().startswith(("http://", "https://"))


def _safe_original_url(v):
    """Choose a validation-safe original URL.

    ASP.NET grids sometimes expose row detail actions as javascript:__doPostBack(...).
    Those are not valid JSON/feed links, so fall back to the official source URL
    or application URL instead of letting a javascript pseudo-link reach the feed.
    """
    candidates = [
        v.get("links", {}).get("view_original_url"),
        v.get("raw", {}).get("detail_url"),
        v.get("source", {}).get("url"),
        v.get("application", {}).get("apply_url"),
    ]
    for candidate in candidates:
        if _is_http_url(candidate):
            return candidate
    return None


def ensure_links(feed):
    changed = 0
    for v in feed.get("vacancies", []):
        links = v.setdefault("links", {})
        original = _safe_original_url(v)
        current = links.get("view_original_url")
        if original and current != original:
            links["view_original_url"] = original
            links["view_original_label"] = "View original role"
            changed += 1
        elif not current and original:
            links["view_original_url"] = original
            links["view_original_label"] = "View original role"
            changed += 1
        links.setdefault("view_source_url", v.get("source", {}).get("url"))
        links.setdefault("view_apply_url", v.get("application", {}).get("apply_url"))
    return changed


def remove_county_scope(feed):
    kept = []
    dropped = []
    for v in feed.get("vacancies", []):
        prov = (v.get("provenance") or [{}])[0]
        sid = str(prov.get("source_id") or "")
        inst_type = str(v.get("institution", {}).get("type") or "").lower()
        if sid.startswith("county_") or "county_government" in inst_type:
            dropped.append(v.get("id"))
            continue
        kept.append(v)
    feed["vacancies"] = kept
    return dropped


def merge_central_collections(feed, collect_live=False, include_mygov_discovery=True):
    """Return feed with live PSCIMS rows merged and discovery/source-health reports."""
    central_report = {"phase": "Phase 3 — Central government collectors", "collect_live": collect_live, "collectors": []}
    discovery_items = []
    health_items = []
    vacancies = list(feed.get("vacancies", []))

    if collect_live:
        try:
            from scripts.collectors import pscims
        except Exception:
            try:
                from collectors import pscims
            except Exception as exc:
                pscims = None
                central_report["collectors"].append({"source_id": "pscims_active_adverts", "error": f"import failed: {exc}"})
        if pscims:
            pscims_vacancies, meta = pscims.collect()
            central_report["collectors"].append(meta)
            if pscims_vacancies:
                # Replace prior PSCIMS rows with freshly collected PSCIMS rows.
                vacancies = [v for v in vacancies if not (v.get("provenance") or [{}])[0].get("source_id") == "pscims_active_adverts"]
                vacancies.extend(pscims_vacancies)
            else:
                meta["preserved_existing_rows"] = True

        if include_mygov_discovery:
            try:
                from scripts.collectors import mygov
            except Exception:
                try:
                    from collectors import mygov
                except Exception as exc:
                    mygov = None
                    central_report["collectors"].append({"source_id": "mygov_job_adverts", "error": f"import failed: {exc}"})
            if mygov:
                discovery_items, meta = mygov.collect()
                central_report["collectors"].append(meta)

        try:
            from scripts.collectors import official_page_monitor
        except Exception:
            try:
                from collectors import official_page_monitor
            except Exception as exc:
                official_page_monitor = None
                central_report["collectors"].append({"source_id": "official_page_monitor", "error": f"import failed: {exc}"})
        if official_page_monitor:
            health_items = official_page_monitor.monitor()
            central_report["collectors"].append({
                "source_id": "official_page_monitor",
                "records_seen": len(health_items),
                "records_emitted": len(health_items),
                "error": None,
            })

    feed["vacancies"] = sorted(vacancies, key=lambda v: (v.get("advert", {}).get("deadline") or "9999", v.get("title") or ""))
    write(DATA / "discovery_queue.json", {"generated_at": NOW, "items": discovery_items})
    write(DATA / "central_source_health.json", {"generated_at": NOW, "items": health_items})
    write(DATA / "central_collector_report.json", {**central_report, "generated_at": NOW, "discovery_items": len(discovery_items), "health_items": len(health_items)})
    return central_report, discovery_items, health_items


def apply_registry(feed, central_report=None, discovery_items=None, health_items=None):
    reg = load(DATA / "source_registry.json", {"sources": []})
    sources = reg.get("sources", [])
    counts = Counter()
    collector_meta = {m.get("source_id"): m for m in (central_report or {}).get("collectors", []) if isinstance(m, dict)}
    health_meta = {h.get("source_id"): h for h in (health_items or []) if isinstance(h, dict)}

    for v in feed.get("vacancies", []):
        prov = (v.get("provenance") or [{}])[0]
        sid = prov.get("source_id")
        if not sid:
            sid = "pscims_active_adverts" if "PSCIMS" in v.get("source", {}).get("name", "") else "ksg_jobapplications"
            v["provenance"] = [{"source_id": sid, "url": v.get("links", {}).get("view_original_url") or v.get("source", {}).get("url"), "seen_at": NOW}]
        counts[sid] += 1

    discovery_counts = Counter(d.get("source_id") for d in (discovery_items or []) if d.get("source_id"))
    status = []
    for s in sources:
        sid = s.get("source_id")
        cm = collector_meta.get(sid, {})
        hm = health_meta.get(sid, {})
        active_roles = counts.get(sid, 0)
        discovery_count = discovery_counts.get(sid, 0)
        error = cm.get("error") or hm.get("error")
        reachable = hm.get("reachable")
        status_value = s.get("status")
        if active_roles:
            status_value = "active_roles_found"
        elif discovery_count:
            status_value = "discovery_items_found_requires_review"
        elif error:
            status_value = "collector_error"
        elif reachable is True:
            status_value = "reachable_no_structured_roles_captured"
        elif s.get("enabled"):
            status_value = "enabled_no_roles_captured"
        status.append({
            "id": sid,
            "name": s.get("name"),
            "owner": s.get("owner_type"),
            "source_class": s.get("source_group"),
            "enabled": s.get("enabled", False),
            "confidence": s.get("confidence_default"),
            "base_url": s.get("official_url"),
            "collector_type": s.get("collector_type"),
            "coverage_priority": s.get("coverage_priority"),
            "status": status_value,
            "last_checked_at": NOW if (s.get("enabled") or cm or hm) else None,
            "last_successful_fetch_at": NOW if (active_roles or discovery_count or reachable is True or (cm and not cm.get("error"))) else None,
            "active_roles": active_roles,
            "discovery_items": discovery_count,
            "last_error": error,
            "http_status": cm.get("http_status") or hm.get("http_status"),
            "notes": s.get("notes")
        })
    write(DATA / "source_status.json", {"generated_at": NOW, "version": "phase3-central-government", "sources": status})
    feed["source_status"] = status
    return counts, len(sources)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(DATA / "public_sector_feed.json"))
    ap.add_argument("--out", default=str(DATA / "public_sector_feed.json"))
    ap.add_argument("--root-out", default=str(ROOT / "public_sector_feed.json"))
    ap.add_argument("--collect-central", action="store_true", help="Run Phase 3 central collectors. Fallback preserves existing feed if sources fail.")
    ap.add_argument("--no-mygov-discovery", action="store_true", help="Do not write MyGov/GAA discovery queue.")
    args = ap.parse_args()

    feed = load(args.input)
    if not feed:
        print("No input feed found; aborting rather than writing empty feed.")
        return 2

    dropped_county = remove_county_scope(feed)
    changed_links = ensure_links(feed)
    central_report, discovery_items, health_items = merge_central_collections(
        feed,
        collect_live=args.collect_central,
        include_mygov_discovery=not args.no_mygov_discovery,
    )
    changed_links += ensure_links(feed)
    counts, source_count = apply_registry(feed, central_report, discovery_items, health_items)

    feed.setdefault("meta", {})
    feed["meta"].update({
        "feed_version": "3.0-central-government-collectors-phase3",
        "schema_version": "1.3-public-sector-national-only",
        "generated_at": NOW,
        "next_expected_update": (dt.datetime.now(EAT) + dt.timedelta(days=1)).isoformat(timespec="seconds"),
        "vacancy_count": len(feed.get("vacancies", [])),
        "source_count": source_count,
        "is_sample_data": False,
        "scope": "national_government_mdas_parastatals_public_institutions_only_no_counties",
        "role_scope": "all_role_families",
        "implementation_phase": "Phase 3 — Central government collectors",
        "coverage_note": "Phase 3 runs PSCIMS official vacancies, MyGov/GAA discovery queue, and central source-health checks. County sources remain excluded.",
    })
    feed.setdefault("rejected_watchlist", load(DATA / "rejected_watchlist.json", {"items": []}).get("items", []))

    if not feed.get("vacancies"):
        print("Refusing to write empty vacancies[] feed.")
        return 3

    write(args.out, feed)
    write(args.root_out, feed)
    report = {
        "run_id": NOW,
        "started_at": NOW,
        "finished_at": NOW,
        "implementation_phase": "Phase 3 — Central government collectors",
        "collect_central_requested": args.collect_central,
        "vacancies_active": len(feed.get("vacancies", [])),
        "sources_registered": source_count,
        "sources_with_roles": len([k for k, v in counts.items() if v]),
        "discovery_items": len(discovery_items),
        "source_health_checks": len(health_items),
        "county_rows_dropped": len(dropped_county),
        "links_added_or_confirmed": changed_links,
        "quality_gate_status": "pending_validation",
        "central_collectors": central_report.get("collectors", []),
        "note": "PSCIMS official rows can replace prior PSCIMS rows when reachable. MyGov/GAA items are stored in discovery_queue.json for review, not added to open vacancies by default.",
    }
    write(DATA / "last_run_report.json", report)
    print(f"Phase 3 refresh complete. Vacancies: {len(feed.get('vacancies', []))}; registered sources: {source_count}; discovery items: {len(discovery_items)}; health checks: {len(health_items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
