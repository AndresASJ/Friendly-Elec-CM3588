# TODO

Open items for the CM5388 homelab, highest-impact first. Verified against live
state on **2026-08-15** — items inherited from older notes were re-checked, not
copied forward.

Status key: 🔴 urgent · 🟠 should do · 🟡 nice to have · ⏸️ deferred by choice

---

## 🔴 1. drive1 is at 96% (83 GB free)

`drive1` is simultaneously the Docker data-root, the containerd image store, and
1.1 TB of torrents. This is structurally the same setup that caused the June eMMC
fill, just on a bigger disk — and when it fills, Docker starts failing writes
across every service at once.

```
drive1  1.8T  1.7T   83G  96%   <-- docker + containerd + 1.1T torrents
drive3  1.9T  1.7T  133G  93%
drive4  1.9T  1.4T  358G  80%
drive2  1.9T  1.4T  418G  77%
toshiba 1.8T   52G  1.7T   3%   <-- 1.7 TB free, barely used
```

Not a standalone problem — it is mostly caused by item 2. Fixing the hardlinking
topology is what actually reclaims the space; moving data is the stopgap.

- [ ] Decide the stopgap: what moves to the Toshiba (1.7 TB free) to buy headroom
- [ ] Set a floor alert — the existing Disk Guard workflow fires at >85%, which
      every drive except drive2/toshiba now exceeds permanently, so it has become
      background noise. Re-tune the threshold or make it per-drive.

## 🔴 2. Hardlinking is still broken — and the waste has tripled

`docs/16-hardlinking-migration-plan.md` diagnosed this on 2026-06-01. The plan was
written and verified, then deferred. **The problem has grown substantially since:**

| | 2026-06-01 | 2026-08-15 |
|---|---|---|
| `drive1/torrents/complete` | 351 GB | **1.1 TB** |
| Hardlinked files in libraries | 0 | 2 |

Every completed torrent is still being *copied* into the library instead of
hardlinked, because downloads are pinned to drive1 while libraries live on
drive2/3/4 — and hardlinks cannot cross filesystems. Sonarr and Radarr both have
`copyUsingHardlinks: True` and silently fall back to copying.

Live audit today confirms it is unchanged:

```
/mnt/drive2/shows: 0 hardlinked    /mnt/drive1/movies: 2 hardlinked
/mnt/drive3/shows: 0 hardlinked    /mnt/drive3/movies: 0 hardlinked
/mnt/drive4/shows: 0 hardlinked    /mnt/drive4/movies: 0 hardlinked
```

mergerfs `2.33.5` is already installed at `/usr/bin/mergerfs`. The migration plan
is written and ready.

- [ ] **Owner go/no-go required** — this touches every library path
- [ ] Run during a low-use window; plan is in `docs/16`
- [ ] ⚠️ Do not auto-run — deliberately gated on owner approval

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

## 🟠 4. Backups don't cover n8n-postgres

`scripts/backup.sh` dumps Immich's Postgres but **not** `n8n-postgres` — which holds
every workflow, credential, and execution history, plus the `contacts` table.
Carried over from the May 31 handoff and still not done.

- [ ] Add a `pg_dump` of `n8n-postgres` to `scripts/backup.sh` (mirror the Immich
      block at lines 49-52)
- [ ] Verify a restore actually works — an untested backup isn't a backup

## 🟠 5. Secret hygiene

- [ ] `/mnt/drive1/AppData/gluetun-qbit/update-port.sh` has the qBit WebUI password
      in plaintext and is mode `0755`. Not in the repo (verified), so local exposure
      only. → `chmod 600`, or delete the script entirely (see item 6).
- [ ] Rotate the main Apple ID password — it was shared in chat during the May
      contacts-sync setup. The app-specific password is what's actually used by
      `contacts-sync.py`, so rotating the main one is safe. **Status unverified.**

## 🟡 6. Two redundant qBit port-push mechanisms

Both work (verified 2026-08-15) but only one is needed. The `*/5` cron predates
gluetun's native `VPN_PORT_FORWARDING_UP_COMMAND` hook.

- [ ] Drop the cron `update-port.sh` and rely on gluetun's native hook — this also
      resolves the plaintext-password half of item 5
- [ ] Its log `/mnt/drive1/AppData/gluetun-qbit/port-update.log` had grown to 2.5 MB
      of `No port file` lines on the 96%-full disk; rotate or remove

## 🟡 7. Smaller service issues

- [ ] `slskd` sits at ~22% CPU steady-state — worth understanding whether that's
      normal share-scanning or a stuck loop
- [ ] Lidarr reports RSS sync gaps on seedpool and DigitalCore (~1 hr uncovered
      windows). Likely indexer flakiness; watch before acting
- [ ] Home Assistant: Music Assistant playlist parse error
      (`MissingField: "items" of type PlaylistTracks`)
- [ ] Home Assistant: `vaca` voice satellite repeatedly disconnects/reconnects
- [ ] Swap sitting at 4.6 GB of 7.8 GB used with 1.2 GB RAM free. Nothing is
      thrashing now, but worth watching on 16 GB
- [ ] Delete leftover `/DATA/AppData/plexamp` (64 KB, inert since PlexAmp removal)

## 🟡 8. Automation backlog (n8n)

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

- ✅ **2026-08-15** — qBit VPN silent death (wedged NAT-PMP); recovered, documented
  in `docs/06` + `docs/14`
- ✅ **2026-08-15** — PlexAmp removed (61,969 restarts, unused, empty claim token)
- ✅ **2026-06-21** — containerd image store moved off the 57 GB eMMC onto NVMe
- ✅ **2026-06-21** — Jellyseerr split-DNS fix (missing NPM proxy host) + HTTPS
- ✅ **2026-05-31** — drive2 rebalanced from 100% → 72% (now 77%)
- ✅ **2026-05-31** — qBit gluetun migrated to native Proton provider (auto-failover)
