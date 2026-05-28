# 06 — Downloads & VPN

All download clients on this stack are routed through **Gluetun** (a VPN client container running ProtonVPN WireGuard). If the VPN drops, the download container loses all network access — a hard kill-switch.

## How `network_mode: service:gluetun` works

```
┌─────────────────────────────────────────────────┐
│ Docker host                                     │
│                                                 │
│  ┌──────────────┐         ┌──────────────────┐  │
│  │   gluetun    │◄────────│   qbittorrent    │  │
│  │ (WireGuard)  │  shares │  (no network of  │  │
│  │              │ network │   its own)       │  │
│  └──────┬───────┘         └──────────────────┘  │
│         │                                       │
└─────────┼───────────────────────────────────────┘
          │ all qBit traffic exits through the VPN tunnel
          ▼
        ProtonVPN
```

Setting `network_mode: service:gluetun` makes qBittorrent reuse Gluetun's network namespace. qBit has no `ports:` of its own — Gluetun publishes them, since they're the same namespace.

If you `docker stop gluetun`, qBittorrent loses all networking instantly. That's the kill-switch.

## Get your ProtonVPN WireGuard config

1. Log into [account.proton.me/u/0/vpn/WireGuard](https://account.proton.me/u/0/vpn/WireGuard)
2. **Create a new WireGuard config**:
   - Name: e.g. `qbit-port-forward`
   - Country: pick one that supports P2P + port forwarding (NL, SE, CH are good)
   - **Enable NAT-PMP (Port Forwarding)**: ✅ for qBittorrent (must be ON for fast downloads)
   - **Enable Moderate NAT**: ✅
3. Download the `.conf` file
4. Copy to `/mnt/drive1/AppData/gluetun-qbit/wg0.conf` (qBit)
   and `/mnt/drive1/AppData/gluetun-slskd/wg0.conf` (slskd)

The `.conf` looks like:
```ini
[Interface]
PrivateKey = xxxxxxxxxxxxxxxxxxxx=
Address = 10.2.0.2/32
DNS = 10.2.0.1
[Peer]
PublicKey = yyyyyyyyyyyyyyyyyyyy=
AllowedIPs = 0.0.0.0/0
Endpoint = 1.2.3.4:51820
```

> **Never commit this file.** It's in `.gitignore`. An example skeleton is at [`configs/wg0.conf.example`](../configs/wg0.conf.example).

## qBittorrent + Gluetun

Full compose: [`compose/qbittorrent-gluetun.yml`](../compose/qbittorrent-gluetun.yml).

### Key bits

```yaml
gluetun:
  environment:
    VPN_SERVICE_PROVIDER: custom
    VPN_TYPE: wireguard
    VPN_PORT_FORWARDING: "on"
    VPN_PORT_FORWARDING_PROVIDER: protonvpn
    VPN_PORT_FORWARDING_UP_COMMAND: '/bin/sh -c "/gluetun/qbit-port-forward.sh up {{PORT}} {{VPN_INTERFACE}}"'
    VPN_PORT_FORWARDING_DOWN_COMMAND: '/bin/sh -c "/gluetun/qbit-port-forward.sh down 0 lo"'
    FIREWALL_INPUT_PORTS: "8090"
    FIREWALL_OUTBOUND_SUBNETS: "192.168.50.0/24"   # ← your LAN subnet
  volumes:
    - /mnt/drive1/AppData/gluetun-qbit:/gluetun

qbittorrent:
  network_mode: service:gluetun
  depends_on:
    gluetun:
      condition: service_healthy
```

### About the port-forwarding script

The `qbit-port-forward.sh` script lives at `/mnt/drive1/AppData/gluetun-qbit/qbit-port-forward.sh`. When Gluetun gets a forwarded port from ProtonVPN, it calls this script, which then hits qBit's API to update its listening port.

Example contents (sanitized — replace `QBIT_USER`/`QBIT_PASS` with your own):

```bash
#!/bin/sh
ACTION=$1
PORT=$2
IFACE=$3
QBIT_API="http://localhost:8090/api/v2"
QBIT_USER="admin"
QBIT_PASS="CHANGE_ME"

if [ "$ACTION" = "up" ]; then
  COOKIE=$(curl -s --cookie-jar - "$QBIT_API/auth/login" \
    --data "username=$QBIT_USER&password=$QBIT_PASS" \
    | grep SID | awk '{print $7}')
  curl -s --cookie "SID=$COOKIE" \
    --data "json={\"listen_port\": $PORT}" \
    "$QBIT_API/app/setPreferences"
fi
```

Make it executable: `chmod +x qbit-port-forward.sh`.

### qBittorrent first-boot

After the container starts, get the temporary admin password:

```bash
docker logs qbittorrent | grep -i password
```

Log in at `http://<homelab-ip>:8090`, then change the password immediately under **Tools → Options → Web UI**.

**Recommended settings:**
- Save path: `/mnt/drive1/torrents/incomplete/`
- Move to: `/mnt/drive1/torrents/complete/`
- Category: `tv-sonarr` → `/mnt/drive1/torrents/complete/tv-sonarr/`
- Category: `movies-radarr` → `/mnt/drive1/torrents/complete/movies-radarr/`
- Enable hardlinks where supported: ✅
- Disable PEX/DHT/LSD only on **private** tracker torrents (per-torrent setting)

## slskd + Gluetun

Soulseek client for music. Same Gluetun pattern, separate VPN instance so qBit's port-forward doesn't interfere.

Full compose: [`compose/slskd-gluetun.yml`](../compose/slskd-gluetun.yml).

### slskd config

After first boot, edit `/mnt/drive1/AppData/slskd/slskd.yml`:

```yaml
shares:
  directories:
    - /downloads   # share what you've downloaded back to the network

soulseek:
  username: YOUR_SOULSEEK_USER
  password: YOUR_SOULSEEK_PASSWORD
  listen_port: 50300
```

Reach the UI at `http://<homelab-ip>:5032`.

## Verifying the kill-switch

Quick sanity check that traffic actually goes through the VPN:

```bash
# Inside qBittorrent container — should show ProtonVPN's IP, not yours:
docker exec qbittorrent curl -s ifconfig.me

# Stop gluetun — qbit should lose all network:
docker stop gluetun-qbit
docker exec qbittorrent curl -s --max-time 5 ifconfig.me   # should timeout
docker start gluetun-qbit
```

If `docker exec qbittorrent curl ifconfig.me` returns your **real** IP, **stop using the stack immediately** and double-check the compose — `network_mode: service:gluetun` is the critical line.

---

## Next

→ [07 — Immich (photos)](07-immich.md)
