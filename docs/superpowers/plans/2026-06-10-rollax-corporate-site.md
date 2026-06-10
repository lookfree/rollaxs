# Rollax 同款四语言企业官网 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按设计文档 `docs/superpowers/specs/2026-06-10-rollax-corporate-site-design.md` 实现 FastAPI + Jinja2 + SQLite 的四语言(中/英/德/日)企业官网,含 /admin 后台、SEO、rollax 内容抓取种子脚本、Docker 部署。

**Architecture:** 单 FastAPI 进程,Jinja2 SSR 前台 + `/admin` 模板后台(htmx 增强),SQLite(WAL)单文件 + 本地 uploads/。语言通过 ASGI 中间件剥离 URL 前缀(`/en/ /de/ /jp/`,中文无前缀)。内容表用 `*_zh/_en/_de/_jp` 四组字段,空值回退中文。

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Jinja2, htmx, Quill(CDN), bcrypt, Pillow, httpx+BeautifulSoup(抓取), pytest, Docker+Nginx。

**约定(全计划通用):**
- 测试命令一律 `python -m pytest tests/ -x -q`(或指定单测)。
- 每个任务结束必须 commit,消息格式 `feat:|fix:|test:|chore: 中文描述`。
- 模板中正文字段已经是后台富文本产生的 HTML,渲染用 `| safe`。
- `pick(obj, "field", lang)`:取 `field_<lang>`,空则回退 `field_zh`。

---

## 文件结构总览

```
app/
  __init__.py
  main.py              # app 工厂、中间件、路由挂载、模板环境
  config.py            # 环境变量配置
  db.py                # engine/Session/Base/init_db(WAL)
  models.py            # 全部 SQLAlchemy 模型
  i18n.py              # LANGS、UI 词条、t()/pick()/lang_url()
  deps.py              # get_db、require_admin、模板上下文
  security.py          # bcrypt、RateLimiter、honeypot
  seo.py               # sitemap/robots/hreflang/JSON-LD
  search.py            # FTS5 建索引与查询
  media.py             # 上传、缩略图、WebP
  mailer.py            # SMTP 询盘通知(可选开启)
  routes/
    front.py           # 首页/页面树/联系/订阅/搜索/招聘/下载/新闻/产品(前台全部)
    admin/
      __init__.py      # admin 总路由
      auth.py          # 登录/登出
      dashboard.py
      content.py       # pages/categories/products/posts/jobs/downloads 通用 CRUD
      media.py
      inquiries.py     # 询盘 + 订阅
      site_settings.py
  templates/
    front/  base.html home.html page.html category.html product.html
            post_list.html post_detail.html jobs.html job_detail.html
            downloads.html contact.html search.html 404.html 500.html
            _macros.html
  static/ css/site.css css/admin.css js/site.js
  templates/admin/  base.html login.html dashboard.html list.html form.html
                    media.html inquiries.html subscribers.html settings.html
                    _i18n_tabs.html
scripts/
  create_admin.py      # 创建/重置管理员
  seed_from_rollax.py  # 抓取 rollax 填充种子数据
  backup.sh
tests/
  conftest.py test_health.py test_models.py test_i18n.py test_front.py
  test_products.py test_posts.py test_forms.py test_search.py test_seo.py
  test_admin_auth.py test_admin_crud.py test_media.py
deploy/
  Dockerfile docker-compose.yml nginx.conf
requirements.txt
README.md
.gitignore
```

---

### Task 1: 项目骨架与依赖

**Files:** Create: `requirements.txt`, `.gitignore`, `app/__init__.py`, `app/config.py`, `app/main.py`, `tests/conftest.py`, `tests/test_health.py`

- [ ] **Step 1: 写依赖与忽略文件**

`requirements.txt`:
```
fastapi==0.115.*
uvicorn[standard]==0.34.*
jinja2==3.1.*
sqlalchemy==2.0.*
python-multipart==0.0.*
itsdangerous==2.2.*
bcrypt==4.*
pillow==11.*
httpx==0.28.*
beautifulsoup4==4.12.*
pytest==8.*
```

`.gitignore`:
```
__pycache__/
*.pyc
data/
uploads/
.venv/
.pytest_cache/
```

- [ ] **Step 2: 建虚拟环境并安装**

Run: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`

- [ ] **Step 3: 写失败测试** `tests/test_health.py`:

```python
from fastapi.testclient import TestClient

def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
```

`tests/conftest.py`(初版,后续任务会扩展):
```python
import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    return create_app()

@pytest.fixture()
def client(app):
    return TestClient(app)
```

- [ ] **Step 4: 跑测试确认失败**(`ModuleNotFoundError: app.main`)

- [ ] **Step 5: 实现** `app/config.py`:

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    def __init__(self):
        self.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
        self.db_path = Path(os.environ.get("DB_PATH", BASE_DIR / "data" / "site.db"))
        self.uploads_dir = Path(os.environ.get("UPLOADS_DIR", BASE_DIR / "uploads"))
        self.base_url = os.environ.get("BASE_URL", "http://localhost:8000")

def get_settings():
    return Settings()
```

`app/main.py`(初版):
```python
from fastapi import FastAPI

def create_app():
    app = FastAPI(docs_url=None, redoc_url=None)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app

app = create_app()
```

注意:config 用 `get_settings()` 每次读 env(测试 monkeypatch 才生效),app 内通过 `app.state.settings` 持有一份。

- [ ] **Step 6: 跑测试通过,commit** `chore: 项目骨架与健康检查`

---

### Task 2: 数据模型与建库

**Files:** Create: `app/db.py`, `app/models.py`, `scripts/create_admin.py`, `tests/test_models.py`

- [ ] **Step 1: 写失败测试** `tests/test_models.py`:

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现** `app/db.py`:

```python
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Base(DeclarativeBase):
    pass

def make_engine(db_path):
    from pathlib import Path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    @event.listens_for(engine, "connect")
    def _pragma(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()
    return engine

def make_session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)

def init_db(engine):
    from app import models  # noqa: F401 注册所有模型
    Base.metadata.create_all(engine)
    from app.search import create_fts  # Task 10 提供;在此之前先建占位函数
    create_fts(engine)
```

`app/models.py` 全部模型(四语言字段全部显式定义,`zh/en/de/jp` 各一组;以下为完整代码):

