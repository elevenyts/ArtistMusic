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
import html

from pyrogram import enums, errors, filters, types
from pyrogram.errors import ChatAdminRequired, ChannelPrivate

from ArtistMusic import app, config, lang
from ArtistMusic.helpers import buttons, utils


# ==========================================
# 🟢 BOT ADDED IN GROUP
# ==========================================
@app.on_message(filters.new_chat_members & filters.group)
async def new_chat_member(_, message: types.Message):

    for member in message.new_chat_members:
        if member.id == app.id:
            chat = message.chat

            chat_name = chat.title
            chat_id = chat.id
            chat_username = f"@{chat.username}" if chat.username else "ᴘʀɪᴠᴀᴛᴇ ɢʀᴏᴜᴘ"

            try:
                members_count = await app.get_chat_members_count(chat_id)
            except (ChannelPrivate, Exception):
                members_count = "ᴜɴᴋɴᴏᴡɴ"

            added_by = message.from_user
            added_by_name = added_by.mention if added_by else "ᴜɴᴋɴᴏᴡɴ"

            # 🔗 LINK SYSTEM
            try:
                if chat.username:
                    chat_link = f"https://t.me/{chat.username}"
                else:
                    bot_member = await app.get_chat_member(chat_id, app.id)
                    if bot_member.privileges and bot_member.privileges.can_invite_users:
                        chat_link = await app.export_chat_invite_link(chat_id)
                    else:
                        chat_link = "<tg-emoji emoji-id='5852812849780362931'>❌</tg-emoji> ɴᴏ ɪɴᴠɪᴛᴇ ᴘᴇʀᴍɪssɪᴏɴ"
            except ChatAdminRequired:
                chat_link = "<tg-emoji emoji-id='5852812849780362931'>❌</tg-emoji> ʙᴏᴛ ɴᴏᴛ ᴀᴅᴍɪɴ"
            except Exception:
                chat_link = "<tg-emoji emoji-id='5852812849780362931'>❌</tg-emoji> ᴜɴᴀʙʟᴇ ᴛᴏ ɢᴇᴛ ʟɪɴᴋ"

            text = f"""<blockquote>🟢 <b>˹˹𝐄𝐥𝐞𝐯𝐞𝐧𝐲𝐭𝐬 ꭙ ᴍᴜꜱɪᴄ˼ ᴀᴅᴅᴇᴅ ɪɴ ᴀ ɴᴇᴡ ɢʀᴏᴜᴘ</b></blockquote>

<blockquote>
🔖 <b>ᴄʜᴀᴛ ɴᴀᴍᴇ:</b> {chat_name}
🆔 <b>ᴄʜᴀᴛ ɪᴅ:</b> <code>{chat_id}</code>
👤 <b>ᴄʜᴀᴛ ᴜꜱᴇʀɴᴀᴍᴇ:</b> {chat_username}
🔗 <b>ᴄʜᴀᴛ ʟɪɴᴋ:</b> {chat_link}
👥 <b>ɢʀᴏᴜᴘ ᴍᴇᴍʙᴇʀs:</b> {members_count}
🤵 <b>ᴀᴅᴅᴇᴅ ʙʏ:</b> {added_by_name}
</blockquote>
"""

            try:
                await utils.send_media(
                    chat_id=config.LOGGER_ID,
                    media=config.START_IMG,
                    caption=text
                )
            except Exception as e:
                print(f"Failed to send new chat notification: {e}")

            break


# ==========================================
# 💌 THANK-YOU MESSAGE IN THE GROUP (image + Add Me / Help)
# ==========================================
# group=8 so it runs alongside (not instead of) the other new_chat_members handlers
@app.on_message(filters.new_chat_members & filters.group, group=8)
@lang.language()
async def bot_added_welcome(_, message: types.Message):
    if message.chat.type != enums.ChatType.SUPERGROUP:
        return

    if not any(member.id == app.id for member in message.new_chat_members):
        return

    adder = f" {message.from_user.mention}" if message.from_user else ""
    text = message.lang["added_gp"].format(
        html.escape(app.name or "Music Bot"),
        adder,
        html.escape(message.chat.title or ""),
    )
    key = buttons.added_key()

    try:
        await utils.send_media(
            chat_id=message.chat.id,
            media=config.ADD_IMG,
            caption=text,
            reply_markup=key,
        )
    except Exception:
        # image not allowed / bad link -> plain text fallback
        try:
            await app.send_message(
                chat_id=message.chat.id, text=text, reply_markup=key
            )
        except Exception:
            pass


