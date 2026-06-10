from fastapi import FastAPI

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

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app

app = create_app()