```python
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

S, T = String(500), Text  # 简写

class I18nSeo:
    """SEO 四语言字段 mixin"""
    seo_title_zh: Mapped[str] = mapped_column(S, default="")
    seo_title_en: Mapped[str] = mapped_column(S, default="")
    seo_title_de: Mapped[str] = mapped_column(S, default="")
    seo_title_jp: Mapped[str] = mapped_column(S, default="")
    seo_desc_zh: Mapped[str] = mapped_column(S, default="")
    seo_desc_en: Mapped[str] = mapped_column(S, default="")
    seo_desc_de: Mapped[str] = mapped_column(S, default="")
    seo_desc_jp: Mapped[str] = mapped_column(S, default="")
    seo_keywords_zh: Mapped[str] = mapped_column(S, default="")
    seo_keywords_en: Mapped[str] = mapped_column(S, default="")
    seo_keywords_de: Mapped[str] = mapped_column(S, default="")
    seo_keywords_jp: Mapped[str] = mapped_column(S, default="")

class Page(Base, I18nSeo):
    __tablename__ = "pages"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("pages.id"), nullable=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    nav_show: Mapped[bool] = mapped_column(Boolean, default=True)
    hero_image: Mapped[str] = mapped_column(S, default="")
    title_zh: Mapped[str] = mapped_column(S, default="")
    title_en: Mapped[str] = mapped_column(S, default="")
    title_de: Mapped[str] = mapped_column(S, default="")
    title_jp: Mapped[str] = mapped_column(S, default="")
    body_zh: Mapped[str] = mapped_column(T, default="")
    body_en: Mapped[str] = mapped_column(T, default="")
    body_de: Mapped[str] = mapped_column(T, default="")
    body_jp: Mapped[str] = mapped_column(T, default="")

class ProductCategory(Base, I18nSeo):
    __tablename__ = "product_categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("product_categories.id"), nullable=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    card_image: Mapped[str] = mapped_column(S, default="")
    hero_image: Mapped[str] = mapped_column(S, default="")
    name_zh: Mapped[str] = mapped_column(S, default="")
    name_en: Mapped[str] = mapped_column(S, default="")
    name_de: Mapped[str] = mapped_column(S, default="")
    name_jp: Mapped[str] = mapped_column(S, default="")
    intro_zh: Mapped[str] = mapped_column(T, default="")
    intro_en: Mapped[str] = mapped_column(T, default="")
    intro_de: Mapped[str] = mapped_column(T, default="")
    intro_jp: Mapped[str] = mapped_column(T, default="")

class Product(Base, I18nSeo):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("product_categories.id"))
    sort: Mapped[int] = mapped_column(Integer, default=0)
    image: Mapped[str] = mapped_column(S, default="")
    gallery: Mapped[str] = mapped_column(T, default="[]")  # JSON 数组字符串
    hero_image: Mapped[str] = mapped_column(S, default="")
    name_zh: Mapped[str] = mapped_column(S, default="")
    name_en: Mapped[str] = mapped_column(S, default="")
    name_de: Mapped[str] = mapped_column(S, default="")
    name_jp: Mapped[str] = mapped_column(S, default="")
    body_zh: Mapped[str] = mapped_column(T, default="")
    body_en: Mapped[str] = mapped_column(T, default="")
    body_de: Mapped[str] = mapped_column(T, default="")
    body_jp: Mapped[str] = mapped_column(T, default="")

class Post(Base, I18nSeo):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    cover: Mapped[str] = mapped_column(S, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|published
    publish_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    title_zh: Mapped[str] = mapped_column(S, default="")
    title_en: Mapped[str] = mapped_column(S, default="")
    title_de: Mapped[str] = mapped_column(S, default="")
    title_jp: Mapped[str] = mapped_column(S, default="")
    excerpt_zh: Mapped[str] = mapped_column(T, default="")
    excerpt_en: Mapped[str] = mapped_column(T, default="")
    excerpt_de: Mapped[str] = mapped_column(T, default="")
    excerpt_jp: Mapped[str] = mapped_column(T, default="")
    body_zh: Mapped[str] = mapped_column(T, default="")
    body_en: Mapped[str] = mapped_column(T, default="")
    body_de: Mapped[str] = mapped_column(T, default="")
    body_jp: Mapped[str] = mapped_column(T, default="")

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(20), default="social")  # social|student|training
    status: Mapped[str] = mapped_column(String(20), default="open")  # open|closed
    sort: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    title_zh: Mapped[str] = mapped_column(S, default="")
    title_en: Mapped[str] = mapped_column(S, default="")
    title_de: Mapped[str] = mapped_column(S, default="")
    title_jp: Mapped[str] = mapped_column(S, default="")
    body_zh: Mapped[str] = mapped_column(T, default="")
    body_en: Mapped[str] = mapped_column(T, default="")
    body_de: Mapped[str] = mapped_column(T, default="")
    body_jp: Mapped[str] = mapped_column(T, default="")

class Download(Base):
    __tablename__ = "downloads"
    id: Mapped[int] = mapped_column(primary_key=True)
    file_path: Mapped[str] = mapped_column(S, default="")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    category_zh: Mapped[str] = mapped_column(S, default="")
    category_en: Mapped[str] = mapped_column(S, default="")
    category_de: Mapped[str] = mapped_column(S, default="")
    category_jp: Mapped[str] = mapped_column(S, default="")
    title_zh: Mapped[str] = mapped_column(S, default="")
    title_en: Mapped[str] = mapped_column(S, default="")
    title_de: Mapped[str] = mapped_column(S, default="")
    title_jp: Mapped[str] = mapped_column(S, default="")

class Inquiry(Base):
    __tablename__ = "inquiries"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(S, default="")
    email: Mapped[str] = mapped_column(S, default="")
    company: Mapped[str] = mapped_column(S, default="")
    phone: Mapped[str] = mapped_column(S, default="")
    message: Mapped[str] = mapped_column(T, default="")
    source_path: Mapped[str] = mapped_column(S, default="")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Subscriber(Base):
    __tablename__ = "subscribers"
    id: Mapped[int] = mapped_column(primary_key=True)
    salutation: Mapped[str] = mapped_column(String(50), default="")
    first_name: Mapped[str] = mapped_column(S, default="")
    last_name: Mapped[str] = mapped_column(S, default="")
    email: Mapped[str] = mapped_column(S, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Media(Base):
    __tablename__ = "media"
    id: Mapped[int] = mapped_column(primary_key=True)
    path: Mapped[str] = mapped_column(S)            # 相对 uploads/ 的路径
    kind: Mapped[str] = mapped_column(String(20))   # image|file
    thumb_path: Mapped[str] = mapped_column(S, default="")
    webp_path: Mapped[str] = mapped_column(S, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(T, default="")

class AdminUser(Base):
    __tablename__ = "admin_users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(S)
```

`app/search.py` 先建占位(Task 10 替换实现):
```python
def create_fts(engine):
    pass
```

`scripts/create_admin.py`:
```python
"""用法: .venv/bin/python scripts/create_admin.py <用户名> <密码>"""
import sys
sys.path.insert(0, ".")
from app.config import get_settings
from app.db import make_engine, make_session_factory, init_db
from app.models import AdminUser
from app.security import hash_password

def main():
    username, password = sys.argv[1], sys.argv[2]
    s = get_settings()
    engine = make_engine(s.db_path)
    init_db(engine)
    with make_session_factory(engine)() as db:
        user = db.query(AdminUser).filter_by(username=username).first()
        if user:
            user.password_hash = hash_password(password)
        else:
            db.add(AdminUser(username=username, password_hash=hash_password(password)))
        db.commit()
    print(f"管理员 {username} 已就绪")

if __name__ == "__main__":
    main()
```

`app/security.py`(本任务先实现哈希部分):
```python
import bcrypt

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False
```

- [ ] **Step 4: 跑测试通过,commit** `feat: 数据模型与建库`

---

### Task 3: i18n 基础设施

**Files:** Create: `app/i18n.py`, `tests/test_i18n.py`; Modify: `app/main.py`

- [ ] **Step 1: 写失败测试** `tests/test_i18n.py`:

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现** `app/i18n.py`:

