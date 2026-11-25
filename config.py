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
from os import getenv
from typing import List
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

# ----------------------------------------------------------
# Media link support for START_IMG / PING_IMG / ADD_IMG / RADIO_IMG / DEFAULT_THUMB
# Any of these can be a direct link (or file_id / local path) to:
#   photo     : jpg, jpeg, png, webp, bmp, heic, jfif
#   animation : gif, mp4, gifv (auto -> mp4), apng
#   video     : webm, mov, mkv, avi, m4v
#   svg       : svg (Telegram can't show svg as photo, so it is sent as a file)
# Query strings / #fragments (e.g. ".../a.gif?width=500") are handled.
# ----------------------------------------------------------
PHOTO_EXT = (".jpg", ".jpeg", ".jfif", ".png", ".webp", ".bmp", ".heic")
ANIMATION_EXT = (".gif", ".mp4", ".gifv", ".apng")
VIDEO_EXT = (".webm", ".mov", ".mkv", ".avi", ".m4v")
SVG_EXT = (".svg", ".svgz")


def normalize_media(url: str) -> str:
    """Trim spaces/quotes and turn imgur-style ``.gifv`` links into ``.mp4``."""
    url = (url or "").strip().strip("\"'")
    try:
        parsed = urlparse(url)
        if parsed.path.lower().endswith(".gifv"):
            url = parsed._replace(path=parsed.path[:-5] + ".mp4").geturl()
    except Exception:
        pass
    return url


_media_state: dict = {}


def pick_media(urls: List[str], fallback: str = "", key: str = "default") -> str:
    """Random media link, but NO repeats until all links have been shown.

    Every variable (key) has its own shuffled round: all URLs are shown once
    before the next shuffle, and the first URL of a new round is never the
    last URL of the previous round (no back-to-back repeat).
    """
    urls = [normalize_media(u) for u in urls if u and u.strip()]
    if not urls:
        return fallback
    if len(urls) == 1:
        return urls[0]
    state = _media_state.setdefault(key, {"queue": [], "last": None, "src": None})
    if state["src"] != urls:  # URL list changed -> reset the round
        state.update(queue=[], src=list(urls))
    if not state["queue"]:
        queue = list(urls)
        random.shuffle(queue)
        if queue[0] == state["last"]:
            queue.append(queue.pop(0))
        state["queue"] = queue
    state["last"] = state["queue"].pop(0)
    return state["last"]


def env_media_list(name: str, defaults: List[str]) -> List[str]:
    """Read comma/space separated URLs from env var ``name`` or use ``defaults``."""
    raw = getenv(name, "")
    items = [u for u in raw.replace(",", " ").split() if u]
    return items or list(defaults)


def media_kind(media) -> str:
    """Return "photo", "animation", "video" or "svg" for a link / path."""
    if not isinstance(media, str):
        return "photo"
    try:
        path = urlparse(media).path.lower()
    except Exception:
        path = media.lower()
    if path.endswith(SVG_EXT):
        return "svg"
    if path.endswith(ANIMATION_EXT):
        return "animation"
    if path.endswith(VIDEO_EXT):
        return "video"
    return "photo"


