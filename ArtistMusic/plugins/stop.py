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
import logging
from pyrogram import filters, types
from pyrogram.errors import ChatSendPlainForbidden, ChatWriteForbidden

from ArtistMusic import tune, app, db, lang
from ArtistMusic.helpers import can_manage_vc

logger = logging.getLogger(__name__)


@app.on_message(filters.command(["end", "stop", "cend", "cstop"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _stop(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass
    
    if len(m.command) > 1:
        return
    
    # Check for channel play mode
    is_channel = m.command[0].lower() in ["cend", "cstop"]
    chat_id = m.chat.id
    
    if is_channel:
        channel_id = await db.get_cmode(m.chat.id)
        if channel_id is None:
            return await m.reply_text("Channel play is not enabled. Use /channelplay to enable.")
        chat_id = channel_id
    
    if not await db.get_call(chat_id):
        try:
            return await m.reply_text("Nothing is playing.")
        except (ChatSendPlainForbidden, ChatWriteForbidden):
            logger.warning("Cannot send text in this chat, skipping reply.")
            return
        except Exception as e:
            logger.error(f"Failed to send reply: {e}")
            return

    await tune.stop(chat_id)
    try:
        sent_msg = await m.reply_text(f"Stopped by {m.from_user.mention}")
    except (ChatSendPlainForbidden, ChatWriteForbidden):
        logger.warning("Cannot send text in this chat, stream stopped silently.")
        return
    except Exception as e:
        logger.error(f"Failed to send stop confirmation: {e}")
        return
    
    await asyncio.sleep(5)
    try:
        await sent_msg.delete()
    except Exception:
        pass