```python
LANGS = ["zh", "en", "de", "jp"]
DEFAULT_LANG = "zh"
LANG_NAMES = {"zh": "中文", "en": "English", "de": "Deutsch", "jp": "日本語"}

UI = {
    "nav.home":      {"zh": "首页", "en": "Home", "de": "Startseite", "jp": "ホーム"},
    "nav.products":  {"zh": "产品", "en": "Products", "de": "Produkte", "jp": "製品"},
    "nav.company":   {"zh": "公司", "en": "Company", "de": "Unternehmen", "jp": "会社"},
    "nav.career":    {"zh": "招聘", "en": "Career", "de": "Karriere", "jp": "採用"},
    "nav.news":      {"zh": "新闻", "en": "News", "de": "Aktuelles", "jp": "ニュース"},
    "nav.downloads": {"zh": "下载", "en": "Downloads", "de": "Downloads", "jp": "ダウンロード"},
    "nav.contact":   {"zh": "联系我们", "en": "Contact", "de": "Kontakt", "jp": "お問い合わせ"},
    "btn.readmore":  {"zh": "继续阅读", "en": "Read more", "de": "Weiterlesen", "jp": "続きを読む"},
    "btn.subscribe": {"zh": "订阅", "en": "Subscribe", "de": "Anmelden", "jp": "登録"},
    "btn.send":      {"zh": "发送", "en": "Send", "de": "Senden", "jp": "送信"},
    "btn.inquiry":   {"zh": "发送询盘", "en": "Send inquiry", "de": "Anfrage senden", "jp": "お問い合わせ"},
    "label.search":  {"zh": "搜索", "en": "Search", "de": "Suche", "jp": "検索"},
    "label.breadcrumb_home": {"zh": "首页", "en": "Home", "de": "Startseite", "jp": "ホーム"},
    "newsletter.title": {"zh": "订阅我们的新闻", "en": "Newsletter", "de": "Newsletter", "jp": "ニュースレター"},
    "form.name":  {"zh": "姓名", "en": "Name", "de": "Name", "jp": "お名前"},
    "form.email": {"zh": "邮箱", "en": "E-Mail", "de": "E-Mail", "jp": "メール"},
    "form.company": {"zh": "公司", "en": "Company", "de": "Firma", "jp": "会社名"},
    "form.message": {"zh": "留言", "en": "Message", "de": "Nachricht", "jp": "メッセージ"},
    "msg.thanks": {"zh": "提交成功,我们会尽快联系您。", "en": "Thank you, we will contact you soon.",
                    "de": "Vielen Dank, wir melden uns in Kürze.", "jp": "送信しました。担当者よりご連絡いたします。"},
}
# 执行时按模板实际用到的词条继续补充 UI 字典,保持同结构。

def t(key: str, lang: str) -> str:
    entry = UI.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get(DEFAULT_LANG) or key

def pick(obj, field: str, lang: str) -> str:
    val = getattr(obj, f"{field}_{lang}", "") or ""
    if not val and lang != DEFAULT_LANG:
        val = getattr(obj, f"{field}_{DEFAULT_LANG}", "") or ""
    return val

def lang_url(lang: str, path: str) -> str:
    if lang == DEFAULT_LANG:
        return path
    return f"/{lang}{path}"
```

`app/main.py` 中加语言中间件(`http` 中间件,在路由前剥离前缀):

```python
NON_LANG_PREFIXES = ("/admin", "/static", "/uploads", "/healthz")

def create_app():
    app = FastAPI(docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def lang_middleware(request, call_next):
        path = request.scope["path"]
        lang = "zh"
        if not path.startswith(NON_LANG_PREFIXES):
            for code in ("en", "de", "jp"):
                if path == f"/{code}" or path.startswith(f"/{code}/"):
                    lang = code
                    request.scope["path"] = path[len(code) + 1:] or "/"
                    break
        request.state.lang = lang
        return await call_next(request)
    ...
```

注意:`/en/healthz` 测试里会被剥成 `/healthz`,符合预期(healthz 不在排除名单的语言前缀下不影响)。

- [ ] **Step 4: 跑测试通过,commit** `feat: 四语言基础设施(前缀路由/回退/UI词条)`

---

### Task 4: 前台基础模板、静态资源与全局上下文

**Files:** Create: `app/deps.py`, `app/templates/front/base.html`, `_macros.html`, `404.html`, `500.html`, `app/static/css/site.css`, `app/static/js/site.js`, `app/routes/front.py`(初版只有首页占位); Modify: `app/main.py`, `tests/conftest.py`

- [ ] **Step 1: 写失败测试** 加入 `tests/test_front.py`:

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现**

`app/deps.py`:
```python
from fastapi import Request

def get_db(request: Request):
    db = request.app.state.session_factory()
    try:
        yield db
    finally:
        db.close()
```

`app/main.py` 完整化:create_app 中初始化 engine/session_factory/templates 并挂载:

```python
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from app.config import get_settings, BASE_DIR
from app.db import make_engine, make_session_factory, init_db
from app import i18n

def create_app():
    settings = get_settings()
    app = FastAPI(docs_url=None, redoc_url=None)
    app.state.settings = settings
    engine = make_engine(settings.db_path)
    init_db(engine)
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)

    app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, same_site="lax")
    # (语言中间件,Task 3 已写)

    templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
    templates.env.globals.update(t=i18n.t, pick=i18n.pick, lang_url=i18n.lang_url,
                                 LANGS=i18n.LANGS, LANG_NAMES=i18n.LANG_NAMES)
    app.state.templates = templates

    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
    app.mount("/uploads", StaticFiles(directory=str(settings.uploads_dir)), name="uploads")

    from app.routes.front import router as front_router
    app.include_router(front_router)

    @app.exception_handler(404)
    async def not_found(request: Request, exc):
        lang = getattr(request.state, "lang", "zh")
        return templates.TemplateResponse(request, "front/404.html",
                                          {"lang": lang}, status_code=404)
    @app.get("/healthz")
    def healthz():
        return {"ok": True}
    return app

app = create_app()
```

`app/routes/front.py` 初版:

```python
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from app.deps import get_db

router = APIRouter()

def render(request: Request, name: str, ctx: dict, status_code: int = 200):
    ctx.setdefault("lang", request.state.lang)
    ctx.setdefault("path", request.scope["path"])
    return request.app.state.templates.TemplateResponse(request, name, ctx, status_code=status_code)

@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    return render(request, "front/home.html", {})
```

`app/templates/front/base.html` 骨架(关键结构,深蓝顶栏+白产品栏+页脚;导航数据 Task 5/6 注入):

```html
<!doctype html>
<html lang="{{ lang }}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}{{ site.get('site_name','') }}{% endblock %}</title>
  {% block seo %}{% endblock %}
  <link rel="stylesheet" href="/static/css/site.css">
</head>
<body>
<header class="topbar">
  <nav class="topbar__nav">{% block topnav %}{% endblock %}</nav>
  <div class="topbar__meta">
    <a href="tel:{{ site.get('phone','') }}">{{ site.get('phone','') }}</a>
    <a class="search-ico" href="{{ lang_url(lang, '/search/') }}">🔍</a>
    {% for code in LANGS %}<a class="lang {{ 'on' if code==lang }}" href="{{ lang_url(code, path) }}">{{ code }}</a>{% endfor %}
  </div>
</header>
<div class="prodbar">{% block prodbar %}{% endblock %}</div>
<main>{% block content %}{% endblock %}</main>
<section class="newsletter">…订阅表单(Task 9 实现 POST)…</section>
<footer class="footer">…联系方式/社交/世界地图/法务链接(从 site 设置读取)…</footer>
<script src="/static/js/site.js" defer></script>
</body>
</html>
```

`site.css` 设计变量(按截图取色):
```css
:root{
  --blue-900:#0d2c6b;  /* 顶栏/页脚深蓝 */
  --blue-600:#1a4ea3;  /* 标题蓝 */
  --ink:#333; --line:#e5e7eb; --bg-soft:#f7f8fa;
  --font:"Helvetica Neue",Arial,"PingFang SC","Hiragino Sans",sans-serif;
}
```
完整版式(双层导航高度、卡片阴影、按钮带右箭头方块等)在 Task 18 对照截图打磨。

模板上下文里的 `site` 字典:在 `render()` 中查询 settings 表灌入(本任务实现:`site = {row.key: row.value for row in db.query(Setting)}`,首页路由先传 `db`)。

- [ ] **Step 4: 跑测试通过,commit** `feat: 前台基础模板与静态资源`

---

### Task 5: 通用页面模块(前台)

**Files:** Create: `app/templates/front/page.html`; Modify: `app/routes/front.py`, `tests/test_front.py`

页面树规则:一级页面 `/{slug}/`,二级 `/{parent}/{slug}/`,以此类推(最多三级)。导航 = `nav_show=True` 的根页面 + 固定项(产品/新闻/招聘/下载/联系)。

- [ ] **Step 1: 写失败测试**(加入 test_front.py):

```python
from app.models import Page

def test_page_render_and_fallback(client, db):
    p1 = Page(slug="company", title_zh="公司", title_en="Company", body_zh="<p>中文正文</p>")
    db.add(p1); db.flush()
    db.add(Page(slug="quality", parent_id=p1.id, title_zh="质量", body_zh="<p>质量正文</p>"))
    db.commit()
    assert "公司" in client.get("/company/").text
    r = client.get("/en/company/quality/")
    assert r.status_code == 200
    assert "质量正文" in r.text          # 英文为空回退中文
    assert client.get("/company/nope/").status_code == 404
```

