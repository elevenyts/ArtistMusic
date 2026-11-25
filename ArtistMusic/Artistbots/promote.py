# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Channel      : https://t.me/artistbots
# ==========================================================
#
# Plugin   : Promote / demote
# Location : ArtistMusic/Artistbots/promote.py
#
#   /promote /fullpromote /demote /tempadmin  (reply, @username or user-ID)
#   Time format for /tempadmin: 30m, 2h, 1d   (auto-demote when it ends)
# ==========================================================

import asyncio
from typing import Optional

from pyrogram import enums, filters
from pyrogram.errors import ChatAdminRequired, RPCError, UserAdminInvalid
from pyrogram.types import ChatPrivileges, Message

from ArtistMusic import app, logger

from ._common import admin_required, esc, extract_user_and_title, mention, parse_time

_LIMITED = ChatPrivileges(
    can_manage_chat=True,
    can_delete_messages=True,
    can_manage_video_chats=True,
    can_restrict_members=False,
    can_promote_members=False,
    can_change_info=False,
    can_invite_users=True,
    can_pin_messages=True,
    is_anonymous=False,
)

_FULL = ChatPrivileges(
    can_manage_chat=True,
    can_delete_messages=True,
    can_manage_video_chats=True,
    can_restrict_members=True,
    can_promote_members=True,
    can_change_info=True,
    can_invite_users=True,
    can_pin_messages=True,
    is_anonymous=False,
)

_DEMOTE = ChatPrivileges(
    can_manage_chat=False,
    can_delete_messages=False,
    can_manage_video_chats=False,
    can_restrict_members=False,
    can_promote_members=False,
    can_change_info=False,
    can_invite_users=False,
    can_pin_messages=False,
    is_anonymous=False,
)

_USAGES = {
    "promote": "/promote @user [ᴛɪᴛʟє] — σʀ ʀєᴘʟʏ ᴡɪᴛʜ /promote [ᴛɪᴛʟє]",
    "fullpromote": "/fullpromote @user [ᴛɪᴛʟє] — σʀ ʀєᴘʟʏ ᴡɪᴛʜ /fullpromote [ᴛɪᴛʟє]",
    "demote": "/demote @user — σʀ ʀєᴘʟʏ ᴡɪᴛʜ /demote",
    "tempadmin": "/tempadmin @user <time> [ᴛɪᴛʟє] — σʀ ʀєᴘʟʏ ᴡɪᴛʜ /tempadmin <time> [ᴛɪᴛʟє]",
}

_GROUP = filters.group & ~app.bl_users


def _usage(cmd: str) -> str:
    return f"<b>υsᴧɢє:</b> <code>{esc(_USAGES[cmd])}</code>"


def _done(action: str, msg: Message, uid: int, name: str, title: Optional[str] = None) -> str:
    text = (
        f"» <b>{esc(action)}</b> ᴧ υsєʀ ɪη {esc(msg.chat.title)}\n"
        f" υsєʀ  : {mention(uid, name)}\n"
        f" ᴧᴅϻɪη : {mention(msg.from_user.id, msg.from_user.first_name)}"
    )
    if title:
        text += f"\n<b>Title:</b> {esc(title)}"
    return text


async def _status(client, chat_id: int, uid: int):
    try:
        return (await client.get_chat_member(chat_id, uid)).status
    except RPCError:
        return None


async def _promote(client, message: Message, uid: int, name: str, privileges, label: str, title=None):
    """Promote + optional custom title. Returns True on success."""
    try:
        await client.promote_chat_member(message.chat.id, uid, privileges=privileges)
    except ChatAdminRequired:
        await message.reply_text("<blockquote>ɪ ηєєᴅ ᴘʀσϻσᴛє ᴘєʀϻɪssɪσηs.</blockquote>")
        return False
    except UserAdminInvalid:
        await message.reply_text("<blockquote>ɪ ᴄᴧηησᴛ ᴘʀσϻσᴛє ᴛʜᴧᴛ υsєʀ.</blockquote>")
        return False
    except RPCError as e:
        await message.reply_text(f"Failed: <code>{esc(str(e))}</code>")
        return False

    if title:
        try:
            await client.set_administrator_title(message.chat.id, uid, title[:16])
        except Exception:
            title = "⚠️  ᴄσυʟᴅη'ᴛ sєᴛ ᴄυsᴛσϻ ᴛɪᴛʟє"
    await message.reply_text(_done(label, message, uid, name, title))
    return True


# ═════════════════════════════ /promote ═════════════════════════════
@app.on_message(filters.command("promote") & _GROUP)
@admin_required("can_promote_members")
async def promote_cmd(client, message: Message):
    if len(message.command) == 1 and not message.reply_to_message:
        return await message.reply_text(_usage("promote"))
    uid, name, title = await extract_user_and_title(message, client)
    if not uid:
        return
    if await _status(client, message.chat.id, uid) in (
        enums.ChatMemberStatus.ADMINISTRATOR,
        enums.ChatMemberStatus.OWNER,
    ):
        return await message.reply_text("<blockquote>υsєʀ ɪs ᴧʟʀєᴧᴅʏ ᴧη ᴧᴅϻɪη.</blockquote>")
    await _promote(client, message, uid, name, _LIMITED, "ᴘʀσϻσᴛєᴅ", title)


