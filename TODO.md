# TODO

Open items for the CM5388 homelab, highest-impact first. Verified against live
state on **2026-08-15** — items inherited from older notes were re-checked, not
copied forward.

Status key: 🔴 urgent · 🟠 should do · 🟡 nice to have · ⏸️ deferred by choice

---

## 🔴 1. Move Immich photos to toshiba (immediate drive1 relief)

Immich's 166 GB photo library sits on drive1 at 97%. Moving it to `/mnt/toshiba/photos`
drops drive1 to ~88%. The move is clean: Immich's volume mount maps the host path to
`/usr/src/app/upload`, so all DB paths are relative — just stop Immich, rsync, swap
the mount source, start Immich.

The Toshiba external library and volume mount are already configured (done 2026-08-15).

- [ ] Stop Immich stack
- [ ] `rsync -avP /mnt/drive1/Photos/ /mnt/toshiba/photos/`
- [ ] Change compose volume source from `/mnt/drive1/Photos` → `/mnt/toshiba/photos`
- [ ] Start Immich, verify photos load
- [ ] Remove `/mnt/drive1/Photos` after confirming
- [ ] Set a floor alert — the existing Disk Guard workflow fires at >85%, which
      every drive except drive2/toshiba now exceeds permanently, so it has become
      background noise. Re-tune the threshold or make it per-drive.

## 🔴 2. mergerfs over NVMe drives (hardlinking fix)

`docs/16-hardlinking-migration-plan.md` diagnosed this on 2026-06-01. The waste has
tripled since (`torrents/complete`: 351 GB → 1.1 TB). Every import is still a full
copy because hardlinks can't cross the four separate ext4 filesystems.

mergerfs `2.33.5` is already installed. Pool the **four NVMe drives only** — the
Toshiba USB HDD stays outside (USB disconnect would degrade the pool).

The mergerfs unified mount path should be chosen so that when RAID replaces the
individual drives in ~2 years, the array mounts at the same path — zero app
reconfiguration on transition.

- [ ] Run during a low-use window; plan is in `docs/16`
- [ ] Update `docs/16` to reflect: toshiba excluded from pool, RAID transition intent
- [ ] Sonarr/Radarr/Lidarr root folders already include `/mnt/toshiba` — these
      stay as-is alongside the new pooled mount

## 🟠 3. VPN alerting is transition-only, so a missed message = silent downtime

Root cause of the 2026-08-12 → 08-15 outage lasting three days rather than an hour.
`vpn-healthcheck.sh` alerts on state *change* only (correct — it prevents spam), so
it fired once and then logged `status=DOWN prev=DOWN` every 5 minutes in silence.

- [ ] Re-alert after N consecutive DOWN checks (e.g. every 12th = hourly nag), **or**
- [ ] Auto-remediate: on sustained DOWN, `docker restart gluetun-qbit` → wait for
      healthy → `docker restart qbittorrent`. The script already has all the
      detection logic; this is a handful of lines.
- [ ] Consider the same treatment for `gluetun-slskd`, which has no healthcheck
      script at all and would fail exactly as silently.

## 🟠 4. No alerting on failed Jellyseerr requests

The same silent-failure shape as #3, different service. Jellyseerr requests were
failing to reach Sonarr/Radarr for **17 days** (movies) and **~4 months** (TV) with
no signal — found only because someone noticed a specific film wasn't downloading.
See `journal/2026-08-31.md`.

`MEDIA_FAILED` notifications do fire, but evidently to somewhere nobody reads. The
cheap fix is a poll, since one call gives the whole answer:

```
GET /api/v1/request?take=100&filter=failed   → pageInfo.results
```

- [ ] n8n workflow: poll hourly, alert when `pageInfo.results > 0`, include titles
- [ ] Check where Jellyseerr's existing `MEDIA_FAILED` notification agent points, and
      either fix that destination or turn it off in favour of the poll
