# Rollax 同款四语言企业官网

基于 FastAPI + Jinja2 + SQLite 构建的四语言（中 / 英 / 德 / 日）企业官网，功能与界面参考 rollax.com，
含完整 `/admin` 后台、SEO 基建、媒体库、询盘表单与 Docker 部署配置。

> **版权警告**
>
> 种子数据（内容文本、图片）来自 rollax.com，**仅作本地开发占位使用**。
> **正式上线前必须全部替换为自有内容与图片，不得将种子素材用于任何公开部署。**

---

## 功能特性

- **四语言路由**：中文无前缀（`/`），英/德/日 URL 前缀 `/en/ /de/ /jp/`，内容字段空时自动回退中文
- **前台页面**：首页、通用页面树（多级）、产品分类树、产品详情、新闻列表/详情、招聘、下载、联系/询盘、站内搜索
- **SEO**：hreflang / canonical / JSON-LD BreadcrumbList / sitemap.xml / robots.txt
- **询盘 & 订阅**：Honeypot 反垃圾 + IP 限速 + 可选 SMTP 邮件通知
- **FTS5 站内搜索**：覆盖产品/页面/新闻，多语言独立索引
- **/admin 后台**：
  - 内容 CRUD：页面、产品分类、产品、新闻、招聘、下载（htmx 增强，Quill 富文本）
  - 媒体库：上传图片/文件，自动生成缩略图与 WebP
  - 询盘 & 订阅管理（标记已读、CSV 导出）
  - 站点设置（名称、电话、社交链接、SMTP、统计代码等）
- **部署**：Docker Compose + Nginx 反向代理，静态文件直出，SQLite 每日备份脚本

---

## 本地开发快速上手

### 1. 建虚拟环境并安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

或使用 [uv](https://github.com/astral-sh/uv)：

```bash
uv venv && uv pip install -r requirements.txt
source .venv/bin/activate
```

### 2. 创建管理员账号

```bash
.venv/bin/python scripts/create_admin.py admin yourpassword
```

### 3. 填充种子数据（可选，需联网）

```bash
.venv/bin/python scripts/seed_from_rollax.py
```

> 注意：种子内容来自 rollax.com，仅供开发占位，上线前务必替换。

### 4. 启动开发服务器

```bash
uvicorn app.main:app --reload --port 8000
```

访问 `http://localhost:8000/`，后台 `http://localhost:8000/admin/`。

---

## 运行测试

```bash
.venv/bin/python -m pytest tests/ -q
```

期望输出：`44 passed`（所有任务完成后）。

---

## 后台使用指南

登录地址：`/admin/`

| 模块 | 路径 | 说明 |
|------|------|------|
| 仪表盘 | `/admin/` | 各表数量统计，最新询盘预览 |
| 页面管理 | `/admin/pages` | 多级页面树，支持 Hero 图、SEO 字段 |
| 产品分类 | `/admin/categories` | 多级分类树，卡片/Hero 图 |
| 产品管理 | `/admin/products` | 含四语言 Quill 富文本、图库、SEO |
| 新闻管理 | `/admin/posts` | 草稿/发布状态，封面图，发布时间 |
| 招聘管理 | `/admin/jobs` | 社招/学生/培训分类，开启/关闭状态 |
| 下载管理 | `/admin/downloads` | 文件路径、大小，多语言分类名 |
| 媒体库 | `/admin/media` | 上传图片/文件，自动 WebP + 缩略图 |
| 询盘管理 | `/admin/inquiries` | 标记已读，CSV 导出 |
| 订阅管理 | `/admin/subscribers` | 邮件订阅列表，CSV 导出 |
| 站点设置 | `/admin/settings` | 基本信息、首页 Hero、社交链接、SMTP、统计代码 |

---

## 部署到 VPS（Docker Compose）

### 前提

- VPS 已安装 Docker 与 Docker Compose（`docker compose version` 验证）
- 项目已 `git clone` 到服务器，例如 `/srv/rollax`

### 1. 配置环境变量

在项目根目录创建 `.env`：

```bash
SECRET_KEY=your-random-secret-key-here
BASE_URL=https://your-domain.com
# 生产 HTTPS 部署时开启：
SESSION_HTTPS_ONLY=1
```

> `SESSION_HTTPS_ONLY=1` 会为 Session Cookie 设置 `Secure` 标志（仅 HTTPS 传输），
> 本地 HTTP 开发时保持默认值 `0`。

### 2. 启动服务

```bash
cd /srv/rollax
docker compose -f deploy/docker-compose.yml up -d --build
```

验证：

```bash
curl http://localhost:8080/healthz
# {"ok":true}
```

### 3. 创建管理员（容器内）

```bash
docker compose -f deploy/docker-compose.yml exec app \
  python scripts/create_admin.py admin yourpassword
```

### 4. 配置数据目录权限

```bash
mkdir -p data uploads
chmod 775 data uploads
```

---

## 备份

`scripts/backup.sh` 每次执行：
1. 使用 `sqlite3 .backup` 热备份数据库到 `backups/site-YYYYMMDD.db`
2. 打包 `uploads/` 为 `backups/uploads-YYYYMMDD.tar.gz`
3. 自动清理 14 天前的旧备份

**推荐 crontab（每天凌晨 3 点）：**

```cron
0 3 * * * /srv/rollax/scripts/backup.sh >> /srv/rollax/backups/backup.log 2>&1
```

---

## HTTPS 配置

Nginx 容器默认监听 80 端口。要启用 HTTPS，推荐以下两种方式之一：

1. **Certbot / Let's Encrypt**：在宿主机或 Nginx 容器内配置 SSL，修改 `deploy/nginx.conf` 加 443 监听与证书路径。
2. **Caddy 反向代理**（更简单）：在 Nginx 前加一层 Caddy，自动申请与续期证书，`Caddyfile` 示例：

   ```
   your-domain.com {
       reverse_proxy localhost:8080
   }
   ```

启用 HTTPS 后记得在 `.env` 中设置 `SESSION_HTTPS_ONLY=1`。

---

## 技术栈

Python 3.11+ · FastAPI 0.115 · Jinja2 · SQLAlchemy 2.0 · SQLite（WAL 模式）·
uvicorn · htmx · Quill · bcrypt · Pillow · httpx + BeautifulSoup4 · pytest · Docker + Nginx
