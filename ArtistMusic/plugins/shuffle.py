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

import random
from pyrogram import filters, types

from ArtistMusic import app, db, lang, queue
from ArtistMusic.helpers import can_manage_vc


@app.on_message(filters.command(["shuffle", "cshuffle"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _shuffle(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass
    
    # Check for channel play mode
    is_channel = m.command[0].lower() == "cshuffle"
    chat_id = m.chat.id
    
    if is_channel:
        channel_id = await db.get_cmode(m.chat.id)
        if channel_id is None:
            return await m.reply_text("Channel play is not enabled. Use /channelplay to enable.")
        chat_id = channel_id
    
    items = queue.get_all(chat_id)
    
    if not items or len(items) <= 1:
        return await m.reply_text("Queue is empty or has only one track!")
    
    current = items[0] if items else None
    remaining = items[1:] if len(items) > 1 else []
    
    if not remaining:
        return await m.reply_text("No tracks to shuffle!")
    
    random.shuffle(remaining)
    
    queue.clear(chat_id)
    if current:
        queue.add(chat_id, current)
    for item in remaining:
        queue.add(chat_id, item)
    
    await m.reply_text(f"Queue shuffled! ({len(remaining)} tracks randomized)")
