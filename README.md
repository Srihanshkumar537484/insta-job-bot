# Instagram Job-Alert Auto-Poster

Ye bot roz naye jobs ko automatically Instagram pe **post/reel** bana ke daal deta hai.
Poora code ban chuka hai — tumhe sirf neeche wale **one-time setup steps** karne hain,
uske baad ye khud daily chalega (GitHub Actions se, bilkul free).

---

## Kaise kaam karta hai (short me)

1. Ek Google Sheet me tum job entries daalte ho (title, company, salary, deadline, link)
2. Bot roz us sheet ko padhta hai, jo jobs pehle post nahi hui unko pick karta hai
3. Har job ke liye ek image ya reel banata hai (Python + Pillow/FFmpeg se)
4. Us media ko GitHub Pages pe host karta hai (public URL ke liye — Graph API ko yahi chahiye)
5. Instagram Graph API se ek-ek karke post/reel publish karta hai
6. Konsi job post ho chuki hai, `state/posted_jobs.json` me save kar leta hai (dobara post nahi hoti)

---

## SETUP STEPS (ye tumhe karna hai)

### 1. Instagram Business/Creator account
- Instagram app → Settings → Account type → **Business** ya **Creator** account me switch karo

### 2. Facebook Page banao aur link karo
- facebook.com pe ek naya Page banao (agar nahi hai)
- Instagram Settings → **Linked Accounts** → us Facebook Page se link karo

### 3. Meta Developer app banao
- [developers.facebook.com](https://developers.facebook.com) pe App create karo (type: Business)
- App me **Instagram Graph API** product add karo
- Graph API Explorer se ek **long-lived access token** generate karo jisme ye permissions hon:
  `instagram_basic`, `instagram_content_publish`, `pages_read_engagement`, `pages_show_list`
- Apna **Instagram Business Account ID** bhi wahin se nikal lo (`IG_USER_ID`)

### 4. Google Sheet banao (job data)
Columns exactly ye rakhna (header row me):

| title | company | location | salary | deadline | link |
|---|---|---|---|---|---|
| Backend Developer | Acme Pvt Ltd | Bangalore | ₹6-9 LPA | 30 Sep | https://... |

Phir: **File → Share → Publish to web → CSV format** choose karo, jo link mile wo copy kar lo (`SHEET_CSV_URL`).

### 5. GitHub repo banao
- Is poore folder ko ek naye GitHub repo me push karo
- Repo **Settings → Pages** me jaake source ko **`/docs` folder (main branch)** set karo
- Save karne ke baad tumhe ek URL milega jaisे `https://<username>.github.io/<repo-name>` —
  yahi `GITHUB_PAGES_BASE_URL` hai (isme aage `/` mat lagana, trailing slash nahi)

### 6. GitHub Secrets add karo
Repo → **Settings → Secrets and variables → Actions → New repository secret** — ye sab add karo:

| Secret name | Value |
|---|---|
| `IG_USER_ID` | Step 3 wala Instagram Business Account ID |
| `IG_ACCESS_TOKEN` | Step 3 wala long-lived access token |
| `SHEET_CSV_URL` | Step 4 wala CSV link |
| `GITHUB_PAGES_BASE_URL` | Step 5 wala Pages URL |

(Adzuna wale optional secrets sirf tab chahiye agar sheet ki jagah Adzuna API use karna ho.)

### 7. Test run karo
- Repo → **Actions** tab → "Daily Job Reel/Post Automation" → **Run workflow** (manual trigger)
- Logs check karo — agar sab sahi hai to job(s) Instagram pe post ho jayengi

Uske baad ye **har din apne aap** chalega (cron: roz subah ~9:30 IST — `.github/workflows/daily_post.yml` me time change kar sakte ho).

---

## Files kya kya karti hain

| File | Kaam |
|---|---|
| `config.py` | Saari settings/secrets ek jagah |
| `fetch_jobs.py` | Google Sheet / Adzuna se job data laata hai |
| `generate_creative.py` | Image post + Reel video banata hai (Pillow + FFmpeg) |
| `instagram_post.py` | Graph API se actual posting karta hai |
| `state.py` | Kaunsi job post ho chuki, track karta hai |
| `main.py` | Sabko jodta hai — ye hi run hota hai |
| `.github/workflows/daily_post.yml` | Daily automatic schedule |

---

## Zaroori baatein / limits

- **Har run me max 3 jobs post hoti hain** (`MAX_POSTS_PER_RUN` config me change kar sakte ho) — Instagram ke publishing rate limits (per 24hr ~25 posts) ke andar rehna zaroori hai, warna account restrict ho sakta hai.
- Ye purely **legit Graph API route** hai — koi auto-follow/auto-like/scraping bot nahi hai, isliye ban hone ka risk bahut kam hai.
- Agar tumhara apna design template hai, `assets/template.jpg` me daal do — code usi background pe text overlay karega. Nahi hai to ek default gradient background use hota hai.
- Access token 60 din me expire hota hai — Meta ke docs se refresh karne ka tareeka follow karo, ya naya generate kar ke secret update karo.
