"""用法: .venv/bin/python scripts/create_admin.py <用户名> <密码>"""
import sys
sys.path.insert(0, ".")
from app.config import get_settings
from app.db import make_engine, make_session_factory, init_db
from app.models import AdminUser
from app.security import hash_password

def main():
    username, password = sys.argv[1], sys.argv[2]
    s = get_settings()
    engine = make_engine(s.db_path)
    init_db(engine)
    with make_session_factory(engine)() as db:
        user = db.query(AdminUser).filter_by(username=username).first()
        if user:
            user.password_hash = hash_password(password)
        else:
            db.add(AdminUser(username=username, password_hash=hash_password(password)))
        db.commit()
    print(f"管理员 {username} 已就绪")

if __name__ == "__main__":
    main()
