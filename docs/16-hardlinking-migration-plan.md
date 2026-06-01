# 16 — Hardlinking fix: migration plan (mergerfs single-tree)

> Status: **PLAN — not yet executed.** Diagnosis is verified live (2026-06-01);
> the migration steps below have NOT been run. Read fully before starting.

## TL;DR

Imports across drives are **full copies, not hardlinks**, so every seeding torrent
is duplicated into the library. ~**351 GB** currently sits in
`/mnt/drive1/torrents/complete`, most of it duplicated into libraries on
drive2/3/4. Cause is **topology**, not config. The fix is a **mergerfs union pool**
so downloads and their imported media land on the *same physical disk* and can be
hardlinked. mergerfs (`2.33.5`) is **already installed** at `/usr/bin/mergerfs`.

## Verified diagnosis (2026-06-01)

- **4 independent ext4 filesystems**, no pool: `/mnt/drive1..4` are each their own
  `/dev/nvmeXn1p1`. (`/DATA` is just a second bind of drive1, not a union.)
- **Downloads are pinned to drive1**: qBit `DefaultSavePath=/mnt/drive1/torrents/complete`,
  `TempPath=/mnt/drive1/torrents/incomplete`.
- **Libraries span other drives**:
  - Sonarr roots: `/mnt/drive2/shows`, `/mnt/drive3/shows`, `/mnt/drive4/shows`
  - Radarr roots: `/mnt/drive1/movies`, `/mnt/drive3/movies`, `/mnt/drive4/movies`
- **`copyUsingHardlinks` is already `True`** in both Sonarr and Radarr — so the apps
  *try* to hardlink and silently fall back to copy when the import crosses a
  filesystem (which is almost always, since downloads are on drive1).
- **Link-count audit** (`st_nlink`): **0 hardlinked files** across all roots —
  including `drive1/movies` (same fs as downloads). The drive1 ones are nlink=1
  because their torrents already finished seeding and were removed (expected, not
  waste). Cross-drive ones are nlink=1 because they physically *can't* link.

| Root | files | standalone (GB) |
|---|---|---|
| drive1/movies | 39 | 42.8 |
| drive3/movies | 260 | 1031.1 |
| drive4/movies | 167 | 320.0 |
| drive2/shows | 1637 | 1367.2 |
| drive3/shows | 751 | 557.8 |
| drive4/shows | 1068 | 1042.6 |

**Why hardlinks can't cross drives:** a hardlink is a second directory entry for the
*same inode*; inodes are filesystem-local, so `link()` between two different
filesystems returns `EXDEV` and *arr copies instead. This is physics, not a setting.

## The fix: mergerfs union pool + single `/data` tree

mergerfs unions the 4 drives into one tree. Crucially, mergerfs routes a `link()`
call to **the branch that already holds the source file**, so when *arr hardlinks
`media/...` ← `torrents/...`, the new media entry is created on the *same disk* as
the download → a real hardlink, **zero extra space**, instant import. New downloads
are spread across drives by the `category.create=mfs` (most-free-space) policy, and
the hardlinked media follows the download onto whatever disk it landed on.

This is the standard TRaSH "single tree / single mount" layout.

### Target layout

Each drive gets a parallel `data/` skeleton; the pool unions them:

```
/mnt/storage/                 <- mergerfs pool (branches: /mnt/drive{1,2,3,4}/data)
└── data/
    ├── torrents/{tv,movies,music}
    └── media/{shows,movies,music,books,audiobooks}
```

Containers get a **single** bind: `/mnt/storage/data => /data`. Then:
- qBit save path → `/data/torrents/...`
- Sonarr root → `/data/media/shows`, Radarr root → `/data/media/movies`

## Migration steps (in order)

> Every `mv` below is a **same-filesystem rename** — instant, no data copied,
> safe. Nothing moves *between* drives. Do this with the *arr apps + qBit stopped.

1. **Stop** qbittorrent, sonarr, radarr (CasaOS).
2. **Reshape each drive into a `data/` skeleton** (rename in place):
   ```bash
   # drive1
   mkdir -p /mnt/drive1/data/media
   mv /mnt/drive1/torrents      /mnt/drive1/data/torrents
   mv /mnt/drive1/movies        /mnt/drive1/data/media/movies
   mv /mnt/drive1/Music         /mnt/drive1/data/media/music     # optional, if pooling music
   # drive2
   mkdir -p /mnt/drive2/data/media && mv /mnt/drive2/shows /mnt/drive2/data/media/shows
   # drive3
   mkdir -p /mnt/drive3/data/media && mv /mnt/drive3/shows /mnt/drive3/data/media/shows && mv /mnt/drive3/movies /mnt/drive3/data/media/movies
   # drive4
   mkdir -p /mnt/drive4/data/media && mv /mnt/drive4/shows /mnt/drive4/data/media/shows && mv /mnt/drive4/movies /mnt/drive4/data/media/movies
   ```
   (Decide per-type what to pool — see "Open decisions".)
