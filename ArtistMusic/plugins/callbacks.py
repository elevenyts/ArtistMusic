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

import re
import asyncio
from functools import wraps

from pyrogram import filters, types
from pyrogram.errors import FloodWait, QueryIdInvalid

from ArtistMusic import tune, app, config, db, lang, logger, queue, tg, yt
from ArtistMusic.helpers import admin_check, buttons, can_manage_vc, utils


def safe_callback(func):
    """Decorator to handle exceptions in callback handlers."""
    @wraps(func)
    async def wrapper(client, query: types.CallbackQuery):
        try:
            return await func(client, query)
        except QueryIdInvalid:
            return
        except Exception as e:
            logger.error(f"Error in callback {func.__name__}: {e}", exc_info=True)
            try:
                await query.answer("❌ An error occurred. Please try again.", show_alert=True)
            except Exception:
                pass
    return wrapper


@app.on_callback_query(filters.regex("^start$") & ~app.bl_users)
@lang.language()
@safe_callback
async def _start_callback(_, query: types.CallbackQuery):
    """Handle start button callback - return to start message."""
    await query.answer()
    
    _text = query.lang["start_pm"].format(query.from_user.first_name, app.name)
    key = buttons.start_key(query.lang, True)
    
    try:
        await query.edit_message_caption(
            caption=_text,
            reply_markup=key,
        )
    except Exception:
        try:
            await query.edit_message_text(
                text=_text,
                reply_markup=key,
            )
        except Exception:
            pass


@app.on_callback_query(filters.regex("cancel_dl") & ~app.bl_users)
@lang.language()
@safe_callback
async def cancel_dl(_, query: types.CallbackQuery):
    await query.answer()
    await tg.cancel(query)


