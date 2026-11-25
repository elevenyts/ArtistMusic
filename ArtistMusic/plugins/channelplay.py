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
from pyrogram import filters
from pyrogram.enums import ChatMembersFilter, ChatMemberStatus, ChatType
from pyrogram.types import Message

from ArtistMusic import app, config, db


@app.on_message(filters.command(["channelplay"]) & filters.group & ~app.bl_users)
async def channelplay_command(_, m: Message):
    """Enable or disable channel play mode."""
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    # Check if from_user exists (not sent by channel/anonymous admin)
    if not m.from_user:
        return await m.reply_text("❌ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ᴄᴀɴɴᴏᴛ ʙᴇ ᴜꜱᴇᴅ ʙʏ ᴄʜᴀɴɴᴇʟꜱ ᴏʀ ᴀɴᴏɴʏᴍᴏᴜꜱ ᴀᴅᴍɪɴꜱ.")
    
    # Check if user is admin
    member = await app.get_chat_member(m.chat.id, m.from_user.id)
    if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        return await m.reply_text("❌ ᴏɴʟʏ ᴀᴅᴍɪɴꜱ ᴄᴀɴ ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ.")

    if len(m.command) < 2:
        return await m.reply_text(
            f"ᴄʜᴀɴɴᴇʟ ᴘʟᴀʏ ꜱᴇᴛᴛɪɴɢꜱ ꜰᴏʀ {m.chat.title}\n\n"
            "ᴛᴏ ᴇɴᴀʙʟᴇ ꜰᴏʀ ʟɪɴᴋᴇᴅ ᴄʜᴀɴɴᴇʟ:\n"
            "`/channelplay linked`\n\n"
            "ᴛᴏ ᴇɴᴀʙʟᴇ ꜰᴏʀ ᴀɴʏ ᴄʜᴀɴɴᴇʟ:\n"
            "`/channelplay [channel_id]`\n\n"
            "ᴛᴏ ᴅɪꜱᴀʙʟᴇ ᴄʜᴀɴɴᴇʟ ᴘʟᴀʏ:\n"
            "`/channelplay disable`"
        )

    query = m.text.split(None, 1)[1].strip()

    # Disable channel play
    if query.lower() == "disable":
        await db.set_cmode(m.chat.id, None)
        return await m.reply_text("✅ ᴄʜᴀɴɴᴇʟ ᴘʟᴀʏ ᴅɪꜱᴀʙʟᴇᴅ.")

    # Enable for linked channel
    elif query.lower() == "linked":
        chat = await app.get_chat(m.chat.id)
        if chat.linked_chat:
            channel_id = chat.linked_chat.id
            await db.set_cmode(m.chat.id, channel_id)
            return await m.reply_text(
                f"✅ ᴄʜᴀɴɴᴇʟ ᴘʟᴀʏ ᴇɴᴀʙʟᴇᴅ ꜰᴏʀ: {chat.linked_chat.title}\n"
                f"ᴄʜᴀɴɴᴇʟ ɪᴅ: `{chat.linked_chat.id}`"
            )
        else:
            return await m.reply_text("❌ ᴛʜɪꜱ ᴄʜᴀᴛ ᴅᴏᴇꜱɴ'ᴛ ʜᴀᴠᴇ ᴀ ʟɪɴᴋᴇᴅ ᴄʜᴀɴɴᴇʟ.")

    # Enable for specific channel
    else:
        # Handle numeric channel IDs
        if query.lstrip("-").isdigit():
            channel_id = int(query)
        else:
            channel_id = query  # Username or invite link

        try:
            chat = await app.get_chat(channel_id)
        except Exception as e:
            return await m.reply_text(
                f"❌ ꜰᴀɪʟᴇᴅ ᴛᴏ ɢᴇᴛ ᴄʜᴀɴɴᴇʟ.\n\n"
                f"ᴇʀʀᴏʀ: `{type(e).__name__}`\n\n"
                "ᴍᴀᴋᴇ ꜱᴜʀᴇ ʏᴏᴜ'ᴠᴇ ᴀᴅᴅᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴀꜱ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ᴘʀᴏᴍᴏᴛᴇᴅ ɪᴛ ᴀꜱ ᴀᴅᴍɪɴ.\n\n"
                "ꜰᴏʀ ɴᴜᴍᴇʀɪᴄ ɪᴅꜱ: ᴜꜱᴇ ᴛʜᴇ ꜰᴜʟʟ ɪᴅ ɪɴᴄʟᴜᴅɪɴɢ `-100` ᴘʀᴇꜰɪx\n"
                "ᴇxᴀᴍᴘʟᴇ: `/channelplay -1001234567890`"
            )

        if chat.type != ChatType.CHANNEL:
            return await m.reply_text("❌ ᴏɴʟʏ ᴄʜᴀɴɴᴇʟꜱ ᴀʀᴇ ꜱᴜᴘᴘᴏʀᴛᴇᴅ.")

        # Check if user is owner of the channel
        owner_username = None
        owner_id = None
        try:
            async for user in app.get_chat_members(
                chat.id, filter=ChatMembersFilter.ADMINISTRATORS
            ):
                if user.status == ChatMemberStatus.OWNER:
                    owner_username = user.user.username or "Unknown"
                    owner_id = user.user.id
                    break
        except Exception as e:
            return await m.reply_text(
                f"❌ ꜰᴀɪʟᴇᴅ ᴛᴏ ɢᴇᴛ ᴄʜᴀɴɴᴇʟ ᴀᴅᴍɪɴɪꜱᴛʀᴀᴛᴏʀꜱ.\n\n"
                f"ᴇʀʀᴏʀ: `{type(e).__name__}`\n\n"
                "ᴍᴀᴋᴇ ꜱᴜʀᴇ ᴛʜᴇ ʙᴏᴛ ɪꜱ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ."
            )

        if not owner_id:
            return await m.reply_text(
                "❌ ᴄᴏᴜʟᴅ ɴᴏᴛ ꜰɪɴᴅ ᴄʜᴀɴɴᴇʟ ᴏᴡɴᴇʀ.\n\n"
                "ᴍᴀᴋᴇ ꜱᴜʀᴇ ᴛʜᴇ ʙᴏᴛ ʜᴀꜱ ᴘᴇʀᴍɪꜱꜱɪᴏɴ ᴛᴏ ᴠɪᴇᴡ ᴄʜᴀɴɴᴇʟ ᴀᴅᴍɪɴꜱ."
            )

        if owner_id != m.from_user.id:
            return await m.reply_text(
                f"❌ ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴛʜᴇ ᴏᴡɴᴇʀ ᴏꜰ ᴄʜᴀɴɴᴇʟ {chat.title} ᴛᴏ ᴄᴏɴɴᴇᴄᴛ ɪᴛ ᴡɪᴛʜ ᴛʜɪꜱ ɢʀᴏᴜᴘ.\n\n"
                f"ᴄʜᴀɴɴᴇʟ'ꜱ ᴏᴡɴᴇʀ: @{owner_username}\n\n"
                "ᴀʟᴛᴇʀɴᴀᴛɪᴠᴇʟʏ, ʏᴏᴜ ᴄᴀɴ ʟɪɴᴋ ʏᴏᴜʀ ᴄʜᴀᴛ'ꜱ ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ᴄᴏɴɴᴇᴄᴛ ᴡɪᴛʜ `/channelplay linked`"
            )

        await db.set_cmode(m.chat.id, chat.id)
        return await m.reply_text(
            f"✅ ᴄʜᴀɴɴᴇʟ ᴘʟᴀʏ ᴇɴᴀʙʟᴇᴅ ꜰᴏʀ: {chat.title}\n"
            f"ᴄʜᴀɴɴᴇʟ ɪᴅ: `{chat.id}`"
        )
