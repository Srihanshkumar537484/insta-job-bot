"""
generate_creative.py
Job dict se ek Instagram-ready IMAGE (1080x1350) aur REEL (1080x1920, ~8 sec)
banata hai. Pure Pillow + FFmpeg se — koi paid API nahi chahiye.

Agar tumhare paas apna background template (PNG/JPG) hai, use
assets/template.jpg me rakh do — code usko automatically use karega.
Nahi hai to code khud ek plain gradient background bana lega.
"""

import os
import json
import subprocess
import textwrap

from PIL import Image, ImageDraw, ImageFont

try:
    from gtts import gTTS
except ImportError:  # gTTS abhi tak install nahi hai to bhi crash na ho
    gTTS = None

import config

IMG_SIZE = (1080, 1350)     # feed post size
REEL_SIZE = (1080, 1920)    # reel/story size
REEL_DURATION = 8           # seconds

BRAND_COLOR = (20, 20, 30)
ACCENT_COLOR = (255, 200, 0)
TEXT_COLOR = (255, 255, 255)

# ---------------------------------------------------------------------------
# 10 ROTATING TEMPLATES
# Har naye job post ke liye agla template use hota hai. 10 ke baad wapas
# pehle wale se shuru ho jata hai (cycle). Index state/template_index.json
# me save rehta hai taaki agla GitHub Actions run bhi wahi se continue kare.
# ---------------------------------------------------------------------------
TEMPLATES = [
    {"name": "Midnight Gold",     "brand": (20, 20, 30),  "accent": (255, 200, 0),   "text": (255, 255, 255), "style": "diag",  "tag": "🔥 NEW JOB ALERT",     "cta": "Apply link in bio / comments →"},
    {"name": "Ocean Blue",        "brand": (10, 30, 60),  "accent": (0, 200, 255),   "text": (255, 255, 255), "style": "vert",  "tag": "🚀 FRESH JOB ALERT",   "cta": "Apply link in bio / comments →"},
    {"name": "Crimson Pop",       "brand": (40, 10, 15),  "accent": (255, 60, 60),   "text": (255, 255, 255), "style": "solid", "tag": "📢 JOB ALERT",         "cta": "Swipe up / link in bio →"},
    {"name": "Forest Green",      "brand": (10, 35, 20),  "accent": (100, 220, 120), "text": (255, 255, 255), "style": "diag",  "tag": "💼 HIRING NOW",        "cta": "Apply link in bio / comments →"},
    {"name": "Royal Purple",      "brand": (30, 15, 45),  "accent": (190, 120, 255), "text": (255, 255, 255), "style": "vert",  "tag": "✨ NEW OPENING",       "cta": "Apply link in bio →"},
    {"name": "Sunset Orange",     "brand": (45, 20, 10),  "accent": (255, 140, 60),  "text": (255, 255, 255), "style": "solid", "tag": "🔥 JOB ALERT",         "cta": "Apply link in bio / comments →"},
    {"name": "Slate Gray",        "brand": (35, 35, 40),  "accent": (200, 200, 210), "text": (255, 255, 255), "style": "diag",  "tag": "📌 NEW JOB ALERT",     "cta": "Apply link in bio / comments →"},
    {"name": "Hot Pink",          "brand": (40, 10, 30),  "accent": (255, 80, 170),  "text": (255, 255, 255), "style": "vert",  "tag": "🚨 HIRING ALERT",      "cta": "Apply link in bio / comments →"},
    {"name": "Teal Fresh",        "brand": (10, 40, 40),  "accent": (60, 230, 210),  "text": (255, 255, 255), "style": "solid", "tag": "💼 WE'RE HIRING",      "cta": "Apply link in bio / comments →"},
    {"name": "Charcoal Yellow",   "brand": (25, 25, 25),  "accent": (255, 225, 80),  "text": (255, 255, 255), "style": "diag",  "tag": "🔥 NEW JOB ALERT",     "cta": "Apply link in bio / comments →"},
]


def _template_index_path():
    state_dir = getattr(config, "STATE_DIR", "state")
    return os.path.join(state_dir, "template_index.json")


