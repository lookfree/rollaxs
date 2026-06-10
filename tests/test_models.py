from app.db import make_engine, make_session_factory, init_db
from app.models import Page, ProductCategory, Product, Post, Job, Download, Inquiry, Subscriber, Media, Setting, AdminUser

def test_create_all_tables(tmp_path):
    engine = make_engine(tmp_path / "m.db")
    init_db(engine)
    Session = make_session_factory(engine)
    with Session() as s:
        s.add(Page(slug="about", title_zh="关于我们", body_zh="<p>正文</p>"))
        cat = ProductCategory(slug="new-mobility", name_zh="新出行")
        s.add(cat); s.flush()
        s.add(Product(slug="nvh", category_id=cat.id, name_zh="NVH 轴承"))
        s.commit()
        assert s.query(Page).filter_by(slug="about").one().title_zh == "关于我们"

def test_wal_mode(tmp_path):
    engine = make_engine(tmp_path / "m.db")
    with engine.connect() as conn:
        from sqlalchemy import text
        assert conn.execute(text("PRAGMA journal_mode")).scalar() == "wal"
