# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved. 
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Channel      : https://t.me/artistbots
#
# Plugin       : Tag members  (utag / all / mention / tagall + fun tags)
# Location     : ArtistMusic/Artistbots/tagall.py
#
# Commands (group admins & sudoers only):
#   /tagall | /all | @all | /utag | /mention [text]
#                                    - ONE command: tag everyone, 6 emojis per message,
#                                      every emoji is a hidden mention of one member
#   /gmtag /gntag /hitag /lifetag /shayari
#                                    - tag one member per message with a random line
#   /ustop /tagstop /tagoff /gmstop /gnstop /histop /lifestop /shayarioff
#                                    - stop the running tag session
# ==========================================================

import asyncio
import html
import random
import re
from types import SimpleNamespace

from pyrogram import Client, enums, filters
from pyrogram.errors import (
    ChatAdminRequired,
    FloodWait,
    InviteRequestSent,
    UserAlreadyParticipant,
    UserNotParticipant,
)
from pyrogram.types import LinkPreviewOptions, Message

from ArtistMusic import app, db, logger

from .funtag_messages import (
    GM_MESSAGES,
    GN_MESSAGES,
    HI_MESSAGES,
    QUOTES,
    SHAYARI,
)

PREFIXES = ["/", "!", "."]

BATCH_SIZE = 6        # members (emojis) per message for tagall
BATCH_DELAY = 3       # seconds between batches (grows automatically after a FloodWait)
MAX_RETRIES = 5       # resend attempts for one batch when FloodWait hits

# every emoji in a message is a clickable mention of a different member
TAG_EMOJIS = [
    "💕", "🌄", "🌚", "💆🏻", "👱🏻", "😃", "🌸", "🦋", "🔥", "✨", "🌙", "🎧",
    "😎", "🥰", "🌺", "🍀", "💫", "🌈", "🎶", "😇", "🦄", "🍓", "🌻", "💖",
    "😋", "🤗", "🌼", "⭐", "🎈", "🍭", "😜", "🐼", "🌷", "💎", "🕊️", "☀️",
]
FUN_DELAY = 4         # seconds between single fun-tag messages

# chat_id -> name of the running session ("utag" | "tagall" | "gmtag" ...)
active_tags: dict[int, str] = {}

STOP_COMMANDS = [
    "ustop", "tagstop", "tagoff",
    "gmstop", "gnstop", "histop", "lifestop", "shayarioff",
]

_MD_BAD = re.compile(r"[\[\]\(\)\*_`~|\\]")


def _name(user) -> str:
    """First name that is safe inside a Markdown link label."""
    name = _MD_BAD.sub("", user.first_name or "").strip()
    return name or "υsєʀ"


def _link(user) -> str:
    return f"[{_name(user)}](tg://user?id={user.id})"


async def _is_admin(client: Client, message: Message) -> bool:
    # anonymous admin (sent "as group")
    if not message.from_user:
        return bool(message.sender_chat and message.sender_chat.id == message.chat.id)

    uid = message.from_user.id
    if uid in app.sudoers:
        return True
    try:
        member = await client.get_chat_member(message.chat.id, uid)
        return member.status in (
            enums.ChatMemberStatus.OWNER,
            enums.ChatMemberStatus.ADMINISTRATOR,
        )
    except Exception:
        return False


async def _guard(client: Client, message: Message) -> bool:
    """Common checks. Returns True when the command may run."""
    if not await _is_admin(client, message):
        await message.reply_text("🚫 <b>σηʟʏ ᴧᴅϻɪηs ᴄᴧη υsє ᴛʜɪs ᴄσϻϻᴧηᴅ.</b>")
        return False

    if message.chat.id in active_tags:
        running = active_tags[message.chat.id]
        await message.reply_text(
            f"⚠️ <b>ᴧ ᴛᴧɢɢɪηɢ sєssɪση ɪs ᴧʟʀєᴧᴅʏ ʀυηηɪηɢ</b> (<code>{running}</code>).\n"
            "➤ υsє <code>/tagstop</code> ᴛσ sᴛσᴘ ɪᴛ."
        )
        return False
    return True


