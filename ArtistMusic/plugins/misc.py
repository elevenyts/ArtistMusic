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
import time

import pyrogram
from pyrogram import enums, filters, types

from ArtistMusic import tune, app, config, db, lang, logger, queue, tasks, userbot, yt
from ArtistMusic.helpers import buttons


@app.on_message(filters.regex(r"^/") & ~filters.service, group=-1)
async def _maintenance_mode_check(_, m: types.Message):
    """
    Global maintenance mode check - runs before all other handlers.
    Blocks non-sudo users when maintenance mode is enabled.
    Only triggers for bot commands (starting with /)
    """
    # Skip check for sudo users
    if not m.from_user or m.from_user.id in app.sudoers:
        return
    
    # Check if maintenance mode is enabled
    maintenance = await db.get_maintenance()
    if maintenance:
        # Block non-sudo user with maintenance message
        try:
            await m.reply_text(
                "<blockquote><b>🔧 Bot Under Maintenance</b>\n\n"
                "The bot is currently undergoing maintenance.\n"
                "Please try again later.</blockquote>"
            )
        except Exception:
            pass
        # Stop propagation - don't process any further handlers
        raise pyrogram.StopPropagation


@app.on_message(filters.video_chat_started, group=19)
@app.on_message(filters.video_chat_ended, group=20)
async def _watcher_vc(_, m: types.Message):
    await tune.stop(m.chat.id)


async def auto_leave():
    """Auto-leave inactive groups. Runs in background with error recovery."""
    while True:
        try:
            await asyncio.sleep(1800)
            for ub in userbot.clients:
                left = 0
                try:
                    for dialog in await ub.get_dialogs():
                        chat_id = dialog.chat.id
                        if left >= 20:
                            break
                        # Skip logger and any excluded chats
                        excluded = [app.logger] + config.EXCLUDED_CHATS
                        if chat_id in excluded:
                            continue
                        if dialog.chat.type in [
                            enums.ChatType.GROUP,
                            enums.ChatType.SUPERGROUP,
                        ]:
                            if chat_id in db.active_calls:
                                continue
                            await ub.leave_chat(chat_id)
                            left += 1
                        await asyncio.sleep(5)
                except Exception as e:
                    logger.error(f"Auto-leave error for assistant {ub.me.username if hasattr(ub, 'me') and ub.me else 'Unknown'}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Critical error in auto_leave task: {e}")
            await asyncio.sleep(60)  # Wait before retrying
            continue


async def track_time():
    """Track playback time. Runs in background with error recovery."""
    while True:
        try:
            await asyncio.sleep(1)
            for chat_id in list(db.active_calls):
                try:
                    if not await db.playing(chat_id):
                        continue
                    media = queue.get_current(chat_id)
                    if not media:
                        continue
                    media.time += 1
                except Exception as e:
                    # Log error but continue tracking other chats
                    logger.debug(f"track_time error for chat {chat_id}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Critical error in track_time task: {e}")
            await asyncio.sleep(1)  # Brief pause before retrying
            continue


