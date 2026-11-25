# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Channel      : https://t.me/artistbots
# ==========================================================
#
# Plugin   : Zombie cleaner + admin list
# Location : ArtistMusic/Artistbots/zombie.py
#
#   /zombies                          - find deleted accounts, confirm, remove them
#   /staff | /admins | /adminlist     - list the group's admins
#   (/bots already exists in ArtistMusic - not duplicated here)
# ==========================================================

import asyncio
import html
from typing import List

from pyrogram import StopPropagation, enums, filters
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import ChannelInvalid, ChatAdminRequired, FloodWait, RPCError
from pyrogram.types import CallbackQuery, Message

from ArtistMusic import app

from ._common import is_admin, send_message_colored, styled_button

_cleaning: set[int] = set()


def _in_group(msg: Message) -> bool:
    return bool(msg.chat and msg.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP))


def _mention_html(user) -> str:
    name = html.escape((user.first_name or "υsєʀ").strip())
    return f'<a href="tg://user?id={user.id}">{name}</a>'


async def _bot_is_admin(client, chat_id: int) -> bool:
    try:
        me = await client.get_chat_member(chat_id, app.id)
        return me.status == ChatMemberStatus.ADMINISTRATOR
    except RPCError:
        return False


async def _scan_deleted(client, chat_id: int) -> List:
    users = []
    try:
        async for member in client.get_chat_members(chat_id):
            if member.user and member.user.is_deleted:
                users.append(member.user)
    except (ChannelInvalid, ChatAdminRequired):
        return []
    return users


async def _safe_edit(msg: Message, text: str):
    try:
        await msg.edit_text(text)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        try:
            await msg.edit_text(text)
        except Exception:
            pass
    except Exception:
        pass


@app.on_message(filters.command("zombies") & filters.group & ~app.bl_users)
async def prompt_zombie_cleanup(client, message: Message):
    if not await _bot_is_admin(client, message.chat.id):
        return await message.reply_text("<blockquote>➠  <b>ɪ ηєєᴅ ᴧᴅϻɪη ʀɪɢʜᴛs ᴛσ ʀєϻσᴠє ᴅєʟєᴛєᴅ ᴧᴄᴄσυηᴛs ʜєʀє.</b></blockquote>")
    if not await is_admin(client, message):
        return await message.reply_text("<blockquote>👮🏻  <b>σηʟʏ ᴧᴅϻɪηs ᴄᴧη ᴄʟєᴧη υᴘ ᴅєʟєᴛєᴅ ᴧᴄᴄσυηᴛs.</b></blockquote>")

    total = len(await _scan_deleted(client, message.chat.id))
    if total == 0:
        return await message.reply_text("<blockquote>✅  <b>ησ ᴢσϻʙɪє (ᴅєʟєᴛєᴅ) ᴧᴄᴄσυηᴛs ғσυηᴅ ɪη ᴛʜɪs ᴄʜᴧᴛ.</b></blockquote>")

    await send_message_colored(
        message.chat.id,
        f"🧟  <b>ғσυηᴅ <code>{total}</code> ᴅєʟєᴛєᴅ ᴧᴄᴄσυηᴛ(s) ɪη "
        f"{html.escape(message.chat.title or 'ᴛʜɪs ᴄʜᴧᴛ')}</b>\n\n"
        "🗑️  <b>ᴅσ ʏσυ ᴡᴧηᴛ ᴛσ ʀєϻσᴠє ᴛʜєϻ ᴧʟʟ?</b>",
        [
            [
                styled_button("✅  ʏєs, ᴄʟєᴧη", callback_data=f"confirm_zombies:{message.chat.id}", style="success"),
                styled_button("❌  ᴄᴧηᴄєʟ", callback_data="cancel_zombies", style="danger"),
            ]
        ],
    )


