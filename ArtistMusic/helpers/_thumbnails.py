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
BRAND_TEXT = "ArtistBots"
WHITE = (255, 255, 255, 255)
SOFT_WHITE = (255, 255, 255, 190)
RED_COLOR = (230, 57, 53, 255)
ACCENT_COLOR = (255, 196, 61, 255)

# fonts (bundled first, system fallbacks after)
BOLD_FONTS = [
    "ArtistMusic/helpers/Raleway-Bold.ttf",
    "ArtistMusic/helpers/DejaVuSans-Bold.ttf",
]
LIGHT_FONTS = [
    "ArtistMusic/helpers/Inter-Light.ttf",
    "ArtistMusic/helpers/DejaVuSans-Bold.ttf",
]
# used when title has Hindi / CJK / other non-latin characters
UNICODE_FONTS = [
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "ArtistMusic/helpers/DejaVuSans-Bold.ttf",
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

    async def save_thumb(self, output_path: str, url: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                with open(output_path, "wb") as f:
                    f.write(await resp.read())
        return output_path

    async def generate(self, song: Track, size=SIZE) -> str:
        try:
            temp = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}_v2.png"
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
        """Blurred, darkened, colour-rich version of the cover as backdrop."""
        w, h = size
        ratio = max(w / cover.width, h / cover.height)
        bg = cover.resize((int(cover.width * ratio), int(cover.height * ratio)), Image.LANCZOS)
        left, top = (bg.width - w) // 2, (bg.height - h) // 2
        bg = bg.crop((left, top, left + w, top + h)).convert("RGB")
        bg = bg.filter(ImageFilter.GaussianBlur(38))
        bg = ImageEnhance.Color(bg).enhance(1.35)
        bg = ImageEnhance.Brightness(bg).enhance(0.55)
        bg = bg.convert("RGBA")

        # left-to-right dark vignette so the text side stays readable
        grad = Image.new("L", (w, 1), 0)
        for x in range(w):
            grad.putpixel((x, 0), int(40 + 90 * (x / w)))
        shade = Image.new("RGBA", size, (0, 0, 0, 0))
        shade.putalpha(grad.resize(size))
        bg.alpha_composite(shade)
        return bg

    def _draw_cover(self, bg: Image.Image, cover: Image.Image, accent):
        # show the WHOLE thumbnail (no crop): fit inside a max box, keep aspect ratio
        max_w, max_h = 590, 420
        scale = min(max_w / cover.width, max_h / cover.height)
        aw, ah = int(cover.width * scale), int(cover.height * scale)
        x, y = 60, (SIZE[1] - ah) // 2 + 10
        radius = 32

        # coloured glow behind the art
        glow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle(
            (x - 6, y - 6, x + aw + 6, y + ah + 6), radius=radius + 6, fill=accent + (170,)
        )
        glow = glow.filter(ImageFilter.GaussianBlur(40))
        bg.alpha_composite(glow)

        # drop shadow
        shadow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle(
            (x + 8, y + 18, x + aw + 8, y + ah + 18), radius=radius, fill=(0, 0, 0, 170)
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(22))
        bg.alpha_composite(shadow)

        art = cover.resize((aw, ah), Image.LANCZOS).convert("RGBA")
        bg.paste(art, (x, y), _rounded_mask((aw, ah), radius))

        # thin glass border
        border = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        ImageDraw.Draw(border).rounded_rectangle(
            (x, y, x + aw, y + ah), radius=radius, outline=(255, 255, 255, 90), width=2
        )
        bg.alpha_composite(border)
        return x + aw

    def _draw_brand(self, bg: Image.Image):
        """Small glass pill with the bot name, top-right."""
        draw = ImageDraw.Draw(bg, "RGBA")
        text = BRAND_TEXT
        tw = draw.textlength(text, font=self.brand_font)
        pad_x, h = 26, 52
        dot = 14
        pw = int(tw + pad_x * 2 + dot + 12)
        x1 = SIZE[0] - 50
        x0 = x1 - pw
        y0 = 40

        layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.rounded_rectangle((x0, y0, x1, y0 + h), radius=h // 2, fill=(255, 255, 255, 38),
                             outline=(255, 255, 255, 80), width=2)
        bg.alpha_composite(layer)

        draw = ImageDraw.Draw(bg, "RGBA")
        cy = y0 + h // 2
        draw.ellipse((x0 + pad_x, cy - dot // 2, x0 + pad_x + dot, cy + dot // 2), fill=RED_COLOR)
        draw.text((x0 + pad_x + dot + 12, cy), text, font=self.brand_font, fill=WHITE, anchor="lm")
        return bg

    def _draw_controls(self, draw, cx, cy, accent):
        """prev / play / next icons drawn with shapes (no emoji fonts needed)."""
        r = 38
        # play button (filled circle + triangle)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=WHITE)
        draw.polygon([(cx - 12, cy - 20), (cx - 12, cy + 20), (cx + 22, cy)], fill=(20, 20, 20, 255))
        # previous
        px = cx - 120
        draw.polygon([(px + 18, cy - 18), (px + 18, cy + 18), (px - 8, cy)], fill=WHITE)
        draw.rectangle((px - 14, cy - 18, px - 9, cy + 18), fill=WHITE)
        # next
        nx = cx + 120
        draw.polygon([(nx - 18, cy - 18), (nx - 18, cy + 18), (nx + 8, cy)], fill=WHITE)
        draw.rectangle((nx + 9, cy - 18, nx + 14, cy + 18), fill=WHITE)

    # --------------------------------------------------------------- main
    def _generate_sync(
        self,
        temp: str,
        output: str,
        song: Track,
        size=SIZE
    ) -> str:
        try:
            with Image.open(temp) as temp_img:
                cover = temp_img.convert("RGB")

            accent = _dominant_accent(cover)
            bg = self._background(cover, size)
            art_right = self._draw_cover(bg, cover, accent)
            bg = self._draw_brand(bg)

            draw = ImageDraw.Draw(bg, "RGBA")
            tx = art_right + 60
            max_w = size[0] - tx - 50
            title = (song.title or "Unknown Title").strip()
            title = re.sub(r"\s+", " ", title)

            # "NOW PLAYING" tag
            tag = "NOW PLAYING"
            tag_w = int(draw.textlength(tag, font=self.tag_font)) + 44
            ty = 150
            tag_layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
            ImageDraw.Draw(tag_layer).rounded_rectangle(
                (tx, ty, tx + tag_w, ty + 42), radius=21, fill=accent + (235,)
            )
            bg.alpha_composite(tag_layer)
            bg = bg.convert("RGB")  # RGB so semi-transparent fills blend properly
            draw = ImageDraw.Draw(bg, "RGBA")
            lum = 0.299 * accent[0] + 0.587 * accent[1] + 0.114 * accent[2]
            tag_color = (15, 15, 15, 255) if lum > 140 else WHITE
            draw.text((tx + tag_w // 2, ty + 21), tag, font=self.tag_font, fill=tag_color, anchor="mm")

            # title (max 2 lines)
            tfont = self.title_font if _is_latin(title) else self.title_font_uni
            lines = _wrap_two_lines(draw, title, tfont, max_w)
            y = ty + 76
            for ln in lines:
                draw.text((tx + 3, y + 3), ln, font=tfont, fill=(0, 0, 0, 120))
                draw.text((tx, y), ln, font=tfont, fill=WHITE)
                y += 68

            # artist / channel
            artist = _fit_text(draw, (song.channel_name or "Unknown Artist").strip(),
                               self.artist_font if _is_latin(song.channel_name or "") else self.title_font_uni,
                               max_w)
            y += 6
            draw.text((tx, y), artist,
                      font=self.artist_font if _is_latin(artist) else self.title_font_uni,
                      fill=SOFT_WHITE)

            # views (optional)
            if song.view_count:
                y += 46
                draw.text((tx, y), f"{song.view_count}", font=self.small_font, fill=(255, 255, 255, 140))

            # progress bar
            bar_y = 535
            bar_h = 8
            draw.rounded_rectangle((tx, bar_y, tx + max_w, bar_y + bar_h), radius=4, fill=(255, 255, 255, 70))
            fill_w = int(max_w * 0.08)
            draw.rounded_rectangle((tx, bar_y, tx + fill_w, bar_y + bar_h), radius=4, fill=accent + (255,))
            draw.ellipse((tx + fill_w - 10, bar_y + bar_h // 2 - 10, tx + fill_w + 10, bar_y + bar_h // 2 + 10),
                         fill=WHITE)

            # timestamps
            draw.text((tx, bar_y + 26), "00:00", font=self.small_font, fill=(255, 255, 255, 170))
            dur = "LIVE" if song.is_live else (song.duration or "--:--")
            draw.text((tx + max_w, bar_y + 26), str(dur), font=self.small_font,
                      fill=(255, 255, 255, 170), anchor="ra")

            # controls
            self._draw_controls(draw, tx + max_w // 2, 640, accent)

            bg.convert("RGB").save(output, quality=95)
            try:
                os.remove(temp)
            except OSError:
                pass
            return output
        except Exception:
            return config.DEFAULT_THUMB
