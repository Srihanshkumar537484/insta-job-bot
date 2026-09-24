"""
generate_creative.py
Job dict se ek Instagram-ready IMAGE (1080x1350) aur REEL (1080x1920, ~8 sec)
banata hai. Pure Pillow + FFmpeg se — koi paid API nahi chahiye.

Ab isme 20 alag ALAG DESIGN wale templates hain (sirf color nahi, poora
layout/look badalta hai):
  - "megaphone" : ek banda megaphone leke job announce kar raha hai
  - "chat"      : do log chat kar rahe hain jaise WhatsApp pe job bataya
  - "badge"     : verified/certified stamp-style badge design
  - "ticket"    : movie-ticket / entry-pass style card
  - "billboard" : road-side hoarding/billboard style

Har naye job post ke liye agla template use hota hai (round-robin), 20 ke
baad wapas pehle wale se shuru ho jata hai. Rotation index
state/template_index.json me save rehta hai.

Agar tumhare paas apna background template (PNG/JPG) hai, use
assets/template.jpg me rakh do — code usko automatically use karega
(is case me rotating designs ki jagah wahi background use hoga).
"""

import os
import json
import random
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
# 20 ROTATING TEMPLATES
# Har template me "layout" batata hai konsa design use hoga, aur baaki
# fields (brand/accent/text) us design ka color palette. Har naye job
# post ke liye agla template use hota hai; 20 ke baad wapas 0 se shuru.
# ---------------------------------------------------------------------------
_LAYOUT_CYCLE = ["megaphone", "chat", "badge", "ticket", "billboard"]

_PALETTES = [
    ("Midnight Gold",   (20, 20, 30),  (255, 200, 0)),
    ("Ocean Blue",      (10, 30, 60),  (0, 200, 255)),
    ("Crimson Pop",     (40, 10, 15),  (255, 60, 60)),
    ("Forest Green",    (10, 35, 20),  (100, 220, 120)),
    ("Royal Purple",    (30, 15, 45),  (190, 120, 255)),
    ("Sunset Orange",   (45, 20, 10),  (255, 140, 60)),
    ("Slate Gray",      (35, 35, 40),  (200, 200, 210)),
    ("Hot Pink",        (40, 10, 30),  (255, 80, 170)),
    ("Teal Fresh",      (10, 40, 40),  (60, 230, 210)),
    ("Charcoal Yellow", (25, 25, 25),  (255, 225, 80)),
    ("Deep Indigo",     (15, 15, 50),  (120, 140, 255)),
    ("Lime Punch",      (20, 40, 10),  (190, 255, 60)),
    ("Berry Wine",      (35, 10, 25),  (255, 90, 140)),
    ("Steel Cyan",      (10, 30, 35),  (80, 220, 255)),
    ("Amber Rush",      (35, 25, 5),   (255, 180, 40)),
    ("Mint Fresh",      (10, 35, 30),  (90, 240, 190)),
    ("Coral Blush",     (40, 15, 20),  (255, 120, 110)),
    ("Violet Dream",    (25, 10, 40),  (170, 100, 255)),
    ("Graphite Blue",   (20, 25, 35),  (90, 170, 255)),
    ("Sunflower",       (30, 25, 10),  (255, 210, 60)),
]

_TAGS = [
    "NEW JOB ALERT", "FRESH JOB ALERT", "JOB ALERT", "HIRING NOW",
    "NEW OPENING", "JOB ALERT", "NEW JOB ALERT", "HIRING ALERT",
    "WE'RE HIRING", "NEW JOB ALERT", "JOB ALERT", "NEW OPENING",
    "HIRING NOW", "FRESH ALERT", "WE'RE HIRING", "JOB ALERT",
    "NEW OPENING", "HIRING ALERT", "JOB ALERT", "FRESH OPENING",
]

_CTAS = [
    "Apply link in bio / comments →", "Swipe up / link in bio →",
    "Apply link in bio →",
]

TEMPLATES = []
for _i, (_name, _brand, _accent) in enumerate(_PALETTES):
    TEMPLATES.append({
        "name": _name,
        "brand": _brand,
        "accent": _accent,
        "text": (255, 255, 255),
        "layout": _LAYOUT_CYCLE[_i % len(_LAYOUT_CYCLE)],
        "tag": _TAGS[_i % len(_TAGS)],
        "cta": _CTAS[_i % len(_CTAS)],
    })


def _template_index_path():
    state_dir = getattr(config, "STATE_DIR", "state")
    return os.path.join(state_dir, "template_index.json")


def get_next_template():
    """Agla template return karta hai aur rotation index ko file me save kar deta hai.
    20 templates ke baad wapas index 0 se shuru ho jata hai."""
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