conftest 需补 `db` fixture(直接用 app.state.session_factory)。

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现** front.py 加路由(放在文件**最后**,作为兜底路由):

```python
@router.get("/{path:path}/")
def page_view(path: str, request: Request, db: Session = Depends(get_db)):
    node, parent = None, None
    for slug in [s for s in path.split("/") if s]:
        node = db.query(Page).filter_by(slug=slug).first()
        if node is None or (parent and node.parent_id != parent.id):
            raise HTTPException(404)
        parent = node
    if node is None:
        raise HTTPException(404)
    crumbs = build_page_crumbs(db, node)   # 沿 parent_id 上溯
    return render(request, "front/page.html", {"page": node, "crumbs": crumbs})
```

`page.html`:Hero 图(若有)+ 面包屑 + 标题 + `{{ pick(page,'body',lang) | safe }}` + 子页面卡片(若有 children)。
导航注入:`render()` 中统一查 `nav_pages = db.query(Page).filter_by(parent_id=None, nav_show=True).order_by(Page.sort)` 放入 ctx(给 base.html topnav 块用,含下拉子页)。

- [ ] **Step 4: 跑测试通过,commit** `feat: 通用页面树前台`

---

### Task 6: 产品模块(前台)

**Files:** Create: `app/templates/front/category.html`, `product.html`; Modify: `app/routes/front.py`, `app/templates/front/home.html`, `tests/test_products.py`

URL:`/products/` 总览、`/products/{cat}/` 分类(可嵌套 `/products/{cat}/{sub}/`)、`/products/{cat}/.../{slug}.html` 产品详情(用 `.html` 后缀区分分类与产品,避免歧义)。

- [ ] **Step 1: 写失败测试** `tests/test_products.py`:

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现** front.py:

```python
@router.get("/products/")
def products_index(request: Request, db: Session = Depends(get_db)):
    roots = db.query(ProductCategory).filter_by(parent_id=None).order_by(ProductCategory.sort).all()
    return render(request, "front/category.html", {"cat": None, "children": roots, "products": []})

@router.get("/products/{path:path}.html")
def product_detail(path: str, request: Request, db: Session = Depends(get_db)):
    slug = path.split("/")[-1]
    prod = db.query(Product).filter_by(slug=slug).first()
    if not prod:
        raise HTTPException(404)
    cat = db.get(ProductCategory, prod.category_id)
    tree = category_tree(db)        # 全量分类树给侧边栏
    crumbs = build_cat_crumbs(db, cat) + [prod]
    return render(request, "front/product.html",
                  {"prod": prod, "cat": cat, "tree": tree, "crumbs": crumbs})

@router.get("/products/{path:path}/")
def category_view(path: str, request: Request, db: Session = Depends(get_db)):
    cat = resolve_category_path(db, path)   # 逐段校验 parent 链,找不到 404
    children = db.query(ProductCategory).filter_by(parent_id=cat.id).order_by(ProductCategory.sort).all()
    products = db.query(Product).filter_by(category_id=cat.id).order_by(Product.sort).all()
    return render(request, "front/category.html",
                  {"cat": cat, "children": children, "products": products,
                   "tree": category_tree(db), "crumbs": build_cat_crumbs(db, cat)})
```

辅助函数 `category_tree(db)`(一次查询按 parent 分组返回 `{parent_id: [cat,...]}`)、`build_cat_crumbs`、`resolve_category_path`、`cat_url(db_or_tree, cat)`(沿 parent 拼 `/products/a/b/`)写在 front.py 顶部,模板通过 globals 暴露 `cat_url`。

`category.html`:Hero + 面包屑 + 简介 + 子分类/产品卡片墙(参照 rollax 卡片:图+标题+蓝色下划线)。
`product.html`:Hero + 面包屑 + 两栏(正文 | 右侧产品树 + "发送询盘"按钮链到 `/contact/?about={slug}`)。
`home.html` 完整化:Hero(`site.home_hero_video` 有值则 `<video>`,否则大图)+ 介绍区(`pages` 里 slug=`home-intro` 的正文)+ 根分类卡片墙。

- [ ] **Step 4: 跑测试通过,commit** `feat: 产品分类树与详情前台`

---

### Task 7: 新闻模块(前台)

**Files:** Create: `app/templates/front/post_list.html`, `post_detail.html`; Modify: `app/routes/front.py`, `tests/test_posts.py`

- [ ] **Step 1: 写失败测试** `tests/test_posts.py`:

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现** front.py:

```python
PAGE_SIZE = 10

@router.get("/news/")
def news_list(request: Request, page: int = 1, db: Session = Depends(get_db)):
    q = (db.query(Post).filter(Post.status == "published",
                               Post.publish_at <= datetime.utcnow())
                       .order_by(Post.publish_at.desc()))
    total = q.count()
    posts = q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    pages = max(1, -(-total // PAGE_SIZE))
    return render(request, "front/post_list.html", {"posts": posts, "page": page, "pages": pages})

@router.get("/news/{slug}.html")
def news_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    post = db.query(Post).filter_by(slug=slug, status="published").first()
    if not post:
        raise HTTPException(404)
    return render(request, "front/post_detail.html", {"post": post})
```

`post_list.html` 按 rollax 版式:页码条(数字+箭头)、每条 = 左缩略图 + 标题 + 摘要 + 日期 + 「继续阅读」按钮(`t('btn.readmore', lang)`)。

- [ ] **Step 4: 跑测试通过,commit** `feat: 新闻列表与详情前台`

---

### Task 8: 招聘与下载(前台)

**Files:** Create: `app/templates/front/jobs.html`, `job_detail.html`, `downloads.html`; Modify: `app/routes/front.py`, `tests/test_front.py`

- [ ] **Step 1: 写失败测试**:

```python
from app.models import Job, Download

def test_jobs_and_downloads(client, db):
    db.add(Job(title_zh="数控工程师", body_zh="<p>职责</p>", category="social"))
    db.add(Job(title_zh="已关闭岗位", status="closed"))
    db.add(Download(title_zh="产品手册", category_zh="手册", file_path="2026/01/cat.pdf", file_size=1024))
    db.commit()
    r = client.get("/career/")
    assert "数控工程师" in r.text and "已关闭岗位" not in r.text
    job_id = db.query(Job).filter_by(title_zh="数控工程师").one().id
    assert "职责" in client.get(f"/career/{job_id}.html").text
    r = client.get("/downloads/")
    assert "产品手册" in r.text and "/uploads/2026/01/cat.pdf" in r.text
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现** 路由 `/career/`(按 category 分组三个 Tab:社招/学生/培训)、`/career/{id}.html`、`/downloads/`(按 category 分组列表,显示文件大小 KB/MB)。代码与 Task 7 同构,查询条件 `status=="open"`,排序 `sort`。

- [ ] **Step 4: 跑测试通过,commit** `feat: 招聘与下载前台`

---

### Task 9: 询盘表单与 Newsletter 订阅

**Files:** Create: `app/templates/front/contact.html`, `app/mailer.py`; Modify: `app/routes/front.py`, `app/security.py`, `app/templates/front/base.html`, `tests/test_forms.py`

- [ ] **Step 1: 写失败测试** `tests/test_forms.py`:

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现**

`app/security.py` 加:
```python
import time
from collections import defaultdict, deque

class RateLimiter:
    def __init__(self, max_hits: int = 5, window_sec: int = 60):
        self.max_hits, self.window = max_hits, window_sec
        self.hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.max_hits:
            return False
        q.append(now)
        return True
```

front.py:`form_limiter = RateLimiter(5, 60)`,POST `/contact/` 与 `/newsletter/`:
- `website` 字段非空(honeypot)→ 直接返回成功页但不落库;
- `form_limiter.allow(request.client.host)` 为 False → 429;
- 校验 email 含 `@`、message 非空(contact),否则带错误信息重渲染表单;
- 落库后渲染感谢信息(`t('msg.thanks', lang)`);contact 落库后调 `mailer.notify_inquiry(site, inquiry)`(SMTP 未配置时静默跳过,`try/except` 包裹)。

`app/mailer.py`:
```python
import smtplib
from email.mime.text import MIMEText

