import json

from scripts.collectors import ksg, mygov, pscims


def test_pscims_postback_links_are_not_used_as_original_urls():
    html = """
    <table><tr><th>#</th><th>Advert Number</th><th>Position</th><th>Job Scale</th><th>Ministry</th><th>Vacancies</th><th>Years</th><th>Category</th><th>Advert Date</th><th>Close Date</th><th>Details</th></tr>
    <tr><td>1</td><td>D99/2026</td><td>Cook[3]</td><td>E</td><td>State Department for Correctional Services</td><td>18</td><td>0</td><td>Open</td><td>17-06-2026</td><td>03-08-2026</td><td><a href="javascript:__doPostBack('DataGrid2$ctl03$LinkButton3','')">View</a></td></tr></table>
    """
    rows = pscims._parse_table_rows(html)
    assert rows[0]["detail_url"] == pscims.PSCIMS_URL


def test_mygov_parser_reads_gaa_table_rows():
    html = """
    <table>
      <tr><th>Title</th><th>Advert Attachment</th><th>Recruiting Agency</th><th>Submission Date</th></tr>
      <tr><td>Kenya Trade Network Agency Career Opportunities</td><td><a href="/sites/default/files/2026-08/KenTrade.pdf">PDF</a></td><td>Kenya Trade Network Agency (KenTrade)</td><td>4th August, 2026</td></tr>
    </table>
    """
    rows = mygov._parse_rows(html, "https://gaa.go.ke/index.php/node/445")
    assert len(rows) == 1
    assert rows[0]["title"] == "Kenya Trade Network Agency Career Opportunities"
    assert rows[0]["agency"] == "Kenya Trade Network Agency (KenTrade)"
    assert rows[0]["attachment_url"].startswith("https://gaa.go.ke/")


def test_ksg_parser_reads_role_blocks():
    html = """
    <div class="card">
      <h3>Senior Hotel Attendant (Receptionist /Cashier)</h3>
      <p>Department: ALL</p><p>Location: Tsavo East, Tsavo West, Mombasa</p>
      <p>Positions: 9</p><p>Type: Contract</p><p>Deadline: 04 August 2026</p>
      <p>Mandatory Requirements For appointment to this grade an Officer must have cumulative service period of Nine years relevant work experience; KCSE Mean Grade D; Proficiency in computer applications.</p>
      <a href="/jobs/senior-hotel-attendant">View</a>
    </div>
    """
    rows = ksg._parse_rows(html, "https://jobapplications.ke/")
    assert len(rows) == 1
    assert rows[0]["title"] == "Senior Hotel Attendant (Receptionist /Cashier)"
    assert rows[0]["positions"] == "9"
    assert rows[0]["deadline"] == "2026-08-04"
    assert rows[0]["detail_url"] == "https://jobapplications.ke/jobs/senior-hotel-attendant"
