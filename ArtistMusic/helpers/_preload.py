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
from typing import Dict, Set

logger = logging.getLogger("ArtistMusic")


class PreloadManager:
    """
    Manages background preloading of upcoming tracks in queue.
    
    This ensures smooth transitions between songs by downloading
    the next track before the current one finishes.
    """

    def __init__(self):
        """Initialize the preload manager."""
        # Track active preload tasks by chat and media id:
        # {chat_id: {media_id: task}}
        self._tasks: Dict[int, Dict[str, asyncio.Task]] = {}
        # Track successfully preloaded media ids by chat:
        # {chat_id: {media_id, ...}}
        self._preloaded: Dict[int, Set[str]] = {}
        # Limit parallel downloads so a big playlist doesn't hammer the API.
        # Semaphore is FIFO, so songs closest to playing are fetched first.
        self._sem = asyncio.Semaphore(2)

    async def preload_next(self, chat_id: int, media) -> None:
        """
        Start preloading the next track for a chat.
        
        Args:
            chat_id: The chat ID to preload for
            media: The Media/Track object to preload
        """
        media_id = getattr(media, "id", None)
        if not media_id:
            return

        # Initialize per-chat stores
        if chat_id not in self._tasks:
            self._tasks[chat_id] = {}
        if chat_id not in self._preloaded:
            self._preloaded[chat_id] = set()

        # Skip if already preloaded
        if media_id in self._preloaded[chat_id]:
            logger.debug(f"Track {media_id} already preloaded for chat {chat_id}")
            return

        # Skip if already actively preloading
        existing = self._tasks[chat_id].get(media_id)
        if existing and not existing.done():
            return

        # Start new preload task
        task = asyncio.create_task(self._preload_task(chat_id, media))
        self._tasks[chat_id][media_id] = task

    async def _preload_task(self, chat_id: int, media) -> None:
        """
        Background task to preload a track.
        
        Args:
            chat_id: The chat ID to preload for
            media: The Media/Track object to preload
        """
        try:
            # Import here to avoid circular dependency
            from ArtistMusic import yt

            logger.debug(f"Starting preload for chat {chat_id}: {media.title}")
            
            # Download the track, then push it to the logger group so that a
            # skip / later play is served instantly (disk or Telegram file_id)
            video = getattr(media, "video", False)
            if not media.file_path:
                async with self._sem:
                    media.file_path = await yt.download(media.id, video=video)
            if media.file_path:
                self._preloaded.setdefault(chat_id, set()).add(media.id)
                await yt.cache_to_logger(media.id, media.file_path, video=video)
                logger.debug(f"Preload complete for chat {chat_id}: {media.title}")
                
        except asyncio.CancelledError:
            logger.debug(f"Preload cancelled for chat {chat_id}")
            raise
        except Exception as e:
            logger.error(f"Preload error for chat {chat_id}: {e}")
        finally:
            # Clean up task reference for this specific media id
            media_tasks = self._tasks.get(chat_id)
            if media_tasks:
                media_tasks.pop(getattr(media, "id", None), None)
                if not media_tasks:
                    self._tasks.pop(chat_id, None)

    async def cancel_preload(self, chat_id: int) -> None:
        """
        Cancel any active preload task for a chat.
        
        Args:
            chat_id: The chat ID to cancel preload for
        """
        media_tasks = self._tasks.get(chat_id, {})
        if media_tasks:
            active = [task for task in media_tasks.values() if not task.done()]
            for task in active:
                task.cancel()
            if active:
                await asyncio.gather(*active, return_exceptions=True)
            logger.debug(f"Cancelled preload for chat {chat_id}")
        
        # Clear preloaded cache
        self._preloaded.pop(chat_id, None)
        self._tasks.pop(chat_id, None)

    def is_preloaded(self, chat_id: int, media_id: str) -> bool:
        """
        Check if a specific track is preloaded for a chat.
        
        Args:
            chat_id: The chat ID to check
            media_id: The media ID to check
            
        Returns:
            bool: True if the track is preloaded
        """
        return media_id in self._preloaded.get(chat_id, set())

    def clear(self, chat_id: int) -> None:
        """
        Clear preload cache for a chat (non-async version).
        
        Args:
            chat_id: The chat ID to clear
        """
        self._preloaded.pop(chat_id, None)
        self._tasks.pop(chat_id, None)

    async def start_preload(self, chat_id: int, count: int | None = None) -> None:
        """
        Download + logger-cache every queued (not currently playing) track.

        Called whenever songs are added to the queue and after each track
        change. Already downloaded / in-progress tracks are skipped, so it is
        safe to call repeatedly.

        Args:
            chat_id: The chat ID to preload for
            count: Optional cap on how many upcoming tracks to handle
                   (default: all of them)
        """
        try:
            from ArtistMusic import queue
            from ArtistMusic.helpers._dataclass import Track

            # [0] is playing now; only YouTube Tracks (Telegram files are already local)
            upcoming = [t for t in queue.get_queue(chat_id)[1:] if isinstance(t, Track)]
            if count:
                upcoming = upcoming[:count]
            for media in upcoming:
                # Live streams have no file to download/cache
                if getattr(media, "is_live", False):
                    continue
                if media.file_path:
                    # Disk pe hai, par logger group mein na ho toh upload kar do
                    if not self.is_preloaded(chat_id, media.id):
                        await self.preload_next(chat_id, media)
                    continue
                await self.preload_next(chat_id, media)

        except Exception as e:
            logger.debug(f"Error in start_preload for {chat_id}: {e}")
