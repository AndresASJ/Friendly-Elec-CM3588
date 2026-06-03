# 20 — Music → Google Drive sync (server-side)

Syncs the Soulseek music library (`/mnt/drive1/Downloads/Soulseek`) up to **Google Drive**
directly from the CM3588, using [`rclone`](https://rclone.org). This **replaces** the old
setup where a Mac mounted the `Drive1` SMB share and the Google Drive desktop app did the
upload — now it runs 24/7 on the server, with no Mac required. Installed 2026-06-03.

## Why server-side

- Runs 24/7 — doesn't depend on the Mac being awake/connected.
- No flaky SMB mount in the path.
- Manageable/observable from the box itself (logs, cron).
- The library is already kept clean (partials live outside it; dupes quarantined).

## Pieces

| Path | What |
|------|------|
| `/usr/local/bin/gdrive-music-sync.sh` | The sync job ([`scripts/gdrive-music-sync.sh`](../scripts/gdrive-music-sync.sh)) |
| `/usr/local/etc/gdrive-music-filter.txt` | Excludes OS cruft + partials ([`configs/gdrive-music-filter.txt`](../configs/gdrive-music-filter.txt)) |
| `/var/log/gdrive-music-sync.log` | Run log |
| root crontab: `*/15 * * * *` | Runs the sync every 15 min (flock-guarded; no-ops until the remote is authed) |
| `rclone` remote `gdrive:` | Google Drive auth — **never committed** (lives in `/root/.config/rclone/rclone.conf`, mode 600) |

The sync is a one-way **mirror** (`rclone sync`): Drive is made to match the local library.
Deletions go to Drive **trash** (`--drive-use-trash`, recoverable) and are capped at
`--max-delete 200` as a safety net against an accidental local wipe.

## One-time auth (the only manual step)

rclone needs to be authorized against your Google account (OAuth). On a machine with a
browser + rclone (e.g. the Mac, `brew install rclone`):

```bash
rclone authorize "drive"
```

Log in, approve, copy the token JSON it prints, then on the server:

```bash
rclone config create gdrive drive token '<PASTED_TOKEN_JSON>' scope drive
rclone lsd gdrive:                     # verify access
/usr/local/bin/gdrive-music-sync.sh    # first sync (mirrors the library up)
```

After that the cron keeps Drive in sync every 15 min.

## Switching off the Mac

Once this is verified, **disable the Google Drive app's sync of the music folder on the
Mac** (and it can unmount the `Drive1` share) so the two don't double-upload or fight over
the same Drive folder.

## Notes

- Uses rclone's built-in OAuth client (fine for personal use). For higher throughput you can
  later add your own Google Cloud OAuth client ID — see rclone's "Making your own client_id".
- Storage: the library is ~90 GB, so the Google account needs a plan with room (Google One).
