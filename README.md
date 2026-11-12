<div align="center">

<img src="https://capsule-render.vercel.app/api?type=rect&color=0:0f0c29,50:302b63,100:24243e&height=150&section=header&text=ArtistMusic&fontSize=56&fontColor=ffffff&fontAlignY=50&desc=Telegram%20voice%20chat%20music%20engine%20%E2%80%A2%20written%20in%20Go&descSize=16&descAlignY=76&descColor=b8b5ff" width="100%" alt="ArtistMusic"/>

<br/>

<a href="https://t.me/Artistbots"><img src="https://img.shields.io/badge/Updates-@Artistbots-229ED9?style=flat-square&logo=telegram&logoColor=white" alt="Updates"></a>
<a href="https://t.me/Elevenytschats"><img src="https://img.shields.io/badge/Chat-@Elevenytschats-229ED9?style=flat-square&logo=telegram&logoColor=white" alt="Chat"></a>
<img src="https://img.shields.io/badge/Go-1.26+-00ADD8?style=flat-square&logo=go&logoColor=white" alt="Go">
<img src="https://img.shields.io/badge/MongoDB-required-47A248?style=flat-square&logo=mongodb&logoColor=white" alt="MongoDB">
<a href="./LICENSE"><img src="https://img.shields.io/badge/License-GPL--3.0-blue?style=flat-square" alt="License"></a>

<br/><br/>

**Stream music and video into Telegram group voice chats, with multi-assistant support, a full playback toolkit and one-click deploys.**