async def _send(target: Message, text: str, **kw):
    """Send one tag message; swallow FloodWait by sleeping, never crash the loop."""
    try:
        return await target.reply_text(
            text,
            parse_mode=enums.ParseMode.MARKDOWN,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
            **kw,
        )
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        logger.warning(f"tag send failed: {e}")


# ═══════════════════════════════════════════════════════════
#  /tagall  /all  @all  /utag  /mention   (one command, 6 emojis per message)
# ═══════════════════════════════════════════════════════════
async def _known(client: Client, user_id: int) -> bool:
    """True if the BOT can build a real hidden mention for this user."""
    try:
        await client.resolve_peer(user_id)
        return True
    except Exception:
        return False


def _emoji_mention(user, emoji: str, real: bool) -> str:
    # real mention -> long-press shows the member's profile (no raw link)
    if real:
        return f'<a href="tg://user?id={user.id}">{emoji}</a>'
    # bot has never seen this user: a hidden mention is impossible, but a plain
    # @username still pings the member
    username = getattr(user, "username", None)
    if username:
        return f"@{username}"
    return f'<a href="tg://openmessage?user_id={user.id}">{emoji}</a>'


async def _send_batch(target: Message, text: str, state: dict):
    """Send one batch FROM THE BOT ONLY. On FloodWait wait and RETRY the same batch."""
    for _ in range(MAX_RETRIES):
        try:
            return await target.reply_text(
                text,
                parse_mode=enums.ParseMode.HTML,
                link_preview_options=LinkPreviewOptions(is_disabled=True),
            )
        except FloodWait as e:
            wait = int(e.value) + 1
            logger.warning(f"tagall FloodWait {wait}s")
            state["delay"] = min(state["delay"] + 2, 15)
            await asyncio.sleep(wait)
        except Exception as e:
            logger.warning(f"tagall send failed ({type(e).__name__}): {e}")
            state["fails"] = state.get("fails", 0) + 1
            state["last_error"] = f"{type(e).__name__}: {e}"
            return None
    return None


# ───────── member tracking (passive) ─────────
# A bot can never list all members of a group, it only "sees" people who talk.
# So remember everybody the bot sees and use that list as a backup source.
_seen_cache: set = set()


def _tracked_col():
    return db.db.tag_members


@app.on_message(filters.group & ~filters.service, group=-9)
async def _track_senders(client: Client, message: Message):
    user = message.from_user
    if not user or user.is_bot or user.is_deleted:
        return
    await _remember(message.chat.id, user)


@app.on_message(filters.new_chat_members & filters.group, group=-9)
async def _track_joined(client: Client, message: Message):
    for user in message.new_chat_members or []:
        if not user.is_bot:
            await _remember(message.chat.id, user)


async def _remember(chat_id: int, user):
    key = (chat_id, user.id)
    if key in _seen_cache:
        return
    _seen_cache.add(key)
    try:
        await _tracked_col().update_one(
            {"_id": f"{chat_id}:{user.id}"},
            {"$set": {
                "chat_id": chat_id,
                "user_id": user.id,
                "first_name": user.first_name or "",
                "username": user.username,
            }},
            upsert=True,
        )
    except Exception as e:
        logger.warning(f"tagall: could not track {user.id}: {e}")


async def _tracked_users(chat_id: int):
    try:
        async for d in _tracked_col().find({"chat_id": chat_id}):
            yield SimpleNamespace(
                id=d["user_id"],
                first_name=d.get("first_name", ""),
                username=d.get("username"),
                is_bot=False,
                is_deleted=False,
            )
    except Exception as e:
        logger.warning(f"tagall: tracked list failed in {chat_id}: {e}")


