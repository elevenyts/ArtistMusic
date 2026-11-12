<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,19,26&height=220&section=header&text=ArtistMusic&fontSize=60&fontColor=ffffff&animation=fadeIn&fontAlignY=38&desc=Next-Generation%20Telegram%20Voice%20Chat%20Music%20Engine&descAlignY=60&descAlign=50" width="100%"/>
</p>

<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=20&pause=1000&color=00E5FF&center=true&vCenter=true&width=620&lines=High-Performance+Go+Streaming+Engine;Ultra-Low+Latency+Voice+Chat+Audio;Multi-Assistant+Seamless+Load+Balancing;Custom+Lyrics%2C+Thumbnails+%26+Animations;Developed+%26+Maintained+by+ArtistMusic" alt="Typing SVG" />
</p>

<p align="center">
  <a href="https://github.com/elevenyts/ArtistMusic/stargazers">
    <img src="https://img.shields.io/badge/GitHub-Stars-FFD700?style=for-the-badge&logo=github&logoColor=white" alt="GitHub Stars">
  </a>
  <a href="https://github.com/elevenyts/ArtistMusic/fork">
    <img src="https://img.shields.io/badge/GitHub-Forks-00C853?style=for-the-badge&logo=github&logoColor=white" alt="GitHub Forks">
  </a>
  <a href="https://go.dev/">
    <img src="https://img.shields.io/badge/Go-1.22+-00ADD8?style=for-the-badge&logo=go&logoColor=white" alt="Go Version">
  </a>
  <a href="https://github.com/elevenyts/ArtistMusic/releases">
    <img src="https://img.shields.io/badge/Release-v1.0.0-FF6F00?style=for-the-badge&logo=semver&logoColor=white" alt="Latest Release">
  </a>
  <a href="https://github.com/elevenyts/ArtistMusic/blob/dev/LICENSE">
    <img src="https://img.shields.io/badge/License-GPL--3.0-blue?style=for-the-badge&logo=opensourceinitiative&logoColor=white" alt="License">
  </a>
  <a href="https://t.me/Artistbots">
    <img src="https://img.shields.io/badge/Telegram-Support-26A69A?style=for-the-badge&logo=telegram&logoColor=white" alt="Support Chat">
  </a>
</p>

---

## ✨ Features & Highlights

- ⚡ **Ultra-Low Latency Streaming:** Powered by Go and native `ntgcalls` CGO bindings, ensuring crystal-clear playback without audio stutters or drops.
- 🤖 **Multi-Assistant Architecture:** Distributes active voice calls across multiple userbot assistant accounts (Pyrogram, Telethon, or Gogram) with automatic load balancing.
- 🎵 **Multi-Platform Provider:** Seamless stream resolution for YouTube, Spotify metadata matching, Telegram audio files, live streams, and direct HTTP audio URLs.
- 🎛️ **Full Playback Controls:** Comprehensive command suite including seek (`/seek`), playback speed (`/speed`), loop (`/loop`), shuffle (`/shuffle`), and auto-play.
- 🔄 **Smart Auto-Fallback:** Automatically retries and falls back to alternate stream sources if an endpoint fails or drops.
- 🌐 **Multi-Language Engine:** Built-in localization support with seamless YAML translations (English, Hindi, Arabic, Turkish, and more).
- 🎨 **Visual Aesthetics:** Dynamic audio thumbnails, customizable start animations, rich Telegram inline buttons, and animated message effect IDs.
- 🛡️ **Admin & Security:** Granular sudo management, per-chat authorizations, smart anti-flood protection, and maintenance mode.

---

## 🚀 Quick Deploy

Deploy **ArtistMusic** in under 60 seconds on your favorite cloud provider:

