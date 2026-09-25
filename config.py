"""
config.py
Sab settings/secrets yahan se load hote hain (environment variables se).
GitHub Actions me ye "Secrets" ke naam se set karoge (README dekho).
"""

import os

# ---- Instagram Graph API ----
IG_USER_ID = os.environ.get("IG_USER_ID", "")          # Instagram Business Account ID
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "") # Long-lived access token

# ---- Job data source ----
# Google Sheet ko File > Share > Publish to web > CSV karke uska link yahan daalna hai
SHEET_CSV_URL = os.environ.get("SHEET_CSV_URL", "")

# Optional: Adzuna API (agar Google Sheet ki jagah use karna ho)
ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")
ADZUNA_COUNTRY = os.environ.get("ADZUNA_COUNTRY", "in")
ADZUNA_QUERY = os.environ.get("ADZUNA_QUERY", "software engineer")

# ---- Posting behaviour ----
MAX_POSTS_PER_RUN = int(os.environ.get("MAX_POSTS_PER_RUN", "3"))  # ek run me kitne jobs post hon
POST_GAP_SECONDS = int(os.environ.get("POST_GAP_SECONDS", "30"))  # do posts ke beech gap

# ---- Telegram (optional — set karo to har post ka notification channel pe jayega) ----
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")  # channel username (@xyz) ya numeric chat id

# ---- Media hosting (Graph API ko public URL chahiye) ----
# GitHub Pages use karenge: repo ke /docs folder ko Pages se serve karenge.
GITHUB_PAGES_BASE_URL = os.environ.get("GITHUB_PAGES_BASE_URL", "")
# example: https://<username>.github.io/<repo-name>

# ---- Paths ----
STATE_FILE = "state/posted_jobs.json"
MEDIA_DIR = "docs/media"
ASSETS_DIR = "assets"