# ───────── assistant (user account) = the only one that can list everyone ─────────
async def _ensure_assistant(client: Client, message: Message):
    """Return (assistant, error). Joins the assistant into the group if needed."""
    chat_id = message.chat.id
    try:
        assistant = await db.get_client(chat_id)
    except Exception as e:
        return None, f"no assistant available ({type(e).__name__})"
    if not assistant:
        return None, "assistant is not running (check STRING_SESSION)"

    try:
        member = await client.get_chat_member(chat_id, assistant.id)
        if member.status in (
            enums.ChatMemberStatus.BANNED,
            enums.ChatMemberStatus.RESTRICTED,
        ):
            try:
                await client.unban_chat_member(chat_id, assistant.id)
            except Exception:
                return None, "assistant is banned in this group, please unban it"
        else:
            return assistant, None
    except UserNotParticipant:
        pass
    except ChatAdminRequired:
        return None, "make the bot admin (with Invite Users) so the assistant can join"
    except Exception as e:
        logger.warning(f"tagall: assistant check failed in {chat_id}: {e}")

    # assistant is not in the group -> add it
    try:
        if message.chat.username:
            link = message.chat.username
        else:
            link = (await client.get_chat(chat_id)).invite_link
            if not link:
                link = await client.export_chat_invite_link(chat_id)
    except ChatAdminRequired:
        return None, "make the bot admin (with Invite Users) so the assistant can join"
    except Exception as e:
        return None, f"could not create invite link ({type(e).__name__})"

    try:
        await assistant.join_chat(link)
    except UserAlreadyParticipant:
        pass
    except InviteRequestSent:
        try:
            await client.approve_chat_join_request(chat_id, assistant.id)
        except Exception as e:
            return None, f"assistant join request pending ({type(e).__name__})"
    except Exception as e:
        return None, f"assistant could not join ({type(e).__name__})"

    await asyncio.sleep(1)
    return assistant, None


async def _members(client: Client, chat_id: int, reader=None):
    """Yield every member: assistant list first, then bot admins, then members
    the bot has seen talking. De-duplicated."""
    seen = set()

    async def _drain(source_client):
        for _ in range(MAX_RETRIES):
            try:
                async for member in source_client.get_chat_members(chat_id):
                    user = member.user
                    if not user or user.id in seen:
                        continue
                    seen.add(user.id)
                    yield user
                return
            except FloodWait as e:
                await asyncio.sleep(int(e.value) + 1)
            except Exception as e:
                logger.warning(f"tagall: member listing failed in {chat_id}: {e}")
                return

    if reader is not None:
        async for u in _drain(reader):
            yield u
    async for u in _drain(client):          # admins (bot can always see these)
        yield u
    async for u in _tracked_users(chat_id):  # everyone the bot saw chatting
        if u.id not in seen:
            seen.add(u.id)
            yield u


async def _tag_batches(client: Client, message: Message, session: str):
    chat_id = message.chat.id
    replied = message.reply_to_message
    parts = (message.text or "").split(None, 1)
    text = html.escape(parts[1]) if len(parts) > 1 else ""

    if not await _guard(client, message):
        return

    reader, reader_err = await _ensure_assistant(client, message)
    if reader is None:
        await message.reply_text(
            "⚠️ <b>ᴧssɪsᴛᴧηᴛ ᴄᴧη'ᴛ ʟɪsᴛ ᴧʟʟ ϻєϻʙєʀs:</b> "
            f"<code>{html.escape(reader_err or 'unknown')}</code>\n"
            "➤ ᴛᴧɢɢɪηɢ ᴏηʟʏ ᴧᴅϻɪηs + ᴀᴄᴛɪᴠє ϻєϻʙєʀs."
        )

    active_tags[chat_id] = session
    target = replied or message
    state = {"delay": BATCH_DELAY}
    batch, total = [], 0

    async def flush():
        nonlocal batch
        if not batch:
            return
        emojis = random.sample(TAG_EMOJIS, len(batch))
        reals = [await _known(client, u.id) for u in batch]
        state["link_only"] = state.get("link_only", 0) + reals.count(False)
        line = " ".join(
            _emoji_mention(u, e, r) for u, e, r in zip(batch, emojis, reals)
        )
        head = f"{text}\n\n" if text else ""
        await _send_batch(target, f"{head}{line}", state)
        batch = []

    try:
        async for user in _members(client, chat_id, reader):
            if chat_id not in active_tags:
                break
            if user.is_bot or user.is_deleted:
                continue

            batch.append(user)
            total += 1
            if len(batch) == BATCH_SIZE:
                await flush()
                await asyncio.sleep(state["delay"])

        if chat_id in active_tags:
            await flush()
    except Exception as e:
        logger.warning(f"{session} failed in {chat_id}: {e}")
    finally:
        was_stopped = chat_id not in active_tags
        active_tags.pop(chat_id, None)

    if not was_stopped:
        msg = f"✅ <b>ᴛᴧɢɢɪηɢ ᴄσϻᴘʟєᴛєᴅ. ᴛσᴛᴧʟ:</b> <code>{total}</code> <b>υsєʀs.</b>"
        if state.get("fails"):
            msg += (
                f"\n⚠️ <b>Failed batches:</b> <code>{state['fails']}</code>\n"
                f"<code>{html.escape(state.get('last_error', ''))[:300]}</code>"
            )
        if state.get("link_only"):
            msg += f"\nℹ️ <code>{state['link_only']}</code> users bot ne kabhi nahi dekhe (link-only mention)."
        try:
            await message.reply_text(msg)
        except FloodWait as e:
            await asyncio.sleep(int(e.value) + 1)
        except Exception:
            pass


