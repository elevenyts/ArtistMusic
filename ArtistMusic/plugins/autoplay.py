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

from ArtistMusic import app, db
from ArtistMusic.helpers import can_manage_vc


@app.on_message(filters.command(["autoplay", "cautoplay"]) & filters.group & ~app.bl_users)
@can_manage_vc
async def _autoplay(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass

    # Determine target chat_id:
    # - /cautoplay → explicitly use linked channel
    # - /autoplay  → use channel if channel-play is active, else group
    is_explicit_channel = m.command[0].lower() == "cautoplay"
    chat_id = m.chat.id

    channel_id = await db.get_cmode(m.chat.id)

    if is_explicit_channel:
        if channel_id is None:
            return await m.reply_text(
                "<blockquote>❌ Channel play is not enabled.\n\n"
                "Use /channelplay to enable it first.</blockquote>"
            )
        chat_id = channel_id
    elif channel_id is not None:
        # /autoplay in a group that has channel-play active → target channel
        chat_id = channel_id

    current = await db.get_autoplay(chat_id)

    # Toggle autoplay
    new_state = not current
    await db.set_autoplay(chat_id, new_state)

    if new_state:
        text = (
            "<blockquote>🎵 <b>Autoplay: ON</b>\n\n"
            "Just use /play once — the rest of the songs will keep playing on their own!\n"
            "When the queue ends, I will automatically find and play a similar song.\n"
            "If nobody is left in the VC, autoplay will turn off automatically when the song ends.\n\n"
            "Use /autoplay again to turn it off.</blockquote>"
        )
    else:
        text = (
            "<blockquote>⏹ <b>Autoplay: OFF</b>\n\n"
            "Autoplay has been turned off. Playback will stop when the queue ends.\n\n"
            "Use /autoplay again to turn it on.</blockquote>"
        )

    await m.reply_text(text)
