from fastapi import FastAPI

def create_app():
    app = FastAPI(docs_url=None, redoc_url=None)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app

app = create_app()
