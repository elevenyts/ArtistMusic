# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Channel      : https://t.me/artistbots
# ==========================================================
#
# Plugin   : Group settings (pin / photo / title / description)
# Location : ArtistMusic/Artistbots/grouphandler.py
#
#   /pin /unpin (reply)  /setphoto (reply to photo)  /removephoto
#   /settitle <text>     /setdescription <text>   (alias: /setdiscription)
# ==========================================================

from pyrogram import filters
from pyrogram.errors import RPCError
from pyrogram.types import Message

from ArtistMusic import app

from ._common import esc, has_privilege

_G = filters.group & ~app.bl_users


async def _allowed(client, message: Message, right: str) -> bool:
    """Caller must hold `right`; replies with the reason otherwise."""
    if not message.from_user:
        await message.reply_text("<blockquote><b>υηʜɪᴅє ʏσυʀ ᴧᴄᴄσυηᴛ ᴛσ υsє ᴛʜɪs ᴄσϻϻᴧηᴅ.</b></blockquote>")
        return False
    if not await has_privilege(client, message.chat.id, message.from_user.id, right):
        await message.reply_text(f"<blockquote>🚫  <b>ʏσυ ʟᴧᴄᴋ ᴛʜє</b> <code>{right}</code> <b>ᴘєʀϻɪssɪση.</b></blockquote>")
        return False
    return True


async def _fail(message: Message, e: Exception):
    await message.reply_text(f"<b>ғᴧɪʟєᴅ:</b> <code>{esc(str(e))}</code>")


@app.on_message(filters.command("pin") & _G)
async def pin_message(client, message: Message):
    if not await _allowed(client, message, "can_pin_messages"):
        return
    if not message.reply_to_message:
        return await message.reply_text("<b>ʀєᴘʟʏ ᴛσ ᴧ ϻєssᴧɢє ᴛσ ᴘɪη ɪᴛ.</b>")
    try:
        await client.pin_chat_message(message.chat.id, message.reply_to_message.id)
        await message.reply_text("<b>ᴘɪηηєᴅ! ✅</b>")
    except RPCError as e:
        await _fail(message, e)


@app.on_message(filters.command("unpin") & _G)
async def unpin_message(client, message: Message):
    if not await _allowed(client, message, "can_pin_messages"):
        return
    if not message.reply_to_message:
        return await message.reply_text("<b>ʀєᴘʟʏ ᴛσ ᴧ ϻєssᴧɢє ᴛσ υηᴘɪη ɪᴛ.</b>")
    try:
        await client.unpin_chat_message(message.chat.id, message.reply_to_message.id)
        await message.reply_text("<b>υηᴘɪηηєᴅ! ✅</b>")
    except RPCError as e:
        await _fail(message, e)


@app.on_message(filters.command("setphoto") & _G)
async def set_group_photo(client, message: Message):
    if not await _allowed(client, message, "can_change_info"):
        return
    reply = message.reply_to_message
    if not reply or not reply.photo:
        return await message.reply_text("<b>ʀєᴘʟʏ ᴛσ ᴧ ᴘʜσᴛσ ᴛσ sєᴛ ɪᴛ ᴧs ɢʀσυᴘ ᴘʜσᴛσ.</b>")
    try:
        await client.set_chat_photo(message.chat.id, photo=reply.photo.file_id)
        await message.reply_text("<b>ɢʀσυᴘ ᴘʜσᴛσ υᴘᴅᴧᴛєᴅ! ✅</b>")
    except RPCError as e:
        await _fail(message, e)


@app.on_message(filters.command("removephoto") & _G)
async def remove_group_photo(client, message: Message):
    if not await _allowed(client, message, "can_change_info"):
        return
    try:
        await client.delete_chat_photo(message.chat.id)
        await message.reply_text("<b>ɢʀσυᴘ ᴘʜσᴛσ ʀєϻσᴠєᴅ! ✅</b>")
    except RPCError as e:
        await _fail(message, e)


@app.on_message(filters.command("settitle") & _G)
async def set_group_title(client, message: Message):
    if not await _allowed(client, message, "can_change_info"):
        return
    if len(message.command) < 2:
        return await message.reply_text("<b>υsᴧɢє:</b> <code>/settitle ηєᴡ ᴛɪᴛʟє</code>")
    title = message.text.split(None, 1)[1]
    try:
        await client.set_chat_title(message.chat.id, title)
        await message.reply_text(f"<b>ᴛɪᴛʟє ᴄʜᴧηɢєᴅ ᴛσ:</b> {esc(title)}")
    except RPCError as e:
        await _fail(message, e)


@app.on_message(filters.command(["setdescription", "setdiscription"]) & _G)
async def set_group_description(client, message: Message):
    if not await _allowed(client, message, "can_change_info"):
        return
    if len(message.command) < 2:
        return await message.reply_text("<b>υsᴧɢє:</b> <code>/setdescription ᴛєxᴛ</code>")
    desc = message.text.split(None, 1)[1]
    try:
        await client.set_chat_description(message.chat.id, desc)
        await message.reply_text("<b>ᴅєsᴄʀɪᴘᴛɪση υᴘᴅᴧᴛєᴅ! ✅</b>")
    except RPCError as e:
        await _fail(message, e)