# ==========================================
# 🔴 BOT REMOVED
# ==========================================
@app.on_message(filters.left_chat_member & filters.group)
async def left_chat_member(_, message: types.Message):

    if message.left_chat_member.id == app.id:
        chat = message.chat

        chat_name = chat.title
        chat_id = chat.id
        chat_username = f"@{chat.username}" if chat.username else "ᴘʀɪᴠᴀᴛᴇ ɢʀᴏᴜᴘ"

        removed_by = message.from_user
        removed_by_name = removed_by.mention if removed_by else "ᴜɴᴋɴᴏᴡɴ"

        # 🔗 LINK
        try:
            if chat.username:
                chat_link = f"https://t.me/{chat.username}"
            else:
                bot_member = await app.get_chat_member(chat_id, app.id)
                if bot_member.privileges and bot_member.privileges.can_invite_users:
                    chat_link = await app.export_chat_invite_link(chat_id)
                else:
                    chat_link = "<tg-emoji emoji-id='5852812849780362931'>❌</tg-emoji> ɴᴏ ɪɴᴠɪᴛᴇ ᴘᴇʀᴍɪssɪᴏɴ"
        except:
            chat_link = "<tg-emoji emoji-id='5852812849780362931'>❌</tg-emoji> ᴜɴᴀʙʟᴇ ᴛᴏ ɢᴇᴛ ʟɪɴᴋ"

        text = f"""<blockquote>🔴 <b>˹𝐄𝐥𝐞𝐯𝐞𝐧𝐲𝐭𝐬 ꭙ ᴍᴜꜱɪᴄ˼ ʀᴇᴍᴏᴠᴇᴅ ꜰʀᴏᴍ ᴀ ɢʀᴏᴜᴘ</b></blockquote>

<blockquote>
🔖 <b>ᴄʜᴀᴛ ɴᴀᴍᴇ:</b> {chat_name}
🆔 <b>ᴄʜᴀᴛ ɪᴅ:</b> <code>{chat_id}</code>
👤 <b>ᴄʜᴀᴛ ᴜꜱᴇʀɴᴀᴍᴇ:</b> {chat_username}
🔗 <b>ᴄʜᴀᴛ ʟɪɴᴋ:</b> {chat_link}
🚫 <b>ʀᴇᴍᴏᴠᴇᴅ ʙʏ:</b> {removed_by_name}
</blockquote>
"""

        try:
            await utils.send_media(
                chat_id=config.LOGGER_ID,
                media=config.START_IMG,
                caption=text
            )
        except Exception as e:
            print(f"Failed to send left chat notification: {e}")


# ==========================================
# 🔗 /LINK COMMAND (OWNER ONLY)
# ==========================================
@app.on_message(filters.command("link") & filters.private)
async def get_group_link(_, message: types.Message):

    # OWNER CHECK
    if message.from_user.id != config.OWNER_ID:
        return await message.reply_text("<tg-emoji emoji-id='5852812849780362931'>❌</tg-emoji> You are not authorized.")

    if len(message.command) < 2:
        return await message.reply_text("⚠️ Usage:\n/link <group_id>")

    try:
        chat_id = int(message.command[1])
    except:
        return await message.reply_text("<tg-emoji emoji-id='5852812849780362931'>❌</tg-emoji> Invalid group ID")

    try:
        chat = await app.get_chat(chat_id)

        if chat.username:
            link = f"https://t.me/{chat.username}"
        else:
            bot_member = await app.get_chat_member(chat_id, app.id)

            if bot_member.privileges and bot_member.privileges.can_invite_users:
                link = await app.export_chat_invite_link(chat_id)
            else:
                return await message.reply_text("<tg-emoji emoji-id='5852812849780362931'>❌</tg-emoji> No invite permission")

        await message.reply_text(
            f"🔗 <b>Group Link:</b>\n{link}",
            disable_web_page_preview=True
        )

    except ChannelPrivate:
        await message.reply_text("<tg-emoji emoji-id='5852812849780362931'>❌</tg-emoji> Bot is not in that group")

    except ChatAdminRequired:
        await message.reply_text("<tg-emoji emoji-id='5852812849780362931'>❌</tg-emoji> Bot is not admin")

    except Exception as e:
        await message.reply_text(f"<tg-emoji emoji-id='5852812849780362931'>❌</tg-emoji> Error:\n{e}")
