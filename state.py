"""
state.py
Ek simple JSON file me track karta hai ki konsi jobs already post ho chuki hain,
taaki same job dubara post na ho. Ye file GitHub Actions run ke end me
commit-push ho jaati hai (workflow file me step hai).
"""

import json
import os

import config


def load_posted_ids():
    if not os.path.exists(config.STATE_FILE):
        return set()
    with open(config.STATE_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return set()
    return set(data.get("posted_ids", []))


def save_posted_ids(ids: set):
    os.makedirs(os.path.dirname(config.STATE_FILE), exist_ok=True)
    with open(config.STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"posted_ids": sorted(ids)}, f, indent=2)


def mark_posted(job_id: str):
    ids = load_posted_ids()
    ids.add(job_id)
    save_posted_ids(ids)
