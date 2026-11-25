# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Channel      : https://t.me/artistbots
# ==========================================================
#
# Plugin   : /deleteall - wipe the group's message history
# Location : ArtistMusic/Artistbots/del_msg.py
#
#   Only the group owner (or a sudoer) can confirm. The assistant account is
#   invited, given "delete messages", clears the history, then is demoted and
#   leaves. Falls back to batch deletion if clearing in one go is not allowed.
# ==========================================================

import asyncio

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import (
    ChannelPrivate,
    ChatAdminRequired,
    FloodWait,
    MessageIdInvalid,
    MessageNotModified,
    PeerIdInvalid,
    UserNotParticipant,
)
from pyrogram.types import CallbackQuery, ChatPrivileges, Message

from ArtistMusic import app, db, logger

from ._common import confirm_buttons, esc, is_owner_or_sudoer, mention, send_message_colored

_busy: set[int] = set()


async def _edit(cb: CallbackQuery, text: str) -> bool:
    try:
        await cb.message.edit(text)
        return True
    except (ChannelPrivate, MessageNotModified, MessageIdInvalid, ChatAdminRequired) as e:
        logger.warning(f"deleteall edit suppressed: {e}")
    except Exception as e:
        logger.warning(f"deleteall edit error: {e}")
    try:
        await cb.answer(text[:190], show_alert=False)
    except Exception:
        pass
    return False


@app.on_message(filters.command("deleteall") & filters.group & ~app.bl_users)
async def deleteall_command(client, message: Message):
    if not message.from_user:
        return
    ok, owner = await is_owner_or_sudoer(client, message.chat.id, message.from_user.id)
    if not ok:
        owner_m = mention(owner.id, owner.first_name) if owner else "ᴛʜє σᴡηєʀ"
        return await message.reply_text(
            f"<blockquote>sσʀʀʏ {message.from_user.mention}, σηʟʏ {owner_m} ᴄᴧη υsє /deleteall.</blockquote>"
        )

    me = await client.get_chat_member(message.chat.id, app.id)
    p = me.privileges
    if not (p and p.can_delete_messages and p.can_invite_users and p.can_promote_members):
        return await message.reply_text(
            "<blockquote>ɪ ηєєᴅ ᴛσ ʙє ᴧᴅϻɪη ᴡɪᴛʜ <b>ᴅєʟєᴛє ϻєssᴧɢєs</b>, <b>ɪηᴠɪᴛє υsєʀs</b> & <b>ᴧᴅᴅ ᴧᴅϻɪηs</b>.</blockquote>"
        )

    await send_message_colored(
        message.chat.id,
        f"{message.from_user.mention}, ᴄσηғɪʀϻ ᴅєʟєᴛє <b>ᴧʟʟ</b> ϻєssᴧɢєs?",
        confirm_buttons("deleteall"),
    )


@app.on_callback_query(filters.regex(r"^deleteall_(yes|no)$"))
async def deleteall_callback(client, cb: CallbackQuery):
    _, ans = cb.data.split("_")
    chat_id = cb.message.chat.id

    ok, _ = await is_owner_or_sudoer(client, chat_id, cb.from_user.id)
    if not ok:
        return await cb.answer("σηʟʏ ᴛʜє ɢʀσυᴘ σᴡηєʀ ᴄᴧη ᴄσηғɪʀϻ.", show_alert=True)
    if ans == "no":
        return await _edit(cb, "ᴅєʟєᴛє ᴧʟʟ ᴄᴧηᴄєʟєᴅ.")
    if chat_id in _busy:
        return await cb.answer("ᴧʟʀєᴧᴅʏ ʀυηηɪηɢ ʜєʀє.", show_alert=True)

    _busy.add(chat_id)
    try:
        await _edit(cb, "⏳  ᴅєʟєᴛɪηɢ ᴧʟʟ ϻєssᴧɢєs...")
        assistant = await db.get_assistant(chat_id)
        ass_id = assistant.me.id if assistant.me else (await assistant.get_me()).id

        # 1) make sure the assistant is in the chat
        try:
            member = await client.get_chat_member(chat_id, ass_id)
            if member.status in (ChatMemberStatus.BANNED, ChatMemberStatus.LEFT):
                raise UserNotParticipant
        except (UserNotParticipant, PeerIdInvalid):
            try:
                link = await client.create_chat_invite_link(chat_id, member_limit=1)
                await assistant.join_chat(link.invite_link)
                await asyncio.sleep(1)
            except ChatAdminRequired:
                return await _edit(cb, "ғᴧɪʟєᴅ ᴛσ ɪηᴠɪᴛє ᴧssɪsᴛᴧηᴛ: ϻɪssɪηɢ ɪηᴠɪᴛє ᴘєʀϻɪssɪση.")
            except Exception as e:
                return await _edit(cb, f"ғᴧɪʟєᴅ ᴛσ ᴧᴅᴅ ᴧssɪsᴛᴧηᴛ: {esc(str(e))}")

        # 2) give it the right to delete
        try:
            await client.promote_chat_member(chat_id, ass_id, privileges=ChatPrivileges(can_delete_messages=True))
        except ChatAdminRequired:
            return await _edit(cb, "ғᴧɪʟєᴅ ᴛσ ᴘʀσϻσᴛє ᴧssɪsᴛᴧηᴛ: ϻɪssɪηɢ ᴘʀσϻσᴛє ᴘєʀϻɪssɪση.")
        except Exception as e:
            return await _edit(cb, f"ғᴧɪʟєᴅ ᴛσ ᴘʀσϻσᴛє ᴧssɪsᴛᴧηᴛ: {esc(str(e))}")

        # 3) wipe
        deleted = None
        try:
            deleted = await assistant.delete_chat_history(chat_id, revoke=True)
        except ChatAdminRequired:
            await _edit(cb, "⚠️  ᴄᴧηησᴛ ᴄʟєᴧʀ ғυʟʟ ʜɪsᴛσʀʏ ɪη σηє ɢσ. ғᴧʟʟɪηɢ ʙᴧᴄᴋ ᴛσ ʙᴧᴛᴄʜ ᴅєʟєᴛɪση...")
        except Exception as e:
            logger.warning(f"delete_chat_history failed: {e}")

        if deleted is not None:
            await _edit(cb, f"✅  ᴅєʟєᴛєᴅ {deleted} ϻєssᴧɢєs sυᴄᴄєssғυʟʟʏ.")
        else:
            count = await _batch_delete(assistant, chat_id, cb.message.id)
            await _edit(cb, f"✅  ғᴧʟʟʙᴧᴄᴋ ᴅєʟєᴛєᴅ ᴧᴘᴘʀσx. {count} ϻєssᴧɢєs.")

        # 4) clean up: demote + leave
        try:
            await client.promote_chat_member(chat_id, ass_id, privileges=ChatPrivileges(can_manage_chat=False))
        except Exception as e:
            logger.warning(f"assistant demote skipped: {e}")
        try:
            await assistant.leave_chat(chat_id)
        except Exception:
            pass
    finally:
        _busy.discard(chat_id)


async def _batch_delete(assistant, chat_id: int, keep_id: int) -> int:
    batch, count = [], 0

    async def flush():
        nonlocal batch, count
        if not batch:
            return
        try:
            await assistant.delete_messages(chat_id, batch)
            count += len(batch)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            logger.warning(f"batch delete error: {e}")
        batch = []

    async for msg in assistant.get_chat_history(chat_id):
        if msg.id == keep_id:
            continue
        batch.append(msg.id)
        if len(batch) >= 100:
            await flush()
    await flush()
    return count
