#!/usr/bin/env bash
set -euo pipefail

# One-click online deployment for ClawFeed via Nginx reverse proxy
# Target: clawfeed.mxyk.org -> 127.0.0.1:8767
#
# Usage:
#   bash deploy/one-click-online.sh
#
# Optional env vars:
#   DOMAIN=clawfeed.mxyk.org
#   APP_PORT=8767
#   APP_DIR=/opt/clawfeed
#
# Notes:
# - Run on the target Linux server (Ubuntu/Debian).
# - Requires sudo privileges.

DOMAIN="${DOMAIN:-clawfeed.mxyk.org}"
APP_PORT="${APP_PORT:-8767}"
APP_DIR="${APP_DIR:-$PWD}"

if ! command -v sudo >/dev/null 2>&1; then
  echo "[error] sudo is required"
  exit 1
fi

echo "[1/7] Installing runtime dependencies..."
sudo apt update -y
sudo apt install -y nginx certbot python3-certbot-nginx curl

echo "[2/7] Ensuring Node dependencies..."
cd "$APP_DIR"
if [ ! -f package.json ]; then
  echo "[error] package.json not found in APP_DIR=$APP_DIR"
  exit 1
fi
npm install

echo "[3/7] Ensuring ClawFeed is running on 127.0.0.1:${APP_PORT} ..."
if lsof -iTCP:"${APP_PORT}" -sTCP:LISTEN -n -P >/dev/null 2>&1; then
  echo "[ok] Port ${APP_PORT} already listening"
else
  # Start app in background with nohup for simple MVP deployment
  nohup npm start >/tmp/clawfeed.log 2>&1 &
  sleep 3
fi

if ! lsof -iTCP:"${APP_PORT}" -sTCP:LISTEN -n -P >/dev/null 2>&1; then
  echo "[error] ClawFeed is not listening on ${APP_PORT}. Check /tmp/clawfeed.log"
  exit 1
fi

echo "[4/7] Writing nginx site config..."
sudo tee "/etc/nginx/sites-available/${DOMAIN}.conf" >/dev/null <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo ln -sf "/etc/nginx/sites-available/${DOMAIN}.conf" "/etc/nginx/sites-enabled/${DOMAIN}.conf"

# Disable default site to avoid conflicts
if [ -L /etc/nginx/sites-enabled/default ]; then
  sudo rm -f /etc/nginx/sites-enabled/default
fi

echo "[5/7] Testing and reloading nginx..."
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

echo "[6/7] Issuing HTTPS certificate (certbot)..."
# --redirect: force HTTPS
# --non-interactive and --register-unsafely-without-email for quick bootstrap
# Replace with --email <your-email> in production.
sudo certbot --nginx -d "${DOMAIN}" --redirect --non-interactive --agree-tos --register-unsafely-without-email || {
  echo "[warn] certbot failed. Usually DNS not ready yet. HTTP may still work: http://${DOMAIN}"
}

echo "[7/7] Final verification..."
set +e
curl -I "http://${DOMAIN}" | head -n 1
curl -I "https://${DOMAIN}" | head -n 1
set -e

echo ""
echo "Done."
echo "- App log: /tmp/clawfeed.log"
echo "- Nginx conf: /etc/nginx/sites-available/${DOMAIN}.conf"
echo "- URL: https://${DOMAIN}"
