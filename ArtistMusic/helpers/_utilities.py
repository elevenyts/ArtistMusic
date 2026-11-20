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

import re

from pyrogram import enums, errors, types
from ArtistMusic import app, config
from config import media_kind as config_media_kind


class Utilities:
    def __init__(self):
        pass

    def format_eta(self, seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}:{seconds % 60:02d} min"
        else:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            s = seconds % 60
            return f"{h}:{m:02d}:{s:02d} h"

    def format_size(self, bytes: int) -> str:
        if bytes >= 1024**3:
            return f"{bytes / 1024 ** 3:.2f} GB"
        elif bytes >= 1024**2:
            return f"{bytes / 1024 ** 2:.2f} MB"
        else:
            return f"{bytes / 1024:.2f} KB"

    def format_duration(self, seconds: int) -> str:
        """Format duration as HH:MM:SS or MM:SS depending on length."""
        if seconds >= 3600:  # 1 hour or more
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:  # Less than 1 hour
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes:02d}:{secs:02d}"

    def to_seconds(self, time: str) -> int:
        parts = [int(p) for p in time.strip().split(":")]
        return sum(value * 60**i for i, value in enumerate(reversed(parts)))

    async def extract_user(self, msg: types.Message) -> types.User | None:
        if msg.reply_to_message:
            return msg.reply_to_message.from_user

        if msg.entities:
            for e in msg.entities:
                if e.type == enums.MessageEntityType.TEXT_MENTION:
                    return e.user

        if msg.text:
            try:
                if m := re.search(r"@(\w{5,32})", msg.text):
                    return await app.get_users(m.group(0))
                if m := re.search(r"\b\d{6,15}\b", msg.text):
                    return await app.get_users(int(m.group(0)))
            except:
                pass

        return None

    async def play_log(
        self,
        m: types.Message,
        title: str,
        duration: str,
    ) -> None:
        if m.chat.id == app.logger:
            return
        _text = m.lang["play_log"].format(
            app.name,
            m.chat.id,
            m.chat.title,
            m.from_user.id,
            m.from_user.mention,
            m.link,
            title,
            duration,
        )
        await app.send_message(chat_id=app.logger, text=_text)

    async def send_log(self, m: types.Message) -> None:
        """Log new user to logger group when they start the bot in private chat."""
        await app.send_message(
            chat_id=app.logger,
            text=m.lang["log_user"].format(
                m.from_user.id,
                f"@{m.from_user.username}",
                m.from_user.mention,
            ),
        )

    # ---- media type detection (photo / gif / mp4 / svg etc.) ----
    # Fallback order tried when Telegram rejects the guessed type
    # (e.g. link has no extension, or a CDN serves a different format).
    _KIND_ORDER = {
        "photo": ("photo", "animation", "video", "document"),
        "animation": ("animation", "video", "photo", "document"),
        "video": ("video", "animation", "document"),
        "svg": ("svg_photo", "document"),
    }

    def media_kind(self, media) -> str:
        """Return "photo", "animation", "video" or "svg" based on the link."""
        return config_media_kind(media)

    @staticmethod
    async def _svg_to_png(url: str):
        """Rasterise an svg link to PNG (needs optional ``cairosvg``). None on failure."""
        try:
            import io
            import aiohttp
            import cairosvg  # optional dependency

            if url.startswith(("http://", "https://")):
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as r:
                        r.raise_for_status()
                        data = await r.read()
            else:
                with open(url, "rb") as f:
                    data = f.read()
            png = cairosvg.svg2png(bytestring=data, output_width=1280)
            bio = io.BytesIO(png)
            bio.name = "image.png"
            return bio
        except Exception:
            return None

    def input_media_candidates(self, media, caption: str | None = None) -> list:
        """InputMedia* objects to try (in order) for ``edit_media``."""
        out = []
        for kind in self._KIND_ORDER[self.media_kind(media)]:
            if kind == "animation":
                out.append(types.InputMediaAnimation(media=media, caption=caption))
            elif kind == "video":
                out.append(types.InputMediaVideo(media=media, caption=caption))
            elif kind == "document":
                out.append(types.InputMediaDocument(media=media, caption=caption))
            elif kind == "photo":
                out.append(types.InputMediaPhoto(media=media, caption=caption))
        return out

    def input_media(self, media, caption: str | None = None):
        """Best-guess InputMedia* object matching the link type (for edit_media)."""
        cands = self.input_media_candidates(media, caption)
        return cands[0] if cands else types.InputMediaPhoto(media=media, caption=caption)

    async def edit_media_safe(self, message, media, caption: str | None = None, **kwargs):
        """edit_media that tries every compatible media type before giving up."""
        first_err = None
        for cand in self.input_media_candidates(media, caption):
            try:
                return await message.edit_media(media=cand, **kwargs)
            except (errors.FloodWait, errors.Forbidden, errors.MessageNotModified):
                raise
            except Exception as e:
                first_err = first_err or e
        if first_err:
            if caption and "ENTITY_TEXT_INVALID" in str(first_err):
                from ArtistMusic.Button_emoji import strip_custom_emoji
                plain = strip_custom_emoji(caption)
                if plain != caption:
                    return await self.edit_media_safe(message, media, plain, **kwargs)
            raise first_err

    async def send_media(
        self,
        chat_id,
        media,
        caption: str | None = None,
        reply_markup=None,
        reply_parameters=None,
        **kwargs,
    ) -> types.Message:
        """Send any supported link: jpg/png/webp -> photo, gif/mp4 -> animation,
        webm/mov/mkv -> video, svg -> png (or file). If Telegram rejects the guessed
        type, the other types are tried automatically."""
        common = dict(
            chat_id=chat_id,
            caption=caption,
            reply_markup=reply_markup,
            reply_parameters=reply_parameters,
        )
        first_err = None
        for kind in self._KIND_ORDER[self.media_kind(media)]:
            try:
                if kind == "animation":
                    return await app.send_animation(animation=media, **common, **kwargs)
                if kind == "video":
                    return await app.send_video(video=media, **common, **kwargs)
                if kind == "photo":
                    return await app.send_photo(photo=media, **common, **kwargs)
                if kind == "svg_photo":
                    png = await self._svg_to_png(media)
                    if png is None:
                        continue
                    return await app.send_photo(photo=png, **common, **kwargs)
                # document: no spoiler support
                doc_kwargs = {k: v for k, v in kwargs.items() if k != "has_spoiler"}
                return await app.send_document(document=media, **common, **doc_kwargs)
            except (errors.FloodWait, errors.Forbidden):
                raise  # not a media-type problem -> let caller handle
            except Exception as e:
                first_err = first_err or e
        if first_err:
            if caption and "ENTITY_TEXT_INVALID" in str(first_err):
                from ArtistMusic.Button_emoji import strip_custom_emoji
                plain = strip_custom_emoji(caption)
                if plain != caption:
                    return await self.send_media(
                        chat_id, media, plain,
                        reply_markup=reply_markup,
                        reply_parameters=reply_parameters,
                        **kwargs,
                    )
            raise first_err
        raise ValueError(f"Unsupported media link: {media}")

    async def reply(
        self,
        message: types.Message,
        *,
        text: str | None = None,
        photo=None,
        caption: str | None = None,
        quote: bool = True,
        reply_markup=None,
        **kwargs,
    ) -> types.Message | None:
        """Send a message/photo into ``message``'s chat, replicating the
        ``quote=True/False`` behaviour that Kurigram >= 2.2.x removed from
        ``Message.reply_text`` / ``Message.reply_photo`` (it now raises
        ``TypeError: unexpected keyword argument 'quote'``). Kurigram's
        replacement is an explicit ``reply_parameters`` on the client-level
        send methods, which this centralizes so call sites keep the same
        ``quote=`` interface they had before.
        """
        reply_parameters = types.ReplyParameters(message_id=message.id) if quote else None
        if photo is not None:
            return await self.send_media(
                chat_id=message.chat.id,
                media=photo,
                caption=caption,
                reply_markup=reply_markup,
                reply_parameters=reply_parameters,
                **kwargs,
            )
        return await app.send_message(
            chat_id=message.chat.id,
            text=text,
            reply_markup=reply_markup,
            reply_parameters=reply_parameters,
            **kwargs,
        )

    async def safe_text(
        self,
        message: types.Message,
        text: str,
        *,
        reply_markup=None,
        quote: bool | None = True,
    ) -> types.Message | None:
        """Send text but gracefully fallback to media-only chats."""
        if not message:
            return None
        try:
            return await self.reply(
                message,
                text=text,
                reply_markup=reply_markup,
                quote=bool(quote),
            )
        except (errors.ChatSendPlainForbidden, errors.ChatWriteForbidden):
            fallback_photo = getattr(config, "START_IMG", None)
            if not fallback_photo:
                return None
            try:
                return await self.reply(
                    message,
                    photo=fallback_photo,
                    caption=text,
                    reply_markup=reply_markup,
                    quote=bool(quote),
                )
            except errors.RPCError:
                return None
        except errors.RPCError:
            return None

    async def safe_edit(
        self,
        message: types.Message | None,
        text: str,
        *,
        reply_markup=None,
    ) -> bool:
        """Edit text or caption safely depending on message type."""
        if not message:
            return False
        try:
            if message.text is not None:
                await message.edit_text(text=text, reply_markup=reply_markup)
            else:
                await message.edit_caption(caption=text, reply_markup=reply_markup)
            return True
        except errors.RPCError:
            return False
