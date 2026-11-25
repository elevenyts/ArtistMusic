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
import asyncio
from typing import List, Tuple

from pyrogram import enums, errors, filters, types

from ArtistMusic import app, db, lang


# Global flag to track if a broadcast is currently running
broadcasting: bool = False


@app.on_message(filters.command(["broadcast"]) & app.sudo_filter)
@lang.language()
async def broadcast_message(_, message: types.Message) -> None:
    """
    Broadcast a message to all groups and/or users.

    Usage:
        /broadcast <reply to message> - Send message to all groups (as copy)
        /broadcast <text> - Send text to all groups
        /broadcast -user <reply to message> - Send to all groups and users
        /broadcast -nochat -user <message> - Send only to users

    Args:
        message: The Telegram message containing the broadcast command.

    Returns:
        None
    """
    # Auto-delete command message
    try:
        await message.delete()
    except Exception:
        pass
    
    global broadcasting

    # Check if another broadcast is already running
    if broadcasting:
        return await message.reply_text(message.lang["gcast_active"])

    # Determine if the command was a reply to a media message
    media_message = None
    media_group = None
    if message.reply_to_message:
        media_message = message.reply_to_message
        
        # Check if it's part of a media group (album)
        if media_message.media_group_id:
            try:
                # Get all messages in the media group
                media_group = await _get_media_group(message.chat.id, media_message)
            except Exception as e:
                # If fetching media group fails, just use single message
                pass

    # Parse command: extract flags and actual message
    flags, broadcast_text = _parse_broadcast_command(message.text)

    # Validate: either text or media must be present
    if not broadcast_text and not media_message:
        return await message.reply_text(message.lang["gcast_usage"])

    # Determine recipients based on flags
    groups, users = await _get_broadcast_recipients(flags)
    all_chats = groups + users

    if not all_chats:
        return await message.reply_text(
            "❌ No recipients found. Make sure the bot is added to groups or has users."
        )

    # Set broadcasting flag
    broadcasting = True
    sent = await message.reply_text(message.lang["gcast_start"])

    # Log broadcast initiation
    await _log_broadcast_start(message)
    await asyncio.sleep(5)

    # Perform the broadcast (supports text and media messages)
    success_groups, success_users, failed_chats = await _send_broadcast(
        broadcast_text, groups, users, sent, media_message, flags, message.lang, media_group
    )

    # Reset broadcasting flag
    broadcasting = False

    # Send completion message
    await _send_broadcast_completion(
        message, sent, success_groups, success_users, failed_chats, media_message
    )


@app.on_message(filters.command(["stop_gcast", "stop_broadcast"]) & app.sudo_filter)
@lang.language()
async def stop_broadcast(_, message: types.Message) -> None:
    """
    Stop an ongoing broadcast operation.

    Args:
        message: The Telegram message containing the stop command.

    Returns:
        None
    """
    # Auto-delete command message
    try:
        await message.delete()
    except Exception:
        pass
    
    global broadcasting

    if not broadcasting:
        return await message.reply_text(message.lang["gcast_inactive"])

    broadcasting = False

    # Log broadcast stop
    await (await app.send_message(
        chat_id=app.logger,
        text=message.lang["gcast_stop_log"].format(
            message.from_user.id,
            message.from_user.mention
        )
    )).pin(disable_notification=False)

    await message.reply_text(message.lang["gcast_stop"])


async def _get_media_group(chat_id: int, message: types.Message) -> List[types.Message]:
    """
    Get all messages in a media group (album).

    Args:
        chat_id: The chat ID where the media group is.
        message: One message from the media group.

    Returns:
        List of messages in the media group, sorted by message ID.
    """
    if not message.media_group_id:
        return None

    media_group_id = message.media_group_id
    messages = []
    
    # Search backward and forward from the current message to find all messages with same media_group_id
    # Telegram typically sends media group messages with consecutive IDs
    search_range = 20  # Search 20 messages before and after
    
    try:
        # Get messages around the replied message
        start_id = max(1, message.id - search_range)
        end_id = message.id + search_range
        
        for msg_id in range(start_id, end_id + 1):
            try:
                msg = await app.get_messages(chat_id, msg_id)
                if msg and hasattr(msg, 'media_group_id') and msg.media_group_id == media_group_id:
                    messages.append(msg)
            except:
                continue
                
        # Sort by message ID to maintain order
        messages.sort(key=lambda x: x.id)
        return messages if messages else None
    except Exception as e:
        return None


