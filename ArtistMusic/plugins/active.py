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
import os
from pyrogram import filters, types
from ArtistMusic import app, db, lang, queue


@app.on_message(filters.command(["ac", "activevc"]) & app.sudo_filter)
@lang.language()
async def _activevc(_, m: types.Message):
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    if not db.active_calls:
        return await m.reply_text(m.lang["vc_empty"])

    if m.command[0] == "ac":
        return await m.reply_text(m.lang["vc_count"].format(len(db.active_calls)))

    sent = await m.reply_text(m.lang["vc_fetching"])
    text = ""

    for i, chat in enumerate(db.active_calls):
        playing = queue.get_current(chat)
        if playing:
            text += f"\n{i+1}. <code>{chat}</code>\n    ➜ {playing.title[:25]}"

    if len(text) < 4000:
        return await sent.edit_text(m.lang["vc_list"] + text)

    with open("activevc.txt", "w") as f:
        f.write(text)

    try:
        await sent.edit_media(
            media=types.InputMediaDocument(
                media="activevc.txt",
                caption=m.lang["vc_list"],
            )
        )
    finally:
        os.remove("activevc.txt")