def _wrap(text, width):
    return "\n".join(textwrap.wrap(text, width=width))


# ---------------------------------------------------------------------------
# Drawing helpers (reusable shapes used across layouts)
# ---------------------------------------------------------------------------
def _background(size, template=None):
    template_path = os.path.join(config.ASSETS_DIR, "template.jpg")
    if os.path.exists(template_path):
        return Image.open(template_path).convert("RGB").resize(size)

    brand = template["brand"] if template else BRAND_COLOR
    bg = Image.new("RGB", size, brand)
    draw = ImageDraw.Draw(bg)
    for y in range(size[1]):
        shade = int((y / size[1]) * 30)
        r = min(255, brand[0] + shade)
        g = min(255, brand[1] + shade)
        b = min(255, brand[2] + shade + 10)
        draw.line([(0, y), (size[0], y)], fill=(r, g, b))
    return bg


def _speech_bubble(draw, box, fill, tail="bl", radius=36, tail_size=36):
    draw.rounded_rectangle(box, radius=radius, fill=fill)
    x0, y0, x1, y1 = box
    if tail == "bl":
        draw.polygon([(x0 + 50, y1 - 2), (x0 + 50, y1 + tail_size), (x0 + 50 + tail_size, y1 - 2)], fill=fill)
    elif tail == "br":
        draw.polygon([(x1 - 50, y1 - 2), (x1 - 50, y1 + tail_size), (x1 - 50 - tail_size, y1 - 2)], fill=fill)


def _dashed_line(draw, x1, y1, x2, y2, fill, width=4, dash=16, gap=12):
    total = int(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)
    if total == 0:
        return
    dx, dy = (x2 - x1) / total, (y2 - y1) / total
    pos = 0
    while pos < total:
        seg_end = min(pos + dash, total)
        draw.line([(x1 + dx * pos, y1 + dy * pos), (x1 + dx * seg_end, y1 + dy * seg_end)], fill=fill, width=width)
        pos += dash + gap


