# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Channel      : https://t.me/artistbots
#
# Plugin       : VC Log  (who joined / who left the voice chat)
# Location     : ArtistMusic/Artistbots/vclog.py
#
# What it does:
#   While the assistant is in a group's voice chat, the bot announces in
#   the group every time someone JOINS, LEAVES or is REMOVED from the VC.
#   Each notification is auto-deleted after a few seconds.
#
# Command (group admins & sudoers):
#   /vclog [on|off]   - turn the notifications on / off (default: ON)
#
# Hooked from core/calls.py (UpdatedGroupCallParticipant update).
# ==========================================================

import asyncio
import time

from pyrogram import filters
from pyrogram.errors import FloodWait
from pyrogram.types import Message
from pytgcalls.types import GroupCallParticipant

from ArtistMusic import app, db, logger, userbot

from ._common import esc, mention
from .tagall import PREFIXES, _is_admin

SEND_GAP = 1.2          # seconds between two notifications in one chat
MAX_PENDING = 15        # drop extra notifications when a chat is flooded
DEDUPE_SECS = 3         # ignore the same event for the same user within N sec
MAX_RETRIES = 5         # FloodWait retries for one message
DELETE_AFTER = 4        # auto-delete each notification after N sec

_enabled: dict[int, bool] = {}          # chat_id -> on/off (cache of the DB value)
_locks: dict[int, asyncio.Lock] = {}    # one sender per chat -> keeps order, avoids flood
_pending: dict[int, int] = {}           # chat_id -> queued notifications
_recent: dict[tuple, float] = {}        # (chat, user, action) -> last time
_names: dict[int, str] = {}             # user_id -> first name cache
_delete_tasks: set[asyncio.Task] = set()  # keeps pending delete tasks alive


# ─────────────────────────── settings ───────────────────────────
async def is_enabled(chat_id: int) -> bool:
    if chat_id in _enabled:
        return _enabled[chat_id]
    try:
        doc = await db.cache.find_one({"_id": f"vclog_{chat_id}"})
        value = doc.get("enabled", True) if doc else True
    except Exception as e:
        logger.warning(f"vclog read failed: {e}")
        value = True
    _enabled[chat_id] = value
    return value


async def set_enabled(chat_id: int, value: bool) -> None:
    _enabled[chat_id] = value
    try:
        await db.cache.update_one(
            {"_id": f"vclog_{chat_id}"}, {"$set": {"enabled": value}}, upsert=True
        )
    except Exception as e:
        logger.warning(f"vclog write failed: {e}")


@app.on_message(
    filters.command(["vclog"], prefixes=PREFIXES) & filters.group & ~app.bl_users
)
async def vclog_cmd(client, message: Message):
    if not await _is_admin(client, message):
        return await message.reply_text("🚫 <b>σηʟʏ ᴧᴅϻɪηs ᴄᴧη υsє ᴛʜɪs ᴄσϻϻᴧηᴅ.</b>")

    chat_id = message.chat.id
    arg = message.command[1].lower() if len(message.command) > 1 else ""

    if arg in ("on", "enable", "yes"):
        await set_enabled(chat_id, True)
        return await message.reply_text("✅ <b>ᴠᴄ ᴊᴏɪη / ʟєᴧᴠє ᴀʟєʀᴛs: ση</b>")
    if arg in ("off", "disable", "no"):
        await set_enabled(chat_id, False)
        return await message.reply_text("🚫 <b>ᴠᴄ ᴊᴏɪη / ʟєᴧᴠє ᴀʟєʀᴛs: σғғ</b>")

    state = "ση ✅" if await is_enabled(chat_id) else "σғғ 🚫"
    await message.reply_text(
        f"🎙 <b>ᴠᴄ ᴊᴏɪη / ʟєᴧᴠє ᴀʟєʀᴛs:</b> {state}\n"
        "➤ <code>/vclog on</code> · <code>/vclog off</code>"
    )


