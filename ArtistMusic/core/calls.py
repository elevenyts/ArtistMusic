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
import logging
from ntgcalls import ConnectionNotFound, TelegramServerError
from pyrogram import enums, errors
from pyrogram.errors import MessageIdInvalid
from pyrogram.types import InputMediaPhoto, Message
from pytgcalls import PyTgCalls, exceptions, types
from pytgcalls.pytgcalls_session import PyTgCallsSession

from ArtistMusic import app, config, db, lang, logger, preload, queue, userbot, yt
from ArtistMusic.core.autoplay import autoplay
from ArtistMusic.helpers import Media, Track, buttons, thumb, utils

# Suppress pytgcalls harmless errors (library bugs - not critical)


class PyTgCallsErrorFilter(logging.Filter):
    def filter(self, record):
        # Filter out UpdateGroupCall errors
        if 'UpdateGroupCall' in record.getMessage():
            return False
        # Filter out ConnectionNotFound errors (happens when call ends but updates still arrive)
        if 'Connection with chat id' in record.getMessage() and 'not found' in record.getMessage():
            return False
        return True


logging.getLogger('pyrogram.dispatcher').addFilter(PyTgCallsErrorFilter())


class TgCall(PyTgCalls):
    def __init__(self):
        self.clients = []
        self._play_next_locks = {}  # Lock to prevent concurrent play_next calls per chat
        self._stream_end_cache = {}  # Cache to prevent duplicate stream end processing

    async def _edit_media_with_retry(self, message: Message, media_obj: InputMediaPhoto, reply_markup):
        """Edit media with basic FloodWait handling."""
        try:
            return await message.edit_media(media=media_obj, reply_markup=reply_markup)
        except errors.FloodWait as fw:
            await asyncio.sleep(fw.value + 1)
            try:
                return await message.edit_media(media=media_obj, reply_markup=reply_markup)
            except Exception:
                return None
        except errors.MessageNotModified:
            return None
        except Exception:
            return None

    async def _send_photo_with_retry(self, chat_id: int, photo, caption: str, reply_markup):
        """Send photo with FloodWait handling."""
        try:
            return await utils.send_media(
                chat_id=chat_id,
                media=photo,
                caption=caption,
                reply_markup=reply_markup,
                spoiler=True,
            )
        except errors.FloodWait as fw:
            await asyncio.sleep(fw.value + 1)
            try:
                return await utils.send_media(
                    chat_id=chat_id,
                    media=photo,
                    caption=caption,
                    reply_markup=reply_markup,
                    spoiler=True,
                )
            except Exception as e:
                logger.error(f"Now Playing photo send failed after FloodWait for {chat_id}: {e}")
                return None
        except Exception as e:
            logger.error(f"Now Playing photo send failed for {chat_id}: {e}")
            return None

    async def pause(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        try:
            await client.pause(chat_id)
            await db.playing(chat_id, paused=True)
            return True
        except (ConnectionNotFound, exceptions.NotInCallError):
            await db.playing(chat_id, paused=False)
            await db.remove_call(chat_id)
            queue.clear(chat_id)
            logger.warning(
                f"Pause requested but assistant not in call for {chat_id}, syncing state")
            return False
        except Exception as e:
            await db.playing(chat_id, paused=False)
            logger.error(f"Pause failed for {chat_id}: {e}")
            return False

    async def resume(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        try:
            await client.resume(chat_id)
            await db.playing(chat_id, paused=False)
            return True
        except (ConnectionNotFound, exceptions.NotInCallError):
            await db.playing(chat_id, paused=False)
            await db.remove_call(chat_id)
            queue.clear(chat_id)
            logger.warning(
                f"Resume requested but assistant not in call for {chat_id}, syncing state")
            return False
        except Exception as e:
            logger.error(f"Resume failed for {chat_id}: {e}")
            return False

    async def stop(self, chat_id: int) -> None:
        client = await db.get_assistant(chat_id)

        # Cancel any active preload tasks when stopping
        try:
            await preload.cancel_preload(chat_id)
        except Exception as e:
            logger.debug(f"Error cancelling preload for {chat_id}: {e}")

        try:
            queue.clear(chat_id)
            await db.remove_call(chat_id)
        except Exception as e:
            logger.warning(f"Error clearing queue/call for {chat_id}: {e}")

        try:
            await client.leave_call(chat_id, close=False)
            # Small delay to let group call state stabilize after leaving
            await asyncio.sleep(0.5)
        except (ConnectionNotFound, exceptions.NotInCallError):
            # Expected: userbot is not in a call
            pass
        except Exception as e:
            # Only log unexpected errors
            error_msg = str(e).lower()
            if not any(ignore in error_msg for ignore in [
                "not in a call",
                "not in the group call",
                "groupcall_forbidden",
                "no active group call",
                "call was already stopped",
                "call already disconnected"
            ]):
                logger.warning(f"Error leaving call for {chat_id}: {e}")

    async def play_media(
        self,
        chat_id: int,
        message: Message | None,
        media: Media | Track,
        seek_time: int = 0,
        message_chat_id: int = None,
        _retry: bool = True,
    ) -> None:
        """Play media in voice chat.

        Args:
            chat_id: Where to stream audio (could be channel in channel play mode)
            message: Message to edit/delete (if any)
            media: Media object to play
            seek_time: Position to seek to (seconds)
            message_chat_id: Where to send control messages (group chat in channel play mode)
                           If None, messages go to same chat as audio (chat_id)
        """
        client = await db.get_assistant(chat_id)
        _lang = await lang.get_lang_for(getattr(media, "user_id", None), chat_id)
        await db.get_autoplay(chat_id)  # warm cache for the autoplay button

        # Determine where messages should go:
        # - If message_chat_id provided (channel play): send to group
        # - Otherwise: send to same chat as audio
        target_chat_for_messages = message_chat_id if message_chat_id else chat_id

        # NOTE: Thumbnail is NOT generated here anymore.
        # First the song starts in the VC, then the thumbnail is generated
        # (see below, right after client.play() succeeds).

        if not media.file_path:
            if message:
                return await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            else:
                logger.error(f"No file path for media in {chat_id}")
                return

        # Validate chat_id - check if it's a valid channel/group
        try:
            chat = await app.get_chat(chat_id)
            if chat.type not in [enums.ChatType.SUPERGROUP, enums.ChatType.GROUP, enums.ChatType.CHANNEL]:
                logger.error(f"Invalid chat type for {chat_id}: {chat.type}")
                if message:
                    await message.edit_text("❌ Can only play in groups/channels.")
                return
            # For channels, verify assistant is member
            if chat.type == enums.ChatType.CHANNEL:
                # Get the userbot (Pyrogram client) to access .me attribute
                userbot_client = await db.get_client(chat_id)
                if not userbot_client:
                    logger.error(f"No userbot client available for {chat_id}")
                    if message:
                        await message.edit_text("❌ No assistant available.")
                    return

                try:
                    assistant_member = await app.get_chat_member(chat_id, userbot_client.me.id)
                    if assistant_member.status == enums.ChatMemberStatus.BANNED:
                        logger.error(f"Assistant banned in channel {chat_id}")
                        if message:
                            await message.edit_text("❌ Assistant is banned in this channel.")
                        # Disable channel play
                        await db.set_cmode(chat_id, None)
                        return
                except errors.RPCError as e:
                    if "CHANNEL_INVALID" in str(e) or "USER_NOT_PARTICIPANT" in str(e):
                        logger.error(
                            f"Assistant not in channel {chat_id}: {e}")
                        if message:
                            await message.edit_text(
                                "❌ <b>Assistant not in channel!</b>\n\n"
                                f"<blockquote>Please add @{userbot_client.me.username} to the channel as admin with voice chat permissions.</blockquote>"
                            )
                        # Disable channel play
                        await db.set_cmode(chat_id, None)
                        return
        except errors.RPCError as e:
            if "CHANNEL_INVALID" in str(e):
                logger.error(f"Invalid channel {chat_id}: {e}")
                if message:
                    await message.edit_text("❌ Invalid channel. Disabling channel play.")
                await db.set_cmode(chat_id, None)  # Disable channel play
                return
            raise

        # Configure audio stream with optimized buffering for lag-free playback
        # PERFORMANCE FIX: Increased buffers prevent stuttering/lagging during playback
        if seek_time > 1:
            # Seeking: Still need buffers but skip to position first
            ffmpeg_params = f"-ss {seek_time} -probesize 10M -analyzeduration 5M -rtbufsize 5M -fflags +genpts+igndts"
        else:
            # Normal playback with aggressive buffering:
            # - probesize 10M: Large input buffer (prevents underruns)
            # - analyzeduration 5M: Analyze more data (better format detection)
            # - rtbufsize 5M: Real-time buffer (crucial for network streams)
            # - fflags +genpts+igndts: Generate PTS, ignore DTS (smooth playback)
            # - sync ext: External sync (reduces A/V desync)
            ffmpeg_params = "-probesize 10M -analyzeduration 5M -rtbufsize 5M -fflags +genpts+igndts -sync ext"

        # URL source: auto-reconnect if the connection drops mid-song
        _src = str(media.file_path)
        if _src.startswith(("http://", "https://")) and not getattr(media, "is_live", False):
            ffmpeg_params += " -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"

        is_video = getattr(media, "video", False)
        video_flags = (
            types.MediaStream.Flags.AUTO_DETECT
            if is_video
            else types.MediaStream.Flags.IGNORE
        )

        stream = types.MediaStream(
            media_path=media.file_path,
            audio_parameters=types.AudioQuality.STUDIO,
            audio_flags=types.MediaStream.Flags.REQUIRED,
            video_flags=video_flags,
            ffmpeg_parameters=ffmpeg_params,
        )

        try:
            call = await client.get_call(chat_id)
            if call:
                logger.debug(
                    f"Already connected to {chat_id}, leaving before reconnecting...")
                await client.leave_call(chat_id, close=False)
        except (ConnectionNotFound, exceptions.NotInCallError):
            pass
        except Exception as e:
            logger.debug(f"Error checking connection state for {chat_id}: {e}")

        max_retries = 3
        retry_delay = 1

        try:
            for attempt in range(max_retries):
                try:
                    await client.play(
                        chat_id=chat_id,
                        stream=stream,
                        config=types.GroupCallConfig(auto_start=True),
                    )
                    break
                except (exceptions.NoActiveGroupCall, errors.RPCError) as e:
                    error_msg = str(e)
                    if "GROUPCALL_INVALID" in error_msg or "GROUPCALL" in error_msg or isinstance(e, exceptions.NoActiveGroupCall):
                        if attempt < max_retries - 1:
                            logger.debug(
                                f"Group call transitioning for {chat_id}, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            raise
                    else:
                        raise
                except Exception as e:
                    error_msg = str(e).lower()
                    if "cannot be initialized more than once" in error_msg or "connection" in error_msg:
                        if attempt < max_retries - 1:
                            logger.debug(
                                f"Connection error for {chat_id}, leaving and retrying... (attempt {attempt + 1}/{max_retries})")
                            try:
                                await client.leave_call(chat_id, close=False)
                                await asyncio.sleep(retry_delay)
                            except Exception:
                                pass
                            continue
                        else:
                            raise
                    else:
                        raise

            if seek_time:
                media.time = seek_time
            else:
                media.time = 1

            if not seek_time:
                await db.add_call(chat_id)
                text = _lang["play_media"].format(
                    media.url,
                    media.title,
                    media.duration,
                    media.user,
                )
                if not media.is_live and media.duration_sec:
                    import time as time_module
                    played = media.time
                    duration = media.duration_sec
                    bar_length = 9
                    if duration == 0:
                        percentage = 0
                    else:
                        percentage = min((played / duration) * 100, 100)
                    filled = int(round(bar_length * percentage / 100))
                    timer_bar = "▰" * filled + "▱" * (bar_length - filled)
                    if duration >= 3600:
                        played_time = time_module.strftime(
                            '%H:%M:%S', time_module.gmtime(played))
                        total_time = time_module.strftime(
                            '%H:%M:%S', time_module.gmtime(duration))
                    else:
                        played_time = time_module.strftime(
                            '%M:%S', time_module.gmtime(played))
                        total_time = time_module.strftime(
                            '%M:%S', time_module.gmtime(duration))
                    timer_text = f"{played_time} {timer_bar} {total_time}"
                    keyboard = buttons.controls(chat_id, timer=timer_text)
                else:
                    keyboard = buttons.controls(chat_id)

                # ✅ Song is already playing in the VC at this point.
                # Now generate the thumbnail (and the rest of the post-play work).
                if config.THUMB_GEN and isinstance(media, Track):
                    try:
                        _thumb = await thumb.generate(media)
                    except Exception as e:
                        logger.debug(f"Thumbnail generation failed for {chat_id}: {e}")
                        _thumb = config.DEFAULT_THUMB
                else:
                    _thumb = config.DEFAULT_THUMB

                if message:
                    try:
                        await message.delete()
                    except Exception:
                        pass

                sent_photo = await self._send_photo_with_retry(
                    chat_id=target_chat_for_messages,
                    photo=_thumb,
                    caption=text,
                    reply_markup=keyboard,
                )
                if sent_photo:
                    media.message_id = sent_photo.id

                try:
                    asyncio.create_task(
                        preload.start_preload(chat_id))
                except Exception as e:
                    logger.debug(f"Error starting preload for {chat_id}: {e}")
        except FileNotFoundError:
            logger.warning(f"File not found for media in {chat_id}, skipping to next track")
            if message:
                try:
                    await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
                except Exception:
                    pass
            await self.play_next(chat_id)  # play_next itself calls queue.get_next(), advancing past the bad track
        except exceptions.NoActiveGroupCall:
            await self.stop(chat_id)
            if message:
                try:
                    await message.edit_text(_lang["error_vc_disabled"])
                except Exception:
                    pass
        except errors.RPCError as e:
            error_str = str(e)

            if any(x in error_str for x in ["CHAT_ADMIN_REQUIRED", "phone.CreateGroupCall", "GROUPCALL_FORBIDDEN", "GROUPCALL_CREATE_FORBIDDEN", "VOICE_MESSAGES_FORBIDDEN"]):
                await self.stop(chat_id)
                if message:
                    try:
                        await message.edit_text(_lang["error_vc_disabled"])
                    except Exception:
                        pass
            elif "GROUPCALL_INVALID" in error_str or "GROUPCALL" in error_str:
                await self.stop(chat_id)
                if message:
                    try:
                        await message.edit_text(_lang["error_no_call"])
                    except Exception:
                        pass
            else:
                logger.error(f"RPC error in play_media for {chat_id}: {e}")
                await self.stop(chat_id)
        except exceptions.NoAudioSourceFound:
            # ffmpeg found no audio in the file -> it is a broken download (often a cached API
            # error body). Delete ONLY this song's file, download it again and retry once.
            media_id = getattr(media, "id", None)
            if _retry and not getattr(media, "is_live", False) and yt.is_yt_id(media_id):
                is_vid = getattr(media, "video", False)
                try:
                    logger.warning(f"No audio in file for {media_id} — deleting and re-downloading")
                    await yt.purge_bad_download(media_id, video=is_vid, force=True)
                    media.file_path = await yt.download(media_id, video=is_vid)
                except Exception as e:
                    logger.warning(f"Re-download failed for {media_id}: {e}")
                    media.file_path = None
                if media.file_path:
                    return await self.play_media(
                        chat_id, message, media, seek_time=seek_time,
                        message_chat_id=message_chat_id, _retry=False,
                    )
            if message:
                try:
                    await message.edit_text(_lang["error_no_audio"])
                except Exception:
                    pass
            await self.play_next(chat_id)
        except (ConnectionNotFound, TelegramServerError):
            await self.stop(chat_id)
            if message:
                try:
                    await message.edit_text(_lang["error_tg_server"])
                except Exception:
                    pass
        except TimeoutError as e:
            error_msg = str(e)
            logger.warning(
                f"⏱️ Timeout joining voice chat {chat_id}: {error_msg}")
            await self.stop(chat_id)
            if message:
                try:
                    await message.edit_text(
                        "⏱️ <b>Connection timed out!</b>\n\n"
                        "<blockquote>Failed to join voice chat. Please check your network and try again.</blockquote>"
                    )
                except Exception:
                    pass
            await asyncio.sleep(2)
            await self.play_next(chat_id)
        except Exception as e:
            logger.error(
                f"Unexpected error in play_media for {chat_id}: {e}", exc_info=True)
            await self.stop(chat_id)
            if message:
                try:
                    await message.edit_text(f"❌ Playback error: {str(e)[:100]}")
                except Exception:
                    pass

    async def replay(self, chat_id: int) -> None:
        try:
            if not await db.get_call(chat_id):
                return

            message_chat_id = None
            try:
                chat = await app.get_chat(chat_id)
                if chat.type == enums.ChatType.CHANNEL:
                    group_id = await db.get_group_for_channel(chat_id)
                    if group_id:
                        message_chat_id = group_id
            except Exception:
                pass

            media = queue.get_current(chat_id)
            _lang = await lang.get_lang_for(getattr(media, "user_id", None), chat_id)
            target_chat = message_chat_id if message_chat_id else chat_id
            msg = await app.send_message(chat_id=target_chat, text=_lang["play_again"])
            await self.play_media(chat_id, msg, media, message_chat_id=message_chat_id)
        except Exception as e:
            logger.error(f"Error in replay for {chat_id}: {e}", exc_info=True)

    async def seek_stream(self, chat_id: int, seconds: int) -> bool:
        """Seek to a specific position in the current stream."""
        try:
            if not await db.get_call(chat_id):
                return False

            media = queue.get_current(chat_id)
            if not media or media.is_live:
                return False

            client = await db.get_assistant(chat_id)
            _lang = await lang.get_lang_for(getattr(media, "user_id", None), chat_id)

            message_chat_id = None
            try:
                chat = await app.get_chat(chat_id)
                if chat.type == enums.ChatType.CHANNEL:
                    group_id = await db.get_group_for_channel(chat_id)
                    if group_id:
                        message_chat_id = group_id
            except Exception:
                pass

            media.time = seconds

            target_chat = message_chat_id if message_chat_id else chat_id

            try:
                msg = await app.get_messages(target_chat, media.message_id)
            except Exception:
                msg = None

            if not msg:
                _lang = await lang.get_lang_for(getattr(media, "user_id", None), chat_id)
                msg = await app.send_message(chat_id=target_chat, text=_lang["seeking"])

            await self.play_media(chat_id, msg, media, seek_time=seconds, message_chat_id=message_chat_id)
            return True
        except Exception as e:
            logger.warning(f"Seek stream failed for {chat_id}: {e}")
            return False

    async def play_next(self, chat_id: int) -> None:
        # setdefault is atomic in Python's GIL — safe from race conditions
        lock = self._play_next_locks.setdefault(chat_id, asyncio.Lock())

        if lock.locked():
            logger.info(
                f"play_next already running for {chat_id}, skipping duplicate call")
            return

        async with lock:
            try:
                if not await db.get_call(chat_id):
                    return

                message_chat_id = None
                try:
                    chat = await app.get_chat(chat_id)
                    if chat.type == enums.ChatType.CHANNEL:
                        group_id = await db.get_group_for_channel(chat_id)
                        if group_id:
                            message_chat_id = group_id
                except Exception:
                    pass

                target_chat = message_chat_id if message_chat_id else chat_id

                loop_mode = await db.get_loop(chat_id)

                if loop_mode == 1:
                    media = queue.get_current(chat_id)
                    if media:
                        _lang = await lang.get_lang_for(getattr(media, "user_id", None), chat_id)
                        try:
                            msg = await app.send_message(chat_id=target_chat, text=_lang["play_again"])
                            await self.play_media(chat_id, msg, media, message_chat_id=message_chat_id)
                        except errors.ChannelPrivate:
                            logger.warning(
                                f"Bot removed from {chat_id}, cleaning up")
                            try:
                                await self.leave_call(chat_id)
                            except (AttributeError, Exception) as leave_ex:
                                logger.debug(
                                    f"Could not leave call for {chat_id}: {leave_ex}")
                            await db.rm_chat(chat_id)
                        return

                finished = queue.get_current(chat_id)  # kept for autoplay
                media = queue.get_next(chat_id)

                if not media and loop_mode == 10:
                    all_items = queue.get_all(chat_id)
                    if all_items:
                        first_track = all_items[0]
                        _lang = await lang.get_lang_for(getattr(first_track, "user_id", None), chat_id)
                        try:
                            msg = await app.send_message(chat_id=target_chat, text="🔁 Looping queue...")
                            if not first_track.file_path:
                                # stream-first (handles live streams too)
                                first_track.file_path = await yt.get_play_source(first_track)
                            first_track.message_id = msg.id
                            await self.play_media(chat_id, msg, first_track, message_chat_id=message_chat_id)
                        except errors.ChannelPrivate:
                            logger.warning(
                                f"Bot removed from {chat_id}, cleaning up")
                            await self.leave_call(chat_id)
                            await db.rm_chat(chat_id)
                        return

                try:
                    if media and media.message_id:
                        await app.delete_messages(
                            chat_id=chat_id,
                            message_ids=media.message_id,
                            revoke=True,
                        )
                        media.message_id = 0
                except Exception as e:
                    logger.debug(
                        f"Could not delete previous message in {chat_id}: {e}")

                if not media and finished and await self._try_autoplay(
                    chat_id, target_chat, message_chat_id, finished
                ):
                    return

                if not media:
                    if config.AUTO_END:
                        _lang = await lang.get_lang(chat_id)
                        try:
                            await app.send_message(
                                chat_id=chat_id,
                                text=_lang.get(
                                    "auto_end", "✅ Queue finished. Stream ended automatically.")
                            )
                        except Exception as e:
                            logger.debug(
                                f"Could not send auto_end message in {chat_id}: {e}")
                    return await self.stop(chat_id)

                _lang = await lang.get_lang_for(getattr(media, "user_id", None), chat_id)
                msg = None
                if not media.file_path:
                    media.file_path = await yt.get_play_source(media)
                    if not media.file_path:
                        await self.stop(chat_id)
                        if msg:
                            try:
                                await msg.edit_text(
                                    _lang["error_no_file"].format(
                                        config.SUPPORT_CHAT)
                                )
                            except Exception:
                                pass
                        return

                try:
                    msg = await app.send_message(chat_id=target_chat, text=_lang["play_next"])
                except errors.FloodWait as fw:
                    # Do not block playback on UI flood waits; continue without message.
                    logger.warning(
                        f"FloodWait in play_next for {chat_id}: skipping status message ({fw.value}s)")
                    msg = None
                except errors.ChannelPrivate:
                    logger.warning(f"Bot removed from {chat_id}, cleaning up")
                    await self.leave_call(chat_id)
                    await db.rm_chat(chat_id)
                    return
                except Exception as e:
                    logger.error(
                        f"Failed to send play_next message for {chat_id}: {e}")
                    msg = None

                media.message_id = msg.id if msg else 0
                if msg:
                    await self.play_media(chat_id, msg, media, message_chat_id=message_chat_id)
                else:
                    logger.info(
                        f"Playing next track for {chat_id} without message update")
                    await self.play_media(chat_id, None, media, message_chat_id=message_chat_id)

                try:
                    asyncio.create_task(
                        preload.start_preload(chat_id))
                except Exception as e:
                    logger.debug(
                        f"Error starting preload after play_next for {chat_id}: {e}")
            except Exception as e:
                logger.error(
                    f"Error in play_next for {chat_id}: {e}", exc_info=True)
                try:
                    await self.stop(chat_id)
                except Exception:
                    pass

    async def _has_listeners(self, chat_id: int) -> bool | None:
        """True if someone besides the assistant is in the VC, None if unknown."""
        try:
            client = await db.get_assistant(chat_id)
            participants = await client.get_participants(chat_id)
            return len(participants) >= 2
        except Exception as e:
            logger.debug(f"Could not read VC participants for {chat_id}: {e}")
            return None

    async def _try_autoplay(self, chat_id: int, target_chat: int, message_chat_id, finished) -> bool:
        """Queue ended: play a similar song if autoplay is ON and someone is listening.

        Returns True if a new song started. If the VC is empty, autoplay is
        switched OFF and False is returned so the stream ends normally.
        """
        try:
            if not await db.get_autoplay(chat_id):
                return False

            listeners = await self._has_listeners(chat_id)
            if listeners is not True:
                if listeners is False:
                    # VC is empty -> turn autoplay off
                    await db.set_autoplay(chat_id, False)
                    autoplay.forget(chat_id)
                    try:
                        await app.send_message(
                            chat_id=target_chat,
                            text=(
                                "<blockquote>⏹ <b>Autoplay: OFF</b>\n\n"
                                "Nobody was in the VC, so autoplay has been turned off.\n"
                                "Use /autoplay again to turn it on.</blockquote>"
                            ),
                        )
                    except Exception:
                        pass
                return False

            try:
                msg = await app.send_message(
                    chat_id=target_chat, text="🔎 Finding the next song from the playlist..."
                )
            except Exception:
                msg = None

            async def _fail(text: str) -> bool:
                if msg:
                    try:
                        await msg.edit_text(text)
                    except Exception:
                        pass
                return False

            track = await autoplay.find_next(chat_id, finished)
            if not track:
                return await _fail("❌ Autoplay: no similar song found.")

            track.video = getattr(finished, "video", False)
            track.file_path = await yt.get_play_source(track)
            if not track.file_path:
                return await _fail("❌ Autoplay: failed to fetch the next song.")

            track.message_id = msg.id if msg else 0
            queue.add(chat_id, track)
            await self.play_media(chat_id, msg, track, message_chat_id=message_chat_id)

            try:
                asyncio.create_task(preload.start_preload(chat_id))
            except Exception:
                pass
            return True
        except Exception as e:
            logger.error(f"Autoplay failed for {chat_id}: {e}", exc_info=True)
            queue.clear(chat_id)  # drop half-added track so stop() starts clean
            return False

    async def ping(self) -> float:
        pings = [client.ping for client in self.clients]
        return round(sum(pings) / len(pings), 2)

    async def decorators(self, client: PyTgCalls) -> None:
        for client in self.clients:
            @client.on_update()
            async def update_handler(_, update: types.Update) -> None:
                if isinstance(update, types.StreamEnded):
                    if update.stream_type == types.StreamEnded.Type.AUDIO:
                        chat_id = update.chat_id
                        current_time = asyncio.get_event_loop().time()

                        if chat_id in self._stream_end_cache:
                            if current_time - self._stream_end_cache[chat_id] < 2.0:
                                return

                        self._stream_end_cache[chat_id] = current_time

                        self._stream_end_cache = {
                            cid: t for cid, t in self._stream_end_cache.items()
                            if current_time - t < 5.0
                        }

                        await self.play_next(chat_id)
                elif isinstance(update, types.ChatUpdate):
                    if update.status in [
                        types.ChatUpdate.Status.KICKED,
                        types.ChatUpdate.Status.LEFT_GROUP,
                        types.ChatUpdate.Status.CLOSED_VOICE_CHAT,
                    ]:
                        await self.stop(update.chat_id)
                elif isinstance(update, getattr(types, "UpdatedGroupCallParticipant", ())):
                    # "who joined / who left the VC" alerts (Artistbots/vclog.py)
                    try:
                        from ArtistMusic.Artistbots.vclog import handle_participant
                        asyncio.create_task(handle_participant(update))
                    except Exception as e:
                        logger.debug(f"vclog hook failed: {e}")

    async def boot(self) -> None:
        PyTgCallsSession.notice_displayed = True
        for ub in userbot.clients:
            client = PyTgCalls(ub, cache_duration=100)
            await client.start()
            self.clients.append(client)
            await self.decorators(client)
        logger.info("📞 PyTgCalls client(s) started.")
