#!/usr/bin/env bash
# Pull the latest code, rebuild, and restart.   sudo bash /opt/pluckreel/deploy/update.sh
set -euo pipefail
APP_DIR=/opt/pluckreel
APP_USER=pluckreel

sudo -u "$APP_USER" -H git -C "$APP_DIR" pull --ff-only
sudo -u "$APP_USER" -H bash -c "cd $APP_DIR && npm ci --no-audit --no-fund && npm run build"
sudo -u "$APP_USER" -H bash -c "cd $APP_DIR/server && .venv/bin/pip install -r requirements.txt -q"
install -m 644 "$APP_DIR/deploy/pluckreel.service" /etc/systemd/system/pluckreel.service
systemctl daemon-reload
systemctl restart pluckreel.service
echo "Updated and restarted."
