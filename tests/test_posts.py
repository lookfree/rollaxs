from datetime import datetime, timedelta
from app.models import Post


def test_news_list_pagination_and_detail(client, db):
    for i in range(12):
        db.add(Post(slug=f"news-{i}", status="published", title_zh=f"新闻{i}",
                    excerpt_zh="摘要", body_zh="<p>正文</p>",
                    publish_at=datetime.utcnow() - timedelta(days=i)))
    db.add(Post(slug="draft-1", status="draft", title_zh="草稿"))
    db.commit()
    r = client.get("/news/")
    assert "新闻0" in r.text and "新闻10" not in r.text     # 每页 10 条
    assert "草稿" not in r.text
    assert "新闻10" in client.get("/news/?page=2").text
    assert "正文" in client.get("/news/news-3.html").text
    assert client.get("/news/draft-1.html").status_code == 404


def test_future_published_post_detail_returns_404(client, db):
    """Bug 2: a published post with publish_at in the future must 404 at detail URL."""
    future_time = datetime.utcnow() + timedelta(hours=1)
    db.add(Post(
        slug="future-news",
        status="published",
        title_zh="未来新闻",
        body_zh="<p>内容</p>",
        publish_at=future_time,
    ))
    db.commit()
    r = client.get("/news/future-news.html")
    assert r.status_code == 404
