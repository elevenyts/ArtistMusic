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
from pathlib import Path
from typing import Dict, Set

from ArtistMusic import logger


class PreloadManager:
    """
    Manages background preloading of upcoming tracks in queue.
    
    This class ensures seamless transitions between songs by downloading
    upcoming tracks while the current track is still playing.
    """
    
    def __init__(self):
        """Initialize the preload manager."""
        # Track active preload tasks per chat: {chat_id: set of asyncio.Task}
        self._preload_tasks: Dict[int, Set[asyncio.Task]] = {}
        
        # Track which items are currently being preloaded to prevent duplicates
        self._preloading: Dict[int, Set[str]] = {}  # {chat_id: set of track IDs}
    
    async def start_preload(self, chat_id: int, count: int = 2) -> None:
        """
        Start preloading upcoming tracks for a chat.
        
        Args:
            chat_id: The chat ID to preload tracks for
            count: Number of upcoming tracks to preload (default: 2)
        """
        from ArtistMusic import queue, yt
        
        # Get upcoming tracks from queue
        upcoming_tracks = queue.peek_next(chat_id, count)
        
        if not upcoming_tracks:
            return
        
        # Initialize tracking sets if needed
        if chat_id not in self._preload_tasks:
            self._preload_tasks[chat_id] = set()
        if chat_id not in self._preloading:
            self._preloading[chat_id] = set()
        
        # Start preload task for each track that needs downloading
        for track in upcoming_tracks:
            # Skip if already downloaded or currently being preloaded
            if queue.is_downloaded(track):
                continue
            
            track_id = getattr(track, 'id', None)
            if not track_id or track_id in self._preloading[chat_id]:
                continue
            
            # Mark as being preloaded
            self._preloading[chat_id].add(track_id)
            
            # Create background task for this track
            task = asyncio.create_task(
                self._preload_track(chat_id, track)
            )
            self._preload_tasks[chat_id].add(task)
            
            # Add callback to clean up task when done
            task.add_done_callback(
                lambda t, cid=chat_id: self._cleanup_task(cid, t)
            )
    
    async def _preload_track(self, chat_id: int, track) -> None:
        """
        Preload a single track in the background.
        
        Args:
            chat_id: The chat ID this track belongs to
            track: Track object to preload
        """
        from ArtistMusic import yt
        
        try:
            track_id = track.id
            is_live = getattr(track, 'is_live', False)
            
            # Download the track (uses existing semaphore for rate limiting)
            file_path = await yt.download(
                track_id,
                is_live=is_live,
                video=getattr(track, "video", False),
            )
            
            if file_path:
                # Update track with downloaded file path
                track.file_path = file_path
            else:
                # Silent failure - track will download normally when needed
                pass
        
        except asyncio.CancelledError:
            # Task was cancelled (queue changed, playback stopped, etc.)
            raise
        
        except Exception as e:
            # Log error but don't crash - track will be downloaded when it's time to play
            logger.error(f"❌ Error preloading track {track.id} for chat {chat_id}: {e}")
        
        finally:
            # Remove from preloading set
            if chat_id in self._preloading and track.id in self._preloading[chat_id]:
                self._preloading[chat_id].remove(track.id)
    
    async def cancel_preload(self, chat_id: int) -> None:
        """
        Cancel all active preload tasks for a chat.
        
        Called when:
        - Queue is cleared
        - Playback is stopped
        - Track is skipped (may need to re-prioritize)
        
        Args:
            chat_id: The chat ID to cancel preloading for
        """
        if chat_id not in self._preload_tasks:
            return
        
        tasks = self._preload_tasks[chat_id].copy()
        
        # Cancel all tasks
        for task in tasks:
            if not task.done():
                task.cancel()
        
        # Wait for all tasks to finish cancellation
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Clean up tracking
        self._preload_tasks[chat_id].clear()
        if chat_id in self._preloading:
            self._preloading[chat_id].clear()
    
    def _cleanup_task(self, chat_id: int, task: asyncio.Task) -> None:
        """
        Clean up completed task from tracking.
        
        Args:
            chat_id: The chat ID this task belongs to
            task: The completed task to clean up
        """
        if chat_id in self._preload_tasks:
            self._preload_tasks[chat_id].discard(task)
