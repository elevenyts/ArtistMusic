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

import random
import re
from collections import defaultdict, deque

from py_yt import VideosSearch

from ArtistMusic import config, logger
from ArtistMusic.helpers import Track, utils

# Titles that are long compilations / non-songs - never autoplay these
_SKIP_WORDS = re.compile(
    r"jukebox|nonstop|non-stop|mashup|playlist|full album|podcast|episode|"
    r"compilation|\bhours?\b|\b\d+\s*songs\b|reaction|interview|trailer|"
    r"lyrical\s+video\s+live|karaoke|status",
    re.I,
)
# Noise stripped from a title to build a clean search query
_NOISE = re.compile(
    r"\(.*?\)|\[.*?\]|official|video|audio|lyrics?|lyrical|full song|"
    r"hd|4k|song|music|\|.*$",
    re.I,
)

MIN_SECONDS = 90
MAX_SECONDS = 10 * 60


def _norm(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


class Autoplay:
    """Finds a similar song when the queue runs out (YouTube search based)."""

    def __init__(self):
        # Last 50 played video ids / titles per chat, so songs don't repeat
        self._ids: dict[int, deque] = defaultdict(lambda: deque(maxlen=50))
        self._titles: dict[int, deque] = defaultdict(lambda: deque(maxlen=50))

    def remember(self, chat_id: int, media) -> None:
        """Mark a played track as recent."""
        if not media:
            return
        self._ids[chat_id].append(media.id)
        self._titles[chat_id].append(_norm(media.title)[:20])

    def forget(self, chat_id: int) -> None:
        self._ids.pop(chat_id, None)
        self._titles.pop(chat_id, None)

    def _is_recent(self, chat_id: int, vid: str, title: str) -> bool:
        if vid in self._ids[chat_id]:
            return True
        short = _norm(title)[:20]
        return bool(short) and short in self._titles[chat_id]

    @staticmethod
    def _queries(last) -> list[str]:
        clean = re.sub(r"\s+", " ", _NOISE.sub(" ", last.title or "")).strip()
        channel = (getattr(last, "channel_name", None) or "").strip()
        queries = []
        if clean:
            queries.append(f"{clean} similar songs")
            queries.append(f"songs like {clean}")
        if channel:
            queries.append(f"{channel} new songs")
        if clean and channel:
            queries.append(f"{clean} {channel}")
        random.shuffle(queries)
        return queries or ["latest hindi songs"]

    async def find_next(self, chat_id: int, last) -> Track | None:
        """Return a fresh Track similar to `last`, or None if nothing found."""
        self.remember(chat_id, last)
        max_sec = min(MAX_SECONDS, config.DURATION_LIMIT)

        queries = self._queries(last)
        queries.append("latest hindi songs")  # final fallback

        for query in queries:
            try:
                results = (await VideosSearch(query, limit=10).next()).get("result") or []
            except Exception as e:
                logger.warning(f"Autoplay search failed for '{query}': {e}")
                continue

            candidates = []
            for data in results:
                vid = data.get("id")
                title = data.get("title") or ""
                duration = data.get("duration")
                if not vid or not duration or duration == "LIVE":
                    continue
                try:
                    secs = utils.to_seconds(duration)
                except Exception:
                    continue
                if secs < MIN_SECONDS or secs > max_sec:
                    continue
                if _SKIP_WORDS.search(title) or self._is_recent(chat_id, vid, title):
                    continue
                candidates.append((data, secs))

            if not candidates:
                continue

            # Pick randomly among the top few so it doesn't loop on one pattern
            data, secs = random.choice(candidates[:4])
            thumbs = data.get("thumbnails") or [{}]
            track = Track(
                id=data["id"],
                channel_name=(data.get("channel") or {}).get("name"),
                duration=data.get("duration"),
                duration_sec=secs,
                title=data["title"][:25],
                thumbnail=(thumbs[-1].get("url") or "").split("?")[0] or None,
                url=data.get("link"),
                view_count=(data.get("viewCount") or {}).get("short"),
                is_live=False,
                user="🔁 ᴀᴜᴛᴏᴘʟᴀʏ",
                user_id=None,
            )
            # Remember by full title too, so a different upload of the same song is skipped
            self._ids[chat_id].append(track.id)
            self._titles[chat_id].append(_norm(data["title"])[:20])
            return track

        return None


autoplay = Autoplay()