def _parse_broadcast_command(text: str) -> Tuple[List[str], str]:
    """
    Parse broadcast command to extract flags and message.

    Args:
        text: The full command text.

    Returns:
        Tuple of (flags list, message text)
    """
    # Handle None or empty text
    if not text:
        return [], ""

    # Split command from the rest (preserve everything after command)
    parts = text.split(None, 1)
    if len(parts) < 2:
        return [], ""

    remaining_text = parts[1]

    # Extract flags (words starting with '-') from the beginning
    flags = []
    lines = remaining_text.split('\n')
    first_line_parts = lines[0].split()

    # Collect flags only from first line
    message_start_index = 0
    for i, part in enumerate(first_line_parts):
        if part.startswith('-'):
            flags.append(part)
            message_start_index = i + 1
        else:
            # Stop collecting flags once we hit non-flag text
            break

    # Reconstruct message preserving all newlines and formatting
    if message_start_index > 0:
        # Remove flags from first line
        first_line_without_flags = ' '.join(
            first_line_parts[message_start_index:])
        if len(lines) > 1:
            message_text = first_line_without_flags + \
                '\n' + '\n'.join(lines[1:])
        else:
            message_text = first_line_without_flags
    else:
        message_text = remaining_text

    return flags, message_text.strip()


async def _get_broadcast_recipients(flags: List[str]) -> Tuple[List[int], List[int]]:
    """
    Get list of groups and users to broadcast to based on flags.

    Args:
        flags: List of command flags.

    Returns:
        Tuple of (groups list, users list)
    """
    groups = []
    users = []

    # Include groups unless -nochat flag is present
    if "-nochat" not in flags:
        groups = await db.get_chats()

    # Include users if -user flag is present
    if "-user" in flags:
        users = await db.get_users()

    return groups, users


async def _log_broadcast_start(message: types.Message) -> None:
    """
    Log broadcast initiation to logger group.

    Args:
        message: The original broadcast command message.

    Returns:
        None
    """
    try:
        log_message = await app.send_message(
            chat_id=app.logger,
            text=message.lang["gcast_log"].format(
                message.from_user.id,
                message.from_user.mention,
                message.text,
            )
        )
    except errors.FloodWait as fw:
        await asyncio.sleep(fw.value + 1)
        log_message = await app.send_message(
            chat_id=app.logger,
            text=message.lang["gcast_log"].format(
                message.from_user.id,
                message.from_user.mention,
                message.text,
            )
        )

    try:
        await log_message.pin(disable_notification=False)
    except errors.FloodWait as fw:
        await asyncio.sleep(fw.value + 1)
        try:
            await log_message.pin(disable_notification=False)
        except Exception:
            pass


