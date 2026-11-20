# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Channel      : https://t.me/artistbots
#
# Plugin       : Group welcome card (image + info + colored buttons)
# Location     : ArtistMusic/Artistbots/welcome.py
# ==========================================================

import asyncio
import html
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import aiohttp
from PIL import Image, ImageChops, ImageDraw, ImageOps
from pyrogram import enums, filters
from pyrogram.errors import TopicClosed
from pyrogram.types import (
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from ArtistMusic import app, config, db, logger

from ._textimg import draw_text

# ─────────────────────────── PATHS ───────────────────────────
_BASE = Path(__file__).parent / "assets"
CARD_PATH = str(_BASE / "welcome_card.png")  # blank 1672x941 template (avatar/name/id/username filled in code)
FALLBACK_PIC = str(_BASE / "upic.png")

# ─────────────────────────── TEXT ────────────────────────────
BTN_VIEW = "ᴠɪєᴡ ϻєϻʙєʀ"
BTN_ADD = "ᴧᴅᴅ ϻє ᴛσ ʏσυʀ ɢʀσυᴘ"

CAPTION_TXT = """✨❄───✧ <b>ᴡᴇʟᴄᴏᴍᴇ</b> ✧───❄✨
🥀 <b>{chat_title}</b> 🥀

╔═══════════════════╗
║ 👤 <b>Nᴀᴍᴇ</b> : {mention}
║ 🆔 <b>Iᴅ</b> : <code>{uid}</code>
║ 🔗 <b>Usᴇʀɴᴀᴍᴇ</b> : @{uname}
║ 🌐 <b>Tᴏᴛᴀʟ Mᴇᴍʙᴇʀs</b> : {count}
╚═══════════════════╝

❄✦─────❅💖💖✦─────✦❄"""

# ─────────────────────── ANTI-SPAM SETTINGS ───────────────────────
JOIN_THRESHOLD = 20   # joins inside TIME_WINDOW => treated as a raid
TIME_WINDOW = 10      # seconds
COOL_MINUTES = 5      # base cooldown
WELCOME_LIMIT = 5     # keep only the last N welcome messages per chat

last_messages: dict[int, list] = {}


# ═══════════════════════════════════════════════════════════
#  DATABASE  (uses the bot's existing MongoDB connection)
# ═══════════════════════════════════════════════════════════
def _col():
    return db.db.welcome


async def is_on(chat_id: int) -> bool:
    doc = await _col().find_one({"_id": chat_id}, {"state": 1})
    return (doc or {}).get("state", "on") == "on"


async def set_state(chat_id: int, flag: str) -> None:
    if flag not in ("on", "off"):
        raise ValueError("flag must be 'on' or 'off'")
    update = {"$set": {"state": flag}}
    if flag == "on":
        update["$unset"] = {"cool_until": ""}
    await _col().update_one({"_id": chat_id}, update, upsert=True)


async def bump(chat_id: int, time_window: int = 8) -> int:
    now = datetime.now(timezone.utc)
    doc = await _col().find_one({"_id": chat_id}, {"last_ts": 1, "join_cnt": 1})
    last_ts: Optional[datetime] = doc.get("last_ts") if doc else None

    if last_ts and last_ts.tzinfo is None:
        last_ts = last_ts.replace(tzinfo=timezone.utc)

    if last_ts and (now - last_ts).total_seconds() <= time_window:
        cnt = int(doc.get("join_cnt") or 0) + 1
    else:
        cnt = 1

    await _col().update_one(
        {"_id": chat_id},
        {"$set": {"last_ts": now, "join_cnt": cnt}},
        upsert=True,
    )
    return cnt


async def cool(chat_id: int, cool_minutes: int = 10) -> None:
    now = datetime.now(timezone.utc)
    await _col().update_one(
        {"_id": chat_id},
        {"$set": {"state": "off", "cool_until": now + timedelta(minutes=cool_minutes)}},
        upsert=True,
    )


async def auto_on(chat_id: int) -> bool:
    """Re-enable welcome after an anti-raid cooldown has expired."""
    now = datetime.now(timezone.utc)
    doc = await _col().find_one({"_id": chat_id}, {"cool_until": 1})
    cool_until: Optional[datetime] = (doc or {}).get("cool_until")

    if cool_until and cool_until.tzinfo is None:
        cool_until = cool_until.replace(tzinfo=timezone.utc)

    if cool_until and now >= cool_until:
        await _col().update_one(
            {"_id": chat_id},
            {"$set": {"state": "on"}, "$unset": {"cool_until": ""}},
            upsert=True,
        )
        return True
    return False


# ═══════════════════════════════════════════════════════════
#  COLORED BUTTONS  (Bot API HTTP, falls back to normal buttons)
# ═══════════════════════════════════════════════════════════
_http: Optional[aiohttp.ClientSession] = None


def _get_session() -> aiohttp.ClientSession:
    """One shared session for Bot API calls (keeps the connection warm)."""
    global _http
    if _http is None or _http.closed:
        _http = aiohttp.ClientSession()
    return _http


def styled_button(text: str, url: str, style: str = None) -> dict:
    btn = {"text": text, "url": url}
    if style:
        btn["style"] = style  # "primary" (blue) | "success" (green) | "danger" (red)
    return btn


def _to_markup(buttons: list[list[dict]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(b["text"], url=b["url"]) for b in row] for row in buttons]
    )


