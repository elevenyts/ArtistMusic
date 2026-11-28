# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Type         : API Based Telegram Music Bot
#
# Bot          : @ArtistApibot
# Channel      : https://t.me/artistbots
# GitHub       : https://github.com/elevenyts/ArtistMusic
#
# Unauthorized copying, modification, or redistribution
# of this source code without permission is prohibited.
# ==========================================================
import os
import re
import asyncio
import aiohttp
from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
    ImageStat,
)
from ArtistMusic import config
from ArtistMusic.helpers import Track

SIZE = (1280, 720)
BRAND_TEXT = "SMARTXMUSIC"
WHITE = (255, 255, 255, 255)
SOFT_WHITE = (255, 255, 255, 190)
RED_COLOR = (230, 57, 53, 255)
ACCENT_COLOR = (255, 196, 61, 255)

# all bundled assets live in ArtistMusic/Artist_assets/
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Artist_assets")
FONT_DIR = os.path.join(ASSETS_DIR, "fonts")

# fonts (bundled first, system fallbacks after)
BOLD_FONTS = [
    os.path.join(FONT_DIR, "Raleway-Bold.ttf"),
    os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf"),
]
LIGHT_FONTS = [
    os.path.join(FONT_DIR, "Inter-Light.ttf"),
    os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf"),
]
# used when title has Hindi / CJK / other non-latin characters
UNICODE_FONTS = [
    # bundled Hindi / Devanagari-capable font (works even if the server has no system fonts)
    os.path.join(FONT_DIR, "FreeSansBold.ttf"),
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf"),
]


def _load_font(paths, size):
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _is_latin(text: str) -> bool:
    return all(ord(c) < 0x250 or not c.isalpha() for c in text)


def _fit_text(draw, text, font, max_w):
    """Trim text with an ellipsis so it fits in max_w pixels."""
    if draw.textlength(text, font=font) <= max_w:
        return text
    while text and draw.textlength(text + "…", font=font) > max_w:
        text = text[:-1]
    if " " in text:  # prefer cutting at a word boundary
        text = text.rsplit(" ", 1)[0]
    return text.rstrip(" -|,(") + "…"


