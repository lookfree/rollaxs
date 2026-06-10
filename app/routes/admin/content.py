"""后台通用内容 CRUD 引擎:一套路由 + 每种内容一份字段描述(ContentType)。"""
from dataclasses import dataclass, field
from datetime import datetime

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.deps import get_db, require_admin
from app.i18n import LANGS
from app.models import Page, ProductCategory, Product
from app.search import rebuild_index

router = APIRouter(dependencies=[Depends(require_admin)])

SEO_FIELDS = ["seo_title", "seo_desc", "seo_keywords"]


@dataclass
class ContentType:
    key: str                  # url 段,如 "pages"
    model: type
    label: str                # 菜单名
    i18n_fields: list = field(default_factory=list)   # [(字段名, 控件), ...] 控件: text|rich|textarea
    plain_fields: list = field(default_factory=list)  # 非多语言字段 [(名, 控件), ...] 控件: text|number|check|image|file|select:xxx|datetime
    has_seo: bool = True
    tree: bool = False        # 树形(pages/categories)
    order_by: str = "sort"
    reindex: bool = False     # 保存后重建搜索索引


CONTENT_TYPES = {ct.key: ct for ct in [
    ContentType("pages", Page, "页面",
                i18n_fields=[("title", "text"), ("body", "rich")],
                plain_fields=[("slug", "text"), ("parent_id", "select:pages"),
                              ("sort", "number"), ("nav_show", "check"), ("hero_image", "image")],
                tree=True, reindex=True),
    ContentType("categories", ProductCategory, "产品分类",
                i18n_fields=[("name", "text"), ("intro", "rich")],
                plain_fields=[("slug", "text"), ("parent_id", "select:categories"),
                              ("sort", "number"), ("card_image", "image"), ("hero_image", "image")],
                tree=True),
    ContentType("products", Product, "产品",
                i18n_fields=[("name", "text"), ("body", "rich")],
                plain_fields=[("slug", "text"), ("category_id", "select:categories"),
                              ("sort", "number"), ("image", "image"), ("hero_image", "image"),
                              ("gallery", "text")],
                reindex=True),
    # posts/jobs/downloads 在 Task 15 加入此表
]}

# select:xxx 枚举选项(非内容引用)
ENUM_OPTIONS = {
    "status": [("draft", "草稿"), ("published", "已发布")],
    "job_category": [("social", "社会招聘"), ("student", "校园招聘"), ("training", "实习培训")],
    "job_status": [("open", "开放"), ("closed", "关闭")],
}

NULLABLE_FK_EMPTY = ("parent_id", "category_id")  # 空串 → None


def get_ct(key: str) -> ContentType:
    ct = CONTENT_TYPES.get(key)
    if ct is None:
        raise HTTPException(status_code=404)
    return ct


def _ordered_query(ct: ContentType, db: Session):
    ob = ct.order_by
    col = getattr(ct.model, ob.lstrip("-"))
    return db.query(ct.model).order_by(col.desc() if ob.startswith("-") else col.asc())


def item_label(ct: ContentType, item) -> str:
    """列表/下拉显示用标题:第一个 i18n 字段,zh 缺省回退其他语言。"""
    fname = ct.i18n_fields[0][0]
    for lang in LANGS:
        val = getattr(item, f"{fname}_{lang}", "")
        if val:
            return val
    return getattr(item, "slug", "") or f"#{item.id}"


def tree_rows(ct: ContentType, items):
    """树形类型按父子缩进展开为 [(item, depth)];非树形 depth=0。"""
    if not ct.tree:
        return [(it, 0) for it in items]
    children: dict = {}
    for it in items:
        children.setdefault(it.parent_id, []).append(it)
    rows = []

    def walk(pid, depth):
        for it in children.get(pid, []):
            rows.append((it, depth))
            walk(it.id, depth + 1)

    walk(None, 0)
    # 防御:父节点丢失的孤儿也要显示
    seen = {id(it) for it, _ in rows}
    rows.extend((it, 0) for it in items if id(it) not in seen)
    return rows


def build_options(ct: ContentType, db: Session, current_id=None):
    """为 select:xxx 控件准备选项 {字段名: [(value, label), ...]}。"""
    options = {}
    for fname, widget in ct.plain_fields:
        if not widget.startswith("select:"):
            continue
        target = widget.split(":", 1)[1]
        if target in CONTENT_TYPES:
            ref = CONTENT_TYPES[target]
            items = _ordered_query(ref, db).all()
            opts = []
            for it, depth in tree_rows(ref, items):
                if ref.key == ct.key and current_id is not None and it.id == current_id:
                    continue  # 树形不能选自己作父级
                opts.append((str(it.id), "　" * depth + item_label(ref, it)))
            options[fname] = opts
        else:
            options[fname] = ENUM_OPTIONS.get(target, [])
    return options


