# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Channel      : https://t.me/artistbots
# ==========================================================
#
# Plugin   : /info /userinfo /whois
# Location : ArtistMusic/Artistbots/info.py
#
#   Reply to someone, pass @username / user-ID, or use it alone for yourself.
# ==========================================================

from pyrogram import enums, filters
from pyrogram.types import Message

from ArtistMusic import app

from ._common import esc, mention

_STATUS = {
    enums.ChatMemberStatus.OWNER: "👑  σᴡηєʀ",
    enums.ChatMemberStatus.ADMINISTRATOR: "🛡  ᴧᴅϻɪη",
    enums.ChatMemberStatus.MEMBER: "👤  ϻєϻʙєʀ",
    enums.ChatMemberStatus.RESTRICTED: "🔇  ʀєsᴛʀɪᴄᴛєᴅ",
    enums.ChatMemberStatus.LEFT: "🚪  ʟєғᴛ",
    enums.ChatMemberStatus.BANNED: "⛔  ʙᴧηηєᴅ",
}


@app.on_message(filters.command(["info", "userinfo", "whois"]) & ~app.bl_users)
async def info_cmd(client, message: Message):
    if message.reply_to_message and message.reply_to_message.from_user:
        user = message.reply_to_message.from_user
    elif len(message.command) > 1:
        arg = message.command[1]
        try:
            user = await client.get_users(int(arg) if arg.lstrip("-").isdigit() else arg)
        except Exception:
            return await message.reply_text("<blockquote><b>υsєʀ ησᴛ ғσυηᴅ.</b></blockquote>")
    elif message.from_user:
        user = message.from_user
    else:
        return

    lines = [
        "<b>👤 υsєʀ ɪηғσ</b>",
        f"<b>ɪᴅ:</b> <code>{user.id}</code>",
        f"<b>ηᴧϻє:</b> {mention(user.id, user.first_name)}",
    ]
    if user.last_name:
        lines.append(f"<b>ʟᴧsᴛ ηᴧϻє:</b> {esc(user.last_name)}")
    lines.append(f"<b>υsєʀηᴧϻє:</b> {'@' + user.username if user.username else 'ησηє'}")
    lines.append(f"<b>ᴅᴄ:</b> {getattr(user, 'dc_id', None) or 'η/ᴧ'}")
    if user.is_bot:
        lines.append("<b>ᴛʏᴘє:</b> 🤖  ʙσᴛ")
    if getattr(user, "is_premium", False):
        lines.append("<b>ᴘʀєϻɪυϻ:</b> ⭐  ʏєs")

    if message.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
        try:
            member = await client.get_chat_member(message.chat.id, user.id)
            lines.append(f"<b>sᴛᴧᴛυs ʜєʀє:</b> {_STATUS.get(member.status, str(member.status))}")
            if member.custom_title:
                lines.append(f"<b>ᴛɪᴛʟє:</b> {esc(member.custom_title)}")
        except Exception:
            pass

    text = "<blockquote>" + "\n".join(lines) + "</blockquote>"
    if user.photo:
        try:
            return await message.reply_photo(user.photo.big_file_id, caption=text)
        except Exception:
            pass
    await message.reply_text(text)
