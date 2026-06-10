LANGS = ["zh", "en", "de", "jp"]
DEFAULT_LANG = "zh"
LANG_NAMES = {"zh": "中文", "en": "English", "de": "Deutsch", "jp": "日本語"}

UI = {
    "nav.home":      {"zh": "首页", "en": "Home", "de": "Startseite", "jp": "ホーム"},
    "nav.products":  {"zh": "产品", "en": "Products", "de": "Produkte", "jp": "製品"},
    "nav.company":   {"zh": "公司", "en": "Company", "de": "Unternehmen", "jp": "会社"},
    "nav.career":    {"zh": "招聘", "en": "Career", "de": "Karriere", "jp": "採用"},
    "nav.news":      {"zh": "新闻", "en": "News", "de": "Aktuelles", "jp": "ニュース"},
    "nav.downloads": {"zh": "下载", "en": "Downloads", "de": "Downloads", "jp": "ダウンロード"},
    "nav.contact":   {"zh": "联系我们", "en": "Contact", "de": "Kontakt", "jp": "お問い合わせ"},
    "btn.readmore":  {"zh": "继续阅读", "en": "Read more", "de": "Weiterlesen", "jp": "続きを読む"},
    "btn.subscribe": {"zh": "订阅", "en": "Subscribe", "de": "Anmelden", "jp": "登録"},
    "btn.send":      {"zh": "发送", "en": "Send", "de": "Senden", "jp": "送信"},
    "btn.inquiry":   {"zh": "发送询盘", "en": "Send inquiry", "de": "Anfrage senden", "jp": "お問い合わせ"},
    "label.search":  {"zh": "搜索", "en": "Search", "de": "Suche", "jp": "検索"},
    "label.breadcrumb_home": {"zh": "首页", "en": "Home", "de": "Startseite", "jp": "ホーム"},
    "newsletter.title": {"zh": "订阅我们的新闻", "en": "Newsletter", "de": "Newsletter", "jp": "ニュースレター"},
    "form.name":  {"zh": "姓名", "en": "Name", "de": "Name", "jp": "お名前"},
    "form.email": {"zh": "邮箱", "en": "E-Mail", "de": "E-Mail", "jp": "メール"},
    "form.company": {"zh": "公司", "en": "Company", "de": "Firma", "jp": "会社名"},
    "form.message": {"zh": "留言", "en": "Message", "de": "Nachricht", "jp": "メッセージ"},
    "msg.thanks": {"zh": "提交成功,我们会尽快联系您。", "en": "Thank you, we will contact you soon.",
                    "de": "Vielen Dank, wir melden uns in Kürze.", "jp": "送信しました。担当者よりご連絡いたします。"},
    "label.404": {"zh": "页面未找到", "en": "Page not found",
                   "de": "Seite nicht gefunden", "jp": "ページが見つかりません"},
    "label.500": {"zh": "服务器内部错误", "en": "Internal Server Error",
                   "de": "Interner Serverfehler", "jp": "サーバーエラー"},
    "job.cat.social":   {"zh": "社会招聘", "en": "Social Hire", "de": "Direktbewerbung", "jp": "社会採用"},
    "job.cat.student":  {"zh": "校园招聘", "en": "Campus Hire", "de": "Hochschulabsolventen", "jp": "学生採用"},
    "job.cat.training": {"zh": "实习培训", "en": "Internship", "de": "Praktikum", "jp": "インターンシップ"},
    "label.download_size": {"zh": "大小", "en": "Size", "de": "Größe", "jp": "サイズ"},
    "label.download": {"zh": "下载", "en": "Download", "de": "Herunterladen", "jp": "ダウンロード"},
    "label.search_results": {"zh": "条结果", "en": "results", "de": "Ergebnisse", "jp": "件の結果"},
    "label.no_results": {"zh": "未找到相关结果", "en": "No results found", "de": "Keine Ergebnisse",
                          "jp": "結果が見つかりません"},
    "label.you_are_here": {"zh": "您的位置", "en": "You are here", "de": "Sie sind hier", "jp": "現在地"},
    "label.backtotop": {"zh": "返回顶部", "en": "Back to top", "de": "Nach oben", "jp": "トップへ"},
    "label.menu": {"zh": "菜单", "en": "Menu", "de": "Menü", "jp": "メニュー"},
    "label.play": {"zh": "播放视频", "en": "Play video", "de": "Video abspielen", "jp": "動画を再生"},
    "footer.contact": {"zh": "联系方式", "en": "Contact", "de": "Kontakt", "jp": "お問い合わせ"},
    "footer.social": {"zh": "社交媒体", "en": "Social Media", "de": "Social Media",
                       "jp": "ソーシャルメディア"},
    "footer.worldwide": {"zh": "全球布局", "en": "Worldwide", "de": "Weltweit", "jp": "グローバル"},
    "btn.locations": {"zh": "全球基地", "en": "Locations", "de": "Standorte", "jp": "拠点一覧"},
    "newsletter.desc": {"zh": "订阅我们的新闻通讯,第一时间了解产品与公司动态。",
                         "en": "Subscribe to our newsletter and stay up to date.",
                         "de": "Abonnieren Sie unseren Newsletter und bleiben Sie auf dem Laufenden.",
                         "jp": "ニュースレターに登録して最新情報をお受け取りください。"},
    "form.salutation": {"zh": "称呼", "en": "Salutation", "de": "Anrede", "jp": "敬称"},
    "form.firstname": {"zh": "名", "en": "First name", "de": "Vorname", "jp": "名"},
    "form.lastname":  {"zh": "姓", "en": "Last name", "de": "Nachname", "jp": "姓"},
    "salutation.mr": {"zh": "先生", "en": "Mr.", "de": "Herr", "jp": "様(男性)"},
    "salutation.ms": {"zh": "女士", "en": "Ms.", "de": "Frau", "jp": "様(女性)"},
}
# 执行时按模板实际用到的词条继续补充 UI 字典,保持同结构。

def t(key: str, lang: str) -> str:
    entry = UI.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get(DEFAULT_LANG) or key

def pick(obj, field: str, lang: str) -> str:
    val = getattr(obj, f"{field}_{lang}", "") or ""
    if not val and lang != DEFAULT_LANG:
        val = getattr(obj, f"{field}_{DEFAULT_LANG}", "") or ""
    return val

def lang_url(lang: str, path: str) -> str:
    if lang == DEFAULT_LANG:
        return path
    return f"/{lang}{path}"