3. **Mount the pool** (test first, then persist):
   ```bash
   mkdir -p /mnt/storage
   mergerfs -o defaults,allow_other,use_ino,cache.files=partial,dropcacheonclose=true,\
   category.create=mfs,moveonenospc=true,minfreespace=20G,fsname=mergerfs \
   /mnt/drive1/data:/mnt/drive2/data:/mnt/drive3/data:/mnt/drive4/data /mnt/storage
   ```
   - `use_ino` → consistent inode numbers so hardlinks/`st_nlink` report correctly.
   - `category.create=mfs` → new files go to the disk with most free space.
   - `moveonenospc=true` → if a disk fills mid-write, spill to another.
   - Persist via `/etc/fstab` (with `x-systemd.requires`/`After` so it mounts
     **before** Docker starts) — see §fstab below.
4. **Re-point CasaOS compose** for qbit/sonarr/radarr: replace the four
   `/mnt/drive{1,2,3,4}` binds with the single `/mnt/storage/data:/data`. Per the
   repo workflow these edits go through CasaOS, then get documented + pushed.
5. **qBittorrent**: set `DefaultSavePath=/data/torrents`, `TempPath=/data/torrents/incomplete`;
   update each category save path to `/data/torrents/{tv,movies}`. Re-point existing
   torrents' save location to the new path (qBit "Set location" — same physical files,
   just the new mount path).
6. **Sonarr/Radarr**: change root folders to `/data/media/shows` and
   `/data/media/movies`; fix the download-client path + any remote path mapping;
   confirm `copyUsingHardlinks` stays on. Use **"Update & move" by editing the root /
   bulk path edit** — because the files were only *renamed in place*, the DB paths
   change but no data is moved.
7. **Verify** (acceptance test):
   ```bash
   # after one fresh grab + import:
   stat -c '%h %n' /mnt/storage/data/media/shows/<Show>/<file>.mkv   # %h should be 2
   # pool free space unchanged by an import (no duplication):
   df -h /mnt/storage
   ```
   nlink ≥ 2 on a freshly imported file = success.

## fstab persistence

```
/mnt/drive1/data:/mnt/drive2/data:/mnt/drive3/data:/mnt/drive4/data  /mnt/storage  fuse.mergerfs  defaults,allow_other,use_ino,cache.files=partial,dropcacheonclose=true,category.create=mfs,moveonenospc=true,minfreespace=20G,x-systemd.requires=/mnt/drive1,x-systemd.before=docker.service  0 0
```
Confirm Docker's unit has `After=mnt-storage.mount` (or the bind mounts will start
before the pool exists and containers will see empty dirs).

## Reclaiming the *existing* ~351 GB of duplicates

The pool fixes things **going forward** — new imports hardlink. Pre-existing copies
were written to a *different* drive than their seeding torrent, so they can't be
retro-linked without moving data across drives. Options for the backlog:
- **Let it age out**: as old torrents hit their seed goals and qBit removes them, the
  duplicate copy in `torrents/` disappears and only the library file remains.
- **Targeted re-link**: for content where keeping the seed matters, re-run the
  import *after* migration so the new copy + torrent co-locate and link (costs a
  re-download only if the torrent isn't already on the destination disk).
- Don't mass-delete `torrents/complete` blindly — some of it is **seed-only** and was
  never in the library (e.g. the German-Remux R&M packs we kept seeding on 2026-06-01).

## Open decisions (need owner input before executing)

1. **Which content types join the pool?** Shows + movies clearly yes. Music
   (drive1), Books/AudioBooks (drive1/drive4), Photos/Immich, Seafile — leave out
   (they're not part of the download→import hardlink flow) unless you want unified
   spreading. Recommendation: **pool only `torrents` + `media/{shows,movies}`** for
   now; leave Immich/Seafile/Music where they are.
2. **Single combined media tree vs keep movies on drive1?** Radarr already has a
   movies root on drive1 (same fs as downloads) — those *could* hardlink today if
   downloads and that root co-locate. The pool makes this uniform; no reason to keep
   the split.
3. **Downtime window** — apps are down during steps 1–6 (minutes, since no data
   moves). Pick a low-use time.
4. **Backups/AppData** stay on drive1 outside the pool (already the case).

## Why not the alternatives

- **Per-drive download dirs aligned to each library (no pool):** brittle — *arr picks
  the destination drive by free space *after* the download finishes, so you'd have to
  pin each app to a single drive and lose multi-drive spreading. Rejected.
- **Do nothing / accept copies:** wastes a full duplicate per seeding torrent and
  doubles write wear. The thing this whole plan exists to kill.
- **Symlinks instead of hardlinks:** breaks if the torrent is removed and confuses
  some players/scanners; hardlinks are strictly better within a pool.

## Repo

Diagnosis commands and live values captured in `journal/2026-06-01.md`. Related:
`docs/02-storage.md`, `docs/06-downloads-vpn.md`.
