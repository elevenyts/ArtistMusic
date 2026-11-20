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
from pyrogram import types
from pyrogram.enums import ButtonStyle
from pyrogram.errors import FloodWait, MessageIdInvalid, MessageDeleteForbidden, ChatSendPlainForbidden, ChatWriteForbidden

from ArtistMusic import tune, app, config, db, lang, queue, tg, yt
from ArtistMusic.helpers import buttons, utils
from ArtistMusic.helpers._play import checkUB
import asyncio
import html
import logging

logger = logging.getLogger(__name__)


# ── Music search -> download animation ────────────────────────────────────
# Frame 1 (instantly)  : 🔍🎶 sєᴧʀᴄʜɪηɢ ғσʀ: <query> ... ⚡✨
# Frame 2 (after ~1 s) : 📥 ᴅσᴡηʟσᴧᴅɪηɢ sσηɢ "<song title> ..."
_FRAME_MIN_SECONDS = 1.0  # how long the "searching" frame stays visible at least


def _short(text: str, limit: int = 40) -> str:
    """Trim + HTML-escape text so it is safe inside a Telegram HTML message."""
    text = " ".join(str(text).split())
    if len(text) > limit:
        text = text[:limit].rstrip()
    return html.escape(text)


def _searching_text(query: str) -> str:
    return f"🔍🎶 sєᴧʀᴄʜɪηɢ ғσʀ: {_short(query)} ... ⚡✨"


def _downloading_text(title: str) -> str:
    return f'📥 ᴅσᴡηʟσᴧᴅɪηɢ sσηɢ "{_short(title)} ..."'


_bg_edits: set = set()


async def _show_downloading(sent, started_at: float, title: str) -> None:
    """
    Switch the "searching" frame to the "downloading" frame.
    No artificial wait and not awaited: the download starts immediately and the
    message edit happens in the background.
    """
    t = asyncio.create_task(safe_edit(sent, _downloading_text(title)))
    _bg_edits.add(t)
    t.add_done_callback(_bg_edits.discard)


async def safe_edit(message, text, **kwargs):
    """
    Safely edit a message with proper error handling for common Telegram API errors.
    
    Args:
        message: The message object to edit
        text: New text content
        **kwargs: Additional arguments for edit_text
        
    Returns:
        True if successful, False otherwise
    """
    try:
        await message.edit_text(text, **kwargs)
        return True
    except FloodWait as e:
        await asyncio.sleep(e.value)
        try:
            await message.edit_text(text, **kwargs)
            return True
        except (MessageIdInvalid, MessageDeleteForbidden, Exception):
            return False
    except (MessageIdInvalid, MessageDeleteForbidden):
        # Message was deleted or became invalid - this is expected
        return False
    except Exception:
        # Other errors - log but don't crash
        return False


async def safe_reply(message, text, **kwargs):
    """
    Safely send a reply message with proper error handling for media-only chats.
    
    Args:
        message: The message object to reply to
        text: Text content to send
        **kwargs: Additional arguments for reply_text
        
    Returns:
        The sent message object if successful, None otherwise
    """
    try:
        return await message.reply_text(text, **kwargs)
    except (ChatSendPlainForbidden, ChatWriteForbidden):
        logger.warning(f"Cannot send text in chat {message.chat.id} (chat write forbidden)")
        return None
    except Exception as e:
        logger.error(f"Failed to send reply: {e}")
        return None


def queue_controls(chat_id: int, item_id: str) -> types.InlineKeyboardMarkup:
    """Single "Play Now" button for the "Added to queue" message."""
    return buttons.ikm([[
        buttons.ikb(
            text="▷ Ƥℓᴀʏ Nσω",
            callback_data=f"controls force {chat_id} {item_id}",
            style=ButtonStyle.PRIMARY,
        )
    ]])


def playlist_to_queue(chat_id: int, tracks: list) -> str:
    """
    Add multiple tracks to queue and format them as a message.
    
    Args:
        chat_id: The chat ID where queue is managed
        tracks: List of Track objects to add
        
    Returns:
        Formatted string listing all added tracks
    """
    text = "<blockquote expandable>"
    for track in tracks:
        pos = queue.add(chat_id, track)  # Add track to queue (returns 0-based index)
        text += f"<b>{pos}.</b> {track.title}\n"  # Show actual queue position
    text = text[:1948] + "</blockquote>"  # Limit message length
    return text