def notify_inquiry(site: dict, inquiry) -> None:
    host = site.get("smtp_host")
    if not host:
        return
    msg = MIMEText(f"姓名: {inquiry.name}\n邮箱: {inquiry.email}\n公司: {inquiry.company}\n"
                   f"电话: {inquiry.phone}\n留言:\n{inquiry.message}", "plain", "utf-8")
    msg["Subject"] = f"[官网询盘] {inquiry.name}"
    msg["From"] = site.get("smtp_from", site.get("smtp_user", ""))
    msg["To"] = site.get("inquiry_to", "")
    with smtplib.SMTP(host, int(site.get("smtp_port", "587")), timeout=10) as s:
        if site.get("smtp_tls", "1") == "1":
            s.starttls()
        if site.get("smtp_user"):
            s.login(site["smtp_user"], site.get("smtp_password", ""))
        s.send_message(msg)
```

base.html 的 newsletter 区块换成真实表单(称谓下拉+名+姓+邮箱+订阅按钮+隐藏 honeypot)。

- [ ] **Step 4: 跑测试通过,commit** `feat: 询盘与订阅表单(honeypot+限速+SMTP通知)`

---

### Task 10: 站内搜索(FTS5)

**Files:** Modify: `app/search.py`, `app/routes/front.py`; Create: `app/templates/front/search.html`, `tests/test_search.py`

- [ ] **Step 1: 写失败测试**:

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现** `app/search.py`:

```python
import re
from sqlalchemy import text
from app.i18n import LANGS

def create_fts(engine):
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5("
            "kind, ref_id UNINDEXED, lang, title, content, url UNINDEXED)"))
        conn.commit()

def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", " ", s or "")

def rebuild_index(engine, db):
    """全量重建:产品/页面/新闻 × 四语言。后台保存内容时调用。"""
    from app.models import Product, Page, Post
    from app.routes.front import cat_url_by_id   # 拼产品 URL
    db.execute(text("DELETE FROM search_index"))
    rows = []
    for p in db.query(Product).all():
        for lang in LANGS:
            title = getattr(p, f"name_{lang}") or p.name_zh
            body = _strip_html(getattr(p, f"body_{lang}") or p.body_zh)
            rows.append(("product", p.id, lang, title, body, cat_url_by_id(db, p.category_id) + f"{p.slug}.html"))
    for pg in db.query(Page).all():
        for lang in LANGS:
            rows.append(("page", pg.id, lang, getattr(pg, f"title_{lang}") or pg.title_zh,
                         _strip_html(getattr(pg, f"body_{lang}") or pg.body_zh), page_url(db, pg)))
    for po in db.query(Post).filter_by(status="published").all():
        for lang in LANGS:
            rows.append(("post", po.id, lang, getattr(po, f"title_{lang}") or po.title_zh,
                         _strip_html(getattr(po, f"body_{lang}") or po.body_zh), f"/news/{po.slug}.html"))
    for r in rows:
        db.execute(text("INSERT INTO search_index VALUES (:k,:i,:l,:t,:c,:u)"),
                   {"k": r[0], "i": r[1], "l": r[2], "t": r[3], "c": r[4], "u": r[5]})
    db.commit()

def query_index(db, q: str, lang: str, limit: int = 30):
    safe = '"' + q.replace('"', " ") + '"'
    rs = db.execute(text(
        "SELECT kind, title, url, snippet(search_index, 4, '<b>', '</b>', '…', 12) AS snip "
        "FROM search_index WHERE search_index MATCH :q AND lang = :lang "
        "ORDER BY bm25(search_index) LIMIT :n"), {"q": safe, "lang": lang, "n": limit})
    return [dict(r._mapping) for r in rs]
```

(`page_url`/`cat_url_by_id` 为 front.py 已有 URL 拼接函数;循环引用用函数内 import 解决。)
front.py 加 `GET /search/`:`q` 为空显示空表单;有值调 `query_index` 渲染结果列表。

- [ ] **Step 4: 跑测试通过,commit** `feat: FTS5 站内搜索`

---

### Task 11: SEO(meta/hreflang/canonical/JSON-LD/sitemap/robots)

**Files:** Create: `app/seo.py`, `tests/test_seo.py`; Modify: `app/routes/front.py`, 各前台模板 seo 块

- [ ] **Step 1: 写失败测试** `tests/test_seo.py`:

```python
def test_hreflang_and_canonical(client, db):
    from app.models import Page
    db.add(Page(slug="company", title_zh="公司", seo_title_en="Company Ltd")); db.commit()
    html = client.get("/en/company/").text
    assert '<link rel="alternate" hreflang="de" href="http://localhost:8000/de/company/"' in html
    assert 'hreflang="x-default"' in html
    assert '<link rel="canonical" href="http://localhost:8000/en/company/"' in html
    assert "<title>Company Ltd" in html

def test_sitemap_and_robots(client, db):
    from app.models import Page
    db.add(Page(slug="company", title_zh="公司")); db.commit()
    xml = client.get("/sitemap.xml").text
    assert "/de/company/" in xml and "<urlset" in xml
    assert "Sitemap:" in client.get("/robots.txt").text

def test_breadcrumb_jsonld(client, db):
    from app.models import Page
    db.add(Page(slug="company", title_zh="公司")); db.commit()
    assert '"@type": "BreadcrumbList"' in client.get("/company/").text
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现** `app/seo.py`:

```python
from app.i18n import LANGS, lang_url

def alternates(base_url: str, logical_path: str):
    alts = [(l, base_url + lang_url(l, logical_path)) for l in LANGS]
    return alts + [("x-default", base_url + logical_path)]

def breadcrumb_jsonld(base_url, lang, crumbs):
    import json
    items = [{"@type": "ListItem", "position": i + 1, "name": name,
              "item": base_url + lang_url(lang, url)} for i, (name, url) in enumerate(crumbs)]
    return json.dumps({"@context": "https://schema.org",
                       "@type": "BreadcrumbList", "itemListElement": items},
                      ensure_ascii=False, indent=1)
```

- `render()` 注入 `alternates=alternates(settings.base_url, request.scope["path"])`、`canonical`。
- base.html `<head>` 输出 alternates/canonical/OG 标签;`{% block seo %}` 由各模板填 `pick(obj,'seo_title',lang) or pick(obj,'title',lang)` 等;description 同理,keywords 有值才输出。
- front.py 加 `GET /sitemap.xml`(遍历 pages/分类/产品/新闻,每个 URL 输出 4 语言条目 + lastmod)与 `GET /robots.txt`(`User-agent: *\nAllow: /\nDisallow: /admin/\nSitemap: {base}/sitemap.xml`)。
- 图片统一 `loading="lazy"`(模板宏 `_macros.html` 里写 `img()` 宏)。

- [ ] **Step 4: 跑测试通过,commit** `feat: SEO 基建(hreflang/canonical/JSON-LD/sitemap)`

---

### Task 12: 后台认证与框架

**Files:** Create: `app/routes/admin/__init__.py`, `auth.py`, `dashboard.py`, `app/templates/admin/base.html`, `login.html`, `dashboard.html`, `app/static/css/admin.css`, `tests/test_admin_auth.py`; Modify: `app/main.py`, `app/deps.py`

- [ ] **Step 1: 写失败测试**:

```python
def login(client, password="pw12345"):
    return client.post("/admin/login", data={"username": "boss", "password": password})

def test_login_flow(client, db, admin_user):
    assert client.get("/admin/").status_code == 303          # 未登录跳 login
    r = login(client, "wrong")
    assert "用户名或密码错误" in r.text
    r = login(client)
    assert r.status_code == 303 and r.headers["location"] == "/admin/"
    assert client.get("/admin/").status_code == 200
    client.get("/admin/logout")
    assert client.get("/admin/").status_code == 303

def test_login_rate_limit(client, db, admin_user):
    for _ in range(11):
        r = login(client, "wrong")
    assert r.status_code == 429
```

