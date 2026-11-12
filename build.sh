#!/bin/bash
# ==============================================================
# ArtistMusic - Build Script for VPS & Local Machines
# ==============================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo -e "\033[1;34m🔨 [ArtistMusic] Starting Build Process...\033[0m"

# 1. Check & Ensure Go is in PATH
if ! command -v go >/dev/null 2>&1; then
    if [[ -x "/usr/local/go/bin/go" ]]; then
        export PATH="/usr/local/go/bin:$PATH"
    else
        echo -e "\033[1;31m✗ Go is not installed or not in PATH!\033[0m"
        echo "Run: bash install.sh --go"
        exit 1
    fi
fi
echo -e "\033[1;32m✓ Go compiler found: $(go version)\033[0m"

# 2. Check GCC
if ! command -v gcc >/dev/null 2>&1; then
    echo -e "\033[1;31m✗ GCC (C compiler) not found! CGO is required for Voice Chat audio.\033[0m"
    echo "Install via: sudo apt install -y build-essential gcc zlib1g-dev"
    exit 1
fi
echo -e "\033[1;32m✓ GCC found: $(gcc --version | head -n1)\033[0m"

# 3. Check ntgcalls static library & headers
if [[ ! -f "./libntgcalls.a" || ! -f "./ntgcalls/ntgcalls.h" ]]; then
    echo -e "\033[1;33m⚠ libntgcalls.a or header missing! Installing...\033[0m"
    bash ./install.sh -n --quiet --skip-summary
fi
if [[ -f "./libntgcalls.a" && -f "./ntgcalls/ntgcalls.h" ]]; then
    echo -e "\033[1;32m✓ libntgcalls.a & header ready\033[0m"
else
    echo -e "\033[1;31m✗ Failed to prepare libntgcalls.a\033[0m"
    exit 1
fi

# 4. Check TDLib shared library
if [[ ! -f "./libtdjson.so.1.8.66" && ! -f "./libtdjson.so" ]]; then
    echo -e "\033[1;33m⚠ TDLib shared library missing! Installing...\033[0m"
    bash ./install.sh -t --quiet --skip-summary
fi
if [[ -f "./libtdjson.so.1.8.66" || -f "./libtdjson.so" ]]; then
    echo -e "\033[1;32m✓ TDLib (tdjson) ready\033[0m"
else
    echo -e "\033[1;31m✗ Failed to prepare TDLib\033[0m"
    exit 1
fi

# 5. Compile binary
echo -e "\033[1;36m🚀 Compiling Go binary (app)...\033[0m"
CGO_ENABLED=1 go build -v -trimpath -ldflags="-w -s" -o app ./cmd/app/
chmod +x app

echo -e "\033[1;32m==================================================\033[0m"
echo -e "\033[1;32m✓ ArtistMusic binary built successfully: $DIR/app\033[0m"
echo -e "\033[1;32m==================================================\033[0m"
echo -e "You can now run the bot using: \033[1;33mbash start.sh\033[0m"
