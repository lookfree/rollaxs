import os
from pathlib import Path

from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.deps import get_db, require_admin
from app.models import Media
from app.media import save_upload

router = APIRouter(dependencies=[Depends(require_admin)])

PAGE_SIZE = 48


@router.post("/media/upload")
async def upload_media(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    uploads_dir: Path = request.app.state.settings.uploads_dir
    data = await file.read()
    try:
        rel, kind, thumb_rel, webp_rel = save_upload(uploads_dir, file.filename or "upload", data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    media = Media(path=rel, kind=kind, thumb_path=thumb_rel, webp_path=webp_rel)
    db.add(media)
    db.commit()
    db.refresh(media)

    return {"url": "/uploads/" + rel, "id": media.id}


@router.get("/media")
def media_list(request: Request, page: int = 1, db: Session = Depends(get_db)):
    total = db.query(Media).count()
    items = (
        db.query(Media)
        .order_by(Media.created_at.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )
    pages = max(1, -(-total // PAGE_SIZE))
    return request.app.state.templates.TemplateResponse(
        request, "admin/media.html",
        {"items": items, "page": page, "pages": pages, "total": total}
    )


@router.delete("/media/{media_id}")
def delete_media(media_id: int, request: Request, db: Session = Depends(get_db)):
    media = db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Not found")

    uploads_dir: Path = request.app.state.settings.uploads_dir
    for rel_path in [media.path, media.thumb_path, media.webp_path]:
        if rel_path:
            try:
                (uploads_dir / rel_path).unlink(missing_ok=True)
            except Exception:
                pass

    db.delete(media)
    db.commit()
    return HTMLResponse("", status_code=200)