- [ ] While there: a mismatch check comparing Jellyseerr's stored `activeDirectory` /
      `activeProfileId` against the live `/api/v3/rootfolder` + `/api/v3/qualityprofile`
      from each *arr would have caught this at the moment of the migration

## 🟠 5. Backups don't cover n8n-postgres

`scripts/backup.sh` dumps Immich's Postgres but **not** `n8n-postgres` — which holds
every workflow, credential, and execution history, plus the `contacts` table.
Carried over from the May 31 handoff and still not done.

- [ ] Add a `pg_dump` of `n8n-postgres` to `scripts/backup.sh` (mirror the Immich
      block at lines 49-52)
- [ ] Verify a restore actually works — an untested backup isn't a backup

## 🟠 6. Secret hygiene

- [ ] `/mnt/drive1/AppData/gluetun-qbit/update-port.sh` has the qBit WebUI password
      in plaintext and is mode `0755`. Not in the repo (verified), so local exposure
      only. → `chmod 600`, or delete the script entirely (see item 6).
- [ ] Rotate the main Apple ID password — it was shared in chat during the May
      contacts-sync setup. The app-specific password is what's actually used by
      `contacts-sync.py`, so rotating the main one is safe. **Status unverified.**

## 🟡 7. Two redundant qBit port-push mechanisms

Both work (verified 2026-08-15) but only one is needed. The `*/5` cron predates
gluetun's native `VPN_PORT_FORWARDING_UP_COMMAND` hook.

- [ ] Drop the cron `update-port.sh` and rely on gluetun's native hook — this also
      resolves the plaintext-password half of item 5
- [ ] Its log `/mnt/drive1/AppData/gluetun-qbit/port-update.log` had grown to 2.5 MB
      of `No port file` lines on the 96%-full disk; rotate or remove

## 🟡 8. Smaller service issues

- [ ] `slskd` sits at ~22% CPU steady-state — worth understanding whether that's
      normal share-scanning or a stuck loop
- [ ] Lidarr reports RSS sync gaps on seedpool and DigitalCore (~1 hr uncovered
      windows). Likely indexer flakiness; watch before acting
- [ ] Home Assistant: Music Assistant playlist parse error
      (`MissingField: "items" of type PlaylistTracks`)
- [ ] Home Assistant: `vaca` voice satellite repeatedly disconnects/reconnects
- [ ] Swap sitting at 4.6 GB of 7.8 GB used with 1.2 GB RAM free. Nothing is
      thrashing now, but worth watching on 16 GB
- [ ] Delete leftover `/DATA/AppData/plexamp` (64 KB) and `/DATA/AppData/plex` (83 MB)

## 🟡 9. Automation backlog (n8n)

Framework already exists in the Todo Capture flow; these are incremental intents.

- [ ] `email → mailto:` intent
- [ ] `directions → Maps` intent
- [ ] `meet → calendar` intent
- [ ] Capture bot: drain more than one message per poll
- [ ] Music Assistant rescan triggered on Soulseek download completion
- [ ] Ghost blog workflows (next up per owner's backlog)
- [ ] ⏸️ Yelp auto-reply — **on hold by owner**

---

## Recently closed

- ✅ **2026-08-15** — Toshiba USB HDD wired as overflow storage — volume mounts + root
  folders added to Sonarr, Radarr, Lidarr, Immich; dirs created with uid 1000
- ✅ **2026-08-15** — Plex removed (unused; Jellyfin + Infuse is the only media stack)
- ✅ **2026-08-15** — qBit VPN silent death (wedged NAT-PMP); recovered, documented
  in `docs/06` + `docs/14`
- ✅ **2026-08-15** — PlexAmp removed (61,969 restarts, unused, empty claim token)
- ✅ **2026-06-21** — containerd image store moved off the 57 GB eMMC onto NVMe
- ✅ **2026-06-21** — Jellyseerr split-DNS fix (missing NPM proxy host) + HTTPS
- ✅ **2026-05-31** — drive2 rebalanced from 100% → 72% (now 77%)
- ✅ **2026-05-31** — qBit gluetun migrated to native Proton provider (auto-failover)
