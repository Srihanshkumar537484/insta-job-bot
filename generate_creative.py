"""
generate_creative.py
Job dict se ek Instagram-ready IMAGE (1080x1350) aur REEL (1080x1920, ~8 sec)
banata hai. Pure Pillow + FFmpeg se — koi paid API nahi chahiye.

Agar tumhare paas apna background template (PNG/JPG) hai, use
assets/template.jpg me rakh do — code usko automatically use karega.
Nahi hai to code khud ek plain gradient background bana lega.
"""

import os
import subprocess
import textwrap

from PIL import Image, ImageDraw, ImageFont

import config

IMG_SIZE = (1080, 1350)     # feed post size
REEL_SIZE = (1080, 1920)    # reel/story size
REEL_DURATION = 8           # seconds

BRAND_COLOR = (20, 20, 30)
ACCENT_COLOR = (255, 200, 0)
TEXT_COLOR = (255, 255, 255)


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


def _background(size):
    template_path = os.path.join(config.ASSETS_DIR, "template.jpg")
    if os.path.exists(template_path):
        bg = Image.open(template_path).convert("RGB").resize(size)
    else:
        bg = Image.new("RGB", size, BRAND_COLOR)
        draw = ImageDraw.Draw(bg)
        # simple diagonal-ish gradient band for visual interest
        for y in range(size[1]):
            shade = int(20 + (y / size[1]) * 25)
            draw.line([(0, y), (size[0], y)], fill=(shade, shade, shade + 15))
    return bg


def _wrap(text, width):
    return "\n".join(textwrap.wrap(text, width=width))


def build_image(job: dict, out_path: str):
    img = _background(IMG_SIZE)
    draw = ImageDraw.Draw(img)

    pad = 70
    y = 120

    tag_font = _load_font(42, bold=True)
    title_font = _load_font(64, bold=True)
    label_font = _load_font(38, bold=True)
    value_font = _load_font(40)

    draw.text((pad, y), "🔥 NEW JOB ALERT", font=tag_font, fill=ACCENT_COLOR)
    y += 100

    title_wrapped = _wrap(job["title"], 22)
    draw.multiline_text((pad, y), title_wrapped, font=title_font, fill=TEXT_COLOR, spacing=14)
    y += title_font.size * (title_wrapped.count("\n") + 1) + 60

    rows = [
        ("Company", job["company"]),
        ("Location", job["location"]),
        ("Salary", job["salary"]),
        ("Deadline", job["deadline"]),
    ]
    for label, value in rows:
        draw.text((pad, y), label.upper(), font=label_font, fill=ACCENT_COLOR)
        y += 48
        draw.multiline_text((pad, y), _wrap(str(value), 34), font=value_font, fill=TEXT_COLOR)
        y += value_font.size * 2 + 30

    draw.rectangle([(0, IMG_SIZE[1] - 110), (IMG_SIZE[0], IMG_SIZE[1])], fill=ACCENT_COLOR)
    cta_font = _load_font(40, bold=True)
    draw.text((pad, IMG_SIZE[1] - 90), "Apply link in bio / comments →",
              font=cta_font, fill=BRAND_COLOR)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, quality=92)
    return out_path


def build_reel(job: dict, out_path: str):
    """
    Static-image-style reel: background + text overlay, FFmpeg se render.
    Pehle ek frame image Pillow se banate hain (build_image jaisa but reel size),
    phir ffmpeg se uss image ko N second ka video bana dete hain.
    """
    frame_path = out_path.replace(".mp4", "_frame.jpg")

    img = _background(REEL_SIZE)
    draw = ImageDraw.Draw(img)

    pad = 70
    y = 260

    tag_font = _load_font(46, bold=True)
    title_font = _load_font(72, bold=True)
    label_font = _load_font(42, bold=True)
    value_font = _load_font(44)

    draw.text((pad, y), "🔥 NEW JOB ALERT", font=tag_font, fill=ACCENT_COLOR)
    y += 120

    title_wrapped = _wrap(job["title"], 20)
    draw.multiline_text((pad, y), title_wrapped, font=title_font, fill=TEXT_COLOR, spacing=16)
    y += title_font.size * (title_wrapped.count("\n") + 1) + 80

    rows = [
        ("Company", job["company"]),
        ("Location", job["location"]),
        ("Salary", job["salary"]),
        ("Deadline", job["deadline"]),
    ]
    for label, value in rows:
        draw.text((pad, y), label.upper(), font=label_font, fill=ACCENT_COLOR)
        y += 52
        draw.multiline_text((pad, y), _wrap(str(value), 30), font=value_font, fill=TEXT_COLOR)
        y += value_font.size * 2 + 40

    draw.rectangle([(0, REEL_SIZE[1] - 130), (REEL_SIZE[0], REEL_SIZE[1])], fill=ACCENT_COLOR)
    cta_font = _load_font(44, bold=True)
    draw.text((pad, REEL_SIZE[1] - 105), "Apply link in bio / comments →",
              font=cta_font, fill=BRAND_COLOR)

    os.makedirs(os.path.dirname(frame_path), exist_ok=True)
    img.save(frame_path, quality=92)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    # loop the still frame into a short silent mp4 (Instagram Reels accept this)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", frame_path,
        "-c:v", "libx264",
        "-t", str(REEL_DURATION),
        "-pix_fmt", "yuv420p",
        "-vf", f"scale={REEL_SIZE[0]}:{REEL_SIZE[1]}",
        out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    os.remove(frame_path)
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
