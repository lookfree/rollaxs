from app.models import Page, ProductCategory, Product, Post, Job, Download, Inquiry, Subscriber


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


def test_inquiries_list_read_export(logged_client, db):
    db.add(Inquiry(name="客户A", email="a@x.com", message="询价")); db.commit()
    iid = db.query(Inquiry).one().id
    assert "客户A" in logged_client.get("/admin/inquiries").text
    logged_client.post(f"/admin/inquiries/{iid}/read")
    db.expire_all()
    assert db.get(Inquiry, iid).is_read is True
    csv = logged_client.get("/admin/inquiries/export.csv")
    assert "客户A" in csv.text and "text/csv" in csv.headers["content-type"]


def test_subscribers_export(logged_client, db):
    db.add(Subscriber(email="s@x.com", first_name="A")); db.commit()
    assert "s@x.com" in logged_client.get("/admin/subscribers/export.csv").text


def test_page_parent_cannot_be_self_or_descendant(logged_client, db):
    logged_client.post("/admin/pages/new", data={"slug": "a", "title_zh": "甲", "sort": "0"})
    a = db.query(Page).filter_by(slug="a").one()
    logged_client.post("/admin/pages/new", data={
        "slug": "b", "title_zh": "乙", "sort": "0", "parent_id": str(a.id)})
    b = db.query(Page).filter_by(slug="b").one()
    # 子级 b 不应出现在 a 的父级下拉中
    form_html = logged_client.get(f"/admin/pages/{a.id}").text
    assert f'value="{b.id}"' not in form_html
    # 把 a 的父级设成它的子级 b → 报错回显且不落库
    r = logged_client.post(f"/admin/pages/{a.id}", data={
        "slug": "a", "title_zh": "甲", "sort": "0", "parent_id": str(b.id)})
    assert r.status_code == 200
    assert "不能选择自身或其子级作为父级" in r.text
    db.expire_all()
    assert db.get(Page, a.id).parent_id is None
    # 设成自己同样被拒绝
    r = logged_client.post(f"/admin/pages/{a.id}", data={
        "slug": "a", "title_zh": "甲", "sort": "0", "parent_id": str(a.id)})
    assert r.status_code == 200 and "不能选择自身或其子级作为父级" in r.text
    db.expire_all()
    assert db.get(Page, a.id).parent_id is None


def test_create_with_invalid_number_echoes_error(logged_client, db):
    r = logged_client.post("/admin/pages/new", data={
        "slug": "x", "title_zh": "X", "sort": "abc"})
    assert r.status_code == 200
    assert "保存失败" in r.text
    assert db.query(Page).count() == 0


def test_update_with_invalid_value_echoes_user_input(logged_client, db):
    logged_client.post("/admin/posts/new", data={
        "slug": "n1", "title_zh": "新闻一", "status": "published",
        "publish_at": "2026-06-10T08:00"})
    pid = db.query(Post).filter_by(slug="n1").one().id
    r = logged_client.post(f"/admin/posts/{pid}", data={
        "slug": "n1", "title_zh": "新标题", "status": "published",
        "publish_at": "garbage"})
    assert r.status_code == 200
    assert "保存失败" in r.text
    assert "新标题" in r.text          # 回显用户输入而非库里旧值
    db.expire_all()
    assert db.get(Post, pid).title_zh == "新闻一"  # 未提交


def test_inquiry_csv_formula_injection_escaped(logged_client, db):
    db.add(Inquiry(name="=cmd()", email="a@x.com", company="+SUM(1)", message="@x")); db.commit()
    body = logged_client.get("/admin/inquiries/export.csv").text
    assert "'=cmd()" in body and ",=cmd()" not in body  # 单元格不再以 = 开头
    assert "'+SUM(1)" in body
    assert "'@x" in body


def test_subscribers_csv_formula_injection_escaped(logged_client, db):
    db.add(Subscriber(email="s@x.com", first_name="=HYPERLINK(1)")); db.commit()
    body = logged_client.get("/admin/subscribers/export.csv").text
    assert "'=HYPERLINK(1)" in body


def test_settings_save(logged_client, db):
    logged_client.post("/admin/settings", data={"site_name": "我的公司", "phone": "+86 100",
                                                "analytics_code": "<script>GA</script>"})
    from app.models import Setting
    assert db.get(Setting, "site_name").value == "我的公司"