@app.on_callback_query(filters.regex("controls") & ~app.bl_users)
@lang.language()
@safe_callback
async def _controls(_, query: types.CallbackQuery):
    args = query.data.split()
    action, chat_id = args[1], int(args[2])

    # FIX #1: qaction ab sirf arg-count pe nahi, "q" value pe check hota hai.
    # Warna play_queued() wale 4-arg callbacks (jinme item_id hota hai)
    # galti se queue_markup wale flow me chale jaate the.
    qaction = len(args) == 4 and args[3] == "q"
    item_id = args[3] if len(args) == 4 and args[3] != "q" else None

    user = query.from_user.mention

    # Handle close action first - allow any user to delete the message (no popup notification)
    if action == "close":
        await query.answer()
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    # Check admin permissions for all other controls
    # Inline permission check: sudo users, authorized users, or group admins
    user_id = query.from_user.id
    has_permission = False
    
    if user_id in app.sudoers:
        has_permission = True
    elif await db.is_auth(chat_id, user_id):
        has_permission = True
    else:
        admins = await db.get_admins(chat_id)
        if user_id in admins:
            has_permission = True
    
    if not has_permission:
        return await query.answer("⚠️ You don't have permission to use this.", show_alert=True)

    if not await db.get_call(chat_id):
        return await query.answer(query.lang["not_playing"], show_alert=True)

    if action == "status":
        return await query.answer()
    
    # Handle seek actions
    if action.startswith("seek_"):
        return await handle_seek(query, chat_id, action, user)
    
    # Handle loop action
    if action == "loop":
        return await handle_loop(query, chat_id, user)
    
    # Handle shuffle action
    if action == "shuffle":
        return await handle_shuffle(query, chat_id, user)
    
    await query.answer(query.lang["processing"], show_alert=True)

    if action == "pause":
        if not await db.playing(chat_id):
            return await query.answer(
                query.lang["play_already_paused"], show_alert=True
            )
        if not await tune.pause(chat_id):
            return await query.answer(query.lang["not_playing"], show_alert=True)
        if qaction:
            return await query.edit_message_reply_markup(
                reply_markup=buttons.queue_markup(
                    chat_id, query.lang["paused"], False)
            )
        status = query.lang["paused"]
        reply = query.lang["play_paused"].format(user)

    elif action == "resume":
        status = query.lang["playing"]
        if await db.playing(chat_id):
            return await query.answer(query.lang["play_not_paused"], show_alert=True)
        if not await tune.resume(chat_id):
            return await query.answer(query.lang["not_playing"], show_alert=True)
        if qaction:
            return await query.edit_message_reply_markup(
                reply_markup=buttons.queue_markup(
                    chat_id, query.lang["playing"], True)
            )
        reply = query.lang["play_resumed"].format(user)

    elif action == "skip":
        await tune.play_next(chat_id)
        status = query.lang["skipped"]
        reply = query.lang["play_skipped"].format(user)

    elif action == "force":
        pos, media = queue.check_item(chat_id, args[3])
        if not media or pos == -1:
            return await query.edit_message_text(query.lang["play_expired"])

        current = queue.get_current(chat_id)
        m_id = current.message_id if current else None
        queue.force_add(chat_id, media, remove=pos)
        try:
            await app.delete_messages(
                chat_id=chat_id, message_ids=[
                    m_id, media.message_id], revoke=True
            )
            media.message_id = None
        except:
            pass

        msg = await app.send_message(chat_id=chat_id, text=query.lang["play_next"])
        if not media.file_path:
            media.file_path = await yt.download(
                media.id,
                video=getattr(media, "video", False),
            )
        media.message_id = msg.id
        return await tune.play_media(chat_id, msg, media)

    elif action == "replay":
        media = queue.get_current(chat_id)
        media.user = user
        media.user_id = query.from_user.id
        await tune.replay(chat_id)
        status = query.lang["replayed"]
        reply = query.lang["play_replayed"].format(user)

    elif action == "stop":
        await tune.stop(chat_id)
        status = query.lang["stopped"]
        reply = query.lang["play_stopped"].format(user)

    try:
        if action in ["skip", "replay", "stop"]:
            sent_msg = None
            try:
                sent_msg = await utils.reply(query.message, text=reply, quote=False)
            except FloodWait as e:
                # If FloodWait occurs, wait and retry once
                await asyncio.sleep(e.value)
                try:
                    sent_msg = await utils.reply(query.message, text=reply, quote=False)
                except Exception:
                    pass
            except Exception:
                pass
            await query.message.delete()
            
            # Auto-delete the reply message after 5 seconds
            if sent_msg:
                await asyncio.sleep(5)
                try:
                    await sent_msg.delete()
                except Exception:
                    pass
        else:
            # FIX #2: mtext/keyboard sirf yahin (pause/resume/etc) chahiye the,
            # lekin edit_message_text pehle if/else ke BAAHAR tha isliye
            # skip/replay/stop ke baad bhi chalne ki koshish karta tha aur
            # mtext/keyboard undefined hone se NameError deta tha (jo bare
            # except se silently swallow ho jata tha). Ab andar hi edit call hai.
            mtext = re.sub(
                r"\n\n<blockquote>.*?</blockquote>",
                "",
                query.message.caption.html or query.message.text.html,
                flags=re.DOTALL,
            )
            keyboard = buttons.controls(
                chat_id, status=status if action != "resume" else None
            )
            await query.edit_message_text(
                f"{mtext}\n\n<blockquote>{reply}</blockquote>", reply_markup=keyboard
            )
    except FloodWait as e:
        # Handle FloodWait on edit_message_text
        await asyncio.sleep(e.value)
        try:
            await query.edit_message_text(
                f"{mtext}\n\n<blockquote>{reply}</blockquote>", reply_markup=keyboard
            )
        except Exception:
            pass
    except Exception:
        pass


async def handle_seek(query: types.CallbackQuery, chat_id: int, action: str, user: str):
    """Handle seek forward/backward actions."""
    media = queue.get_current(chat_id)
    if not media or media.is_live:
        return await query.answer("⚠️ Cannot seek in live streams!", show_alert=True)
    
    if not media.duration_sec or media.duration_sec == 0:
        return await query.answer("⚠️ Cannot seek in this track!", show_alert=True)
    
    # Determine seek amount and direction
    if action == "seek_back_10":
        seconds = -10
        label = "« 10s"
    elif action == "seek_back_30":
        seconds = -30
        label = "« 30s"
    elif action == "seek_forward_10":
        seconds = 10
        label = "10s »"
    elif action == "seek_forward_30":
        seconds = 30
        label = "30s »"
    else:
        return await query.answer("⚠️ Invalid seek action!", show_alert=True)
    
    # Calculate new position
    current_time = getattr(media, 'time', 0)
    new_time = max(0, min(current_time + seconds, media.duration_sec - 5))
    
    # Check if we're at the boundaries
    if new_time == 0 and seconds < 0:
        return await query.answer(f"⏮️ Already at the beginning!", show_alert=True)
    if new_time >= media.duration_sec - 5 and seconds > 0:
        return await query.answer(f"⏭️ Too close to the end!", show_alert=True)
    
    # Perform seek
    success = await tune.seek_stream(chat_id, int(new_time))
    if success:
        # Format time display
        import time as time_module
        if media.duration_sec >= 3600:
            time_str = time_module.strftime('%H:%M:%S', time_module.gmtime(new_time))
        else:
            time_str = time_module.strftime('%M:%S', time_module.gmtime(new_time))
        
        # Use callback answer to avoid FloodWait
        _dir = "⏩ ꜰᴏʀᴡᴀʀᴅᴇᴅ" if seconds > 0 else "⏪ ʀᴇᴡɪɴᴅᴇᴅ"
        await query.answer(f"Seeked to {time_str}", show_alert=True)
        
        # Try to send reply message with FloodWait handling and auto-delete after 5 seconds
        try:
            sent_msg = await utils.reply(
                query.message,
                text=f"<blockquote><b>{_dir}</b>\n\n⏱  ᴅᴜʀᴀᴛɪᴏɴ ╌ {time_str}\n👤  ʙʏ ╌ {user}</blockquote>",
                quote=False,
            )
            # Auto-delete after 5 seconds
            await asyncio.sleep(5)
            try:
                await sent_msg.delete()
            except Exception:
                pass
        except FloodWait as e:
            # If rate limited, just skip the message since user already got feedback via callback
            pass
        except Exception:
            pass


