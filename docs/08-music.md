# 08 — Music

The music side runs separately from Sonarr/Radarr. Music sourcing uses **slskd** (Soulseek) since most studio rips and FLAC come from there.

## Stack

| Service | Purpose | Port |
|---------|---------|------|
| **slskd** | Soulseek client (behind Gluetun — see [docs/06](06-downloads-vpn.md)) | 5032 |
| **Music Assistant** | Server that aggregates local + streaming music | — |
| **PlexAmp** | Plex-native music player (headless container for casting to speakers) | — |
| **kord-lastfm** | Lightweight Last.fm scrobbling bridge | 8787 |

## Music Assistant

[Music Assistant](https://music-assistant.io) discovers your local library, plus Spotify/Tidal/Qobuz/Apple Music if you connect them. Pairs with Home Assistant to control playback on any media_player entity.

[`compose/music-assistant.yml`](../compose/music-assistant.yml):
- Data dir: `/mnt/drive1/music-assistant/data`
- Music library: `/mnt/drive1/Music`

On first launch, add music providers via the UI. Add **Plex** or **Jellyfin** as providers to surface their library inside MA.

## Plex + PlexAmp

PlexAmp is Plex's high-end music player. Running a headless instance on the homelab lets it cast to any UPnP/Cast/AirPlay speaker on the network.

[`compose/plexamp.yml`](../compose/plexamp.yml).

After the container starts, get the claim token from `plex.tv/claim`, paste it in the PlexAmp container logs URL, then it self-registers to your Plex server.

> **If PlexAmp keeps restarting:** it's almost always a Plex token issue. Re-claim via `plex.tv/claim` and restart.

## kord-lastfm — scrobble bridge

A small Node.js script that listens to webhook events from Plex/Jellyfin and forwards listening data to Last.fm.

[`compose/kord-lastfm.yml`](../compose/kord-lastfm.yml).

The server script is mounted from `/DATA/AppData/kord-lastfm/server.js`. Configure your Last.fm API key + session token via env vars (see the compose file).

In Plex/Jellyfin, add a webhook pointing to `http://192.168.50.178:8787/scrobble`.

## Library convention

```
/mnt/drive1/Music/
├── Artist Name/
│   ├── Album (Year)/
│   │   ├── 01 - Track Name.flac
│   │   ├── 02 - Track Name.flac
│   │   └── cover.jpg
│   └── Album 2 (Year)/
└── ...
```

slskd downloads to `/mnt/drive1/Downloads/Soulseek/` — manually move + rename into `/mnt/drive1/Music/` once you've checked the rip is clean (slskd downloads include lots of junk MP3s — manual sorting is sane).

---

## Next

→ [09 — Home Assistant](09-home-assistant.md)
