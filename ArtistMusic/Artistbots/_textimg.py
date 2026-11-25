# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Channel      : https://t.me/artistbots
# ==========================================================
#
# Multi-font text renderer for the welcome card.
# NOT a plugin - it has no handlers.
#
# People write their names in every style imaginable (𝓕𝓪𝓷𝓬𝔂, ʟɪᴋᴇ ᴛʜɪs, हिंदी,
# العربية, 한국어, 中文, ꧁༒☬ symbols ☬༒꧂, emoji 😎 ...). A single font cannot
# draw all of that, so every character is drawn with the first bundled font
# that actually contains it.
# ==========================================================

import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path(__file__).parent / "assets" / "fonts"

# Order = priority.  First font that has the character wins.
_TEXT_FONTS = [
    "Arimo.ttf",              # Latin / Greek / Cyrillic (the card's main font)
    "DejaVuSans.ttf",         # Arabic, Hebrew, Armenian, Georgian, symbols, IPA, small caps
    "FreeSans.ttf",           # Devanagari, Bengali, Gujarati, Gurmukhi, Tamil, Malayalam...
    "FreeSerif.ttf",          # Thai, Arabic, Telugu*, Math-alphanumeric (𝓐 𝔸 𝕬 𝒜), more symbols
    "DejaVuMathTeXGyre.ttf",  # Math alphanumeric fallback
    "wqy-zenhei.ttc",         # Chinese / Japanese / Korean
    "unifont.otf",            # Almost every remaining BMP character
    "unifont_upper.otf",      # Almost every remaining character outside the BMP
]
_EMOJI_FONT = "NotoColorEmoji.ttf"
_EMOJI_SIZE = 109  # the only size the bitmap emoji font supports

_VARIATION = {0xFE0E, 0xFE0F}
_ZWJ = 0x200D
_ZERO_WIDTH = {0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x200E, 0x200F, 0x202A, 0x202B,
               0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069}


@lru_cache(maxsize=None)
def _cmap(name: str) -> frozenset:
    try:
        from fontTools.ttLib import TTFont

        f = TTFont(str(FONT_DIR / name), fontNumber=0, lazy=True)
        return frozenset(f.getBestCmap().keys())
    except Exception:
        return frozenset()


@lru_cache(maxsize=256)
def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


def _available(name: str) -> bool:
    return (FONT_DIR / name).exists()


def _is_emoji(cp: int) -> bool:
    return (
        0x1F000 <= cp <= 0x1FAFF
        or 0x2600 <= cp <= 0x27BF
        or 0x2B00 <= cp <= 0x2BFF
        or 0x2190 <= cp <= 0x21FF and cp in (0x2194, 0x2195, 0x21A9, 0x21AA)
        or cp in (0x00A9, 0x00AE, 0x203C, 0x2049, 0x2122, 0x2139, 0x231A, 0x231B, 0x2328,
                  0x23CF, 0x23E9, 0x23EA, 0x23ED, 0x23EE, 0x23EF, 0x23F0, 0x23F1, 0x23F2,
                  0x23F3, 0x23F8, 0x23F9, 0x23FA, 0x24C2, 0x25AA, 0x25AB, 0x25B6, 0x25C0,
                  0x25FB, 0x25FC, 0x25FD, 0x25FE, 0x2934, 0x2935, 0x3030, 0x303D, 0x3297, 0x3299)
    )


def _clusters(text: str) -> list:
    """Split into (base_char, full_cluster_string).  Marks/ZWJ/variation selectors stay attached."""
    out = []
    i, n = 0, len(text)
    while i < n:
        j = i + 1
        # regional-indicator pair = flag
        if 0x1F1E6 <= ord(text[i]) <= 0x1F1FF and j < n and 0x1F1E6 <= ord(text[j]) <= 0x1F1FF:
            j += 1
        while j < n:
            c = ord(text[j])
            if c == _ZWJ and j + 1 < n:
                j += 2
            elif c in _VARIATION or 0x1F3FB <= c <= 0x1F3FF or c == 0x20E3 or unicodedata.combining(text[j]) \
                    or unicodedata.category(text[j]) in ("Mn", "Me", "Mc") or 0xE0020 <= c <= 0xE007F:
                j += 1
            else:
                break
        out.append((text[i], text[i:j]))
        i = j
    return out


