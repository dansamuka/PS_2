#!/usr/bin/env python3
"""Stable role identity and discovery-review helpers for PS_2.

Phase 3C separates a vacancy's volatile feed row ID from the underlying job identity.
This prevents a live collector from reporting the same KSG role as new merely because
its generated ID changed between the original snapshot and a refreshed scrape.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import re
from collections import defaultdict
from typing import Iterable

EAT = dt.timezone(dt.timedelta(hours=3))

_WORD_FIXES = {
    "airtisan": "artisan",
    "techhnician": "technician",
    "maintainance": "maintenance",
    "maintainance": "maintenance",
    "recieptionist": "receptionist",
    "recptionist": "receptionist",
    "cashier": "cashier",
}
_ROMAN = {
    "i": "1",
    "ii": "2",
    "iii": "3",
    "iv": "4",
    "v": "5",
}
_GENERIC_TITLE_PATTERNS = [
    re.compile(r"\badvertised\s+vacanc(?:y|ies)\b", re.I),
    re.compile(r"\bopen\s+vacanc(?:y|ies)\b", re.I),
    re.compile(r"\bjob\s+advert(?:s|isement)?\b", re.I),
]


def compact_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalise_text(value: str | None) -> str:
    text = compact_text(value).lower()
    for wrong, right in _WORD_FIXES.items():
        text = re.sub(rf"\b{re.escape(wrong)}\b", right, text)
    text = text.replace("&", " and ")
    text = re.sub(r"\[(?:\d+)\]", " ", text)
    text = re.sub(r"[()/_.,;:\\-]+", " ", text)
    words = []
    for w in re.findall(r"[a-z0-9]+", text):
        words.append(_ROMAN.get(w, w))
    return " ".join(words)


def canonical_title(title: str | None) -> str:
    text = normalise_text(title)
    if text == "senior account":
        text = "senior accountant"
    return text


def canonical_institution(value: str | None) -> str:
    text = normalise_text(value)
    text = text.replace("the ", "") if text.startswith("the ") else text
    return text


def canonical_location(value: str | None) -> str:
    text = normalise_text(value)
    # Keep multi-station postings stable without overfitting order from punctuation.
    if not text:
        return "kenya"
    parts = sorted({p for p in text.split() if p not in {"and", "or", "all"}})
    return " ".join(parts) or "kenya"


def canonical_date(value: str | None) -> str:
    if not value:
        return "deadline_unknown"
    text = str(value).strip()
    try:
        d = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        return d.date().isoformat()
    except Exception:
        pass
    m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
    if m:
        y, mo, da = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(da):02d}"
    return normalise_text(text) or "deadline_unknown"


def canonical_advert_number(value: str | None) -> str:
    text = compact_text(value).upper()
    if not text or text in {"N/A", "NA", "NONE", "UNKNOWN"}:
        return ""
    return re.sub(r"\s+", "", text)


def is_generic_listing_title(title: str | None) -> bool:
    text = compact_text(title)
    if not text:
        return True
    if any(p.search(text) for p in _GENERIC_TITLE_PATTERNS):
        return True
    # Portal landing-page labels often include stations but no real job family.
    if len(text.split()) > 10 and not re.search(r"\b(officer|assistant|manager|accountant|auditor|driver|cook|artisan|attendant|waiter|technician|secretary|clerk|engineer|analyst|warden|house\s*keeper|chef|operator)\b", text, re.I):
        return True
    return False


def source_id(v: dict) -> str:
    return str((v.get("provenance") or [{}])[0].get("source_id") or v.get("source", {}).get("source_id") or "unknown_source")


def role_identity_fields(v: dict) -> dict:
    institution = v.get("institution", {}).get("name") or v.get("institution", {}).get("hiring_body") or ""
    title = v.get("title") or ""
    advert_no = canonical_advert_number(v.get("advert", {}).get("advert_number"))
    deadline = canonical_date(v.get("advert", {}).get("deadline"))
    location = v.get("location", {}).get("raw") or "Kenya"
    return {
        "source_id": source_id(v),
        "institution": canonical_institution(institution),
        "title": canonical_title(title),
        "deadline": deadline,
        "location": canonical_location(location),
        "advert_number": advert_no,
    }


def role_identity_key(v: dict) -> str:
    f = role_identity_fields(v)
    # Advert numbers are stronger than scraped IDs and usually cross-post across PSC/MyGov.
    if f["advert_number"]:
        raw = f"advert|{f['institution']}|{f['advert_number']}"
    else:
        raw = f"role|{f['institution']}|{f['title']}|{f['deadline']}|{f['location']}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"rid_{digest}"


def annotate_role_identity(v: dict) -> dict:
    fields = role_identity_fields(v)
    key = role_identity_key(v)
    v["identity"] = {
        "canonical_key": key,
        "canonical_fields": fields,
        "row_id": v.get("id"),
        "reconciliation_version": "3C.1",
    }
    return v


def annotate_vacancies(vacancies: Iterable[dict]) -> list[dict]:
    return [annotate_role_identity(v) for v in vacancies]


def identity_map(vacancies: Iterable[dict]) -> dict:
    by_key = defaultdict(list)
    for v in vacancies:
        key = role_identity_key(v)
        by_key[key].append(v)
    roles = []
    for key, rows in sorted(by_key.items()):
        first = rows[0]
        roles.append({
            "canonical_key": key,
            "title": first.get("title"),
            "institution": first.get("institution", {}).get("name"),
            "deadline": first.get("advert", {}).get("deadline"),
            "current_ids": sorted({r.get("id") for r in rows if r.get("id")}),
            "source_ids": sorted({source_id(r) for r in rows}),
            "row_count": len(rows),
        })
    return {
        "version": "3C.1",
        "role_count": len(roles),
        "roles": roles,
    }


def stable_projection(v: dict) -> dict:
    """Fields that indicate meaningful role updates, excluding volatile IDs/timestamps."""
    annotate_role_identity(v)
    return {
        "identity": v.get("identity", {}).get("canonical_key"),
        "title": canonical_title(v.get("title")),
        "display_title": compact_text(v.get("title")),
        "institution": canonical_institution(v.get("institution", {}).get("name")),
        "deadline": canonical_date(v.get("advert", {}).get("deadline")),
        "vacancies": v.get("advert", {}).get("number_of_vacancies"),
        "verification": v.get("verification", {}).get("status"),
        "source_confidence": v.get("source", {}).get("confidence"),
        "view_original_url": v.get("links", {}).get("view_original_url"),
    }


def build_reconciled_change_summary(before_vacancies: list[dict], after_vacancies: list[dict], *, expired_ids=None, dropped_county=None) -> dict:
    before_rows = [annotate_role_identity(v) for v in before_vacancies]
    after_rows = [annotate_role_identity(v) for v in after_vacancies]
    before_by_key = {v["identity"]["canonical_key"]: v for v in before_rows}
    after_by_key = {v["identity"]["canonical_key"]: v for v in after_rows}
    before_keys = set(before_by_key)
    after_keys = set(after_by_key)
    new_keys = sorted(after_keys - before_keys)
    removed_keys = sorted(before_keys - after_keys)
    common_keys = sorted(before_keys & after_keys)
    updated_keys = [k for k in common_keys if stable_projection(before_by_key[k]) != stable_projection(after_by_key[k])]
    reconciled_pairs = []
    refreshed_same_identity = []
    for k in common_keys:
        old_id = before_by_key[k].get("id")
        new_id = after_by_key[k].get("id")
        if old_id != new_id:
            reconciled_pairs.append({"canonical_key": k, "old_id": old_id, "new_id": new_id, "title": after_by_key[k].get("title")})
        else:
            refreshed_same_identity.append(new_id)
    return {
        # Backward-compatible fields; these now mean genuine canonical identities.
        "new_roles": len(new_keys),
        "updated_roles": len(updated_keys),
        "removed_roles": len(removed_keys),
        "expired_roles": len(expired_ids or []),
        "county_rows_dropped": len(dropped_county or []),
        "unchanged_roles": max(0, len(after_keys) - len(new_keys) - len(updated_keys)),
        "new_role_ids": [after_by_key[k].get("id") for k in new_keys[:50]],
        "updated_role_ids": [after_by_key[k].get("id") for k in updated_keys[:50]],
        "removed_role_ids": [before_by_key[k].get("id") for k in removed_keys[:50]],
        "expired_role_ids": list(expired_ids or [])[:50],
        # Phase 3C explicit reconciliation fields.
        "genuine_new_roles": len(new_keys),
        "genuine_removed_roles": len(removed_keys),
        "identity_reconciled_roles": len(reconciled_pairs),
        "refreshed_existing_roles": len(common_keys),
        "row_id_replacements": len(reconciled_pairs),
        "canonical_roles_before": len(before_keys),
        "canonical_roles_after": len(after_keys),
        "reconciled_role_pairs": reconciled_pairs[:50],
    }


def discovery_review_record(item: dict) -> dict:
    title = compact_text(item.get("title"))
    institution = compact_text(item.get("institution"))
    url = item.get("view_original_url") or item.get("attachment_url") or item.get("source_url")
    text = f"{title} {institution}".lower()
    score = 0
    for kw in ["vacancy", "vacancies", "recruitment", "career", "job", "positions", "public service", "commission", "university", "authority", "ministry"]:
        if kw in text:
            score += 10
    if str(url or "").lower().endswith(".pdf"):
        score += 20
    if item.get("source_confidence") in {"official_discovery", "official"}:
        score += 20
    if title and len(title) >= 8:
        score += 10
    priority = "high" if score >= 50 else "medium" if score >= 30 else "low"
    review_status = "needs_hiring_institution_confirmation"
    return {
        "id": item.get("id") or hashlib.sha1(f"{title}|{institution}|{url}".encode()).hexdigest()[:16],
        "title": title,
        "institution": institution,
        "source_id": item.get("source_id"),
        "source_confidence": item.get("source_confidence"),
        "view_original_url": url,
        "attachment_url": item.get("attachment_url"),
        "seen_at": item.get("seen_at"),
        "review_priority": priority,
        "review_score": score,
        "promotion_status": review_status,
        "can_auto_promote": False,
        "manual_checks_required": [
            "Open the original GAA/MyGov item or PDF",
            "Confirm the hiring institution and official application channel",
            "Extract deadline, role title, requirements and number of vacancies",
            "Reject if application channel is Gmail/WhatsApp/payment-based or unofficial",
        ],
    }


def build_discovery_review_queue(discovery_items: Iterable[dict]) -> dict:
    records = [discovery_review_record(x) for x in discovery_items]
    records.sort(key=lambda r: ({"high": 0, "medium": 1, "low": 2}.get(r["review_priority"], 9), -r["review_score"], r["title"]))
    counts = defaultdict(int)
    for r in records:
        counts[r["review_priority"]] += 1
    return {
        "version": "3C.1",
        "generated_count": len(records),
        "priority_counts": dict(sorted(counts.items())),
        "promotion_policy": "Discovery items never enter open vacancies automatically. Review and confirm the hiring institution first.",
        "items": records,
    }


def write_json(path: str | pathlib.Path, obj: dict):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
