#!/bin/bash
# ==============================================================
# ArtistMusic - Systemd Service Installer for VPS
# ==============================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="artistmusic"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo -e "\033[1;34m⚙️  Configuring ${SERVICE_NAME} systemd service...\033[0m"

if [[ $EUID -ne 0 ]]; then
    echo -e "\033[1;31m✗ Please run as root (or with sudo):\033[0m sudo bash setup_service.sh"
    exit 1
fi

cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=ArtistMusic Telegram Voice Chat Engine
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$DIR
Environment=LD_LIBRARY_PATH=$DIR:/usr/local/lib
ExecStart=/bin/bash $DIR/start.sh --no-restart
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

echo -e "\033[1;32m==================================================\033[0m"
echo -e "\033[1;32m✓ Service ${SERVICE_NAME} created & enabled!\033[0m"
echo -e "\033[1;32m==================================================\033[0m"
echo -e "Commands to manage your bot:"
echo -e "  ▶ Start:   \033[1;33msystemctl start ${SERVICE_NAME}\033[0m"
echo -e "  ▶ Stop:    \033[1;33msystemctl stop ${SERVICE_NAME}\033[0m"
echo -e "  ▶ Status:  \033[1;33msystemctl status ${SERVICE_NAME}\033[0m"
echo -e "  ▶ Logs:    \033[1;33mjournalctl -u ${SERVICE_NAME} -f\033[0m"
