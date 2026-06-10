from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from app.config import get_settings, BASE_DIR
from app.db import make_engine, make_session_factory, init_db
from app import i18n

NON_LANG_PREFIXES = ("/admin", "/static", "/uploads", "/healthz")


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

    @app.middleware("http")
    async def lang_middleware(request, call_next):
        path = request.scope["path"]
        lang = "zh"
        if not path.startswith(NON_LANG_PREFIXES):
            for code in ("en", "de", "jp"):
                if path == f"/{code}" or path.startswith(f"/{code}/"):
                    lang = code
                    request.scope["path"] = path[len(code) + 1:] or "/"
                    request.scope["raw_path"] = request.scope["path"].encode()
                    break
        request.state.lang = lang
        return await call_next(request)

    templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
    templates.env.globals.update(
        t=i18n.t,
        pick=i18n.pick,
        lang_url=i18n.lang_url,
        LANGS=i18n.LANGS,
        LANG_NAMES=i18n.LANG_NAMES,
    )
    app.state.templates = templates

    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
    app.mount("/uploads", StaticFiles(directory=str(settings.uploads_dir)), name="uploads")

    # Per-app rate limiters — live on app.state so each test app gets a fresh one
    from app.security import RateLimiter
    app.state.form_limiter = RateLimiter(5, 60)
    app.state.login_limiter = RateLimiter(10, 300)

    from app.deps import RequiresLogin
    from fastapi.responses import RedirectResponse as _Redirect

    @app.exception_handler(RequiresLogin)
    async def requires_login_handler(request: Request, exc: RequiresLogin):
        return _Redirect("/admin/login", status_code=303)

    from app.routes.front import router as front_router, pages_router
    from app.routes.admin import admin_router
    app.include_router(front_router)
    app.include_router(admin_router)   # admin BEFORE pages catch-all
    app.include_router(pages_router)  # 页面树 catch-all,必须最后挂载

    @app.exception_handler(404)
    async def not_found(request: Request, exc):
        lang = getattr(request.state, "lang", "zh")
        return templates.TemplateResponse(
            request, "front/404.html",
            {"lang": lang, "site": {}, "nav_pages": [], "path": request.scope.get("path", "/")},
            status_code=404,
        )

    @app.exception_handler(500)
    async def server_error(request: Request, exc):
        lang = getattr(request.state, "lang", "zh")
        return templates.TemplateResponse(
            request, "front/500.html",
            {"lang": lang, "site": {}, "nav_pages": [], "path": request.scope.get("path", "/")},
            status_code=500,
        )

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app


app = create_app()
