#!/usr/bin/env bash
# Jarvis install script for Linux.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PROJECT_DIR}/.venv"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/jarvis"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/jarvis"

echo "==> Project: $PROJECT_DIR"
echo "==> Config:  $CONFIG_DIR"
echo "==> Data:    $DATA_DIR"

# System deps hint (best-effort; user installs what's missing).
if command -v apt-get >/dev/null 2>&1; then
  echo "==> Suggested apt packages: portaudio19-dev libxcb-cursor0 python3-venv python3-dev"
fi

# Python venv.
python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"

# Config + data dirs.
mkdir -p "$CONFIG_DIR" "$DATA_DIR" "$DATA_DIR/logs"
if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
  cp "$PROJECT_DIR/config/default_config.yaml" "$CONFIG_DIR/config.yaml"
  echo "==> Wrote default config to $CONFIG_DIR/config.yaml"
fi

# Optional systemd user service (commented; uncomment to enable).
SERVICE_FILE="$HOME/.config/systemd/user/jarvis.service"
mkdir -p "$(dirname "$SERVICE_FILE")"
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Jarvis personal assistant
After=graphical-session.target

[Service]
Type=simple
ExecStart=${VENV_DIR}/bin/python ${PROJECT_DIR}/jarvis.py
Restart=on-failure
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
EOF
echo "==> systemd unit written to $SERVICE_FILE (run: systemctl --user enable --now jarvis)"

echo
echo "Done. Launch with:  $VENV_DIR/bin/python $PROJECT_DIR/jarvis.py"
