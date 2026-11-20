# ==========================================================
#  Button_emoji.py  -  PREMIUM EMOJI SETTINGS (ek hi file)
# ==========================================================
#  1) BUTTON_EMOJI : inline button ka naam  ->  premium emoji ID
#  2) TEXT_EMOJI   : message text ka default emoji -> premium emoji ID
#
#  RULE (dono jagah same):
#     ID likhi hai (sirf digits)  -> premium emoji use hoga
#     ID khali ""  ya galat hai   -> default / normal emoji hi dikhega
#
#  Premium emoji ID kaise nikale?  Kisi bhi premium emoji ko @JsonDumpBot /
#  @RawDataBot ko bhejo -> "custom_emoji_id" copy karo.
#
#  Bas ID badlo aur bot restart karo. Code me kuch nahi badalna.
# ==========================================================
import functools
import inspect
import logging
import re
import unicodedata

log = logging.getLogger("ArtistMusic")

# ----------------------------------------------------------
# MASTER SWITCHES (False karoge to sab jagah default emoji)
# ----------------------------------------------------------
PREMIUM_BUTTONS = True   # inline buttons me premium emoji
PREMIUM_TEXT = True      # messages (locales/*.json) me premium emoji

# True  : button me premium icon aane par text ka purana emoji / decoration
#         (jaise "♫ Back ♫" -> "Back") hata diya jata hai
# False : text jaisa hai waisa rahega, icon uske saath alag se lagega
REMOVE_DEFAULT_BUTTON_EMOJI = True


# ==========================================================
# 1) BUTTON EMOJIS      "button name": "premium emoji id"
#    ID khali "" = default emoji (jo button text me pehle se hai)
# ==========================================================
BUTTON_EMOJI = {
    # ---- start / navigation ----
    "back": "",            # ♫ Back ♫
    "help": "5972055534352733289",            # ♫ Help ♫ / ✦ Help
    "langs": "6325837556801868339",           # 🌐 Langs  (language list kholne wala)
    "add_to_group": "6325454162251223334",    # Add To Group
    "add_me": "6325454162251223334",          # ♡ + Add Me
    "owner": "",           # ♛ Owner ♛
    "support": "5971801057540443125",         # 🦋 Support
    "channel": "5852830669599674051",         # Channel
    "updates": "5971944878815317190",         # 🌙 Updates

    # ---- player controls (neeche ki row) ----
    "toggle": "",          # ▷  (play / pause toggle)
    "resume": "",          # ▷  (queue wala resume)
    "pause": "",           # II
    "skip": "",            # Ⅱ / ‣‣I
    "replay": "",          # ↻
    "stop": "",            # ▢
    "autoplay": "",        # ♫ Autoplay: On/Off ♫
    "status": "",          # status / timer wali button
    "cancel": "",          # ✗ Cancel (download cancel)

    # ---- settings ----
    "admin_play": "",      # 🛡 Admin Play   (left button)
    "force_mode": "",      # ⚡ Force Mode   (left button)
    "playmode": "",        # Everyone / Admin Only (play mode value)
    "forcemode": "",       # Everyone / Admin Only (force mode value)

    # ---- YouTube link buttons ----
    "copy_link": "",
    "open_in_yt": "",

    # ---- help menu category buttons ----
    "admins": "",
    "auth": "",
    "broadcast": "",
    "blacklist": "",
    "ban": "",
    "control": "",
    "loop": "",
    "play": "",
    "queue": "",
    "seek": "",
    "shuffle": "",
    "ping": "",
    "sudo": "",
    "group": "",
    "clean": "",
    "extra": "",
    "sticker": "",
    "tag": "",             # Tag All
    "restart": "",
    "calls": "",

    # ---- sticker / kang buttons ----
    "stk_add": "",         # ➕ Save Pack
    "stk_new": "",         # 🆕 New Pack
    "stk_no": "",          # ✖ Cancel
}
# Naya button add karna ho to bas yahan likh do:  "button_name": "ID"
# Button ka naam = uske text ke English words, small letters me, "_" laga ke
#   (jaise "Add To Group" -> add_to_group)  YA  callback_data ka pehla word.


