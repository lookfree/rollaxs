"""抓取 rollax.com 公开页面灌入种子数据(仅开发占位用,上线前必须全部替换素材)。

用法: .venv/bin/python scripts/seed_from_rollax.py
可重复执行(按 slug upsert);Cloudflare 拦截/抓取失败的页面自动落占位文本,绝不中断。
各语言 URL 不假设同路径:先抓德语页,从 <link rel="alternate" hreflang=...> 发现
en/jp/cn 的本地化地址,缺失时退回 "语言前缀 + 德语路径"。
"""
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, unquote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings
from app.db import make_engine, make_session_factory, init_db
from app.i18n import LANGS
from app.media import save_upload
from app.models import Media, Page, Post, ProductCategory, Setting

BASE = "https://www.rollax.com"
LANG_PREFIX = {"zh": "/cn", "en": "/en", "de": "", "jp": "/jp"}
# rollax 的 hreflang 标注(短码 "cn" 有指向 jp 的脏数据,故用带地区的长码)
HREFLANG_TO_LANG = {"de-DE": "de", "en-EN": "en", "jp-JP": "jp", "cn-CN": "zh"}
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"}
PLACEHOLDER = {"zh": "<p>内容整理中。</p>", "en": "<p>Content coming soon.</p>",
               "de": "<p>Inhalt folgt in Kürze.</p>", "jp": "<p>準備中です。</p>"}
SLEEP = 0.4  # 请求间隔,礼貌抓取

# rollax 德语路径 → 本站结构映射
CATEGORY_MAP = [  # (rollax 德语路径, 本站 slug, 本站父 slug 或 None)
    ("/produkte/new-mobility/", "new-mobility", None),
    ("/produkte/new-mobility/nvh-lager/", "nvh-bearings", "new-mobility"),
    ("/produkte/new-mobility/freilauflager/", "freewheel-bearings", "new-mobility"),
    ("/produkte/new-mobility/kompensationslager/", "compensation-bearings", "new-mobility"),
    ("/produkte/new-mobility/axiallager/", "axial-bearings", "new-mobility"),
    ("/produkte/new-mobility/linearlager/", "linear-bearings", "new-mobility"),
    ("/produkte/new-mobility/multifunktionslager/", "multifunctional-bearings", "new-mobility"),
    ("/produkte/federbeinlager/", "strut-bearings", None),
    ("/produkte/sonstige-loesungen/rillenkugellager/", "standard-ball-bearings", None),
    ("/produkte/lenkungslager/", "steering-bearings", None),
    ("/produkte/sitzversteller/", "seat-adjusters", None),
    ("/produkte/arretierung-und-rastierung/", "locking-and-detent", None),
    ("/produkte/sonstige-loesungen/", "other-solutions", None),
    ("/produkte/sonstige-loesungen/kugelkaefige/", "ball-cages", "other-solutions"),
]
PAGE_MAP = [
    ("/unternehmen/", "company", None),
    ("/unternehmen/rollax-dns/", "dna", "company"),
    ("/unternehmen/standorte/", "locations", "company"),
    ("/unternehmen/kompetenzen/", "competencies", "company"),
    ("/unternehmen/kunden/", "customers", "company"),
    ("/unternehmen/qualitaet/", "quality", "company"),
    ("/entwicklung/", "development", None),
    ("/partnerschaften-sponsoring/", "partnerships", None),
    ("/impressum/", "imprint", None),
    ("/datenschutz/", "privacy", None),
    ("/agb/", "terms", None),
    ("/unternehmen/compliance/", "compliance", None),
]
# 德语新闻日期月份缩写 → 月份数字
DE_MONTHS = {"jan": 1, "feb": 2, "mär": 3, "mar": 3, "apr": 4, "mai": 5, "jun": 6,
             "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dez": 12}

stats = {"categories": 0, "pages": 0, "posts": 0, "images": 0, "placeholder_langs": 0}


def fetch(client: httpx.Client, url: str):
    """GET 一个 URL 返回 soup;非 200 或网络错误回 None(Cloudflare 403/520 等)。"""
    try:
        r = client.get(url, timeout=20)
        if r.status_code != 200:
            print(f"    ! {url} -> HTTP {r.status_code}")
            return None
        return BeautifulSoup(r.text, "html.parser")
    except httpx.HTTPError as e:
        print(f"    ! {url} -> {type(e).__name__}")
        return None


def alternate_urls(de_soup) -> dict:
    """从德语页的 hreflang alternate 链接发现各语言本地化 URL。"""
    urls = {}
    if de_soup is None:
        return urls
    for link in de_soup.find_all("link", rel="alternate"):
        lang = HREFLANG_TO_LANG.get(link.get("hreflang") or "")
        href = link.get("href")
        if lang and href:
            urls[lang] = urljoin(BASE + "/", href)
    return urls


