import re

from pyrogram import types
from pyrogram.enums import ButtonStyle

from ArtistMusic import app, config, lang

# (callback key, button label, [(help_ key, commands to take or None=all, commands to skip)])
HELP_GROUPS = [
    ("admins", "ᴀᴅᴍɪɴꜱ", [("promote", None, ()), ("admins", ("reload",), ())]),
    ("auth", "ᴀᴜᴛʜ", [("auth", None, ())]),
    ("broadcast", "ʙʀᴏᴀᴅᴄᴀꜱᴛ", [("broadcast", None, ())]),
    ("blacklist", "ʙʟᴀᴄᴋʟɪꜱᴛ", [("blchat", None, ()), ("bluser", None, ()), ("gban", None, ())]),
    ("ban", "ʙᴀɴ", [("ban", None, ()), ("mute", None, ()), ("mass", None, ("unpinall",))]),
    ("control", "ᴄᴏɴᴛʀᴏʟ", [("pause", None, ()), ("resume", None, ()), ("skip", None, ()), ("stop", None, ()),
                          ("autoplay", None, ()), ("playmode", None, ())]),
    ("loop", "ʟᴏᴏᴘ", [("loop", None, ())]),
    ("play", "ᴘʟᴀʏ", [("play", None, ())]),
    ("queue", "ǫᴜᴇᴜᴇ", [("queue", ("queue",), ())]),
    ("seek", "ꜱᴇᴇᴋ", [("seek", None, ())]),
    ("shuffle", "ꜱʜᴜꜰꜰʟᴇ", [("shuffle", None, ())]),
    ("ping", "ᴘɪɴɢ", [("ping", None, ("sudolist",)), ("stats", None, ()), ("misc", ("alive",), ())]),
    ("sudo", "ꜱᴜᴅᴏ", [("sudo", ("addsudo", "rmsudo"), ()), ("ping", ("sudolist",), ()),
                     ("maintenance", None, ()), ("eval", None, ()), ("logs", None, ())]),
    ("group", "ɢʀᴏᴜᴘ", [("group", None, ("admins",)), ("pin", ("unpinall",), ()),
                       ("welcome", None, ()), ("bots", None, ())]),
    ("clean", "ᴄʟᴇᴀɴ", [("clean", None, ())]),
    ("extra", "ᴇxᴛʀᴀ", [("info", None, ()), ("link", None, ()), ("assistant", None, ()), ("autoleave", None, ())]),
    ("sticker", "ꜱᴛɪᴄᴋᴇʀ", [("sticker", None, ())]),
    ("tag", "ᴛᴀɢ ᴀʟʟ", [("tag", None, ())]),
    ("restart", "ʀᴇꜱᴛᴀʀᴛ", [("restart", None, ()), ("leave", None, ())]),
    ("active", "ᴄᴀʟʟꜱ", [("active", None, ())]),
]


