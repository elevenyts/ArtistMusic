#!/bin/bash
# ==============================================================
# ArtistMusic - Startup Script for VPS & Servers
# ==============================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo -e "\033[1;34m🎵 [ArtistMusic] Initializing Environment...\033[0m"

# 1. Check .env configuration
if [[ ! -f ".env" ]]; then
    if [[ -f "sample.env" ]]; then
        echo -e "\033[1;33m⚠ .env file not found! Created template from sample.env\033[0m"
        cp sample.env .env
        echo -e "\033[1;31m❗ Please edit .env with your credentials (API_ID, API_HASH, TOKEN, MONGO_DB_URI, STRING_SESSIONS) and re-run start.sh!\033[0m"
        exit 1
    else
        echo -e "\033[1;31m✗ Neither .env nor sample.env found!\033[0m"
        exit 1
    fi
fi

# 2. Check binary
if [[ ! -x "./app" ]]; then
    echo -e "\033[1;33m⚠ Compiled binary ./app not found, triggering build...\033[0m"
    bash "$DIR/build.sh"
fi

# 3. Ensure runtime tools (ffmpeg, yt-dlp) are in PATH
if ! command -v ffmpeg >/dev/null 2>&1; then
    echo -e "\033[1;31m✗ ffmpeg is missing! Installing via apt...\033[0m"
    if command -v apt >/dev/null 2>&1; then
        sudo apt update && sudo apt install -y ffmpeg
    fi
fi

if ! command -v yt-dlp >/dev/null 2>&1; then
    if [[ -x "$HOME/.local/bin/yt-dlp" ]]; then
        export PATH="$HOME/.local/bin:$PATH"
    fi
fi

# 4. Set Library Paths for TDLib & NTGCalls
export LD_LIBRARY_PATH="$DIR:/usr/local/lib:$LD_LIBRARY_PATH"

if [[ -f "$DIR/libtdjson.so.1.8.66" ]]; then
    export TDJSON_PATH="$DIR/libtdjson.so.1.8.66"
elif [[ -f "$DIR/libtdjson.so" ]]; then
    export TDJSON_PATH="$DIR/libtdjson.so"
elif [[ -f "/usr/local/lib/libtdjson.so" ]]; then
    export TDJSON_PATH="/usr/local/lib/libtdjson.so"
fi

# 5. Start Bot with Auto-Restart loop (unless --no-restart is passed)
if [[ "${1:-}" == "--no-restart" ]]; then
    shift
    echo -e "\033[1;32m🚀 Starting ArtistMusic in direct mode...\033[0m"
    exec ./app "$@"
else
    echo -e "\033[1;32m🚀 Starting ArtistMusic (Auto-Restart Guard ON)...\033[0m"
    echo -e "Tip: To run in background, use \033[1;33mscreen -dmS artistmusic bash start.sh\033[0m or systemd"
    while true; do
        ./app "$@"
        EXIT_CODE=$?
        echo -e "\033[1;33m[ArtistMusic] Process stopped with exit code $EXIT_CODE. Restarting in 3 seconds... (Press Ctrl+C to abort)\033[0m"
        sleep 3
    done
fi
