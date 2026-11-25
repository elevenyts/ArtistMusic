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
import os
import time

from pyrogram import types

from ArtistMusic import config
from ArtistMusic.helpers import Media, buttons, utils


class Telegram:
    def __init__(self):
        """Initialize the Telegram download handler."""
        self.active = [
        ]  # List of currently downloading file IDs (prevent duplicates)
        self.events = {}  # Dictionary of download events for cancellation
        # Track last progress update time (for rate limiting)
        self.last_edit = {}
        self.active_tasks = {}  # Active download tasks for cancellation
        self.sleep = 5  # Minimum seconds between progress updates

    def get_media(self, msg: types.Message) -> bool:
        """Check if message contains downloadable media."""
        return any([msg.audio, msg.document, msg.voice, msg.video])

    async def download(self, msg: types.Message, sent: types.Message) -> Media | None:
        """
        Download media from a Telegram message with progress tracking.

        Args:
            msg: The message containing the media
            sent: The status message to update with progress

        Returns:
            Media object if successful, None if failed or cancelled
        """
        msg_id = sent.id
        event = asyncio.Event()  # Event for cancellation
        self.events[msg_id] = event
        self.last_edit[msg_id] = 0  # Initialize last edit time
        start_time = time.time()  # Track download start time

        # Extract media information from message
        media = msg.audio or msg.voice or msg.video or msg.document
        # Detect if this is a video file
        is_video = bool(msg.video) or (msg.document and getattr(msg.document, "mime_type", "").startswith("video/"))
        # Unique file identifier
        file_id = getattr(media, "file_unique_id", None)
        file_ext = getattr(media, "file_name", "").split(
            ".")[-1]  # File extension
        file_size = getattr(media, "file_size", 0)  # File size in bytes
        file_title = getattr(
            media, "title", "Telegram File") or "Telegram File"  # Media title
        duration = getattr(media, "duration", 0)  # Duration in seconds

        # Validate duration limit (configured in config.py)
        if duration > config.DURATION_LIMIT:
            await sent.edit_text(sent.lang["play_duration_limit"].format(config.DURATION_LIMIT // 60))
            return await sent.stop_propagation()

        # Validate file size (max 200 MB)
        if file_size > 200 * 1024 * 1024:
            await sent.edit_text(sent.lang["dl_limit"])
            return await sent.stop_propagation()

        async def progress(current, total):
            if event.is_set():
                return

            now = time.time()
            if now - self.last_edit[msg_id] < self.sleep:
                return

            self.last_edit[msg_id] = now
            percent = current * 100 / total
            speed = current / (now - start_time or 1e-6)
            eta = utils.format_eta(int((total - current) / speed))
            text = sent.lang["dl_progress"].format(
                utils.format_size(current),
                utils.format_size(total),
                percent,
                utils.format_size(speed),
                eta,
            )

            await sent.edit_text(
                text, reply_markup=buttons.cancel_dl(sent.lang["cancel"])
            )

        try:
            file_path = f"downloads/{file_id}.{file_ext}"
            if not os.path.exists(file_path):
                if file_id in self.active:
                    await sent.edit_text(sent.lang["dl_active"])
                    return await sent.stop_propagation()

                self.active.append(file_id)
                task = asyncio.create_task(
                    msg.download(file_name=file_path, progress=progress)
                )
                self.active_tasks[msg_id] = task
                await task
                self.active.remove(file_id)
                self.active_tasks.pop(msg_id, None)
                await sent.edit_text(
                    sent.lang["dl_complete"].format(
                        round(time.time() - start_time, 2))
                )

            # Format duration with hours support
            if duration >= 3600:
                duration_str = time.strftime("%H:%M:%S", time.gmtime(duration))
            else:
                duration_str = time.strftime("%M:%S", time.gmtime(duration))

            return Media(
                id=file_id,
                duration=duration_str,
                duration_sec=duration,
                file_path=file_path,
                message_id=sent.id,
                url=msg.link,
                title=file_title[:25],
                video=is_video,
            )
        except asyncio.CancelledError:
            return await sent.stop_propagation()
        finally:
            self.events.pop(msg_id, None)
            self.last_edit.pop(msg_id, None)
            self.active = [f for f in self.active if f != file_id]

    async def cancel(self, query: types.CallbackQuery):
        event = self.events.get(query.message.id)
        task = self.active_tasks.pop(query.message.id, None)
        if event:
            event.set()

        if task and not task.done():
            task.cancel()
        if event or task:
            await query.edit_message_text(
                query.lang["dl_cancel"].format(query.from_user.mention)
            )
        else:
            await query.answer(query.lang["dl_not_found"], show_alert=True)
