"""Branded infographic / carousel slides (Pillow). 1080x1350 (4:5), SBM UK navy + green."""
import os, uuid, textwrap
from PIL import Image, ImageDraw, ImageFont

NAVY, NAVY2, GREEN, WHITE, SOFT = (27, 58, 92), (37, 74, 115), (90, 122, 74), (255, 255, 255), (222, 230, 240)
W, H = 1080, 1350
FONTS = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
IMAGE_DIR = os.getenv("IMAGE_DIR", "data/img")


def _f(name, size):
    return ImageFont.truetype(os.path.join(FONTS, f"Poppins-{name}.ttf"), size)


def _wrap(d, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur); cur = w
    return lines + ([cur] if cur else [])


def _base(desk_name):
    im = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 14], fill=GREEN)
    d.rectangle([0, H - 150, W, H], fill=NAVY2)
    d.text((64, H - 112), desk_name, font=_f("Bold", 30), fill=WHITE)
    d.text((64, H - 66), "www.schoolbusinessmanager.uk", font=_f("Regular", 24), fill=SOFT)
    return im, d


def _save(im):
    os.makedirs(IMAGE_DIR, exist_ok=True)
    name = f"{uuid.uuid4().hex}.png"
    im.save(os.path.join(IMAGE_DIR, name), optimize=True)
    return name


def infographic(title, points, desk_name):
    im, d = _base(desk_name)
    d.rounded_rectangle([64, 70, 64 + 230, 118], 24, fill=GREEN)
    d.text((86, 77), "SBM UK  INSIGHT", font=_f("Bold", 24), fill=WHITE)
    y = 160
    for line in _wrap(d, title, _f("Bold", 62), W - 128)[:5]:
        d.text((64, y), line, font=_f("Bold", 62), fill=WHITE); y += 80
    y += 30
    d.line([64, y, 264, y], fill=GREEN, width=8); y += 50
    avail = H - 150 - y - 30
    block = avail // max(1, len(points))
    for i, p in enumerate(points[:4], 1):
        top = y + (i - 1) * block
        d.ellipse([64, top, 64 + 76, top + 76], fill=GREEN)
        d.text((64 + 38, top + 38), str(i), font=_f("Bold", 40), fill=WHITE, anchor="mm")
        lines = _wrap(d, p, _f("Medium", 38), W - 128 - 110)[:3]
        ty = top + 38 - (len(lines) * 50) // 2
        for ln in lines:
            d.text((176, ty), ln, font=_f("Medium", 38), fill=WHITE); ty += 50
    return _save(im)


def carousel(title, points, question, desk_name):
    slides = []
    im, d = _base(desk_name)
    d.rounded_rectangle([64, 70, 294, 118], 24, fill=GREEN)
    d.text((86, 77), "SBM UK  INSIGHT", font=_f("Bold", 24), fill=WHITE)
    y = 380
    for line in _wrap(d, title, _f("Bold", 76), W - 128)[:6]:
        d.text((64, y), line, font=_f("Bold", 76), fill=WHITE); y += 98
    d.text((64, H - 230), "Swipe  >", font=_f("Bold", 34), fill=(160, 200, 140))
    slides.append(_save(im))
    for i, p in enumerate(points[:4], 1):
        im, d = _base(desk_name)
        d.text((64, 110), f"{i}/{min(4, len(points))}", font=_f("Bold", 34), fill=(160, 200, 140))
        d.ellipse([64, 250, 64 + 110, 250 + 110], fill=GREEN)
        d.text((64 + 55, 250 + 55), str(i), font=_f("Bold", 60), fill=WHITE, anchor="mm")
        y = 420
        for ln in _wrap(d, p, _f("Bold", 58), W - 128)[:7]:
            d.text((64, y), ln, font=_f("Bold", 58), fill=WHITE); y += 78
        slides.append(_save(im))
    im, d = _base(desk_name)
    d.text((64, 300), "Over to you", font=_f("Bold", 80), fill=(160, 200, 140))
    y = 450
    for ln in _wrap(d, question, _f("Medium", 52), W - 128)[:7]:
        d.text((64, y), ln, font=_f("Medium", 52), fill=WHITE); y += 72
    d.text((64, H - 240), "Share your answer in the comments", font=_f("Regular", 32), fill=SOFT)
    slides.append(_save(im))
    return slides
