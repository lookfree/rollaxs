from app.i18n import t, pick, lang_url, LANGS

class Obj:
    title_zh = "中文标题"; title_en = ""; title_de = "DE"; title_jp = ""

def test_pick_fallback():
    o = Obj()
    assert pick(o, "title", "de") == "DE"
    assert pick(o, "title", "en") == "中文标题"   # 空回退中文
    assert pick(o, "title", "zh") == "中文标题"

def test_lang_url():
    assert lang_url("zh", "/products/") == "/products/"
    assert lang_url("en", "/products/") == "/en/products/"
    assert lang_url("jp", "/") == "/jp/"

def test_middleware_strips_prefix(client):
    r = client.get("/en/healthz")
    assert r.status_code == 200  # 前缀被剥离后命中 /healthz

def test_ui_translation():
    assert t("nav.home", "zh") == "首页"
    assert t("nav.home", "de") == "Startseite"
    assert t("不存在的key", "en") == "不存在的key"
