import re
import time
from pathlib import Path
from PIL import Image

ALLOWED = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf", ".zip", ".mp4"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def save_upload(uploads_dir: Path, filename: str, data: bytes):
    """Save uploaded file, generate thumb and WebP for images.

    Returns (rel, kind, thumb_rel, webp_rel).
    Raises ValueError for disallowed extensions.
    """
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED:
        raise ValueError(f"不允许的文件类型: {ext}")

    stem = re.sub(r"[^a-zA-Z0-9_-]", "-", Path(filename).stem)[:60] or "file"
    sub = time.strftime("%Y/%m")
    rel = f"{sub}/{stem}-{int(time.time() * 1000) % 100000}{ext}"
    abs_path = uploads_dir / rel
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(data)

    kind = "image" if ext in IMAGE_EXT else "file"
    thumb_rel = webp_rel = ""

    if kind == "image" and ext != ".gif":
        img = Image.open(abs_path).convert("RGB")

        t = img.copy()
        t.thumbnail((400, 400))
        thumb_rel = rel.rsplit(ext, 1)[0] + ".thumb.jpg"
        t.save(uploads_dir / thumb_rel, "JPEG", quality=82)

        webp_rel = rel.rsplit(ext, 1)[0] + ".webp"
        img.save(uploads_dir / webp_rel, "WEBP", quality=82)

    return rel, kind, thumb_rel, webp_rel