class Config:
    def __init__(self):
        # Telegram API
        self.API_ID: int = int(getenv("API_ID", "29308061"))
        self.API_HASH: str = getenv("API_HASH", "462de3dfc98fd938ef9c6ee31a72d099")
        self.BOT_TOKEN: str = getenv("BOT_TOKEN", "")
        self.LOGGER_ID: int = int(getenv("LOGGER_ID", "0"))
        self.OWNER_ID: int = int(getenv("OWNER_ID", "0"))

        # Database
        self.MONGO_URL: str = getenv("MONGO_DB_URI", "mongodb+srv://Elevenyts:Elevenyts@cluster0.vuyc1u2.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

        # Limits
        self.DURATION_LIMIT: int = int(getenv("DURATION_LIMIT", "300")) * 60
        self.QUEUE_LIMIT: int = int(getenv("QUEUE_LIMIT", "30"))
        self.PLAYLIST_LIMIT: int = int(getenv("PLAYLIST_LIMIT", "20"))

        # Assistant Sessions @stringenbot
        self.SESSION1: str = getenv("STRING_SESSION", "")
        self.SESSION2: str = getenv("STRING_SESSION2", "")
        self.SESSION3: str = getenv("STRING_SESSION3", "")

        # Support Links
        self.SUPPORT_CHANNEL: str = getenv("SUPPORT_CHANNEL", "https://t.me/Elevenytschats")
        self.SUPPORT_CHAT: str = getenv("SUPPORT_CHAT", "https://t.me/Artistbots")

        # Excluded Chats
        self.EXCLUDED_CHATS: List[int] = self._parse_excluded_chats()

        # Feature Flags
        self.AUTO_END: bool = self._str_to_bool(getenv("AUTO_END", "False"))
        self.AUTO_LEAVE: bool = self._str_to_bool(getenv("AUTO_LEAVE", "False"))
        self.THUMB_GEN: bool = self._str_to_bool(getenv("THUMB_GEN", "True"))
        self.VIDEO_PLAY: bool = self._str_to_bool(getenv("VIDEO_PLAY", "True"))
        self.VIDEO_MAX_HEIGHT: int = self._parse_video_height()

        # ArtistBots API t.me/Artistbots 
        self.ARTISTBOTS_API_URL: str = getenv("ARTISTBOTS_API_URL", "https://api.artistbotsapi.bond")
        self.ARTISTBOTS_KEY: str = getenv("ARTISTBOTS_KEY", "")
        self.ENABLE_API: bool = self._str_to_bool(getenv("ENABLE_API", "True"))
        self.ENABLE_COOKIES_FALLBACK: bool = self._str_to_bool(getenv("ENABLE_COOKIES_FALLBACK", "True"))
        self.API_TIMEOUT: int = int(getenv("API_TIMEOUT", "60"))
        self.API_STREAM_TIMEOUT: int = int(getenv("API_STREAM_TIMEOUT", "300"))

        # YouTube Cookies
        self.COOKIES_URL: List[str] = self._parse_cookies()

        # Images (jpg / png / webp / svg / gif / mp4 / webm ... links all supported)
        # Only these URLs are needed -> used for DEFAULT_THUMB, PING_IMG, START_IMG,
        # ADD_IMG, RADIO_IMG. A RANDOM one is picked each time.
        # Env override: MEDIA_URLS="url1,url2,url3,url4"
        self.MEDIA_URLS: List[str] = env_media_list("MEDIA_URLS", [
            "https://artistbox.bond/f/uj4enj66.png",  # URL 1
            "https://artistbox.bond/f/37z4213f.png",  # URL 2
            "https://artistbox.bond/f/98q3faxn.png",  # URL 3
            "https://artistbox.bond/f/yctsplb0.png",  # URL 4
        ])

        # Moderation
        self.EXCLUDED_USERNAMES: List[str] = getenv("EXCLUDED_USERNAMES", "").split()

    # Random media: a new URL every time, no repeat until all URLs have been shown
    @property
    def DEFAULT_THUMB(self) -> str:
        return pick_media(self.MEDIA_URLS, key="DEFAULT_THUMB")

    @property
    def PING_IMG(self) -> str:
        return pick_media(self.MEDIA_URLS, key="PING_IMG")

    @property
    def START_IMG(self) -> str:
        return pick_media(self.MEDIA_URLS, key="START_IMG")

    @property
    def ADD_IMG(self) -> str:
        return pick_media(self.MEDIA_URLS, key="ADD_IMG")

    @property
    def RADIO_IMG(self) -> str:
        return pick_media(self.MEDIA_URLS, key="RADIO_IMG")

    def _parse_video_height(self) -> int:
        default_height = 1080
        raw_value = getenv("VIDEO_MAX_HEIGHT", str(default_height))
        try:
            height = int(raw_value)
        except (TypeError, ValueError):
            return default_height
        if height <= 0:
            return 0
        return max(480, min(height, 2160))

    def _parse_excluded_chats(self) -> List[int]:
        excluded = getenv("EXCLUDED_CHATS", "")
        if not excluded:
            return []
        chat_ids = []
        for chat_id in excluded.split(","):
            chat_id = chat_id.strip()
            if chat_id.lstrip('-').isdigit():
                chat_ids.append(int(chat_id))
        return chat_ids

    def _parse_cookies(self) -> List[str]:
        cookie_str = getenv("COOKIE_URL", "")
        if not cookie_str:
            return []
        valid_sources = ["batbin.me", "pastebin.com", "paste.ee", "rentry.co"]
        return [url.strip() for url in cookie_str.split() if url.strip() and any(source in url for source in valid_sources)]

    @staticmethod
    def _str_to_bool(value: str) -> bool:
        return value.lower() in ("true", "1", "yes", "y", "on")

    def check(self) -> None:
        required_vars = {
            "API_ID": self.API_ID,
            "API_HASH": self.API_HASH,
            "BOT_TOKEN": self.BOT_TOKEN,
            "MONGO_DB_URI": self.MONGO_URL,
            "LOGGER_ID": self.LOGGER_ID,
            "OWNER_ID": self.OWNER_ID,
            "STRING_SESSION": self.SESSION1,
        }
        missing = [name for name, value in required_vars.items() if not value or (isinstance(value, int) and value == 0)]
        if missing:
            raise SystemExit(f"Missing required env vars: {', '.join(missing)}")
        
        if self.ENABLE_API and not self.ARTISTBOTS_KEY:
            print("Warning: ENABLE_API is True but ARTISTBOTS_KEY is not set")


config = Config()