[Features](#-features) · [Deploy](#-deploy) · [Setup](#-setup) · [Config](#-configuration) · [Commands](#-commands) · [Structure](#-project-structure)

</div>

<br/>

## ✨ Features

|  |  |
| :-- | :-- |
| ⚡ **Fast streaming** | Go + native `ntgcalls` bindings for low-latency, stutter-free playback |
| 🤖 **Multiple assistants** | Spread voice chats across several assistant accounts, auto balanced |
| 🎬 **Audio & video** | `/play` for audio, `/vplay` for video, plus force-play variants |
| 🎛️ **Full control** | Seek, speed, loop, shuffle, jump, move, replay, playlists, autoplay |
| 📡 **Channel play** | Play into a linked channel's voice chat with the `c` commands (`/cplay`) |
| 🔌 **Many sources** | YouTube, Telegram files, direct links, and the Artistbots / Artist APIs |
| 🌍 **Localization** | English, with YAML locale files so more languages can be added |
| 🛡️ **Admin tools** | Sudo users, per-chat auth, blacklists, maintenance mode, admin & clean mode |
| 📝 **Logging** | Voice chat logger, start/add/remove logs and error reports to a log chat |

<br/>

## 🚀 Deploy

<div align="center">

<a href="https://heroku.com/deploy?template=https://github.com/elevenyts/ArtistMusic"><img src="https://www.herokucdn.com/deploy/button.svg" alt="Deploy to Heroku" height="36"></a>
&nbsp;
<a href="https://railway.com/new/template?template=https://github.com/elevenyts/ArtistMusic"><img src="https://railway.com/button.svg" alt="Deploy on Railway" height="36"></a>
&nbsp;
<a href="https://render.com/deploy?repo=https://github.com/elevenyts/ArtistMusic"><img src="https://render.com/images/deploy-to-render-button.svg" alt="Deploy to Render" height="36"></a>
&nbsp;
<a href="https://app.koyeb.com/deploy?type=git&repository=elevenyts/ArtistMusic&branch=dev&name=artistmusic&service_type=worker&env[API_ID]=&env[API_HASH]=&env[TOKEN]=&env[MONGO_DB_URI]=&env[STRING_SESSIONS]=&env[OWNER_ID]="><img src="https://www.koyeb.com/static/images/deploy/button.svg" alt="Deploy to Koyeb" height="36"></a>

</div>

> [!IMPORTANT]
> Set **`OWNER_ID`** to your own Telegram user ID before you deploy. It decides who can use owner-only commands such as `/broadcast`, `/addsudo` and `/sh`.

<br/>

## 🛠️ Setup

You need: **API ID/Hash** ([my.telegram.org](https://my.telegram.org)), a **bot token** ([@BotFather](https://t.me/BotFather)), a **MongoDB URI**, and at least one **assistant session string**.

<details open>
<summary><b>🐳 Docker (recommended)</b></summary>

```bash
git clone https://github.com/elevenyts/ArtistMusic.git
cd ArtistMusic

cp sample.env .env && nano .env     # fill in your values
docker compose up -d --build
```

```bash
docker compose logs -f artistmusic      # live logs
docker compose restart artistmusic      # restart
git pull && docker compose up -d --build   # update
```

</details>

<details>
<summary><b>🖥️ VPS / Linux</b></summary>

```bash
sudo apt-get update && sudo apt-get install -y git curl ffmpeg build-essential

git clone https://github.com/elevenyts/ArtistMusic.git
cd ArtistMusic

bash install.sh                     # installs dependencies
cp sample.env .env && nano .env     # fill in your values
```

Run it 24/7, pick one:

```bash
bash start.sh                       # builds, sets library paths, auto-restarts on crash
```

```bash
sudo bash setup_service.sh          # systemd service
sudo systemctl start artistmusic
sudo systemctl status artistmusic
```

</details>

<br/>

## ⚙️ Configuration

Copy `sample.env` to `.env`. Variables marked ✅ are required.

| Variable | | Default | Description |
| :-- | :-: | :-- | :-- |
| `API_ID` | ✅ | | Telegram API ID |
| `API_HASH` | ✅ | | Telegram API hash |
| `TOKEN` | ✅ | | Bot token from @BotFather |
| `MONGO_DB_URI` | ✅ | | MongoDB connection string |
| `STRING_SESSIONS` | ✅ | | Assistant session strings, separated by space or comma |
| `OWNER_ID` | ✅ | | Telegram user ID of the owner |
| `SESSION_TYPE` | | `pyrogram` | Session string library: `pyrogram`, `telethon`, `gogram` |
| `DB_NAME` | | `ArtistMusic` | MongoDB database name |
| `LOGGER_ID` | | `0` | Chat ID for logs and error reports (`0` turns it off) |
| `OWNER_USERNAME` | | | Used for the developer button |
| `DEV_URL` | | | Custom developer link |
| `DURATION_LIMIT` | | `4200` | Max track length in seconds |
| `QUEUE_LIMIT` | | `24` | Max tracks per chat queue |
| `MAX_AUTH_USERS` | | `25` | Max authorized users per chat |
| `DEFAULT_LANG` | | `en` | Default language (only `en` is included) |
| `LEAVE_ON_DEMOTED` | | `false` | Leave a group when the bot is demoted |
| `SET_CMDS` | | `false` | Register the command list with BotFather on start |
| `START_IMAGES` | | | Start media URLs |
| `SUPPORT_CHAT` | | `https://t.me/Artistbots` | Support chat link |
| `SUPPORT_CHANNEL` | | `https://t.me/Artistbots` | Updates channel link |
| `COOKIES_LINK` | | | batbin link(s) to YouTube cookies for `yt-dlp` |
| `ARTIST_API_URL` / `ARTIST_API_KEY` | | | Artist streaming API |
| `ARTISTBOTS_API_URL` / `ARTISTBOTS_API_KEY` | | `https://api.artistbotsapi.bond` | Artistbots API (leave the key empty to disable) |
| `PORT` | | `8000` | Health-check HTTP port |

> [!NOTE]
> On startup every assistant account joins **@Elevenytschats** and **@Artistbots**. To change this, edit `autoJoinChannels` in `artistmusic/core/clients.go`.

<br/>

## 🎮 Commands

<details open>
<summary><b>🎵 Playback</b></summary>

| Command | What it does |
| :-- | :-- |
| `/play <query or link>` | Play audio in the voice chat |
| `/vplay <query or link>` | Play video |
| `/playforce` · `/vplayforce` | Play now, skipping the current track |
| `/pause` · `/resume` | Pause or resume |
| `/skip` | Next track |
| `/stop` · `/end` | Stop and clear the queue |
| `/seek <s>` · `/seekback <s>` | Jump forward or back |
| `/speed <0.5-2.0>` | Change playback speed |
| `/loop <1-10>` | Repeat the current track |
| `/shuffle` · `/replay` · `/jump <n>` | Shuffle, replay, or jump to a track |
| `/queue` · `/remove` · `/move` · `/clear` | Manage the queue |
| `/position` | Show current position |
| `/cplay` and other `c` commands | Same as above, for the linked channel |

</details>

<details>
<summary><b>📚 Playlists</b></summary>

`/createplaylist` · `/deleteplaylist` · `/addtoplaylist` · `/removefromplaylist` · `/playlistinfo` · `/myplaylists`

</details>

<details>
<summary><b>👥 Group settings</b></summary>

| Command | What it does |
| :-- | :-- |
| `/settings` | Interactive settings panel |
| `/auth` · `/unauth` · `/authusers` | Let non-admins control playback |
| `/language` | Set the chat language |
| `/playmode` · `/adminmode` · `/cleanmode` | Behaviour of play commands and message cleanup |
| `/autoplay` | Keep playing related tracks |
| `/channelplay` | Link a channel for channel play |
| `/vclogger` · `/vcstatus` | Voice chat join/leave logging |
| `/reload` | Refresh admin cache and reconnect the assistant |
| `/ping` · `/help` · `/repo` · `/privacy` · `/bug` | Utilities |

</details>

<details>
<summary><b>🛡️ Owner & sudo</b></summary>

| Command | What it does |
| :-- | :-- |
| `/addsudo` · `/delsudo` · `/sudoers` | Manage sudo users |
| `/broadcast` (`/gcast`, `/bcast`) | Broadcast to chats and users, owner only |
| `/blockuser` · `/blockchat` · `/blocked` | Blacklist users and chats (and their `un` versions) |
| `/maintenance` | Toggle maintenance mode |
| `/autoleave` | Assistants leave inactive chats |
| `/logger` | Toggle log-chat messages |
| `/stats` | Server and database stats |
| `/restart` | Restart the bot |
| `/eval` · `/sh` · `/logs` | Owner debugging tools |

</details>

<br/>

## 📁 Project structure

```text
ArtistMusic/
├── cmd/app/            entry point and dependency checks
├── config/             env loader and cookies handling
├── artistmusic/
│   ├── core/           rooms, chat state, assistant pool
│   ├── modules/        command handlers (play, queue, broadcast, settings ...)
│   ├── platforms/      stream resolvers (YouTube, Telegram, APIs, direct links)
│   ├── database/       MongoDB access and migrations
│   ├── locales/        translation files (en)
│   ├── artist/         Telegram client library (TDLib)
│   └── utils/          helpers
├── ntgcalls/           voice chat call bindings
├── ubot/               assistant userbot call handling
├── Dockerfile · docker-compose.yml
├── start.sh · install.sh · setup_service.sh
└── sample.env
```

<br/>

## 📜 License

Released under the **GNU GPL v3.0**. See [`LICENSE`](./LICENSE).

<div align="center">

<br/>

Made with ❤️ by [@Artistbots](https://t.me/Artistbots) · [@Elevenytschats](https://t.me/Elevenytschats)

</div>
