from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from app.deps import get_db
from app.i18n import pick
from app.models import Page, Setting

router = APIRouter()
# 页面树兜底路由单独一个 router,由 main.py 在 router 之后挂载,
# 保证后续任务往 router 追加的具体路由永远优先于 catch-all。
pages_router = APIRouter()


def render(request: Request, name: str, ctx: dict, db: Session, status_code: int = 200):
    ctx.setdefault("lang", request.state.lang)
    ctx.setdefault("path", request.scope["path"])
    if "site" not in ctx:
        ctx["site"] = {row.key: row.value for row in db.query(Setting).all()}
    if "nav_pages" not in ctx:
        roots = db.query(Page).filter_by(parent_id=None, nav_show=True).order_by(Page.sort).all()
        for root in roots:
            root._children = db.query(Page).filter_by(parent_id=root.id).order_by(Page.sort).all()
        ctx["nav_pages"] = roots
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


@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    return render(request, "front/home.html", {}, db=db)


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