async def _send_broadcast(
    text: str,
    groups: List[int],
    users: List[int],
    status_message: types.Message,
    media_message: types.Message | None = None,
    flags: List[str] = None,
    lang: dict = None,
    media_group: List[types.Message] = None,
) -> Tuple[int, int, str]:
    """
    Send broadcast message to all recipients (always as copy, no forward tag).

    Args:
        text: Message text to broadcast.
        groups: List of group chat IDs.
        users: List of user IDs.
        status_message: Message to update with progress.
        media_message: Optional media message to broadcast.
        flags: List of command flags.
        lang: Language dictionary for localized strings.
        media_group: Optional list of messages if broadcasting a media group (album).

    Returns:
        Tuple of (successful groups count, successful users count, failed chats log)
    """
    global broadcasting

    # Use provided flags or default to empty list
    if flags is None:
        flags = []

    success_groups = 0
    success_users = 0
    failed_log = ""
    pinned_count = 0
    all_chats = groups + users
    total_chats = len(all_chats)

    for index, chat_id in enumerate(all_chats, start=1):
        # Check if broadcast was stopped
        if not broadcasting:
            await status_message.edit_text(
                lang["gcast_stopped"].format(
                    success_groups, success_users)
            )
            break

        # Update progress every 50 chats
        if index % 50 == 0:
            try:
                await status_message.edit_text(
                    f"📤 Broadcasting...\n\n"
                    f"Progress: {index}/{total_chats}\n"
                    f"✅ Groups: {success_groups}\n"
                    f"✅ Users: {success_users}"
                )
            except:
                pass

        # Attempt to send message
        try:
            # Check if it's a channel (not a group) - skip channels
            if chat_id in groups:
                try:
                    chat = await app.get_chat(chat_id)
                    # Skip channels - only send to supergroups (groups)
                    if chat.type == enums.ChatType.CHANNEL:
                        failed_log += f"{chat_id} - Skipped (channel, not a group)\n"
                        continue
                except:
                    pass  # If can't get chat info, try to send anyway

            # Priority 1: If media_group exists (album), send as media group
            if media_group:
                sent_message = None
                try:
                    # ALWAYS use copy mode (no forward tag)
                    media_list = []
                    for idx, msg in enumerate(media_group):
                        # Use caption from first media or provided text
                        caption = text if (idx == 0 and text) else (msg.caption if idx == 0 else None)
                        
                        if msg.photo:
                            file_id = msg.photo.file_id if hasattr(msg.photo, 'file_id') else msg.photo[-1].file_id
                            media_list.append(types.InputMediaPhoto(media=file_id, caption=caption))
                        elif getattr(msg, 'video', None):
                            media_list.append(types.InputMediaVideo(media=msg.video.file_id, caption=caption))
                        elif getattr(msg, 'audio', None):
                            media_list.append(types.InputMediaAudio(media=msg.audio.file_id, caption=caption))
                        elif getattr(msg, 'document', None):
                            media_list.append(types.InputMediaDocument(media=msg.document.file_id, caption=caption))
                    
                    if media_list:
                        sent_messages = await app.send_media_group(chat_id=chat_id, media=media_list)
                        sent_message = sent_messages[0] if sent_messages else None
                        
                        # Handle pinning if requested (pin first message)
                        if sent_message and chat_id in groups:
                            if "-pin" in flags:
                                try:
                                    await sent_message.pin(disable_notification=True)
                                    pinned_count += 1
                                except:
                                    pass
                            elif "-pinloud" in flags:
                                try:
                                    await sent_message.pin(disable_notification=False)
                                    pinned_count += 1
                                except:
                                    pass
                    else:
                        failed_log += f"{chat_id} - No valid media in group\n"
                        await asyncio.sleep(0.3)
                        continue
                            
                except Exception as mg_ex:
                    failed_log += f"{chat_id} - Media group send failed: {type(mg_ex).__name__}: {str(mg_ex)}\n"
                    await asyncio.sleep(0.3)
                    continue

            # Priority 2: If a single media message was provided, ALWAYS send as copy (no forward tag)
            elif media_message:
                sent_message = None

                # ALWAYS use copy mode (no forward tag)
                caption = text if text else (media_message.caption or "")
                # Get caption entities to preserve formatting (blockquote, bold, italic, etc.)
                caption_entities = None if text else (media_message.caption_entities or None)
                
                try:
                    if media_message.photo:
                        # Photo is a list of PhotoSize objects, get the largest
                        file_id = media_message.photo.file_id if hasattr(
                            media_message.photo, 'file_id') else media_message.photo[-1].file_id
                        sent_message = await app.send_photo(chat_id=chat_id, photo=file_id, caption=caption, caption_entities=caption_entities)
                    elif getattr(media_message, 'video', None):
                        file_id = media_message.video.file_id
                        sent_message = await app.send_video(chat_id=chat_id, video=file_id, caption=caption, caption_entities=caption_entities)
                    elif getattr(media_message, 'audio', None):
                        file_id = media_message.audio.file_id
                        sent_message = await app.send_audio(chat_id=chat_id, audio=file_id, caption=caption, caption_entities=caption_entities)
                    elif getattr(media_message, 'voice', None):
                        file_id = media_message.voice.file_id
                        sent_message = await app.send_voice(chat_id=chat_id, voice=file_id, caption=caption, caption_entities=caption_entities)
                    elif getattr(media_message, 'document', None):
                        file_id = media_message.document.file_id
                        sent_message = await app.send_document(chat_id=chat_id, document=file_id, caption=caption, caption_entities=caption_entities)
                    elif getattr(media_message, 'animation', None):
                        file_id = media_message.animation.file_id
                        sent_message = await app.send_animation(chat_id=chat_id, animation=file_id, caption=caption, caption_entities=caption_entities)
                    elif getattr(media_message, 'sticker', None):
                        file_id = media_message.sticker.file_id
                        sent_message = await app.send_sticker(chat_id=chat_id, sticker=file_id)
                    else:
                        # Text-only message: send the text with formatting
                        message_text = text if text else (
                            media_message.text or media_message.caption or "")
                        # Get text entities to preserve formatting (blockquote, bold, italic, etc.)
                        message_entities = None if text else (media_message.entities or media_message.caption_entities or None)
                        if message_text:
                            sent_message = await app.send_message(chat_id, message_text, entities=message_entities)
                        else:
                            failed_log += f"{chat_id} - Empty message\n"
                            await asyncio.sleep(0.3)
                            continue

                    # Handle pinning if requested
                    if sent_message and chat_id in groups:
                        if "-pin" in flags:
                            try:
                                await sent_message.pin(disable_notification=True)
                                pinned_count += 1
                            except:
                                pass
                        elif "-pinloud" in flags:
                            try:
                                await sent_message.pin(disable_notification=False)
                                pinned_count += 1
                            except:
                                pass

                except Exception as send_ex:
                    failed_log += f"{chat_id} - Media send failed: {type(send_ex).__name__}: {str(send_ex)}\n"
                    await asyncio.sleep(0.3)
                    continue
                    
            else:
                # No media: send text message
                sent_message = await app.send_message(chat_id, text)

                # Handle pinning if requested
                if sent_message and chat_id in groups:
                    if "-pin" in flags:
                        try:
                            await sent_message.pin(disable_notification=True)
                            pinned_count += 1
                        except:
                            pass
                    elif "-pinloud" in flags:
                        try:
                            await sent_message.pin(disable_notification=False)
                            pinned_count += 1
                        except:
                            pass

            # Track success
            if chat_id in groups:
                success_groups += 1
            else:
                success_users += 1

            # Anti-flood delay: 300ms between messages
            await asyncio.sleep(0.3)

        except errors.FloodWait as fw:
            # Handle flood wait by waiting and continuing
            try:
                await status_message.edit_text(
                    f"⏳ Flood wait triggered. Waiting {fw.value} seconds...\n\n"
                    f"Progress: {index}/{total_chats}\n"
                    f"Don't worry, broadcast will continue!"
                )
            except:
                pass

            await asyncio.sleep(fw.value + 5)

            # Retry sending after waiting
            try:
                retry_sent = None
                
                # Retry media group if it was a media group
                if media_group:
                    media_list = []
                    for idx, msg in enumerate(media_group):
                        caption = text if (idx == 0 and text) else (msg.caption if idx == 0 else None)
                        if msg.photo:
                            file_id = msg.photo.file_id if hasattr(msg.photo, 'file_id') else msg.photo[-1].file_id
                            media_list.append(types.InputMediaPhoto(media=file_id, caption=caption))
                        elif getattr(msg, 'video', None):
                            media_list.append(types.InputMediaVideo(media=msg.video.file_id, caption=caption))
                        elif getattr(msg, 'audio', None):
                            media_list.append(types.InputMediaAudio(media=msg.audio.file_id, caption=caption))
                        elif getattr(msg, 'document', None):
                            media_list.append(types.InputMediaDocument(media=msg.document.file_id, caption=caption))
                    if media_list:
                        retry_msgs = await app.send_media_group(chat_id=chat_id, media=media_list)
                        retry_sent = retry_msgs[0] if retry_msgs else None
                
                # Retry single media message
                elif media_message:
                    caption = text if text else (media_message.caption or "")
                    caption_entities = None if text else (media_message.caption_entities or None)
                    
                    if media_message.photo:
                        file_id = media_message.photo.file_id if hasattr(media_message.photo, 'file_id') else media_message.photo[-1].file_id
                        retry_sent = await app.send_photo(chat_id=chat_id, photo=file_id, caption=caption, caption_entities=caption_entities)
                    elif getattr(media_message, 'video', None):
                        file_id = media_message.video.file_id
                        retry_sent = await app.send_video(chat_id=chat_id, video=file_id, caption=caption, caption_entities=caption_entities)
                    elif getattr(media_message, 'audio', None):
                        file_id = media_message.audio.file_id
                        retry_sent = await app.send_audio(chat_id=chat_id, audio=file_id, caption=caption, caption_entities=caption_entities)
                    elif getattr(media_message, 'voice', None):
                        file_id = media_message.voice.file_id
                        retry_sent = await app.send_voice(chat_id=chat_id, voice=file_id, caption=caption, caption_entities=caption_entities)
                    elif getattr(media_message, 'document', None):
                        file_id = media_message.document.file_id
                        retry_sent = await app.send_document(chat_id=chat_id, document=file_id, caption=caption, caption_entities=caption_entities)
                    elif getattr(media_message, 'animation', None):
                        file_id = media_message.animation.file_id
                        retry_sent = await app.send_animation(chat_id=chat_id, animation=file_id, caption=caption, caption_entities=caption_entities)
                    elif getattr(media_message, 'sticker', None):
                        file_id = media_message.sticker.file_id
                        retry_sent = await app.send_sticker(chat_id=chat_id, sticker=file_id)
                    else:
                        message_entities = None if text else (media_message.entities or media_message.caption_entities or None)
                        retry_sent = await app.send_message(chat_id, text, entities=message_entities)
                else:
                    retry_sent = await app.send_message(chat_id, text)

                # Handle pinning on retry
                if retry_sent and chat_id in groups:
                    if "-pin" in flags:
                        try:
                            await retry_sent.pin(disable_notification=True)
                            pinned_count += 1
                        except:
                            pass
                    elif "-pinloud" in flags:
                        try:
                            await retry_sent.pin(disable_notification=False)
                            pinned_count += 1
                        except:
                            pass

                if chat_id in groups:
                    success_groups += 1
                else:
                    success_users += 1
            except Exception as retry_ex:
                failed_log += f"{chat_id} - FloodWait retry failed: {retry_ex}\n"

        except errors.UserIsBlocked:
            # User blocked the bot - skip silently
            failed_log += f"{chat_id} - User blocked bot\n"
            continue

        except errors.ChatWriteForbidden:
            # Bot can't write in this chat - skip
            failed_log += f"{chat_id} - No write permission\n"
            continue

        except errors.ChannelPrivate:
            # Bot was removed from channel/group - remove from database
            if chat_id in groups:
                try:
                    await db.rm_chat(chat_id)
                    failed_log += f"{chat_id} - Removed from group (cleaned from database)\n"
                except:
                    failed_log += f"{chat_id} - Channel private (bot not member)\n"
            else:
                failed_log += f"{chat_id} - Channel private\n"
            continue

        except errors.PeerIdInvalid:
            # Invalid chat ID - remove from database
            if chat_id in groups:
                try:
                    await db.rm_chat(chat_id)
                    failed_log += f"{chat_id} - Invalid ID (cleaned from database)\n"
                except:
                    failed_log += f"{chat_id} - Invalid chat ID\n"
            else:
                failed_log += f"{chat_id} - Invalid user ID\n"
            continue

        except Exception as ex:
            # Log failed send but CONTINUE to next chat
            failed_log += f"{chat_id} - {type(ex).__name__}: {str(ex)}\n"
            continue

    return success_groups, success_users, failed_log


