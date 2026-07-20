#!/usr/bin/env python3
"""Kazi Sasa public-sector feed refresh / normalization runner.

Phase 3C adds role identity reconciliation on top of Phase 3B:
- PSCIMS remains the official central public-service collector.
- MyGov/GAA discovery tries current and legacy URLs rather than failing on one 404.
- KSG is refreshed as a live institutional-portal source when reachable.
- Expired roles are marked as expired so the viewer hides them from Open roles by default.
- Each run writes a reconciled change summary so refreshed existing roles are not miscounted as new.
- Discovery items are converted into a manual review queue for promotion into open roles.

Accuracy-first behaviour:
- If a live collector fails, existing validated vacancies are preserved.
- The script never overwrites a good feed with an empty result.
- Discovery-only items stay in discovery_queue.json until reviewed.
- County coverage remains out of scope.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import pathlib
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
EAT = dt.timezone(dt.timedelta(hours=3))
NOW_DT = dt.datetime.now(EAT)
NOW = NOW_DT.isoformat(timespec="seconds")

try:
    from scripts.role_identity import (
        annotate_vacancies,
        build_discovery_review_queue,
        build_reconciled_change_summary,
        identity_map,
        write_json as write_identity_json,
    )
except Exception:  # pragma: no cover - local script execution fallback
    from role_identity import (
        annotate_vacancies,
        build_discovery_review_queue,
        build_reconciled_change_summary,
        identity_map,
        write_json as write_identity_json,
    )


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


def _source_id(v):
    return (v.get("provenance") or [{}])[0].get("source_id")


def _is_expired(v, now_dt=NOW_DT):
    deadline = v.get("advert", {}).get("deadline")
    if not deadline:
        return False
    try:
        d = dt.datetime.fromisoformat(str(deadline).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=EAT)
        return d.astimezone(EAT) < now_dt
    except Exception:
        return False


def mark_expired_roles(feed):
    expired = []
    for v in feed.get("vacancies", []):
        if not _is_expired(v):
            continue
        verification = v.setdefault("verification", {})
        if verification.get("status") != "expired":
            verification["status"] = "expired"
            notes = verification.get("notes") or ""
            verification["notes"] = (notes + " Expired by automated deadline check.").strip()
        flags = verification.setdefault("risk_flags", [])
        if "expired_deadline" not in flags:
            flags.append("expired_deadline")
        expired.append(v.get("id"))
    return expired


def remove_county_scope(feed):
    kept = []
    dropped = []
    for v in feed.get("vacancies", []):
        sid = str(_source_id(v) or "")
        inst_type = str(v.get("institution", {}).get("type") or "").lower()
        if sid.startswith("county_") or "county_government" in inst_type:
            dropped.append(v.get("id"))
            continue
        kept.append(v)
    feed["vacancies"] = kept
    return dropped


def _replace_source(vacancies, source_id, new_rows):
    if not new_rows:
        return vacancies
    return [v for v in vacancies if _source_id(v) != source_id] + list(new_rows)


def merge_central_collections(feed, collect_live=False, include_mygov_discovery=True):
    """Return feed with live central rows merged and discovery/source-health reports."""
    central_report = {"phase": "Phase 3C — Role identity reconciliation", "collect_live": collect_live, "collectors": []}
    discovery_items = []
    health_items = []
    vacancies = list(feed.get("vacancies", []))

    if collect_live:
        # PSCIMS official live vacancies.
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
                vacancies = _replace_source(vacancies, "pscims_active_adverts", pscims_vacancies)
            else:
                meta["preserved_existing_rows"] = True

        # KSG live institutional portal, kept as needs_review.
        try:
            from scripts.collectors import ksg
        except Exception:
            try:
                from collectors import ksg
            except Exception as exc:
                ksg = None
                central_report["collectors"].append({"source_id": "ksg_jobapplications", "error": f"import failed: {exc}"})
        if ksg:
            ksg_vacancies, meta = ksg.collect()
            central_report["collectors"].append(meta)
            if ksg_vacancies:
                vacancies = _replace_source(vacancies, "ksg_jobapplications", ksg_vacancies)
            else:
                meta["preserved_existing_rows"] = True

        # MyGov/GAA discovery only.
        if include_mygov_discovery:
            try:
                from scripts.collectors import mygov
            except Exception:
                try:
                    from collectors import mygov
                except Exception as exc:
                    mygov = None
                    central_report["collectors"].append({"source_id": "mygov_government_advertising_agency", "error": f"import failed: {exc}"})
            if mygov:
                discovery_items, meta = mygov.collect()
                central_report["collectors"].append(meta)

        # Central source-health.
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


def _stable_compare_projection(v):
    """Projection used for change detection, excluding volatile fetch timestamps."""
    return {
        "title": v.get("title"),
        "institution": v.get("institution", {}).get("name"),
        "deadline": v.get("advert", {}).get("deadline"),
        "vacancies": v.get("advert", {}).get("number_of_vacancies"),
        "verification": v.get("verification", {}).get("status"),
        "source_id": _source_id(v),
        "view_original_url": v.get("links", {}).get("view_original_url"),
    }


def build_change_summary(before_vacancies, after_vacancies, expired_ids=None, dropped_county=None):
    before = {v.get("id"): v for v in before_vacancies if v.get("id")}
    after = {v.get("id"): v for v in after_vacancies if v.get("id")}
    before_ids = set(before)
    after_ids = set(after)
    new_ids = sorted(after_ids - before_ids)
    removed_ids = sorted(before_ids - after_ids)
    common = before_ids & after_ids
    updated_ids = sorted(i for i in common if _stable_compare_projection(before[i]) != _stable_compare_projection(after[i]))
    return {
        "new_roles": len(new_ids),
        "updated_roles": len(updated_ids),
        "removed_roles": len(removed_ids),
        "expired_roles": len(expired_ids or []),
        "county_rows_dropped": len(dropped_county or []),
        "unchanged_roles": max(0, len(after_ids) - len(new_ids) - len(updated_ids)),
        "new_role_ids": new_ids[:50],
        "updated_role_ids": updated_ids[:50],
        "removed_role_ids": removed_ids[:50],
        "expired_role_ids": list(expired_ids or [])[:50],
    }


def apply_registry(feed, central_report=None, discovery_items=None, health_items=None):
    reg = load(DATA / "source_registry.json", {"sources": []})
    sources = reg.get("sources", [])
    counts = Counter()
    collector_meta = {m.get("source_id"): m for m in (central_report or {}).get("collectors", []) if isinstance(m, dict)}
    health_meta = {h.get("source_id"): h for h in (health_items or []) if isinstance(h, dict)}

    for v in feed.get("vacancies", []):
        sid = _source_id(v)
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
            "notes": s.get("notes"),
        })
    write(DATA / "source_status.json", {"generated_at": NOW, "version": "phase3c-role-identity-reconciliation", "sources": status})
    feed["source_status"] = status
    return counts, len(sources)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(DATA / "public_sector_feed.json"))
    ap.add_argument("--out", default=str(DATA / "public_sector_feed.json"))
    ap.add_argument("--root-out", default=str(ROOT / "public_sector_feed.json"))
    ap.add_argument("--collect-central", action="store_true", help="Run central/latest collectors. Fallback preserves existing feed if sources fail.")
    ap.add_argument("--no-mygov-discovery", action="store_true", help="Do not write MyGov/GAA discovery queue.")
    args = ap.parse_args()

    feed = load(args.input)
    if not feed:
        print("No input feed found; aborting rather than writing empty feed.")
        return 2

    before_vacancies = copy.deepcopy(feed.get("vacancies", []))
    dropped_county = remove_county_scope(feed)
    changed_links = ensure_links(feed)
    central_report, discovery_items, health_items = merge_central_collections(
        feed,
        collect_live=args.collect_central,
        include_mygov_discovery=not args.no_mygov_discovery,
    )
    changed_links += ensure_links(feed)
    expired_ids = mark_expired_roles(feed)
    counts, source_count = apply_registry(feed, central_report, discovery_items, health_items)
    annotate_vacancies(feed.get("vacancies", []))
    change_summary = build_reconciled_change_summary(before_vacancies, feed.get("vacancies", []), expired_ids=expired_ids, dropped_county=dropped_county)
    role_map = identity_map(feed.get("vacancies", []))
    discovery_review = build_discovery_review_queue(discovery_items)
    write_identity_json(DATA / "role_identity_map.json", {**role_map, "generated_at": NOW})
    write_identity_json(DATA / "discovery_review_queue.json", {**discovery_review, "generated_at": NOW})
    write_identity_json(DATA / "discovery_review_summary.json", {"generated_at": NOW, "items_total": discovery_review.get("generated_count", 0), "priority_counts": discovery_review.get("priority_counts", {}), "promotion_policy": discovery_review.get("promotion_policy")})

    feed.setdefault("meta", {})
    feed["meta"].update({
        "feed_version": "3.2-role-identity-reconciliation-phase3c",
        "schema_version": "1.3-public-sector-national-only",
        "generated_at": NOW,
        "next_expected_update": (dt.datetime.now(EAT) + dt.timedelta(days=1)).isoformat(timespec="seconds"),
        "vacancy_count": len(feed.get("vacancies", [])),
        "source_count": source_count,
        "is_sample_data": False,
        "scope": "national_government_mdas_parastatals_public_institutions_only_no_counties",
        "role_scope": "all_role_families",
        "implementation_phase": "Phase 3C — Role identity reconciliation",
        "phase": "Phase 3C — Role identity reconciliation",
        "coverage_note": "Phase 3C reconciles refreshed roles by canonical identity, keeps KSG/PSCIMS live ingestion, filters generic listing rows, and prepares MyGov/GAA discovery items for manual review.",
        "change_summary": change_summary,
    })
    q = feed.setdefault("meta", {}).setdefault("quality_summary", {})
    q.update({
        "expired_roles": len(expired_ids),
        "latest_ingestion_phase": "3C",
        "identity_reconciled_roles_last_run": change_summary.get("identity_reconciled_roles", 0),
        "genuine_new_roles_last_run": change_summary.get("genuine_new_roles", change_summary.get("new_roles", 0)),
        "new_roles_last_run": change_summary["new_roles"],
        "updated_roles_last_run": change_summary["updated_roles"],
        "discovery_items_last_run": len(discovery_items),
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
        "implementation_phase": "Phase 3C — Role identity reconciliation",
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
        "change_summary": change_summary,
        "note": "Phase 3C reconciles refreshed PSCIMS/KSG roles by canonical identity and prepares MyGov/GAA discovery items for manual review, not automatic promotion.",
        "role_identity_map_count": role_map.get("role_count", 0),
        "discovery_review_items": discovery_review.get("generated_count", 0),
    }
    write(DATA / "last_run_report.json", report)
    print(
        "Phase 3C refresh complete. "
        f"Vacancies: {len(feed.get('vacancies', []))}; registered sources: {source_count}; "
        f"genuine_new: {change_summary.get('genuine_new_roles', change_summary['new_roles'])}; updated: {change_summary['updated_roles']}; reconciled: {change_summary.get('identity_reconciled_roles', 0)}; "
        f"expired: {change_summary['expired_roles']}; discovery: {len(discovery_items)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
