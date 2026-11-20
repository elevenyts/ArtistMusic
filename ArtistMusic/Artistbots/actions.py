# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Channel      : https://t.me/artistbots
# ==========================================================
#
# Plugin   : Single-user moderation
# Location : ArtistMusic/Artistbots/actions.py
#
#   /ban /unban /mute /unmute /kick /dban /sban /tban /tmute /kickme
#   Every command accepts a reply, @username or user-ID.
#   Time format for /tban and /tmute: 30s, 10m, 2h, 3d
# ==========================================================

import asyncio
import datetime as dt
from typing import Optional

from pyrogram import enums, filters
from pyrogram.errors import ChatAdminRequired, RPCError, UserAdminInvalid, UserNotParticipant
from pyrogram.types import ChatPermissions, Message

from ArtistMusic import app

from ._common import (
    ADMIN_STATUSES,
    admin_required,
    default_permissions,
    esc,
    extract_user_and_reason,
    mention,
    parse_time,
)

_MUTE = ChatPermissions()  # everything False

_USAGES = {
    "ban": "/ban @user [ʀєᴧsση] — σʀ ʀєᴘʟʏ ᴡɪᴛʜ /ban [ʀєᴧsση]",
    "unban": "/unban @user [ʀєᴧsση] — σʀ ʀєᴘʟʏ ᴡɪᴛʜ /unban [ʀєᴧsση]",
    "mute": "/mute @user [ʀєᴧsση] — σʀ ʀєᴘʟʏ ᴡɪᴛʜ /mute [ʀєᴧsση]",
    "unmute": "/unmute @user [ʀєᴧsση] — σʀ ʀєᴘʟʏ ᴡɪᴛʜ /unmute [ʀєᴧsση]",
    "tmute": "/tmute @user <time> [ʀєᴧsση] — σʀ ʀєᴘʟʏ ᴡɪᴛʜ /tmute <time> [ʀєᴧsση]",
    "kick": "/kick @user [ʀєᴧsση] — σʀ ʀєᴘʟʏ ᴡɪᴛʜ /kick [ʀєᴧsση]",
    "dban": "ʀєᴘʟʏ ᴛσ ᴧ υsєʀ's ϻєssᴧɢє ᴡɪᴛʜ /dban [ʀєᴧsση]",
    "sban": "/sban @user — σʀ ʀєᴘʟʏ ᴡɪᴛʜ /sban",
    "tban": "/tban @user <time> [ʀєᴧsση] — σʀ ʀєᴘʟʏ ᴡɪᴛʜ /tban <time> [ʀєᴧsση]",
}

_GROUP = filters.group & ~app.bl_users


def _usage(cmd: str) -> str:
    return f"<blockquote>📋  <b>υsᴧɢє:</b>\n\n<code>{esc(_USAGES.get(cmd, 'ɪηᴠᴧʟɪᴅ υsᴧɢє.'))}</code></blockquote>"


def _done(action: str, msg: Message, uid: int, name: str, reason: Optional[str] = None) -> str:
    text = (
        f"<blockquote>✅  <b>{esc(action)}</b>  ɪη  {esc(msg.chat.title)}\n\n"
        f"▸  υsєʀ  : {mention(uid, name)}\n"
        f"▸  ᴧᴅϻɪη : {mention(msg.from_user.id, msg.from_user.first_name)}"
    )
    if reason:
        text += f"\n▸  ʀєᴧsση : {esc(reason)}"
    return text + "</blockquote>"


async def _member(client, chat_id: int, user_id: int):
    try:
        return await client.get_chat_member(chat_id, user_id)
    except (UserNotParticipant, RPCError):
        return None


async def _is_admin_target(client, chat_id: int, user_id: int) -> bool:
    m = await _member(client, chat_id, user_id)
    return bool(m and m.status in ADMIN_STATUSES)


