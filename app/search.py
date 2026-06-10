import re
from sqlalchemy import text
from app.i18n import LANGS


def create_fts(engine):
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5("
            "kind, ref_id UNINDEXED, lang, title, content, url UNINDEXED)"
        ))
        conn.commit()


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", " ", s or "")


def rebuild_index(engine, db):
    """全量重建索引:产品/页面/新闻 × 四语言。后台保存内容时调用。"""
    from app.models import Product, Page, Post
    # Avoid circular import: front helpers imported inside function
    from app.routes.front import cat_url_by_id, page_url

    db.execute(text("DELETE FROM search_index"))
    rows = []

    for p in db.query(Product).all():
        for lang in LANGS:
            title = getattr(p, f"name_{lang}") or p.name_zh
            body = _strip_html(getattr(p, f"body_{lang}") or p.body_zh)
            url = cat_url_by_id(db, p.category_id) + f"{p.slug}.html"
            rows.append(("product", p.id, lang, title, body, url))

    for pg in db.query(Page).all():
        for lang in LANGS:
            title = getattr(pg, f"title_{lang}") or pg.title_zh
            body = _strip_html(getattr(pg, f"body_{lang}") or pg.body_zh)
            rows.append(("page", pg.id, lang, title, body, page_url(db, pg)))

    for po in db.query(Post).filter_by(status="published").all():
        for lang in LANGS:
            title = getattr(po, f"title_{lang}") or po.title_zh
            body = _strip_html(getattr(po, f"body_{lang}") or po.body_zh)
            rows.append(("post", po.id, lang, title, body, f"/news/{po.slug}.html"))

    for r in rows:
        db.execute(
            text("INSERT INTO search_index VALUES (:k,:i,:l,:t,:c,:u)"),
            {"k": r[0], "i": r[1], "l": r[2], "t": r[3], "c": r[4], "u": r[5]},
        )
    db.commit()


def query_index(db, q: str, lang: str, limit: int = 30):
    safe = '"' + q.replace('"', " ") + '"'
    rs = db.execute(
        text(
            "SELECT kind, title, url, snippet(search_index, 4, '<b>', '</b>', '…', 12) AS snip "
            "FROM search_index WHERE search_index MATCH :q AND lang = :lang "
            "ORDER BY bm25(search_index) LIMIT :n"
        ),
        {"q": safe, "lang": lang, "n": limit},
    )
    return [dict(r._mapping) for r in rs]
