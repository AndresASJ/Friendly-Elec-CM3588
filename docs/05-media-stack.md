# 05 — Media Stack

The classic "*arr stack" — automatic media library management.

## What's in it

| Service | Purpose | Port |
|---------|---------|------|
| **Prowlarr** | Indexer aggregator — manages all torrent/Usenet trackers in one place | 9696 |
| **Sonarr** | TV show manager (grabs new episodes, organizes library) | 8989 |
| **Radarr** | Movie manager | 7878 |
| **Jellyseerr** | Request UI for users (fork of Overseerr with Jellyfin support) | 5055 |
| **FlareSolverr** | Headless browser that bypasses Cloudflare on indexer sites | 8191 |
| **Jellyfin** | Primary media server | 8096 |
| **Plex** | Secondary media server (kept for PlexAmp users) | host network |
| **Unpackerr** | Auto-extracts RAR archives from completed downloads | — |
| **Recyclarr** | Syncs quality profiles from TRaSH Guides (see [docs/12](12-recyclarr.md)) | — |

## How data flows

```
                 ┌─────────────┐
You ask for ──►  │ Jellyseerr  │  (or you add directly in Sonarr/Radarr)
something        └──────┬──────┘
                        │
                        ▼
            ┌────────────────────────┐
            │  Sonarr (TV)           │
            │  Radarr (Movies)       │
            └───────────┬────────────┘
                        │ searches via
                        ▼
                  ┌─────────────┐    bypasses CF on
                  │  Prowlarr   │◄── indexers via ── FlareSolverr
                  └──────┬──────┘
                         │ finds release
                         ▼
                ┌──────────────────┐
                │  qBittorrent     │  (behind Gluetun VPN — see docs/06)
                └────────┬─────────┘
                         │
                         ▼
            /mnt/drive1/torrents/complete
                         │
                         ▼ Sonarr/Radarr import as hardlinks
                         │
            /mnt/drive1/Movies, /mnt/drive3/TV, ...
                         │
                         ▼
                ┌──────────────────┐
                │ Jellyfin / Plex  │  serves to your devices
                └──────────────────┘
```

## Setup order

You **must** install in this order or you'll be reconfiguring constantly.

### 1. qBittorrent (with Gluetun)

See [docs/06-downloads-vpn.md](06-downloads-vpn.md).

Get this working first — verify torrents complete to `/mnt/drive1/torrents/complete`.

### 2. Prowlarr

Install from CasaOS or use [`compose/prowlarr.yml`](../compose/prowlarr.yml).

In Prowlarr UI:
- Add indexers (1337x, Nyaa, RARBG mirrors, private trackers, etc.)
- Test each one — if a tracker fails with a Cloudflare challenge, add **FlareSolverr** as a proxy

### 3. FlareSolverr

See [`compose/flaresolverr.yml`](../compose/flaresolverr.yml).

In Prowlarr → **Indexers → Add Proxy**:

```
Name: flaresolverr
Tags: flaresolverr   ← apply this tag to any indexer that needs CF bypass
Host: http://192.168.50.178:8191/   ← homelab LAN IP
```

### 4. Sonarr & Radarr

[`compose/sonarr.yml`](../compose/sonarr.yml) and [`compose/radarr.yml`](../compose/radarr.yml).

Both mount `/mnt/drive1`, `/mnt/drive3`, `/mnt/drive4` at the same paths inside the container — critical for hardlinks to work.

**In Sonarr/Radarr:**

- **Settings → Download Clients → Add qBittorrent**
  - Host: `192.168.50.178` (LAN IP, not container name)
  - Port: `8090`
  - Username/Password: from your qBit setup
- **Settings → Media Management**:
  - Use Hardlinks instead of Copy: ✅
  - Import Extra Files: `srt,nfo`
- **Connect to Prowlarr** (Settings → Apps in Prowlarr):
  - Sonarr URL: `http://192.168.50.178:8989`
  - Radarr URL: `http://192.168.50.178:7878`
  - API keys: find in each app's Settings → General
  - Test → Sync App Indexers — Prowlarr will push every indexer config into Sonarr/Radarr

### 5. Recyclarr

See [docs/12-recyclarr.md](12-recyclarr.md). This is what makes Sonarr/Radarr actually grab good releases without you babysitting custom formats.

### 6. Jellyseerr

[`compose/jellyseerr.yml`](../compose/jellyseerr.yml).

On first launch, point it at Jellyfin (after Jellyfin is up). Connect Sonarr + Radarr as request handlers.

### 7. Jellyfin

[`compose/jellyfin.yml`](../compose/jellyfin.yml).

Add libraries:
- **Movies** → `/Media/Movies`
- **TV Shows** → `/Media/TV`
- **Music** → `/Media/Music` (or skip if using Plex/Music Assistant for music)

The container has `/DATA/Media` mapped to `/Media`. Inside `/DATA/Media` create the subfolders and point Radarr/Sonarr's "root folder" there.

**Hardware transcoding (RK3588):**
- Settings → Playback → Hardware acceleration: **Video4Linux2 (V4L2)**
- Enable: HEVC, H.264, AV1
- The compose file mounts `/dev/dri` and `/dev/mpp_service` for this

### 8. Plex (optional)

Kept around for **PlexAmp** users. [`compose/plex.yml`](../compose/plex.yml).

Runs in host networking mode (Plex's discovery features need it).

### 9. Unpackerr

[`compose/unpackerr.yml`](../compose/unpackerr.yml).

Watches `/mnt/drive1/torrents/complete` for RAR-archived releases (some scene groups still do this). Auto-extracts them so Sonarr/Radarr can import.

Config goes in `/mnt/drive1/AppData/unpackerr/unpackerr.conf` — Unpackerr's defaults are fine if you only need Sonarr + Radarr integration.

---

## Library folder convention

Inside `/mnt/drive1/Movies/`:
```
Movies/
├── Inception (2010)/
│   ├── Inception (2010).mkv
│   └── Inception (2010).en.srt
└── ...
```

Inside `/mnt/drive3/TV/`:
```
TV/
├── Severance/
│   ├── Season 01/
│   │   ├── Severance - S01E01 - Good News About Hell.mkv
│   │   └── ...
│   └── Season 02/
└── ...
```

Sonarr and Radarr handle the renaming automatically when their **Media Management** settings are configured. Use TRaSH Guides' recommended naming format.

---

## Next

→ [06 — Downloads + VPN](06-downloads-vpn.md)