async def _timed_target(client, message: Message):
    """For /tban & /tmute -> (user, time_arg, rest) or None after replying."""
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        if not user:
            await message.reply_text("<blockquote>ɪ ᴄᴧη'ᴛ υsє ᴛʜᴧᴛ ϻєssᴧɢє (ησ υsєʀ ᴧᴛᴛᴧᴄʜєᴅ).</blockquote>")
            return None
        time_arg = message.command[1]
    else:
        try:
            user = await client.get_users(message.command[1])
        except Exception:
            await message.reply_text("<blockquote>ɪ ᴄᴧη'ᴛ ғɪηᴅ ᴛʜᴧᴛ υsєʀ.</blockquote>")
            return None
        time_arg = message.command[2]
    if user.id == app.id:
        await message.reply_text("<blockquote>ɪ ᴄᴧη'ᴛ ᴅσ ᴛʜᴧᴛ ᴛσ ϻʏsєʟғ 😅</blockquote>")
        return None
    return user, time_arg, message.text.partition(time_arg)[2].strip()


# ═════════════════════════════ /ban ═════════════════════════════
@app.on_message(filters.command("ban") & _GROUP)
@admin_required("can_restrict_members")
async def ban_cmd(client, message: Message):
    if len(message.command) == 1 and not message.reply_to_message:
        return await message.reply_text(_usage("ban"))
    uid, name, reason = await extract_user_and_reason(message, client)
    if not uid:
        return
    target = await _member(client, message.chat.id, uid)
    if target and target.status in ADMIN_STATUSES:
        return await message.reply_text("<blockquote>ɪ ᴄᴧηησᴛ ʙᴧη ᴧη ᴧᴅϻɪη σʀ ᴛʜє ɢʀσυᴘ σᴡηєʀ.</blockquote>")
    if target and target.status == enums.ChatMemberStatus.BANNED:
        return await message.reply_text("<blockquote>υsєʀ ɪs ᴧʟʀєᴧᴅʏ ʙᴧηηєᴅ.</blockquote>")
    try:
        await client.ban_chat_member(message.chat.id, uid)
        await message.reply_text(_done("ʙᴧηηєᴅ", message, uid, name, reason))
    except ChatAdminRequired:
        await message.reply_text("<blockquote>ɪ ηєєᴅ ʙᴧη ᴘєʀϻɪssɪσηs.</blockquote>")
    except UserAdminInvalid:
        await message.reply_text("<blockquote>ɪ ᴄᴧηησᴛ ʙᴧη ᴧη ᴧᴅϻɪη.</blockquote>")


# ═════════════════════════════ /unban ═════════════════════════════
@app.on_message(filters.command("unban") & _GROUP)
@admin_required("can_restrict_members")
async def unban_cmd(client, message: Message):
    if len(message.command) == 1 and not message.reply_to_message:
        return await message.reply_text(_usage("unban"))
    uid, name, reason = await extract_user_and_reason(message, client)
    if not uid:
        return
    target = await _member(client, message.chat.id, uid)
    if not target or target.status != enums.ChatMemberStatus.BANNED:
        return await message.reply_text("<blockquote>υsєʀ ɪs ησᴛ ʙᴧηηєᴅ.</blockquote>")
    try:
        await client.unban_chat_member(message.chat.id, uid)
        await message.reply_text(_done("υηʙᴧηηєᴅ", message, uid, name, reason))
    except ChatAdminRequired:
        await message.reply_text("<blockquote>ɪ ηєєᴅ υηʙᴧη ᴘєʀϻɪssɪσηs.</blockquote>")


