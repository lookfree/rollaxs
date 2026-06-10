from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Base(DeclarativeBase):
    pass

def make_engine(db_path):
    from pathlib import Path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    @event.listens_for(engine, "connect")
    def _pragma(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()
    return engine

def make_session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)

def init_db(engine):
    from app import models  # noqa: F401 注册所有模型
    Base.metadata.create_all(engine)
    from app.search import create_fts  # Task 10 提供;在此之前先建占位函数
    create_fts(engine)
