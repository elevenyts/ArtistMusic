# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Channel      : https://t.me/artistbots
# ==========================================================
#
# Plugin   : Mass group actions (owner / sudo only, Yes/No confirmation)
# Location : ArtistMusic/Artistbots/mass_actions.py
#
#   /kickall   - kick every non-admin member
#   /banall    - ban every non-admin member
#   /unbanall  - unban everyone in the ban list
#   /muteall   - mute every non-admin member
#   /unmuteall - lift the mute of every non-admin member
#   /unpinall  - unpin all pinned messages
# ==========================================================

import asyncio

from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, ChatMembersFilter
from pyrogram.errors import FloodWait
from pyrogram.types import CallbackQuery, ChatPermissions, Message

from ArtistMusic import app, logger

from ._common import (
    ADMIN_STATUSES,
    confirm_buttons,
    default_permissions,
    esc,
    is_owner_or_sudoer,
    mention,
    send_message_colored,
)

MASS_CMDS = ["kickall", "banall", "unbanall", "muteall", "unmuteall", "unpinall"]
_running: set[int] = set()  # chats with a mass action in progress


async def _each_member(client, chat_id: int, **kw):
    """Yield non-bot, non-admin members."""
    async for m in client.get_chat_members(chat_id, **kw):
        if not m.user or m.user.is_bot or m.status in ADMIN_STATUSES:
            continue
        yield m


async def _try(coro_fn, *args, **kw) -> bool:
    try:
        await coro_fn(*args, **kw)
        return True
    except FloodWait as e:
        await asyncio.sleep(e.value)
        try:
            await coro_fn(*args, **kw)
            return True
        except Exception:
            return False
    except Exception:
        return False


@app.on_message(filters.command(MASS_CMDS) & filters.group & ~app.bl_users)
async def ask_mass_confirm(client: Client, message: Message):
    if not message.from_user:
        return
    cmd = message.command[0].lower().split("@")[0]
    ok, owner = await is_owner_or_sudoer(client, message.chat.id, message.from_user.id)
    if not ok:
        owner_m = mention(owner.id, owner.first_name) if owner else "ᴛʜє σᴡηєʀ"
        return await message.reply_text(f"<blockquote>❌  σηʟʏ {owner_m} ϻᴧʏ ʀυη <code>{cmd}</code>.</blockquote>")

    await send_message_colored(
        message.chat.id,
        f"⚠️  {message.from_user.mention}, ᴄσηғɪʀϻ <code>{cmd}</code> ғσʀ ᴛʜɪs ɢʀσυᴘ?",
        confirm_buttons(cmd),
    )


@app.on_callback_query(filters.regex(rf"^({'|'.join(MASS_CMDS)})_(yes|no)$"))
async def handle_mass_confirm(client: Client, cb: CallbackQuery):
    cmd, answer = cb.data.split("_")
    chat_id = cb.message.chat.id

    ok, _ = await is_owner_or_sudoer(client, chat_id, cb.from_user.id)
    if not ok:
        return await cb.answer("σηʟʏ ᴛʜє ɢʀσυᴘ σᴡηєʀ ᴄᴧη ᴄσηғɪʀϻ.", show_alert=True)

    if answer == "no":
        return await cb.message.edit(f"❌ <code>{cmd}</code> canceled.")

    if chat_id in _running:
        return await cb.answer("ᴧησᴛʜєʀ ϻᴧss ᴧᴄᴛɪση ɪs ᴧʟʀєᴧᴅʏ ʀυηηɪηɢ ʜєʀє.", show_alert=True)

    me = await client.get_chat_member(chat_id, app.id)
    priv = me.privileges
    need_pin = cmd == "unpinall"
    allowed = bool(priv and (priv.can_pin_messages if need_pin else priv.can_restrict_members))
    if not allowed:
        return await cb.message.edit("❌  ɪ ʟᴧᴄᴋ ᴛʜє ηєᴄєssᴧʀʏ ᴧᴅϻɪη ᴘєʀϻɪssɪση.")

    _running.add(chat_id)
    await cb.message.edit(f"⏳  <code>{cmd}</code> ɪη ᴘʀσɢʀєss…")
    try:
        report = await _RUNNERS[cmd](client, chat_id)
        await client.send_message(chat_id, report)
        await cb.message.edit(f"✅ <code>{cmd}</code> completed.")
    except Exception as e:
        logger.warning(f"{cmd} failed in {chat_id}: {e}")
        await cb.message.edit(f"❌  єʀʀσʀ ᴅυʀɪηɢ <code>{cmd}</code>:\n<code>{esc(str(e))}</code>")
    finally:
        _running.discard(chat_id)


# ─────────────────────────── implementations ───────────────────────────
async def _do_kickall(client, chat_id):
    done = errors = 0
    async for m in _each_member(client, chat_id):
        if await _try(client.ban_chat_member, chat_id, m.user.id):
            await asyncio.sleep(0.1)
            await _try(client.unban_chat_member, chat_id, m.user.id)
            done += 1
        else:
            errors += 1
        await asyncio.sleep(0.05)
    return f"ᴋɪᴄᴋєᴅ: {done}\nғᴧɪʟυʀєs: {errors}"


async def _do_banall(client, chat_id):
    done = errors = 0
    async for m in _each_member(client, chat_id):
        if await _try(client.ban_chat_member, chat_id, m.user.id):
            done += 1
        else:
            errors += 1
        await asyncio.sleep(0.05)
    return f"ʙᴧηηєᴅ: {done}\nғᴧɪʟυʀєs: {errors}"


async def _do_unbanall(client, chat_id):
    done = errors = 0
    async for m in client.get_chat_members(chat_id, filter=ChatMembersFilter.BANNED):
        if await _try(client.unban_chat_member, chat_id, m.user.id):
            done += 1
        else:
            errors += 1
        await asyncio.sleep(0.05)
    return f"υηʙᴧηηєᴅ: {done}\nғᴧɪʟυʀєs: {errors}"


async def _do_muteall(client, chat_id):
    done = errors = 0
    perms = ChatPermissions()
    async for m in _each_member(client, chat_id):
        if await _try(client.restrict_chat_member, chat_id, m.user.id, perms):
            done += 1
        else:
            errors += 1
        await asyncio.sleep(0.05)
    return f"ϻυᴛєᴅ: {done}\nғᴧɪʟυʀєs: {errors}"


async def _do_unmuteall(client, chat_id):
    done = errors = 0
    perms = await default_permissions(client, chat_id)
    async for m in _each_member(client, chat_id):
        if await _try(client.restrict_chat_member, chat_id, m.user.id, perms):
            done += 1
        else:
            errors += 1
        await asyncio.sleep(0.05)
    return f"υηϻυᴛєᴅ: {done}\nғᴧɪʟυʀєs: {errors}"


async def _do_unpinall(client, chat_id):
    await client.unpin_all_chat_messages(chat_id)
    return "υηᴘɪηηєᴅ ᴧʟʟ ϻєssᴧɢєs."


_RUNNERS = {
    "kickall": _do_kickall,
    "banall": _do_banall,
    "unbanall": _do_unbanall,
    "muteall": _do_muteall,
    "unmuteall": _do_unmuteall,
    "unpinall": _do_unpinall,
}