def _draw_person(draw, cx, top_y, skin, shirt):
    head_r = 52
    draw.ellipse([cx - head_r, top_y, cx + head_r, top_y + 2 * head_r], fill=skin)
    draw.pieslice([cx - head_r - 4, top_y - 14, cx + head_r + 4, top_y + head_r + 6], 180, 360, fill=(35, 25, 20))
    body_top = top_y + 2 * head_r - 6
    body_w, body_h = 150, 130
    draw.rounded_rectangle([cx - body_w // 2, body_top, cx + body_w // 2, body_top + body_h], radius=34, fill=shirt)
    hand_x, hand_y = cx + body_w // 2 + 35, body_top + 10
    draw.line([cx + int(body_w * 0.2), body_top + 8, hand_x, hand_y], fill=shirt, width=20)
    draw.ellipse([hand_x - 16, hand_y - 16, hand_x + 16, hand_y + 16], fill=skin)
    return hand_x, hand_y


def _draw_megaphone(draw, x, y, color):
    draw.polygon([(x, y - 22), (x, y + 22), (x + 95, y + 60), (x + 95, y - 60)], fill=color)
    draw.rectangle([x - 28, y - 14, x, y + 14], fill=color)
    for i in range(3):
        r = 100 + i * 24
        bbox = [x + 95 - r, y - r, x + 95 + r, y + r]
        draw.arc(bbox, -30, 30, fill=color, width=6)
    return x + 95, y


def _draw_rows(draw, x, y, rows, label_font, value_font, chip_color, text_color, wrap_width):
    for label, value in rows:
        draw.rectangle([x, y + 10, x + 14, y + 24], fill=chip_color)
        draw.text((x + 28, y), label.upper(), font=label_font, fill=chip_color)
        y += label_font.size + 14
        wrapped = _wrap(str(value), wrap_width)
        draw.multiline_text((x, y), wrapped, font=value_font, fill=text_color, spacing=8)
        y += value_font.size * (wrapped.count("\n") + 1) + 26
    return y


def _job_rows(job):
    return [
        ("Company", job["company"]),
        ("Location", job["location"]),
        ("Salary", job["salary"]),
        ("Deadline", job["deadline"]),
    ]


def _footer(draw, size, accent, brand, text, pad=70, height=110, font_size=40):
    draw.rectangle([(0, size[1] - height), (size[0], size[1])], fill=accent)
    font = _load_font(font_size, bold=True)
    draw.text((pad, size[1] - height + 20), text, font=font, fill=brand)


# ---------------------------------------------------------------------------
# LAYOUTS — each draws a full, distinctly different design onto (draw, img)
# ---------------------------------------------------------------------------
def _layout_megaphone(draw, img, size, template, job):
    brand, accent, text_color = template["brand"], template["accent"], template["text"]
    pad = 70
    skin = (240, 200, 160)

    hand_x, hand_y = _draw_person(draw, pad + 90, 60, skin, accent)
    mx, my = _draw_megaphone(draw, hand_x + 10, hand_y, text_color)

    bubble_box = [mx + 20, hand_y - 90, size[0] - pad, hand_y + 70]
    _speech_bubble(draw, bubble_box, accent, tail="bl")
    tag_font = _load_font(38, bold=True)
    draw.multiline_text((bubble_box[0] + 30, bubble_box[1] + 28), _wrap(template["tag"], 18),
                         font=tag_font, fill=brand, spacing=8)

    y = hand_y + 150
    title_font = _load_font(64, bold=True)
    title_wrapped = _wrap(job["title"], 22)
    draw.multiline_text((pad, y), title_wrapped, font=title_font, fill=text_color, spacing=14)
    y += title_font.size * (title_wrapped.count("\n") + 1) + 50

    label_font = _load_font(36, bold=True)
    value_font = _load_font(40)
    _draw_rows(draw, pad, y, _job_rows(job), label_font, value_font, accent, text_color, 34)

    _footer(draw, size, accent, brand, template["cta"], pad=pad)


def _layout_chat(draw, img, size, template, job):
    brand, accent, text_color = template["brand"], template["accent"], template["text"]
    pad = 70

    opener_font = _load_font(34)
    bubble1_box = [pad, 90, size[0] - pad - 140, 210]
    _speech_bubble(draw, bubble1_box, (255, 255, 255), tail="bl")
    draw.multiline_text((bubble1_box[0] + 30, bubble1_box[1] + 30), "Suno! Ek naya\njob aaya hai",
                         font=opener_font, fill=(30, 30, 30), spacing=8)

    y2 = bubble1_box[3] + 70
    title_font = _load_font(52, bold=True)
    title_wrapped = _wrap(job["title"], 20)
    lines = title_wrapped.count("\n") + 1
    bubble2_box = [pad + 80, y2, size[0] - pad, y2 + 100 + lines * 66]
    _speech_bubble(draw, bubble2_box, accent, tail="br")
    tag_font = _load_font(30, bold=True)
    draw.text((bubble2_box[0] + 30, bubble2_box[1] + 24), template["tag"], font=tag_font, fill=brand)
    draw.multiline_text((bubble2_box[0] + 30, bubble2_box[1] + 68), title_wrapped,
                         font=title_font, fill=brand, spacing=10)

    y = bubble2_box[3] + 70
    label_font = _load_font(36, bold=True)
    value_font = _load_font(40)
    _draw_rows(draw, pad, y, _job_rows(job), label_font, value_font, accent, text_color, 34)

    _footer(draw, size, accent, brand, template["cta"], pad=pad)


def _layout_badge(draw, img, size, template, job):
    brand, accent, text_color = template["brand"], template["accent"], template["text"]
    pad = 70
    cx, cy, r = size[0] // 2, 220, 140

    draw.polygon([(cx - 90, cy + r - 20), (cx - 40, cy + r + 90), (cx - 10, cy + r - 10)], fill=accent)
    draw.polygon([(cx + 90, cy + r - 20), (cx + 40, cy + r + 90), (cx + 10, cy + r - 10)], fill=accent)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=accent)
    draw.ellipse([cx - r + 18, cy - r + 18, cx + r - 18, cy + r - 18], outline=brand, width=6)
    check_font = _load_font(90, bold=True)
    draw.text((cx, cy), "✔", font=check_font, fill=brand, anchor="mm")

    tag_font = _load_font(38, bold=True)
    draw.text((cx, cy + r + 115), template["tag"], font=tag_font, fill=accent, anchor="ma")

    y = cy + r + 185
    title_font = _load_font(56, bold=True)
    title_wrapped = _wrap(job["title"], 22)
    draw.multiline_text((cx, y), title_wrapped, font=title_font, fill=text_color,
                         spacing=14, align="center", anchor="ma")
    y += title_font.size * (title_wrapped.count("\n") + 1) + 60

    label_font = _load_font(36, bold=True)
    value_font = _load_font(40)
    _draw_rows(draw, pad, y, _job_rows(job), label_font, value_font, accent, text_color, 34)

    _footer(draw, size, accent, brand, template["cta"], pad=pad)


def _layout_ticket(draw, img, size, template, job):
    brand, accent, text_color = template["brand"], template["accent"], template["text"]
    pad = 60
    card = [pad, 80, size[0] - pad, size[1] - 160]
    draw.rounded_rectangle(card, radius=30, fill=(255, 255, 255))

    header_h = 110
    draw.rounded_rectangle([card[0], card[1], card[2], card[1] + header_h], radius=30, fill=accent)
    draw.rectangle([card[0], card[1] + header_h - 30, card[2], card[1] + header_h], fill=accent)
    header_font = _load_font(38, bold=True)
    draw.text((card[0] + 40, card[1] + 36), template["tag"], font=header_font, fill=brand)

    notch_y = card[1] + header_h + 60
    draw.ellipse([card[0] - 24, notch_y - 24, card[0] + 24, notch_y + 24], fill=brand)
    draw.ellipse([card[2] - 24, notch_y - 24, card[2] + 24, notch_y + 24], fill=brand)
    _dashed_line(draw, card[0] + 10, notch_y, card[2] - 10, notch_y, (210, 210, 210), width=4)

    y = notch_y + 50
    title_font = _load_font(52, bold=True)
    title_wrapped = _wrap(job["title"], 22)
    draw.multiline_text((card[0] + 40, y), title_wrapped, font=title_font, fill=(20, 20, 20), spacing=12)
    y += title_font.size * (title_wrapped.count("\n") + 1) + 40

    label_font = _load_font(32, bold=True)
    value_font = _load_font(36)
    _draw_rows(draw, card[0] + 40, y, _job_rows(job), label_font, value_font, brand, (40, 40, 40), 30)

    _footer(draw, size, accent, brand, template["cta"], pad=pad, height=120, font_size=38)


def _layout_billboard(draw, img, size, template, job):
    brand, accent, text_color = template["brand"], template["accent"], template["text"]
    pad = 70

    draw.ellipse([60, 40, 170, 140], fill=(255, 255, 255))
    draw.ellipse([130, 60, 240, 150], fill=(255, 255, 255))
    draw.ellipse([size[0] - 260, 30, size[0] - 150, 130], fill=(255, 255, 255))

    sign_top = 190
    sign_bottom = size[1] - 260
    sign_box = [30, sign_top, size[0] - 30, sign_bottom]
    draw.rectangle(sign_box, fill=brand, outline=accent, width=10)

    pole_w = 40
    draw.rectangle([size[0] // 2 - 160 - pole_w, sign_bottom, size[0] // 2 - 160, size[1] - 60], fill=(90, 70, 50))
    draw.rectangle([size[0] // 2 + 160, sign_bottom, size[0] // 2 + 160 + pole_w, size[1] - 60], fill=(90, 70, 50))

    tag_font = _load_font(38, bold=True)
    draw.text((sign_box[0] + 40, sign_box[1] + 30), template["tag"], font=tag_font, fill=accent)

    y = sign_box[1] + 110
    title_font = _load_font(54, bold=True)
    title_wrapped = _wrap(job["title"], 20)
    draw.multiline_text((sign_box[0] + 40, y), title_wrapped, font=title_font, fill=text_color, spacing=12)
    y += title_font.size * (title_wrapped.count("\n") + 1) + 40

    label_font = _load_font(32, bold=True)
    value_font = _load_font(36)
    _draw_rows(draw, sign_box[0] + 40, y, _job_rows(job), label_font, value_font, accent, text_color, 30)

    footer_font = _load_font(32, bold=True)
    draw.text((pad, size[1] - 50), template["cta"], font=footer_font, fill=accent)


_LAYOUTS = {
    "megaphone": _layout_megaphone,
    "chat": _layout_chat,
    "badge": _layout_badge,
    "ticket": _layout_ticket,
    "billboard": _layout_billboard,
}


def _render(size, template, job):
    img = _background(size, template)
    draw = ImageDraw.Draw(img)
    layout_fn = _LAYOUTS.get(template["layout"], _layout_megaphone)
    layout_fn(draw, img, size, template, job)
    return img


# ---------------------------------------------------------------------------
# Public build functions (called from main.py — signatures unchanged)
# ---------------------------------------------------------------------------
def build_image(job: dict, out_path: str):
    template = get_next_template()
    img = _render(IMG_SIZE, template, job)
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
    Ek frame image (reel size) banate hain us job ke current template se,
    phir uske upar ek "New job alert..." voice-over (gTTS) generate karke
    ffmpeg se image + audio dono ko mila kar ek video bana dete hain.
    Voice-over fail ho to reel silent (bina awaaz) bhi ban jayega — job
    fail nahi hoga.
    """
    template = get_next_template()
    frame_path = out_path.replace(".mp4", "_frame.jpg")

    img = _render(REEL_SIZE, template, job)
    os.makedirs(os.path.dirname(frame_path), exist_ok=True)
    img.save(frame_path, quality=92)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

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
    
