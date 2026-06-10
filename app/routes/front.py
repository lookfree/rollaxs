import re
from fastapi import APIRouter, Request, Depends, HTTPException, Query, Form, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
from app.deps import get_db
from app.i18n import pick
from app.models import Page, Setting, ProductCategory, Product, Post, Job, Download, Inquiry, Subscriber, utcnow

router = APIRouter()
# 页面树兜底路由单独一个 router,由 main.py 在 router 之后挂载,
# 保证后续任务往 router 追加的具体路由永远优先于 catch-all。
pages_router = APIRouter()


def render(request: Request, name: str, ctx: dict, db: Session, status_code: int = 200):
    lang = getattr(request.state, "lang", "zh")
    logical_path = request.scope["path"]
    ctx.setdefault("lang", lang)
    ctx.setdefault("path", logical_path)
    if "site" not in ctx:
        ctx["site"] = {row.key: row.value for row in db.query(Setting).all()}
    if "nav_pages" not in ctx:
        roots = db.query(Page).filter_by(parent_id=None, nav_show=True).order_by(Page.sort).all()
        for root in roots:
            root._children = db.query(Page).filter_by(parent_id=root.id).order_by(Page.sort).all()
        ctx["nav_pages"] = roots
    if "root_categories" not in ctx:
        ctx["root_categories"] = (
            db.query(ProductCategory)
            .filter_by(parent_id=None)
            .order_by(ProductCategory.sort)
            .all()
        )
    # SEO context
    if "alternates" not in ctx:
        from app.seo import alternates as _alternates, canonical_url as _canonical_url
        base_url = request.app.state.settings.base_url
        ctx["alternates"] = _alternates(base_url, logical_path)
        ctx["canonical"] = _canonical_url(base_url, lang, logical_path)
    # breadcrumb_jsonld helper available in templates
    if "breadcrumb_jsonld" not in ctx:
        from app.seo import breadcrumb_jsonld as _bj
        base_url = request.app.state.settings.base_url
        ctx["breadcrumb_jsonld"] = lambda crumbs: _bj(base_url, lang, crumbs)
    return request.app.state.templates.TemplateResponse(request, name, ctx, status_code=status_code)


def build_page_crumbs(db: Session, node: Page, lang: str) -> list:
    """Walk parent_id chain upward; return list of (title, url) tuples top-down."""
    crumbs = []
    current = node
    while current is not None:
        crumbs.append(current)
        if current.parent_id is None:
            break
        current = db.query(Page).filter_by(id=current.parent_id).first()
    crumbs.reverse()
    # Build URL for each crumb by constructing slug path
    result = []
    path_parts = []
    for page in crumbs:
        path_parts.append(page.slug)
        url = "/" + "/".join(path_parts) + "/"
        result.append((pick(page, "title", lang) or page.slug, url))
    return result


# ---------------------------------------------------------------------------
# Product helpers
# ---------------------------------------------------------------------------

def category_tree(db: Session) -> dict:
    """Return {parent_id: [ProductCategory, ...]} for the full tree."""
    cats = db.query(ProductCategory).order_by(ProductCategory.sort).all()
    tree: dict = {}
    for cat in cats:
        tree.setdefault(cat.parent_id, []).append(cat)
    return tree


def cat_url_path(db: Session, cat: ProductCategory) -> str:
    """Return the canonical URL path for a category, e.g. /products/new-mobility/nvh-bearings/"""
    parts = []
    current = cat
    while current is not None:
        parts.append(current.slug)
        if current.parent_id is None:
            break
        current = db.query(ProductCategory).filter_by(id=current.parent_id).first()
    parts.reverse()
    return "/products/" + "/".join(parts) + "/"


def cat_url_by_id(db: Session, category_id: int) -> str:
    """Return the canonical URL path for a category by id. Used by Task 10 search."""
    cat = db.query(ProductCategory).filter_by(id=category_id).first()
    if cat is None:
        return "/products/"
    return cat_url_path(db, cat)


def build_cat_crumbs(db: Session, cat: ProductCategory, lang: str) -> list:
    """Return list of (name, url) tuples from root down to cat."""
    crumbs = []
    current = cat
    while current is not None:
        crumbs.append(current)
        if current.parent_id is None:
            break
        current = db.query(ProductCategory).filter_by(id=current.parent_id).first()
    crumbs.reverse()
    result, base = [], "/products/"
    for c in crumbs:
        base = f"{base}{c.slug}/"
        result.append((pick(c, "name", lang) or c.slug, base))
    return result