<p align="center">
  <a href="https://heroku.com/deploy?template=https://github.com/elevenyts/ArtistMusic">
    <img src="https://www.herokucdn.com/deploy/button.svg" alt="Deploy to Heroku" height="38">
  </a>
  &nbsp;&nbsp;&nbsp;
  <a href="https://railway.com/new/template?template=https://github.com/elevenyts/ArtistMusic">
    <img src="https://railway.com/button.svg" alt="Deploy on Railway" height="38">
  </a>
  &nbsp;&nbsp;&nbsp;
  <a href="https://render.com/deploy?repo=https://github.com/elevenyts/ArtistMusic">
    <img src="https://render.com/images/deploy-to-render-button.svg" alt="Deploy to Render" height="38">
  </a>
  &nbsp;&nbsp;&nbsp;
  <a href="https://app.koyeb.com/deploy?type=git&repository=elevenyts/ArtistMusic&branch=dev&name=artistmusic&service_type=worker&env[API_ID]=&env[API_HASH]=&env[TOKEN]=&env[MONGO_DB_URI]=&env[STRING_SESSION]=&env[OWNER_ID]=">
    <img src="https://www.koyeb.com/static/images/deploy/button.svg" alt="Deploy to Koyeb" height="38">
  </a>
</p>

---

## 🛠️ Deployment Methods

<details>
  <summary><b>🖥️ [Click to Expand] VPS / Linux Server Installation Guide</b></summary>
  <br>

  ### 📋 Prerequisites
  Make sure your Linux VPS has basic dependencies installed:
  ```bash
  sudo apt-get update && sudo apt-get upgrade -y
  sudo apt-get install -y git curl ffmpeg build-essential
  ```

  ### 🚀 Step-by-Step Setup
  ```bash
  # 1. Clone the repository
  git clone https://github.com/elevenyts/ArtistMusic.git
  cd ArtistMusic

  # 2. Run automated dependency installer
  bash install.sh

  # 3. Setup configuration environment
  cp sample.env .env  # Edit your API_ID, TOKEN, etc.
  nano .env

  # 4. Tidy & Run
  go mod tidy
  go run ./cmd/app
  ```

  ### 🔄 Running 24/7 in Background
  **Method 1: Using Automated Runner Script**
  ```bash
  # Auto-builds, exports library paths, and auto-restarts on crash
  bash start.sh
  ```

  **Method 2: Using Automated Systemd Service**
  ```bash
  sudo bash setup_service.sh
  sudo systemctl start artistmusic
  sudo systemctl status artistmusic
  ```

  **Method 3: Using Tmux**
  ```bash
  tmux new -s artistmusic
  go run ./cmd/app
  # Press Ctrl+B then D to detach. Re-attach anytime with: tmux a -t artistmusic
  ```
</details>

<details>
  <summary><b>🐳 [Click to Expand] Docker & Docker Compose Deployment Guide</b></summary>
  <br>

  ### 🚀 Docker Compose Setup
  ```bash
  # 1. Clone repo
  git clone https://github.com/elevenyts/ArtistMusic.git
  cd ArtistMusic

  # 2. Prepare environment variables
  cp sample.env .env
  nano .env  # Edit your configuration values

  # 3. Build & start container
  docker compose up -d --build
  ```

  ### 📜 Useful Docker Commands
  ```bash
  # View live real-time logs
  docker compose logs -f artistmusic

  # Restart the bot
  docker compose restart artistmusic

  # Stop the container
  docker compose down

  # Update to latest code & rebuild
  git pull && docker compose up -d --build
  ```
</details>

---

## ⚙️ Configuration Variables

