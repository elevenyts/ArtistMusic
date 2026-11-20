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
from collections import defaultdict, deque
from typing import Union

from ._dataclass import Media, Track

# MediaItem can be either a Media or Track object
MediaItem = Union[Media, Track]


class Queue:
    def __init__(self):
        """Initialize the queue manager with empty queues for all chats."""
        # Dictionary mapping chat_id to its queue (deque of Media/Track items)
        # defaultdict automatically creates a new deque for new chat_ids
        self.queues: dict[int, deque[MediaItem]] = defaultdict(deque)

    def add(self, chat_id: int, item: MediaItem) -> int:
        """Add a song to the end of the queue and return its position."""
        self.queues[chat_id].append(item)  # Add to end of queue
        return len(self.queues[chat_id]) - 1  # Return position (0-based index)

    def check_item(self, chat_id: int, item_id: str) -> tuple[int, MediaItem | None]:
        """Check if an item with the given ID exists in the queue."""
        pos, track = next(
            (
                (i, track)
                for i, track in enumerate(list(self.queues[chat_id]))
                if track.id == item_id
            ),
            (-1, None),
        )
        return pos, track

    def force_add(
        self, chat_id: int, item: MediaItem, remove: int | bool = False
    ) -> None:
        """Replace the currently playing item with a new one."""
        self.remove_current(chat_id)
        self.queues[chat_id].appendleft(item)
        if remove:
            self.queues[chat_id].rotate(-remove)
            self.queues[chat_id].popleft()
            self.queues[chat_id].rotate(remove)

    def get_current(self, chat_id: int) -> MediaItem | None:
        """Return the currently playing item (first in queue), if any."""
        return self.queues[chat_id][0] if self.queues[chat_id] else None

    def get_next(self, chat_id: int, check: bool = False) -> MediaItem | None:
        """Remove current item and return the next one, or None if empty."""
        if not self.queues[chat_id]:
            return None
        if check:
            return self.queues[chat_id][1] if len(self.queues[chat_id]) > 1 else None

        self.queues[chat_id].popleft()
        return self.queues[chat_id][0] if self.queues[chat_id] else None

    def get_queue(self, chat_id: int) -> list[MediaItem]:
        """Return the full queue including the currently playing item."""
        return list(self.queues[chat_id])
    
    def get_all(self, chat_id: int) -> list[MediaItem]:
        """Alias for get_queue() - return the full queue including currently playing item."""
        return self.get_queue(chat_id)

    def remove_current(self, chat_id: int) -> None:
        """Remove the currently playing item only (if exists)."""
        if self.queues[chat_id]:
            self.queues[chat_id].popleft()

    def clear(self, chat_id: int) -> None:
        """Clear the entire queue."""
        self.queues[chat_id].clear()

    def peek_next(self, chat_id: int, count: int = 2) -> list[MediaItem]:
        """
        Return next N upcoming tracks without removing them from queue.
        
        Args:
            chat_id: The chat ID to peek queue for
            count: Number of upcoming tracks to return (default: 2)
            
        Returns:
            List of upcoming MediaItem objects (excluding currently playing track)
        """
        if not self.queues[chat_id] or len(self.queues[chat_id]) <= 1:
            return []
        
        # Convert deque to list and skip first item (currently playing)
        queue_list = list(self.queues[chat_id])
        return queue_list[1:min(len(queue_list), count + 1)]
    
    @staticmethod
    def is_downloaded(item: MediaItem) -> bool:
        """
        Check if a track has already been downloaded.
        
        Args:
            item: MediaItem or Track object to check
            
        Returns:
            True if file_path exists and is not empty, False otherwise
        """
        return bool(getattr(item, 'file_path', None))
