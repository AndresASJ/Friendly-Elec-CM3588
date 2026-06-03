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

## Request-only monitoring (important)

Soularr auto-grabs **every monitored album** on its list, so monitoring a full discography
floods Soulseek with hundreds of downloads. This stack is therefore run **request-only**:

- All artists have `monitorNewItems = none` and **no albums monitored** by default.
- A song/album is only ever pulled when explicitly requested (via Hermes or the Lidarr UI):
  monitor *just that album* → `AlbumSearch`. Nothing else.
- Hermes is instructed to add artists with `monitor:"none"` and monitor only the one requested
  album — see [`docs/17-hermes.md`](17-hermes.md). (Earlier `monitor:"all"` default caused a
  157-album flood; fixed 2026-06-03 — see that day's journal.)

## Torrent music → straight into the library (flat album folders)

The owner's library is a **flat pile of album folders** (Soulseek style), and Lidarr's default
`Artist/Album/` reorganization clashed with it. So torrented music is configured to land as album
folders directly in the library, matching Soulseek downloads:

- qBittorrent's `lidarr` category `save_path` = `/mnt/drive1/Downloads/Soulseek` (downloads land in
  the library and seed from there; partial files stay in `…/torrents/incomplete`).
- Lidarr **Completed Download Handling is OFF** (`config/downloadclient`
  `enableCompletedDownloadHandling=false`) — Lidarr still searches/grabs requested music but does
  **not** move or reorganize it afterward. (Soularr does its own import and is unaffected.)
- Trade-off: Lidarr no longer auto-tracks "have/missing" for torrent grabs and won't auto-remove
  finished torrents — acceptable here since the owner browses the library folder directly.

See the 2026-06-03 journal for the full rationale.

## Notes

- **Soulseek (slskd)** is also wired now via the **Soularr** bridge — see
  [`docs/19-soularr.md`](19-soularr.md). (The `gluetun-slskd` VPN was dead ~8 weeks and was
  fixed 2026-06-03; see that day's journal.) So Lidarr grabs music from **both** torrents
  (Prowlarr + qBittorrent) and Soulseek.
- Hermes can request music by text — see [`docs/17-hermes.md`](17-hermes.md) ("Music").
