"""
instagram_post.py
Instagram Graph API se post karne ka code — dono, feed IMAGE aur REEL,
support karta hai.
"""

import time
import requests

import config

GRAPH_BASE = "https://graph.facebook.com/v19.0"


def _check_token():
    if not (config.IG_USER_ID and config.IG_ACCESS_TOKEN):
        raise ValueError("IG_USER_ID / IG_ACCESS_TOKEN set nahi hai (secrets check karo)")


def _raise_with_detail(resp):
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except ValueError:
            detail = resp.text
        raise RuntimeError(f"Graph API error (status {resp.status_code}): {detail}")


def post_image(image_url: str, caption: str) -> str:
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


def get_permalink(media_id: str) -> str:
    """Publish hone ke baad us post ka asli Instagram link (permalink) nikalta hai."""
    resp = requests.get(f"{GRAPH_BASE}/{media_id}", params={
        "fields": "permalink",
        "access_token": config.IG_ACCESS_TOKEN,
    }, timeout=30)
    _raise_with_detail(resp)
    return resp.json().get("permalink", "")
