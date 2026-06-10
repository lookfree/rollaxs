from app.models import Job, Download


def test_jobs_and_downloads(client, db):
    db.add(Job(title_zh="数控工程师", body_zh="<p>职责</p>", category="social"))
    db.add(Job(title_zh="已关闭岗位", status="closed"))
    db.add(Download(title_zh="产品手册", category_zh="手册", file_path="2026/01/cat.pdf", file_size=1024))
    db.commit()
    r = client.get("/career/")
    assert "数控工程师" in r.text and "已关闭岗位" not in r.text
    job_id = db.query(Job).filter_by(title_zh="数控工程师").one().id
    assert "职责" in client.get(f"/career/{job_id}.html").text
    r = client.get("/downloads/")
    assert "产品手册" in r.text and "/uploads/2026/01/cat.pdf" in r.text


def test_home_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert 'lang="zh"' in r.text

def test_home_en(client):
    r = client.get("/en/")
    assert 'lang="en"' in r.text

def test_404_page(client):
    r = client.get("/no-such-page/")
    assert r.status_code == 404


from app.models import Page

def test_page_render_and_fallback(client, db):
    p1 = Page(slug="company", title_zh="公司", title_en="Company", body_zh="<p>中文正文</p>")
    db.add(p1); db.flush()
    db.add(Page(slug="quality", parent_id=p1.id, title_zh="质量", body_zh="<p>质量正文</p>"))
    db.commit()
    assert "公司" in client.get("/company/").text
    r = client.get("/en/company/quality/")
    assert r.status_code == 200
    assert "质量正文" in r.text          # 英文为空回退中文
    assert client.get("/company/nope/").status_code == 404
