import io
import pytest
from PIL import Image
from app.models import Media


def make_png(w=800, h=600):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "#0d2c6b").save(buf, "PNG")
    buf.seek(0)
    return buf


def test_upload_image(logged_client, db, app):
    r = logged_client.post("/admin/media/upload",
                           files={"file": ("test.png", make_png(), "image/png")})
    assert r.status_code == 200
    m = db.query(Media).one()
    assert m.kind == "image" and m.thumb_path and m.webp_path
    uploads = app.state.settings.uploads_dir
    assert (uploads / m.path).exists() and (uploads / m.webp_path).exists()


def test_upload_rejects_exe(logged_client):
    r = logged_client.post("/admin/media/upload",
                           files={"file": ("x.exe", io.BytesIO(b"MZ"), "application/x-msdownload")})
    assert r.status_code == 400
