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
from ArtistMusic.helpers import utils


@app.on_message(filters.command(["addsudo", "delsudo", "rmsudo"]) & app.sudo_filter)
@lang.language()
async def _sudo(_, m: types.Message):
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    user = await utils.extract_user(m)
    if not user:
        return await m.reply_text(m.lang["user_not_found"])

    if m.command[0] == "addsudo":
        if user.id in app.sudoers:
            return await m.reply_text(m.lang["sudo_already"].format(user.mention))

        app.sudoers.add(user.id)
        app.sudo_filter.update([user.id])
        await db.add_sudo(user.id)
        await m.reply_text(m.lang["sudo_added"].format(user.mention))
    else:
        if user.id not in app.sudoers:
            return await m.reply_text(m.lang["sudo_not"].format(user.mention))

        app.sudoers.discard(user.id)
        app.sudo_filter.discard(user.id)
        await db.del_sudo(user.id)
        await m.reply_text(m.lang["sudo_removed"].format(user.mention))


o_mention = None


@app.on_message(filters.command(["listsudo", "sudolist"]) & app.sudo_filter)
@lang.language()
async def _listsudo(_, m: types.Message):
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    sent = await m.reply_text(m.lang["sudo_fetching"])

    # Always fetch fresh owner info with ID
    owner_user = await app.get_users(app.owner)
    o_mention = f"{owner_user.mention} ({app.owner})"
    
    txt = m.lang["sudo_owner"].format(o_mention)
    sudoers = await db.get_sudoers()
    
    if sudoers:
        sudo_list = ""
        for user_id in sudoers:
            try:
                user = await app.get_users(user_id)
                sudo_list += f"\n- {user.mention} ({user_id})"
            except:
                # Deleted account or inaccessible user
                sudo_list += f"\n- Deleted Account ({user_id})"
                continue
        
        if sudo_list:
            txt += f"<blockquote><u><b>ꜱᴜᴅᴏ ᴜꜱᴇʀꜱ:</b></u>{sudo_list}\n\n</blockquote>"

    await sent.edit_text(txt)