async def _send_broadcast_completion(
    message: types.Message,
    status_message: types.Message,
    success_groups: int,
    success_users: int,
    failed_log: str,
    media_message: types.Message | None = None,
) -> None:
    """
    Send broadcast completion message with results.

    Args:
        message: Original command message.
        status_message: Status message to edit.
        success_groups: Number of successful group sends.
        success_users: Number of successful user sends.
        failed_log: Log of failed sends.
        media_message: Optional media message that was broadcast.

    Returns:
        None
    """
    media_type = "text"
    if media_message:
        if media_message.photo:
            media_type = "photo"
        elif getattr(media_message, 'video', None):
            media_type = "video"
        elif getattr(media_message, 'audio', None):
            media_type = "audio"
        elif getattr(media_message, 'document', None):
            media_type = "document"
        elif getattr(media_message, 'animation', None):
            media_type = "animation"
        elif getattr(media_message, 'sticker', None):
            media_type = "sticker"

    completion_text = message.lang["gcast_end"].format(
        success_groups, success_users)
    if media_message:
        completion_text += f"\n📎 Media type: {media_type}"

    # If there were failures, send error file
    if failed_log:
        error_file = "errors.txt"
        with open(error_file, "w") as f:
            f.write(failed_log)

        await message.reply_document(
            document=error_file,
            caption=completion_text,
        )
        os.remove(error_file)

    await status_message.edit_text(completion_text)
