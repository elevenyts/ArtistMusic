<div align="center">

# 🗂️ Project Structure

Where everything lives in **ArtistMusic**.
Made by **Artist** · [@elevenyts](https://github.com/elevenyts) · [ArtistBots](https://t.me/Artistbots)

</div>

> New here? Read [ARCHITECTURE.md](ARCHITECTURE.md) for *how* the pieces work together. This file only tells you *where* things are.

---

## Top level

```text
ArtistMusic/
├── ArtistMusic/              # The bot's Python package (all source code)
├── .github/
│   └── workflows/
│       └── deploy.yml        # CI (syntax + locale check) and Docker/Render/Fly deploy
├── .dockerignore             # Files excluded from the Docker build context
├── .gitignore                # Files Git must never track (.env, sessions, cache, …)
├── Artist.env                # Environment variable TEMPLATE → copy to .env and fill in
├── config.py                 # Reads env vars into the Config object
├── requirements.txt          # Python dependencies
├── start                     # Start command:  python3 -m ArtistMusic
├── setup                     # VPS helper script (ffmpeg, deno, pip install, creates .env)
├── Dockerfile                # Image: python 3.10 + ffmpeg + node
├── docker-compose.yml        # Run on a VPS with Docker
├── Procfile                  # Heroku/Procfile-style worker command
├── heroku.yml                # Heroku container deploy
├── railway.json              # Railway deploy settings
├── render.yaml               # Render Blueprint
├── fly.toml                  # Fly.io settings
├── app.json                  # Heroku "Deploy" button manifest
├── README.md                 # Project overview, features, commands
├── DEPLOY.md                 # Step-by-step deploy guide
├── ARCHITECTURE.md           # How the bot works internally
├── Structure.md              # This file
├── CONTRIBUTING.md           # How to contribute
├── SECURITY.md               # Security policy & hardening checklist
└── LICENSE                   # MIT License + project details & credits
```

---

## `ArtistMusic/` — the package

```text
ArtistMusic/
├── __init__.py               # Creates the shared objects: config, app, userbot, db, lang,
│                             #   yt, tg, queue, preload, tune (+ stop())
├── __main__.py               # Entry point: boot sequence, plugin loading, health server
│
├── core/                     # Engine: clients, database, calls, downloading
├── helpers/                  # Reusable building blocks used by plugins
├── plugins/                  # Music & bot-management commands
├── Artistbots/               # Group manager, tag, sticker & welcome tools
└── locales/                  # Translations (22 languages)
```

### `core/` — the engine

| File | What it does |
|---|---|
| `bot.py` | `Bot` — the main Pyrogram bot client; holds owner, sudoers, blacklist filters |
| `userbot.py` | `Userbot` — up to 3 assistant accounts (`STRING_SESSION`, `2`, `3`) that join voice chats |
| `calls.py` | `TgCall` — voice/video streaming with py-tgcalls: play, pause, resume, seek, next, stop |
| `youtube.py` | `YouTube` — search, playlists, ArtistBots API `/download`, cookies fallback, logger-group song cache |
| `mongo.py` | `MongoDB` — all database access plus in-memory caches (admins, auth, chats, language, cache) |
| `preload.py` | Background preloading of upcoming tracks |
| `autoplay.py` | Picks a related track when the queue ends (`/autoplay`) |
| `telegram.py` | Downloads audio/video files that users send or reply to |
| `lang.py` | Loads locale JSON files, merges with English fallback, `@lang.language()` decorator |
| `dir.py` | Creates the `cache/` and `downloads/` folders at startup |

### `helpers/` — shared tools

| File | What it does |
|---|---|
| `_queue.py` | Per-chat queue: add, force-add, next, remove, clear, peek |
| `_dataclass.py` | `Media` and `Track` data classes |
| `_play.py` | `checkUB` decorator — checks the assistant before play commands |
| `_admins.py` | `admin_check`, `can_manage_vc`, admin list cache & reload |
| `_inline.py` | Inline keyboard / button builders |
| `_thumbnails.py` | Generates the now-playing thumbnail image |
| `_preload.py` | Next-track download manager |
| `_utilities.py` | Time/size formatting, user extraction, safe send/edit/reply, logging helpers |
| `_exec.py` | Code runner used by the owner-only `/eval` and `/exec` |
| `fonts/` | `artistbots_regular.ttf`, `artistbots_bold.ttf` for thumbnails |

### `plugins/` — music & bot management

Every `.py` file here is loaded automatically at startup.

| Area | Files (commands) |
|---|---|
| **Playback** | `play.py` (play / vplay / cplay + force variants), `pause.py`, `resume.py`, `skip.py`, `stop.py` (`/end`, `/stop`), `seek.py`, `loop.py`, `shuffle.py`, `queue.py`, `autoplay.py`, `autoleave.py`, `channelplay.py` |
| **Access control** | `auth.py` (`/auth`, `/unauth`, `/authlist`, `/reload`), `sudoers.py`, `blacklist.py`, `gban.py` |
| **Owner & maintenance** | `broadcast.py`, `maintenance.py`, `restart.py` (`/restart`, `/logs`, `/update`, `/logger`), `eval.py` (`/eval`, `/exec`), `leave.py`, `groupdata.py` |
| **Info & utility** | `start.py` (`/start`, `/help`, `/playmode`, `/settings`), `ping.py` (`/ping`, `/alive`), `stats.py`, `active.py` (`/ac`, `/activevc`), `bots.py` (`/bots`), `link.py`, `userid.py` (`/id`) |
| **Events & background** | `callbacks.py` (button presses), `iquery.py` (inline queries), `new_chat.py` (bot added to / removed from a chat, `/link`), `adminmention.py` (`@admin` call), `misc.py` (maintenance-mode gate, voice-chat watcher, auto-leave and play-time background tasks) |

### `Artistbots/` — group manager & fun tools

Every `.py` file here is also loaded automatically.

| File | What it does |
|---|---|
| `actions.py` | `/ban` `/dban` `/sban` `/tban` `/mute` `/tmute` `/kick` `/kickme` and the un-actions |
| `promote.py` | `/promote` `/fullpromote` `/demote` `/tempadmin` |
| `grouphandler.py` | `/pin` `/unpin` `/setphoto` `/removephoto` `/settitle` `/setdescription` |
| `purge.py`, `del_msg.py` | `/purge` `/spurge` `/del` `/deleteall` |
| `mass_actions.py` | Group-owner / sudo mass actions (`/kickall`, `/banall`, …) with a Yes/No confirmation button |
| `zombie.py` | `/zombies` cleaner, `/admins`, `/staff` |
| `info.py` | `/info` `/userinfo` `/whois` |
| `tagall.py` | `/tagall` `/all` `@all` `/utag` `/mention` and tag-stop commands |
| `funtag_messages.py` | Message pool for fun tags (GM / GN / Hi / life / shayari) |
| `welcome.py` | Welcome card for new members (`/welcome`) |
| `vclog.py` | Voice-chat join/leave alerts (`/vclog`) |
| `kang.py`, `sticker.py` | Sticker pack tools (`/kang`, `/sticker`) |
| `_common.py`, `_textimg.py` | Shared helpers, text-to-image rendering for cards |
| `assets/fonts/` | Large Unicode fonts (Unifont, WenQuanYi) so names in any script render correctly |

### `locales/` — translations

`en.json` is the base. 22 languages: `ar bho bn de en es fa fr hi id ja ko my ne pt ru te th tr ur vi zh`.
Add a new one as described in [CONTRIBUTING.md](CONTRIBUTING.md#translations).

---

## Files created at runtime (never committed)

| Path | Created by | Purpose |
|---|---|---|
| `.env` | you | Your real configuration |
| `*.session` | Pyrogram | Login sessions |
| `log.txt` (+ rotations) | `__init__.py` | Log file, rotates at 10 MB |
| `downloads/` | `core/dir.py` | Downloaded audio / video |
| `cache/` | `core/dir.py` | Thumbnails and temporary files |

---

<div align="center">

Made with ❤️ by **Artist** · Powered by **ArtistBots**
[GitHub](https://github.com/elevenyts) · [Channel](https://t.me/Artistbots) · [Support](https://t.me/Elevenytschats)

</div>