def flatten_category_tree(db: Session) -> list:
    """侧边产品树:[(cat, url, depth), ...] 先序遍历,URL 已拼好祖先路径。"""
    tree = category_tree(db)
    out = []

    def walk(parent_id, base, depth):
        for c in tree.get(parent_id, []):
            url = f"{base}{c.slug}/"
            out.append((c, url, depth))
            walk(c.id, url, depth + 1)

    walk(None, "/products/", 0)
    return out


def page_url(db: Session, page: Page) -> str:
    """Build the canonical URL for a page by walking its parent chain."""
    parts = []
    current = page
    while current is not None:
        parts.append(current.slug)
        if current.parent_id is None:
            break
        current = db.query(Page).filter_by(id=current.parent_id).first()
    parts.reverse()
    return "/" + "/".join(parts) + "/"


def resolve_category_path(db: Session, path: str) -> ProductCategory:
    """Walk /products/{slug1}/{slug2}/... verifying parent chain. Raises 404 if invalid."""
    slugs = [s for s in path.split("/") if s]
    if not slugs:
        raise HTTPException(404)
    parent_id = None
    cat = None
    for slug in slugs:
        cat = db.query(ProductCategory).filter_by(slug=slug).first()
        if cat is None:
            raise HTTPException(404)
        if cat.parent_id != parent_id:
            raise HTTPException(404)
        parent_id = cat.id
    return cat


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    # Query optional home-intro page for intro section
    intro_page = db.query(Page).filter_by(slug="home-intro").first()
    return render(request, "front/home.html", {"intro_page": intro_page}, db=db)


# Product routes — registered BEFORE pages_router catch-all and also before
# /products/{path:path}/ so the .html suffix route wins.

@router.get("/products/")
def products_index(request: Request, db: Session = Depends(get_db)):
    roots = (
        db.query(ProductCategory)
        .filter_by(parent_id=None)
        .order_by(ProductCategory.sort)
        .all()
    )
    return render(
        request,
        "front/category.html",
        {"cat": None, "children": roots, "products": [], "crumbs": [], "cat_url": "/products/"},
        db=db,
    )


@router.get("/products/{path:path}.html")
def product_detail(path: str, request: Request, db: Session = Depends(get_db)):
    segments = path.split("/")
    if len(segments) < 2:
        # A product URL must have at least one category segment before the slug.
        raise HTTPException(404)
    prod_slug = segments[-1]
    cat_segments = segments[:-1]
    # Validate that the category path is correct (parent chain must match).
    resolved_cat = resolve_category_path(db, "/".join(cat_segments))
    prod = db.query(Product).filter_by(slug=prod_slug).first()
    if not prod:
        raise HTTPException(404)
    # Ensure the product actually belongs to the resolved category.
    if prod.category_id != resolved_cat.id:
        raise HTTPException(404)
    cat = resolved_cat
    lang = request.state.lang
    cat_url = "/products/" + "/".join(cat_segments) + "/"
    crumbs = build_cat_crumbs(db, cat, lang) + [
        (pick(prod, "name", lang) or prod.slug, cat_url + f"{prod.slug}.html")
    ]
    return render(
        request,
        "front/product.html",
        {"prod": prod, "cat": cat, "side_tree": flatten_category_tree(db), "crumbs": crumbs},
        db=db,
    )


@router.get("/products/{path:path}/")
def category_view(path: str, request: Request, db: Session = Depends(get_db)):
    cat = resolve_category_path(db, path)
    children = (
        db.query(ProductCategory)
        .filter_by(parent_id=cat.id)
        .order_by(ProductCategory.sort)
        .all()
    )
    products = (
        db.query(Product)
        .filter_by(category_id=cat.id)
        .order_by(Product.sort)
        .all()
    )
    lang = request.state.lang
    return render(
        request,
        "front/category.html",
        {
            "cat": cat,
            "children": children,
            "products": products,
            "crumbs": build_cat_crumbs(db, cat, lang),
            "cat_url": "/products/" + path.strip("/") + "/",
        },
        db=db,
    )


# ---------------------------------------------------------------------------
# News routes (Task 7)
# ---------------------------------------------------------------------------

