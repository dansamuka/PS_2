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


def test_pscims_postback_detail_links_fall_back_to_official_page():
    html = '''
    <table><tr><th>#</th><th>Advert Number</th><th>Position</th><th>Job Scale</th><th>Ministry</th><th>Vacancies</th><th>Years</th><th>Category</th><th>Advert Date</th><th>Close Date</th><th>Details</th></tr>
    <tr><td>1</td><td>D88/2026</td><td>Artisan III</td><td>E</td><td>State Department for Correctional Services</td><td>19</td><td>0</td><td>Open</td><td>17-06-2026</td><td>03-08-2026</td><td><a href="javascript:__doPostBack('DataGrid2$ctl06$LinkButton3','')">Details</a></td></tr></table>
    '''
    rows = pscims._parse_table_rows(html)
    assert len(rows) == 1
    assert rows[0]["detail_url"] == pscims.PSCIMS_URL
    assert not rows[0]["detail_url"].startswith("javascript:")
