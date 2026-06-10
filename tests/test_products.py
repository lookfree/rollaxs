from app.models import ProductCategory, Product


def seed_products(db):
    root = ProductCategory(slug="new-mobility", name_zh="新出行", name_en="New Mobility")
    db.add(root); db.flush()
    sub = ProductCategory(slug="nvh-bearings", parent_id=root.id, name_zh="NVH 轴承")
    db.add(sub); db.flush()
    db.add(Product(slug="nvh-100", category_id=sub.id, name_zh="NVH-100", body_zh="<p>详情</p>"))
    db.commit()


def test_category_and_product(client, db):
    seed_products(db)
    assert "新出行" in client.get("/products/").text
    assert "NVH 轴承" in client.get("/products/new-mobility/").text
    r = client.get("/products/new-mobility/nvh-bearings/nvh-100.html")
    assert "NVH-100" in r.text and "详情" in r.text


def test_home_shows_category_cards(client, db):
    seed_products(db)
    assert "New Mobility" in client.get("/en/").text
