# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Channel      : https://t.me/artistbots
#
# Plugin       : Sticker  (one sticker -> its own pack)
# Location     : ArtistMusic/Artistbots/sticker.py
#
# Command:
#   /sticker  (reply to a sticker)
#       -> creates a pack owned by the user with ONLY that single sticker.
#          Pack title : "<User name> by Artistbots"
#       If the user already has a /sticker pack of the same type, the bot
#       asks:  add to the same pack  /  create a new pack.
#
# Shared helpers live in kang.py.
# ==========================================================

import secrets
import time

from pyrogram import filters
from pyrogram.errors import RPCError
from pyrogram.raw import functions, types as raw
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
    Message,
)

from ArtistMusic import app, logger

from .kang import (
    MAX_STICKERS,
    mem_packs,
    PREFIXES,
    esc,
    friendly_error,
    input_doc_from_sticker,
    invoke,
    link_markup,
    pack_link,
    create_set,
    pack_collection,
    pack_title,
    save_pack,
    set_item,
    sticker_type,
    user_pack_count,
    DEFAULT_EMOJI,
)

PENDING_TTL = 600  # seconds the "same pack / new pack" question stays valid

# token -> {user, doc (InputDocument), emoji, stype, pack, time}
_pending: dict[str, dict] = {}


def _cleanup_pending():
    now = time.time()
    for t in [t for t, d in _pending.items() if now - d["time"] > PENDING_TTL]:
        _pending.pop(t, None)


async def _last_pack(user_id: int):
    """Newest /sticker pack of this user that still has free space."""
    best = None
    try:
        cursor = pack_collection().find(
            {"user_id": user_id, "kind": "sticker", "count": {"$lt": MAX_STICKERS}}
        ).sort("created", -1).limit(1)
        async for doc in cursor:
            best = doc
    except Exception as e:
        logger.warning(f"last_pack db read failed: {e}")
    # fall back to the in-memory record (e.g. DB write/read problem)
    for rec in mem_packs.get(user_id, []):
        if rec["kind"] == "sticker" and rec["count"] < MAX_STICKERS:
            if not best or rec["created"] > best.get("created", 0):
                best = rec
    return best


async def _create_single(client, user, doc, emoji: str, stype: str, msg: Message, note: str = ""):
    number = await user_pack_count(user.id) + 1
    title = pack_title(user, number)
    try:
        short_name = await create_set(client, user, title, [set_item(doc, emoji)])
    except Exception as e:
        logger.warning(f"sticker create failed for {user.id}: {e}")
        return await msg.edit_text(f"❌ <b>ғᴧɪʟєᴅ ᴛσ ᴄʀєᴧᴛє ᴘᴧᴄᴋ.</b>\n{friendly_error(e)}")

    await save_pack(user.id, short_name, title, "sticker", stype, 1)
    await msg.edit_text(
        "✅ <b>ηєᴡ ᴘᴧᴄᴋ ᴄʀєᴧᴛєᴅ!</b>\n\n"
        f"▸ <b>ᴛɪᴛʟє :</b> {esc(title)}\n"
        "▸ <b>sᴛɪᴄᴋєʀs :</b> <code>1</code>" + note,
        reply_markup=link_markup(short_name),
    )


@app.on_message(
    filters.command(["sticker"], prefixes=PREFIXES) & ~app.bl_users
)
async def sticker_cmd(client, message: Message):
    try:
        await _sticker_cmd(client, message)
    except Exception as e:
        logger.error(f"/sticker crashed: {e}", exc_info=True)
        try:
            await message.reply_text(f"❌ <b>/sticker ᴇʀʀᴏʀ:</b> <code>{esc(str(e)[:200])}</code>")
        except Exception:
            pass


