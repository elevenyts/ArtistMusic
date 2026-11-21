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
    "back": "5805434498602506971",            # ♫ Back ♫
    "help": "5030653042995757810",            # ♫ Help ♫ / ✦ Help
    "langs": "6325837556801868339",           # 🌐 Langs  (language list kholne wala)
    "add_to_group": "6325454162251223334",    # Add To Group
    "add_me": "6325454162251223334",          # ♡ + Add Me
    "owner": "",           # ♛ Owner ♛
    "support": "6026306335715365949",         # 🦋 Support
    "channel": "6325774639825948896",         # Channel
    "updates": "6088954841818732889",         # 🌙 Updates

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
    "admin_play": "6325413811033477368",      # 🛡 Admin Play   (left button)
    "force_mode": "6325415120998502570",      # ⚡ Force Mode   (left button)
    "playmode": "6325587147323609800",        # Everyone / Admin Only (play mode value)
    "forcemode": "6325814248014353377",       # Everyone / Admin Only (force mode value)

    # ---- YouTube link buttons ----
    "copy_link": "",
    "open_in_yt": "",

    # ---- help menu category buttons ----
    "admins": "4967667085606912536",
    "auth": "4967797089971995307",
    "broadcast": "4967957395331351254",
    "blacklist": "5032973497861669622",
    "ban": "5852812849780362931",
    "control": "4965290516993278759",
    "loop": "4969971262546772590",
    "play": "4970133401857163956",
    "queue": "4970086827231806362",
    "seek": "4967525849902350972",
    "shuffle": "5974235702701853774",
    "ping": "4969746438188696430",
    "sudo": "4970181191958266458",
    "group": "4967667085606912536",
    "clean": "5033287275287413303",
    "extra": "5030749344752468962",
    "sticker": "5033108527338488459",
    "tag": "4967853603151676186",             # Tag All
    "restart": "4969971262546772590",
    "calls": "4969971262546772590",

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
    "⏹": "", "📊": "", "👑": "6325564362522104416", "📌": "", "🏠": "", "📛": "", "🔕": "",
    "🔇": "", "🖤": "", "♡": "", "🔗": "", "➲": "", "🎧": "", "🕔": "",
    "🎶": "", "🔴": "", "🔒": "", "👋": "", "🥀": "5875204537224008462", "✦": "", "❓": "",
    "👢": "", "🧹": "", "🧟": "", "🪪": "", "♾": "", "🚪": "", "🤖": "",
    "📢": "6237568428316562386", "📝": "", "🏃": "", "💻": "5030534970049823529", "🔨": "", "⭐": "", "💣": "",
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

# Telegram custom emoji (<tg-emoji>) ke andar sirf ASSLI emoji hi chal sakta hai.
# "♡ ➲ ✦ ✧ ◈ ✗ ♫ ▷" jaise symbols emoji nahi hain -> ENTITY_TEXT_INVALID aata hai.
_BMP_REAL_EMOJI = set(
    "\u203c\u2049\u2122\u2139\u2194\u2195\u2196\u2197\u2198\u2199\u21a9\u21aa"
    "\u231a\u231b\u2328\u23cf\u23e9\u23ea\u23eb\u23ec\u23ed\u23ee\u23ef\u23f0"
    "\u23f1\u23f2\u23f3\u23f8\u23f9\u23fa\u24c2\u25aa\u25ab\u25b6\u25c0\u25fb"
    "\u25fc\u25fd\u25fe\u2600\u2601\u2602\u2603\u2604\u260e\u2611\u2614\u2615"
    "\u2618\u261d\u2620\u2622\u2623\u2626\u262a\u262e\u262f\u2638\u2639\u263a"
    "\u2640\u2642\u2648\u2649\u264a\u264b\u264c\u264d\u264e\u264f\u2650\u2651"
    "\u2652\u2653\u265f\u2660\u2663\u2665\u2666\u2668\u267b\u267e\u267f\u2692"
    "\u2693\u2694\u2695\u2696\u2697\u2699\u269b\u269c\u26a0\u26a1\u26a7\u26aa"
    "\u26ab\u26b0\u26b1\u26bd\u26be\u26c4\u26c5\u26c8\u26ce\u26cf\u26d1\u26d3"
    "\u26d4\u26e9\u26ea\u26f0\u26f1\u26f2\u26f3\u26f4\u26f5\u26f7\u26f8\u26f9"
    "\u26fa\u26fd\u2702\u2705\u2708\u2709\u270a\u270b\u270c\u270d\u270f\u2712"
    "\u2714\u2716\u271d\u2721\u2728\u2733\u2734\u2744\u2747\u274c\u274e\u2753"
    "\u2754\u2755\u2757\u2763\u2764\u2795\u2796\u2797\u27a1\u27b0\u27bf\u2934"
    "\u2935\u2b05\u2b06\u2b07\u2b1b\u2b1c\u2b50\u2b55\u3030\u303d\u3297\u3299"
)


def _is_real_emoji(text: str) -> bool:
    """True agar text Telegram custom-emoji ke liye valid (asli) emoji hai."""
    t = (text or "").replace(_VS16, "").replace("\u200d", "")
    if not t:
        return False
    for ch in t:
        cp = ord(ch)
        if 0x1F000 <= cp <= 0x1FAFF or 0x1F1E6 <= cp <= 0x1F1FF or ch in _BMP_REAL_EMOJI:
            continue
        return False
    return True


def strip_custom_emoji(text: str) -> str:
    """<tg-emoji ...>X</tg-emoji> -> X  (plain text fallback)."""
    return _TAG_RE.sub(lambda m: m.group(3), text) if isinstance(text, str) else text


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
        if eid and _is_real_emoji(emoji):
            return f"<tg-emoji emoji-id='{eid}'>{emoji}</tg-emoji>"
        return emoji

    out = []
    pos = 0
    for m in _TAG_RE.finditer(value):
        out.append(_BARE_RE.sub(lambda x: x.group(1) or wrap(x.group(0)), value[pos:m.start()]))
        eid, inner = m.group(2).strip(), m.group(3)
        if PREMIUM_TEXT and _is_id(eid) and _is_real_emoji(inner):
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