# ==========================================================
# 2) TEXT EMOJIS (messages)     "default emoji": "premium emoji id"
#    en.json / hi.json / ... sab language files me ye apne aap lagta hai.
#    (en.json me kisi emoji ke tag me ID pehle se likhi ho to wo pehle chalegi)
# ==========================================================
TEXT_EMOJI = {
    "✅": "5852871561983299073",
    "⚠️": "5449671663006291693",
    "❌": "5852812849780362931",
    "👤": "4967667085606912536",
    "⚡": "5199785165735367039",
    "🎵": "6325708780797432188",
    "❤️": "5255956191141454203",
    "📞": "5465624021947140508",
    "💠": "5971944878815317190",
    "💾": "4990318000096675490",
    "🖥": "5929221469027437894",
    "⏰": "4967525849902350972",
    "🔹": "5972211849687470465",
    "⚙️": "5929098607192969118",
    "◀️": "4970176665062736422",
    "🔺": "5971837723676249096",
    "📼": "6026256492619895014",
    "🔸": "5972240522889138094",
    "🌎": "5224450179368767019",
    "📣": "5197304993920616826",
    "🟢": "6325587147323609800",

    # --- neeche wale emojis ki ID abhi khali hai (default dikhega) ---
    "⏳": "", "🚫": "", "📋": "", "🔐": "", "🚶": "", "⏱": "", "🔄": "",
    "📥": "", "📤": "", "🛑": "", "🛡": "", "🚷": "", "🔁": "", "⏩": "",
    "🔀": "", "🔧": "", "📡": "", "⏪": "", "⏸": "", "▶️": "", "⏭": "",
    "⏹": "", "📊": "", "👑": "", "📌": "", "🏠": "", "📛": "", "🔕": "",
    "🔇": "", "🖤": "", "♡": "", "🔗": "", "➲": "", "🎧": "", "🕔": "",
    "🎶": "", "🔴": "", "🔒": "", "👋": "", "🥀": "", "✦": "", "❓": "",
    "👢": "", "🧹": "", "🧟": "", "🪪": "", "♾": "", "🚪": "", "🤖": "",
    "📢": "", "📝": "", "🏃": "", "💻": "", "🔨": "", "⭐": "", "💣": "",
    "🏷": "", "✧": "", "🎴": "", "✨": "", "🎮": "", "👥": "", "🏆": "",
    "🌐": "",
}


# ==========================================================
#  Neeche ka code chhedne ki zarurat nahi
# ==========================================================
_VS16 = "\ufe0f"
_EM = (
    r"(?:[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u2B06\u2B05\u2B07"
    r"\u23E9-\u23FA\u231A\u231B\u25B6\u25C0\u2705\u274C]\ufe0f?)"
)
_TAG = r"<tg-emoji\s+emoji-id=(['\"])(.*?)\1\s*>(.*?)</tg-emoji>"
_TAG_RE = re.compile(_TAG, re.DOTALL)
_BARE_RE = re.compile(r"(<[^>]*>)|" + _EM)


def _is_id(value) -> bool:
    return str(value).strip().isdigit()


def _text_ids() -> dict:
    return {k.replace(_VS16, ""): str(v).strip() for k, v in TEXT_EMOJI.items() if _is_id(v)}