async def _send_media_colored(chat_id: int, path: str, caption: str, buttons: list[list[dict]]):
    """Send a local photo through the Bot API so the buttons keep their colors.

    Returns {"chat_id", "message_id"} on success, None on failure.
    """
    if not config.BOT_TOKEN:
        return None

    method, field, fname, ctype = "sendPhoto", "photo", "welcome.png", "image/png"
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/{method}"
    try:
        import json

        form = aiohttp.FormData()
        form.add_field("chat_id", str(chat_id))
        form.add_field("caption", caption)
        form.add_field("parse_mode", "HTML")
        form.add_field("reply_markup", json.dumps({"inline_keyboard": buttons}))
        with open(path, "rb") as f:
            form.add_field(field, f.read(), filename=fname, content_type=ctype)

        timeout = aiohttp.ClientTimeout(total=30, connect=8)
        session = _get_session()
        async with session.post(url, data=form, timeout=timeout) as resp:
            data = await resp.json()
        if data.get("ok"):
            res = data["result"]
            return {"chat_id": res["chat"]["id"], "message_id": res["message_id"]}
        logger.warning(f"Welcome colored send failed: {data.get('description')}")
    except Exception as e:
        logger.warning(f"Welcome colored send error: {e}")
    return None


# ═══════════════════════════════════════════════════════════
#  IMAGE
# ═══════════════════════════════════════════════════════════
def _cooldown_minutes(burst: int, threshold: int = JOIN_THRESHOLD, base: int = COOL_MINUTES) -> int:
    if burst < threshold:
        return 0
    extra = max(0, burst - threshold)
    return min(60, base + extra * 2)


def _circle(im: Image.Image, d: int) -> Image.Image:
    """Square-crop (no stretching) and cut to a smooth circle of diameter d."""
    im = ImageOps.fit(im.convert("RGB"), (d, d), Image.LANCZOS).convert("RGBA")
    k = 4
    mask = Image.new("L", (d * k, d * k), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, d * k - 1, d * k - 1), fill=255)
    im.putalpha(mask.resize((d, d), Image.LANCZOS))
    return im


