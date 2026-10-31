#!/usr/bin/env bash
# bootstrap.sh - richtet einen Reserveknoten auf einem frischen Debian/Ubuntu-Server ein (als root). NICHT auf dem Mac ausfuehren.
# Voraussetzung: shop-standby.tar.gz, env.elements (Bot-Token) und wrangler-default.toml (Cloudflare-Anmeldung) liegen im selben Ordner;
# die beiden letzten kopiert Hermes per scp, sie stehen nie im Paket und nie im Chat.
# Der Knoten antwortet nur, wenn die feste Adresse ausfaellt (live.py ELEMENTS_ROLE=standby), und gibt sie zurueck, sobald der Hauptknoten wieder da ist.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
APP=/opt/elements
apt-get update -qq && apt-get install -y -qq python3 curl ca-certificates nodejs npm >/dev/null
if ! command -v cloudflared >/dev/null; then
  ARCH=$(dpkg --print-architecture)
  curl -fsSL -o /tmp/cloudflared.deb "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH}.deb"
  dpkg -i /tmp/cloudflared.deb >/dev/null
fi
id elements >/dev/null 2>&1 || useradd --system --create-home --home-dir "$APP" --shell /usr/sbin/nologin elements
mkdir -p "$APP" && tar xzf "$DIR/shop-standby.tar.gz" -C "$APP"
mkdir -p "$APP/miniapp/runtime" "$APP/front" "$APP/.config/.wrangler/config"
install -m 600 "$DIR/env.elements" "$APP/miniapp/runtime/.env.elements"
install -m 600 "$DIR/wrangler-default.toml" "$APP/.config/.wrangler/config/default.toml"
cp "$DIR/front/"* "$APP/front/"      # worker.js, wrangler.toml, front.json
chown -R elements:elements "$APP"
cat > /etc/systemd/system/elements-standby.service <<'U'
[Unit]
Description=Elements Labs Reserveknoten
After=network-online.target
Wants=network-online.target
[Service]
User=elements
WorkingDirectory=/opt/elements/miniapp
Environment=ELEMENTS_ROLE=standby ELEMENTS_NODE=standby ELEMENTS_SKIP_BUILD=1 HOME=/opt/elements XDG_CONFIG_HOME=/opt/elements/.config
ExecStart=/usr/bin/python3 -u live.py
Restart=always
RestartSec=20
[Install]
WantedBy=multi-user.target
U
systemctl daemon-reload && systemctl enable --now elements-standby
sleep 40; curl -fsS http://127.0.0.1:8766/health && echo " <- Reserveknoten laeuft"
