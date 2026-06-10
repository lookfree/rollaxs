from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from app.deps import get_db
from app.models import AdminUser
from app.security import verify_password

router = APIRouter()


def _templates(request: Request):
    return request.app.state.templates


@router.get("/login")
def login_get(request: Request):
    return _templates(request).TemplateResponse(
        request, "admin/login.html", {"error": None}
    )


@router.post("/login")
async def login_post(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    username = form.get("username", "")
    password = form.get("password", "")

    limiter = request.app.state.login_limiter
    client_ip = request.client.host if request.client else "unknown"

    if not limiter.allow(client_ip):
        return HTMLResponse("Too Many Requests", status_code=429)

    user = db.query(AdminUser).filter_by(username=username).first()
    if not user or not verify_password(password, user.password_hash):
        return _templates(request).TemplateResponse(
            request, "admin/login.html",
            {"error": "用户名或密码错误"},
            status_code=200,
        )

    request.session["admin_id"] = user.id
    return RedirectResponse("/admin/", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=303)
