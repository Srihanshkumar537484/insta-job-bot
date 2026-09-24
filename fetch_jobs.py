"""
fetch_jobs.py
Job listings fetch karta hai — teen source support karta hai:
  1. Repo ki Jobs.csv file (PRIMARY) -> sabse simple, koi setup nahi chahiye
  2. Google Sheet (published as CSV) -> optional fallback
  3. Adzuna API                      -> optional fallback

Har job ek dict banti hai:
{
  "id": "unique-hash",
  "title": "...",
  "company": "...",
  "location": "...",
  "salary": "...",
  "deadline": "...",
  "link": "...",
}
"""

import csv
import hashlib
import io
import os
import requests

import config

LOCAL_CSV_PATH = "Jobs.csv"


def _make_id(title: str, company: str) -> str:
    raw = f"{title.strip().lower()}|{company.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _rows_to_jobs(reader):
    """csv.DictReader se jobs ki list banata hai. Agar kisi row me header se
    zyada columns ho (extra comma), to wo extra data safely ignore ho jata
    hai — crash nahi hota, bas wo extra hissa drop ho jata hai."""
    jobs = []
    for row in reader:
        row.pop(None, None)
        row = {
            (k or "").strip().lower(): (v or "").strip()
            for k, v in row.items()
            if k is not None
        }
        title = row.get("title", "")
        company = row.get("company", "")
        if not title or not company:
            continue  # incomplete row, skip
        jobs.append({
            "id": _make_id(title, company),
            "title": title,
            "company": company,
            "location": row.get("location", "Remote / Multiple"),
            "salary": row.get("salary", "Not disclosed"),
            "deadline": row.get("deadline", "Apply soon"),
            "link": row.get("link", ""),
        })
    return jobs


def fetch_from_local_csv(path: str = LOCAL_CSV_PATH):
    """
    Repo ke andar rakhi Jobs.csv file se seedha job data padhta hai.
    Koi Google Sheet setup nahi chahiye — bas GitHub pe Jobs.csv edit karo,
    commit karo, agli run me bot khud naye jobs utha lega.
    Columns expected (case-insensitive header row):
    title, company, location, salary, deadline, link
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} repo me nahi mili")

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return _rows_to_jobs(reader)


def fetch_from_sheet():
    """
    Google Sheet columns expected (case-insensitive header row):
    title, company, location, salary, deadline, link
    Sheet ko: File -> Share -> Publish to web -> CSV format se publish karo,
    us link ko config.SHEET_CSV_URL me daalo.
    """
    if not config.SHEET_CSV_URL:
        raise ValueError("SHEET_CSV_URL set nahi hai (config.py / secrets check karo)")

    resp = requests.get(config.SHEET_CSV_URL, timeout=30)
    resp.raise_for_status()

    reader = csv.DictReader(io.StringIO(resp.text))
    return _rows_to_jobs(reader)


def fetch_from_adzuna():
    if not (config.ADZUNA_APP_ID and config.ADZUNA_APP_KEY):
        raise ValueError("ADZUNA_APP_ID / ADZUNA_APP_KEY set nahi hai")

    url = f"https://api.adzuna.com/v1/api/jobs/{config.ADZUNA_COUNTRY}/search/1"
    params = {
        "app_id": config.ADZUNA_APP_ID,
        "app_key": config.ADZUNA_APP_KEY,
        "what": config.ADZUNA_QUERY,
        "results_per_page": 10,
        "content-type": "application/json",
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for item in data.get("results", []):
        title = item.get("title", "").strip()
        company = (item.get("company") or {}).get("display_name", "").strip()
        if not title or not company:
            continue
        salary_min = item.get("salary_min")
        salary_max = item.get("salary_max")
        salary = "Not disclosed"
        if salary_min and salary_max:
            salary = f"₹{int(salary_min):,} - ₹{int(salary_max):,}"
        jobs.append({
            "id": _make_id(title, company),
            "title": title,
            "company": company,
            "location": (item.get("location") or {}).get("display_name", "India"),
            "salary": salary,
            "deadline": "Apply soon",
            "link": item.get("redirect_url", ""),
        })
    return jobs


def fetch_all_jobs():
    """
    Priority order:
      1. Repo ki Jobs.csv file (sabse simple — GitHub pe edit karo, bas)
      2. Google Sheet (agar SHEET_CSV_URL set hai)
      3. Adzuna API (agar keys set hain)
    Jaise hi kisi source se jobs mil jate hain, aage wale sources skip ho jate hain.
    """
    jobs = []

    try:
        jobs.extend(fetch_from_local_csv())
    except Exception as e:
        print(f"[fetch_jobs] Local Jobs.csv fetch failed: {e}")

    if not jobs and config.SHEET_CSV_URL:
        try:
            jobs.extend(fetch_from_sheet())
        except Exception as e:
            print(f"[fetch_jobs] Sheet fetch failed: {e}")

    if not jobs and config.ADZUNA_APP_ID:
        try:
            jobs.extend(fetch_from_adzuna())
        except Exception as e:
            print(f"[fetch_jobs] Adzuna fetch failed: {e}")

    return jobs
