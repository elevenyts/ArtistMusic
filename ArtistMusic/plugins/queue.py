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

from ArtistMusic import app, config, db, lang, queue
from ArtistMusic.helpers import Track, buttons, thumb, utils


@app.on_message(filters.command(["queue", "playing", "cqueue", "cplaying"]) & filters.group & ~app.bl_users)
@lang.language()
async def _queue_func(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass
    
    # Check for channel play mode
    is_channel = m.command[0].lower() in ["cqueue", "cplaying"]
    chat_id = m.chat.id
    
    if is_channel:
        channel_id = await db.get_cmode(m.chat.id)
        if channel_id is None:
            return await m.reply_text("Channel play is not enabled. Use /channelplay to enable.")
        chat_id = channel_id
    
    if not await db.get_call(chat_id):
        return await m.reply_text("Nothing is playing.")

    _reply = await m.reply_text("Fetching queue...")
    _queue = queue.get_queue(chat_id)
    _media = _queue[0]
    _thumb = (
        await thumb.generate(_media)
        if isinstance(_media, Track)
        else config.DEFAULT_THUMB
    )
    _text = f"Now Playing:\n{_media.title}\nDuration: {_media.duration}\nRequested by: {_media.user}"
    
    _queue.pop(0)

    if _queue:
        _text += "\n\nUpcoming:"
        for i, media in enumerate(_queue, start=1):
            if i == 15:
                break
            _text += f"\n{i}. {media.title} ({media.duration})"

    _playing = await db.playing(chat_id)
    await _reply.edit_media(
        media=utils.input_media(_thumb, _text),
        reply_markup=buttons.queue_markup(
            chat_id,
            "Playing" if _playing else "Paused",
            _playing,
        ),
    )
