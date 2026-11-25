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

from pyrogram import filters, types

from ArtistMusic import app, db, lang
from ArtistMusic.helpers import admin_check, is_admin, utils


@app.on_message(filters.command(["auth", "unauth"]) & filters.group & ~app.bl_users)
@lang.language()
@admin_check
async def _auth(_, m: types.Message):
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    user = await utils.extract_user(m)
    if not user:
        return await utils.safe_text(m, m.lang["user_not_found"])

    if m.command[0] == "auth":
        if await is_admin(m.chat.id, user.id):
            return await utils.safe_text(m, m.lang["auth_is_admin"])

        await db.add_auth(m.chat.id, user.id)
        await utils.safe_text(m, m.lang["auth_added"].format(user.mention))
    else:
        await db.rm_auth(m.chat.id, user.id)
        await utils.safe_text(m, m.lang["auth_removed"].format(user.mention))


@app.on_message(filters.command(["authlist"]) & filters.group & ~app.bl_users)
@lang.language()
@admin_check
async def _authlist(_, m: types.Message):
    """Display the authorized users for the chat."""
    auth_users = await db._get_auth(m.chat.id)
    if not auth_users:
        return await utils.safe_text(m, m.lang["auth_empty"])

    auth_txt = m.lang["auth_list"].format(m.chat.title)
    for idx, user_id in enumerate(sorted(auth_users), start=1):
        auth_txt += f"\n{idx}. <a href=\"tg://user?id={user_id}\">{user_id}</a>"

    await utils.safe_text(m, auth_txt)


rel_hist = {}


@app.on_message(filters.command(["admincache", "reload"]) & filters.group & ~app.bl_users)
@lang.language()
async def _admincache(_, m: types.Message):
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    # Check if message is from anonymous admin
    if not m.from_user:
        return
    
    if m.from_user.id in rel_hist:
        if time.time() < rel_hist[m.from_user.id]:
            return await utils.safe_text(m, m.lang["admin_cache_wait"])

    rel_hist[m.from_user.id] = time.time() + 600
    sent = await utils.safe_text(m, m.lang["admin_cache_reloading"])
    await db.get_admins(m.chat.id, reload=True)
    if not await utils.safe_edit(sent, m.lang["admin_cache_reloaded"]):
        await utils.safe_text(m, m.lang["admin_cache_reloaded"])
