# Handoff — whole-system state as of 2026-08-15

What is running on this box, where everything lives, how to verify it, and the
traps that will cost you a day if you rediscover them the hard way.

> **Scope note.** This is the *system-wide* handoff. The older
> [`docs/HANDOFF.md`](docs/HANDOFF.md) is a deep, still-useful handoff for the
> **n8n / Todoist / contacts** stack specifically (as of 2026-05-31) — read it for
> that subsystem. Its §6 "open items" list is stale; use [`TODO.md`](TODO.md) instead.

Related: [`TODO.md`](TODO.md) · [`CHANGELOG.md`](CHANGELOG.md) ·
[`journal/`](journal/) · [`docs/`](docs/)

---

## 1. The box

**FriendlyElec CM5388** carrier board, Rockchip RK3588 (4×A76 + 4×A55), Mali-G610
GPU, 6 TOPS NPU, 16 GB RAM. Hostname `cm3588-nas`, LAN `192.168.50.178`.
Ubuntu on eMMC. Uptime at handoff: 42 days.

**Storage** — four independent ext4 filesystems, **not** a pool. This matters more
than anything else on this page (see §6).

| Mount | Device | Size | Used | Role |
|---|---|---|---|---|
| `/` | eMMC `mmcblk0p1` | 57 G | 15% | Ubuntu root |
| `/mnt/drive1` | `nvme0n1p1` | 1.8 T | **96%** ⚠️ | Docker data-root, containerd store, torrents, AppData |
| `/mnt/drive2` | `nvme3n1p1` | 1.9 T | 77% | media library |
| `/mnt/drive3` | `nvme1n1p1` | 1.9 T | **93%** ⚠️ | media library |
| `/mnt/drive4` | `nvme2n1p1` | 1.9 T | 80% | media library |
| `/mnt/toshiba` | `sda1` | 1.8 T | **3%** | USB HDD, mostly unused |

`/DATA` is a second **bind mount of drive1**, not a union — CasaOS apps write there.
Docker's data-root is `/mnt/drive1/docker` and containerd's store is
`/mnt/drive1/containerd` (both moved off eMMC on 2026-06-21 after it filled).

> 🚧 **These numbers are actively changing — storage work is underway as of
> 2026-08-15.** drive1 at 96% and the hardlinking fix are being addressed now
> (see §8). Re-run `df -h` rather than trusting this table, and check the latest
> [`journal/`](journal/) entry before acting on it.

## 2. Services

**38 containers, all managed as CasaOS apps** (`/var/lib/casaos/apps/<name>/docker-compose.yml`).
House rule: *every* service goes in CasaOS, not bare compose.

| Service | Port | Notes |
|---|---|---|
| **Media** | | |
| Jellyfin | 8096 | primary; HW transcode via Mali-G610 |
| Plex | host net | secondary |
| Jellyseerr | 5055 | requests; HTTPS via NPM (see §6 split-DNS trap) |
| Sonarr / Radarr / Lidarr | 8989 / 7878 / 8686 | |
| Prowlarr | 9696 | indexers |
| Recyclarr | — | quality profile sync |
| Unpackerr | — | |
| Flaresolverr | 8191 | Cloudflare solver for indexers |
| **Downloads (VPN-gated)** | | |
| gluetun-qbit → qBittorrent | 8090 | ProtonVPN WireGuard, **provider mode** |
| gluetun-slskd → slskd | 5032, 50300 | ProtonVPN WireGuard |
| Soularr | 8265 | Lidarr ↔ Soulseek bridge |
| **Photos** | | |
| Immich (server / ML / postgres / redis) | 2283 | NPU-accelerated ML |
| **Home / Voice** | | |
| Home Assistant | host net | |
| Music Assistant | host net | |
| faster-whisper / piper | 10300 / 10200 | Wyoming STT/TTS for HA Assist |
| **Infra** | | |
| Nginx Proxy Manager | 80/81/443 | reverse proxy + Let's Encrypt |
| AdGuard Home | 53, 3000 | DNS + wildcard rewrites |
| Cloudflared | 14333 | tunnel |
| Tailscale | 5252 | remote access |
| **Apps** | | |
| n8n + postgres | 5678 | automation — see `docs/HANDOFF.md` |
| Hermes | — | self-hosted Telegram AI agent |
| Ghost + mysql | 2368 | blog |
| Seafile (+ db, memcached) | 7777 | file sync |
| 2FAuth | 8000 | TOTP |
| kord-lastfm | 8787 | scrobble bridge |

**Removed 2026-08-15:** PlexAmp (crash-looped 61,969 times on an expired claim
token, unused). `compose/plexamp.yml` kept for reference.

## 3. Cron (root)

```
*/5  * * * *  update-port.sh          qBit port push  (redundant — see TODO #6)
*/30 * * * *  n8n-disk-report.sh      feeds n8n Disk Guard webhook
7    * * * *  flacplayer-todo-sync.py FlacPlayer TODO.md -> Todoist
0    4 * * *  contacts-sync.py        iCloud CardDAV -> Postgres `contacts`
*/5  * * * *  vpn-healthcheck.sh      qBit VPN state -> Telegram on change
#PAUSED */15  gdrive-music-sync.sh
```

All tracked in [`scripts/`](scripts/). **`vpn-healthcheck.sh` is the single most
valuable script here** — it is the only thing that detects a silent VPN death, and
it has now caught two (see §6).

## 4. Secrets — none are in the repo

Locations only; values live on the box. Repo exports are sanitized to `CHANGE_ME`
and every push is secret-scanned.