# ═════════════════════════════ /mute ═════════════════════════════
@app.on_message(filters.command("mute") & _GROUP)
@admin_required("can_restrict_members")
async def mute_cmd(client, message: Message):
    if len(message.command) == 1 and not message.reply_to_message:
        return await message.reply_text(_usage("mute"))
    uid, name, reason = await extract_user_and_reason(message, client)
    if not uid:
        return
    target = await _member(client, message.chat.id, uid)
    if target and target.status in ADMIN_STATUSES:
        return await message.reply_text("<blockquote>ɪ ᴄᴧηησᴛ ϻυᴛє ᴧη ᴧᴅϻɪη σʀ ᴛʜє ɢʀσυᴘ σᴡηєʀ.</blockquote>")
    if (
        target
        and target.status == enums.ChatMemberStatus.RESTRICTED
        and target.permissions
        and not target.permissions.can_send_messages
    ):
        return await message.reply_text("<blockquote>υsєʀ ɪs ᴧʟʀєᴧᴅʏ ϻυᴛєᴅ.</blockquote>")
    try:
        await client.restrict_chat_member(message.chat.id, uid, _MUTE)
        await message.reply_text(_done("ϻυᴛєᴅ", message, uid, name, reason))
    except ChatAdminRequired:
        await message.reply_text("<blockquote>ɪ ηєєᴅ ϻυᴛє ᴘєʀϻɪssɪσηs.</blockquote>")
    except UserAdminInvalid:
        await message.reply_text("<blockquote>ɪ ᴄᴧηησᴛ ϻυᴛє ᴧη ᴧᴅϻɪη.</blockquote>")


# ═════════════════════════════ /unmute ═════════════════════════════
@app.on_message(filters.command("unmute") & _GROUP)
@admin_required("can_restrict_members")
async def unmute_cmd(client, message: Message):
    if len(message.command) == 1 and not message.reply_to_message:
        return await message.reply_text(_usage("unmute"))
    uid, name, reason = await extract_user_and_reason(message, client)
    if not uid:
        return
    target = await _member(client, message.chat.id, uid)
    if not target or target.status != enums.ChatMemberStatus.RESTRICTED:
        return await message.reply_text("<blockquote>υsєʀ ɪs ησᴛ ϻυᴛєᴅ.</blockquote>")
    try:
        perms = await default_permissions(client, message.chat.id)
        await client.restrict_chat_member(message.chat.id, uid, perms)
        await message.reply_text(_done("υηϻυᴛєᴅ", message, uid, name, reason))
    except ChatAdminRequired:
        await message.reply_text("<blockquote>ɪ ηєєᴅ υηϻυᴛє ᴘєʀϻɪssɪσηs.</blockquote>")


# ═════════════════════════════ /kick ═════════════════════════════
@app.on_message(filters.command("kick") & _GROUP)
@admin_required("can_restrict_members")
async def kick_cmd(client, message: Message):
    if len(message.command) == 1 and not message.reply_to_message:
        return await message.reply_text(_usage("kick"))
    uid, name, reason = await extract_user_and_reason(message, client)
    if not uid:
        return
    if await _is_admin_target(client, message.chat.id, uid):
        return await message.reply_text("<blockquote>ɪ ᴄᴧηησᴛ ᴋɪᴄᴋ ᴧη ᴧᴅϻɪη σʀ ᴛʜє ɢʀσυᴘ σᴡηєʀ.</blockquote>")
    try:
        await client.ban_chat_member(message.chat.id, uid)
        await asyncio.sleep(2)
        await client.unban_chat_member(message.chat.id, uid)
        await message.reply_text(_done("ᴋɪᴄᴋєᴅ", message, uid, name, reason))
    except ChatAdminRequired:
        await message.reply_text("<blockquote>ɪ ηєєᴅ ʙᴧη ᴘєʀϻɪssɪσηs.</blockquote>")
    except UserAdminInvalid:
        await message.reply_text("<blockquote>ɪ ᴄᴧηησᴛ ᴋɪᴄᴋ ᴧη ᴧᴅϻɪη.</blockquote>")


