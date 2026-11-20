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

import logging
from pyrogram import filters, types
from pyrogram.errors import ChatSendPlainForbidden, ChatWriteForbidden

from ArtistMusic import tune, app, db, lang
from ArtistMusic.helpers import buttons, can_manage_vc

logger = logging.getLogger(__name__)


@app.on_message(filters.command(["resume", "cresume"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _resume(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass
    
    # Check for channel play mode
    is_channel = m.command[0].lower() == "cresume"
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
            return

    if await db.playing(chat_id):
        try:
            return await m.reply_text("Playback is already playing.")
        except (ChatSendPlainForbidden, ChatWriteForbidden):
            return

    await tune.resume(chat_id)
    try:
        await m.reply_text(
            f"Resumed by {m.from_user.mention}",
            reply_markup=buttons.controls(chat_id),
        )
    except (ChatSendPlainForbidden, ChatWriteForbidden):
        logger.warning("Cannot send text in media-only chat")