@app.on_callback_query(filters.regex(r"^confirm_zombies:"))
async def execute_zombie_cleanup(client, cq: CallbackQuery):
    try:
        chat_id = int(cq.data.split(":", 1)[1])
    except Exception:
        return await cq.answer("ɪηᴠᴧʟɪᴅ ʀєǫυєsᴛ.", show_alert=True)

    if chat_id != cq.message.chat.id:
        return await cq.answer("ɪηᴠᴧʟɪᴅ ʀєǫυєsᴛ.", show_alert=True)
    if not await is_admin(client, cq):
        return await cq.answer("👮🏻  σηʟʏ ᴧᴅϻɪηs ᴄᴧη ᴄσηғɪʀϻ ᴛʜɪs ᴧᴄᴛɪση.", show_alert=True)
    if not await _bot_is_admin(client, chat_id):
        return await _safe_edit(cq.message, "➠  <b>ɪ ηєєᴅ ᴧᴅϻɪη ʀɪɢʜᴛs ᴛσ ʀєϻσᴠє ᴅєʟєᴛєᴅ ᴧᴄᴄσυηᴛs.</b>")
    if chat_id in _cleaning:
        return await cq.answer("⚠️  ᴄʟєᴧηυᴘ ᴧʟʀєᴧᴅʏ ɪη ᴘʀσɢʀєss.", show_alert=True)

    _cleaning.add(chat_id)
    try:
        deleted = await _scan_deleted(client, chat_id)
        total = len(deleted)
        await _safe_edit(
            cq.message,
            f"🧭  <b>ғσυηᴅ <code>{total}</code> ᴅєʟєᴛєᴅ ᴧᴄᴄσυηᴛs.</b>\n🥀 | <b>sᴛᴧʀᴛɪηɢ ᴄʟєᴧηυᴘ...</b>",
        )

        async def ban(user_id: int) -> bool:
            for _ in range(3):
                try:
                    await client.ban_chat_member(chat_id, user_id)
                    return True
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                except Exception:
                    return False
            return False

        removed = 0
        for i in range(0, total, 20):
            batch = deleted[i : i + 20]
            results = await asyncio.gather(*(ban(u.id) for u in batch), return_exceptions=True)
            removed += sum(1 for r in results if r is True)
            await _safe_edit(cq.message, f"♻️  <b>ʀєϻσᴠєᴅ {removed}/{total} ᴅєʟєᴛєᴅ ᴧᴄᴄσυηᴛs...</b>")
            await asyncio.sleep(2)

        await _safe_edit(
            cq.message,
            f"✅  <b>sυᴄᴄєssғυʟʟʏ ʀєϻσᴠєᴅ <code>{removed}</code> συᴛ σғ <code>{total}</code> ᴢσϻʙɪєs.</b>",
        )
    finally:
        _cleaning.discard(chat_id)


@app.on_callback_query(filters.regex(r"^cancel_zombies$"))
async def cancel_zombie_cleanup(client, cq: CallbackQuery):
    if not await is_admin(client, cq):
        return await cq.answer("👮🏻  σηʟʏ ᴧᴅϻɪηs ᴄᴧη ᴄᴧηᴄєʟ ᴛʜɪs.", show_alert=True)
    await _safe_edit(cq.message, "❌  <b>ᴄʟєᴧηυᴘ ᴄᴧηᴄєʟʟєᴅ.</b>")


# group=-1 + StopPropagation: ArtistMusic's /admin mention plugin matches any text
# containing "/admin" (so it would also fire on /admins and /adminlist).
@app.on_message(filters.command(["admins", "staff", "adminlist"]) & filters.group & ~app.bl_users, group=-1)
async def list_admins(client, message: Message):
    text = f"<b>👑  ᴧᴅϻɪηs σғ {html.escape(message.chat.title or 'ᴛʜɪs ᴄʜᴧᴛ')}:</b>\n\n"
    try:
        async for m in client.get_chat_members(message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
            if not m.user or m.user.is_bot:
                continue
            line = f"👤 {_mention_html(m.user)}"
            if m.custom_title:
                line += f" — <code>{html.escape(m.custom_title)}</code>"
            if m.status == ChatMemberStatus.OWNER:
                line = "👑 " + line
            text += line + "\n"
        await message.reply_text(text)
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except (ChannelInvalid, ChatAdminRequired):
        await message.reply_text("<blockquote>➠  <b>ɪ ηєєᴅ ᴧᴅϻɪη ʀɪɢʜᴛs ᴛσ ʟɪsᴛ ᴧᴅϻɪηs ʜєʀє.</b></blockquote>")
    raise StopPropagation
