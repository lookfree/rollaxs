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