conftest 加 `admin_user` fixture(用 `hash_password("pw12345")` 插入 boss),`client` 设 `follow_redirects=False`。

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现**

`app/deps.py` 加:
```python
from fastapi import HTTPException
from starlette.responses import RedirectResponse

class RequiresLogin(Exception):
    pass

def require_admin(request: Request):
    if not request.session.get("admin_id"):
        raise RequiresLogin()
    return request.session["admin_id"]
```
main.py 注册 `@app.exception_handler(RequiresLogin)` → `RedirectResponse("/admin/login", 303)`。

`auth.py`:GET/POST `/admin/login`(POST 验证 `verify_password`,限速 `RateLimiter(10, 300)` 按 IP;成功 `request.session["admin_id"] = user.id` 跳 `/admin/`)、GET `/admin/logout`(清 session)。
`dashboard.py`:`/admin/` 显示统计(各表 count、最新 5 条询盘)。
`admin/base.html`:左侧菜单(仪表盘/页面/产品分类/产品/新闻/招聘/下载/媒体库/询盘/订阅/设置)+ 顶栏(登出),引入 htmx CDN `<script src="https://unpkg.com/htmx.org@2"></script>` 与 admin.css(朴素表格风)。
`app/routes/admin/__init__.py` 汇总子路由为 `admin_router`(prefix="/admin",除 login 外全部 `dependencies=[Depends(require_admin)]`),main.py include。

- [ ] **Step 4: 跑测试通过,commit** `feat: 后台登录认证与框架`

---

### Task 13: 媒体库

**Files:** Create: `app/media.py`, `app/routes/admin/media.py`, `app/templates/admin/media.html`, `tests/test_media.py`

- [ ] **Step 1: 写失败测试**:

```python
import io
from PIL import Image

def make_png(w=800, h=600):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "#0d2c6b").save(buf, "PNG")
    buf.seek(0)
    return buf

def test_upload_image(logged_client, db, app):
    r = logged_client.post("/admin/media/upload",
                           files={"file": ("test.png", make_png(), "image/png")})
    assert r.status_code == 200
    m = db.query(Media).one()
    assert m.kind == "image" and m.thumb_path and m.webp_path
    uploads = app.state.settings.uploads_dir
    assert (uploads / m.path).exists() and (uploads / m.webp_path).exists()

def test_upload_rejects_exe(logged_client):
    r = logged_client.post("/admin/media/upload",
                           files={"file": ("x.exe", io.BytesIO(b"MZ"), "application/x-msdownload")})
    assert r.status_code == 400
```

conftest 加 `logged_client` fixture(admin_user + 登录后的 client)。

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现** `app/media.py`:

```python
import re, time
from pathlib import Path
from PIL import Image

ALLOWED = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf", ".zip", ".mp4"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

def save_upload(uploads_dir: Path, filename: str, data: bytes):
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED:
        raise ValueError(f"不允许的文件类型: {ext}")
    stem = re.sub(r"[^a-zA-Z0-9_-]", "-", Path(filename).stem)[:60] or "file"
    sub = time.strftime("%Y/%m")
    rel = f"{sub}/{stem}-{int(time.time()*1000)%100000}{ext}"
    abs_path = uploads_dir / rel
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(data)
    kind = "image" if ext in IMAGE_EXT else "file"
    thumb_rel = webp_rel = ""
    if kind == "image" and ext != ".gif":
        img = Image.open(abs_path).convert("RGB")
        t = img.copy(); t.thumbnail((400, 400))
        thumb_rel = rel.rsplit(ext, 1)[0] + ".thumb.jpg"
        t.save(uploads_dir / thumb_rel, "JPEG", quality=82)
        webp_rel = rel.rsplit(ext, 1)[0] + ".webp"
        img.save(uploads_dir / webp_rel, "WEBP", quality=82)
    return rel, kind, thumb_rel, webp_rel
```

admin/media.py:`POST /admin/media/upload`(写 Media 行,返回 JSON `{url, id}` — Quill 图片上传也调它)、`GET /admin/media`(分页网格,htmx 删除按钮 `DELETE /admin/media/{id}` 同时删文件)。

- [ ] **Step 4: 跑测试通过,commit** `feat: 媒体库(上传/缩略图/WebP)`

---

### Task 14: 后台内容 CRUD — 通用框架 + 页面/分类/产品

**Files:** Create: `app/routes/admin/content.py`, `app/templates/admin/list.html`, `form.html`, `_i18n_tabs.html`, `tests/test_admin_crud.py`

核心思路:**一套通用 CRUD 引擎,六种内容各给一份字段描述**,避免六份重复代码。

- [ ] **Step 1: 写失败测试**:

```python
def test_page_crud(logged_client, db):
    r = logged_client.post("/admin/pages/new", data={
        "slug": "about", "title_zh": "关于", "body_zh": "<p>x</p>",
        "nav_show": "1", "sort": "0"})
    assert r.status_code == 303
    pid = db.query(Page).filter_by(slug="about").one().id
    assert "关于" in logged_client.get("/admin/pages").text
    logged_client.post(f"/admin/pages/{pid}", data={"slug": "about", "title_zh": "关于我们",
                                                    "nav_show": "1", "sort": "0"})
    db.expire_all()
    assert db.get(Page, pid).title_zh == "关于我们"
    logged_client.post(f"/admin/pages/{pid}/delete")
    assert db.query(Page).count() == 0

def test_product_crud_updates_search_index(logged_client, db):
    logged_client.post("/admin/categories/new", data={"slug": "c1", "name_zh": "分类", "sort": "0"})
    cid = db.query(ProductCategory).one().id
    logged_client.post("/admin/products/new", data={
        "slug": "p1", "category_id": str(cid), "name_zh": "产品一",
        "name_en": "Product One", "sort": "0"})
    from app.search import query_index
    assert query_index(db, "Product", "en")     # 保存后索引已重建

def test_crud_requires_login(client):
    assert client.get("/admin/pages").status_code == 303
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现** `content.py` 通用引擎:

```python
from dataclasses import dataclass, field

@dataclass
class ContentType:
    key: str                  # url 段,如 "pages"
    model: type
    label: str                # 菜单名
    i18n_fields: list[tuple]  # [(字段名, 控件), ...] 控件: text|rich|textarea
    plain_fields: list[tuple] # 非多语言字段 [(名, 控件), ...] 控件: text|number|check|image|file|select:xxx|datetime
    has_seo: bool = True
    tree: bool = False        # 树形(pages/categories)
    order_by: str = "sort"
    reindex: bool = False     # 保存后重建搜索索引

