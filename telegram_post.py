"""
telegram_post.py
Job ka media (reel/image) + caption (jisme apply link bhi hota hai)
Telegram channel par bhejta hai, Telegram Bot API (sendVideo / sendPhoto) se.
Local file directly upload hoti hai — GitHub Pages public URL ka wait
nahi karna padta (Instagram ke alag, Telegram bot API file upload allow
karta hai).

--------------------------- SETUP (ek baar karna hai) ---------------------------
1. Telegram me @BotFather ko message karo -> /newbot -> naam do -> ek
   BOT TOKEN milega (jaisa: 123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx).
2. Apna Telegram channel kholo -> Administrators -> Add Admin -> apne
   naye bot ko admin banao ("Post Messages" permission zaroor on rakhna).
3. Channel ka username nikal lo (jaise @mychannel) — agar channel
   private hai to numeric chat_id use karna padega (uska tareeka thoda
   alag hai, bata dena agar channel private hai).
4. config.py me ye 2 lines add kar do:
       TELEGRAM_BOT_TOKEN = "yaha_apna_bot_token_daalo"
       TELEGRAM_CHAT_ID = "@mychannel"
---------------------------------------------------------------------------------
"""

import requests

import config


def _api_url(method: str) -> str:
    token = getattr(config, "TELEGRAM_BOT_TOKEN", None)
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN config.py me set nahi hai")
    return f"https://api.telegram.org/bot{token}/{method}"


def _chat_id():
    chat_id = getattr(config, "TELEGRAM_CHAT_ID", None)
    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID config.py me set nahi hai")
    return chat_id


def _check(resp):
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")
    return data["result"]


def post_video(local_path: str, caption: str):
    """Reel (.mp4) ko Telegram channel par video ke roop me post karta hai."""
    with open(local_path, "rb") as f:
        resp = requests.post(
            _api_url("sendVideo"),
            data={
                "chat_id": _chat_id(),
                "caption": caption[:1024],  # Telegram caption limit
                "supports_streaming": True,
            },
            files={"video": f},
            timeout=120,
        )
    result = _check(resp)
    return result["message_id"]


def post_photo(local_path: str, caption: str):
    """Feed image (.jpg) ko Telegram channel par photo ke roop me post karta hai."""
    with open(local_path, "rb") as f:
        resp = requests.post(
            _api_url("sendPhoto"),
            data={"chat_id": _chat_id(), "caption": caption[:1024]},
            files={"photo": f},
            timeout=60,
        )
    result = _check(resp)
    return result["message_id"]