def slug_error(ct: ContentType, form, db: Session, exclude_id=None):
    """slug 必填且唯一(仅对有 slug 字段的模型);返回错误信息或 None。"""
    if not hasattr(ct.model, "slug"):
        return None
    slug = (form.get("slug") or "").strip()
    if not slug:
        return "slug 必填"
    q = db.query(ct.model).filter(ct.model.slug == slug)
    if exclude_id is not None:
        q = q.filter(ct.model.id != exclude_id)
    if db.query(q.exists()).scalar():
        return f"slug「{slug}」已存在"
    return None


def apply_form(obj, ct: ContentType, form):
    """把表单值写回模型实例。"""
    i18n_names = [f for f, _ in ct.i18n_fields]
    if ct.has_seo:
        i18n_names += SEO_FIELDS
    for fname in i18n_names:
        for lang in LANGS:
            name = f"{fname}_{lang}"
            if name in form:
                setattr(obj, name, form.get(name) or "")

    for fname, widget in ct.plain_fields:
        raw = form.get(fname)
        if widget == "check":
            setattr(obj, fname, fname in form and raw not in ("", "0", "false"))
            continue
        if fname not in form:
            continue
        raw = (raw or "").strip()
        if widget == "number":
            setattr(obj, fname, int(raw) if raw else 0)
        elif widget == "datetime":
            if raw:
                setattr(obj, fname, datetime.strptime(raw, "%Y-%m-%dT%H:%M"))
        elif widget.startswith("select:") and fname in NULLABLE_FK_EMPTY:
            setattr(obj, fname, int(raw) if raw else None)
        elif fname == "slug":
            setattr(obj, fname, raw)
        else:
            setattr(obj, fname, form.get(fname) or "")


def _render_form(request: Request, ct: ContentType, obj, db: Session, error=None, status_code=200):
    return request.app.state.templates.TemplateResponse(
        request, "admin/form.html",
        {"ct": ct, "obj": obj,
         "options": build_options(ct, db, current_id=getattr(obj, "id", None)),
         "error": error},
        status_code=status_code,
    )


def _after_save(request: Request, ct: ContentType, db: Session):
    if ct.reindex:
        rebuild_index(request.app.state.engine, db)
    return RedirectResponse(f"/admin/{ct.key}", status_code=303)


@router.get("/{key}")
def list_items(key: str, request: Request, db: Session = Depends(get_db)):
    ct = get_ct(key)
    rows = tree_rows(ct, _ordered_query(ct, db).all())
    return request.app.state.templates.TemplateResponse(
        request, "admin/list.html",
        {"ct": ct, "rows": rows, "item_label": item_label,
         "has_slug": hasattr(ct.model, "slug")},
    )


@router.get("/{key}/new")
def new_form(key: str, request: Request, db: Session = Depends(get_db)):
    ct = get_ct(key)
    return _render_form(request, ct, None, db)


@router.post("/{key}/new")
async def create_item(key: str, request: Request, db: Session = Depends(get_db)):
    ct = get_ct(key)
    form = await request.form()
    err = slug_error(ct, form, db)
    if err:
        obj = ct.model()           # 不入库,仅用于回显
        apply_form(obj, ct, form)
        return _render_form(request, ct, obj, db, error=err)
    obj = ct.model()
    apply_form(obj, ct, form)
    db.add(obj)
    db.commit()
    return _after_save(request, ct, db)


@router.get("/{key}/{item_id}")
def edit_form(key: str, item_id: int, request: Request, db: Session = Depends(get_db)):
    ct = get_ct(key)
    obj = db.get(ct.model, item_id)
    if obj is None:
        raise HTTPException(status_code=404)
    return _render_form(request, ct, obj, db)


@router.post("/{key}/{item_id}")
async def update_item(key: str, item_id: int, request: Request, db: Session = Depends(get_db)):
    ct = get_ct(key)
    obj = db.get(ct.model, item_id)
    if obj is None:
        raise HTTPException(status_code=404)
    form = await request.form()
    err = slug_error(ct, form, db, exclude_id=item_id)
    if err:
        return _render_form(request, ct, obj, db, error=err)
    apply_form(obj, ct, form)
    db.commit()
    return _after_save(request, ct, db)


@router.post("/{key}/{item_id}/delete")
def delete_item(key: str, item_id: int, request: Request, db: Session = Depends(get_db)):
    ct = get_ct(key)
    obj = db.get(ct.model, item_id)
    if obj is None:
        raise HTTPException(status_code=404)
    if ct.tree:  # 子节点提升为根
        db.query(ct.model).filter(ct.model.parent_id == item_id).update({"parent_id": None})
    db.delete(obj)
    db.commit()
    return _after_save(request, ct, db)