# ─────────────────────────── helpers ───────────────────────────
def _assistant_ids() -> set[int]:
    return {c.id for c in getattr(userbot, "clients", []) if getattr(c, "id", None)}


async def _user_name(user_id: int) -> str:
    if user_id in _names:
        return _names[user_id]
    name = "υsєʀ"
    try:
        user = await app.get_users(user_id)
        name = (user.first_name or "").strip() or name
    except Exception:
        pass
    if len(_names) > 2000:
        _names.clear()
    _names[user_id] = name
    return name


async def _delete_later(message: Message) -> None:
    """Delete a notification after DELETE_AFTER seconds."""
    await asyncio.sleep(DELETE_AFTER)
    for _ in range(MAX_RETRIES):
        try:
            await message.delete()
            return
        except FloodWait as e:
            await asyncio.sleep(int(e.value) + 1)
        except Exception as e:
            logger.debug(f"vclog delete failed in {message.chat.id}: {e}")
            return


async def _send(chat_id: int, text: str) -> None:
    """Send one notification; on FloodWait wait it out and retry the SAME message."""
    for _ in range(MAX_RETRIES):
        try:
            sent = await app.send_message(chat_id, text)
            # run in the background so the next notification is not delayed
            task = asyncio.create_task(_delete_later(sent))
            _delete_tasks.add(task)
            task.add_done_callback(_delete_tasks.discard)
            return
        except FloodWait as e:
            await asyncio.sleep(int(e.value) + 1)
        except Exception as e:
            logger.warning(f"vclog send failed in {chat_id}: {e}")
            return


# ─────────────────────────── main hook ───────────────────────────
async def handle_participant(update) -> None:
    """Called from core/calls.py for every UpdatedGroupCallParticipant."""
    try:
        action = update.action
        A = GroupCallParticipant.Action

        def has(flag) -> bool:
            try:
                return bool(action & flag)
            except TypeError:
                return action == flag

        if has(A.JOINED):
            icon, label = "🌱", "ᴠᴄ ᴊᴏɪη"
        elif has(A.LEFT):
            icon, label = "🥀", "ᴠᴄ ʟєᴧᴠє"
        elif has(A.KICKED):
            icon, label = "🌚", "ᴠᴄ ʀєϻσᴠєᴅ"
        else:
            return  # mute / volume / hand-raise changes -> ignore

        user_id = update.participant.user_id
        if user_id in _assistant_ids():
            return  # the assistant's own join/leave (e.g. while seeking)

        # In channel-play mode the VC is in the channel, alerts go to the group
        voice_chat = update.chat_id
        target = await db.get_group_for_channel(voice_chat) or voice_chat
        if not await is_enabled(target):
            return

        now = time.time()
        key = (target, user_id, icon)
        if now - _recent.get(key, 0) < DEDUPE_SECS:
            return
        _recent[key] = now
        if len(_recent) > 500:
            for k in [k for k, t in _recent.items() if now - t > 30]:
                _recent.pop(k, None)

        if _pending.get(target, 0) >= MAX_PENDING:
            return  # busy chat: skip instead of piling up and hitting FloodWait
        _pending[target] = _pending.get(target, 0) + 1

        name = await _user_name(user_id)
        text = (
            f"<b>{icon} {label}</b>\n"
            f"━━━━━━━━━━━\n"
            f"✧ <b>ηᴧϻє</b> : {mention(user_id, name)}\n"
            f"✧ <b>υsєʀ ɪᴅ</b> : <code>{user_id}</code>"
        )

        lock = _locks.setdefault(target, asyncio.Lock())
        try:
            async with lock:
                await _send(target, text)
                await asyncio.sleep(SEND_GAP)
        finally:
            _pending[target] = max(0, _pending.get(target, 1) - 1)
    except Exception as e:
        logger.warning(f"vclog handler error: {e}", exc_info=True)
