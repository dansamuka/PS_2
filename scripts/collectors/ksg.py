#!/usr/bin/env python3
"""Kenya School of Government application-portal collector.

KSG is currently the highest-yield source in the viewer, but earlier packages retained it
as a static snapshot. This collector refreshes the KSG portal when reachable while keeping
its records as `needs_review` until the portal's official linkage is reconfirmed.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

try:
    from ._common import build_vacancy, clean_title, deadline_iso, fetch_html, parse_date, stable_id
except ImportError:  # pragma: no cover
    from _common import build_vacancy, clean_title, deadline_iso, fetch_html, parse_date, stable_id

SOURCE_ID = "ksg_jobapplications"
KSG_URL = "https://jobapplications.ke/"
LOGIN_URL = "https://jobapplications.ke/client/login"
SOURCE_NAME = "Kenya School of Government Job Application Portal"


def _int_or_none(value: str | None):
    try:
        return int(str(value).replace(",", "").strip())
    except Exception:
        return None


def _safe_url(href: str | None, base: str = KSG_URL) -> str | None:
    if not href:
        return None
    href = href.strip()
    if not href or href.lower().startswith(("javascript:", "#", "mailto:", "tel:")):
        return None
    resolved = urljoin(base, href)
    if resolved.lower().startswith(("http://", "https://")):
        return resolved
    return None


def _field(text: str, name: str) -> str | None:
    # Capture `Name: value` until the next likely label.
    pat = re.compile(
        rf"{re.escape(name)}\s*[:\-]\s*(.*?)\s*(?=(Department|Location|Positions|Type|Deadline|Mandatory Requirements|For appointment|$)\s*[:\-]?)",
        re.I | re.S,
    )
    m = pat.search(text or "")
    if not m:
        return None
    return clean_title(m.group(1))


def _deadline_from_text(text: str) -> str | None:
    # Examples: 04 August 2026, 4th August, 2026, Deadline: 04 August 2026
    m = re.search(r"(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,?\s+\d{4})", text or "", flags=re.I)
    if not m:
        return None
    return parse_date(m.group(1))


def _parse_table_rows(soup: BeautifulSoup, source_url: str) -> list[dict]:
    rows = []
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 3:
            continue
        joined = " ".join(cells).lower()
        if "deadline" in joined and ("title" in joined or "job" in joined):
            continue
        link = tr.find("a", href=True)
        title = clean_title(cells[0])
        if not title or len(title) < 4:
            continue
        # Heuristic: find common fields by label where possible.
        row_text = " ".join(cells)
        rows.append({
            "title": title,
            "department": _field(row_text, "Department"),
            "location": _field(row_text, "Location") or next((c for c in cells if any(x in c.lower() for x in ["mombasa", "tsavo", "nairobi", "matuga", "baringo", "embu"])), None),
            "positions": _field(row_text, "Positions") or next((c for c in cells if re.fullmatch(r"\d+", c)), None),
            "type": _field(row_text, "Type"),
            "deadline": _deadline_from_text(row_text),
            "requirements_text": row_text,
            "detail_url": _safe_url(link.get("href") if link else None, source_url) or source_url,
        })
    return rows


def _parse_card_blocks(soup: BeautifulSoup, source_url: str) -> list[dict]:
    blocks = []
    selectors = [".card", ".job", ".vacancy", ".listing", "article", "section"]
    seen_text = set()
    for sel in selectors:
        for node in soup.select(sel):
            text = clean_title(node.get_text(" ", strip=True))
            if len(text) < 80 or text in seen_text:
                continue
            if not re.search(r"Deadline\s*[:\-]", text, re.I) and not re.search(r"Positions\s*[:\-]", text, re.I):
                continue
            seen_text.add(text)
            h = node.find(["h1", "h2", "h3", "h4", "h5", "strong"])
            title = clean_title(h.get_text(" ", strip=True) if h else "")
            if not title:
                # title before Department/Location labels
                title = clean_title(re.split(r"\bDepartment\s*[:\-]|\bLocation\s*[:\-]", text, maxsplit=1, flags=re.I)[0])
            if len(title) > 140:
                title = title[:140].rsplit(" ", 1)[0]
            a = node.find("a", href=True)
            blocks.append({
                "title": title,
                "department": _field(text, "Department"),
                "location": _field(text, "Location"),
                "positions": _field(text, "Positions"),
                "type": _field(text, "Type"),
                "deadline": _deadline_from_text(text),
                "requirements_text": text,
                "detail_url": _safe_url(a.get("href") if a else None, source_url) or source_url,
            })
    return blocks


def _parse_text_blocks(soup: BeautifulSoup, source_url: str) -> list[dict]:
    text = clean_title(soup.get_text(" ", strip=True))
    pattern = re.compile(
        r"(?P<title>[A-Z][A-Za-z0-9 &,/()'\-.]{3,160}?)\s+"
        r"Department\s*[:\-]\s*(?P<department>.*?)\s+"
        r"Location\s*[:\-]\s*(?P<location>.*?)\s+"
        r"Positions\s*[:\-]\s*(?P<positions>\d+)\s+"
        r"Type\s*[:\-]\s*(?P<type>.*?)\s+"
        r"Deadline\s*[:\-]\s*(?P<deadline>\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,?\s+\d{4})"
        r"(?P<requirements>.*?)(?=(?:[A-Z][A-Za-z0-9 &,/()'\-.]{3,160}?\s+Department\s*[:\-])|$)",
        re.I | re.S,
    )
    rows = []
    for m in pattern.finditer(text):
        title = clean_title(m.group("title"))
        if not title or len(title) < 4:
            continue
        rows.append({
            "title": title,
            "department": clean_title(m.group("department")),
            "location": clean_title(m.group("location")),
            "positions": m.group("positions"),
            "type": clean_title(m.group("type")),
            "deadline": parse_date(m.group("deadline")),
            "requirements_text": clean_title(m.group("requirements"))[:2500],
            "detail_url": source_url,
        })
    return rows


def _parse_rows(html: str, source_url: str = KSG_URL) -> list[dict]:
    soup = BeautifulSoup(html or "", "html.parser")
    rows = _parse_table_rows(soup, source_url)
    if rows:
        return rows
    rows = _parse_card_blocks(soup, source_url)
    if rows:
        return rows
    return _parse_text_blocks(soup, source_url)


def collect(url: str = KSG_URL) -> tuple[list[dict], dict]:
    html, status, error = fetch_html(url)
    meta = {
        "source_id": SOURCE_ID,
        "source_name": SOURCE_NAME,
        "url": url,
        "http_status": status,
        "error": error,
        "records_seen": 0,
        "records_emitted": 0,
    }
    if error:
        return [], meta
    rows = _parse_rows(html, url)
    vacancies = []
    for r in rows:
        title = clean_title(r.get("title"))
        if not title:
            continue
        deadline = deadline_iso(r.get("deadline"))
        detail_url = r.get("detail_url") or url
        vid = stable_id(title, r.get("location"), r.get("deadline"), prefix="ksg")
        requirements_text = r.get("requirements_text") or "Review full requirements on the KSG application portal before applying."
        vacancy = build_vacancy(
            vid=vid,
            title=title,
            institution="Kenya School of Government",
            source_name="KSG Job Application Portal",
            source_url=url,
            source_id=SOURCE_ID,
            source_confidence="needs_review",
            source_type="institutional_portal",
            view_original_url=detail_url,
            apply_url=LOGIN_URL,
            number_of_vacancies=_int_or_none(r.get("positions")),
            advert_date=None,
            deadline=deadline,
            deadline_confidence="explicit" if deadline else "unknown",
            years_experience_minimum=_int_or_none(re.search(r"(\d+)\s+years?", requirements_text, flags=re.I).group(1)) if re.search(r"(\d+)\s+years?", requirements_text, flags=re.I) else None,
            location_raw=r.get("location") or "Kenya",
            employment_type=(r.get("type") or "contract").lower().replace(" ", "_"),
            terms=r.get("type") or "Contract",
            requirements_text=requirements_text,
            verification_status="needs_review",
            risk_flags=["external_portal_confirm_institution_linkage"],
            evidence_type="institutional_portal_listing",
            http_status=status,
        )
        vacancy["institution"].update({
            "name": "Kenya School of Government",
            "hiring_body": "Kenya School of Government",
            "type": "public_institution",
            "official_domain": "ksg.ac.ke",
        })
        vacancy["employment"]["department"] = r.get("department")
        vacancy["verification"]["notes"] = "Captured from KSG application portal. Cross-check KSG official channels before submitting sensitive documents."
        vacancy["links"]["view_original_label"] = "View role on original site"
        vacancies.append(vacancy)
    meta["records_seen"] = len(rows)
    meta["records_emitted"] = len(vacancies)
    return vacancies, meta


if __name__ == "__main__":  # pragma: no cover
    import json
    print(json.dumps(collect()[0], indent=2, ensure_ascii=False))
