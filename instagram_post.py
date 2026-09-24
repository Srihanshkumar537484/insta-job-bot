"""
"""
instagram_post.py
Instagram Graph API se post karne ka code — dono, feed IMAGE aur REEL,
support karta hai. Graph API ka flow do-step hai:
  1. Media container create karo (image_url ya video_url de kar)
  2. Container ko publish karo
Video (reel) ke case me container ko process hone me thoda time lagta hai,
isliye status poll karte hain jab tak "FINISHED" na ho jaye.

IMPORTANT: Graph API ko media ka PUBLIC URL chahiye (localhost/private URL
nahi chalega) — isliye pehle GitHub Pages pe file host karni padti hai
(main.py me ye step hai).
"""

import time
import requests

import config

GRAPH_BASE = "https://graph.facebook.com/v19.0"


def _check_token():
    if not (config.IG_USER_ID and config.IG_ACCESS_TOKEN):
        raise ValueError("IG_USER_ID / IG_ACCESS_TOKEN set nahi hai (secrets check karo)")


def _raise_with_detail(resp):
    """Graph API fail ho to uska asli JSON error message print/raise karo,
    sirf '400 Bad Request' nahi — taaki asli wajah pata chale."""
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except ValueError:
            detail = resp.text
        raise RuntimeError(f"Graph API error (status {resp.status_code}): {detail}")


def post_image(image_url: str, caption: str) -> str:
    """Feed post karta hai. Returns published media id."""
    _check_token()

    create_url = f"{GRAPH_BASE}/{config.IG_USER_ID}/media"
    resp = requests.post(create_url, data={
        "image_url": image_url,
        "caption": caption,
        "access_token": config.IG_ACCESS_TOKEN,
    }, timeout=60)
    _raise_with_detail(resp)
    creation_id = resp.json()["id"]

    return _publish(creation_id)


def post_reel(video_url: str, caption: str, cover_url: str = None) -> str:
    """Reel post karta hai. Returns published media id."""
    _check_token()

    create_url = f"{GRAPH_BASE}/{config.IG_USER_ID}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": config.IG_ACCESS_TOKEN,
    }
    if cover_url:
        payload["cover_url"] = cover_url

    resp = requests.post(create_url, data=payload, timeout=60)
    _raise_with_detail(resp)
    creation_id = resp.json()["id"]

    _wait_until_ready(creation_id)
    return _publish(creation_id)


def _wait_until_ready(creation_id: str, max_wait_seconds: int = 180, poll_every: int = 10):
    """Reel container ko process hone me time lagta hai — status poll karo."""
    status_url = f"{GRAPH_BASE}/{creation_id}"
    waited = 0
    while waited < max_wait_seconds:
        resp = requests.get(status_url, params={
            "fields": "status_code",
            "access_token": config.IG_ACCESS_TOKEN,
        }, timeout=30)
        resp.raise_for_status()
        status = resp.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Instagram video processing failed for container {creation_id}")
        time.sleep(poll_every)
        waited += poll_every
    raise TimeoutError(f"Video container {creation_id} processing timeout")


def _publish(creation_id: str) -> str:
    publish_url = f"{GRAPH_BASE}/{config.IG_USER_ID}/media_publish"
    resp = requests.post(publish_url, data={
        "creation_id": creation_id,
        "access_token": config.IG_ACCESS_TOKEN,
    }, timeout=60)
    _raise_with_detail(resp)
    return resp.json()["id"]