# ─────────────────────── CARD RENDERING ───────────────────────
# The artwork (glass card, ring, JOINED badge, ID / @ pills, brand) is the ready-made PNG.
# We only fill in: profile photo, name (gradient), user id and username.
# Coordinates are for the 1672x941 template.
AV_CENTER = (424, 435)   # centre of the dark disc inside the rainbow ring
AV_RADIUS = 176          # photo radius (covers the placeholder silhouette)
BADGE_BOX = (326, 570, 524, 632)  # "JOINED" pill - restored on top of the photo
BADGE_RADIUS = 31
NAME_X, NAME_CAP_TOP, NAME_SIZE, NAME_MAXW = 704, 385, 76, 600
ID_X, ID_CAP_TOP, USER_CAP_TOP, ROW_SIZE, ROW_MAXW = 840, 523, 624, 37, 600
FONT_NAME, FONT_ROW = "Poppins-Bold.ttf", "Poppins-Medium.ttf"
TEXT_DARK = (34, 30, 72, 255)
NAME_GRAD = ((92, 70, 226), (150, 72, 232), (214, 62, 172))  # blue-violet -> violet -> pink


def _cap_offset(size: int, font: str) -> int:
    """Pixels between the top of a draw_text() canvas and the top of a capital letter."""
    probe = Image.new("RGBA", (size * 3, size * 3), (0, 0, 0, 0))
    draw_text(probe, (0, 0), "H", size, fill=(255, 255, 255, 255), primary=font)
    return probe.getbbox()[1]