# ═════════════════════════════ /tmute ═════════════════════════════
@app.on_message(filters.command("tmute") & _GROUP)
@admin_required("can_restrict_members")
async def tmute_cmd(client, message: Message):
    if (not message.reply_to_message and len(message.command) < 3) or (
        message.reply_to_message and len(message.command) < 2
    ):
        return await message.reply_text(_usage("tmute"))
    res = await _timed_target(client, message)
    if not res:
        return
    user, time_arg, reason = res
    if await _is_admin_target(client, message.chat.id, user.id):
        return await message.reply_text("<blockquote>ɪ ᴄᴧηησᴛ ϻυᴛє ᴧη ᴧᴅϻɪη σʀ ᴛʜє ɢʀσυᴘ σᴡηєʀ.</blockquote>")
    delta = parse_time(time_arg)
    if not delta:
        return await message.reply_text("<blockquote>ɪηᴠᴧʟɪᴅ ᴛɪϻє ғσʀϻᴧᴛ. υsє s/ϻ/ʜ/ᴅ sυғғɪx (є.ɢ. 30m).</blockquote>")
    until = dt.datetime.now(dt.timezone.utc) + delta
    try:
        await client.restrict_chat_member(message.chat.id, user.id, _MUTE, until_date=until)
        await message.reply_text(_done(f"ϻυᴛєᴅ ғσʀ {time_arg}", message, user.id, user.first_name, reason))
    except ChatAdminRequired:
        await message.reply_text("<blockquote>ɪ ηєєᴅ ϻυᴛє ᴘєʀϻɪssɪσηs.</blockquote>")
    except UserAdminInvalid:
        await message.reply_text("<blockquote>ɪ ᴄᴧηησᴛ ϻυᴛє ᴧη ᴧᴅϻɪη.</blockquote>")


# ═════════════════════════════ /dban ═════════════════════════════
@app.on_message(filters.command("dban") & _GROUP)
@admin_required("can_restrict_members", "can_delete_messages")
async def dban_cmd(client, message: Message):
    reply = message.reply_to_message
    if not reply or not reply.from_user:
        return await message.reply_text(_usage("dban"))
    user = reply.from_user
    if user.id == app.id:
        return await message.reply_text("<blockquote>ɪ ᴄᴧη'ᴛ ᴅσ ᴛʜᴧᴛ ᴛσ ϻʏsєʟғ 😅</blockquote>")
    reason = message.text.split(None, 1)[1] if len(message.command) > 1 else None
    if await _is_admin_target(client, message.chat.id, user.id):
        return await message.reply_text("<blockquote>ɪ ᴄᴧηησᴛ ʙᴧη ᴧη ᴧᴅϻɪη σʀ ᴛʜє ɢʀσυᴘ σᴡηєʀ.</blockquote>")
    try:
        await client.ban_chat_member(message.chat.id, user.id)
        await reply.delete()
        await message.reply_text(_done("ʙᴧηηєᴅ", message, user.id, user.first_name, reason))
    except ChatAdminRequired:
        await message.reply_text("<blockquote>ɪ ηєєᴅ ʙᴧη & ᴅєʟєᴛє ᴘєʀϻɪssɪσηs.</blockquote>")
    except UserAdminInvalid:
        await message.reply_text("<blockquote>ɪ ᴄᴧηησᴛ ʙᴧη ᴧη ᴧᴅϻɪη.</blockquote>")


# ═════════════════════════════ /sban ═════════════════════════════
@app.on_message(filters.command("sban") & _GROUP)
@admin_required("can_restrict_members")
async def sban_cmd(client, message: Message):
    if len(message.command) == 1 and not message.reply_to_message:
        return await message.reply_text(_usage("sban"))
    uid, _, _ = await extract_user_and_reason(message, client)
    if not uid:
        return
    if await _is_admin_target(client, message.chat.id, uid):
        return await message.reply_text("<blockquote>ɪ ᴄᴧηησᴛ ʙᴧη ᴧη ᴧᴅϻɪη σʀ ᴛʜє ɢʀσυᴘ σᴡηєʀ.</blockquote>")
    try:
        await client.ban_chat_member(message.chat.id, uid)
        await message.delete()  # silent
    except ChatAdminRequired:
        await message.reply_text("<blockquote>ɪ ηєєᴅ ʙᴧη ᴘєʀϻɪssɪσηs.</blockquote>")
    except UserAdminInvalid:
        await message.reply_text("<blockquote>ɪ ᴄᴧηησᴛ ʙᴧη ᴧη ᴧᴅϻɪη.</blockquote>")