def process_text(value):
    """Locale string ke emojis: ID ho to premium, warna default emoji."""
    if not isinstance(value, str):
        return value
    message_like = (
        "<tg-emoji" in value or "<blockquote" in value or "<b>" in value or "\n" in value
    )
    if not message_like:
        return value
    ids = _text_ids() if PREMIUM_TEXT else {}

    def wrap(emoji: str):
        eid = ids.get(emoji.replace(_VS16, ""))
        return f"<tg-emoji emoji-id='{eid}'>{emoji}</tg-emoji>" if eid else emoji

    out = []
    pos = 0
    for m in _TAG_RE.finditer(value):
        out.append(_BARE_RE.sub(lambda x: x.group(1) or wrap(x.group(0)), value[pos:m.start()]))
        eid, inner = m.group(2).strip(), m.group(3)
        if PREMIUM_TEXT and _is_id(eid):
            out.append(f"<tg-emoji emoji-id='{eid}'>{inner}</tg-emoji>")
        else:
            out.append(wrap(inner))   # khali ID -> map se ID ya default emoji
        pos = m.end()
    out.append(_BARE_RE.sub(lambda x: x.group(1) or wrap(x.group(0)), value[pos:]))
    return "".join(out)


# ---------------- button name resolve ----------------
_SC_REV = {c: a for a, c in zip(
    "abcdefghijklmnopqrstuvwxyz", "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋℓᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ")}
_SC_REV.update({"ꜱ": "s", "ғ": "f", "ʟ": "l"})


def _slug(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "")       # bold-math -> normal
    t = "".join(_SC_REV.get(c, c) for c in t).lower()   # small caps -> normal
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def _cb_name(cb):
    if cb is None:
        return ""
    if isinstance(cb, bytes):
        cb = cb.decode("utf-8", "ignore")
    parts = str(cb).split()
    if not parts:
        return ""
    if parts[0] == "controls" and len(parts) > 1:
        return parts[1]
    if parts[0] == "help_main" or parts[0] == "start":
        return "back"
    if parts[0].startswith("help_"):
        return parts[0][5:]
    if parts[0] == "cancel_dl":
        return "cancel"
    return parts[0].split(":")[0]


_BTN_IDS = None


def _button_ids() -> dict:
    global _BTN_IDS
    if _BTN_IDS is None:
        _BTN_IDS = {_slug(k): str(v).strip() for k, v in BUTTON_EMOJI.items() if _is_id(v)}
    return _BTN_IDS


def _find_button_id(text, cb):
    ids = _button_ids()
    if not ids:
        return None
    for cand in (_slug(text), _slug(_cb_name(cb))):
        if cand and cand in ids:
            return ids[cand]
    return None


def _strip_default(text: str) -> str:
    s = re.sub(r"^[^\w]+|[^\w]+$", "", text, flags=re.UNICODE)
    if re.sub(r"[\sIiⅡ_]", "", s) == "":      # sirf symbol wali button
        return "\u2800"                         # invisible text (button khali na ho)
    return s


def install():
    """InlineKeyboardButton me BUTTON_EMOJI ke hisaab se icon_custom_emoji_id lagata hai."""
    try:
        from pyrogram import types
    except Exception:
        return
    cls = types.InlineKeyboardButton
    if getattr(cls, "_btn_emoji_patched", False):
        return
    try:
        params = inspect.signature(cls.__init__).parameters
    except Exception:
        params = {}
    if "icon_custom_emoji_id" not in params:
        log.warning(
            "Button_emoji: installed pyrogram/kurigram InlineKeyboardButton me "
            "icon_custom_emoji_id nahi hai -> buttons me default emoji rahenge."
        )
        return
    orig = cls.__init__

    @functools.wraps(orig)
    def __init__(self, text=None, *args, **kwargs):
        if PREMIUM_BUTTONS and isinstance(text, str) and not kwargs.get("icon_custom_emoji_id"):
            cb = kwargs.get("callback_data", args[0] if args else None)
            eid = _find_button_id(text, cb)
            if eid:
                kwargs["icon_custom_emoji_id"] = eid
                if REMOVE_DEFAULT_BUTTON_EMOJI:
                    text = _strip_default(text)
        orig(self, text, *args, **kwargs)

    cls.__init__ = __init__
    cls._btn_emoji_patched = True


install()