def _wrap_two_lines(draw, text, font, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
        if len(lines) == 2:
            break
    if len(lines) < 2 and cur:
        lines.append(cur)
    lines = lines[:2]
    # anything left over (or a single huge word) gets an ellipsis on the last line
    if " ".join(lines) != text.strip() and lines:
        lines[-1] = _fit_text(draw, lines[-1] + " …", font, max_w)
    return [_fit_text(draw, ln, font, max_w) for ln in lines] or [""]


def _rounded_mask(size, radius):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return m


def _dominant_accent(img: Image.Image):
    """Pick a vivid accent colour from the cover (used for progress bar / glow)."""
    small = img.convert("RGB").resize((48, 48))
    small = ImageEnhance.Color(small).enhance(2.0)
    best, best_score = (255, 196, 61), -1
    for (r, g, b) in small.getdata():
        mx, mn = max(r, g, b), min(r, g, b)
        sat = (mx - mn) / (mx + 1)
        score = sat * (mx / 255)
        if score > best_score and mx > 110:
            best, best_score = (r, g, b), score
    return best


class Thumbnail:
    def __init__(self):
        self.title_font = _load_font(BOLD_FONTS, 54)
        self.title_font_uni = _load_font(UNICODE_FONTS, 50)
        self.artist_font = _load_font(LIGHT_FONTS, 34)
        self.small_font = _load_font(BOLD_FONTS, 26)
        self.brand_font = _load_font(BOLD_FONTS, 28)
        self.tag_font = _load_font(BOLD_FONTS, 22)
        self.info_font = _load_font(BOLD_FONTS, 30)
        self.line_font = _load_font(LIGHT_FONTS, 27)
        self.time_font = _load_font(BOLD_FONTS, 28)
        self.uni_small = _load_font(UNICODE_FONTS, 28)

    async def save_thumb(self, output_path: str, url: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                with open(output_path, "wb") as f:
                    f.write(await resp.read())
        return output_path

    async def generate(self, song: Track, size=SIZE) -> str:
        try:
            temp = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}_v3.png"
            if os.path.exists(output):
                return output
            await self.save_thumb(temp, song.thumbnail)
            return await asyncio.get_event_loop().run_in_executor(
                None,
                self._generate_sync,
                temp,
                output,
                song,
                size
            )
        except Exception:
            return config.DEFAULT_THUMB

    # ------------------------------------------------------------------ helpers
    def _background(self, cover: Image.Image, size):
        """Blurred, darkened backdrop built from the cover itself."""
        w, h = size
        ratio = max(w / cover.width, h / cover.height)
        bg = cover.resize((int(cover.width * ratio), int(cover.height * ratio)), Image.LANCZOS)
        left, top = (bg.width - w) // 2, (bg.height - h) // 2
        bg = bg.crop((left, top, left + w, top + h)).convert("RGB")
        bg = bg.filter(ImageFilter.GaussianBlur(30))
        bg = ImageEnhance.Color(bg).enhance(1.3)
        bg = ImageEnhance.Brightness(bg).enhance(0.6)
        bg = bg.convert("RGBA")

        # bottom fade so the text/progress area is always readable
        fade = Image.new("L", (1, h), 0)
        start = int(h * 0.68)
        for y in range(start, h):
            fade.putpixel((0, y), int(185 * ((y - start) / (h - start))))
        shade = Image.new("RGBA", size, (0, 0, 0, 0))
        shade.putalpha(fade.resize(size))
        bg.alpha_composite(shade)
        return bg

    def _draw_cover(self, bg: Image.Image, cover: Image.Image, accent):
        # whole thumbnail (no crop), fitted into the big top box
        max_w, max_h = 740, 400
        scale = min(max_w / cover.width, max_h / cover.height)
        aw, ah = int(cover.width * scale), int(cover.height * scale)
        x, y = (SIZE[0] - (aw + 250)) // 2, 30 + (max_h - ah) // 2
        radius = 44

        shadow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle(
            (x + 4, y + 16, x + aw + 4, y + ah + 16), radius=radius, fill=(0, 0, 0, 150))
        bg.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(24)))

        art = cover.resize((aw, ah), Image.LANCZOS).convert("RGBA")
        bg.paste(art, (x, y), _rounded_mask((aw, ah), radius))
        return x, y, aw, ah

    def _draw_brand(self, bg: Image.Image, cy, x0=900):
        """Bot-name watermark pill (red dot + name), right of the cover."""
        text = BRAND_TEXT
        draw = ImageDraw.Draw(bg, "RGBA")
        tw = draw.textlength(text, font=self.brand_font)
        pad_x, h, dot = 24, 52, 14
        pw = int(tw + pad_x * 2 + dot + 12)
        y0 = int(cy - h / 2)
        layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).rounded_rectangle((x0, y0, x0 + pw, y0 + h), radius=h // 2,
                                                fill=(255, 255, 255, 38), outline=(255, 255, 255, 80), width=2)
        bg.alpha_composite(layer)
        draw = ImageDraw.Draw(bg, "RGBA")
        draw.ellipse((x0 + pad_x, cy - dot // 2, x0 + pad_x + dot, cy + dot // 2), fill=RED_COLOR)
        draw.text((x0 + pad_x + dot + 12, cy), text, font=self.brand_font, fill=WHITE, anchor="lm")

    # --------------------------------------------------------------- main
    def _generate_sync(self, temp: str, output: str, song: Track, size=SIZE) -> str:
        try:
            with Image.open(temp) as temp_img:
                cover = temp_img.convert("RGB")

            accent = _dominant_accent(cover)
            bg = self._background(cover, size)
            x, y, aw, ah = self._draw_cover(bg, cover, accent)
            self._draw_brand(bg, y + ah // 2, x + aw + 40)
            bg = bg.convert("RGB")
            draw = ImageDraw.Draw(bg, "RGBA")

            left, right = 50, size[0] - 67
            full_w = right - left

            channel = re.sub(r"\s+", " ", (song.channel_name or "Unknown Artist").strip())
            title = re.sub(r"\s+", " ", (song.title or "Unknown Title").strip())
            info = f"{channel} | {song.view_count}" if song.view_count else channel
            ifont = self.info_font if _is_latin(info) else self.uni_small
            tfont = self.title_font if _is_latin(title) else self.title_font_uni
            tfont = _load_font(BOLD_FONTS if _is_latin(title) else UNICODE_FONTS, 38)

            # title (single line, centred) + channel right under the thumbnail
            mid = size[0] // 2
            title = _fit_text(draw, title, tfont, full_w)
            draw.text((mid + 2, 487), title, font=tfont, fill=(0, 0, 0, 130), anchor="mm")
            draw.text((mid, 485), title, font=tfont, fill=WHITE, anchor="mm")

            # controls: prev / pause / next
            cx, cy = size[0] // 2, 568
            px = cx - 120
            draw.polygon([(px + 18, cy - 21), (px + 18, cy + 21), (px - 17, cy)], fill=WHITE)
            draw.rounded_rectangle((cx - 17, cy - 24, cx - 4, cy + 24), radius=6, fill=WHITE)
            draw.rounded_rectangle((cx + 4, cy - 24, cx + 17, cy + 24), radius=6, fill=WHITE)
            nx = cx + 120
            draw.polygon([(nx - 18, cy - 21), (nx - 18, cy + 21), (nx + 17, cy)], fill=WHITE)

            # times + thin full-width progress line
            dur = "LIVE" if song.is_live else str(song.duration or "--:--")
            draw.text((left, 628), "00:00", font=self.time_font, fill=(255, 255, 255, 235), anchor="lm")
            draw.text((right, 628), dur, font=self.time_font, fill=(255, 255, 255, 235), anchor="rm")
            by = 665
            draw.rounded_rectangle((left, by - 2, right, by + 2), radius=2, fill=(255, 255, 255, 235))
            draw.rounded_rectangle((left, by - 2, left + 14, by + 2), radius=2, fill=accent + (255,))

            bg.convert("RGB").save(output, quality=95)
            try:
                os.remove(temp)
            except OSError:
                pass
            return output
        except Exception:
            return config.DEFAULT_THUMB