async def handle_loop(query: types.CallbackQuery, chat_id: int, user: str):
    """Handle loop mode toggling."""
    current_loop = await db.get_loop(chat_id)
    
    # Cycle through loop modes: 0 (off) -> 1 (single) -> 10 (queue) -> 0
    if current_loop == 0:
        new_loop = 1
        text = "🔂 Loop: Single Track"
        message = f"🔂 Loop mode set to <b>Single Track</b>"
    elif current_loop == 1:
        new_loop = 10
        text = "🔁 Loop: Queue"
        message = f"🔁 Loop mode set to <b>Queue</b>"
    else:
        new_loop = 0
        text = "➡️ Loop: Off"
        message = f"➡️ Loop mode <b>Disabled</b>"
    
    await db.set_loop(chat_id, new_loop)
    await query.answer(text, show_alert=False)
    await utils.reply(query.message, text=message, quote=False)


async def handle_shuffle(query: types.CallbackQuery, chat_id: int, user: str):
    """Handle queue shuffling."""
    import random
    
    items = queue.get_queue(chat_id)
    if not items or len(items) <= 1:
        return await query.answer("⚠️ Queue is empty or has only one track!", show_alert=True)
    
    # Get current track and remove from list
    current = items[0] if items else None
    remaining = items[1:] if len(items) > 1 else []
    
    if not remaining:
        return await query.answer("⚠️ No tracks to shuffle!", show_alert=True)
    
    # Shuffle remaining tracks
    random.shuffle(remaining)
    
    # Rebuild queue with current track first
    queue.clear(chat_id)
    if current:
        queue.add(chat_id, current)
    for item in remaining:
        queue.add(chat_id, item)
    
    await query.answer("🔀 Queue shuffled!", show_alert=False)
    await utils.reply(
        query.message,
        text=f"🔀 Queue <b>shuffled</b> ({len(remaining)} tracks)",
        quote=False,
    )


@app.on_callback_query(filters.regex(r"^help") & ~app.bl_users)
@lang.language()
async def _help(_, query: types.CallbackQuery):
    await query.answer()
    
    # Handle plain "help" callback - show main menu
    if query.data == "help":
        try:
            # Try to edit as photo message first
            await query.edit_message_caption(
                caption=query.lang["help_menu"], 
                reply_markup=buttons.help_markup(query.lang)
            )
        except Exception:
            # Fallback to text edit if not a photo message
            try:
                await query.edit_message_text(
                    text=query.lang["help_menu"], 
                    reply_markup=buttons.help_markup(query.lang)
                )
            except Exception:
                pass
        return
    
    category = query.data.replace("help_", "")
    
    if category == "main":
        # Return to main help menu from category
        try:
            await query.edit_message_caption(
                caption=query.lang["help_menu"], 
                reply_markup=buttons.help_markup(query.lang)
            )
        except Exception:
            try:
                await query.edit_message_text(
                    text=query.lang["help_menu"], 
                    reply_markup=buttons.help_markup(query.lang)
                )
            except Exception:
                pass
        return

    if category == "langs":
        try:
            await query.edit_message_caption(
                caption=query.lang["lang_select"],
                reply_markup=buttons.langs_markup(),
            )
        except Exception:
            try:
                await query.edit_message_text(
                    text=query.lang["lang_select"],
                    reply_markup=buttons.langs_markup(),
                )
            except Exception:
                pass
        return

    # Handle all help categories
    help_texts = {
        "admins": query.lang["help_admins"],
        "auth": query.lang["help_auth"],
        "broadcast": query.lang["help_sudo"],  # Broadcast is sudo feature
        "blchat": query.lang["help_blchat"],
        "bluser": query.lang["help_bluser"],
        "gban": query.lang["help_gban"],
        "loop": query.lang["help_loop"],
        "play": query.lang["help_play"],
        "queue": query.lang["help_queue"],
        "seek": query.lang["help_seek"],
        "shuffle": query.lang["help_shuffle"],
        "ping": query.lang["help_ping"],
        "stats": query.lang["help_stats"],
        "sudo": query.lang["help_sudo"],
        "maintenance": query.lang["help_maintenance"],
    }
    
    help_text = help_texts.get(category, query.lang["help_admins"])
    
    try:
        await query.edit_message_caption(
            caption=help_text,
            reply_markup=buttons.help_markup(query.lang, True),
        )
    except Exception:
        try:
            await query.edit_message_text(
                text=help_text,
                reply_markup=buttons.help_markup(query.lang, True),
            )
        except Exception:
            pass


