import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    def __init__(self):
        self.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
        self.db_path = Path(os.environ.get("DB_PATH", BASE_DIR / "data" / "site.db"))
        self.uploads_dir = Path(os.environ.get("UPLOADS_DIR", BASE_DIR / "uploads"))
        self.base_url = os.environ.get("BASE_URL", "http://localhost:8000")
        self.session_https_only = os.environ.get("SESSION_HTTPS_ONLY", "0") == "1"

def get_settings():
    return Settings()