def fetch_all_langs(client: httpx.Client, de_path: str) -> dict:
    """返回 {lang: soup|None}。德语页先抓,其余语言用 alternate 发现的 URL。"""
    soups = {}
    de_soup = fetch(client, BASE + de_path)
    time.sleep(SLEEP)
    soups["de"] = de_soup
    alts = alternate_urls(de_soup)
    for lang in LANGS:
        if lang == "de":
            continue
        url = alts.get(lang) or (BASE + LANG_PREFIX[lang] + de_path)
        soups[lang] = fetch(client, url)
        time.sleep(SLEEP)
    return soups


def extract(soup):
    """返回 (title, html_body, hero_img_url);soup 为 None 时返回 None。"""
    if soup is None:
        return None
    main = (soup.find(id="content")
            or soup.find("section", class_="content")
            or soup.body)
    if main is None:
        return None
    h1 = main.find("h1") or soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""
    for tag in main.find_all(["script", "style", "form", "nav"]):
        tag.decompose()
    for tag in main.find_all(class_=["page-navigation", "f3-widget-paginator"]):
        tag.decompose()
    parts = []
    for el in main.find_all(["p", "h2", "h3", "ul", "blockquote"]):
        # 跳过 blockquote 内部的 p(避免内容重复),以及纯链接列表(rollax 页内导航)
        if el.name == "p" and el.find_parent("blockquote") is not None:
            continue
        if el.name == "ul":
            lis = el.find_all("li")
            link_lis = [li for li in lis if li.find("a") is not None]
            if lis and len(link_lis) >= len(lis) * 0.8:
                continue
        if el.name in ("h2", "h3") and el.get_text(strip=True) in ("产品", "联系我们", "Produkte", "Products", "Kontaktieren Sie uns", "Contact us", "製品", "お問い合わせ"):
            continue
        parts.append(str(el))
    body = "".join(parts)
    imgs = [img.get("src") or img.get("data-src") for img in main.find_all("img")]
    banner = soup.find(id="banner")
    if banner:
        imgs = [i.get("src") or i.get("data-src") for i in banner.find_all("img")] + imgs
    imgs = [i for i in imgs if i and not i.lower().endswith(".svg")]
    return title, body, (imgs[0] if imgs else "")


def download_image(client: httpx.Client, uploads_dir: Path, db, src: str) -> str:
    """下载图片存入 uploads 并登记 Media,返回相对路径(模板自加 /uploads/ 前缀)。"""
    if not src:
        return ""
    url = urljoin(BASE + "/", src)
    try:
        r = client.get(url, timeout=30)
        time.sleep(SLEEP)
        if r.status_code != 200 or len(r.content) < 1000:
            return ""
        filename = unquote(url.split("/")[-1].split("?")[0]) or "image.jpg"
        rel, kind, thumb_rel, webp_rel = save_upload(uploads_dir, filename, r.content)
        db.add(Media(path=rel, kind=kind, thumb_path=thumb_rel, webp_path=webp_rel))
        stats["images"] += 1
        return rel
    except (httpx.HTTPError, ValueError) as e:
        print(f"    ! 图片失败 {url}: {e}")
        return ""


def upsert(db, model, slug: str, **fields):
    obj = db.query(model).filter_by(slug=slug).first()
    if not obj:
        obj = model(slug=slug)
        db.add(obj)
    for k, v in fields.items():
        if v is None or v == "":
            continue  # 不用空值覆盖已有数据(False/0 等仍照常写入)
        setattr(obj, k, v)
    db.flush()
    return obj


def seed_settings(db):
    defaults = {
        "site_name": "ROLLAX 同业演示站",
        "tagline": "轴承与传动解决方案(演示数据)",
        "phone": "+86 21 8888 0000",
        "email": "info@example.com",
        "copyright": "© 2026 ROLLAX 同业演示站 · 演示数据,上线前替换",
    }
    for key, value in defaults.items():
        if db.query(Setting).filter_by(key=key).first() is None:
            db.add(Setting(key=key, value=value))
            print(f"设置: {key} = {value}")
    db.flush()


def seed_categories(client, db, uploads_dir):
    slug_to_id = {}
    for de_path, slug, parent_slug in CATEGORY_MAP:
        soups = fetch_all_langs(client, de_path)
        fields, fallback = {}, 0
        for lang in LANGS:
            data = extract(soups[lang])
            if data and (data[0] or data[1]):
                fields[f"name_{lang}"] = data[0]
                fields[f"intro_{lang}"] = data[1] or PLACEHOLDER[lang]
            else:
                fields[f"intro_{lang}"] = PLACEHOLDER[lang]
                fallback += 1
        stats["placeholder_langs"] += fallback
        fields["parent_id"] = slug_to_id.get(parent_slug)
        existing = db.query(ProductCategory).filter_by(slug=slug).first()
        de_data = extract(soups["de"])
        if de_data and de_data[2] and not (existing and existing.hero_image):
            rel = download_image(client, uploads_dir, db, de_data[2])
            fields["hero_image"] = rel
            fields["card_image"] = rel
        cat = upsert(db, ProductCategory, slug, **fields)
        slug_to_id[slug] = cat.id
        stats["categories"] += 1
        print(f"分类: {slug} {'(含占位 ' + str(fallback) + ' 语)' if fallback else '✓'}")
    return slug_to_id