# ═════════════════════════════ /tban ═════════════════════════════
@app.on_message(filters.command("tban") & _GROUP)
@admin_required("can_restrict_members")
async def tban_cmd(client, message: Message):
    if (not message.reply_to_message and len(message.command) < 3) or (
        message.reply_to_message and len(message.command) < 2
    ):
        return await message.reply_text(_usage("tban"))
    res = await _timed_target(client, message)
    if not res:
        return
    user, time_arg, reason = res
    if await _is_admin_target(client, message.chat.id, user.id):
        return await message.reply_text("<blockquote>ɪ ᴄᴧηησᴛ ʙᴧη ᴧη ᴧᴅϻɪη σʀ ᴛʜє ɢʀσυᴘ σᴡηєʀ.</blockquote>")
    delta = parse_time(time_arg)
    if not delta:
        return await message.reply_text("<blockquote>ɪηᴠᴧʟɪᴅ ᴛɪϻє ғσʀϻᴧᴛ. υsє s/ϻ/ʜ/ᴅ sυғғɪx (є.ɢ. 1d).</blockquote>")
    until = dt.datetime.now(dt.timezone.utc) + delta
    try:
        await client.ban_chat_member(message.chat.id, user.id, until_date=until)
        await message.reply_text(_done(f"ʙᴧηηєᴅ ғσʀ {time_arg}", message, user.id, user.first_name, reason))
    except ChatAdminRequired:
        await message.reply_text("<blockquote>ɪ ηєєᴅ ʙᴧη ᴘєʀϻɪssɪσηs.</blockquote>")
    except UserAdminInvalid:
        await message.reply_text("<blockquote>ɪ ᴄᴧηησᴛ ʙᴧη ᴧη ᴧᴅϻɪη.</blockquote>")


# ═════════════════════════════ /kickme ═════════════════════════════
@app.on_message(filters.command("kickme") & _GROUP)
async def kickme_cmd(client, message: Message):
    if not message.from_user:
        return
    if await _is_admin_target(client, message.chat.id, message.from_user.id):
        return await message.reply_text("<blockquote>ηɪᴄє ᴛʀʏ, ʙσss 😅 ɪ ᴄᴧη'ᴛ ᴋɪᴄᴋ ᴧᴅϻɪηs σʀ ᴛʜє σᴡηєʀ.</blockquote>")
    me = await _member(client, message.chat.id, app.id)
    if not me or not (me.privileges and me.privileges.can_restrict_members):
        return await message.reply_text("<blockquote>ɪ ηєєᴅ ʙᴧη ᴘєʀϻɪssɪσηs ᴛσ ᴋɪᴄᴋ ʏσυ. ᴧsᴋ ᴧη ᴧᴅϻɪη ᴛσ єηᴧʙʟє ɪᴛ.</blockquote>")
    try:
        await client.ban_chat_member(message.chat.id, message.from_user.id)
        await asyncio.sleep(3)
        await client.unban_chat_member(message.chat.id, message.from_user.id)
        await message.reply_text("<blockquote>ᴋɪᴄᴋєᴅ sσ ʜᴧʀᴅ, ʏσυʀ ᴧηᴄєsᴛσʀs ғєʟᴛ ɪᴛ. 👟💥</blockquote>")
    except ChatAdminRequired:
        await message.reply_text("<blockquote>ɪ ηєєᴅ ʙᴧη ᴘєʀϻɪssɪσηs.</blockquote>")
    except UserAdminInvalid:
        await message.reply_text("<blockquote>ɪ ᴄᴧη'ᴛ ᴋɪᴄᴋ ᴧᴅϻɪηs σʀ ᴛʜє σᴡηєʀ.</blockquote>")
