# 19 — Soularr (Lidarr ↔ Soulseek bridge)

[Soularr](https://github.com/mrusse/soularr) bridges **Lidarr**'s wanted/missing list to
**slskd** (Soulseek). On each interval it reads Lidarr's missing albums, searches Soulseek
via slskd, downloads matches, and triggers Lidarr to import them. Installed 2026-06-03
(see [`journal/2026-06-03.md`](../journal/2026-06-03.md)).

## Stack

| Container | Image | Purpose |
|-----------|-------|---------|
| `soularr` | `mrusse08/soularr:latest` | Lidarr→slskd search/download bridge + web UI (`:8265`) |

Runs as `1000:1000`, `SCRIPT_INTERVAL=300` (runs every 5 min). Compose:
[`compose/soularr.yml`](../compose/soularr.yml).

## How it fits

```
Lidarr (wanted albums) ──> Soularr ──> slskd ──> Soulseek
                                          └─ downloads to /mnt/drive1/Downloads/Soulseek
                                             (= Lidarr root) ──> Lidarr imports
```

slskd downloads land in `/mnt/drive1/Downloads/Soulseek`, which is also Lidarr's root
folder, so Lidarr imports/organizes in place.

## Install

```bash
casaos-cli app-management install -f compose/soularr.yml
```

## Configuration

`/mnt/drive1/AppData/soularr/config.ini` (git-ignored, chmod 600):

- **[Lidarr]** `host_url = http://192.168.50.178:8686`, `api_key` (Lidarr),
  `download_dir = /mnt/drive1/Downloads/Soulseek` (path Lidarr sees the downloads).
- **[Slskd]** `host_url = http://192.168.50.178:5032`, `api_key` (a dedicated `soularr`
  key added to slskd's `api_keys` in `slskd.yml`), `download_dir = /downloads`
  (Soularr's mount of the slskd download folder).
- Defaults otherwise; `search_source = missing`, FLAC-preferred `allowed_filetypes`.

## Notes

- Depends on **slskd** being online — see [`docs/06-downloads-vpn.md`](06-downloads-vpn.md)
  / the slskd VPN fix in the 2026-06-03 journal. slskd routes through `gluetun-slskd`
  (ProtonVPN); if that VPN is down, Soularr has nothing to search.
- Lidarr also grabs music via **torrents** (Prowlarr + qBittorrent) independently — see
  [`docs/18-lidarr.md`](18-lidarr.md). Soularr just adds the Soulseek source.
