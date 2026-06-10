from fastapi import APIRouter
from app.routes.admin import auth, dashboard, media

admin_router = APIRouter(prefix="/admin")

# Auth routes are accessible without login
admin_router.include_router(auth.router)

# Dashboard and other routes require login (handled inside each router via dependencies)
admin_router.include_router(dashboard.router)
admin_router.include_router(media.router)
