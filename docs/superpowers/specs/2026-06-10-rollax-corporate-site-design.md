# Rollax 同款企业官网 — 设计文档

日期:2026-06-10
状态:已与用户确认

## 1. 目标

为用户自己的公司(与 rollax.com 同行业:轴承/运动系统制造,外贸)开发一个内容结构、版式、视觉风格与 https://www.rollax.com/ 完整对齐的企业官网,带完整后台管理,SEO 友好,轻量,部署到云服务器 VPS。

- 四语言:中(默认)/ 英 / 德 / 日,URL 前缀 `/`、`/en/`、`/de/`、`/jp/`
- 开发阶段用 rollax.com 的公开文本和图片做种子填充数据;**正式上线前必须通过后台替换为自有素材(版权要求)**
- 数据库 SQLite,单文件 + 本地 uploads/ 目录

## 2. 技术栈(方案 A,已选定)

```
浏览器 ──▶ Nginx(静态/缓存/HTTPS) ──▶ FastAPI + uvicorn
                                        ├─ 前台:Jinja2 SSR,四语言路由
                                        ├─ 后台:/admin,Jinja2 模板 + htmx(无前端构建链)
                                        ├─ SQLite(WAL 模式)
                                        └─ uploads/ 图片与文件
```

- Python 3.11+,FastAPI,Jinja2,SQLAlchemy(或 sqlite3 + 轻量 DAO),Pillow(缩略图/WebP)
- 富文本编辑器:Quill 或 TipTap,CDN 引入
- 打包:Dockerfile + docker-compose(app + nginx);本地开发直接 uvicorn --reload
- 内存目标 ~80MB,1 核 1G VPS 可跑

## 3. 前台信息架构(与 rollax.com 对照)

| 板块 | 说明 |
|---|---|
| 双层导航 | 深蓝顶栏(主导航+电话+搜索+语言切换)+ 白色产品栏(7 大产品分类) |
| 首页 | 全屏视频/大图 Hero、公司介绍两栏文字、产品分类卡片墙(瀑布流)、Newsletter 订阅条 |
| 产品 | 多级分类树(New Mobility 含 6 子类、Federbeinlager、Standard-Kugellager、Lenkungslager、Sitzversteller、Arretierung und Rastierung、Sonstige Lösungen);详情页 = 大图 Hero + 面包屑 + 正文 + 右侧产品树 + 询盘 CTA |
| 公司 | 简介、DNS(企业文化)、全球布局(欧/美/亚)、能力、客户、质量 —— 通用页面树维护 |
| 研发 / 合作赞助 | 通用页面树维护 |
| 招聘 | 职位列表+详情,分类:社招/学生/培训岗 |
| 新闻 | 分页列表(缩略图+摘要+继续阅读按钮)+ 详情 |
| 下载 | 分类文件列表 |
| 联系 | 公司信息 + 询盘表单(落库+可选邮件通知) |
| 站内搜索 | SQLite FTS5 全文搜索,顶栏放大镜入口 |
| 法务/页脚 | Sitemap、Impressum、隐私、AGB、Compliance、Social Media;页脚含联系方式、社交图标、世界地图+据点按钮、版权条 |

视觉:深蓝(#0a2e6e 系)+ 白工业风,照截图还原配色、字体气质、卡片、按钮样式。

## 4. 数据模型

多语言策略:每个内容表用 `*_zh / *_en / *_de / *_jp` 四组字段(非翻译表)。某语言留空时前台回退中文。

核心表:

- `pages` — 通用页面树:slug、parent_id、sort、模板类型、四语言(title/body/seo_title/seo_desc/seo_keywords)、是否显示导航
- `product_categories` — 分类树:slug、parent_id、sort、四语言名称/简介、卡片图、Hero 图
- `products` — slug、category_id、sort、四语言(名称/正文/SEO)、主图、图集(JSON)
- `posts` — 新闻:slug、四语言(标题/摘要/正文/SEO)、封面、publish_at、status(草稿/发布)
- `jobs` — 职位:四语言(标题/正文)、分类(社招/学生/培训)、有效期、status
- `downloads` — 文件:分类、四语言标题、文件路径、大小
- `inquiries` — 询盘:姓名/邮箱/公司/留言/来源页、已读状态、created_at
- `subscribers` — 订阅:称谓/姓/名/邮箱、created_at
- `media` — 媒体库:文件路径、类型、尺寸、缩略图/WebP 路径
- `settings` — 键值:公司信息、社交链接、统计代码、SMTP 配置
- `admin_users` — 后台账号:用户名、bcrypt 密码哈希
- FTS5 虚表 `search_index` — 产品/页面/新闻四语言全文索引

## 5. 后台 `/admin`

- 登录:session + bcrypt,登录限速防爆破
- 仪表盘:最新询盘/订阅、内容统计
- 内容管理(全部带四语言 Tab):产品分类(树+拖拽排序)、产品(富文本+图集)、通用页面(树)、新闻(草稿/定时发布)、招聘、下载
- 媒体库:上传图片/PDF,自动缩略图+WebP
- 询盘管理:列表、已读/未读、CSV 导出、SMTP 邮件提醒(可配)
- 订阅管理:名单导出
- 站点设置 + SEO 设置(每内容独立四语言 TDK)

## 6. SEO 内建

- 全站 SSR 直出 HTML,语义化标签
- 四语言 `hreflang` 互链 + canonical
- 自动 `sitemap.xml`(四语言)+ `robots.txt`
- 面包屑 JSON-LD 结构化数据、OG 标签
- 图片 lazy-load + WebP、友好 slug URL

## 7. 种子数据(开发用)

抓取脚本:爬 rollax.com 四语言公开页面(带浏览器 UA;站点有 Cloudflare,个别页面可能 403/520,抓不到的用占位文本),解析正文与图片,下载图片入 media,内容灌入对应表。脚本一次性运行,可重复执行(幂等)。

## 8. 部署

- `Dockerfile` + `docker-compose.yml`(app + nginx),VPS 上 `docker compose up -d`
- SQLite WAL;每日 cron 备份 db + uploads 打包
- 环境变量:SECRET_KEY、管理员初始密码、SMTP 等

## 9. 错误处理与测试

- 自定义 404/500 页(四语言)
- 表单校验(服务端),询盘防垃圾:honeypot 字段 + 限速
- 测试:pytest + httpx,覆盖路由渲染、后台 CRUD、多语言回退、sitemap/hreflang 生成