CONTENT_TYPES = {ct.key: ct for ct in [
    ContentType("pages", Page, "页面",
                i18n_fields=[("title", "text"), ("body", "rich")],
                plain_fields=[("slug", "text"), ("parent_id", "select:pages"),
                              ("sort", "number"), ("nav_show", "check"), ("hero_image", "image")],
                tree=True, reindex=True),
    ContentType("categories", ProductCategory, "产品分类",
                i18n_fields=[("name", "text"), ("intro", "rich")],
                plain_fields=[("slug", "text"), ("parent_id", "select:categories"),
                              ("sort", "number"), ("card_image", "image"), ("hero_image", "image")],
                tree=True),
    ContentType("products", Product, "产品",
                i18n_fields=[("name", "text"), ("body", "rich")],
                plain_fields=[("slug", "text"), ("category_id", "select:categories"),
                              ("sort", "number"), ("image", "image"), ("hero_image", "image"),
                              ("gallery", "text")],
                reindex=True),
    # posts/jobs/downloads 在 Task 15 加入此表
]}
```

通用路由(单文件实现,key 作为路径参数):

```python
@router.get("/{key}")            # 列表(树形类型按树缩进渲染)
@router.get("/{key}/new")        # 空表单
@router.post("/{key}/new")       # 创建 → 303 列表
@router.get("/{key}/{item_id}")  # 编辑表单
@router.post("/{key}/{item_id}") # 更新 → 303 列表
@router.post("/{key}/{item_id}/delete")
```

表单写回逻辑 `apply_form(obj, ct, form)`:遍历 `i18n_fields × LANGS` 与 `plain_fields`,check→bool,number→int,parent_id/category_id 空串→None;slug 必填且查重(冲突返回表单页带错误)。保存后 `if ct.reindex: rebuild_index(...)`。树形删除时子节点 `parent_id` 置 None。

`_i18n_tabs.html`:宏 `i18n_tabs(ct, obj)` — 四个 Tab 按钮(中/英/德/日)+ 每语言一组输入;`rich` 控件渲染 Quill 容器 + 隐藏 textarea,提交前 JS 同步 HTML;Quill 图片按钮走 `/admin/media/upload`。
`list.html`:表格(标题/slug/排序/操作),树形递归缩进,htmx 删除确认。

- [ ] **Step 4: 跑测试通过,commit** `feat: 后台通用 CRUD(页面/分类/产品)`

---

### Task 15: 后台内容 CRUD — 新闻/招聘/下载

**Files:** Modify: `app/routes/admin/content.py`, `tests/test_admin_crud.py`

- [ ] **Step 1: 写失败测试**:

```python
def test_post_job_download_crud(logged_client, db):
    logged_client.post("/admin/posts/new", data={
        "slug": "n1", "title_zh": "新闻一", "status": "published",
        "publish_at": "2026-06-10T08:00"})
    assert db.query(Post).filter_by(slug="n1", status="published").count() == 1
    logged_client.post("/admin/jobs/new", data={"title_zh": "工程师", "category": "social",
                                                "status": "open", "sort": "0"})
    assert db.query(Job).count() == 1
    logged_client.post("/admin/downloads/new", data={"title_zh": "手册", "file_path": "a.pdf",
                                                     "sort": "0", "file_size": "0"})
    assert db.query(Download).count() == 1
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现** 向 `CONTENT_TYPES` 追加三项:

```python
ContentType("posts", Post, "新闻",
            i18n_fields=[("title", "text"), ("excerpt", "textarea"), ("body", "rich")],
            plain_fields=[("slug", "text"), ("cover", "image"),
                          ("status", "select:status"), ("publish_at", "datetime")],
            order_by="-publish_at", reindex=True),
ContentType("jobs", Job, "招聘",
            i18n_fields=[("title", "text"), ("body", "rich")],
            plain_fields=[("category", "select:job_category"), ("status", "select:job_status"),
                          ("sort", "number")], has_seo=False),
ContentType("downloads", Download, "下载",
            i18n_fields=[("title", "text"), ("category", "text")],
            plain_fields=[("file_path", "file"), ("file_size", "number"), ("sort", "number")],
            has_seo=False),
```

引擎需要的增量:`datetime` 控件解析 `%Y-%m-%dT%H:%M`;`select:status` 等枚举选项字典;`file` 控件 = 媒体库选择器(弹窗选已上传文件,回填路径与大小);`order_by` 支持 `-` 前缀降序;Job/Download 无 slug,引擎跳过 slug 校验(`hasattr(model, "slug")` 判断)。

- [ ] **Step 4: 跑测试通过,commit** `feat: 后台新闻/招聘/下载管理`

---

### Task 16: 后台询盘/订阅/站点设置

**Files:** Create: `app/routes/admin/inquiries.py`, `site_settings.py`, `app/templates/admin/inquiries.html`, `subscribers.html`, `settings.html`; Modify: `tests/test_admin_crud.py`

- [ ] **Step 1: 写失败测试**:

```python
def test_inquiries_list_read_export(logged_client, db):
    db.add(Inquiry(name="客户A", email="a@x.com", message="询价")); db.commit()
    iid = db.query(Inquiry).one().id
    assert "客户A" in logged_client.get("/admin/inquiries").text
    logged_client.post(f"/admin/inquiries/{iid}/read")
    db.expire_all()
    assert db.get(Inquiry, iid).is_read is True
    csv = logged_client.get("/admin/inquiries/export.csv")
    assert "客户A" in csv.text and "text/csv" in csv.headers["content-type"]

def test_subscribers_export(logged_client, db):
    db.add(Subscriber(email="s@x.com", first_name="A")); db.commit()
    assert "s@x.com" in logged_client.get("/admin/subscribers/export.csv").text

def test_settings_save(logged_client, db):
    logged_client.post("/admin/settings", data={"site_name": "我的公司", "phone": "+86 100",
                                                "analytics_code": "<script>GA</script>"})
    from app.models import Setting
    assert db.get(Setting, "site_name").value == "我的公司"
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现**
- inquiries.py:列表(未读加粗,htmx 标记已读 `POST /{id}/read`)、`GET export.csv`(`csv` 模块写 StringIO,`Response(media_type="text/csv")`,UTF-8 BOM 让 Excel 正常显示中文);subscribers 同文件:列表 + export.csv。
- site_settings.py:固定键清单分组表单(基本信息: site_name/phone/email/address/copyright;首页: home_hero_video/home_hero_image;社交: social_linkedin/social_instagram/social_xing;统计: analytics_code;SMTP: smtp_host/port/user/password/tls/from/inquiry_to),POST 全量 upsert 到 settings 表。
- 前台 base.html 页脚/统计代码从 `site` 读取(`analytics_code | safe` 输出在 `</body>` 前)。

- [ ] **Step 4: 跑测试通过,commit** `feat: 询盘/订阅管理与站点设置`

---

### Task 17: rollax 种子抓取脚本

**Files:** Create: `scripts/seed_from_rollax.py`

抓取目标(每语言一棵):rollax 语言前缀 `de=""`、`en="/en"`、`jp="/jp"`、`zh="/cn"`。**仅作开发占位数据,上线前必须替换素材(版权)。**

- [ ] **Step 1: 实现脚本**(无单测,跑通即验):

```python
"""抓取 rollax.com 公开页面灌入种子数据(开发占位用,上线前替换)。
用法: .venv/bin/python scripts/seed_from_rollax.py
可重复执行(按 slug upsert)。Cloudflare 拦截的页面自动用占位文本。
"""
import sys, time, json, re
sys.path.insert(0, ".")
import httpx
from bs4 import BeautifulSoup
from app.config import get_settings
from app.db import make_engine, make_session_factory, init_db
from app.models import Page, ProductCategory, Product, Post
from app.media import save_upload
from app.i18n import LANGS

BASE = "https://www.rollax.com"
LANG_PREFIX = {"zh": "/cn", "en": "/en", "de": "", "jp": "/jp"}
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"}
PLACEHOLDER = {"zh": "<p>内容整理中。</p>", "en": "<p>Content coming soon.</p>",
               "de": "<p>Inhalt folgt in Kürze.</p>", "jp": "<p>準備中です。</p>"}

# rollax 路径 → 本站结构映射
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

def fetch(client, lang, de_path):
    """同一逻辑页的各语言 URL:德语路径在其它语言下相同(TYPO3 同构路径),失败回 None"""
    url = BASE + LANG_PREFIX[lang] + de_path
    try:
        r = client.get(url, timeout=20)
        if r.status_code != 200:
            return None
        return BeautifulSoup(r.text, "html.parser")
    except httpx.HTTPError:
        return None

def extract(soup):
    """返回 (title, html_body, hero_img_url, first_content_img)"""
    if soup is None:
        return None
    main = soup.find("main") or soup.find("div", id="content") or soup.body
    h1 = main.find("h1")
    title = h1.get_text(strip=True) if h1 else ""
    for tag in main.find_all(["script", "style", "form", "nav"]):
        tag.decompose()
    body = "".join(str(p) for p in main.find_all(["p", "h2", "h3", "ul", "blockquote"]))
    imgs = [img.get("src") or img.get("data-src") for img in main.find_all("img")]
    imgs = [i for i in imgs if i and not i.endswith(".svg")]
    return title, body, (imgs[0] if imgs else ""), imgs