def seed_pages(client, db, uploads_dir):
    page_ids = {}
    for de_path, slug, parent_slug in PAGE_MAP:
        soups = fetch_all_langs(client, de_path)
        fields, fallback = {}, 0
        for lang in LANGS:
            data = extract(soups[lang])
            if data and (data[0] or data[1]):
                fields[f"title_{lang}"] = data[0]
                fields[f"body_{lang}"] = data[1] or PLACEHOLDER[lang]
            else:
                fields[f"body_{lang}"] = PLACEHOLDER[lang]
                fallback += 1
        stats["placeholder_langs"] += fallback
        fields["parent_id"] = page_ids.get(parent_slug)
        existing = db.query(Page).filter_by(slug=slug).first()
        de_data = extract(soups["de"])
        if de_data and de_data[2] and not (existing and existing.hero_image):
            fields["hero_image"] = download_image(client, uploads_dir, db, de_data[2])
        pg = upsert(db, Page, slug, **fields)
        page_ids[slug] = pg.id
        stats["pages"] += 1
        print(f"页面: {slug} {'(含占位 ' + str(fallback) + ' 语)' if fallback else '✓'}")
    return page_ids


def seed_home_intro(client, db):
    soups = fetch_all_langs(client, "/")
    fields = {"nav_show": False}
    for lang in LANGS:
        data = extract(soups[lang])
        if data:
            fields[f"title_{lang}"] = data[0]
        fields[f"body_{lang}"] = (data[1] if data else "") or PLACEHOLDER[lang]
        if not data:
            stats["placeholder_langs"] += 1
    upsert(db, Page, "home-intro", **fields)
    print("页面: home-intro ✓")


def parse_news_date(text_div) -> datetime | None:
    span = text_div.find("span", class_="date")
    if not span:
        return None
    try:
        day = int(span.find("span", class_="day").get_text(strip=True))
        month = DE_MONTHS[span.find("span", class_="month").get_text(strip=True).lower()[:3]]
        year = int(span.find("span", class_="year").get_text(strip=True))
        return datetime(year, month, day)
    except (AttributeError, KeyError, ValueError):
        return None


def seed_posts(client, db):
    soup = fetch(client, BASE + "/aktuelles/")
    time.sleep(SLEEP)
    news = soup.find("div", class_="news") if soup else None
    if news is None:
        print("新闻: 列表抓取失败,跳过(可重跑补抓)")
        return
    count = 0
    for item in news.select("div.text"):
        h3 = item.find("h3")
        if h3 is None:
            continue
        title = h3.get_text(strip=True)
        if not title:
            continue
        link = item.find("a", href=True)
        slug = ""
        if link:
            slug = unquote(link["href"]).rstrip("/").split("/")[-1][:180]
        slug = slug or f"news-{count + 1}"
        excerpt_p = item.find("p")
        excerpt = excerpt_p.get_text(strip=True) if excerpt_p else ""
        body = f"<p>{excerpt or title}</p>"
        publish = parse_news_date(item) or datetime(2025, 1, 1 + count * 3)
        upsert(db, Post, slug, status="published", publish_at=publish,
               title_zh=title, title_de=title,
               excerpt_zh=excerpt, excerpt_de=excerpt,
               body_zh=body, body_de=body)
        count += 1
        stats["posts"] += 1
        print(f"新闻: {slug} ({publish:%Y-%m-%d}) ✓")
        if count >= 6:
            break


def main():
    settings = get_settings()
    engine = make_engine(settings.db_path)
    init_db(engine)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    Session = make_session_factory(engine)
    client = httpx.Client(headers=UA, follow_redirects=True)
    with Session() as db:
        seed_settings(db)
        seed_categories(client, db, settings.uploads_dir)
        seed_pages(client, db, settings.uploads_dir)
        seed_home_intro(client, db)
        seed_posts(client, db)
        db.commit()
        from app.search import rebuild_index
        rebuild_index(engine, db)
    client.close()
    print(f"\n种子数据完成: 分类 {stats['categories']}, 页面 {stats['pages']} (+home-intro), "
          f"新闻 {stats['posts']}, 图片 {stats['images']}, "
          f"占位回退 {stats['placeholder_langs']} 个语言版本")


if __name__ == "__main__":
    main()
