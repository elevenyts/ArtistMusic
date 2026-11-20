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

from pyrogram import errors, filters, types

from ArtistMusic import app, db, lang, userbot


@app.on_message(filters.command(["gban"]) & app.sudo_filter)
@lang.language()
async def _gban(_, m: types.Message):
    """Globally ban a user from all groups."""
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    # Extract user from command or reply
    user_id = None
    reason = "No reason provided"
    
    # Check if replying to a user
    if m.reply_to_message and m.reply_to_message.from_user:
        user_id = m.reply_to_message.from_user.id
        user_mention = m.reply_to_message.from_user.mention
        if len(m.command) > 1:
            reason = " ".join(m.command[1:])
    
    # Check if user ID provided
    elif len(m.command) > 1:
        try:
            user_id = int(m.command[1])
            user = await app.get_users(user_id)
            user_mention = user.mention
            if len(m.command) > 2:
                reason = " ".join(m.command[2:])
        except ValueError:
            return await m.reply_text("<blockquote>❌ Invalid user ID</blockquote>")
        except Exception:
            return await m.reply_text("<blockquote>❌ User not found</blockquote>")
    else:
        return await m.reply_text(
            "<blockquote><b>ᴜꜱᴀɢᴇ:</b>\n"
            "<code>/gban [user_id] [reason]</code>\n"
            "ᴏʀ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜꜱᴇʀ</blockquote>"
        )
    
    # Don't allow banning sudo users or owner
    if user_id in app.sudoers:
        return await m.reply_text("<blockquote>❌ Cannot ban sudo users</blockquote>")
    
    # Check if already gbanned
    if await db.is_gbanned(user_id):
        return await m.reply_text(
            f"<blockquote>⚠️ {user_mention} is already globally banned</blockquote>"
        )
    
    # Add to gban list
    await db.add_gban(user_id)
    
    sent = await m.reply_text(
        f"<blockquote><u><b>🚫 ɢʟᴏʙᴀʟ ʙᴀɴ ᴀᴘᴘʟɪᴇᴅ</b></u>\n\n"
        f"<b>ᴜꜱᴇʀ:</b> {user_mention}\n"
        f"<b>ɪᴅ:</b> <code>{user_id}</code>\n"
        f"<b>ʀᴇᴀꜱᴏɴ:</b> {reason}\n\n"
        f"⏳ Kicking from all groups...</blockquote>"
    )
    
    # Kick user from all groups
    kicked_count = 0
    failed_count = 0
    
    chats = await db.get_chats()
    for chat_id in chats:
        try:
            # Get chat members to check if user is in that chat
            await app.ban_chat_member(chat_id, user_id)
            kicked_count += 1
            await asyncio.sleep(0.3)  # Avoid FloodWait from Telegram
        except errors.FloodWait as fw:
            await asyncio.sleep(fw.value + 1)
        except Exception:
            failed_count += 1
            continue
    
    await sent.edit_text(
        f"<blockquote><u><b>✅ ɢʟᴏʙᴀʟ ʙᴀɴ ᴄᴏᴍᴘʟᴇᴛᴇ</b></u>\n\n"
        f"<b>ᴜꜱᴇʀ:</b> {user_mention}\n"
        f"<b>ɪᴅ:</b> <code>{user_id}</code>\n"
        f"<b>ʀᴇᴀꜱᴏɴ:</b> {reason}\n\n"
        f"<b>ᴋɪᴄᴋᴇᴅ ꜰʀᴏᴍ:</b> {kicked_count} groups\n"
        f"<b>ꜰᴀɪʟᴇᴅ:</b> {failed_count} groups</blockquote>"
    )


@app.on_message(filters.command(["ungban", "unglobalban"]) & app.sudo_filter)
@lang.language()
async def _ungban(_, m: types.Message):
    """Remove user from global ban list."""
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    # Extract user from command or reply
    user_id = None
    
    # Check if replying to a user
    if m.reply_to_message and m.reply_to_message.from_user:
        user_id = m.reply_to_message.from_user.id
        user_mention = m.reply_to_message.from_user.mention
    
    # Check if user ID provided
    elif len(m.command) > 1:
        try:
            user_id = int(m.command[1])
            user = await app.get_users(user_id)
            user_mention = user.mention
        except ValueError:
            return await m.reply_text("<blockquote>❌ Invalid user ID</blockquote>")
        except Exception:
            user_mention = f"User {user_id}"
    else:
        return await m.reply_text(
            "<blockquote><b>ᴜꜱᴀɢᴇ:</b>\n"
            "<code>/ungban [user_id]</code>\n"
            "ᴏʀ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜꜱᴇʀ</blockquote>"
        )
    
    # Check if gbanned
    if not await db.is_gbanned(user_id):
        return await m.reply_text(
            f"<blockquote>⚠️ {user_mention} is not globally banned</blockquote>"
        )
    
    # Remove from gban list
    await db.del_gban(user_id)
    
    await m.reply_text(
        f"<blockquote><u><b>✅ ɢʟᴏʙᴀʟ ʙᴀɴ ʀᴇᴍᴏᴠᴇᴅ</b></u>\n\n"
        f"<b>ᴜꜱᴇʀ:</b> {user_mention}\n"
        f"<b>ɪᴅ:</b> <code>{user_id}</code></blockquote>"
    )


@app.on_message(filters.command(["gbanlist", "gbannedusers"]) & app.sudo_filter)
@lang.language()
async def _gbanlist(_, m: types.Message):
    """Show list of globally banned users."""
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    sent = await m.reply_text("📋 Fetching global ban list...")
    
    gbanned = await db.get_gbanned()
    
    if not gbanned:
        return await sent.edit_text("<blockquote>✅ No users are globally banned</blockquote>")
    
    text = "<u><b>🚫 ɢʟᴏʙᴀʟʟʏ ʙᴀɴɴᴇᴅ ᴜꜱᴇʀꜱ:</b></u>\n<blockquote>"
    
    for user_id in gbanned:
        try:
            user = await app.get_users(user_id)
            text += f"\n- {user.mention} ({user_id})"
        except:
            text += f"\n- Deleted Account ({user_id})"
    
    text += "\n\n</blockquote>"
    await sent.edit_text(text)
