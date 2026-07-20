#!/usr/bin/env python3
"""Shared helpers for central-government collectors.

Accuracy policy:
- Collectors may emit official vacancies only when they can point to an official source URL.
- Discovery items that cannot be confirmed as still open should go to discovery_queue.json, not the live vacancies[] feed.
- No Gmail/WhatsApp/payment-request records are allowed into open vacancies.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import re
from typing import Iterable, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

EAT = dt.timezone(dt.timedelta(hours=3))
USER_AGENT = "KaziSasaPublicSectorRadar/0.3 (+private accuracy-first vacancy monitor)"


def now_iso() -> str:
    return dt.datetime.now(EAT).isoformat(timespec="seconds")


def fetch_html(url: str, timeout: int = 25) -> tuple[str, int, str | None]:
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        )
        resp.raise_for_status()
        return resp.text, resp.status_code, None
    except Exception as exc:  # pragma: no cover - network-dependent
        return "", 0, f"{type(exc).__name__}: {exc}"


def soup_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    return soup.get_text("\n", strip=True)


def stable_id(*parts: str, prefix: str = "ps") -> str:
    raw = "|".join(str(p or "").strip().lower() for p in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    slug = re.sub(r"[^a-z0-9]+", "_", raw)[:55].strip("_")
    return f"{prefix}_{slug}_{digest}" if slug else f"{prefix}_{digest}"


def parse_date(value: str | None, default_year: int | None = None) -> str | None:
    if not value:
        return None
    text = str(value).strip().replace(",", " ").replace("  ", " ")
    # Common PSCIMS dd-mm-yyyy
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d %B %Y", "%d %b %Y"):
        try:
            return dt.datetime.strptime(text, fmt).date().isoformat()
        except Exception:
            pass
    # Common MyGov: 14th April, 2026 / 17th February 2026
    cleaned = re.sub(r"(\d{1,2})(st|nd|rd|th)", r"\1", text, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    for fmt in ("%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y"):
        try:
            return dt.datetime.strptime(cleaned, fmt).date().isoformat()
        except Exception:
            pass
    # If day/month with no year and default year provided.
    if default_year:
        for fmt in ("%d %B", "%d %b"):
            try:
                d = dt.datetime.strptime(cleaned, fmt).replace(year=default_year).date()
                return d.isoformat()
            except Exception:
                pass
    return None


def deadline_iso(date_str: str | None) -> str | None:
    if not date_str:
        return None
    try:
        d = dt.date.fromisoformat(date_str)
        return dt.datetime(d.year, d.month, d.day, 23, 59, tzinfo=EAT).isoformat(timespec="seconds")
    except Exception:
        return None


def clean_title(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    text = text.replace(" : ", ": ")
    return text


def infer_job_family(title: str, organisation: str = "") -> list[str]:
    t = f"{title} {organisation}".lower()
    rules = [
        ("customer_service", ["customer", "call centre", "contact centre", "service desk"]),
        ("administration", ["admin", "administrative", "office assistant", "secretary"]),
        ("clerical_records", ["clerical", "records", "registry", "data entry", "registration"]),
        ("finance_accounting", ["accountant", "finance", "accounts", "treasury", "cashier"]),
        ("audit", ["audit", "auditor", "assurance", "risk"]),
        ("ict_data", ["ict", "information", "system", "data", "database", "cyber", "digital"]),
        ("legal", ["legal", "counsel", "advocate", "law", "corporation secretary"]),
        ("procurement_supply_chain", ["procurement", "supply", "stores", "logistics"]),
        ("hr", ["human resource", "hr", "people", "personnel"]),
        ("communications", ["communication", "public relations", "corporate affairs", "media"]),
        ("engineering_technical", ["engineer", "technician", "technical", "artisan", "mechanic", "electrician"]),
        ("driver_transport", ["driver", "transport"]),
        ("security", ["security", "warden", "guard"]),
        ("hospitality", ["cook", "hotel", "housekeeping", "cater", "receptionist", "attendant"]),
        ("health", ["medical", "clinical", "nurse", "pharmaceutical", "laboratory", "health"]),
        ("education_training", ["teacher", "lecturer", "trainer", "instructor", "curriculum"]),
        ("research_policy", ["research", "policy", "planning", "economist", "statistic"]),
        ("leadership_management", ["chief executive", "ceo", "director general", "general manager", "manager", "commissioner"]),
        ("internship_graduate", ["intern", "graduate trainee", "trainee"]),
    ]
    found = [label for label, keys in rules if any(k in t for k in keys)]
    return found or ["public_service_general"]


def sanitize_keywords(*parts: str, limit: int = 14) -> list[str]:
    raw = " ".join(str(p or "") for p in parts).lower()
    words = re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", raw)
    stop = {"the", "and", "for", "with", "into", "position", "positions", "vacancy", "vacancies", "job", "jobs", "career", "opportunities"}
    out = []
    for w in words:
        w = w.strip("-")
        if w in stop or w in out:
            continue
        out.append(w)
        if len(out) >= limit:
            break
    return out


def build_vacancy(
    *,
    vid: str,
    title: str,
    institution: str,
    source_name: str,
    source_url: str,
    source_id: str,
    source_confidence: str,
    source_type: str,
    view_original_url: str,
    apply_url: str | None = None,
    advert_number: str | None = None,
    job_scale: str | None = None,
    number_of_vacancies: int | None = None,
    advert_date: str | None = None,
    deadline: str | None = None,
    deadline_confidence: str = "unknown",
    years_experience_minimum: int | None = None,
    location_raw: str = "Kenya",
    employment_type: str = "public_service",
    terms: str = "public_service",
    requirements_text: str | None = None,
    verification_status: str = "verified",
    risk_flags: list[str] | None = None,
    evidence_type: str = "official_page",
    http_status: int | None = 200,
) -> dict:
    title = clean_title(title)
    institution = clean_title(institution or "Government of Kenya")
    families = infer_job_family(title, institution)
    official_domain = urlparse(source_url).netloc.replace("www.", "")
    now = now_iso()
    apply_url = apply_url or view_original_url or source_url
    return {
        "id": vid,
        "title": title,
        "institution": {
            "name": institution,
            "hiring_body": institution,
            "type": "national_government_or_public_body",
            "official_domain": official_domain,
        },
        "source": {
            "name": source_name,
            "url": source_url,
            "source_type": source_type,
            "confidence": source_confidence,
            "last_checked_at": now,
            "http_status": http_status,
        },
        "advert": {
            "advert_number": advert_number,
            "job_scale": job_scale,
            "number_of_vacancies": number_of_vacancies or 1,
            "advert_date": advert_date,
            "deadline": deadline,
            "deadline_confidence": deadline_confidence,
        },
        "location": {
            "raw": location_raw,
            "county": None,
            "region": "national",
            "duty_station": location_raw,
        },
        "employment": {
            "type": employment_type,
            "terms": terms,
            "department": None,
        },
        "requirements": {
            "education_minimum": None,
            "kcse_minimum": None,
            "years_experience_minimum": years_experience_minimum,
            "professional_body": None,
            "computer_proficiency_required": bool(re.search(r"computer", requirements_text or "", re.I)),
            "chapter_six_required": bool(re.search(r"chapter\s+six|chapter 6", requirements_text or "", re.I)),
            "mandatory_text": requirements_text or f"Review the original advert/source page before applying: {view_original_url}",
        },
        "job_family": families,
        "keywords": sanitize_keywords(title, institution, *(families or [])),
        "application": {
            "mode": "online_portal" if apply_url else "review_original_source",
            "apply_url": apply_url,
            "requires_login": "pscims" in (apply_url or ""),
            "requires_email_submission": False,
            "email": None,
            "fee_required": False,
        },
        "verification": {
            "status": verification_status,
            "risk_flags": risk_flags or [],
            "notes": "Captured from central government source. Verify details on the original site before applying." if verification_status != "verified" else "Captured from official central-government source.",
        },
        "raw": {
            "html_hash": None,
            "pdf_url": view_original_url if str(view_original_url).lower().endswith(".pdf") else None,
            "screenshot_path": None,
        },
        "links": {
            "view_original_url": view_original_url,
            "view_original_label": "View original role",
            "view_source_url": source_url,
            "view_apply_url": apply_url,
        },
        "provenance": [
            {
                "source_id": source_id,
                "url": view_original_url or source_url,
                "seen_at": now,
                "evidence_type": evidence_type,
            }
        ],
        "scope": "national_government_or_government_related",
    }
