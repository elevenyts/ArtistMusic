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
#   svg       : svg (rasterised to PNG if cairosvg is installed, else sent as a file)
# Query strings / #fragments (e.g. ".../a.gif?width=500") are handled.
# Unknown extensions are tried as photo -> animation -> video -> document.
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
        # Owner button link (default: owner's profile via OWNER_ID)
        self.OWNER_LINK: str = getenv("OWNER_LINK", "") or f"tg://user?id={self.OWNER_ID}"

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
        _default_media = "https://graph.org/file/e9b9081be519f0e1413dd-a0fd9c7fc36c010a1c.mp4"
        self.DEFAULT_THUMB: str = normalize_media(getenv("DEFAULT_THUMB", "") or _default_media)
        self.PING_IMG: str = normalize_media(getenv("PING_IMG", "") or _default_media)
        self.START_IMG: str = normalize_media(getenv("START_IMG", "") or _default_media)
        # Image/GIF/MP4 sent when the bot is added to a group (default: START_IMG)
        self.ADD_IMG: str = normalize_media(getenv("ADD_IMG", "")) or self.START_IMG
        self.RADIO_IMG: str = normalize_media(getenv("RADIO_IMG", "") or _default_media)

        # Moderation
        self.EXCLUDED_USERNAMES: List[str] = getenv("EXCLUDED_USERNAMES", "").split()

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