_LANG_NAMES = {
    "en": "🇬🇧 English", "hi": "🇮🇳 Hindi", "te": "🇮🇳 Telugu",
    "ko": "🇰🇷 Korean", "my": "🇲🇲 Myanmar", "id": "🇮🇩 Indonesian",
    "pt": "🇧🇷 Portuguese", "ar": "🇸🇦 Arabic", "es": "🇪🇸 Spanish",
    "fr": "🇫🇷 French", "ru": "🇷🇺 Russian", "de": "🇩🇪 German",
    "tr": "🇹🇷 Turkish", "bn": "🇧🇩 Bengali", "th": "🇹🇭 Thai",
    "vi": "🇻🇳 Vietnamese", "ja": "🇯🇵 Japanese", "zh": "🇨🇳 Chinese",
    "ur": "🇵🇰 Urdu", "fa": "🇮🇷 Persian",
    "bho": "🇮🇳 Bhojpuri", "ne": "🇳🇵 Nepali",
}


@app.on_callback_query(filters.regex(r"^setlang_") & ~app.bl_users)
async def _setlang(_, query: types.CallbackQuery):
    code = query.data.replace("setlang_", "")
    if code not in _LANG_NAMES:
        return await query.answer("❌ Invalid language.", show_alert=True)
    lang_name = _LANG_NAMES[code]
    # Saved against the user, not the chat — so it follows them into DM
    # and every group, instead of only affecting the chat they clicked in.
    await db.set_user_lang(query.from_user.id, code)
    new_lang = lang.get_merged_lang(code)
    confirmation = new_lang["lang_changed"].format(lang_name)
    await query.answer()
    try:
        await query.edit_message_caption(
            caption=confirmation,
            reply_markup=buttons.langs_markup(),
        )
    except Exception:
        try:
            await query.edit_message_text(
                text=confirmation,
                reply_markup=buttons.langs_markup(),
            )
        except Exception:
            pass


@app.on_callback_query(filters.regex("^playmode$") & ~app.bl_users)
@lang.language()
@admin_check
async def _playmode(_, query: types.CallbackQuery):
    await query.answer(query.lang["processing"], show_alert=True)
    chat_id = query.message.chat.id
    admin_only = await db.get_play_mode(chat_id)
    force_admin = await db.get_force_mode(chat_id)
    _language = "en"
    await db.set_play_mode(chat_id, admin_only)
    await query.edit_message_reply_markup(
        reply_markup=buttons.settings_markup(
            query.lang,
            not admin_only,
            force_admin,
            _language,
            chat_id,
        )
    )


@app.on_callback_query(filters.regex("^forcemode$") & ~app.bl_users)
@lang.language()
@admin_check
async def _forcemode(_, query: types.CallbackQuery):
    await query.answer(query.lang["processing"], show_alert=True)
    chat_id = query.message.chat.id
    admin_only = await db.get_play_mode(chat_id)
    force_admin = await db.get_force_mode(chat_id)
    _language = "en"
    await db.set_force_mode(chat_id, force_admin)
    await query.edit_message_reply_markup(
        reply_markup=buttons.settings_markup(
            query.lang,
            admin_only,
            not force_admin,
            _language,
            chat_id,
        )
    )