async def update_timer(length=10):
    """Update progress bar every 20 seconds for all active chats independently."""
    chat_tasks = {}  # Track individual chat update tasks

    async def _preload_next(chat_id, next_media):
        """Pre-download next song without blocking timer updates."""
        try:
            next_media.file_path = await yt.download(
                next_media.id,
                video=getattr(next_media, "video", False),
            )
        except Exception as e:
            print(f"Preload error for chat {chat_id}: {e}")

    async def update_chat_timer(chat_id):
        """Update timer for a specific chat every 20 seconds."""
        while True:
            try:
                await asyncio.sleep(20)

                # Check if chat is still active and playing
                if chat_id not in db.active_calls or not await db.playing(chat_id):
                    break

                media = queue.get_current(chat_id)
                if not media:
                    break

                # Ensure media.time is initialized
                if not hasattr(media, 'time') or media.time is None:
                    media.time = 0

                duration, message_id = media.duration_sec, media.message_id
                if not duration or not message_id:
                    continue

                played = media.time
                remaining = duration - played
                # Generate progress bar (clean block style)
                bar_length = 9
                if duration == 0:
                    percentage = 0
                else:
                    percentage = min((played / duration) * 100, 100)
                filled = int(round(bar_length * percentage / 100))
                timer_bar = "▰" * filled + "▱" * (bar_length - filled)

                # Pre-download next song if needed (don't block timer update)
                if remaining <= 30:
                    next = queue.get_next(chat_id, check=True)
                    if next and not next.file_path:
                        asyncio.create_task(_preload_next(chat_id, next))

                if remaining < 10:
                    remove = True
                    timer_text = timer_bar
                else:
                    remove = False
                    # Format time properly with hours support
                    if duration >= 3600:
                        played_time = time.strftime('%H:%M:%S', time.gmtime(played))
                        total_time = time.strftime('%H:%M:%S', time.gmtime(duration))
                    else:
                        played_time = time.strftime('%M:%S', time.gmtime(played))
                        total_time = time.strftime('%M:%S', time.gmtime(duration))
                    timer_text = f"{played_time} {timer_bar} {total_time}"

                await app.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=buttons.controls(
                        chat_id=chat_id, timer=timer_text, remove=remove),
                )
            except Exception as e:
                error_str = str(e)
                # Silently ignore expected Telegram API errors
                if not any(err in error_str for err in [
                    "MESSAGE_NOT_MODIFIED",
                    "MESSAGE_ID_INVALID",
                    "MESSAGE_DELETE",
                    "MESSAGE_AUTHOR_REQUIRED",
                    "CHAT_ADMIN_REQUIRED",
                    "CHANNEL_PRIVATE",
                    "haven't joined this channel"
                ]):
                    print(f"update_timer error for chat {chat_id}: {e}")
                # Stop tracking chats with CHANNEL_PRIVATE errors
                if "CHANNEL_PRIVATE" in error_str:
                    break
                await asyncio.sleep(1)  # Brief pause before retry

    # Monitor and spawn individual chat timers
    while True:
        await asyncio.sleep(2)  # Check for new chats every 2 seconds

        for chat_id in list(db.active_calls):
            # Start timer for new active chats
            if chat_id not in chat_tasks:
                task = asyncio.create_task(update_chat_timer(chat_id))
                chat_tasks[chat_id] = task

        # Clean up finished tasks
        finished_chats = [
            chat_id for chat_id, task in chat_tasks.items()
            if task.done() or chat_id not in db.active_calls
        ]
        for chat_id in finished_chats:
            chat_tasks.pop(chat_id, None)


async def vc_watcher(sleep=15):
    """Leave voice chat after 5 minutes if no users are listening."""
    alone_times = {}  # Track when assistant started being alone in VC
    LEAVE_TIMEOUT = 300  # 5 minutes in seconds (hardcoded)
    
    while True:
        await asyncio.sleep(sleep)
        current_time = time.time()
        
        for chat_id in list(db.active_calls):
            try:
                # Check if auto-leave is enabled for this chat
                if not await db.get_autoleave(chat_id):
                    alone_times.pop(chat_id, None)
                    continue
                
                client = await db.get_assistant(chat_id)
                
                # Check if userbot is actually in the call
                try:
                    participants = await client.get_participants(chat_id)
                except Exception as call_err:
                    # Userbot is not in the call or call doesn't exist
                    # Remove from tracking and continue
                    alone_times.pop(chat_id, None)
                    continue
                
                # Check if only assistant is in VC (participants < 2 means only assistant)
                if len(participants) < 2:
                    # Start tracking alone time
                    if chat_id not in alone_times:
                        alone_times[chat_id] = current_time
                    else:
                        # Check if alone for 5 minutes
                        alone_duration = current_time - alone_times[chat_id]
                        if alone_duration >= LEAVE_TIMEOUT:
                            _lang = await lang.get_lang(chat_id)
                            try:
                                current_media = queue.get_current(chat_id)
                                if current_media and current_media.message_id:
                                    sent = await app.edit_message_reply_markup(
                                        chat_id=chat_id,
                                        message_id=current_media.message_id,
                                        reply_markup=buttons.controls(
                                            chat_id=chat_id, status=_lang["stopped"], remove=True
                                        ),
                                    )
                                    await sent.reply_text(_lang["auto_left"])
                            except:
                                pass
                            
                            # Stop playback and leave
                            await tune.stop(chat_id)
                            try:
                                await client.leave_call(chat_id, close=False)
                            except Exception as e:
                                # Suppress expected call disconnection errors
                                error_msg = str(e).lower()
                                if not any(ignore in error_msg for ignore in [
                                    "not in a call",
                                    "not in the group call",
                                    "no active group call",
                                    "call was already stopped",
                                    "call already disconnected"
                                ]):
                                    print(f"Error leaving call for {chat_id}: {e}")
                            alone_times.pop(chat_id, None)
                else:
                    # Reset timer if users join
                    alone_times.pop(chat_id, None)
                    
            except Exception as e:
                print(f"vc_watcher error for chat {chat_id}: {e}")
                alone_times.pop(chat_id, None)
                continue


# Always run VC watcher to check for empty voice chats
tasks.append(asyncio.create_task(vc_watcher()))
if config.AUTO_LEAVE:
    tasks.append(asyncio.create_task(auto_leave()))
tasks.append(asyncio.create_task(track_time()))
tasks.append(asyncio.create_task(update_timer()))
