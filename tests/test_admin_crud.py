from app.models import Page, ProductCategory, Product, Post, Job, Download


def test_page_crud(logged_client, db):
    r = logged_client.post("/admin/pages/new", data={
        "slug": "about", "title_zh": "关于", "body_zh": "<p>x</p>",
        "nav_show": "1", "sort": "0"})
    assert r.status_code == 303
    pid = db.query(Page).filter_by(slug="about").one().id
    assert "关于" in logged_client.get("/admin/pages").text
    logged_client.post(f"/admin/pages/{pid}", data={"slug": "about", "title_zh": "关于我们",
                                                    "nav_show": "1", "sort": "0"})
    db.expire_all()
    assert db.get(Page, pid).title_zh == "关于我们"
    logged_client.post(f"/admin/pages/{pid}/delete")
    assert db.query(Page).count() == 0


def test_product_crud_updates_search_index(logged_client, db):
    logged_client.post("/admin/categories/new", data={"slug": "c1", "name_zh": "分类", "sort": "0"})
    cid = db.query(ProductCategory).one().id
    logged_client.post("/admin/products/new", data={
        "slug": "p1", "category_id": str(cid), "name_zh": "产品一",
        "name_en": "Product One", "sort": "0"})
    from app.search import query_index
    assert query_index(db, "Product", "en")     # 保存后索引已重建


def test_crud_requires_login(client):
    assert client.get("/admin/pages").status_code == 303


def test_post_job_download_crud(logged_client, db):
    logged_client.post("/admin/posts/new", data={
        "slug": "n1", "title_zh": "新闻一", "status": "published",
        "publish_at": "2026-06-10T08:00"})
    assert db.query(Post).filter_by(slug="n1", status="published").count() == 1
    logged_client.post("/admin/jobs/new", data={"title_zh": "工程师", "category": "social",
                                                "status": "open", "sort": "0"})
    assert db.query(Job).count() == 1
    logged_client.post("/admin/downloads/new", data={"title_zh": "手册", "file_path": "a.pdf",
                                                     "sort": "0", "file_size": "0"})
    assert db.query(Download).count() == 1
