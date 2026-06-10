"""站点设置:固定键清单分组表单,POST 全量 upsert 到 settings 表。"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.deps import get_db, require_admin
from app.models import Setting

router = APIRouter(dependencies=[Depends(require_admin)])

# (分组名, [(键, 标签, 控件), ...]) 控件: text|textarea|check|password
SETTING_GROUPS = [
    ("基本信息", [
        ("site_name", "网站名称", "text"),
        ("phone", "电话", "text"),
        ("email", "邮箱", "text"),
        ("address", "地址", "textarea"),
        ("copyright", "版权信息", "text"),
    ]),
    ("首页", [
        ("home_hero_video", "首页 Hero 视频", "text"),
        ("home_hero_image", "首页 Hero 图片", "text"),
    ]),
    ("社交", [
        ("social_linkedin", "LinkedIn", "text"),
        ("social_instagram", "Instagram", "text"),
        ("social_xing", "Xing", "text"),
    ]),
    ("统计", [
        ("analytics_code", "统计代码(输出在 </body> 前)", "textarea"),
    ]),
    ("SMTP 邮件", [
        ("smtp_host", "SMTP 主机", "text"),
        ("smtp_port", "SMTP 端口", "text"),
        ("smtp_user", "SMTP 用户", "text"),
        ("smtp_password", "SMTP 密码", "password"),
        ("smtp_tls", "启用 TLS", "check"),
        ("smtp_from", "发件人", "text"),
        ("inquiry_to", "询盘通知收件人", "text"),
    ]),
]

ALL_KEYS = [key for _, fields in SETTING_GROUPS for key, _, _ in fields]
CHECK_KEYS = {key for _, fields in SETTING_GROUPS for key, _, w in fields if w == "check"}


@router.get("/settings")
def settings_form(request: Request, db: Session = Depends(get_db)):
    values = {s.key: s.value for s in db.query(Setting).all()}
    return request.app.state.templates.TemplateResponse(
        request, "admin/settings.html",
        {"groups": SETTING_GROUPS, "values": values, "saved": request.query_params.get("saved")}
    )


@router.post("/settings")
async def settings_save(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    for key in ALL_KEYS:
        if key in CHECK_KEYS:
            value = "1" if form.get(key) else "0"
        elif key in form:
            value = form.get(key) or ""
        else:
            continue  # 未提交的键保持原值
        setting = db.get(Setting, key)
        if setting is None:
            db.add(Setting(key=key, value=value))
        else:
            setting.value = value
    db.commit()
    return RedirectResponse("/admin/settings?saved=1", status_code=303)