# "@all" is plain text (not a /command), so it needs a regex filter
_ATALL = filters.regex(r"(?i)^@all(\s|$)")


@app.on_message(
    (filters.command(["tagall", "all", "utag", "mention"], prefixes=PREFIXES) | _ATALL)
    & filters.group
    & ~app.bl_users
)
async def tagall_cmd(client: Client, message: Message):
    await _tag_batches(client, message, "tagall")


# ═══════════════════════════════════════════════════════════
#  Fun tags: one member per message with a random line
# ═══════════════════════════════════════════════════════════
async def _fun_tag(client: Client, message: Message, session: str, pool: list):
    chat_id = message.chat.id
    if not await _guard(client, message):
        return

    reader, _err = await _ensure_assistant(client, message)
    active_tags[chat_id] = session
    try:
        async for user in _members(client, chat_id, reader):
            if chat_id not in active_tags:
                break
            if not user or user.is_bot or user.is_deleted:
                continue
            try:
                await client.send_message(
                    chat_id,
                    f"{_link(user)} {random.choice(pool)}",
                    parse_mode=enums.ParseMode.MARKDOWN,
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )
            except FloodWait as e:
                await asyncio.sleep(e.value)
                continue
            except Exception as e:
                logger.warning(f"{session} send failed: {e}")
                continue
            await asyncio.sleep(FUN_DELAY)
    except Exception as e:
        logger.warning(f"{session} failed in {chat_id}: {e}")
    finally:
        active_tags.pop(chat_id, None)
        try:
            await client.send_message(chat_id, "✅ <b>ᴛᴧɢɢɪηɢ sєssɪση єηᴅєᴅ.</b>")
        except Exception:
            pass


_FUN = {
    "gmtag": GM_MESSAGES,
    "gntag": GN_MESSAGES,
    "hitag": HI_MESSAGES,
    "lifetag": QUOTES,
    "shayari": SHAYARI,
}


@app.on_message(
    filters.command(list(_FUN), prefixes=PREFIXES) & filters.group & ~app.bl_users
)
async def fun_tag_cmd(client: Client, message: Message):
    cmd = message.command[0].lower().split("@")[0]
    await _fun_tag(client, message, cmd, _FUN[cmd])


# ═══════════════════════════════════════════════════════════
#  Stop
# ═══════════════════════════════════════════════════════════
@app.on_message(
    filters.command(STOP_COMMANDS, prefixes=PREFIXES) & filters.group & ~app.bl_users
)
async def stop_tagging(client: Client, message: Message):
    chat_id = message.chat.id

    if chat_id not in active_tags:
        return await message.reply_text("⚠️ <b>ησ ᴧᴄᴛɪᴠє ᴛᴧɢɢɪηɢ sєssɪση ғσυηᴅ.</b>")

    if not await _is_admin(client, message):
        return await message.reply_text("🚫 <b>σηʟʏ ᴧᴅϻɪηs ᴄᴧη sᴛσᴘ ᴛᴧɢɢɪηɢ.</b>")

    active_tags.pop(chat_id, None)
    await message.reply_text("🚫 <b>ᴛᴧɢɢɪηɢ ᴄᴧηᴄєʟʟєᴅ sυᴄᴄєssғυʟʟʏ.</b>")
