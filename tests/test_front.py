def test_home_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert 'lang="zh"' in r.text

def test_home_en(client):
    r = client.get("/en/")
    assert 'lang="en"' in r.text

def test_404_page(client):
    r = client.get("/no-such-page/")
    assert r.status_code == 404
