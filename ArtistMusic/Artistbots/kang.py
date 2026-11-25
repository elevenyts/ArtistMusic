# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Channel      : https://t.me/artistbots
#
# Plugin       : Kang  (copy a whole sticker pack to the user)
# Location     : ArtistMusic/Artistbots/kang.py
#
# Command:
#   /kang  (reply to any sticker)
#       -> duplicates the WHOLE sticker pack of that sticker into a new pack
#          owned by the user who ran the command.
#          Pack title : "<User name> by Artistbots"
#
# This file also holds the sticker-pack helpers shared with sticker.py.
# ==========================================================

import asyncio
import html
import random
import re
import string
import time
from typing import Optional

from pyrogram import filters
from pyrogram.errors import FloodWait, RPCError
from pyrogram.file_id import FileId
from pyrogram.raw import functions, types as raw
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from ArtistMusic import app, db, logger

PREFIXES = ["/", "!", "."]

BRAND = "Artistbots"
MAX_STICKERS = 120          # Telegram limit per pack
FIRST_BATCH = 50            # stickers sent with createStickerSet, rest via addStickerToSet
ADD_DELAY = 1.0             # seconds between addStickerToSet calls (flood protection)
MAX_RETRIES = 5             # retries for one call when FloodWait hits
DEFAULT_EMOJI = "🙂"


# ═══════════════════════════════════════════════════════════
#  Helpers (also imported by sticker.py)
# ═══════════════════════════════════════════════════════════
def esc(text) -> str:
    return html.escape(str(text or ""))


# fallback when MongoDB read/write fails: user_id -> list of pack dicts
mem_packs: dict[int, list] = {}


def pack_collection():
    """Mongo collection that remembers the packs created for each user."""
    return db.db.sticker_packs


def sticker_type(sticker) -> str:
    if getattr(sticker, "is_video", False):
        return "video"
    if getattr(sticker, "is_animated", False):
        return "animated"
    return "static"


def pack_title(user, number: int = 1) -> str:
    """'<User name> by Artistbots'  (a number is added from the 2nd pack on)."""
    name = (user.first_name or "").strip() or "User"
    name = name[:36].strip()
    suffix = f" {number}" if number > 1 else ""
    return f"{name} by {BRAND}{suffix}"


def make_short_name(user_id: int) -> str:
    """Telegram rule: letters/digits/_ , must end with _by_<botusername>."""
    rnd = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    bot = (app.username or "bot").lower()
    name = f"p{user_id}_{rnd}_by_{bot}"
    if len(name) > 64:  # very long bot username: drop the user id part
        name = f"p{rnd}_by_{bot}"
    return name


def pack_link(short_name: str) -> str:
    return f"https://t.me/addstickers/{short_name}"


def link_markup(short_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("📦 ᴏᴘєη ᴘᴧᴄᴋ", url=pack_link(short_name))]]
    )


def input_doc_from_sticker(sticker) -> raw.InputDocument:
    fid = FileId.decode(sticker.file_id)
    return raw.InputDocument(
        id=fid.media_id,
        access_hash=fid.access_hash,
        file_reference=fid.file_reference or b"",
    )


def set_item(document: raw.InputDocument, emoji: Optional[str]) -> raw.InputStickerSetItem:
    return raw.InputStickerSetItem(document=document, emoji=emoji or DEFAULT_EMOJI)


async def invoke(client, request):
    """client.invoke that waits out FloodWait and retries (never gives up silently)."""
    for attempt in range(MAX_RETRIES):
        try:
            return await client.invoke(request)
        except FloodWait as e:
            wait = int(e.value) + 1
            logger.warning(f"sticker FloodWait {wait}s (attempt {attempt + 1})")
            await asyncio.sleep(wait)
    return await client.invoke(request)  # last try, let the error propagate


