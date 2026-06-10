from fastapi import APIRouter, Request, Depends
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


@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    return render(request, "front/home.html", {}, db=db)