async def _sticker_cmd(client, message: Message):
    user = message.from_user
    if not user:
        return

    replied = message.reply_to_message
    sticker = replied.sticker if replied else None
    if not sticker:
        return await message.reply_text(
            "<b>ʀєᴘʟʏ ᴛσ ᴧ sᴛɪᴄᴋєʀ ᴡɪᴛʜ</b> <code>/sticker</code> "
            "<b>ᴛσ ϻᴧᴋє ᴧ ᴘᴧᴄᴋ ᴡɪᴛʜ ᴛʜᴧᴛ ᴏηє sᴛɪᴄᴋєʀ.</b>"
        )

    stype = sticker_type(sticker)
    doc = input_doc_from_sticker(sticker)
    emoji = sticker.emoji or DEFAULT_EMOJI

    existing = await _last_pack(user.id)
    if not existing:
        status = await message.reply_text("⏳ <b>ᴄʀєᴧᴛɪηɢ ᴘᴧᴄᴋ...</b>")
        return await _create_single(client, user, doc, emoji, stype, status)

    # A pack can only hold one sticker type (static / animated / video)
    if existing.get("type") != stype:
        status = await message.reply_text("⏳ <b>ᴄʀєᴧᴛɪηɢ ᴘᴧᴄᴋ...</b>")
        note = (
            f"\n\nℹ️ <i>ʏσυʀ ᴏʟᴅ ᴘᴧᴄᴋ ɪs {esc(existing.get('type'))}, ᴛʜɪs sᴛɪᴄᴋєʀ ɪs "
            f"{esc(stype)} — ᴛєʟєɢʀᴧϻ ᴅσєsη'ᴛ ᴧʟʟᴏᴡ ϻɪxɪηɢ, sσ ᴧ ηєᴡ ᴘᴧᴄᴋ ᴡᴧs ϻᴧᴅє.</i>"
        )
        return await _create_single(client, user, doc, emoji, stype, status, note)

    # User already has a pack of this type -> ask
    _cleanup_pending()
    token = secrets.token_hex(4)
    _pending[token] = {
        "user": user,
        "doc": doc,
        "emoji": emoji,
        "stype": stype,
        "pack": existing["short_name"],
        "title": existing.get("title", ""),
        "count": existing.get("count", 1),
        "time": time.time(),
    }
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ sᴧϻє ᴘᴧᴄᴋ", callback_data=f"stk_add:{token}"),
            InlineKeyboardButton("🆕 ηєᴡ ᴘᴧᴄᴋ", callback_data=f"stk_new:{token}"),
        ],
        [InlineKeyboardButton("✖ ᴄᴧηᴄєʟ", callback_data=f"stk_no:{token}")],
    ])
    await message.reply_text(
        "📦 <b>ʏσυ ᴧʟʀєᴧᴅʏ ʜᴧᴠє ᴧ ᴘᴧᴄᴋ:</b>\n"
        f"<a href=\"{pack_link(existing['short_name'])}\">"
        f"{esc(existing.get('title', 'Your pack'))}</a> "
        f"(<code>{existing.get('count', 1)}</code> sᴛɪᴄᴋєʀs)\n\n"
        "<b>ᴧᴅᴅ ᴛʜɪs sᴛɪᴄᴋєʀ ɪη ᴛʜᴧᴛ ᴘᴧᴄᴋ, σʀ ᴄʀєᴧᴛє ᴧ ηєᴡ ᴏηє?</b>",
        reply_markup=kb,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@app.on_callback_query(filters.regex(r"^stk_(add|new|no):[0-9a-f]+$"))
async def sticker_choice(client, cb: CallbackQuery):
    try:
        await _sticker_choice(client, cb)
    except Exception as e:
        logger.error(f"sticker callback crashed: {e}", exc_info=True)
        try:
            await cb.message.edit_text(f"❌ <b>ᴇʀʀᴏʀ:</b> <code>{esc(str(e)[:200])}</code>")
        except Exception:
            pass


async def _sticker_choice(client, cb: CallbackQuery):
    action, token = cb.data.split(":", 1)
    data = _pending.get(token)

    if not data:
        await cb.answer("⏳ ᴛʜɪs ʀєϙυєsᴛ ᴇxᴘɪʀєᴅ. sєηᴅ /sticker ᴧɢᴧɪη.", show_alert=True)
        try:
            await cb.message.delete()
        except Exception:
            pass
        return

    if cb.from_user.id != data["user"].id:
        return await cb.answer("ᴛʜɪs ɪs ηᴏᴛ ғσʀ ʏσυ.", show_alert=True)

    _pending.pop(token, None)
    await cb.answer()

    if action == "stk_no":
        return await cb.message.edit_text("🚫 <b>ᴄᴧηᴄєʟʟєᴅ.</b>")

    await cb.message.edit_text("⏳ <b>ᴘʀᴏᴄєssɪηɢ...</b>")
    user, doc, emoji, stype = data["user"], data["doc"], data["emoji"], data["stype"]

    if action == "stk_new":
        return await _create_single(client, user, doc, emoji, stype, cb.message)

    # ── add to the same pack ──
    short_name = data["pack"]
    try:
        await invoke(
            client,
            functions.stickers.AddStickerToSet(
                stickerset=raw.InputStickerSetShortName(short_name=short_name),
                sticker=set_item(doc, emoji),
            ),
        )
    except RPCError as e:
        err = str(e).upper()
        if "STICKERSET_INVALID" in err or "SHORT_NAME_INVALID" in err:
            # pack was deleted by the user -> forget it and make a fresh one
            try:
                await pack_collection().delete_one({"short_name": short_name})
            except Exception:
                pass
            await cb.message.edit_text("⚠️ <b>ʏσυʀ ᴏʟᴅ ᴘᴧᴄᴋ ᴡᴧs ᴅєʟєᴛєᴅ. ᴄʀєᴧᴛɪηɢ ᴧ ηєᴡ ᴏηє...</b>")
            return await _create_single(client, user, doc, emoji, stype, cb.message)
        logger.warning(f"sticker add failed for {user.id}: {e}")
        return await cb.message.edit_text(f"❌ <b>ᴄσυʟᴅη'ᴛ ᴧᴅᴅ sᴛɪᴄᴋєʀ.</b>\n{friendly_error(e)}")
    except Exception as e:
        logger.warning(f"sticker add failed for {user.id}: {e}")
        return await cb.message.edit_text(f"❌ <b>ᴄσυʟᴅη'ᴛ ᴧᴅᴅ sᴛɪᴄᴋєʀ.</b>\n{friendly_error(e)}")

    count = data["count"] + 1
    try:
        await pack_collection().update_one(
            {"short_name": short_name}, {"$set": {"count": count}}
        )
    except Exception as e:
        logger.warning(f"count update failed: {e}")

    await cb.message.edit_text(
        "✅ <b>sᴛɪᴄᴋєʀ ᴧᴅᴅєᴅ ᴛσ ʏσυʀ ᴘᴧᴄᴋ!</b>\n\n"
        f"▸ <b>ᴛɪᴛʟє :</b> {esc(data['title'])}\n"
        f"▸ <b>sᴛɪᴄᴋєʀs :</b> <code>{count}</code>",
        reply_markup=link_markup(short_name),
    )