def _put_text(img, x, cap_top, text, size, maxw, font, fill=None, gradient=None):
    """Draw text so that the capital-letter top sits on `cap_top`.  fill = solid colour, gradient = colour stops."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    off = _cap_offset(size, font)
    draw_text(layer, (x, cap_top - off), text, size, fill=(255, 255, 255, 255), max_width=maxw, min_size=24, primary=font)
    bbox = layer.getbbox()
    if not bbox:
        return
    if gradient:
        w = max(1, bbox[2] - bbox[0])
        strip = Image.new("RGB", (w, 1))
        for i in range(w):
            u = i / max(1, w - 1) * (len(gradient) - 1)
            k = min(int(u), len(gradient) - 2)
            c = [round(gradient[k][j] + (gradient[k + 1][j] - gradient[k][j]) * (u - k)) for j in range(3)]
            strip.putpixel((i, 0), tuple(c))
        tint = Image.new("RGB", img.size, (255, 255, 255))
        tint.paste(strip.resize((w, img.height)), (bbox[0], 0))
    else:
        tint = Image.new("RGB", img.size, fill[:3])
    # multiply keeps coloured emoji looking right while plain letters take the tint
    rgb = ImageChops.multiply(layer.convert("RGB"), tint)
    layer = Image.merge("RGBA", (*rgb.split(), layer.getchannel("A")))
    img.alpha_composite(layer)


def _badge_mask(size: tuple) -> Image.Image:
    k = 4
    x0, y0, x1, y1 = BADGE_BOX
    m = Image.new("L", (size[0] * k, size[1] * k), 0)
    ImageDraw.Draw(m).rounded_rectangle((x0 * k, y0 * k, x1 * k, y1 * k), radius=BADGE_RADIUS * k, fill=255)
    return m.resize(size, Image.LANCZOS)


def build_pic(av: str, fn: str, uid: int, un: str) -> str:
    """Welcome card PNG: template + profile photo + name / id / username."""
    card = Image.open(CARD_PATH).convert("RGBA")
    base = card.copy()

    # profile photo inside the ring, then bring the JOINED badge back on top of it
    d = AV_RADIUS * 2
    cx, cy = AV_CENTER
    card.alpha_composite(_circle(Image.open(av), d), (cx - AV_RADIUS, cy - AV_RADIUS))
    card.paste(base, (0, 0), _badge_mask(card.size))

    _put_text(card, NAME_X, NAME_CAP_TOP, fn, NAME_SIZE, NAME_MAXW, FONT_NAME, gradient=NAME_GRAD)
    _put_text(card, ID_X, ID_CAP_TOP, str(uid), ROW_SIZE, ROW_MAXW, FONT_ROW, fill=TEXT_DARK)
    _put_text(card, ID_X, USER_CAP_TOP, un, ROW_SIZE, ROW_MAXW, FONT_ROW, fill=TEXT_DARK)

    os.makedirs("downloads", exist_ok=True)
    path = f"downloads/welcome_{uid}.png"
    card.convert("RGB").save(path)
    return path


# ═══════════════════════════════════════════════════════════
#  /welcome on | off   (group admins & sudoers)
# ═══════════════════════════════════════════════════════════
@app.on_message(filters.command(["welcome"]) & filters.group & ~app.bl_users)
async def welcome_toggle(_, m: Message):
    if not m.from_user:
        return

    admins = await db.get_admins(m.chat.id)
    if m.from_user.id not in app.sudoers and m.from_user.id not in admins:
        return await m.reply_text("<blockquote>❌  σηʟʏ ᴧᴅϻɪηs ᴄᴧη υsє ᴛʜɪs ᴄσϻϻᴧηᴅ.</blockquote>")

    state = "єηᴧʙʟєᴅ" if await is_on(m.chat.id) else "ᴅɪsᴧʙʟєᴅ"
    if len(m.command) < 2 or m.command[1].lower() not in ("on", "off", "enable", "disable"):
        return await m.reply_text(
            f"<blockquote>👋  ᴡєʟᴄσϻє ϻєssᴧɢєs: <b>{state}</b></blockquote>\n\n"
            "<blockquote><b>υsᴧɢє:</b>\n"
            "▸  <code>/welcome on</code>\n"
            "▸  <code>/welcome off</code></blockquote>"
        )

    flag = "on" if m.command[1].lower() in ("on", "enable") else "off"
    await set_state(m.chat.id, flag)
    await m.reply_text(
        "<blockquote>✅  ᴡєʟᴄσϻє ϻєssᴧɢєs єηᴧʙʟєᴅ.</blockquote>"
        if flag == "on"
        else "<blockquote>✅  ᴡєʟᴄσϻє ϻєssᴧɢєs ᴅɪsᴧʙʟєєᴅ.</blockquote>"
    )


# ═══════════════════════════════════════════════════════════
#  WELCOME HANDLER
# ═══════════════════════════════════════════════════════════
@app.on_chat_member_updated(filters.group, group=-3)
async def welcome(client, update: ChatMemberUpdated):
    old = update.old_chat_member
    new = update.new_chat_member
    cid = update.chat.id

    if not (new and new.status == enums.ChatMemberStatus.MEMBER):
        return
    # Welcome regular users AND other bots; only skip this music bot itself.
    if new.user.id == client.me.id:
        return

    valid_old = (enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED)
    if old and old.status not in valid_old:
        return

    if not await is_on(cid):
        if await auto_on(cid):
            try:
                await client.send_message(cid, "**ᴡєʟᴄσϻє ϻєssᴧɢєs ʀє-єηᴧʙʟєᴅ.**")
            except TopicClosed:
                return
            except Exception:
                pass
        else:
            return

    burst = await bump(cid, TIME_WINDOW)
    if burst >= JOIN_THRESHOLD:
        minutes = _cooldown_minutes(burst, JOIN_THRESHOLD, COOL_MINUTES)
        await cool(cid, minutes)
        try:
            return await client.send_message(
                cid,
                f"**ϻᴧssɪᴠє ᴊσɪη ᴅєᴛєᴄᴛєᴅ (x{burst}). ᴡєʟᴄσϻє ϻєssᴧɢєs ᴅɪsᴧʙʟєᴅ ғσʀ {minutes} ϻɪηυᴛєs.**",
            )
        except Exception:
            return

    # Heavy work (avatar download, card render, upload) runs in the background so the
    # update worker is freed at once and one slow join can't delay the next ones.
    task = asyncio.create_task(_send_welcome(client, update, new.user))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)


_bg_tasks: set = set()
_card_sem: Optional[asyncio.Semaphore] = None


def _get_card_sem() -> asyncio.Semaphore:
    global _card_sem
    if _card_sem is None:
        _card_sem = asyncio.Semaphore(3)  # max 3 cards rendering at once (CPU friendly)
    return _card_sem


async def _send_welcome(client, update: ChatMemberUpdated, user) -> None:
    cid = update.chat.id
    avatar = img = None
    pp_path = f"downloads/pp_{user.id}.png"
    try:
        async def _get_avatar():
            if not user.photo:
                return FALLBACK_PIC
            try:
                got = await asyncio.wait_for(
                    client.download_media(user.photo.big_file_id, file_name=pp_path), timeout=10
                )
                return got or FALLBACK_PIC
            except Exception:
                return FALLBACK_PIC  # slow / failed photo download -> don't make the welcome late

        async def _count():
            try:
                return await client.get_chat_members_count(cid)
            except Exception:
                return "?"

        # run both network calls at the same time
        avatar, members = await asyncio.gather(_get_avatar(), _count())

        name = user.first_name or "υsєʀ"
        uname_txt = user.username or "No Username"
        async with _get_card_sem():
            img = await asyncio.to_thread(build_pic, avatar, name, user.id, uname_txt)

        caption = CAPTION_TXT.format(
            chat_title=html.escape(str(update.chat.title)),
            mention=user.mention,
            uid=user.id,
            uname=html.escape(user.username or "No Username"),
            count=members,
        )

        buttons = [
            [styled_button(BTN_VIEW, f"tg://openmessage?user_id={user.id}", "primary")],
            [styled_button(BTN_ADD, f"https://t.me/{app.username}?startgroup=true", "success")],
        ]

        try:
            sent = await _send_media_colored(cid, img, caption, buttons)
            if not sent:  # Bot API failed -> normal (uncolored) buttons via pyrogram
                sent = await client.send_photo(cid, img, caption=caption, reply_markup=_to_markup(buttons))
        except TopicClosed:
            return

        # keep only the last WELCOME_LIMIT welcome messages in the chat
        last_messages.setdefault(cid, []).append(sent)
        if len(last_messages[cid]) > WELCOME_LIMIT:
            old_msg = last_messages[cid].pop(0)
            try:
                if isinstance(old_msg, dict):
                    await client.delete_messages(old_msg["chat_id"], old_msg["message_id"])
                elif old_msg:
                    await old_msg.delete()
            except Exception:
                pass

    except TopicClosed:
        return
    except Exception as e:
        logger.warning(f"Welcome card failed in {cid}: {e}")
        try:
            await client.send_message(cid, f"🎉  ᴡєʟᴄσϻє, {user.mention}!")
        except Exception:
            return
    finally:
        for f in (avatar, img, pp_path):
            if f and os.path.exists(f) and str(_BASE) not in os.path.abspath(f):
                try:
                    os.remove(f)
                except Exception:
                    pass


# ─────────────── warm-up: load fonts once at startup (first welcome was the slowest) ───────────────
def _warm_fonts() -> None:
    try:
        probe = Image.new("RGBA", (500, 200), (0, 0, 0, 0))
        draw_text(
            probe, (0, 0), "Aa Zz 123 हिन्दी العربية 中文 한국어 😎 ʟɪᴋᴇ ᴛʜɪs",
            40, fill=(255, 255, 255, 255), max_width=480, min_size=24, primary=FONT_NAME,
        )
        _cap_offset(NAME_SIZE, FONT_NAME)
        _cap_offset(ROW_SIZE, FONT_ROW)
        Image.open(CARD_PATH).load()
    except Exception as e:
        logger.debug(f"Welcome font warm-up skipped: {e}")


import threading as _threading

_threading.Thread(target=_warm_fonts, daemon=True).start()
