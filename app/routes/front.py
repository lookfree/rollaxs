from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from app.deps import get_db
from app.models import Page, Setting

router = APIRouter()


def render(request: Request, name: str, ctx: dict, db: Session = None, status_code: int = 200):
    ctx.setdefault("lang", request.state.lang)
    ctx.setdefault("path", request.scope["path"])
    # Inject site settings dict
    if db is not None and "site" not in ctx:
        ctx["site"] = {row.key: row.value for row in db.query(Setting).all()}
    elif "site" not in ctx:
        ctx["site"] = {}
    # Inject nav_pages: root pages with nav_show=True ordered by sort
    if db is not None and "nav_pages" not in ctx:
        roots = db.query(Page).filter_by(parent_id=None, nav_show=True).order_by(Page.sort).all()
        # attach children to each root
        for root in roots:
            root._children = db.query(Page).filter_by(parent_id=root.id).order_by(Page.sort).all()
        ctx["nav_pages"] = roots
    elif "nav_pages" not in ctx:
        ctx["nav_pages"] = []
    return request.app.state.templates.TemplateResponse(request, name, ctx, status_code=status_code)


def build_page_crumbs(db: Session, node: Page) -> list:
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
        result.append((page.title_zh or page.slug, url))
    return result


@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    return render(request, "front/home.html", {}, db=db)


@router.get("/{path:path}/")
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
    if node is None:
        raise HTTPException(404)
    crumbs = build_page_crumbs(db, node)
    # Get children for display
    children = db.query(Page).filter_by(parent_id=node.id).order_by(Page.sort).all()
    return render(request, "front/page.html", {"page": node, "crumbs": crumbs, "children": children}, db=db)
