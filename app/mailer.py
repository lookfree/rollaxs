import smtplib
from email.mime.text import MIMEText


def notify_inquiry(site: dict, inquiry) -> None:
    host = site.get("smtp_host")
    if not host:
        return
    msg = MIMEText(
        f"姓名: {inquiry.name}\n邮箱: {inquiry.email}\n公司: {inquiry.company}\n"
        f"电话: {inquiry.phone}\n留言:\n{inquiry.message}",
        "plain",
        "utf-8",
    )
    # 头部值必须去掉换行,防止邮件头注入
    safe_name = (inquiry.name or "").replace("\r", " ").replace("\n", " ")
    msg["Subject"] = f"[官网询盘] {safe_name}"
    msg["From"] = site.get("smtp_from", site.get("smtp_user", ""))
    msg["To"] = site.get("inquiry_to", "")
    try:
        with smtplib.SMTP(host, int(site.get("smtp_port", "587")), timeout=10) as s:
            if site.get("smtp_tls", "1") == "1":
                s.starttls()
            if site.get("smtp_user"):
                s.login(site["smtp_user"], site.get("smtp_password", ""))
            s.send_message(msg)
    except Exception:
        pass  # SMTP failure must never break form POST
