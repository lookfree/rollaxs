from app.models import Inquiry, Subscriber


def test_contact_form_creates_inquiry(client, db):
    r = client.post("/contact/", data={"name": "张三", "email": "z@x.com",
                                       "message": "询价", "website": ""})
    assert r.status_code == 200 and "提交成功" in r.text
    assert db.query(Inquiry).count() == 1


def test_honeypot_silently_drops(client, db):
    client.post("/contact/", data={"name": "bot", "email": "b@x.com",
                                   "message": "spam", "website": "http://spam"})
    assert db.query(Inquiry).count() == 0


def test_rate_limit(client, db):
    for i in range(6):
        r = client.post("/contact/", data={"name": f"n{i}", "email": "a@b.c",
                                           "message": "m", "website": ""})
    assert r.status_code == 429


def test_newsletter_subscribe_dedup(client, db):
    for _ in range(2):
        client.post("/newsletter/", data={"email": "s@x.com", "first_name": "A",
                                          "last_name": "B", "salutation": "Mr", "website": ""})
    assert db.query(Subscriber).count() == 1
