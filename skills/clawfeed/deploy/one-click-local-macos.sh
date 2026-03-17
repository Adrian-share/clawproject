#!/usr/bin/env bash
set -euo pipefail

# One-click local deployment on macOS (no remote server needed)
# - Starts ClawFeed on 127.0.0.1:8767
# - Configures Homebrew nginx reverse proxy on 127.0.0.1:8088
# - Verifies API path through nginx

APP_PORT="${APP_PORT:-8767}"
NGINX_PORT="${NGINX_PORT:-8088}"
APP_DIR="${APP_DIR:-$PWD}"

cd "$APP_DIR"

if ! command -v brew >/dev/null 2>&1; then
  echo "[error] Homebrew not found"
  exit 1
fi

if ! command -v nginx >/dev/null 2>&1; then
  echo "[1/6] Installing nginx via brew..."
  brew install nginx
fi

echo "[2/6] Installing node deps..."
npm install

echo "[3/6] Starting ClawFeed app..."
if ! lsof -iTCP:"${APP_PORT}" -sTCP:LISTEN -n -P >/dev/null 2>&1; then
  nohup npm start >/tmp/clawfeed.log 2>&1 &
  sleep 3
fi

if ! lsof -iTCP:"${APP_PORT}" -sTCP:LISTEN -n -P >/dev/null 2>&1; then
  echo "[error] ClawFeed not listening on ${APP_PORT}. Check /tmp/clawfeed.log"
  exit 1
fi

echo "[4/6] Writing nginx reverse proxy config..."
mkdir -p /usr/local/etc/nginx/servers
cat > /usr/local/etc/nginx/servers/clawfeed.local.conf <<EOF
server {
    listen ${NGINX_PORT};
    server_name clawfeed.mxyk.org;

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

echo "[5/6] Reloading nginx..."
/usr/local/opt/nginx/bin/nginx -t
if pgrep -f 'nginx: master process' >/dev/null 2>&1; then
  /usr/local/opt/nginx/bin/nginx -s reload
else
  /usr/local/opt/nginx/bin/nginx
fi

echo "[6/6] Verifying via nginx..."
curl -s "http://127.0.0.1:${NGINX_PORT}/api/digests?limit=1" | python3 -c 'import sys,json; j=json.load(sys.stdin); print("count",len(j)); c=(j[0].get("content","") if j else ""); print("has_reddit", "## Reddit Signals" in c); print("has_merged", "## Merged Ranked Feed" in c)'

echo
echo "Local deployment ready: http://127.0.0.1:${NGINX_PORT}"
echo "ClawFeed API direct: http://127.0.0.1:${APP_PORT}"
echo "App log: /tmp/clawfeed.log"
