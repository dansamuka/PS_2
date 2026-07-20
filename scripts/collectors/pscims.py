#!/usr/bin/env python3
"""PSCIMS active-adverts collector.

Collects the official Public Service Commission active adverts table. The PSCIMS page exposes
advert number, position, job scale, ministry, vacancies, experience, advert category, advert date,
and advert close date. Detail links may be ASP.NET postback-driven, so each collected row keeps
`view_original_url` at the official active-adverts page unless a direct detail href is found.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

try:
    from ._common import build_vacancy, deadline_iso, fetch_html, parse_date, stable_id
except ImportError:  # pragma: no cover
    from _common import build_vacancy, deadline_iso, fetch_html, parse_date, stable_id

PSCIMS_URL = "https://pscims.publicservice.go.ke/jobs/ActiveJobsAdverts.aspx"


def _clean_position(value: str) -> str:
    return re.sub(r"\[\d+\]", "", value or "").strip()


def _int_or_none(value: str | None):
    try:
        return int(str(value).replace(",", "").strip())
    except Exception:
        return None


def _parse_table_rows(html: str, source_url: str = PSCIMS_URL) -> list[dict]:
    soup = BeautifulSoup(html or "", "html.parser")
    rows = []
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 9:
            continue
        joined = " ".join(cells).lower()
        if "advert number" in joined and "position" in joined:
            continue
        # Expected cells may include row number at start:
        # #, Advert Number, Position, Job Scale, Ministry, Vacancies, Years, Category, Advert Date, Close Date, Details
        if re.match(r"^\d+$", cells[0]) and len(cells) >= 10:
            cells = cells[1:]
        if not re.match(r"^[A-Z]\d+\/\d{4}$", cells[0] or ""):
            continue
        href = None
        a = tr.find("a", href=True)
        if a:
            href = urljoin(source_url, a["href"])
        rows.append({
            "advert_number": cells[0],
            "position": cells[1],
            "job_scale": cells[2] if len(cells) > 2 else None,
            "ministry": cells[3] if len(cells) > 3 else None,
            "vacancies": cells[4] if len(cells) > 4 else None,
            "experience": cells[5] if len(cells) > 5 else None,
            "advert_category": cells[6] if len(cells) > 6 else None,
            "advert_date": cells[7] if len(cells) > 7 else None,
            "close_date": cells[8] if len(cells) > 8 else None,
            "detail_url": href or source_url,
        })
    return rows


def _parse_text_rows(html: str, source_url: str = PSCIMS_URL) -> list[dict]:
    """Fallback parser for PSCIMS text rendering returned by simple HTML fetchers."""
    text = BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)
    pattern = re.compile(
        r"(?P<num>\d+)\s+"
        r"(?P<advert>[A-Z]\d+\/\d{4})\s+"
        r"(?P<position>.*?)\s+"
        r"(?P<scale>[A-Z])\s+"
        r"(?P<ministry>State Department .*?|Ministry .*?|Office .*?|Public Service Commission.*?)\s+"
        r"(?P<vacancies>\d+)\s+"
        r"(?P<experience>\d+)\s+"
        r"(?P<category>Open|Closed)\s+"
        r"(?P<advert_date>\d{2}-\d{2}-\d{4})\s+"
        r"(?P<close_date>\d{2}-\d{2}-\d{4})",
        flags=re.I,
    )
    rows = []
    for m in pattern.finditer(text):
        rows.append({
            "advert_number": m.group("advert"),
            "position": m.group("position"),
            "job_scale": m.group("scale"),
            "ministry": m.group("ministry"),
            "vacancies": m.group("vacancies"),
            "experience": m.group("experience"),
            "advert_category": m.group("category"),
            "advert_date": m.group("advert_date"),
            "close_date": m.group("close_date"),
            "detail_url": source_url,
        })
    return rows


def collect(url: str = PSCIMS_URL) -> tuple[list[dict], dict]:
    html, status, error = fetch_html(url)
    meta = {
        "source_id": "pscims_active_adverts",
        "source_name": "Public Service Commission Active Adverts",
        "url": url,
        "http_status": status,
        "error": error,
        "records_seen": 0,
        "records_emitted": 0,
    }
    if error:
        return [], meta
    rows = _parse_table_rows(html, url) or _parse_text_rows(html, url)
    vacancies = []
    for r in rows:
        if str(r.get("advert_category", "")).lower() not in {"open", ""}:
            continue
        advert_date = parse_date(r.get("advert_date"))
        close_date = parse_date(r.get("close_date"))
        title = _clean_position(r.get("position") or "")
        vid = stable_id(r.get("advert_number"), title, r.get("ministry"), prefix="pscims")
        requirements_text = (
            f"PSCIMS active-advert row: {r.get('advert_number')}; job scale {r.get('job_scale')}; "
            f"{r.get('vacancies')} vacancies; {r.get('experience')} years of experience required. "
            "Review Advert Details on PSCIMS before applying."
        )
        vacancies.append(build_vacancy(
            vid=vid,
            title=title,
            institution=r.get("ministry") or "Public Service Commission",
            source_name="PSCIMS Active Adverts",
            source_url=url,
            source_id="pscims_active_adverts",
            source_confidence="official",
            source_type="official_portal",
            view_original_url=r.get("detail_url") or url,
            apply_url="https://pscims.publicservice.go.ke/puio/",
            advert_number=r.get("advert_number"),
            job_scale=r.get("job_scale"),
            number_of_vacancies=_int_or_none(r.get("vacancies")),
            advert_date=advert_date,
            deadline=deadline_iso(close_date),
            deadline_confidence="explicit" if close_date else "unknown",
            years_experience_minimum=_int_or_none(r.get("experience")),
            requirements_text=requirements_text,
            evidence_type="official_table",
            http_status=status,
        ))
    meta["records_seen"] = len(rows)
    meta["records_emitted"] = len(vacancies)
    return vacancies, meta


if __name__ == "__main__":  # pragma: no cover
    import json
    print(json.dumps(collect()[0], indent=2, ensure_ascii=False))
