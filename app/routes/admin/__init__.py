from fastapi import APIRouter
from app.routes.admin import auth, dashboard, media, content, inquiries, site_settings

admin_router = APIRouter(prefix="/admin")

# Auth routes are accessible without login
admin_router.include_router(auth.router)

# Dashboard and other routes require login (handled inside each router via dependencies)
admin_router.include_router(dashboard.router)
admin_router.include_router(media.router)
admin_router.include_router(inquiries.router)
admin_router.include_router(site_settings.router)
# 通用内容 CRUD 使用 /{key} 参数路由,必须最后注册,避免吞掉上面的具体路径
admin_router.include_router(content.router)
