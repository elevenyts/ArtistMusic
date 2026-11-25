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
import time
import psutil

from pyrogram import filters, types
from ArtistMusic import app, tune, boot, config, lang
from ArtistMusic.helpers import buttons, utils


@app.on_message(filters.command(["alive", "ping"]) & ~app.bl_users)
@lang.language()
async def _ping(_, m: types.Message):
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    start = time.time()
    sent = await m.reply_text(m.lang["pinging"])

    def get_time(s): return (lambda r: (f"{r[-1]}, " if r[-1][:-4] != "0" else "") + ":".join(reversed(r[:-1])))(
        [f"{v}{u}" for v, u in zip([s % 60, (s//60) % 60, (s//3600) % 24, s//86400], ["s", "m", "h", "days"])])
    uptime = get_time(int(time.time() - boot))
    latency = round((time.time() - start) * 1000, 2)
    
    # Get system stats
    mem = psutil.virtual_memory()
    ram_usage = f"{round(mem.used / (1024 ** 3), 1)}GB / {round(mem.total / (1024 ** 3), 1)}GB"
    cpu_percent = psutil.cpu_percent(interval=0.5)
    
    # Get active chats count
    from ArtistMusic import db
    active_chats = len(await db.get_chats())
    
    caption_text = m.lang["ping_pong"].format(
        latency,
        uptime,
        await tune.ping(),
        ram_usage,
        cpu_percent,
        active_chats,
    )
    
    # Try to send with media, fallback to text if it fails
    try:
        await sent.edit_media(
            media=utils.input_media(config.PING_IMG, caption_text),
            reply_markup=buttons.ping_markup(m.lang["support"]),
        )
    except Exception:
        # Fallback to text if media fails
        await sent.edit_text(
            text=caption_text,
            reply_markup=buttons.ping_markup(m.lang["support"]),
        )