def get_next_template():
    """Agla template return karta hai aur rotation index ko file me save kar deta hai.
    10 templates ke baad wapas index 0 se shuru ho jata hai."""
    path = _template_index_path()
    idx = 0
    if os.path.exists(path):
        try:
            with open(path) as f:
                idx = json.load(f).get("index", 0)
        except Exception:
            idx = 0

    idx = idx % len(TEMPLATES)
    template = TEMPLATES[idx]

    next_idx = (idx + 1) % len(TEMPLATES)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump({"index": next_idx}, f)

    return template


def _load_font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _background(size, template=None):
    template_path = os.path.join(config.ASSETS_DIR, "template.jpg")
    if os.path.exists(template_path):
        # agar tumne apna custom background daal rakha hai (assets/template.jpg),
        # to wahi use hoga — rotating templates niche wale sirf tab lagenge
        # jab ye file exist nahi karti.
        bg = Image.open(template_path).convert("RGB").resize(size)
        return bg

    brand = template["brand"] if template else BRAND_COLOR
    style = template["style"] if template else "diag"

    bg = Image.new("RGB", size, brand)
    draw = ImageDraw.Draw(bg)

    if style == "solid":
        pass  # flat color, kuch aur draw nahi karna
    elif style == "vert":
        # top se bottom halka lighter gradient
        for y in range(size[1]):
            shade = int((y / size[1]) * 40)
            r = min(255, brand[0] + shade)
            g = min(255, brand[1] + shade)
            b = min(255, brand[2] + shade)
            draw.line([(0, y), (size[0], y)], fill=(r, g, b))
    else:  # "diag" (default) — original diagonal-ish banding
        for y in range(size[1]):
            shade = int((y / size[1]) * 25)
            r = min(255, brand[0] + shade)
            g = min(255, brand[1] + shade)
            b = min(255, brand[2] + shade + 15)
            draw.line([(0, y), (size[0], y)], fill=(r, g, b))

    return bg


def _wrap(text, width):
    return "\n".join(textwrap.wrap(text, width=width))


def build_image(job: dict, out_path: str):
    template = get_next_template()
    brand, accent, text_color = template["brand"], template["accent"], template["text"]

    img = _background(IMG_SIZE, template)
    draw = ImageDraw.Draw(img)

    pad = 70
    y = 120

    tag_font = _load_font(42, bold=True)
    title_font = _load_font(64, bold=True)
    label_font = _load_font(38, bold=True)
    value_font = _load_font(40)

    draw.text((pad, y), template["tag"], font=tag_font, fill=accent)
    y += 100

    title_wrapped = _wrap(job["title"], 22)
    draw.multiline_text((pad, y), title_wrapped, font=title_font, fill=text_color, spacing=14)
    y += title_font.size * (title_wrapped.count("\n") + 1) + 60

    rows = [
        ("Company", job["company"]),
        ("Location", job["location"]),
        ("Salary", job["salary"]),
        ("Deadline", job["deadline"]),
    ]
    for label, value in rows:
        draw.text((pad, y), label.upper(), font=label_font, fill=accent)
        y += 48
        draw.multiline_text((pad, y), _wrap(str(value), 34), font=value_font, fill=text_color)
        y += value_font.size * 2 + 30

    draw.rectangle([(0, IMG_SIZE[1] - 110), (IMG_SIZE[0], IMG_SIZE[1])], fill=accent)
    cta_font = _load_font(40, bold=True)
    draw.text((pad, IMG_SIZE[1] - 90), template["cta"],
              font=cta_font, fill=brand)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, quality=92)
    return out_path


def _voiceover_text(job: dict) -> str:
    return (
        f"New job alert! {job['title']} at {job['company']}. "
        f"Location: {job['location']}. "
        f"Salary: {job['salary']}. "
        f"Apply before {job['deadline']}."
    )


def build_audio(job: dict, out_path: str):
    """gTTS se 'New job alert...' wali voice-over mp3 banata hai."""
    if gTTS is None:
        raise RuntimeError("gTTS installed nahi hai (requirements.txt me 'gTTS' add karo)")
    tts = gTTS(text=_voiceover_text(job), lang="en")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    tts.save(out_path)
    return out_path


