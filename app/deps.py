from fastapi import Request


def get_db(request: Request):
    db = request.app.state.session_factory()
    try:
        yield db
    finally:
        db.close()


class RequiresLogin(Exception):
    pass


def require_admin(request: Request):
    if not request.session.get("admin_id"):
        raise RequiresLogin()
    return request.session["admin_id"]