def friendly_error(e: Exception) -> str:
    s = str(e).upper()
    if "USER_ID_INVALID" in s or "PEER_ID_INVALID" in s:
        return "ᴄᴧη'ᴛ ʀєᴧᴄʜ ᴛʜɪs υsєʀ. sᴛᴧʀᴛ ᴛʜє ʙσᴛ ɪη ᴘʀɪᴠᴧᴛє ғɪʀsᴛ ᴧηᴅ ᴛʀʏ ᴧɢᴧɪη."
    if "STICKERS_TOO_MUCH" in s:
        return "ᴛʜɪs ᴘᴧᴄᴋ ɪs ғυʟʟ (120 sᴛɪᴄᴋєʀs)."
    if "STICKER_PNG" in s or "STICKER_TGS" in s or "STICKER_VIDEO" in s or "STICKER_INVALID" in s:
        return "ᴛᴇʟєɢʀᴧϻ ʀєᴊєᴄᴛєᴅ ᴛʜɪs sᴛɪᴄᴋєʀ ғσʀᴧϻᴧᴛ."
    return f"<code>{esc(str(e)[:150])}</code>"


async def create_set(
    client,
    user,
    title: str,
    items: list,
    *,
    masks: bool = False,
    emojis: bool = False,
    progress=None,
) -> str:
    """Create a new sticker set owned by `user` and return its short name.

    The first FIRST_BATCH stickers go with createStickerSet, the remaining ones
    are added one by one (with FloodWait handling). `progress(done, total)` is
    an optional async callback.
    """
    peer = await client.resolve_peer(user.id)  # InputPeerUser -> needs InputUser
    user_peer = raw.InputUser(user_id=peer.user_id, access_hash=peer.access_hash)
    items = items[:MAX_STICKERS]

    last_err = None
    for _ in range(5):  # new random short name if it is already taken
        short_name = make_short_name(user.id)
        try:
            await invoke(
                client,
                functions.stickers.CreateStickerSet(
                    user_id=user_peer,
                    title=title,
                    short_name=short_name,
                    stickers=items[:FIRST_BATCH],
                    masks=masks or None,
                    emojis=emojis or None,
                ),
            )
            break
        except RPCError as e:
            last_err = e
            if "OCCUPIED" in str(e).upper() or "SHORT_NAME" in str(e).upper():
                continue
            raise
    else:
        raise last_err  # type: ignore[misc]

    done = min(len(items), FIRST_BATCH)
    if progress:
        await progress(done, len(items))

    for item in items[FIRST_BATCH:]:
        await invoke(
            client,
            functions.stickers.AddStickerToSet(
                stickerset=raw.InputStickerSetShortName(short_name=short_name),
                sticker=item,
            ),
        )
        done += 1
        if progress and done % 10 == 0:
            await progress(done, len(items))
        await asyncio.sleep(ADD_DELAY)

    return short_name


async def save_pack(user_id: int, short_name: str, title: str, kind: str, stype: str, count: int):
    rec = {
        "user_id": user_id, "short_name": short_name, "title": title,
        "kind": kind, "type": stype, "count": count, "created": int(time.time()),
    }
    lst = mem_packs.setdefault(user_id, [])
    lst[:] = [r for r in lst if r["short_name"] != short_name] + [rec]
    try:
        await pack_collection().update_one(
            {"short_name": short_name},
            {"$set": {
                "user_id": user_id,
                "short_name": short_name,
                "title": title,
                "kind": kind,          # "kang" | "sticker"
                "type": stype,         # static | animated | video
                "count": count,
                "created": int(time.time()),
            }},
            upsert=True,
        )
    except Exception as e:
        logger.warning(f"save_pack failed: {e}")


async def user_pack_count(user_id: int) -> int:
    try:
        n = await pack_collection().count_documents({"user_id": user_id})
    except Exception:
        n = 0
    return max(n, len(mem_packs.get(user_id, [])))


def _progress_cb(msg: Message):
    last = {"t": 0.0}

    async def cb(done: int, total: int):
        now = time.time()
        if now - last["t"] < 2.5:  # don't spam edits
            return
        last["t"] = now
        try:
            await msg.edit_text(f"⏳ <b>ᴄʀєᴧᴛɪηɢ ᴘᴧᴄᴋ...</b> <code>{done}/{total}</code>")
        except FloodWait as e:
            await asyncio.sleep(int(e.value) + 1)
        except Exception:
            pass

    return cb


# ═══════════════════════════════════════════════════════════
#  /kang
# ═══════════════════════════════════════════════════════════
async def _fetch_set(client, set_name: str):
    return await invoke(
        client,
        functions.messages.GetStickerSet(
            stickerset=raw.InputStickerSetShortName(short_name=set_name),
            hash=0,
        ),
    )


