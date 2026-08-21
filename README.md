# CM3588 Homelab

A complete, reproducible self-hosted stack on a single FriendlyElec CM3588 board — 20+ services, fully containerized, documented to rebuild from scratch.

## Background

I wanted my photos and files on hardware I own, backed up where no unwanted eyes can reach them, instead of renting that trust from Google. I also wanted a playground: a standing excuse to learn Linux as a server, Docker networking, and everything in between. The usual fate of a setup like this is a pile of undocumented containers that nobody can rebuild after a disk dies, including future-you.

## Approach

I treated the homelab as a living blueprint. Every service is a sanitized Docker Compose file, every decision is written down, and the whole stack can be reproduced from a freshly flashed board. CasaOS sits on top for day-to-day management; twenty numbered guides carry the actual knowledge, from flashing the board and laying out storage to VPN routing and troubleshooting.

## Results

| Metric | Value |
|--------|-------|
| Self-hosted services | 20+ |
| Hardware | 1 ARM board — 8-core, 16 GB |
| Rebuild guides | 20 numbered docs |

## Learnings

The docs ended up mattering more than the containers. Writing each step down as I went, to the point a stranger could reproduce the stack, is why I trust this board with my actual photo library. It also keeps the whole thing a playground: I can try a new service, break it, and rebuild it without fear.

---

> **Running this box?** Start with **[HANDOFF.md](HANDOFF.md)** — current system
> state, verification commands, and the traps worth not rediscovering.
> Then **[TODO.md](TODO.md)** for what's open, and **[CHANGELOG.md](CHANGELOG.md)**
> for how it got here.

---

## What you get

- 📺 **Media server** — Jellyfin + Plex, fed by the *arr stack (Sonarr / Radarr / Prowlarr)
- 📥 **VPN-routed downloads** — qBittorrent + slskd, both forced through ProtonVPN WireGuard via Gluetun (kill-switched)
- 📸 **Photos** — Immich for phone backup, face/object search, multi-user
- 🎵 **Music** — Music Assistant + Last.fm scrobbling
- 🏠 **Home automation** — Home Assistant
- ☁️ **Personal cloud** — Seafile with MariaDB + Memcached
- 📝 **Blog** — Ghost on MySQL
- 🛡️ **DNS + ad blocking** — AdGuard Home as network-wide resolver
- 🌐 **Remote access** — Nginx Proxy Manager + Cloudflare Tunnel + Tailscale
- 🔐 **2FA codes** — 2FAuth, self-hosted
- 🤖 **Quality automation** — Recyclarr auto-syncs Sonarr/Radarr quality profiles from TRaSH Guides

---

## Quickstart

```bash
# 1. Flash Ubuntu (ARM64) to the CM5388 eMMC
# 2. SSH in, then:
curl -fsSL https://get.docker.com | sh
curl -fsSL https://get.casaos.io | bash

# 3. Mount your drives (see docs/02-storage.md)
# 4. Open CasaOS at http://<your-ip> and start deploying
```

Then follow the docs in order:

| # | Doc | What it covers |
|---|-----|----------------|
| 01 | [Hardware & OS](docs/01-hardware-and-os.md) | CM5388 specs, Ubuntu install, base packages |
| 02 | [Storage layout](docs/02-storage.md) | Drive partitioning, `fstab`, `/DATA` bind mount |
| 03 | [CasaOS](docs/03-casaos.md) | Install, app store, custom compose imports |
| 04 | [Networking](docs/04-networking.md) | NPM, Cloudflare Tunnel, Tailscale, AdGuard |
| 05 | [Media stack](docs/05-media-stack.md) | Jellyfin, Plex, Sonarr, Radarr, Prowlarr, Jellyseerr |
| 06 | [Downloads + VPN](docs/06-downloads-vpn.md) | qBittorrent + slskd routed through Gluetun |
| 07 | [Immich (photos)](docs/07-immich.md) | Full Immich stack with hardware transcoding |
| 08 | [Music](docs/08-music.md) | Music Assistant, kord-lastfm |
| 09 | [Home Assistant](docs/09-home-assistant.md) | HA in Docker (not HAOS) |
| 10 | [Seafile](docs/10-seafile.md) | Self-hosted file sync |
| 11 | [Ghost blog](docs/11-ghost.md) | Ghost + MySQL behind NPM |
| 12 | [Recyclarr](docs/12-recyclarr.md) | TRaSH Guides automation |
| 13 | [Backups & maintenance](docs/13-backups-and-maintenance.md) | What to back up, how often |
| 14 | [Troubleshooting](docs/14-troubleshooting.md) | Common gotchas |
| 15 | [n8n](docs/15-n8n.md) | Workflow automation (n8n + Postgres) |
| 16 | [Hardlinking migration](docs/16-hardlinking-migration-plan.md) | Planned mergerfs/hardlink fix |
| 17 | [Hermes Agent](docs/17-hermes.md) | Self-hosted AI agent (Gemini 3.5 Flash) on Telegram |
| 18 | [Lidarr](docs/18-lidarr.md) | Music *arr (artists/albums via Prowlarr + qBittorrent) |
| 19 | [Soularr](docs/19-soularr.md) | Lidarr ↔ Soulseek (slskd) bridge |
| 20 | [GDrive sync](docs/20-gdrive-sync.md) | Music library → Google Drive via rclone (server-side) |

See [`journal/`](journal/) for a running daily log of changes.

---

## Repo layout

```
.
├── docs/         # Step-by-step guides
├── compose/      # Sanitized docker-compose files for every service
├── configs/      # Example app configs (.example files only)
├── scripts/      # Helper scripts (initial setup, drive mounting)
├── journal/      # Daily logs (YYYY-MM-DD.md)
├── .gitignore
└── README.md
```

---

## Security note

**This repo is public.** Every file is sanitized:

- Secrets (API keys, passwords, WireGuard keys) are replaced with placeholders like `CHANGE_ME` or `YOUR_API_KEY`
- Personal domains are replaced with `yourdomain.com`
- The `.gitignore` blocks real configs (`recyclarr.yml`, `.env`, `wg0.conf`) from ever being committed

Always copy `*.example` files to their real name locally and fill in your own values. Never commit a file with a real secret.

> The docs use `192.168.50.178` as the homelab's LAN IP and `yourdomain.com` as the public domain. Replace both with your own values everywhere they appear.

---

## Hardware at a glance

| Component | Spec |
|-----------|------|
| Board | FriendlyElec CM5388 (Rockchip RK3588, 8-core ARM64, 16 GB RAM) |
| Primary storage | 1 TB NVMe (`/mnt/drive1`, also bind-mounted at `/DATA`) |
| Secondary NVMes | 3× additional NVMe drives (`/mnt/drive{2,3,4}`) |
| External | 2 TB USB SATA (`/mnt/toshiba`) for cold backup |
| OS | Ubuntu 22.04 LTS (ARM64) |
| Container runtime | Docker 24+, managed by CasaOS |
