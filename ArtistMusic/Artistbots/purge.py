# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Channel      : https://t.me/artistbots
# ==========================================================
#
# Plugin   : Message cleanup
# Location : ArtistMusic/Artistbots/purge.py
#
#   /purge   - reply to a message: delete everything from it up to the command
#   /spurge  - same, but silent (no confirmation message)
#   /del     - reply to a message: delete it
#   Needs: caller + bot with "delete messages"; purge works in supergroups only.
# ==========================================================

import asyncio

from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.errors import FloodWait, MessageDeleteForbidden, RPCError
from pyrogram.types import Message

from ArtistMusic import app

from ._common import esc, has_privilege

_G = filters.group & ~app.bl_users


def _chunks(items: list, n: int = 100):
    for i in range(0, len(items), n):
        yield items[i : i + n]


async def _can_delete(client, message: Message) -> bool:
    if not message.from_user:
        await message.reply_text("<blockquote><b>υηʜɪᴅє ʏσυʀ ᴧᴄᴄσυηᴛ ᴛσ υsє ᴛʜɪs ᴄσϻϻᴧηᴅ.</b></blockquote>")
        return False
    if not await has_privilege(client, message.chat.id, message.from_user.id, "can_delete_messages"):
        await message.reply_text("<blockquote>🚫  <b>ʏσυ ʟᴧᴄᴋ ᴛʜє</b> <code>can_delete_messages</code> <b>ᴘєʀϻɪssɪση.</b></blockquote>")
        return False
    return True


async def _do_purge(client, msg: Message, silent: bool):
    if msg.chat.type != ChatType.SUPERGROUP:
        return await msg.reply_text(
            "<b>ɪ ᴄᴧη'ᴛ ᴘυʀɢє ϻєssᴧɢєs ɪη ᴧ ʙᴧsɪᴄ ɢʀσυᴘ. ᴘʟєᴧsє ᴄσηᴠєʀᴛ ɪᴛ ᴛσ ᴧ sυᴘєʀɢʀσυᴘ.</b>"
        )
    if not msg.reply_to_message:
        return await msg.reply_text("<b>ʀєᴘʟʏ ᴛσ ᴧ ϻєssᴧɢє ᴛσ sᴛᴧʀᴛ ᴘυʀɢє!</b>")

    ids = list(range(msg.reply_to_message.id, msg.id))
    try:
        for chunk in _chunks(ids):
            try:
                await client.delete_messages(msg.chat.id, chunk, revoke=True)
            except FloodWait as e:
                await asyncio.sleep(e.value)
                await client.delete_messages(msg.chat.id, chunk, revoke=True)
            await asyncio.sleep(0.5)
        await msg.delete()
        if not silent:
            done = await client.send_message(msg.chat.id, f"✅ <b>ᴘυʀɢєᴅ</b> <code>{len(ids)}</code> <b>ϻєssᴧɢєs.</b>")
            await asyncio.sleep(3)
            await done.delete()
    except MessageDeleteForbidden:
        await msg.reply_text("<b>ɪ ᴄᴧη'ᴛ ᴅєʟєᴛє ϻєssᴧɢєs ɪη ᴛʜɪs ᴄʜᴧᴛ.</b>")
    except RPCError as e:
        await msg.reply_text(f"<b>єʀʀσʀ σᴄᴄυʀʀєᴅ:</b>\n<code>{esc(str(e))}</code>")


@app.on_message(filters.command("purge") & _G)
async def purge(client, msg: Message):
    if await _can_delete(client, msg):
        await _do_purge(client, msg, silent=False)


@app.on_message(filters.command("spurge") & _G)
async def spurge(client, msg: Message):
    if await _can_delete(client, msg):
        await _do_purge(client, msg, silent=True)


@app.on_message(filters.command("del") & _G)
async def delete_msg(client, msg: Message):
    if not await _can_delete(client, msg):
        return
    if not msg.reply_to_message:
        return await msg.reply_text("<b>ʀєᴘʟʏ ᴛσ ᴧ ϻєssᴧɢє ᴛσ ᴅєʟєᴛє ɪᴛ.</b>")
    try:
        await msg.reply_to_message.delete()
        await msg.delete()
    except Exception as e:
        await msg.reply_text(f"<b>єʀʀσʀ:</b> <code>{esc(str(e))}</code>")
