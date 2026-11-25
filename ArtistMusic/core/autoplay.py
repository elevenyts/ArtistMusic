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
import random
import re
from collections import defaultdict, deque

import yt_dlp
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
    """Finds the next song when the queue runs out (from the playing song's YouTube Mix playlist, search as fallback)."""

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

    @staticmethod
    def _fmt(secs: int) -> str:
        h, rem = divmod(int(secs), 3600)
        m, sec = divmod(rem, 60)
        return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"

    @staticmethod
    def _mix_entries(video_id: str) -> list[dict]:
        """Blocking: songs of the YouTube Mix (auto playlist) of `video_id`."""
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "playlistend": 30,
            "skip_download": True,
            "socket_timeout": 20,
            "extractor_retries": 2,
        }
        try:
            from ArtistMusic import yt as _yt
            cookie = _yt.get_cookies()
            if cookie:
                opts["cookiefile"] = cookie
        except Exception:
            pass
        url = f"https://www.youtube.com/watch?v={video_id}&list=RD{video_id}"
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False) or {}
        return [e for e in (info.get("entries") or []) if e]

    async def _from_playlist(self, chat_id: int, last, max_sec: int) -> Track | None:
        """Next song from the playlist (YouTube Mix) of the song that just played."""
        vid_last = getattr(last, "id", None)
        if not vid_last or not re.fullmatch(r"[A-Za-z0-9_-]{11}", str(vid_last)):
            return None  # not a YouTube song (e.g. Telegram file)
        try:
            entries = await asyncio.wait_for(
                asyncio.to_thread(self._mix_entries, str(vid_last)), timeout=40
            )
        except Exception as e:
            logger.warning(f"Autoplay playlist fetch failed for {vid_last}: {e}")
            return None

        candidates = []
        for data in entries:
            vid = data.get("id")
            title = data.get("title") or ""
            if not vid or vid == vid_last or not title:
                continue
            if data.get("live_status") in ("is_live", "is_upcoming"):
                continue
            secs = data.get("duration")
            if secs is not None:
                try:
                    secs = int(secs)
                except Exception:
                    secs = None
            if secs is not None and (secs < MIN_SECONDS or secs > max_sec):
                continue
            if _SKIP_WORDS.search(title) or self._is_recent(chat_id, vid, title):
                continue
            candidates.append((data, secs))

        if not candidates:
            return None

        data, secs = random.choice(candidates[:8])
        vid = data["id"]
        if secs is None:
            # flat entry had no duration -> look it up for this one song only
            try:
                results = (await VideosSearch(vid, limit=1).next()).get("result") or []
                dur = results[0].get("duration") if results else None
                secs = utils.to_seconds(dur) if dur and dur != "LIVE" else None
            except Exception:
                secs = None
            if secs is None or secs < MIN_SECONDS or secs > max_sec:
                return None

        thumbs = data.get("thumbnails") or [{}]
        track = Track(
            id=vid,
            channel_name=data.get("channel") or data.get("uploader"),
            duration=self._fmt(secs),
            duration_sec=secs,
            title=data["title"][:25],
            thumbnail=(thumbs[-1].get("url") or "").split("?")[0] or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            url=f"https://www.youtube.com/watch?v={vid}",
            view_count=None,
            is_live=False,
            user="🔁 ᴀᴜᴛᴏᴘʟᴀʏ",
            user_id=None,
        )
        self._ids[chat_id].append(track.id)
        self._titles[chat_id].append(_norm(data["title"])[:20])
        return track

    async def find_next(self, chat_id: int, last) -> Track | None:
        """Return a fresh Track from the playlist of `last`, or None if nothing found."""
        self.remember(chat_id, last)
        max_sec = min(MAX_SECONDS, config.DURATION_LIMIT)

        # 1) Preferred: a song from the playlist (YouTube Mix) of the song that just played
        track = await self._from_playlist(chat_id, last, max_sec)
        if track:
            return track

        # 2) Fallback: search based

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
