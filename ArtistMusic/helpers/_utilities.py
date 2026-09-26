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
            return await app.send_photo(
                chat_id=message.chat.id,
                photo=photo,
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
