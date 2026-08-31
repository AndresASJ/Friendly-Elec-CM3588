# 08 — Music

The music side runs separately from Sonarr/Radarr. Music sourcing uses **slskd** (Soulseek) since most studio rips and FLAC come from there.

## Stack

| Service | Purpose | Port |
|---------|---------|------|
| **slskd** | Soulseek client (behind Gluetun — see [docs/06](06-downloads-vpn.md)) | 5032 |
| **Music Assistant** | Server that aggregates local + streaming music | — |
| **PlexAmp** | ~~Plex-native music player~~ — **removed 2026-08-15, unused** | — |
| **kord-lastfm** | Lightweight Last.fm scrobbling bridge | 8787 |
| **Jellyfin** | Serves the music library (see below) | 8096 |

## Music Assistant

[Music Assistant](https://music-assistant.io) discovers your local library, plus Spotify/Tidal/Qobuz/Apple Music if you connect them. Pairs with Home Assistant to control playback on any media_player entity.

[`compose/music-assistant.yml`](../compose/music-assistant.yml):
- Data dir: `/mnt/drive1/music-assistant/data`
- Music library: `/mnt/drive1/Music`

On first launch, add music providers via the UI. Add **Plex** or **Jellyfin** as providers to surface their library inside MA.

## Plex + PlexAmp

> **PlexAmp was removed 2026-08-15 — unused.** It had been crash-looping since it
> was deployed on 2026-03-10 (61,969 restarts) because it was created with an empty
> `PLEXAMP_CLAIM_TOKEN` and never completed first-start auth. Rather than re-claim a
> player nobody used, the CasaOS app was taken down and
> `/var/lib/casaos/apps/plexamp/` deleted. Leftover config at `/DATA/AppData/plexamp`
> (64K) is inert. [`compose/plexamp.yml`](../compose/plexamp.yml) is kept for
> reference if it's ever wanted back. Plex itself is untouched and still running.

PlexAmp is Plex's high-end music player. Running a headless instance on the homelab lets it cast to any UPnP/Cast/AirPlay speaker on the network.

[`compose/plexamp.yml`](../compose/plexamp.yml).

After the container starts, get the claim token from `plex.tv/claim`, paste it in the PlexAmp container logs URL, then it self-registers to your Plex server.

> **If PlexAmp keeps restarting:** it's almost always a Plex token issue. The claim
> token is **single-use and expires 4 minutes** after you generate it, so it must be
> pasted into the compose file and the container recreated within that window. A
> blank or stale token means it can never come up — it will loop roughly every 55
> seconds forever, since `restart: unless-stopped` keeps retrying a state that
> cannot self-heal.

## kord-lastfm — scrobble bridge

A small Node.js script that listens to webhook events from Plex/Jellyfin and forwards listening data to Last.fm.

[`compose/kord-lastfm.yml`](../compose/kord-lastfm.yml).

The server script is mounted from `/DATA/AppData/kord-lastfm/server.js`. Configure your Last.fm API key + session token via env vars (see the compose file).

In Plex/Jellyfin, add a webhook pointing to `http://192.168.50.178:8787/scrobble`.

## Jellyfin — Music library

Jellyfin serves the Soulseek music directly out of the slskd download directory. The
library is defined at `/DATA/AppData/jellyfin/config/data/root/default/Music/`:

| File | Contents |
|------|----------|
| `music.collection` | empty marker file — sets the collection type to Music |
| `music.mblink` | `/mnt/drive1/Downloads/Soulseek` |
| `options.xml` | realtime monitor on, MusicBrainz for artist + album metadata |

Files are owned `1000:devmon`, matching the `Movies`/`Shows` libraries beside them. No
mount change was needed — the Jellyfin container bind-mounts `/mnt` → `/mnt`, so the
path resolves inside the container unchanged.

> **A new virtual folder only registers during a library scan.** Restarting Jellyfin is
> not enough — the folder stays absent from the database until
> **Dashboard → Scheduled Tasks → Scan Media Library** runs. If a library you just added
> never shows up in the UI, that scan is almost always what is missing.

> **The library points at the raw download dir, not the pool.** Lidarr's root folder *is*
> `/mnt/drive1/Downloads/Soulseek`, so it manages music in place. Only a few artists are
> renamed into clean `Artist/Album` folders; the rest are still raw slskd folder names and
> will show in Jellyfin as junk artists/albums. Tidying this means creating
> `/mnt/storage/media/music` in the pool, re-pointing Lidarr's root, and letting it move +
> rename — which would also relieve `drive1`, currently at 98%.

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
