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

import os
import re
import glob
import time
import yt_dlp
import random
import uuid
import asyncio
from urllib.parse import urlencode
import aiohttp
from dataclasses import replace
from pathlib import Path
from typing import Optional, Union

from pyrogram import enums, types
from py_yt import Playlist, VideosSearch
from ArtistMusic import config, logger, app, db
from ArtistMusic.helpers import Track, utils


class YouTube:
    def __init__(self):
        """Initialize YouTube handler with configuration and caching."""
        self.base = "https://www.youtube.com/watch?v="
        self.cookies = []
        self.checked = False
        self.warned = False

        # Get API configuration from config
        self.api_url = config.ARTISTBOTS_API_URL
        self.artistbots_key = config.ARTISTBOTS_KEY
        self.enable_api = config.ENABLE_API
        self.enable_cookies_fallback = config.ENABLE_COOKIES_FALLBACK
        self.api_timeout = config.API_TIMEOUT
        self.api_stream_timeout = config.API_STREAM_TIMEOUT

        # Same (video_id, video) ke parallel downloads ko ek hi task se serve karne ke liye
        self._inflight: dict[tuple[str, bool], asyncio.Future] = {}
        # logger-group uploads currently running (prevents duplicate uploads)
        self._uploading: set[tuple[str, bool]] = set()

        # Regular expression to match YouTube URLs
        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|live/|embed/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )

        # Cache search results (10 minute TTL)
        self.search_cache = {}
        self._download_semaphore = asyncio.Semaphore(5)
        self._max_video_height = config.VIDEO_MAX_HEIGHT

        # Log configuration
        logger.info("=" * 50)
        logger.info("📹 YouTube Handler Initialized")
        logger.info(f"🎵 API Priority: {'ENABLED' if self.enable_api else 'DISABLED'}")
        if self.enable_api:
            logger.info(f"🔗 API URL: {self.api_url}")
            if self.artistbots_key:
                masked_key = self.artistbots_key[:8] + "..." if len(self.artistbots_key) > 8 else "***"
                logger.info(f"🔑 API Key: {masked_key}")
            else:
                logger.warning("⚠️ No API Key configured!")
        logger.info(f"🍪 Cookies Fallback: {'ENABLED' if self.enable_cookies_fallback else 'DISABLED'}")
        logger.info("=" * 50)

    # ───────────── bad-file detection / cleanup (touches ONLY the given video's files) ─────────────
    _MEDIA_EXTS = {".mp3", ".mp4", ".m4a", ".webm", ".opus", ".ogg", ".wav", ".flac", ".mkv", ".mov"}

    @staticmethod
    def is_yt_id(value) -> bool:
        """YouTube ids are exactly 11 chars; protects Telegram-uploaded files from being touched."""
        import re as _re
        return bool(value) and bool(_re.fullmatch(r"[A-Za-z0-9_-]{11}", str(value)))

    @staticmethod
    def is_bad_media_file(path: str) -> bool:
        """True when the file is clearly NOT media: empty/tiny, or a JSON/HTML/text error body."""
        try:
            if os.path.getsize(path) < 1024:
                return True
            with open(path, "rb") as f:
                head = f.read(512).lstrip()
        except OSError:
            return False
        return head[:1] in (b"{", b"[", b"<") or head[:5].lower() in (b"error", b"<!doc")

    async def purge_bad_download(self, video_id: str, video: bool = False, force: bool = False) -> list:
        """Delete this video's broken file(s) so they get downloaded again.

        force=False -> remove only files that sniff as non-media (valid cached songs stay untouched).
        force=True  -> player (ffmpeg) rejected the file, so remove it, and drop the logger-group
                       cache entry too (it may hold the same broken copy).
        """
        removed = []
        if not self.is_yt_id(video_id):
            return removed
        for path in glob.glob(f"downloads/{glob.escape(video_id)}.*"):
            if os.path.isdir(path) or Path(path).suffix.lower() not in self._MEDIA_EXTS:
                continue
            if force or self.is_bad_media_file(path):
                try:
                    os.remove(path)
                    removed.append(path)
                    logger.warning(f"🗑️ Removed broken cached file: {path}")
                except OSError as e:
                    logger.warning(f"Could not remove {path}: {e}")
        if force:
            try:
                await db.delete_song_cache(video_id, video=video)
            except Exception as e:
                logger.debug(f"Could not clear logger cache entry for {video_id}: {e}")
        return removed

    def _locate_download_file(self, video_id: str, video: bool = False) -> Optional[str]:
        """Locate any completed download file for a video id."""
        pattern = f"downloads/{video_id}*"
        candidates = sorted([
            path for path in glob.glob(pattern)
            if not path.endswith((".part", ".ytdl", ".info.json", ".temp"))
        ])

        video_exts = {".mp4", ".mkv", ".webm", ".mov"}
        audio_exts = {".m4a", ".webm", ".opus", ".mp3", ".ogg", ".wav", ".flac"}

        if video:
            for path in candidates:
                if os.path.isdir(path):
                    continue
                if Path(path).suffix.lower() in video_exts:
                    return path
        else:
            for path in candidates:
                if os.path.isdir(path):
                    continue
                if Path(path).suffix.lower() in audio_exts:
                    return path

        for path in candidates:
            if os.path.isdir(path):
                continue
            return path
        return None

    def get_cookies(self):
        """Get random cookie file from cookies directory."""
        if not self.checked:
            cookies_dir = "ArtistMusic/cookies"
            if os.path.exists(cookies_dir):
                for file in os.listdir(cookies_dir):
                    if file.endswith(".txt"):
                        self.cookies.append(file)
            self.checked = True
        
        if not self.cookies:
            if not self.warned:
                self.warned = True
                logger.warning("🍪 Cookies are missing; downloads might fail.")
            return None
        
        cookie_file = f"ArtistMusic/cookies/{random.choice(self.cookies)}"
        logger.debug(f"Using cookie file: {cookie_file}")
        return cookie_file

    async def save_cookies(self, urls: list[str]) -> None:
        """Save cookies from URLs to files."""
        logger.info("🍪 Saving cookies from urls...")
        saved_count = 0
        
        # Create cookies directory if not exists
        cookies_dir = Path("ArtistMusic/cookies")
        cookies_dir.mkdir(parents=True, exist_ok=True)
        
        for url in urls:
            try:
                # Generate unique filename
                path = cookies_dir / f"cookie{random.randint(10000, 99999)}.txt"
                
                # Convert to raw URL if needed
                if "pastebin.com" in url:
                    link = url.replace("pastebin.com", "pastebin.com/raw")
                elif "batbin.me" in url:
                    link = url.replace("batbin.me", "batbin.me/raw")
                else:
                    link = url
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(link, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        if resp.status != 200:
                            logger.error(f"❌ Cookie download failed: HTTP {resp.status} from {url}")
                            continue
                        
                        content = await resp.read()
                        if not content or len(content) < 50:
                            logger.error(f"❌ Cookie file empty or invalid from {url}")
                            continue
                        
                        # Save cookie file
                        with open(path, "wb") as fw:
                            fw.write(content)
                        
                        if path.exists() and path.stat().st_size > 0:
                            saved_count += 1
                            cookie_filename = path.name
                            if cookie_filename not in self.cookies:
                                self.cookies.append(cookie_filename)
                            logger.info(f"✅ Saved: {cookie_filename} ({len(content)} bytes)")
                            
            except asyncio.TimeoutError:
                logger.error(f"❌ Cookie download timeout from {url}")
            except Exception as e:
                logger.error(f"❌ Cookie download error from {url}: {e}")
        
        self.checked = True
        
        if saved_count > 0:
            logger.info(f"✅ Cookies saved successfully! ({saved_count} file(s))")
        else:
            logger.error("❌ No cookies saved! Check COOKIE_URL in .env.")

    # ───────────── Play source (API /download -> full file -> play) ─────────────
    async def get_play_source(self, track) -> Optional[str]:
        """
        Returns the file path to play.

        The song is always fully downloaded first (ArtistBots API `/download`,
        then the cookies fallback) and only then handed to the voice chat:

        1. already cached (disk / logger group)   -> local file path
        2. API /download (full download)          -> local file path
        3. cookies fallback (yt-dlp)              -> local file path
        """
        video = getattr(track, "video", False)
        video_id = track.id
        if getattr(track, "is_live", False):
            return await self.download(video_id, is_live=True, video=video)
        return await self.download(video_id, video=video)

    async def download_via_api(self, link: str, video: bool = False) -> Optional[str]:
        """
        Download audio/video using ArtistBots API (Primary Method).
        
        Args:
            link: YouTube URL or video ID
            video: True for video download, False for audio download
        
        Returns:
            Path to downloaded file or None if failed
        """
        if not self.enable_api:
            logger.debug("API is disabled in config")
            return None

        if not self.api_url:
            logger.debug("ARTISTBOTS_API_URL not configured")
            return None

        # Extract video ID from URL
        if "v=" in link:
            video_id = link.split("v=")[-1].split("&")[0]
        elif "youtu.be" in link:
            video_id = link.split("/")[-1].split("?")[0]
        else:
            video_id = link

        if not video_id or len(video_id) < 3:
            logger.debug(f"Invalid video ID: {video_id}")
            return None

        DOWNLOAD_DIR = "downloads"
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        
        # Set file extension based on type
        file_ext = ".mp4" if video else ".mp3"
        file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}{file_ext}")

        # Check if already downloaded
        if os.path.exists(file_path):
            if self.is_bad_media_file(file_path):
                logger.warning(f"Cached file is broken, re-downloading: {file_path}")
                try:
                    os.remove(file_path)
                except OSError:
                    pass
            else:
                logger.debug(f"File already exists: {file_path}")
                return file_path

        try:
            download_type = "video" if video else "audio"
            logger.info(f"🚀 [API PRIMARY] Trying ArtistBots API for {video_id} (type: video, mode: {download_type})")
            
            # Prepare API parameters
            params = {
                "url": video_id,
                # always fetch the video form; /play still streams audio only (see calls.py)
                "type": "video",
            }
            
            # Add API key if available
            if self.artistbots_key:
                params["api_key"] = self.artistbots_key
                logger.debug(f"Using API key: {self.artistbots_key[:8]}...")
            else:
                logger.warning("No ArtistBots API key configured!")
                return None
            
            async with aiohttp.ClientSession() as session:
                api_endpoint = f"{self.api_url.rstrip('/')}/download"
                logger.debug(f"Calling API: {api_endpoint}")
                
                async with session.get(
                    api_endpoint,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.api_stream_timeout),
                ) as response:
                    logger.debug(f"API response status: {response.status}")
                    
                    if response.status != 200:
                        try:
                            error_text = await response.text()
                            logger.error(f"API returned status {response.status}: {error_text[:200]}")
                        except:
                            logger.error(f"API returned status {response.status}")
                        return None
                    
                    # Handle direct binary download
                    logger.info(f"📥 Downloading {download_type} via API for {video_id}...")
                    
                    # Get total file size if available
                    content_length = response.headers.get('content-length')
                    if content_length:
                        file_size_mb = int(content_length) / (1024 * 1024)
                        logger.info(f"📦 File size: {file_size_mb:.2f} MB")
                    
                    # Download file with progress
                    downloaded = 0
                    last_log = 0
                    # Content-Type guard: API sometimes sends JSON/HTML error with status 200
                    ctype = (response.headers.get("content-type") or "").lower()
                    if any(t in ctype for t in ("json", "html", "text/")):
                        try:
                            body = (await response.text())[:200]
                        except Exception:
                            body = ""
                        logger.error(f"❌ API returned non-media content ({ctype}) for {video_id}: {body}")
                        return None

                    # Download to a temp file; only moved to final path after validation
                    tmp_path = file_path + ".part"
                    with open(tmp_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(65536):  # 64KB chunks
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Log progress every 5MB
                            if downloaded - last_log >= 5 * 1024 * 1024:
                                progress_mb = downloaded / (1024 * 1024)
                                if content_length:
                                    total_mb = int(content_length) / (1024 * 1024)
                                    percent = (downloaded / int(content_length)) * 100
                                    logger.info(f"📊 Progress: {progress_mb:.1f}/{total_mb:.1f} MB ({percent:.1f}%)")
                                else:
                                    logger.info(f"📊 Downloaded: {progress_mb:.1f} MB")
                                last_log = downloaded
                    
                    # Verify file was created and has content
                    if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                        # Sniff first bytes: reject JSON / HTML / text error bodies
                        with open(tmp_path, "rb") as _f:
                            head = _f.read(512).lstrip()
                        if head[:1] in (b"{", b"[", b"<") or head[:5].lower() in (b"error", b"<!doc"):
                            logger.error(f"❌ API sent non-media data for {video_id}: {head[:120]!r}")
                            os.remove(tmp_path)
                            return None
                        # Never overwrite an existing cached file
                        if os.path.exists(file_path):
                            os.remove(tmp_path)
                            return file_path
                        os.replace(tmp_path, file_path)
                        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                        logger.info(f"✅ [API SUCCESS] Downloaded: {file_path} ({file_size_mb:.2f} MB)")
                        return file_path
                    else:
                        logger.error(f"❌ API download failed: file is empty or not created")
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                        return None

        except asyncio.TimeoutError:
            logger.error(f"⏰ API timeout for {video_id} after {self.api_stream_timeout} seconds")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"🌐 API client error for {video_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ API download failed for {video_id}: {type(e).__name__}: {e}")
            return None

    async def download_via_cookies(self, video_id: str, video: bool = False) -> Optional[str]:
        """
        Download audio/video using yt-dlp with cookies (Fallback Method).
        
        Args:
            video_id: YouTube video ID
            video: True for video download, False for audio download
        
        Returns:
            Path to downloaded file or None if failed
        """
        if not self.enable_cookies_fallback:
            logger.debug("Cookies fallback is disabled in config")
            return None

        url = self.base + video_id
        filename_pattern = f"downloads/{video_id}"
        
        # Check existing files
        existing_files = [
            f for f in glob.glob(f"{filename_pattern}.*")
            if not f.endswith('.part')
        ]
        
        if video:
            video_candidates = [
                f for f in existing_files
                if Path(f).suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}
            ]
            if video_candidates:
                logger.debug(f"Found existing video file: {video_candidates[0]}")
                return video_candidates[0]
        else:
            audio_candidates = [
                f for f in existing_files
                if Path(f).suffix.lower() in {".m4a", ".webm", ".opus", ".mp3", ".ogg", ".wav", ".flac"}
            ]
            if audio_candidates:
                logger.debug(f"Found existing audio file: {audio_candidates[0]}")
                return audio_candidates[0]

            container_fallbacks = [
                f for f in existing_files
                if Path(f).suffix.lower() in {".mp4", ".mkv", ".mov"}
            ]
            if container_fallbacks:
                logger.debug(f"Found existing container file: {container_fallbacks[0]}")
                return container_fallbacks[0]
        
        # Create downloads directory
        downloads_dir = Path("downloads")
        if not downloads_dir.exists():
            try:
                downloads_dir.mkdir(parents=True, exist_ok=True)
                logger.info("📁 Created downloads directory")
            except Exception as e:
                logger.error(f"❌ Cannot create downloads directory: {e}")
                return None

        async with self._download_semaphore:
            cookie = self.get_cookies()
            base_opts = {
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "quiet": True,
                "noplaylist": True,
                "geo_bypass": True,
                "no_warnings": True,
                "overwrites": False,
                "nocheckcertificate": True,
                "continuedl": True,
                "noprogress": True,
                "concurrent_fragment_downloads": 4,
                "http_chunk_size": 524288,
                "socket_timeout": 30,
                "retries": 2,
                "fragment_retries": 2,
                "extractor_retries": 5,
                "sleep_interval_requests": 1,
                "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
            }

            if video:
                height_filter = ""
                if self._max_video_height and self._max_video_height > 0:
                    height_filter = f"[height<={self._max_video_height}]"
                format_chain = (
                    f"bestvideo[ext=mp4]{height_filter}+bestaudio[ext=m4a]/"
                    f"bestvideo{height_filter}+bestaudio/"
                    "bestvideo+bestaudio/best"
                )
                ydl_opts = {
                    **base_opts,
                    "format": format_chain,
                    "merge_output_format": "mp4",
                    "postprocessors": [
                        {
                            "key": "FFmpegVideoConvertor",
                            "preferedformat": "mp4",
                        }
                    ],
                }
            else:
                ydl_opts = {
                    **base_opts,
                    "format": "bestaudio[ext=m4a]/bestaudio[acodec=opus]/bestaudio/best",
                    "postprocessors": [],
                }

            ydl_opts_cookie = {
                **ydl_opts,
                "cookiefile": cookie,
            }

            def _download(ydl_runtime_opts):
                ydl_instance = None
                try:
                    ydl_instance = yt_dlp.YoutubeDL(ydl_runtime_opts)
                    info = ydl_instance.extract_info(url, download=True)
                    if not info:
                        logger.error(f"❌ Failed to extract info for {video_id}")
                        return None
                    
                    time.sleep(0.5)
                    located = self._locate_download_file(video_id, video=video)
                    if located:
                        logger.info(f"✅ Download completed: {located}")
                        return located
                    
                    logger.error(f"❌ Download completed but file not found for: {video_id}")
                    return None
                except Exception as ex:
                    logger.warning(f"⚠️ Download error for {video_id}: {ex}")
                    recovered = self._locate_download_file(video_id, video=video)
                    if recovered:
                        logger.info(f"✅ Recovered existing file: {recovered}")
                        return recovered
                    return None
                finally:
                    if ydl_instance:
                        try:
                            ydl_instance.close()
                        except Exception:
                            pass

            logger.info(f"🍪 [COOKIES FALLBACK] Downloading {video_id} with cookies...")
            result = await asyncio.to_thread(_download, ydl_opts_cookie)
            
            if result:
                logger.info(f"✅ [COOKIES SUCCESS] Downloaded: {result}")
            else:
                logger.warning(f"⚠️ [COOKIES FAILED] Could not download {video_id}")
            
            return result

    def valid(self, url: str) -> bool:
        """Check if URL is a valid YouTube URL."""
        return bool(re.match(self.regex, url))

    def url(self, message_1: types.Message) -> Union[str, None]:
        """Extract YouTube URL from message."""
        messages = [message_1]
        link = None
        
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)

        for message in messages:
            text = message.text or message.caption or ""

            if message.entities:
                for entity in message.entities:
                    if entity.type == enums.MessageEntityType.URL:
                        link = text[entity.offset: entity.offset + entity.length]
                        break

            if message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == enums.MessageEntityType.TEXT_LINK:
                        link = entity.url
                        break

        if link:
            # Remove tracking parameters
            return link.split("&si")[0].split("?si")[0]
        return None



        return None

    async def search(self, query: str, m_id: int) -> Track | None:
        """Search for a song on YouTube."""
        cache_key = query
        current_time = asyncio.get_running_loop().time()

        # Check cache
        if cache_key in self.search_cache:
            cached_result, cache_timestamp = self.search_cache[cache_key]
            if current_time - cache_timestamp < 600:  # 10 minutes TTL
                fresh = replace(cached_result)
                fresh.message_id = m_id
                fresh.file_path = None
                fresh.user = None
                fresh.time = 0
                fresh.video = False
                return fresh

        try:
            _search = VideosSearch(query, limit=1)
            results = await _search.next()
        except Exception as e:
            logger.warning(f"⚠️ YouTube search failed for '{query}': {e}")
            return None

        if results and results["result"]:
            data = results["result"][0]
            duration = data.get("duration")
            is_live = duration is None or duration == "LIVE"

            track = Track(
                id=data.get("id"),
                channel_name=data.get("channel", {}).get("name"),
                duration=duration if not is_live else "LIVE",
                duration_sec=0 if is_live else utils.to_seconds(duration),
                message_id=m_id,
                title=data.get("title")[:25],
                thumbnail=data.get("thumbnails", [{}])[-1].get("url").split("?")[0],
                url=data.get("link"),
                view_count=data.get("viewCount", {}).get("short"),
                is_live=is_live,
            )

            # Cache result
            self.search_cache[cache_key] = (track, current_time)
            
            # Clean old cache entries
            if len(self.search_cache) > 100:
                oldest_key = min(self.search_cache.keys(),
                                 key=lambda k: self.search_cache[k][1])
                del self.search_cache[oldest_key]

            return replace(track)
        return None

    async def playlist(self, limit: int, user: str, url: str) -> list[Track]:
        """Extract tracks from a YouTube playlist."""
        try:
            plist = await Playlist.get(url)
            tracks = []

            if not plist or "videos" not in plist or not plist["videos"]:
                return []

            for data in plist["videos"][:limit]:
                try:
                    thumbnails = data.get("thumbnails", [])
                    thumbnail_url = ""
                    if thumbnails and len(thumbnails) > 0:
                        thumbnail_url = thumbnails[-1].get("url", "").split("?")[0]

                    link = data.get("link", "")
                    if "&list=" in link:
                        link = link.split("&list=")[0]

                    track = Track(
                        id=data.get("id", ""),
                        channel_name=data.get("channel", {}).get("name", ""),
                        duration=data.get("duration", "0:00"),
                        duration_sec=utils.to_seconds(data.get("duration", "0:00")),
                        title=(data.get("title", "Unknown")[:25]),
                        thumbnail=thumbnail_url,
                        url=link,
                        user=user,
                        view_count="",
                    )
                    tracks.append(track)
                except Exception as e:
                    logger.warning(f"Failed to parse playlist item: {e}")
                    continue

            return tracks
        except KeyError as e:
            raise Exception(f"Failed to parse playlist. YouTube may have changed their structure.")
        except Exception as e:
            logger.error(f"Playlist extraction error: {e}")
            raise

    async def try_logger_cache(self, video_id: str, video: bool = False) -> Optional[str]:
        """
        Check if this track was already played before and cached in the logger
        group. If so, pull it straight from Telegram (fast, no yt-dlp/API call
        needed) instead of downloading it from YouTube again.

        Bot token aur Logger Group ID same rahe toh kitne bhi redeploy ho,
        cache hamesha kaam karega. file_id Telegram mein permanent hota hai
        jab tak message logger group mein exist kare.

        Args:
            video_id: YouTube video ID
            video: True to look up the video cache, False for audio

        Returns:
            Path to the downloaded file, or None if there's no valid cache.
        """
        # Logger cache is OFF by default (toggle with /loggercache on)
        if not config.LOGGER_ID or not db.is_logger_cache():
            return None

        cached = await db.get_song_cache(video_id, video=video)
        if not cached:
            return None

        file_id = cached.get("file_id")
        message_id = cached.get("message_id")

        if not file_id:
            return None

        os.makedirs("downloads", exist_ok=True)
        file_path = f"downloads/{video_id}.{'mp4' if video else 'mp3'}"

        # Disk pe already hai (same session mein dobaara play hua)
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            if self.is_bad_media_file(file_path):
                logger.warning(f"⚠️ [CACHE] {video_id} on disk is broken — removing and re-fetching")
                try:
                    os.remove(file_path)
                except OSError:
                    pass
            else:
                logger.info(f"⚡ [CACHE HIT] {video_id} already on disk")
                return file_path

        # Attempt 1: file_id se direct download karo
        try:
            logger.info(f"⚡ [CACHE HIT] Fetching {video_id} from logger group via file_id...")
            downloaded = await app.download_media(file_id, file_name=file_path)
            if downloaded and os.path.exists(downloaded) and os.path.getsize(downloaded) > 0:
                if self.is_bad_media_file(downloaded):
                    logger.warning(f"⚠️ [CACHE] Logger copy of {video_id} is broken — clearing it")
                    os.remove(downloaded)
                    await db.delete_song_cache(video_id, video=video)
                    return None
                logger.info(f"✅ [CACHE] Served {video_id} instantly from logger group")
                return downloaded
            # file download hua par empty hai — disk file saaf karo aur fallback try karo
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.warning(f"⚠️ [CACHE] file_id fetch failed for {video_id}: {e}")
            # file_id fail hua — disk pe adha file hoga toh hatao
            if os.path.exists(file_path):
                os.remove(file_path)

        # Attempt 2: message_id se logger group message forward karke download karo
        # (file_id kabhi kabhi Telegram internally refresh karta hai, message se
        #  naya file_id milta hai bina re-download ke YouTube se)
        if message_id:
            try:
                logger.info(f"⚡ [CACHE] Trying message_id fallback for {video_id}...")
                msg = await app.get_messages(config.LOGGER_ID, message_id)
                if msg and not msg.empty:
                    media_obj = msg.audio or msg.video or msg.document or msg.voice
                    if media_obj:
                        # Naya fresh file_id mil gaya — update karo MongoDB mein
                        fresh_file_id = media_obj.file_id
                        await db.set_song_cache(video_id, fresh_file_id, message_id, video=video)
                        logger.info(f"🔄 [CACHE] Refreshed file_id for {video_id}, downloading...")
                        downloaded = await app.download_media(fresh_file_id, file_name=file_path)
                        if downloaded and os.path.exists(downloaded) and os.path.getsize(downloaded) > 0:
                            if self.is_bad_media_file(downloaded):
                                logger.warning(f"⚠️ [CACHE] Logger copy of {video_id} is broken — clearing it")
                                os.remove(downloaded)
                                await db.delete_song_cache(video_id, video=video)
                                return None
                            logger.info(f"✅ [CACHE] Served {video_id} via refreshed file_id")
                            return downloaded
                        if os.path.exists(file_path):
                            os.remove(file_path)
            except Exception as e:
                logger.warning(f"⚠️ [CACHE] message_id fallback failed for {video_id}: {e}")
                if os.path.exists(file_path):
                    os.remove(file_path)

        # Dono attempts fail — ab cache delete karo aur fresh YouTube download hoga
        # NOTE: Yeh tab hi hoga jab logger group ka message delete ho gaya ho
        logger.warning(f"⚠️ [CACHE] Both attempts failed for {video_id} — clearing stale cache entry")
        await db.delete_song_cache(video_id, video=video)
        return None

    async def cache_to_logger(self, video_id: str, file_path: str, video: bool = False) -> None:
        """
        Upload a freshly downloaded track to the logger group and remember its
        file_id, so the next time anyone (in any group) plays the same song it
        can be served instantly from Telegram instead of being re-downloaded.

        Runs as a fire-and-forget background task so it never delays playback.
        """
        # Logger cache is OFF by default (toggle with /loggercache on)
        if not config.LOGGER_ID or not db.is_logger_cache():
            return

        # Same track ka upload already chal raha ho toh dobara mat karo
        # (download task + preload task dono is function ko call karte hain)
        ukey = (video_id, video)
        if ukey in self._uploading:
            return
        self._uploading.add(ukey)

        # Agar MongoDB mein pehle se hai toh dobara upload mat karo
        # (redeploy ke baad fresh download hua lekin cache already valid tha)
        existing = await db.get_song_cache(video_id, video=video)
        if existing and existing.get("file_id"):
            logger.info(f"⏭️ [CACHE] {video_id} already in logger group DB — skipping re-upload")
            self._uploading.discard(ukey)
            return

        try:
            caption = f"🎵 <b>Cached Track</b>\n\n<b>ID:</b> <code>{video_id}</code>"
            if video:
                sent = await app.send_video(
                    chat_id=config.LOGGER_ID,
                    video=file_path,
                    caption=caption,
                    disable_notification=True,
                )
            else:
                sent = await app.send_audio(
                    chat_id=config.LOGGER_ID,
                    audio=file_path,
                    caption=caption,
                    disable_notification=True,
                )

            # The requested type (audio/video) and the actual container
            # Telegram stores it as can differ — e.g. an "audio" request
            # sometimes only has a muxed video+audio stream available, so
            # Telegram may file it under .video or .document instead of
            # .audio. Grab whichever field actually came back.
            media_obj = sent.audio or sent.video or sent.document or sent.voice
            if not media_obj:
                logger.warning(f"⚠️ Logger upload for {video_id} returned no usable media object")
                return

            tg_file_id = media_obj.file_id
            await db.set_song_cache(video_id, tg_file_id, sent.id, video=video)
            logger.info(f"📥 Cached {video_id} to logger group for instant future plays")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cache {video_id} to logger group: {e}")
        finally:
            self._uploading.discard(ukey)

    async def download(self, video_id: str, is_live: bool = False, video: bool = False) -> Optional[str]:
        """
        Dedupe wrapper: agar same video_id ka download pehle se chal raha hai
        toh naya download start nahi hota, usi ka result share hota hai.
        """
        if is_live:
            return await self._download_impl(video_id, is_live=True, video=video)

        key = (video_id, video)
        task = self._inflight.get(key)
        if task is None or task.done():
            task = asyncio.ensure_future(
                self._download_impl(video_id, is_live=False, video=video)
            )
            self._inflight[key] = task
            task.add_done_callback(
                lambda t, k=key: self._inflight.get(k) is t and self._inflight.pop(k, None)
            )
        else:
            logger.info(f"♻️ [DEDUPE] {video_id} already downloading, waiting for same task")
        # shield: ek waiter cancel ho toh baaki waiters ka download na ruke
        return await asyncio.shield(task)

    async def _download_impl(self, video_id: str, is_live: bool = False, video: bool = False) -> Optional[str]:
        """
        Download audio/video from YouTube.
        
        PRIORITY: API First → Cookies Fallback
        
        Args:
            video_id: YouTube video ID
            is_live: Whether it's a live stream
            video: True for video download, False for audio download
        
        Returns:
            Path to downloaded file or None if failed
        """
        # For live streams, only cookies method works
        if is_live:
            logger.info(f"🔴 Live stream detected for {video_id}, using cookies method...")
            cookie = self.get_cookies()
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "cookiefile": cookie,
                "format": "bestaudio/best",
                "noplaylist": True,
                "socket_timeout": 20,
                "extractor_retries": 5,
                "sleep_interval_requests": 1,
                "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
            }

            def _extract_url():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        info = ydl.extract_info(self.base + video_id, download=False)
                        if not info:
                            return None

                        direct = info.get("url")
                        if direct:
                            return direct

                        for fmt in info.get("formats", []):
                            if fmt.get("acodec") != "none" and fmt.get("url"):
                                return fmt["url"]

                        return info.get("manifest_url")
                    except Exception as ex:
                        logger.error(f"Live stream extraction failed: {ex}")
                        return None

            try:
                stream_url = await asyncio.wait_for(asyncio.to_thread(_extract_url), timeout=35)
                if stream_url:
                    logger.info(f"✅ Live stream URL extracted for {video_id}")
                return stream_url
            except asyncio.TimeoutError:
                logger.error(f"Live stream URL extraction timed out for {video_id}")
                return None

        # Drop this song's broken local file(s) (JSON/HTML error bodies saved as .mp3) so they
        # get downloaded again. Valid cached songs are NOT touched.
        await self.purge_bad_download(video_id, video=video)

        # ⚡ Try instant cache from logger group first (same song played before
        # in any group gets served straight from Telegram, no re-download)
        cached_path = await self.try_logger_cache(video_id, video=video)
        if cached_path:
            return cached_path

        # Normal video/audio download - API FIRST, then cookies
        result = None
        
        # Try API first (Primary)
        if self.enable_api and self.api_url and self.artistbots_key:
            logger.info(f"🎯 [PRIORITY 1] Trying API download for {video_id}")
            result = await self.download_via_api(self.base + video_id, video=video)
            
            if result:
                logger.info(f"✅ [SUCCESS] Downloaded via API: {video_id}")
                asyncio.create_task(self.cache_to_logger(video_id, result, video=video))
                return result
            else:
                logger.warning(f"⚠️ [API FAILED] {video_id}, trying cookies fallback...")
        
        # Try cookies as fallback (Secondary)
        if self.enable_cookies_fallback:
            logger.info(f"🍪 [PRIORITY 2] Trying cookies download for {video_id}")
            result = await self.download_via_cookies(video_id, video=video)
            
            if result:
                logger.info(f"✅ [SUCCESS] Downloaded via cookies: {video_id}")
                asyncio.create_task(self.cache_to_logger(video_id, result, video=video))
                return result
            else:
                logger.error(f"❌ [COOKIES FAILED] Could not download {video_id}")
        
        # Both methods failed
        if not result:
            logger.error(f"❌ [FAILED] All download methods failed for {video_id}")
        
        return result