# ═════════════════════════════ /fullpromote ═════════════════════════════
@app.on_message(filters.command("fullpromote") & _GROUP)
@admin_required("can_promote_members")
async def fullpromote_cmd(client, message: Message):
    if len(message.command) == 1 and not message.reply_to_message:
        return await message.reply_text(_usage("fullpromote"))
    uid, name, title = await extract_user_and_title(message, client)
    if not uid:
        return
    if await _status(client, message.chat.id, uid) in (
        enums.ChatMemberStatus.ADMINISTRATOR,
        enums.ChatMemberStatus.OWNER,
    ):
        return await message.reply_text("<blockquote>υsєʀ ɪs ᴧʟʀєᴧᴅʏ ᴧη ᴧᴅϻɪη.</blockquote>")
    await _promote(client, message, uid, name, _FULL, "ғυʟʟʏ ᴘʀσϻσᴛєᴅ", title)


# ═════════════════════════════ /demote ═════════════════════════════
@app.on_message(filters.command("demote") & _GROUP)
@admin_required("can_promote_members")
async def demote_cmd(client, message: Message):
    if len(message.command) == 1 and not message.reply_to_message:
        return await message.reply_text(_usage("demote"))
    uid, name, _ = await extract_user_and_title(message, client)
    if not uid:
        return
    status = await _status(client, message.chat.id, uid)
    if status == enums.ChatMemberStatus.OWNER:
        return await message.reply_text("<blockquote>ɪ ᴄᴧηησᴛ ᴅєϻσᴛє ᴛʜє ɢʀσυᴘ σᴡηєʀ.</blockquote>")
    if status != enums.ChatMemberStatus.ADMINISTRATOR:
        return await message.reply_text("<blockquote>υsєʀ ɪs ησᴛ ᴧη ᴧᴅϻɪη.</blockquote>")
    try:
        await client.promote_chat_member(message.chat.id, uid, privileges=_DEMOTE)
        await message.reply_text(_done("ᴅєϻσᴛєᴅ", message, uid, name))
    except ChatAdminRequired:
        await message.reply_text("<blockquote>ɪ ηєєᴅ ᴘʀσϻσᴛє ᴘєʀϻɪssɪσηs.</blockquote>")
    except UserAdminInvalid:
        await message.reply_text("<blockquote>ɪ ᴄᴧηησᴛ ᴅєϻσᴛє ᴛʜᴧᴛ υsєʀ.</blockquote>")


# ═════════════════════════════ /tempadmin ═════════════════════════════
@app.on_message(filters.command("tempadmin") & _GROUP)
@admin_required("can_promote_members")
async def tempadmin_cmd(client, message: Message):
    if (not message.reply_to_message and len(message.command) < 3) or (
        message.reply_to_message and len(message.command) < 2
    ):
        return await message.reply_text(_usage("tempadmin"))

    if message.reply_to_message:
        user = message.reply_to_message.from_user
        if not user:
            return await message.reply_text("<blockquote>ɪ ᴄᴧη'ᴛ υsє ᴛʜᴧᴛ ϻєssᴧɢє (ησ υsєʀ ᴧᴛᴛᴧᴄʜєᴅ).</blockquote>")
        time_arg = message.command[1]
    else:
        try:
            user = await client.get_users(message.command[1])
        except Exception:
            return await message.reply_text("<blockquote>ɪ ᴄᴧη'ᴛ ғɪηᴅ ᴛʜᴧᴛ υsєʀ.</blockquote>")
        time_arg = message.command[2]

    if user.id == app.id:
        return await message.reply_text("<blockquote>ɪ ᴄᴧη'ᴛ ᴅσ ᴛʜᴧᴛ ᴛσ ϻʏsєʟғ 😅</blockquote>")
    title = message.text.partition(time_arg)[2].strip() or None
    delta = parse_time(time_arg)
    if not delta:
        return await message.reply_text("<blockquote>ɪηᴠᴧʟɪᴅ ᴛɪϻє ғσʀϻᴧᴛ. υsє s/ϻ/ʜ/ᴅ sυғғɪx (є.ɢ. 2h).</blockquote>")

    if await _status(client, message.chat.id, user.id) in (
        enums.ChatMemberStatus.ADMINISTRATOR,
        enums.ChatMemberStatus.OWNER,
    ):
        return await message.reply_text("<blockquote>υsєʀ ɪs ᴧʟʀєᴧᴅʏ ᴧη ᴧᴅϻɪη.</blockquote>")

    ok = await _promote(client, message, user.id, user.first_name, _FULL, f"ᴛєϻᴘ-ᴘʀσϻσᴛєᴅ ғσʀ {time_arg}", title)
    if not ok:
        return

    chat_id, uid, name = message.chat.id, user.id, user.first_name

    async def _auto_demote():
        await asyncio.sleep(delta.total_seconds())
        try:
            await client.promote_chat_member(chat_id, uid, privileges=_DEMOTE)
            await client.send_message(chat_id, f"ᴧυᴛσ-ᴅєϻσᴛєᴅ {mention(uid, name)} ᴧғᴛєʀ {esc(time_arg)}.")
        except Exception as e:
            logger.warning(f"tempadmin auto-demote failed in {chat_id}: {e}")

    asyncio.create_task(_auto_demote())
