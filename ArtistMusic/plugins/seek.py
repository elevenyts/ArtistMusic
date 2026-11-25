# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Type         : API Based Telegram Music Bot
#
# Bot          : @ArtistApibot
# Channel      : https://t.me/artistbots
# GitHub       : https://github.com/elevenyts/ArtistMusic
#
# Unauthorized copying, modification, or redistribution
# of this source code without permission is prohibited.
# ==========================================================

import asyncio

from pyrogram import filters, types

from ArtistMusic import tune, app, db, lang, queue
from ArtistMusic.helpers import can_manage_vc


AUTO_DELETE_AFTER = 5  # seconds after which seek messages are deleted


async def _delete_later(msg: types.Message, delay: int = AUTO_DELETE_AFTER):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass


def _auto_delete(msg: types.Message, delay: int = AUTO_DELETE_AFTER):
    """Schedule msg for deletion without blocking the handler."""
    asyncio.create_task(_delete_later(msg, delay))
    return msg


@app.on_message(filters.command(["seek", "seekback", "cseek", "cseekback"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _seek(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass
    
    if len(m.command) < 2:
        return _auto_delete(await m.reply_text(f"Usage: {m.command[0]} <seconds>"))

    try:
        to_seek = int(m.command[1])
    except ValueError:
        return _auto_delete(await m.reply_text(f"Usage: {m.command[0]} <seconds>"))
    
    if to_seek < 10:
        return _auto_delete(await m.reply_text("Minimum seek is 10 seconds"))

    # Check for channel play mode
    is_channel = m.command[0].lower() in ["cseek", "cseekback"]
    chat_id = m.chat.id
    
    if is_channel:
        channel_id = await db.get_cmode(m.chat.id)
        if channel_id is None:
            return _auto_delete(await m.reply_text("Channel play is not enabled. Use /channelplay to enable."))
        chat_id = channel_id

    if not await db.get_call(chat_id):
        return _auto_delete(await m.reply_text("Nothing is playing."))

    if not await db.playing(chat_id):
        return _auto_delete(await m.reply_text("Playback is paused. Resume first."))

    media = queue.get_current(chat_id)
    if not media.duration_sec:
        return _auto_delete(await m.reply_text("Cannot seek in live streams."))

    sent = await m.reply_text("Seeking...")
    
    current_time = getattr(media, 'time', 0)
    if m.command[0] in ["seekback", "cseekback"]:
        stype = "backward"
        start_from = max(1, current_time - to_seek)
    else:
        stype = "forward"
        start_from = min(current_time + to_seek, media.duration_sec - 5)

    success = await tune.seek_stream(chat_id, int(start_from))
    
    if success:
        _t = int(start_from)
        _ts = f"{_t//60:02d}:{_t%60:02d}"
        _dir = ">> ꜰᴏʀᴡᴀʀᴅᴇᴅ" if stype == "forward" else "▢ ʀᴇᴡɪɴᴅᴇᴅ"
        await sent.edit_text(
            f"<blockquote><b>{_dir}</b>\n\n⏱  ᴅᴜʀᴀᴛɪᴏɴ ╌ {_ts}\n👤  ʙʏ ╌ {m.from_user.mention}</blockquote>"
        )
    else:
        await sent.edit_text("Failed to seek!")
    _auto_delete(sent)