def download_image(client, db_uploads, src):
    if not src:
        return ""
    url = src if src.startswith("http") else BASE + src
    try:
        r = client.get(url, timeout=30)
        if r.status_code != 200 or len(r.content) < 1000:
            return ""
        rel, *_ = save_upload(db_uploads, url.split("/")[-1].split("?")[0], r.content)
        return "/uploads/" + rel
    except (httpx.HTTPError, ValueError):
        return ""

def upsert(db, model, slug, **fields):
    obj = db.query(model).filter_by(slug=slug).first()
    if not obj:
        obj = model(slug=slug)
        db.add(obj)
    for k, v in fields.items():
        if v:
            setattr(obj, k, v)
    db.flush()
    return obj

def main():
    settings = get_settings()
    engine = make_engine(settings.db_path)
    init_db(engine)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    client = httpx.Client(headers=UA, follow_redirects=True)
    Session = make_session_factory(engine)
    with Session() as db:
        slug_to_id = {}
        for de_path, slug, parent_slug in CATEGORY_MAP:
            fields = {}
            for lang in LANGS:
                data = extract(fetch(client, lang, de_path))
                title, body = (data[0], data[1]) if data else ("", PLACEHOLDER[lang])
                fields[f"name_{lang}"] = title
                fields[f"intro_{lang}"] = body or PLACEHOLDER[lang]
                if lang == "de" and data:
                    fields["hero_image"] = download_image(client, settings.uploads_dir, data[2])
                    fields["card_image"] = fields["hero_image"]
                time.sleep(0.4)
            fields["parent_id"] = slug_to_id.get(parent_slug)
            cat = upsert(db, ProductCategory, slug, **fields)
            slug_to_id[slug] = cat.id
            print("分类:", slug, "✓")
        page_ids = {}
        for de_path, slug, parent_slug in PAGE_MAP:
            fields = {}
            for lang in LANGS:
                data = extract(fetch(client, lang, de_path))
                fields[f"title_{lang}"] = data[0] if data else ""
                fields[f"body_{lang}"] = (data[1] if data else "") or PLACEHOLDER[lang]
                time.sleep(0.4)
            fields["parent_id"] = page_ids.get(parent_slug)
            pg = upsert(db, Page, slug, **fields)
            page_ids[slug] = pg.id
            print("页面:", slug, "✓")
        # 首页介绍块
        data = extract(fetch(client, "zh", "/"))
        upsert(db, Page, "home-intro", nav_show=False,
               **{f"body_{l}": (extract(fetch(client, l, "/")) or [None, PLACEHOLDER[l]])[1] for l in LANGS})
        # 新闻列表(只抓第一页标题做示例数据)
        soup = fetch(client, "de", "/aktuelles/")
        if soup:
            for i, h in enumerate(soup.select("h3")[:6]):
                title = h.get_text(strip=True)
                if title:
                    upsert(db, Post, f"news-{i+1}", status="published",
                           title_zh=title, title_de=title, body_zh=f"<p>{title}</p>")
        db.commit()
        from app.search import rebuild_index
        rebuild_index(engine, db)
    print("种子数据完成")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行验证** `.venv/bin/python scripts/seed_from_rollax.py`,然后 `uvicorn app.main:app` 人工浏览首页/产品/公司页确认有内容(Cloudflare 拦截时应看到占位文本而非报错)。
- [ ] **Step 3: commit** `feat: rollax 种子抓取脚本`

---

### Task 18: 首页完整化与视觉还原打磨

**Files:** Modify: `app/static/css/site.css`, `app/templates/front/*.html`, `app/static/js/site.js`

- [ ] **Step 1:** 对照设计文档与 rollax 截图逐块核对并补全 CSS:
  - 顶栏:深蓝 `--blue-900`,白字小号导航,右侧电话/搜索/四个语言切换(当前语言高亮);
  - 产品栏:白底,LOGO 左侧,根分类全大写字母间距,hover 下划线;
  - Hero:全屏(70vh)图/视频,中央播放按钮;内页 Hero 高 320px 深色叠加;
  - 卡片墙:3 列错落(CSS grid + 不同 row span),卡片白底,标题居中加蓝色短下划线,hover 阴影;
  - Newsletter 条:深蓝底白字,横向表单圆角输入框;
  - 页脚:三栏(联系/社交圆形图标/世界地图占位 SVG)+ 底部版权条与法务链接;
  - 按钮:深蓝底白字 + 右侧深色方块箭头(rollax 标志性按钮);
  - 移动端:≤900px 汉堡菜单(site.js 切换),卡片单列。
- [ ] **Step 2:** `uvicorn app.main:app --reload` 起本地,浏览器逐页(首页/分类/产品/新闻/招聘/下载/联系/搜索,中英两语言)与 rollax 截图对比调整。
- [ ] **Step 3:** 全量测试回归 `python -m pytest tests/ -q`,commit `feat: 视觉还原与响应式打磨`

---

### Task 19: Docker 部署与文档

**Files:** Create: `deploy/Dockerfile`, `deploy/docker-compose.yml`, `deploy/nginx.conf`, `scripts/backup.sh`, `README.md`

- [ ] **Step 1: 实现**

`deploy/Dockerfile`:
```dockerfile
FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
COPY scripts/ scripts/
ENV DB_PATH=/srv/data/site.db UPLOADS_DIR=/srv/uploads
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

`deploy/docker-compose.yml`:
```yaml
services:
  app:
    build: { context: .., dockerfile: deploy/Dockerfile }
    restart: unless-stopped
    environment:
      - SECRET_KEY=${SECRET_KEY:?请在 .env 设置}
      - BASE_URL=${BASE_URL:-http://localhost:8080}
    volumes: [ "../data:/srv/data", "../uploads:/srv/uploads" ]
  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports: [ "8080:80" ]
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ../uploads:/srv/uploads:ro
      - ../app/static:/srv/static:ro
    depends_on: [ app ]
```

`deploy/nginx.conf`:
```nginx
server {
    listen 80;
    client_max_body_size 50m;
    location /static/  { alias /srv/static/;  expires 30d; }
    location /uploads/ { alias /srv/uploads/; expires 30d; }
    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

`scripts/backup.sh`:
```bash
#!/usr/bin/env bash
# 每日备份 SQLite 与 uploads;crontab: 0 3 * * * /srv/rollax/scripts/backup.sh
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
stamp=$(date +%Y%m%d)
sqlite3 data/site.db ".backup backups/site-$stamp.db"
tar czf "backups/uploads-$stamp.tar.gz" uploads/
ls -t backups/site-*.db | tail -n +15 | xargs -r rm   # 保留 14 天
ls -t backups/uploads-*.tar.gz | tail -n +15 | xargs -r rm
```

`README.md`:本地开发(venv、create_admin、seed、uvicorn)、测试、部署(VPS 装 docker → `.env` 写 SECRET_KEY/BASE_URL → `docker compose -f deploy/docker-compose.yml up -d --build` → 容器内跑 create_admin)、备份 cron、**版权提示:种子内容来自 rollax.com,上线前必须全部替换**。

- [ ] **Step 2: 验证** `docker compose -f deploy/docker-compose.yml up -d --build`,curl `http://localhost:8080/healthz` 返回 `{"ok":true}`,首页 200。
- [ ] **Step 3: commit** `chore: Docker 部署与备份脚本`

---

## 自检记录

- **规格覆盖**:四语言路由(T3)、信息架构全部板块(T5-T9)、搜索(T10)、SEO(T11)、后台全功能(T12-T16)、种子抓取(T17)、视觉还原(T18)、部署备份(T19)——设计文档第 3-9 节全部有对应任务。
- **类型一致性**:`pick/t/lang_url` 签名全计划一致;`ContentType` 字段在 T14 定义、T15 复用;`save_upload` 返回四元组在 T13/T17 一致;`rebuild_index(engine, db)` 在 T10/T14/T17 一致。
- **执行注意**:Task 4 的 `render()` 是后续所有前台任务的共享入口;Task 14 的通用引擎决定 T15 的工作量,先把引擎做对。
