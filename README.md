<div align="center">

<img src="https://artistbox.bond/f/odklxlnu.svg" width="100%" height="500">

<br>
<br><br>

[![Stars](https://img.shields.io/github/stars/elevenyts/ArtistMusic?style=for-the-badge&logo=starship&logoColor=white&color=A960FF&labelColor=0D1117)](https://github.com/elevenyts/ArtistMusic)
[![Forks](https://img.shields.io/github/forks/elevenyts/ArtistMusic?style=for-the-badge&logo=git&logoColor=white&color=7C3AED&labelColor=0D1117)](https://github.com/elevenyts/ArtistMusic)
[![Issues](https://img.shields.io/github/issues/elevenyts/ArtistMusic?style=for-the-badge&logo=github&logoColor=white&color=FF6B6B&labelColor=0D1117)](https://github.com/elevenyts/ArtistMusic/issues)
[![License](https://img.shields.io/badge/License-MIT-A960FF?style=for-the-badge&logo=opensourceinitiative&logoColor=white&labelColor=0D1117)](LICENSE)

<br>

[![Telegram Channel](https://img.shields.io/badge/📢_Channel-Artistbots-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white&labelColor=0D1117)](https://t.me/Artistbots)
[![Support Group](https://img.shields.io/badge/💬_Support-ArtistMusic-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white&labelColor=0D1117)](https://t.me/Elevenytschats)

</div>

<br>

<div align="center">

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                   ✦  ARTISTMUSIC MUSIC BOT  ✦
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

</div>

## 📖 Table of Contents

- [Overview](#-overview)
- [Feature Showcase](#-feature-showcase)
- [Requirements](#-requirements)
- [Environment Variables](#-environment-variables)
- [Deploy](#-deploy)
- [Commands](#-commands)
- [Group Manager, Tag & Sticker Tools](#-group-manager-tag--sticker-tools)
- [Security](#-security)
- [Support](#-support)
- [Credits](#-credits)

<br>

## 〔 ✦ 〕 Overview

> **ArtistMusic** is a next-generation Telegram Voice Chat Music Bot engineered for performance, stability, and scale.
> Built on **Pyrogram** · **PyTgCalls** · **MongoDB** — delivering crystal-clear audio with powerful admin tooling, a full group-manager suite, member tagging, sticker-pack tools and multi-language support across global communities.

<br>

## 〔 ✦ 〕 Feature Showcase

<table>
<tr>
<td width="50%">

### 🎵 Music Streaming
```
✦ High Quality Audio Streaming
✦ YouTube Search & Play
✦ Direct URL Playback
✦ Voice Chat Streaming
✦ Live Stream Support
✦ Playlist Management
✦ Auto Queue System
✦ Continuous Playback
✦ Fast Audio Processing
```

</td>
<td width="50%">

### 🎛 Admin Controls
```
✦ Pause / Resume Stream
✦ Skip Current Track
✦ Force Play (Skip Queue)
✦ Stop Playback
✦ Mute / Unmute Assistant
✦ Volume Control
✦ Queue Cleanup
✦ Seek Forward / Backward
  (seek message auto-deletes)
✦ Loop Modes
```

</td>
</tr>
<tr>
<td width="50%">

### 👥 User Management
```
✦ Authorized Users System
✦ Sudo Users Panel
✦ Global Ban System
✦ User Statistics
✦ Blacklist Chat / User
✦ Owner Controls
✦ Admin-Only Play Mode
✦ Force Admin Mode
```

</td>
<td width="50%">

### 🤖 Bot Management
```
✦ Restart Command
✦ Broadcast System
✦ Maintenance Mode
✦ Live Logs Monitor
✦ Error Reporting
✦ Auto Restart Support
✦ MongoDB Integration
✦ Multi-Language Support
```

</td>
</tr>
<tr>
<td width="50%">

### 🛠 Group Manager
```
✦ Ban / Mute / Kick (+ timed)
✦ Promote / Demote / Temp Admin
✦ Pin / Unpin / Purge / Delete
✦ Mass Actions (owner only)
✦ Zombie (Deleted Acc) Cleaner
✦ Welcome Card for New Members
✦ VC Join / Leave Alerts (/vclog)
✦ User Info Lookup
✦ Group Photo / Title / Description
```

</td>
<td width="50%">

### 📣 Tag & 🎴 Stickers
```
✦ /tagall — 6 hidden emoji mentions
  per message, FloodWait safe
✦ Fun Tags (GM / GN / Hi / Quotes)
✦ /kang — copy a whole sticker pack
✦ /sticker — pack from one sticker
✦ Packs named "<You> by Artistbots"
✦ Same pack or new pack prompt
```

</td>
</tr>
</table>

<br>

## 〔 ✦ 〕 Requirements

| Component | Minimum Version / Note |
|:---|:---|
| Python | 3.10 or higher |
| FFmpeg | Latest stable release |
| MongoDB | Local instance or Atlas cluster |
| RAM | 512 MB minimum (1 GB+ recommended) |
| Telegram Account | For the assistant (string session) |

<br>

## 〔 ✦ 〕 Environment Variables

<div align="center">

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         Copy  Artist.env  to  .env  and fill these values
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

</div>

| Variable | Required | Description |
|:---|:---:|:---|
| `API_ID` | ✅ | Telegram API ID — [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | ✅ | Telegram API Hash — [my.telegram.org](https://my.telegram.org) |
| `BOT_TOKEN` | ✅ | Bot Token — [@BotFather](https://t.me/BotFather) |
| `STRING_SESSION` | ✅ | Pyrogram String Session for assistant |
| `MONGO_DB_URI` | ✅ | MongoDB connection string |
| `LOGGER_ID` | ✅ | Telegram group ID for logs |
| `OWNER_ID` | ✅ | Your Telegram user ID |
| `ARTISTBOTS_API_URL` | ⚙️ | ArtistBots API endpoint — `https://api.artistbotsapi.bond` (default) |
| `ARTISTBOTS_KEY` | ⚙️ | API key — log in at [artistbotsapi.bond](https://artistbotsapi.bond) to get your key |
| `SUPPORT_CHAT` | 🔵 | Support group link (optional) |
| `SUPPORT_CHANNEL` | 🔵 | Updates channel link (optional) |
| `START_IMG` | 🔵 | Start message image URL (optional) |
| `PING_IMG` | 🔵 | Ping message image URL (optional) |
| `STRING_SESSION2` | 🔵 | Second assistant session (optional) |
| `STRING_SESSION3` | 🔵 | Third assistant session (optional) |

> ✅ Required · ⚙️ Recommended · 🔵 Optional

<br>

## 〔 ✦ 〕 Deploy

<div align="center">

### ☁️ One-Click Deploy

[![Deploy on Render](https://img.shields.io/badge/Deploy_on-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white&labelColor=0D1117)](https://render.com)
[![Deploy on Railway](https://img.shields.io/badge/Deploy_on-Railway-7C3AED?style=for-the-badge&logo=railway&logoColor=white&labelColor=0D1117)](https://railway.app)

</div>

<br>

<details>
<summary><b>🖥 Render — Step by Step</b></summary>

<br>

**1.** Fork this repository

**2.** Go to [render.com](https://render.com) → **New Web Service**

**3.** Connect your GitHub and select this repo

**4.** Set build & start commands:

```bash
# Build Command
pip install -U -r requirements.txt

# Start Command
bash start
```

**5.** Add all environment variables from the table above

**6.** Hit **Deploy** 🚀

</details>

<details>
<summary><b>🚂 Railway — Step by Step</b></summary>

<br>

**1.** Fork this repository

**2.** Create a new project at [railway.app](https://railway.app)

**3.** Connect your GitHub repo

**4.** Add environment variables

**5.** Deploy 🚀

</details>

<details>
<summary><b>🖥 VPS / Self-Host</b></summary>

<br>

```bash
# Update system
apt update && apt upgrade -y

# Install dependencies
apt install python3 python3-pip ffmpeg git -y

# Clone repo
git clone https://github.com/elevenyts/ArtistMusic
cd ArtistMusic

# Install requirements
pip3 install -U -r requirements.txt

# Configure variables
cp Artist.env .env
nano .env

# Run the bot
bash start
# or
python -m ArtistMusic
```

</details>

<details>
<summary><b>🐳 Docker</b></summary>

<br>

```bash
# Build the image
docker build -t artistmusic .

# Run the container (pass your .env file)
docker run -d --env-file .env --name artistmusic artistmusic
```

</details>

<br>

## 〔 ✦ 〕 Commands

<table>
<tr>
<td width="33%">

**🎵 Music**
```
/play    — Play audio
/vplay   — Play video
/cplay   — Channel play
/pause   — Pause stream
/resume  — Resume stream
/skip    — Skip track
/end     — End stream
/queue   — View queue
/loop    — Loop mode
/shuffle — Shuffle queue
```

</td>
<td width="33%">

**🛡 Admin**
```
/reload   — Refresh admins
/auth     — Authorize user
/unauth   — Remove auth
/authlist — View auth list
/seek     — Seek stream
/seekback — Seek backward
/mute     — Mute assistant
/unmute   — Unmute assistant
/volume   — Set volume
/stop     — Stop playback
```

</td>
<td width="33%">

**👑 Sudo / Owner**
```
/addsudo     — Add sudo user
/delsudo     — Remove sudo
/sudolist    — List sudos
/broadcast   — Send broadcast
/gban        — Global ban
/ungban      — Global unban
/maintenance — Toggle mode
/stats       — Bot statistics
/restart     — Restart bot
/logs        — View logs
```

</td>
</tr>
</table>

<br>

## 〔 ✦ 〕 Group Manager, Tag & Sticker Tools

<table>
<tr>
<td width="50%">

**🛠 Group Manager** *(admins)*
```
/ban /unban /dban /sban
/tban  <time>  — timed ban
/mute /unmute
/tmute <time>  — timed mute
/kick /kickme
/promote /fullpromote /demote
/tempadmin <time>
/pin /unpin
/purge /spurge /del
/deleteall
/zombies — clean deleted accounts
/info /userinfo /whois
/admins /staff
/setphoto /removephoto
/settitle /setdescription
/welcome [on/off]
/vclog [on/off] — VC join/leave alerts
/userbotjoin /userbotleave
```
> Time format: `30s` · `10m` · `2h` · `3d`

**💣 Mass Actions** *(group owner only)*
```
/kickall   /banall   /unbanall
/muteall   /unmuteall /unpinall
```

</td>
<td width="50%">

**📣 Tag Everyone** *(admins)*
```
/tagall  /all  @all  /utag  /mention [text]
```
One command, five aliases. Every message carries **6 emojis** — each emoji is a hidden mention of one member, tap it to open that profile. FloodWait is handled automatically: the bot waits, **resends the same batch** (nobody is skipped) and slows down afterwards.

```
/gmtag  /gntag  /hitag
/lifetag  /shayari
```
Fun tags — one member per message with a random line.

```
/tagstop  /tagoff  /ustop
/gmstop /gnstop /histop
/lifestop /shayarioff
```
Stop a running tag session.

**🎴 Stickers** *(everyone)*
```
/kang    — reply to a sticker
/sticker — reply to a sticker
```
- `/kang` duplicates the **whole pack** of that sticker into a new pack owned by you.
- `/sticker` makes a pack with **only that one sticker**. Run it again and the bot asks: **add to the same pack** or **create a new one**.
- Pack title: **`<Your name> by Artistbots`** (`… 2`, `… 3` for later packs).
- A pack holds one type only (static / animated / video) and up to 120 stickers.

</td>
</tr>
</table>

> ℹ️ For `@all` to work the bot must be an **admin** in the group (or have privacy mode turned off in @BotFather), otherwise Telegram does not deliver plain-text messages to it.
> ℹ️ **VC alerts** (`/vclog on|off`, default **on**): while the assistant is in the voice chat, the bot posts who **joined**, **left** or was **removed**. Alerts are queued per chat, de-duplicated and FloodWait-safe.
> ℹ️ Sticker packs can only be created for users the bot has seen (any user who has messaged in the group, or started the bot).

<br>

## 〔 ✦ 〕 Security

<div align="center">

```
╔══════════════════════════════════════════════════════╗
║  ✦  KEEP THESE PRIVATE — NEVER SHARE PUBLICLY  ✦    ║
╠══════════════════════════════════════════════════════╣
║  ✗  BOT_TOKEN          ✗  STRING_SESSION             ║
║  ✗  MONGO_DB_URI       ✗  API_HASH                   ║
║  ✓  Use a separate Telegram account for assistant    ║
║  ✓  Keep the logger group private                    ║
║  ✓  Bot must be admin in group & logger group        ║
╚══════════════════════════════════════════════════════╝
```

</div>

<br>

## 〔 ✦ 〕 Support

<br>

| Platform | Link |
|:---:|:---:|
| 📢 Updates Channel | [Artistbots](https://t.me/Artistbots) |
| 💬 Support Group | [Elevenytschats](https://t.me/elevenytschats) |

</div>

<br>

## 〔 ✦ 〕 Credits

<div align="center">

Built on the shoulders of giants:

`Pyrogram` · `PyTgCalls` · `MongoDB` · `Telegram Bot API` · `ArtistBots`

<br>

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         Made with ❤️  by  Artist  ·  Powered by ArtistBots
                   © 2026 ArtistMusic · MIT License
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

</div>
