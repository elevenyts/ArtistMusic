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
import html
import time

from pyrogram import enums, filters, types
from pyrogram.errors import ChatAdminRequired, ChannelPrivate

from ArtistMusic import app, config
from ArtistMusic.helpers import utils


async def _send_group_welcome(chat, added_by) -> None:
    """Welcome message (image + Add Me / Help buttons) sent in the group itself."""
    chat_title = html.escape(chat.title or "this group")
    thanks = (
        f"Thank you {added_by.mention} for adding me to {chat_title} ♡"
        if added_by
        else f"Thank you for adding me to {chat_title} ♡"
    )
    caption = (
        "<b>♡ Thank You For Adding Me ♡\n\n"
        f"🎵 {html.escape(app.name or 'Music Bot')}\n\n"
        "🥀 Ready To Play Your Favourite Music.\n\n"
        f"{thanks}</b>"
    )
    markup = types.InlineKeyboardMarkup([[
        types.InlineKeyboardButton(
            text="ᴀᴅᴅ ᴍᴇ",
            url=f"https://t.me/{app.username}?startgroup=true",
        ),
        types.InlineKeyboardButton(text="ʜᴇʟᴘ", callback_data="help"),
    ]])
    try:
        await utils.send_media(
            chat_id=chat.id,
            media=config.START_IMG,
            caption=caption,
            reply_markup=markup,
        )
    except Exception:
        # Image failed (or no photo permission) -> plain text welcome
        try:
            await app.send_message(chat_id=chat.id, text=caption, reply_markup=markup)
        except Exception as e:
            print(f"Failed to send group welcome message: {e}")


_welcomed: dict = {}  # chat_id -> time of last welcome (stops double-sending)
_bg_tasks: set = set()


def _claim_welcome(chat_id: int) -> bool:
    """True only for the first trigger (join update or service message) per join."""
    now = time.time()
    for cid, ts in list(_welcomed.items()):
        if now - ts > 30:
            _welcomed.pop(cid, None)
    if chat_id in _welcomed:
        return False
    _welcomed[chat_id] = now
    return True


def _fire_welcome(chat, added_by) -> None:
    """Send the welcome in the background so nothing else can delay it."""
    task = asyncio.create_task(_send_group_welcome(chat, added_by))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)


# ==========================================
# ⚡ INSTANT WELCOME (fires the moment the bot is added)
# ==========================================
@app.on_chat_member_updated(filters.group, group=-10)
async def _bot_added_instant(_, update: types.ChatMemberUpdated):
    new = update.new_chat_member
    old = update.old_chat_member
    if not new or not new.user or new.user.id != app.id:
        return
    if new.status not in (
        enums.ChatMemberStatus.MEMBER,
        enums.ChatMemberStatus.ADMINISTRATOR,
    ):
        return
    if old and old.status in (
        enums.ChatMemberStatus.MEMBER,
        enums.ChatMemberStatus.ADMINISTRATOR,
        enums.ChatMemberStatus.OWNER,
    ):
        return  # was already in the group (e.g. just promoted)
    if not _claim_welcome(update.chat.id):
        return
    _fire_welcome(update.chat, update.from_user)


# ==========================================
# 🟢 BOT ADDED IN GROUP
# ==========================================
@app.on_message(filters.new_chat_members & filters.group, group=-10)
async def new_chat_member(_, message: types.Message):

    for member in message.new_chat_members:
        if member.id == app.id:
            chat = message.chat

            # Welcome message in the group right away (skipped if the join update already sent it)
            if _claim_welcome(chat.id):
                _fire_welcome(chat, message.from_user)

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
                        chat_link = "❌ ɴᴏ ɪɴᴠɪᴛᴇ ᴘᴇʀᴍɪssɪᴏɴ"
            except ChatAdminRequired:
                chat_link = "❌ ʙᴏᴛ ɴᴏᴛ ᴀᴅᴍɪɴ"
            except Exception:
                chat_link = "❌ ᴜɴᴀʙʟᴇ ᴛᴏ ɢᴇᴛ ʟɪɴᴋ"

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
                    chat_link = "❌ ɴᴏ ɪɴᴠɪᴛᴇ ᴘᴇʀᴍɪssɪᴏɴ"
        except:
            chat_link = "❌ ᴜɴᴀʙʟᴇ ᴛᴏ ɢᴇᴛ ʟɪɴᴋ"

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
        return await message.reply_text("❌ You are not authorized.")

    if len(message.command) < 2:
        return await message.reply_text("⚠️ Usage:\n/link <group_id>")

    try:
        chat_id = int(message.command[1])
    except:
        return await message.reply_text("❌ Invalid group ID")

    try:
        chat = await app.get_chat(chat_id)

        if chat.username:
            link = f"https://t.me/{chat.username}"
        else:
            bot_member = await app.get_chat_member(chat_id, app.id)

            if bot_member.privileges and bot_member.privileges.can_invite_users:
                link = await app.export_chat_invite_link(chat_id)
            else:
                return await message.reply_text("❌ No invite permission")

        await message.reply_text(
            f"🔗 <b>Group Link:</b>\n{link}",
            disable_web_page_preview=True
        )

    except ChannelPrivate:
        await message.reply_text("❌ Bot is not in that group")

    except ChatAdminRequired:
        await message.reply_text("❌ Bot is not admin")

    except Exception as e:
        await message.reply_text(f"❌ Error:\n{e}")
