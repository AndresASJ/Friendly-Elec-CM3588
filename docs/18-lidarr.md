# 18 — Lidarr (Music)

[Lidarr](https://lidarr.audio) — the music *arr. Monitors artists/albums, grabs releases
via Prowlarr indexers + qBittorrent, and organizes them into the library. Installed
2026-06-03 (see [`journal/2026-06-03.md`](../journal/2026-06-03.md)).

## Stack

| Container | Image | Purpose |
|-----------|-------|---------|
| `lidarr` | `lscr.io/linuxserver/lidarr:latest` | Music collection manager + web UI (`:8686`) |

Mirrors the radarr/sonarr pattern: `PUID/PGID=1000`, `/mnt/drive1` mounted 1:1 so
hardlink imports work between qBit downloads (`/mnt/drive1/torrents`) and the library.
Compose: [`compose/lidarr.yml`](../compose/lidarr.yml).

## Install

```bash
mkdir -p /mnt/drive1/appdata/lidarr
casaos-cli app-management install -f compose/lidarr.yml
```

## Configuration (done via API)

- **Root folder**: `/mnt/drive1/Downloads/Soulseek` — the existing music library (also
  served by Plex). It was `root:root` and Lidarr runs as uid 1000 (`devmon`), so it was
  **`chown -R 1000:1000`'d** to give Lidarr ownership (slskd/root and Plex/read still
  work). Default quality profile **Lossless**, metadata **Standard**.
- **Download client**: qBittorrent at `192.168.50.178:8090` (mirrored from Radarr's
  config, category `lidarr`). `downloadclient/testall` → OK.
- **Indexers**: registered Lidarr as a Prowlarr **Application** (`fullSync`); Prowlarr
  pushes its music-capable indexers automatically (currently 1337x, DigitalCore,
  seedpool).

## Notes

- **Soulseek (slskd) is separate** and not wired here — the **Soularr** bridge
  (Lidarr → slskd) is deferred until the `gluetun-slskd` WireGuard VPN is fixed (dead
  ~8 weeks; slskd offline). Torrent music works today via the healthy `gluetun-qbit`.
- Hermes can request music by text — see [`docs/17-hermes.md`](17-hermes.md) ("Music").
