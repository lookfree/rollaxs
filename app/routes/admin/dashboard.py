from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from app.deps import get_db, require_admin
from app.models import Page, Product, Post, Job, Download, Inquiry, Subscriber, Media

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    stats = {
        "pages": db.query(Page).count(),
        "products": db.query(Product).count(),
        "posts": db.query(Post).count(),
        "jobs": db.query(Job).count(),
        "downloads": db.query(Download).count(),
        "inquiries": db.query(Inquiry).count(),
        "subscribers": db.query(Subscriber).count(),
        "media": db.query(Media).count(),
    }
    recent_inquiries = (
        db.query(Inquiry).order_by(Inquiry.created_at.desc()).limit(5).all()
    )
    return request.app.state.templates.TemplateResponse(
        request, "admin/dashboard.html",
        {"stats": stats, "recent_inquiries": recent_inquiries}
    )