def _pick_font(base: str, cluster: str, primary: Optional[str] = None) -> Optional[str]:
    cp = ord(base)
    if cp in _ZERO_WIDTH:
        return None
    wants_emoji = (
        _is_emoji(cp)
        or 0xFE0F in map(ord, cluster)
        or 0x20E3 in map(ord, cluster)
        or 0x1F1E6 <= cp <= 0x1F1FF
    )
    if wants_emoji and _available(_EMOJI_FONT) and (cp in _cmap(_EMOJI_FONT)):
        # text-style symbols (e.g. ☬ ♛ ★) exist in normal fonts and look better in white
        if cp > 0xFFFF or 0xFE0F in map(ord, cluster) or cp < 0x2600 or cp > 0x27BF:
            return _EMOJI_FONT
    if primary and _available(primary) and cp in _cmap(primary):
        return primary
    for name in _TEXT_FONTS:
        if _available(name) and cp in _cmap(name):
            return name
    if _available(_EMOJI_FONT) and cp in _cmap(_EMOJI_FONT):
        return _EMOJI_FONT
    return "__missing__"


def _runs(text: str, primary: Optional[str] = None) -> list:
    """[(font_name, string), ...] merging neighbours that use the same font."""
    runs = []
    for base, cluster in _clusters(text):
        name = _pick_font(base, cluster, primary)
        if name is None:
            continue
        if name == "__missing__":
            # last resort: drop control chars, show a plain placeholder for unknown ones
            if unicodedata.category(base).startswith("C"):
                continue
            name, cluster = _TEXT_FONTS[0], "?"
        if runs and runs[-1][0] == name and name != _EMOJI_FONT:
            runs[-1] = (name, runs[-1][1] + cluster)
        else:
            runs.append((name, cluster))
    return runs


def _render_run(name: str, s: str, size: int, fill):
    """Render one single-font run to an RGBA image (tight to its ink, advance-based width)."""
    if name == _EMOJI_FONT:
        f = _font(name, _EMOJI_SIZE)
        w = max(1, int(f.getlength(s)))
        im = Image.new("RGBA", (w + 8, int(_EMOJI_SIZE * 1.6)), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((0, 0), s, font=f, embedded_color=True)
        bbox = im.getbbox()
        if not bbox:
            return None
        im = im.crop((0, 0, max(bbox[2], w), max(bbox[3], 1)))
        ratio = size * 1.15 / _EMOJI_SIZE
        return im.resize((max(1, round(im.width * ratio)), max(1, round(im.height * ratio))), Image.LANCZOS), "emoji", None

    f = _font(name, size)
    try:
        adv = f.getlength(s)
    except Exception:
        adv = size * len(s)
    asc, desc = f.getmetrics()
    pad = size // 2
    im = Image.new("RGBA", (int(adv) + pad * 2, asc + desc + pad), (0, 0, 0, 0))
    try:
        ImageDraw.Draw(im).text((pad, 0), s, font=f, fill=fill)
    except Exception:
        return None
    return im.crop((pad, 0, pad + max(1, int(adv)), im.height)), "text", asc


def _compose(runs: list, size: int, fill):
    parts = []
    for name, s in runs:
        r = _render_run(name, s, size, fill)
        if r:
            parts.append(r)
    if not parts:
        return None
    # align every run on a common baseline (fonts have different ascents)
    text_asc = [p[2] for p in parts if p[2] is not None]
    base_asc = max(text_asc) if text_asc else int(size * 0.9)
    placed = []
    for im, kind, asc in parts:
        y = base_asc - asc if asc is not None else max(0, base_asc - int(im.height * 0.85))
        placed.append((im, y))
    width = sum(im.width for im, _ in placed)
    height = max(y + im.height for im, y in placed)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    x = 0
    for im, y in placed:
        canvas.paste(im, (x, y), im)
        x += im.width
    return canvas


def draw_text(
    base: Image.Image,
    xy: tuple,
    text: str,
    size: int,
    fill=(242, 242, 242),
    max_width: Optional[int] = None,
    min_size: int = 18,
    primary: Optional[str] = None,
) -> None:
    """Draw `text` onto `base` at xy using per-character font fallback.

    If the text is wider than `max_width` the font size is reduced step by step; if it still
    does not fit at `min_size` the text is cut and finished with "…".
    """
    text = (text or "").replace("\n", " ").strip() or "?"
    runs = _runs(text, primary)
    canvas = None
    cur = size
    while cur >= min_size:
        canvas = _compose(runs, cur, fill)
        if canvas is None or not max_width or canvas.width <= max_width:
            break
        cur -= max(2, cur // 12)

    if canvas is not None and max_width and canvas.width > max_width:
        clusters = _clusters(text)
        while len(clusters) > 1:
            clusters.pop()
            cand = _runs("".join(c for _, c in clusters) + "…", primary)
            canvas = _compose(cand, min_size, fill)
            if canvas and canvas.width <= max_width:
                break

    if canvas is None:
        canvas = _compose(_runs("?", primary), size, fill)
    x, y = xy
    base.paste(canvas, (int(x), int(y)), canvas)
