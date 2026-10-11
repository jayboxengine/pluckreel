#!/usr/bin/env bash
# One-time setup of PluckReel on a fresh Ubuntu 22.04/24.04 VPS (e.g. Hostinger KVM VPS).
#
#   curl -fsSL https://raw.githubusercontent.com/jayboxengine/pluckreel/main/deploy/setup.sh -o setup.sh
#   sudo bash setup.sh pluckreel.com
#
# Point the domain's A record at the VPS IP *before* running, so Caddy can get the HTTPS certificate.
# Safe to re-run. Later code updates: sudo bash /opt/pluckreel/deploy/update.sh
set -euo pipefail

DOMAIN="${1:?usage: sudo bash setup.sh <domain>}"
REPO="${REPO:-https://github.com/jayboxengine/pluckreel.git}"
APP_DIR=/opt/pluckreel
APP_USER=pluckreel

[ "$(id -u)" -eq 0 ] || { echo "Run as root (sudo)." >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive

echo "==> System packages"
apt-get update -y
apt-get install -y git curl ca-certificates gnupg python3 python3-venv python3-pip \
  debian-keyring debian-archive-keyring apt-transport-https ufw

echo "==> Node.js 22 (to build the frontend)"
if ! command -v node >/dev/null || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 20 ]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi

echo "==> Caddy (reverse proxy + automatic HTTPS)"
if ! command -v caddy >/dev/null; then
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key \
    | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt \
    > /etc/apt/sources.list.d/caddy-stable.list
  chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -y
  apt-get install -y caddy
fi

echo "==> App user and code"
id "$APP_USER" >/dev/null 2>&1 || \
  useradd --system --create-home --home-dir /var/lib/$APP_USER --shell /usr/sbin/nologin "$APP_USER"
if [ -d "$APP_DIR/.git" ]; then
  sudo -u "$APP_USER" -H git -C "$APP_DIR" pull --ff-only
else
  install -d -o "$APP_USER" -g "$APP_USER" "$APP_DIR"
  sudo -u "$APP_USER" -H git clone "$REPO" "$APP_DIR"
fi

echo "==> Build frontend"
sudo -u "$APP_USER" -H bash -c "cd $APP_DIR && npm ci --no-audit --no-fund && npm run build"

echo "==> Python environment"
sudo -u "$APP_USER" -H bash -c "cd $APP_DIR/server && python3 -m venv .venv && \
  .venv/bin/pip install --upgrade pip -q && .venv/bin/pip install -r requirements.txt -q"
if [ ! -f "$APP_DIR/server/.env" ]; then
  install -o "$APP_USER" -g "$APP_USER" -m 600 "$APP_DIR/deploy/env.example" "$APP_DIR/server/.env"
fi

if [ ! -f "$APP_DIR/server/blocklist.txt" ]; then
  cat > "$APP_DIR/server/blocklist.txt" <<'EOF'
# Links blocked after a copyright/abuse report. One per line: a video ID or part of the URL.
# Changes apply immediately, no restart needed.
EOF
  chown "$APP_USER:$APP_USER" "$APP_DIR/server/blocklist.txt"
fi

echo "==> Log retention (the Privacy Policy promises error logs are kept up to 14 days)"
install -d /etc/systemd/journald.conf.d
printf '[Journal]\nMaxRetentionSec=14day\n' > /etc/systemd/journald.conf.d/pluckreel-retention.conf
systemctl restart systemd-journald

echo "==> Services"
install -m 644 "$APP_DIR/deploy/pluckreel.service" /etc/systemd/system/pluckreel.service
install -m 644 "$APP_DIR/deploy/pluckreel-ytdlp-update.service" /etc/systemd/system/
install -m 644 "$APP_DIR/deploy/pluckreel-ytdlp-update.timer" /etc/systemd/system/
sed "s/{DOMAIN}/$DOMAIN/g" "$APP_DIR/deploy/Caddyfile" > /etc/caddy/Caddyfile
systemctl daemon-reload
systemctl enable --now pluckreel.service pluckreel-ytdlp-update.timer
systemctl restart pluckreel.service
systemctl reload caddy || systemctl restart caddy

echo "==> Firewall"
ufw allow OpenSSH >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null

echo "==> Checking the app answers locally"
for _ in $(seq 1 30); do
  curl -fsS -o /dev/null http://127.0.0.1:8000/ && { echo "OK: https://$DOMAIN should now be live."; exit 0; }
  sleep 1
done
echo "The app didn't respond. Check: journalctl -u pluckreel -n 50" >&2
exit 1
