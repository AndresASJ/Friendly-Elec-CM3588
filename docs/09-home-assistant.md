# 09 — Home Assistant

Smart home automation hub. This runs **Home Assistant Container** (the bare Docker image), not HAOS or the Supervised install — so add-ons aren't available, but you get full Docker flexibility and can easily back the whole thing up.

## Compose

See [`compose/home-assistant.yml`](../compose/home-assistant.yml).

Key bits:

```yaml
home-assistant:
  image: ghcr.io/home-assistant/home-assistant:stable
  network_mode: host             # mDNS, broadcast discovery, etc. need host net
  privileged: true
  volumes:
    - /mnt/drive1/homeassistant/config:/config
    - /run/dbus:/run/dbus:ro     # for Bluetooth and dbus-based integrations
  restart: unless-stopped
```

`network_mode: host` is necessary for HomeKit, Apple AirPlay discovery, Shelly devices, Sonos, etc. — anything that uses multicast/broadcast.

## First boot

1. Bring up the container
2. Visit `http://<homelab-ip>:8123`
3. Create the admin user + set location/timezone

## Behind a reverse proxy

If you want `home.yourdomain.com` to work, edit `/mnt/drive1/homeassistant/config/configuration.yaml`:

```yaml
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 172.17.0.0/16     # Docker bridge
    - 192.168.50.0/24   # your LAN
```

Restart HA, then add a proxy host in NPM:
- Domain: `home.yourdomain.com`
- Forward to: `192.168.50.178:8123`
- Websockets: ✅

## HACS (optional)

Home Assistant Community Store gives access to community integrations.

```bash
docker exec -it homeassistant bash -c \
  "wget -O - https://get.hacs.xyz | bash -"
docker restart homeassistant
```

Then **Settings → Devices & services → Add integration → HACS** and follow the GitHub OAuth flow.

## Integrations worth adding for this setup

- **Music Assistant** — auto-discovered, controls playback to speakers
- **Plex / Jellyfin** — media library control
- **AdGuard Home** — see DNS stats in dashboards
- **System Monitor** — CPU/RAM/disk of the homelab itself
- **Mobile App** — for presence detection and notifications

## Backup

The entire HA state lives in `/mnt/drive1/homeassistant/config/`. Snapshot it nightly:

```bash
# In your backup script:
rsync -a --delete /mnt/drive1/homeassistant/config/ /mnt/toshiba/backups/homeassistant/
```

See [docs/13](13-backups-and-maintenance.md).

---

## Next

→ [10 — Seafile](10-seafile.md)
