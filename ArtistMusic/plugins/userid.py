# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
#
# Channel      : https://t.me/artistbots
# GitHub       : https://github.com/elevenyts/ArtistMusic
# ==========================================================
import html

from pyrogram import filters, types
from pyrogram.enums import ParseMode

from ArtistMusic import app, logger
from ArtistMusic.helpers import utils


def _msg_link(msg: types.Message):
    """message.link is None (or can raise) in private chats / basic groups."""
    try:
        return msg.link
    except Exception:
        return None


def _line(label: str, value, url: str | None = None) -> str:
    title = f'<a href="{url}">{label}</a>' if url else label
    return f"<b>{title}</b> <code>{value}</code>\n"


@app.on_message(filters.command("id") & ~app.bl_users)
async def getid(client, message: types.Message):
    chat = message.chat
    reply = message.reply_to_message

    text = _line("ᴍᴇssᴀɢᴇ ɪᴅ:", message.id, _msg_link(message))

    # from_user is None for anonymous admins / channel posts
    if message.from_user:
        uid = message.from_user.id
        text += _line("ʏᴏᴜʀ ɪᴅ:", uid, f"tg://user?id={uid}")
    elif message.sender_chat:
        text += _line("sᴇɴᴅᴇʀ ᴄʜᴀᴛ ɪᴅ:", message.sender_chat.id)

    # /id @username  or  /id 123456789
    if len(message.command) > 1:
        arg = message.command[1].strip()
        if arg.lstrip("-").isdigit():
            arg = int(arg)
        try:
            user = await client.get_users(arg)
            text += _line("ᴜsᴇʀ ɪᴅ:", user.id, f"tg://user?id={user.id}")
        except Exception:
            try:
                target = await client.get_chat(arg)
                text += _line("ᴄʜᴀᴛ ɪᴅ:", target.id)
            except Exception:
                return await utils.reply(
                    message,
                    text="ᴛʜɪs ᴜsᴇʀ ᴏʀ ᴄʜᴀᴛ ᴅᴏᴇsɴ'ᴛ ᴇxɪsᴛ.",
                    quote=True,
                )

    # chat.username is None for private groups -> no link in that case
    chat_url = f"https://t.me/{chat.username}" if getattr(chat, "username", None) else None
    text += _line("ᴄʜᴀᴛ ɪᴅ:", chat.id, chat_url) + "\n"

    if reply:
        text += _line("ʀᴇᴘʟɪᴇᴅ ᴍᴇssᴀɢᴇ ɪᴅ:", reply.id, _msg_link(reply))
        if reply.from_user:
            rid = reply.from_user.id
            text += _line("ʀᴇᴘʟɪᴇᴅ ᴜsᴇʀ ɪᴅ:", rid, f"tg://user?id={rid}")
        elif reply.sender_chat:
            text += _line("ʀᴇᴘʟɪᴇᴅ ᴄʜᴀᴛ/ᴄʜᴀɴɴᴇʟ ɪᴅ:", reply.sender_chat.id)

        # forwarded message: old (forward_from_chat) and new (forward_origin) Kurigram fields
        origin = getattr(reply, "forward_origin", None)
        fchat = getattr(reply, "forward_from_chat", None) or getattr(origin, "chat", None)
        fuser = getattr(reply, "forward_from", None) or getattr(origin, "sender_user", None)
        if fchat:
            text += "\n" + _line(
                f"ғᴏʀᴡᴀʀᴅᴇᴅ ᴄʜᴀɴɴᴇʟ ɪᴅ ({html.escape(getattr(fchat, 'title', '') or '')}):",
                fchat.id,
            )
        if fuser:
            text += _line("ғᴏʀᴡᴀʀᴅᴇᴅ ᴜsᴇʀ ɪᴅ:", fuser.id, f"tg://user?id={fuser.id}")

    try:
        await utils.reply(message, text=text, quote=True, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.warning(f"/id reply failed in {chat.id}: {e}")
