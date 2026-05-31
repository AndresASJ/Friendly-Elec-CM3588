#!/bin/sh
# VPN health check for qBit's gluetun tunnel -> Telegram alert on state change.
# Catches a silent VPN death (the kind that hid for ~3 weeks): tunnel "connected"
# but firewalled, listen_port 0, no forwarded port, 0 peers.
#
# Sends a Telegram message ONLY on transitions (up->down, down->up), not every run,
# using a state file. Credentials read from a root-only file (NOT in the repo):
#   /root/.config/vpn-alert/telegram.cred  with two lines:
#     TOKEN=123456:AA...        (the @ASJNOTI_BOT bot token)
#     CHAT_ID=123456789         (your Telegram chat id)
# Installed by Claude 2026-05-31. See docs/06-downloads-vpn.md.
set -eu

CRED="/root/.config/vpn-alert/telegram.cred"
STATE="/var/lib/vpn-healthcheck.state"   # holds last status: UP or DOWN
QBIT="http://127.0.0.1:8090"

[ -f "$CRED" ] || { echo "no cred file $CRED"; exit 0; }
# shellcheck disable=SC1090
TOKEN=$(grep '^TOKEN=' "$CRED" | cut -d= -f2-)
CHAT_ID=$(grep '^CHAT_ID=' "$CRED" | cut -d= -f2-)

# --- gather VPN/qBit health (qBit reachable only from inside the container ns) ---
conn=$(docker exec qbittorrent curl -s --max-time 12 "$QBIT/api/v2/transfer/info" 2>/dev/null \
        | sed -n 's/.*"connection_status":"\([^"]*\)".*/\1/p')
port=$(docker exec qbittorrent curl -s --max-time 12 "$QBIT/api/v2/app/preferences" 2>/dev/null \
        | sed -n 's/.*"listen_port":\([0-9]*\).*/\1/p')
fwd=$(docker exec gluetun-qbit cat /tmp/gluetun/forwarded_port 2>/dev/null || echo "")
ghealth=$(docker inspect --format '{{.State.Health.Status}}' gluetun-qbit 2>/dev/null || echo "unknown")

# --- decide UP vs DOWN ---
status="DOWN"
reason=""
if [ "$conn" = "connected" ] && [ -n "${port:-}" ] && [ "${port:-0}" -gt 0 ] 2>/dev/null; then
    status="UP"
else
    reason="conn=${conn:-?} listen_port=${port:-?} fwd_port=${fwd:-none} gluetun=${ghealth}"
fi

prev=$(cat "$STATE" 2>/dev/null || echo "UNKNOWN")
echo "$(date -Is) status=$status prev=$prev ${reason:+($reason)}"
echo "$status" > "$STATE"

send() {  # $1 = text
    [ -n "$TOKEN" ] && [ -n "$CHAT_ID" ] || { echo "no creds, not sending"; return 0; }
    curl -s --max-time 15 "https://api.telegram.org/bot${TOKEN}/sendMessage" \
        --data-urlencode "chat_id=${CHAT_ID}" \
        --data-urlencode "text=$1" >/dev/null 2>&1 || true
}

# --- alert only on transition ---
if [ "$status" = "DOWN" ] && [ "$prev" != "DOWN" ]; then
    send "🚨 qBit VPN DOWN — $reason. Downloads + seeding stopped (kill-switch). Check gluetun-qbit."
elif [ "$status" = "UP" ] && [ "$prev" = "DOWN" ]; then
    send "✅ qBit VPN recovered — connected, listen_port=$port, fwd_port=$fwd."
fi