class Inline:
    def __init__(self):
        self.ikm = types.InlineKeyboardMarkup
        self.ikb = types.InlineKeyboardButton

    def cancel_dl(self, text) -> types.InlineKeyboardMarkup:
        return self.ikm([[
            self.ikb(
                text=f"✗  {text}",
                callback_data="cancel_dl",
                style=ButtonStyle.DANGER,
            )
        ]])

    def controls(
        self,
        chat_id: int,
        status: str = None,
        timer: str = None,
        remove: bool = False,
    ) -> types.InlineKeyboardMarkup:
        keyboard = []

        if status:
            keyboard.append(
                [self.ikb(
                    text=f"{status}",
                    callback_data=f"controls status {chat_id}",
                    style=ButtonStyle.PRIMARY,
                )]
            )
        elif timer:
            keyboard.append(
                [self.ikb(
                    text=f"{timer}",
                    callback_data=f"controls status {chat_id}",
                    style=ButtonStyle.PRIMARY,
                )]
            )

        if not remove:
            from ArtistMusic import db as _db
            paused = _db.active_calls.get(chat_id) == 0
            keyboard.append(
                [
                    self.ikb(text="▷", callback_data=f"controls resume {chat_id}", style=ButtonStyle.PRIMARY)
                    if paused else self.ikb(text="II", callback_data=f"controls pause {chat_id}", style=ButtonStyle.PRIMARY),
                    self.ikb(text="‣‣I", callback_data=f"controls skip {chat_id}", style=ButtonStyle.PRIMARY),
                    self.ikb(text="↻", callback_data=f"controls replay {chat_id}", style=ButtonStyle.PRIMARY),
                    self.ikb(text="▢", callback_data=f"controls stop {chat_id}", style=ButtonStyle.PRIMARY),
                ]
            )
            from ArtistMusic import db
            ap_on = chat_id in db.autoplay_on
            keyboard.append(
                [
                    self.ikb(
                        text="ᴀᴜᴛᴏᴘʟᴀʏ : ᴏɴ" if ap_on else "ᴀᴜᴛᴏᴘʟᴀʏ : ᴏғғ",
                        callback_data=f"controls autoplay {chat_id}",
                        style=ButtonStyle.SUCCESS,
                    ),
                    self.ikb(
                        text="• ᴄʟᴏsᴇ •",
                        callback_data=f"controls close {chat_id}",
                        style=ButtonStyle.DANGER,
                    ),
                ]
            )

        return self.ikm(keyboard)

    def help_markup(
        self, _lang: dict, back: bool = False
    ) -> types.InlineKeyboardMarkup:
        if back:
            rows = [
                [self.ikb(
                    text="• ʙᴀᴄᴋ •",
                    callback_data="help_main",
                    style=ButtonStyle.SUCCESS,
                )]
            ]
        else:
            _btns = {
                _key: self.ikb(
                    text=_label,
                    callback_data=f"help_{_key}",
                    style=ButtonStyle.PRIMARY,
                )
                for _key, _label, _ in HELP_GROUPS
            }
            _grid = [b for k, b in _btns.items() if k not in ("restart", "active")]
            rows = [_grid[n:n + 3] for n in range(0, len(_grid), 3)]
            rows.append([
                _btns["restart"],
                _btns["active"],
                self.ikb(
                    text="🌐 ʟᴀɴɢꜱ",
                    callback_data="help_langs",
                    style=ButtonStyle.PRIMARY,
                ),
            ])
            rows.append([
                self.ikb(
                    text="ꜱᴏᴜʀᴄᴇ",
                    url="https://github.com/elevenyts/ArtistMusic",
                    style=ButtonStyle.PRIMARY,
                )
            ])
            rows.append([
                self.ikb(
                    text="• ʙᴀᴄᴋ •",
                    callback_data="start",
                    style=ButtonStyle.SUCCESS,
                )
            ])
        return self.ikm(rows)

    def help_text(self, _lang: dict, category: str):
        """Merged text for a group; every command is listed under one group only."""
        cmd = re.compile(r"▸\s+/(\w+)")
        for _key, _label, _srcs in HELP_GROUPS:
            if _key != category:
                continue
            parts, extra = [], []
            for src, only, skip in _srcs:
                lines = (_lang.get(f"help_{src}") or "").replace("<time>", "&lt;time&gt;").split("\n")
                if only:
                    for line in lines:
                        found = cmd.search(line)
                        if found and found.group(1) in only:
                            extra.append(re.sub(r"</?blockquote>", "", line))
                    continue
                kept = []
                for line in lines:
                    found = cmd.search(line)
                    if found and found.group(1) in skip:
                        # drop the command but keep any blockquote tag on its line
                        line = "".join(re.findall(r"</?blockquote>", line))
                        if line == "</blockquote>" and kept:
                            kept[-1] += line
                        continue
                    kept.append(line)
                parts.append("\n".join(kept))
            if extra:
                parts.append("<blockquote>" + "\n".join(extra) + "</blockquote>")
            seen, out = set(), []
            for line in "\n\n".join(p for p in parts if p).split("\n"):
                bare = re.sub(r"</?blockquote>", "", line).strip()
                if bare and "▸" not in bare and "•" not in bare and bare in seen:
                    if line.endswith("</blockquote>") and out:
                        out[-1] += "</blockquote>"
                    continue
                seen.add(bare)
                out.append(line)
            return "\n".join(out) or None
        return None

    def langs_markup(self) -> types.InlineKeyboardMarkup:
        langs = [
            ("🇬🇧 English", "en"), ("🇮🇳 हिन्दी", "hi"),
            ("🇮🇳 తెలుగు", "te"), ("🇮🇳 भोजपुरी", "bho"),
            ("🇳🇵 नेपाली", "ne"), ("🇰🇷 한국어", "ko"),
            ("🇲🇲 မြန်မာ", "my"), ("🇮🇩 Bahasa Indonesia", "id"),
            ("🇧🇷 Português", "pt"), ("🇸🇦 العربية", "ar"),
            ("🇪🇸 Español", "es"), ("🇫🇷 Français", "fr"),
            ("🇷🇺 Русский", "ru"), ("🇩🇪 Deutsch", "de"),
            ("🇹🇷 Türkçe", "tr"), ("🇧🇩 বাংলা", "bn"),
            ("🇹🇭 ไทย", "th"), ("🇻🇳 Tiếng Việt", "vi"),
            ("🇯🇵 日本語", "ja"), ("🇨🇳 中文", "zh"),
            ("🇵🇰 اردو", "ur"), ("🇮🇷 فارسی", "fa"),
        ]
        rows = []
        for i in range(0, len(langs), 2):
            row = [self.ikb(text=langs[i][0], callback_data=f"setlang_{langs[i][1]}", style=ButtonStyle.PRIMARY)]
            if i + 1 < len(langs):
                row.append(self.ikb(text=langs[i + 1][0], callback_data=f"setlang_{langs[i + 1][1]}", style=ButtonStyle.PRIMARY))
            rows.append(row)
        rows.append([self.ikb(
            text="• ʙᴀᴄᴋ •",
            callback_data="help_main",
            style=ButtonStyle.SUCCESS,
        )])
        return self.ikm(rows)

    # FIX #1: the 'text' param is now actually used (in the status row)
    def ping_markup(self, text: str) -> types.InlineKeyboardMarkup:
        return self.ikm([
            [
                self.ikb(
                    text=f"{text}",
                    callback_data="ping_refresh",
                    style=ButtonStyle.PRIMARY,
                ),
            ],
            [
                self.ikb(text="  ᴄʜᴀɴɴᴇʟ", url=config.SUPPORT_CHANNEL, style=ButtonStyle.PRIMARY),
                self.ikb(text="  ꜱᴜᴘᴘᴏʀᴛ",  url=config.SUPPORT_CHAT,    style=ButtonStyle.PRIMARY),
            ],
            [
                self.ikb(
                    text="ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ",
                    url=f"https://t.me/{app.username}?startgroup=true",
                    style=ButtonStyle.SUCCESS,
                ),
            ],
        ])

    # FIX #2: 'item_id' is now passed in callback_data so that the
    # correct item is controlled in a multi-track queue (the wrong item is not pressed)
    def play_queued(
        self, chat_id: int, item_id: str, _text: str
    ) -> types.InlineKeyboardMarkup:
        return self.ikm([
            [
                self.ikb(text="▷",   callback_data=f"controls resume {chat_id} {item_id}", style=ButtonStyle.PRIMARY),
                self.ikb(text="II",  callback_data=f"controls pause {chat_id} {item_id}",  style=ButtonStyle.PRIMARY),
                self.ikb(text="↻",   callback_data=f"controls replay {chat_id} {item_id}", style=ButtonStyle.PRIMARY),
                self.ikb(text="‣‣I", callback_data=f"controls skip {chat_id} {item_id}",   style=ButtonStyle.PRIMARY),
                self.ikb(text="▢",   callback_data=f"controls stop {chat_id} {item_id}",   style=ButtonStyle.PRIMARY),
            ],
        ])

    def queue_markup(
        self, chat_id: int, _text: str, playing: bool
    ) -> types.InlineKeyboardMarkup:
        _action = "pause" if playing else "resume"
        return self.ikm(
            [[self.ikb(
                text=_text,
                callback_data=f"controls {_action} {chat_id} q",
                style=ButtonStyle.SUCCESS,
            )]]
        )

    # FIX #3: 'language' is now displayed in its own row
    def settings_markup(
        self, lang: dict, admin_only: bool, force_admin: bool, language: str, chat_id: int
    ) -> types.InlineKeyboardMarkup:
        play_mode_txt  = lang["admin_only_txt"] if admin_only  else lang["everyone"]
        force_mode_txt = lang["admin_only_txt"] if force_admin else lang["everyone"]
        return self.ikm([
            [
                self.ikb(text="  " + lang["play_mode"],  callback_data=f"controls status {chat_id}", style=ButtonStyle.PRIMARY),
                self.ikb(text=play_mode_txt,               callback_data="playmode",                   style=ButtonStyle.SUCCESS),
            ],
            [
                self.ikb(text="  " + lang["force_mode"], callback_data=f"controls status {chat_id}", style=ButtonStyle.PRIMARY),
                self.ikb(text=force_mode_txt,              callback_data="forcemode",                  style=ButtonStyle.SUCCESS),
            ],
            [
                self.ikb(text="" + language.upper(),  callback_data="help_langs", style=ButtonStyle.PRIMARY),
            ],
        ])

    def start_key(
        self, lang: dict, private: bool = False
    ) -> types.InlineKeyboardMarkup:
        rows = [
            [
                self.ikb(
                    text="" + lang["add_me"],
                    url=f"https://t.me/{app.username}?startgroup=true",
                    style=ButtonStyle.PRIMARY,
                )
            ],
            [
                self.ikb(text="ᴏᴡɴᴇʀ", url=f"tg://openmessage?user_id={config.OWNER_ID}"),
                self.ikb(text="  " + lang["help"],  callback_data="help"),
            ],
            [
                self.ikb(text=" " + lang["channel"], url=config.SUPPORT_CHANNEL),
                self.ikb(text="  " + lang["support"], url=config.SUPPORT_CHAT),
            ],
        ]
        return self.ikm(rows)

    def yt_key(self, link: str) -> types.InlineKeyboardMarkup:
        return self.ikm([
            [
                self.ikb(text="ᴄᴏᴘʏ ʟɪɴᴋ",     copy_text=link, style=ButtonStyle.PRIMARY),
                self.ikb(text="ᴏᴘᴇɴ ɪɴ ʏᴛ", url=link,       style=ButtonStyle.DANGER),
            ],
        ])
