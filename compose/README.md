# Compose files

These are the **sanitized** docker-compose files for every service in this stack. They're the actual running configs from the host, with secrets replaced by `CHANGE_ME_*` placeholders.

## How to use

For each file:

1. Open the compose file you want to deploy
2. Replace every `CHANGE_ME_*` placeholder with a real value
3. Either:
   - **Via CasaOS:** click **+** (top right) → **Install a customized app** → switch to YAML → paste → install
   - **Via CLI:** `docker compose -f <file>.yml up -d`

For files referencing `configs/*.example`, copy the example file to its real path and fill in your secrets there.

## Suggested deploy order

1. `nginx-proxy-manager.yml` — reverse proxy first
2. `adguard-home.yml` — DNS
3. `tailscale.yml` + `cloudflared.yml` — remote access
4. `qbittorrent-gluetun.yml` — verify VPN kill-switch before adding *arrs
5. `prowlarr.yml`, `flaresolverr.yml`, `sonarr.yml`, `radarr.yml`, `recyclarr.yml`
6. `jellyfin.yml`, `plex.yml`, `jellyseerr.yml`, `unpackerr.yml`
7. `slskd-gluetun.yml`, `music-assistant.yml`, `plexamp.yml`, `kord-lastfm.yml`
8. `immich.yml`
9. `seafile.yml`, `ghost.yml`
10. `home-assistant.yml`
11. `2fauth.yml`

## File reference

| Compose file | Service(s) | Port(s) | Notes |
|--------------|------------|---------|-------|
| `nginx-proxy-manager.yml` | NPM | 80, 81, 443 | Reverse proxy + Let's Encrypt |
| `cloudflared.yml` | Cloudflare Tunnel | — | Public exposure without open ports |
| `tailscale.yml` | Tailscale | 5252 | Mesh VPN |
| `adguard-home.yml` | AdGuard Home | 53, 3000 | DNS + ad blocking |
| `qbittorrent-gluetun.yml` | qBittorrent + Gluetun | 8090 | VPN-routed torrents |
| `slskd-gluetun.yml` | slskd + Gluetun | 5032, 50300 | VPN-routed Soulseek |
| `prowlarr.yml` | Prowlarr | 9696 | Indexer manager |
| `flaresolverr.yml` | FlareSolverr | 8191 | Cloudflare bypass |
| `sonarr.yml` | Sonarr | 8989 | TV shows |
| `radarr.yml` | Radarr | 7878 | Movies |
| `recyclarr.yml` | Recyclarr | — | TRaSH Guides automation |
| `unpackerr.yml` | Unpackerr | — | Auto-extract archives |
| `jellyfin.yml` | Jellyfin | 8096 | Primary media server |
| `plex.yml` | Plex | host | Secondary media server |
| `jellyseerr.yml` | Jellyseerr | 5055 | Request UI |
| `music-assistant.yml` | Music Assistant | host | Music aggregator |
| `plexamp.yml` | PlexAmp | host | Headless music player |
| `kord-lastfm.yml` | kord-lastfm | 8787 | Last.fm scrobble bridge |
| `immich.yml` | Immich (4 containers) | 2283 | Photos |
| `seafile.yml` | Seafile (3 containers) | 7777 | File sync |
| `ghost.yml` | Ghost + MySQL | 2368 | Blog |
| `home-assistant.yml` | Home Assistant | host | Smart home |
| `2fauth.yml` | 2FAuth | 8000 | 2FA manager |
