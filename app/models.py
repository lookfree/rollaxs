from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

S, T = String(500), Text  # 简写

class I18nSeo:
    """SEO 四语言字段 mixin"""
    seo_title_zh: Mapped[str] = mapped_column(S, default="")
    seo_title_en: Mapped[str] = mapped_column(S, default="")
    seo_title_de: Mapped[str] = mapped_column(S, default="")
    seo_title_jp: Mapped[str] = mapped_column(S, default="")
    seo_desc_zh: Mapped[str] = mapped_column(S, default="")
    seo_desc_en: Mapped[str] = mapped_column(S, default="")
    seo_desc_de: Mapped[str] = mapped_column(S, default="")
    seo_desc_jp: Mapped[str] = mapped_column(S, default="")
    seo_keywords_zh: Mapped[str] = mapped_column(S, default="")
    seo_keywords_en: Mapped[str] = mapped_column(S, default="")
    seo_keywords_de: Mapped[str] = mapped_column(S, default="")
    seo_keywords_jp: Mapped[str] = mapped_column(S, default="")

class Page(Base, I18nSeo):
    __tablename__ = "pages"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pages.id"), nullable=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    nav_show: Mapped[bool] = mapped_column(Boolean, default=True)
    hero_image: Mapped[str] = mapped_column(S, default="")
    title_zh: Mapped[str] = mapped_column(S, default="")
    title_en: Mapped[str] = mapped_column(S, default="")
    title_de: Mapped[str] = mapped_column(S, default="")
    title_jp: Mapped[str] = mapped_column(S, default="")
    body_zh: Mapped[str] = mapped_column(T, default="")
    body_en: Mapped[str] = mapped_column(T, default="")
    body_de: Mapped[str] = mapped_column(T, default="")
    body_jp: Mapped[str] = mapped_column(T, default="")

class ProductCategory(Base, I18nSeo):
    __tablename__ = "product_categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("product_categories.id"), nullable=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    card_image: Mapped[str] = mapped_column(S, default="")
    hero_image: Mapped[str] = mapped_column(S, default="")
    name_zh: Mapped[str] = mapped_column(S, default="")
    name_en: Mapped[str] = mapped_column(S, default="")
    name_de: Mapped[str] = mapped_column(S, default="")
    name_jp: Mapped[str] = mapped_column(S, default="")
    intro_zh: Mapped[str] = mapped_column(T, default="")
    intro_en: Mapped[str] = mapped_column(T, default="")
    intro_de: Mapped[str] = mapped_column(T, default="")
    intro_jp: Mapped[str] = mapped_column(T, default="")

class Product(Base, I18nSeo):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("product_categories.id"))
    sort: Mapped[int] = mapped_column(Integer, default=0)
    image: Mapped[str] = mapped_column(S, default="")
    gallery: Mapped[str] = mapped_column(T, default="[]")  # JSON 数组字符串
    hero_image: Mapped[str] = mapped_column(S, default="")
    name_zh: Mapped[str] = mapped_column(S, default="")
    name_en: Mapped[str] = mapped_column(S, default="")
    name_de: Mapped[str] = mapped_column(S, default="")
    name_jp: Mapped[str] = mapped_column(S, default="")
    body_zh: Mapped[str] = mapped_column(T, default="")
    body_en: Mapped[str] = mapped_column(T, default="")
    body_de: Mapped[str] = mapped_column(T, default="")
    body_jp: Mapped[str] = mapped_column(T, default="")

class Post(Base, I18nSeo):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    cover: Mapped[str] = mapped_column(S, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|published
    publish_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    title_zh: Mapped[str] = mapped_column(S, default="")
    title_en: Mapped[str] = mapped_column(S, default="")
    title_de: Mapped[str] = mapped_column(S, default="")
    title_jp: Mapped[str] = mapped_column(S, default="")
    excerpt_zh: Mapped[str] = mapped_column(T, default="")
    excerpt_en: Mapped[str] = mapped_column(T, default="")
    excerpt_de: Mapped[str] = mapped_column(T, default="")
    excerpt_jp: Mapped[str] = mapped_column(T, default="")
    body_zh: Mapped[str] = mapped_column(T, default="")
    body_en: Mapped[str] = mapped_column(T, default="")
    body_de: Mapped[str] = mapped_column(T, default="")
    body_jp: Mapped[str] = mapped_column(T, default="")

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(20), default="social")  # social|student|training
    status: Mapped[str] = mapped_column(String(20), default="open")  # open|closed
    sort: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    title_zh: Mapped[str] = mapped_column(S, default="")
    title_en: Mapped[str] = mapped_column(S, default="")
    title_de: Mapped[str] = mapped_column(S, default="")
    title_jp: Mapped[str] = mapped_column(S, default="")
    body_zh: Mapped[str] = mapped_column(T, default="")
    body_en: Mapped[str] = mapped_column(T, default="")
    body_de: Mapped[str] = mapped_column(T, default="")
    body_jp: Mapped[str] = mapped_column(T, default="")

class Download(Base):
    __tablename__ = "downloads"
    id: Mapped[int] = mapped_column(primary_key=True)
    file_path: Mapped[str] = mapped_column(S, default="")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    category_zh: Mapped[str] = mapped_column(S, default="")
    category_en: Mapped[str] = mapped_column(S, default="")
    category_de: Mapped[str] = mapped_column(S, default="")
    category_jp: Mapped[str] = mapped_column(S, default="")
    title_zh: Mapped[str] = mapped_column(S, default="")
    title_en: Mapped[str] = mapped_column(S, default="")
    title_de: Mapped[str] = mapped_column(S, default="")
    title_jp: Mapped[str] = mapped_column(S, default="")

class Inquiry(Base):
    __tablename__ = "inquiries"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(S, default="")
    email: Mapped[str] = mapped_column(S, default="")
    company: Mapped[str] = mapped_column(S, default="")
    phone: Mapped[str] = mapped_column(S, default="")
    message: Mapped[str] = mapped_column(T, default="")
    source_path: Mapped[str] = mapped_column(S, default="")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Subscriber(Base):
    __tablename__ = "subscribers"
    id: Mapped[int] = mapped_column(primary_key=True)
    salutation: Mapped[str] = mapped_column(String(50), default="")
    first_name: Mapped[str] = mapped_column(S, default="")
    last_name: Mapped[str] = mapped_column(S, default="")
    email: Mapped[str] = mapped_column(S, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Media(Base):
    __tablename__ = "media"
    id: Mapped[int] = mapped_column(primary_key=True)
    path: Mapped[str] = mapped_column(S)            # 相对 uploads/ 的路径
    kind: Mapped[str] = mapped_column(String(20))   # image|file
    thumb_path: Mapped[str] = mapped_column(S, default="")
    webp_path: Mapped[str] = mapped_column(S, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(T, default="")

class AdminUser(Base):
    __tablename__ = "admin_users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(S)