def _audio_duration(path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrapper=1:nokey=1",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def build_reel(job: dict, out_path: str):
    """
    Static-image-style reel: background + text overlay, FFmpeg se render.
    Pehle ek frame image Pillow se banate hain (build_image jaisa but reel size),
    phir uske upar ek "New job alert..." wali voice-over (gTTS) generate karke
    ffmpeg se image + audio dono ko mila kar ek video bana dete hain.
    Agar kisi wajah se voice-over generate nahi ho paata (jaise internet issue),
    to reel bina awaaz ke (silent) bhi ban jayega — job fail nahi hoga.
    """
    template = get_next_template()
    brand, accent, text_color = template["brand"], template["accent"], template["text"]

    frame_path = out_path.replace(".mp4", "_frame.jpg")

    img = _background(REEL_SIZE, template)
    draw = ImageDraw.Draw(img)

    pad = 70
    y = 260

    tag_font = _load_font(46, bold=True)
    title_font = _load_font(72, bold=True)
    label_font = _load_font(42, bold=True)
    value_font = _load_font(44)

    draw.text((pad, y), template["tag"], font=tag_font, fill=accent)
    y += 120

    title_wrapped = _wrap(job["title"], 20)
    draw.multiline_text((pad, y), title_wrapped, font=title_font, fill=text_color, spacing=16)
    y += title_font.size * (title_wrapped.count("\n") + 1) + 80

    rows = [
        ("Company", job["company"]),
        ("Location", job["location"]),
        ("Salary", job["salary"]),
        ("Deadline", job["deadline"]),
    ]
    for label, value in rows:
        draw.text((pad, y), label.upper(), font=label_font, fill=accent)
        y += 52
        draw.multiline_text((pad, y), _wrap(str(value), 30), font=value_font, fill=text_color)
        y += value_font.size * 2 + 40

    draw.rectangle([(0, REEL_SIZE[1] - 130), (REEL_SIZE[0], REEL_SIZE[1])], fill=accent)
    cta_font = _load_font(44, bold=True)
    draw.text((pad, REEL_SIZE[1] - 105), template["cta"],
              font=cta_font, fill=brand)

    os.makedirs(os.path.dirname(frame_path), exist_ok=True)
    img.save(frame_path, quality=92)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # Voice-over banane ki koshish karo; fail ho to silent reel bana denge
    audio_path = out_path.replace(".mp4", "_audio.mp3")
    audio_ok = False
    try:
        build_audio(job, audio_path)
        audio_ok = True
    except Exception as e:
        print(f"WARNING: voice-over nahi ban paya ({e}), reel silent banega.")

    duration = REEL_DURATION
    if audio_ok:
        try:
            duration = max(REEL_DURATION, _audio_duration(audio_path) + 1)
        except Exception:
            pass

    if audio_ok:
        # image loop + voice-over audio dono ko mila kar video banao
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", frame_path,
            "-i", audio_path,
            "-c:v", "libx264",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-vf", f"scale={REEL_SIZE[0]}:{REEL_SIZE[1]}",
            "-c:a", "aac",
            "-b:a", "128k",
            out_path,
        ]
    else:
        # purana silent-reel wala tareeka (fallback)
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", frame_path,
            "-c:v", "libx264",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-vf", f"scale={REEL_SIZE[0]}:{REEL_SIZE[1]}",
            out_path,
        ]

    subprocess.run(cmd, check=True, capture_output=True)
    os.remove(frame_path)
    if audio_ok and os.path.exists(audio_path):
        os.remove(audio_path)
    return out_path


def build_caption(job: dict) -> str:
    link_line = f"\n🔗 Apply: {job['link']}" if job.get("link") else ""
    return (
        f"🚨 {job['title']} @ {job['company']}\n\n"
        f"📍 Location: {job['location']}\n"
        f"💰 Salary: {job['salary']}\n"
        f"⏳ Deadline: {job['deadline']}"
        f"{link_line}\n\n"
        f"👉 Follow for daily job updates!\n"
        f"#jobs #hiring #jobalert #freshershiring #{job['company'].replace(' ', '')}"
    )
