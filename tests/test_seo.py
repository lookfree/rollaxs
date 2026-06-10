def test_hreflang_and_canonical(client, db):
    from app.models import Page
    db.add(Page(slug="company", title_zh="公司", seo_title_en="Company Ltd")); db.commit()
    html = client.get("/en/company/").text
    assert '<link rel="alternate" hreflang="de" href="http://localhost:8000/de/company/"' in html
    assert 'hreflang="x-default"' in html
    assert '<link rel="canonical" href="http://localhost:8000/en/company/"' in html
    assert "<title>Company Ltd" in html


def test_sitemap_and_robots(client, db):
    from app.models import Page
    db.add(Page(slug="company", title_zh="公司")); db.commit()
    xml = client.get("/sitemap.xml").text
    assert "/de/company/" in xml and "<urlset" in xml
    assert "Sitemap:" in client.get("/robots.txt").text


def test_breadcrumb_jsonld(client, db):
    from app.models import Page
    db.add(Page(slug="company", title_zh="公司")); db.commit()
    assert '"@type": "BreadcrumbList"' in client.get("/company/").text
