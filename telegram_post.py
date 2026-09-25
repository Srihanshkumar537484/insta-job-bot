"""
telegram_post.py
Har job successfully Instagram pe post hone ke baad, isi job ki details
(title, company, Instagram post link, apply link) ek Telegram channel me
bhi bhej deta hai — Telegram Bot API ke through.
"""

import requests

import config


def is_configured() -> bool:
    return bool(config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID)


def send_job_notification(job: dict, instagram_link: str) -> bool:
    if not is_configured():
        return False

    link_line = f"\n🔗 Apply: {job['link']}" if job.get("link") else ""
    ig_line = f"\n📸 Instagram post: {instagram_link}" if instagram_link else ""

    text = (
        f"🚨 {job['title']} @ {job['company']}\n\n"
        f"📍 {job['location']}\n"
        f"💰 {job['salary']}\n"
        f"⏳ Deadline: {job['deadline']}"
        f"{link_line}"
        f"{ig_line}"
    )

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, data={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": text,
            "disable_web_page_preview": False,
        }, timeout=30)
        if resp.status_code >= 400:
            print(f"[telegram_post] Telegram send failed: {resp.status_code} {resp.text}")
            return False
        return True
    except requests.RequestException as e:
        print(f"[telegram_post] Telegram send error: {e}")
        return False
