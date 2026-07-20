import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.collectors import pscims, mygov

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def test_pscims_fixture_rows_to_vacancies():
    html = (FIXTURES / "pscims_active_adverts_sample.html").read_text(encoding="utf-8")
    rows = pscims._parse_table_rows(html)
    assert len(rows) == 2
    assert rows[0]["advert_number"] == "D85/2026"
    assert rows[0]["position"] == "Cook[3]"


def test_mygov_fixture_to_discovery_items():
    html = (FIXTURES / "mygov_job_adverts_sample.html").read_text(encoding="utf-8")
    rows = mygov._parse_rows(html)
    assert len(rows) == 2
    assert rows[0]["agency"] == "Kenya Medical Supplies Authority (KEMSA)"
    assert rows[0]["attachment_url"].endswith("KEMSA.pdf")