@app.on_message(
    filters.command(
        [
            "play",
            "playforce",
            "cplay",
            "cplayforce",
            "vplay",
            "vplayforce",
            "cvplay",
            "cvplayforce",
        ]
    )
    & filters.group
    & ~app.bl_users
)
@lang.language()
@checkUB
async def play_hndlr(
    _,
    m: types.Message,
    force: bool = False,
    url: str = None,
    cplay: bool = False,
    video: bool = False,
) -> None:
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    # Handle channel play mode
    chat_id = m.chat.id
    message_chat_id = m.chat.id  # Store original group chat ID for thumbnail
    if cplay:
        channel_id = await db.get_cmode(m.chat.id)
        if channel_id is None:
            return await safe_reply(m,
                "<blockquote>❌ Channel play is not enabled.\n\n"
                "To enable for linked channel:\n"
                "`/channelplay linked`\n\n"
                "To enable for any channel:\n"
                "`/channelplay [channel_id]`</blockquote>"
            )
        try:
            chat = await app.get_chat(channel_id)
            chat_id = channel_id
        except:
            await db.set_cmode(m.chat.id, None)
            return await safe_reply(m,
                "<blockquote>❌ Cannot find channel!\n\n"
                "Please make sure I'm admin in the channel and channel exists.</blockquote>"
            )
        
        # Auto-join assistant to channel if not already a member
        client = await db.get_client(channel_id)
        try:
            # Check if assistant is in the channel
            await app.get_chat_member(channel_id, client.id)
        except Exception:
            # Assistant not in channel, try to join
            try:
                # For channels, we need an invite link
                if chat.username:
                    invite_link = chat.username
                else:
                    # Try to get/create invite link
                    try:
                        invite_link = chat.invite_link
                        if not invite_link:
                            invite_link = await app.export_chat_invite_link(channel_id)
                    except Exception:
                        return await safe_reply(m,
                            f"<blockquote>❌ Assistant cannot join channel!\n\n"
                            f"Please add @{client.username if client.username else client.mention} "
                            f"to the channel as an admin with permission to join.</blockquote>"
                        )
                
                # Show joining message
                join_msg = await safe_reply(m,
                    f"<blockquote>🔌 Joining assistant to channel...</blockquote>"
                )
                
                # Try to join the channel
                await client.join_chat(invite_link)
                await asyncio.sleep(1)  # Give it time to fully join
                
                # Delete joining message
                try:
                    await join_msg.delete()
                except:
                    pass
                    
            except Exception as e:
                error_str = str(e)
                return await safe_reply(m,
                    f"<blockquote>❌ Failed to join assistant to channel!\n\n"
                    f"Please manually add @{client.username if client.username else client.mention} "
                    f"to the channel as an admin with permission to join.\n\n"
                    f"Error: {error_str}</blockquote>"
                )

    # Send animated searching message (frame 1)
    if url:
        _label = url
    elif len(m.command) >= 2:
        _label = " ".join(m.command[1:])
    else:
        _label = "your song"
    _searching_msg = _searching_text(_label)

    try:
        sent = await safe_reply(m, _searching_msg)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        try:
            sent = await safe_reply(m, _searching_msg)
        except FloodWait as e2:
            await asyncio.sleep(e2.value)
            return
        except Exception:
            return
    except Exception:
        return

    if not sent:
        return
    _anim_start = asyncio.get_running_loop().time()

    mention = m.from_user.mention
    media = tg.get_media(m.reply_to_message) if m.reply_to_message else None
    tracks = []
    file = None  # Initialize file variable

    # Check media first (Telegram files) before URL extraction
    if media:
        setattr(sent, "lang", m.lang)
        file = await tg.download(m.reply_to_message, sent)

    elif url:
        if "playlist" in url:
            await safe_edit(sent, m.lang["playlist_fetch"])
            try:
                tracks = await yt.playlist(
                    config.PLAYLIST_LIMIT, mention, url
                )
            except Exception as e:
                await safe_edit(
                    sent,
                    f"<blockquote>❌ Failed to fetch playlist.\n\n"
                    f"YouTube playlists are currently experiencing issues. "
                    f"Please try a single track instead.</blockquote>"
                )
                return

            if not tracks:
                await safe_edit(sent, m.lang["playlist_error"])
                return

            file = tracks[0]
            tracks.remove(file)
            file.message_id = sent.id
        else:
            file = await yt.search(url, sent.id)

        if not file:
            await safe_edit(
                sent,
                m.lang["play_not_found"].format(config.SUPPORT_CHAT)
            )
            return

    elif len(m.command) >= 2:
        query = " ".join(m.command[1:])
        file = await yt.search(query, sent.id)
        if not file:
            await safe_edit(
                sent,
                m.lang["play_not_found"].format(config.SUPPORT_CHAT)
            )
            return

    if not file:
        return

    file.video = getattr(file, "video", False) or video
    if file.video:
        for track in tracks:
            track.video = True

    # Skip duration check for live streams
    if not file.is_live and file.duration_sec > config.DURATION_LIMIT:
        await safe_edit(
            sent,
            m.lang["play_duration_limit"].format(config.DURATION_LIMIT // 60)
        )
        return

    if await db.is_logger():
        await utils.play_log(m, file.title, file.duration)

    file.user = mention
    file.user_id = m.from_user.id
    if force:
        queue.force_add(chat_id, file)
    else:
        position = queue.add(chat_id, file)  # Returns 0-based index

        if await db.get_call(chat_id):
            # When call is active, position 0 is currently playing
            # So actual waiting position is: position (e.g., 1st waiting = index 1)
            # Display as 1-based for users: index 1 → "1st in queue"
            await safe_edit(
                sent,
                m.lang["play_queued"].format(
                    position,  # Shows waiting position: 1, 2, 3...
                    file.url,
                    file.title,
                    file.duration,
                    m.from_user.mention,
                ),
                # Single "Play Now" button (plays this track immediately)
                reply_markup=queue_controls(chat_id, file.id),
            )
            if tracks:
                added = playlist_to_queue(chat_id, tracks)
                try:
                    await app.send_message(
                        chat_id=m.chat.id,
                        text=m.lang["playlist_queued"].format(len(tracks)) + added,
                    )
                except Exception:
                    # Can't send message, continue anyway
                    pass
            
            # ✨ NEW: Start preloading queued tracks in background
            try:
                from ArtistMusic import preload
                asyncio.create_task(preload.start_preload(chat_id))
            except Exception:
                # Non-critical, continue without preload
                pass
            
            return

    # ⚡ Already on disk (cached song)? -> skip animation + download, play right away
    if not file.file_path and not file.is_live:
        _local = yt.local_cached(file.id, getattr(file, "video", False))
        if _local:
            file.file_path = _local

    if not file.file_path:
        # Frame 2: search finished, now downloading / streaming the song
        await _show_downloading(sent, _anim_start, file.title)

        if file.is_live:
            # Live streams: extract direct stream URL
            file.file_path = await yt.download(
                file.id,
                is_live=True,
                video=False,
            )
        else:
            # Regular songs: stream URL from API (instant start), file saves in background.
            # Falls back to full download automatically if streaming is not possible.
            file.file_path = await yt.get_play_source(file)

        if not file.file_path:
            await safe_edit(
                sent,
                "<blockquote>❌ Failed to stream media.\n\n"
                "Possible reasons:\n"
                "• YouTube bot detection (try again in a moment)\n"
                "• Video is region-blocked or private\n"
                "• Age-restricted content\n\n"
                f"Support: {config.SUPPORT_CHAT}</blockquote>"
            )
            return

    try:
        # Pass message_chat_id only if it's different from chat_id (channel play mode)
        await tune.play_media(
            chat_id=chat_id, 
            message=sent, 
            media=file, 
            message_chat_id=message_chat_id if chat_id != message_chat_id else None
        )
        # React with emoji on successful play
        try:
            emoji = m.lang["play_emoji"]
            await m.react(emoji)
        except Exception:
            # If reaction fails, continue anyway (not critical)
            pass
    except Exception as e:
        error_msg = str(e)
        if "bot" in error_msg.lower() or "sign in" in error_msg.lower():
            await safe_edit(
                sent,
                "<blockquote>❌ YouTube bot detection triggered.\n\n"
                "Solution:\n"
                "• Wait a few minutes and try again\n"
                "• Try /radio for uninterrupted music\n\n"
                f"Support: {config.SUPPORT_CHAT}</blockquote>"
            )
        else:
            await safe_edit(
                sent,
                f"<blockquote>❌ Playback error:\n{error_msg}\n\n"
                f"Support: {config.SUPPORT_CHAT}</blockquote>"
            )
        return
    if not tracks:
        return
    added = playlist_to_queue(chat_id, tracks)
    # Playlist tracks queued -> download + upload to logger group right away
    try:
        from ArtistMusic import preload
        asyncio.create_task(preload.start_preload(chat_id))
    except Exception:
        pass
    try:
        await app.send_message(
            chat_id=m.chat.id,
            text=m.lang["playlist_queued"].format(len(tracks)) + added,
        )
    except Exception:
        # Can't send message, but playback is working
        pass
