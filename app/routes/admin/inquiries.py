"""后台询盘与 Newsletter 订阅管理:列表 + 标记已读 + CSV 导出。"""
import csv
import io

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import Response, HTMLResponse
from sqlalchemy.orm import Session

from app.deps import get_db, require_admin
from app.models import Inquiry, Subscriber

router = APIRouter(dependencies=[Depends(require_admin)])


def _csv_response(filename: str, header: list, rows) -> Response:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    # UTF-8 BOM,让 Excel 正确识别中文
    return Response(
        content="\ufeff" + buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---- 询盘 ----

@router.get("/inquiries/export.csv")
def inquiries_export(db: Session = Depends(get_db)):
    items = db.query(Inquiry).order_by(Inquiry.created_at.desc()).all()
    rows = [(i.id, i.name, i.email, i.company, i.phone, i.message, i.source_path,
             "是" if i.is_read else "否", i.created_at.strftime("%Y-%m-%d %H:%M"))
            for i in items]
    return _csv_response("inquiries.csv",
                         ["ID", "姓名", "邮箱", "公司", "电话", "留言", "来源页面", "已读", "时间"],
                         rows)


@router.get("/inquiries")
def inquiries_list(request: Request, db: Session = Depends(get_db)):
    items = db.query(Inquiry).order_by(Inquiry.created_at.desc()).all()
    return request.app.state.templates.TemplateResponse(
        request, "admin/inquiries.html", {"items": items}
    )


@router.post("/inquiries/{inquiry_id}/read")
def inquiry_mark_read(inquiry_id: int, db: Session = Depends(get_db)):
    item = db.get(Inquiry, inquiry_id)
    if item is None:
        raise HTTPException(status_code=404)
    item.is_read = True
    db.commit()
    return HTMLResponse("已读")


# ---- 订阅 ----

@router.get("/subscribers/export.csv")
def subscribers_export(db: Session = Depends(get_db)):
    items = db.query(Subscriber).order_by(Subscriber.created_at.desc()).all()
    rows = [(s.id, s.salutation, s.first_name, s.last_name, s.email,
             s.created_at.strftime("%Y-%m-%d %H:%M"))
            for s in items]
    return _csv_response("subscribers.csv",
                         ["ID", "称谓", "名", "姓", "邮箱", "时间"],
                         rows)


@router.get("/subscribers")
def subscribers_list(request: Request, db: Session = Depends(get_db)):
    items = db.query(Subscriber).order_by(Subscriber.created_at.desc()).all()
    return request.app.state.templates.TemplateResponse(
        request, "admin/subscribers.html", {"items": items}
    )
