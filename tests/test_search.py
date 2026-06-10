from app.search import rebuild_index, query_index
from app.models import Product, ProductCategory


def test_search(client, db, app):
    cat = ProductCategory(slug="c1", name_zh="分类")
    db.add(cat); db.flush()
    db.add(Product(slug="strut", category_id=cat.id, name_zh="悬架轴承",
                   name_en="Strut bearing", body_en="<p>premium strut mount bearing</p>"))
    db.commit()
    rebuild_index(app.state.engine, db)
    hits = query_index(db, "strut", "en")
    assert hits and hits[0]["url"].endswith("strut.html")
    r = client.get("/en/search/?q=strut")
    assert "Strut bearing" in r.text