PAGE_SIZE = 10


@router.get("/news/")
def news_list(request: Request, page: int = Query(default=1, ge=1), db: Session = Depends(get_db)):
    q = (
        db.query(Post)
        .filter(Post.status == "published", Post.publish_at <= utcnow())
        .order_by(Post.publish_at.desc())
    )
    total = q.count()
    posts = q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    pages = max(1, -(-total // PAGE_SIZE))
    return render(
        request,
        "front/post_list.html",
        {"posts": posts, "page": page, "pages": pages},
        db=db,
    )


@router.get("/news/{slug}.html")
def news_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    post = (
        db.query(Post)
        .filter(Post.slug == slug, Post.status == "published", Post.publish_at <= utcnow())
        .first()
    )
    if not post:
        raise HTTPException(404)
    return render(request, "front/post_detail.html", {"post": post}, db=db)


# ---------------------------------------------------------------------------
# Career & Downloads routes (Task 8)
# ---------------------------------------------------------------------------

@router.get("/career/")
def career_list(request: Request, db: Session = Depends(get_db)):
    jobs = (
        db.query(Job)
        .filter_by(status="open")
        .order_by(Job.sort, Job.created_at.desc())
        .all()
    )
    # Group by category: social | student | training
    groups: dict[str, list] = {"social": [], "student": [], "training": []}
    for job in jobs:
        groups.setdefault(job.category, []).append(job)
    return render(request, "front/jobs.html", {"groups": groups}, db=db)


@router.get("/career/{job_id}.html")
def career_detail(job_id: int, request: Request, db: Session = Depends(get_db)):
    job = db.query(Job).filter_by(id=job_id, status="open").first()
    if not job:
        raise HTTPException(404)
    return render(request, "front/job_detail.html", {"job": job}, db=db)


@router.get("/downloads/")
def downloads_list(request: Request, db: Session = Depends(get_db)):
    lang = request.state.lang
    items = db.query(Download).order_by(Download.sort, Download.id).all()
    # Group by translated category label
    groups: dict[str, list] = {}
    for item in items:
        cat_label = pick(item, "category", lang) or item.category_zh or "其他"
        groups.setdefault(cat_label, []).append(item)
    return render(request, "front/downloads.html", {"groups": groups}, db=db)


# ---------------------------------------------------------------------------
# SEO: sitemap.xml + robots.txt (Task 11)
# ---------------------------------------------------------------------------


@router.get("/sitemap.xml")
def sitemap(request: Request, db: Session = Depends(get_db)):
    from app.i18n import LANGS, lang_url
    from fastapi.responses import Response as PlainResp

    base_url = request.app.state.settings.base_url
    urls: list[dict] = []

    def add_url(logical_path: str, lastmod: str = ""):
        for lang in LANGS:
            entry = {"loc": base_url + lang_url(lang, logical_path)}
            if lastmod:
                entry["lastmod"] = lastmod
            urls.append(entry)

    # Static / well-known paths
    for path in ("/", "/news/", "/career/", "/downloads/", "/contact/", "/search/"):
        add_url(path)

    # Pages(一次查询建 id→page 映射,内存拼 URL,避免逐级查询)
    pages = db.query(Page).all()
    page_by_id = {p.id: p for p in pages}
    for pg in pages:
        parts, cur = [], pg
        while cur is not None:
            parts.append(cur.slug)
            cur = page_by_id.get(cur.parent_id) if cur.parent_id else None
        add_url("/" + "/".join(reversed(parts)) + "/")

    # Product categories + products(flatten 一次查询出全树 URL)
    cat_urls = {c.id: url for c, url, _ in flatten_category_tree(db)}
    for url in cat_urls.values():
        add_url(url)
    for prod in db.query(Product).all():
        add_url(cat_urls.get(prod.category_id, "/products/") + f"{prod.slug}.html")

    # Posts (published)
    for po in db.query(Post).filter_by(status="published").all():
        lastmod = po.publish_at.strftime("%Y-%m-%d") if po.publish_at else ""
        add_url(f"/news/{po.slug}.html", lastmod=lastmod)

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    from html import escape
    for entry in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{escape(entry['loc'])}</loc>")
        if entry.get("lastmod"):
            lines.append(f"    <lastmod>{entry['lastmod']}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return PlainResp("\n".join(lines), media_type="application/xml")


@router.get("/robots.txt")
def robots(request: Request):
    from fastapi.responses import Response as PlainResp

    base_url = request.app.state.settings.base_url
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin/\n"
        f"Sitemap: {base_url}/sitemap.xml\n"
    )
    return PlainResp(content, media_type="text/plain")


# ---------------------------------------------------------------------------
# Search (Task 10)
# ---------------------------------------------------------------------------


@router.get("/search/")
def search_view(request: Request, q: str = Query(default=""), db: Session = Depends(get_db)):
    hits = []
    if q.strip():
        from app.search import query_index
        hits = query_index(db, q.strip(), request.state.lang)
    return render(request, "front/search.html", {"q": q, "hits": hits}, db=db)


# ---------------------------------------------------------------------------
# Contact form (Task 9)
# ---------------------------------------------------------------------------


@router.get("/contact/")
def contact_get(request: Request, about: str = Query(default=""), db: Session = Depends(get_db)):
    msg = f"Re: {about}" if about else ""
    return render(
        request,
        "front/contact.html",
        {"success": False, "error": None, "form_data": {"message": msg}},
        db=db,
    )


@router.post("/contact/")
def contact_post(
    request: Request,
    name: str = Form(default=""),
    email: str = Form(default=""),
    company: str = Form(default=""),
    message: str = Form(default=""),
    website: str = Form(default=""),
    db: Session = Depends(get_db),
):
    # Honeypot check
    if website:
        return render(
            request,
            "front/contact.html",
            {"success": True, "error": None, "form_data": {}},
            db=db,
        )

    # Rate limit
    limiter = request.app.state.form_limiter
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.allow(client_ip):
        return Response(status_code=429, content="Too many requests")

    # Basic validation
    if not EMAIL_RE.match(email) or not message.strip():
        return render(
            request,
            "front/contact.html",
            {
                "success": False,
                "error": "请填写有效邮箱和留言",
                "form_data": {"name": name, "email": email, "company": company, "message": message},
            },
            db=db,
        )

    inq = Inquiry(
        name=name,
        email=email,
        company=company,
        message=message,
        source_path=request.scope.get("path", "/contact/"),
    )
    db.add(inq)
    db.commit()

    # SMTP 失败在 mailer.notify_inquiry 内部吞掉,这里不再包一层
    from app.mailer import notify_inquiry
    site = {row.key: row.value for row in db.query(Setting).all()}
    notify_inquiry(site, inq)

    return render(
        request,
        "front/contact.html",
        {"success": True, "error": None, "form_data": {}},
        db=db,
    )


# ---------------------------------------------------------------------------
# Newsletter subscription (Task 9)
# ---------------------------------------------------------------------------


@router.post("/newsletter/")
def newsletter_post(
    request: Request,
    email: str = Form(default=""),
    first_name: str = Form(default=""),
    last_name: str = Form(default=""),
    salutation: str = Form(default=""),
    website: str = Form(default=""),
    db: Session = Depends(get_db),
):
    from app.i18n import lang_url
    done = RedirectResponse(lang_url(request.state.lang, "/?subscribed=1"), status_code=303)
    # Honeypot
    if website:
        return done

    if email and EMAIL_RE.match(email):
        existing = db.query(Subscriber).filter_by(email=email).first()
        if not existing:
            db.add(Subscriber(
                email=email,
                first_name=first_name,
                last_name=last_name,
                salutation=salutation,
            ))
            db.commit()

    return done


# ---------------------------------------------------------------------------
# Pages catch-all (must stay in pages_router, mounted last by main.py)
# ---------------------------------------------------------------------------

@pages_router.get("/{path:path}/")
def page_view(path: str, request: Request, db: Session = Depends(get_db)):
    slugs = [s for s in path.split("/") if s]
    if not slugs:
        raise HTTPException(404)
    node = None
    parent = None
    for slug in slugs:
        node = db.query(Page).filter_by(slug=slug).first()
        if node is None:
            raise HTTPException(404)
        if parent is not None and node.parent_id != parent.id:
            raise HTTPException(404)
        parent = node
    crumbs = build_page_crumbs(db, node, request.state.lang)
    children = db.query(Page).filter_by(parent_id=node.id).order_by(Page.sort).all()
    return render(request, "front/page.html", {"page": node, "crumbs": crumbs, "children": children}, db=db)
