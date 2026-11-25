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

from pyrogram import filters, types

from ArtistMusic import app, db, lang
from ArtistMusic.helpers import can_manage_vc


@app.on_message(filters.command(["loop", "cloop"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _loop(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass
    
    # Check for channel play mode
    is_channel = m.command[0].lower() == "cloop"
    chat_id = m.chat.id
    
    if is_channel:
        channel_id = await db.get_cmode(m.chat.id)
        if channel_id is None:
            return await m.reply_text("Channel play is not enabled. Use /channelplay to enable.")
        chat_id = channel_id
    
    current_loop = await db.get_loop(chat_id)
    
    if len(m.command) > 1:
        mode_arg = m.command[1].lower()
        if mode_arg in ["0", "disable"]:
            new_loop = 0
            text = "Loop mode disabled"
        elif mode_arg in ["single", "1", "one"]:
            new_loop = 1
            text = "Loop mode set to Single Track"
        elif mode_arg in ["queue", "all", "10"]:
            new_loop = 10
            text = "Loop mode set to Queue"
        else:
            return await m.reply_text(
                "Usage:\n"
                "/loop - Cycle through modes\n"
                "/loop disable - Disable loop\n"
                "/loop single - Loop current track\n"
                "/loop queue - Loop entire queue\n\n"
                "Channel commands:\n"
                "/cloop - Same as /loop but for channel"
            )
    else:
        if current_loop == 0:
            new_loop = 1
            text = "Loop mode set to Single Track"
        elif current_loop == 1:
            new_loop = 10
            text = "Loop mode set to Queue"
        else:
            new_loop = 0
            text = "Loop mode disabled"
    
    await db.set_loop(chat_id, new_loop)
    await m.reply_text(text)