<details open>
  <summary><b>🔑 Environment Variables Reference Table</b></summary>
  <br>

  | Variable | Required | Default | Description |
  | :--- | :---: | :---: | :--- |
  | `API_ID` | **Yes** | — | Telegram API ID from [my.telegram.org](https://my.telegram.org) |
  | `API_HASH` | **Yes** | — | Telegram API Hash from [my.telegram.org](https://my.telegram.org) |
  | `TOKEN` | **Yes** | — | Telegram Bot Token from [@BotFather](https://t.me/BotFather) |
  | `MONGO_DB_URI` | **Yes** | — | MongoDB Connection String (`mongodb+srv://...`) |
  | `STRING_SESSIONS` | **Yes** | — | Assistant account session strings (separated by spaces or commas) |
  | `OWNER_ID` | **Yes** | — | Telegram User ID of the bot owner |
  | `SESSION_TYPE` | No | `pyrogram` | Session string library: `pyrogram`, `telethon`, or `gogram` |
  | `DB_NAME` | No | `ArtistMusic` | MongoDB database name |
  | `LOGGER_ID` | No | `0` | Telegram Chat ID for logs and error reports |
  | `DURATION_LIMIT`| No | `4200` | Max track duration in seconds (70 minutes) |
  | `QUEUE_LIMIT` | No | `24` | Max tracks allowed in queue per chat |
  | `DEFAULT_LANG` | No | `en` | Default language code (`en`, `hi`, `ar`, `tr`) |
  | `SUPPORT_CHAT` | No | `https://t.me/Artistbots` | Link to your Telegram support chat |
  | `SUPPORT_CHANNEL`| No | `https://t.me/Artistbots` | Link to your Telegram announcement channel |
  | `SPOTIFY_CLIENT_ID` | No | — | Spotify Client ID for track resolution |
  | `SPOTIFY_CLIENT_SECRET` | No | — | Spotify Client Secret for track resolution |
  | `COOKIES_LINK` | No | — | batbin URL to YouTube cookies file for `yt-dlp` |
</details>

---

## 🎮 Bot Commands Reference

<details>
  <summary><b>🎵 [Click to Expand] Playback & Stream Commands</b></summary>
  <br>

  | Command | Description |
  | :--- | :--- |
  | `/play <query/url>` | Streams requested song into group voice chat |
  | `/fplay <query/url>` | Force plays track, skipping the current playing track immediately |
  | `/pause` | Pauses active playback stream |
  | `/resume` | Resumes paused audio stream |
  | `/skip` | Skips current track to the next item in queue |
  | `/stop` | Stops playback and clears the entire playlist queue |
  | `/queue` | Displays the current playlist and upcoming tracks |
  | `/seek <seconds>` | Seeks playback to a specific timestamp |
  | `/speed <0.5-2.0>` | Changes audio playback speed dynamically |
  | `/loop <1-10>` | Loops the current track specified number of times |
  | `/shuffle` | Shuffles queued songs randomly |
  | `/replay` | Replays the current playing song from beginning |
</details>

<details>
  <summary><b>👥 [Click to Expand] Group Admin & Settings Commands</b></summary>
  <br>

  | Command | Description |
  | :--- | :--- |
  | `/auth <user>` | Authorizes non-admin user to use bot playback commands |
  | `/unauth <user>` | Revokes bot access authorization from a user |
  | `/authusers` | Lists all authorized users in the current group |
  | `/language` | Changes bot language for current chat (Multi-language) |
  | `/settings` | Opens the interactive visual settings control panel |
  | `/reload` | Refreshes admin cache and reconnects the assistant account |
  | `/cplay <channel>` | Streams audio directly linked to a Telegram channel |
</details>

<details>
  <summary><b>🛡️ [Click to Expand] Bot Owner & Sudo Commands</b></summary>
  <br>

  | Command | Description |
  | :--- | :--- |
  | `/addsudo <user>` | Adds a new user to sudoers list |
  | `/delsudo <user>` | Removes a user from sudoers list |
  | `/sudolist` | Shows list of all current bot sudoers |
  | `/stats` | Shows server performance, memory, and database metrics |
  | `/broadcast <msg>` | Broadcasts announcements to all served chats and users |
  | `/maintenance` | Toggles global bot maintenance mode |
  | `/eval <code>` | Executes internal runtime evaluation (Owner only) |
</details>

---

## 📁 Project Architecture

```
ArtistMusic/
├── cmd/app/              # Application entry point & dependencies verification
├── config/               # Flexible configuration loader & cookies system
├── artistmusic/
│   ├── core/             # State machine, room controllers, & assistant pooling
│   ├── database/         # MongoDB schemas, caching layers, & automated migrations
│   ├── locales/          # YAML-based multi-language translation packs
│   ├── artist/             # High-performance Telegram MTProto client engine
│   ├── modules/          # Command modules (play, skip, pause, settings, etc.)
│   ├── platforms/        # Media stream resolvers (YouTube, Spotify, Telegram)
│   └── utils/            # Admin checks, parsing, formatters, and helpers
├── Dockerfile            # Multi-stage production container build
├── docker-compose.yml    # Docker Compose orchestration recipe
├── install.sh            # Automated server setup and dependency script
└── sample.env            # Template environment variables file
```

---

## 📜 License

Distributed under the **GNU General Public License v3.0**. See the [`LICENSE`](./LICENSE) file for full details.

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,19,26&height=100&section=footer" width="100%"/>
</p>

<p align="center">
  <b>Developed & Maintained with ❤️ by <a href="https://github.com/elevenyts">ArtistMusic</a></b>
</p>