| Secret | Location |
|---|---|
| Telegram bot token + chat id | `/root/.config/vpn-alert/telegram.cred` (0600) and n8n credential |
| n8n encryption key | compose env + `/mnt/drive1/AppData/n8n/config` |
| Postgres password | n8n compose env |
| Gemini / Todoist / slskd keys | n8n credentials; Todoist also `/root/.config/flac-sync/todoist.token` |
| iCloud app-specific password | `/mnt/drive1/AppData/contacts-sync/icloud.cred` (0600) |
| ProtonVPN WireGuard key | gluetun compose env |
| ⚠️ qBit WebUI password | **plaintext, mode 0755** in `/mnt/drive1/AppData/gluetun-qbit/update-port.sh` — see TODO #5 |

## 5. Verifying it's actually healthy

Container status lies. These are the checks that tell the truth:

```bash
# Anything crash-looping? (PlexAmp hid at 61,969 restarts for 5 months)
docker ps -a --format '{{.Names}}' | while read c; do
  printf '%s %s\n' "$c" "$(docker inspect -f '{{.RestartCount}}' "$c")"
done | sort -k2 -rn | head

# qBit actually moving data? "healthy" gluetun does NOT prove this
docker exec qbittorrent curl -s http://127.0.0.1:8090/api/v2/transfer/info
# want: connection_status "connected", dht_nodes > 0, nonzero speeds
# bad:  "firewalled" + dht_nodes 0  ->  §6 wedged NAT-PMP

# Forwarded port present and matching qBit's listen port?
docker exec gluetun-qbit cat /tmp/gluetun/forwarded_port      # 0 bytes = wedged
docker exec qbittorrent curl -s http://127.0.0.1:8090/api/v2/app/preferences \
  | grep -o '"listen_port":[0-9]*'

df -h | grep -Ev 'tmpfs|overlay'
tail -5 /var/log/vpn-healthcheck.log
```

## 6. Traps — do not relearn these

**Gluetun `healthy` does not mean port forwarding works.** The healthcheck only
tests outbound reachability. Port forwarding is a *separate loop* that can die
silently; `HEALTH_RESTART_VPN=on` does not cover it, so nothing self-heals. Cost
3 days of zero traffic in Aug 2026. Recovery: restart `gluetun-qbit`, wait for
healthy, **then** restart `qbittorrent` (it shares gluetun's netns via
`network_mode: service:gluetun`, so it loses networking when gluetun restarts).
Full detail in [`docs/06`](docs/06-downloads-vpn.md).

**Never pin a single VPN server.** A pinned `wg0.conf` dies silently when Proton
retires that server — no failover, no error. Both gluetun instances use ProtonVPN
**provider mode** so they auto-rotate. This bit us twice (slskd in June, qBit
earlier).

**The qBit port-push scripts look broken but aren't.** `qbit-port-forward.sh` and
the cron `update-port.sh` log `setPreferences ... [1]` / `Connection refused` when
they fire before qBit's WebUI is listening — normal startup ordering. qBit has
`bypass_local_auth: true`, so localhost calls need no credentials.

**Hardlinks cannot cross filesystems.** drive1–4 are four separate ext4 filesystems.
Downloads are pinned to drive1 while libraries sit on drive2/3/4, so every import is
a full **copy** — Sonarr/Radarr have `copyUsingHardlinks: True` and silently fall
back. This is why drive1 is at 96%. Fix is a mergerfs union
([`docs/16`](docs/16-hardlinking-migration-plan.md), written, **not executed**).

**Setting qBit share limits auto-removes imported torrents** when \*arr Completed
Download Handling is on — it deletes your seeding data. Use `scripts/qbit-cleanup.py`
instead.

**Split DNS: works on cellular, broken at home = missing NPM proxy host.** The
AdGuard wildcard sends `*.asj.media` to NPM; if NPM has no proxy host for that
subdomain, it only resolves off-LAN. Bit us with Jellyseerr.

**n8n's image is hardened** — no Execute Command node, and the Code node can't
`require` or touch the filesystem. OS-level work happens in host scripts that feed
n8n via webhook or Postgres. `n8n-postgres` publishes no host port, so write to it
with `docker exec`.

**Hermes memory perms:** `memories/USER.md` must be uid 10000 (0640) or Hermes runs
with no homelab knowledge. Editing it as root silently breaks it.

## 7. Workflow

Repo: `https://github.com/AndresASJ/Friendly-Elec-CM3588` (renamed from
`Friendly-Elec-CM5388`; the old URL redirects — local remote corrected 2026-08-15).
Push via the box's `gh` auth.

**Every change:** update the repo → add a `journal/YYYY-MM-DD.md` entry → push.
Every new service goes in **CasaOS**, then gets documented, then pushed.

## 8. Where to start

Read [`TODO.md`](TODO.md). The top two items — drive1 at 96% and the unexecuted
hardlinking migration — are the same problem, and it is the one thing on this box
that is actively getting worse (`torrents/complete` went 351 GB → 1.1 TB between
June and August). Everything else is stable.

> 🚧 **In progress as of 2026-08-15 — storage is being addressed now.** The owner
> has given the go-ahead to take on the drive1 / hardlinking problem in this
> stretch, so treat items 1 and 2 in [`TODO.md`](TODO.md) as *active work*, not
> backlog. If you are picking this up mid-flight, check the newest entry in
> [`journal/`](journal/) before touching drive1, mount points, or any library
> path — the mergerfs migration in [`docs/16`](docs/16-hardlinking-migration-plan.md)
> moves library trees, so a stale mental model here is expensive.