def _emoji_map(sset) -> dict:
    """document id -> first emoji of the sticker."""
    out = {}
    for pack in getattr(sset, "packs", []) or []:
        for doc_id in pack.documents:
            out.setdefault(doc_id, pack.emoticon)
    return out


@app.on_message(
    filters.command(["kang"], prefixes=PREFIXES) & ~app.bl_users
)
async def kang_cmd(client, message: Message):
    user = message.from_user
    if not user:
        return

    replied = message.reply_to_message
    sticker = replied.sticker if replied else None
    if not sticker:
        return await message.reply_text(
            "<b>ʀєᴘʟʏ ᴛσ ᴧ sᴛɪᴄᴋєʀ ᴡɪᴛʜ</b> <code>/kang</code> "
            "<b>ᴛσ ᴄσᴘʏ ɪᴛs ᴡʜσʟє ᴘᴧᴄᴋ.</b>"
        )

    # Sticker that does not belong to any pack -> nothing to duplicate
    if not sticker.set_name:
        return await message.reply_text(
            "⚠️ <b>ᴛʜɪs sᴛɪᴄᴋєʀ ɪs ηᴏᴛ ɪη ᴧηʏ ᴘᴧᴄᴋ.</b>\n"
            "➤ υsє <code>/sticker</code> ᴛσ ϻᴧᴋє ᴧ ᴘᴧᴄᴋ ғʀσϻ ᴏηє sᴛɪᴄᴋєʀ."
        )

    status = await message.reply_text("⏳ <b>ʀєᴧᴅɪηɢ sᴛɪᴄᴋєʀ ᴘᴧᴄᴋ...</b>")

    try:
        sset = await _fetch_set(client, sticker.set_name)
    except Exception as e:
        logger.warning(f"kang get set failed: {e}")
        return await status.edit_text(f"❌ <b>ᴄσυʟᴅη'ᴛ ʀєᴧᴅ ᴛʜє ᴘᴧᴄᴋ.</b>\n{friendly_error(e)}")

    docs = list(sset.documents or [])
    if not docs:
        return await status.edit_text("❌ <b>ᴛʜᴧᴛ ᴘᴧᴄᴋ ɪs єϻᴘᴛʏ.</b>")

    emoji_of = _emoji_map(sset)
    items = [
        set_item(
            raw.InputDocument(
                id=d.id,
                access_hash=d.access_hash,
                file_reference=d.file_reference,
            ),
            emoji_of.get(d.id),
        )
        for d in docs
    ]

    number = await user_pack_count(user.id) + 1
    title = pack_title(user, number)
    truncated = len(items) > MAX_STICKERS

    await status.edit_text(f"⏳ <b>ᴄʀєᴧᴛɪηɢ ᴘᴧᴄᴋ...</b> <code>0/{min(len(items), MAX_STICKERS)}</code>")

    try:
        short_name = await create_set(
            client,
            user,
            title,
            items,
            masks=bool(getattr(sset.set, "masks", False)),
            emojis=bool(getattr(sset.set, "emojis", False)),
            progress=_progress_cb(status),
        )
    except Exception as e:
        logger.warning(f"kang create failed for {user.id}: {e}")
        return await status.edit_text(f"❌ <b>ғᴧɪʟєᴅ ᴛσ ᴄʀєᴧᴛє ᴘᴧᴄᴋ.</b>\n{friendly_error(e)}")

    total = min(len(items), MAX_STICKERS)
    await save_pack(user.id, short_name, title, "kang", sticker_type(sticker), total)

    text = (
        "✅ <b>ᴘᴧᴄᴋ ᴋᴧηɢєᴅ sυᴄᴄєssғυʟʟʏ!</b>\n\n"
        f"▸ <b>ᴛɪᴛʟє :</b> {esc(title)}\n"
        f"▸ <b>sᴛɪᴄᴋєʀs :</b> <code>{total}</code>"
    )
    if truncated:
        text += f"\n⚠️ <i>ᴏηʟʏ ғɪʀsᴛ {MAX_STICKERS} sᴛɪᴄᴋєʀs ᴄᴧη ғɪᴛ ɪη ᴏηє ᴘᴧᴄᴋ.</i>"
    await status.edit_text(text, reply_markup=link_markup(short_name))
