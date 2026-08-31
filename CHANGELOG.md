# Changelog

Notable changes to the CM5388 homelab. Newest first.

Format loosely follows [Keep a Changelog](https://keepachangelog.com). There are no
releases — this is infrastructure, so entries are grouped by date. Each entry links
to the journal for the full narrative and to the relevant doc for how it works now.

---

## 2026-08-31

### Added
- **Jellyfin `Music` library** — Jellyfin previously had only `Movies` and `Shows`, so
  the ~88 GB of Soulseek FLAC in `/mnt/drive1/Downloads/Soulseek` was not reachable from
  any client. Added a third library pointed straight at that download directory, built by
  hand as a virtual folder (`music.collection` + `music.mblink` + `options.xml`) to match
  the existing two. Points at the raw download dir rather than the mergerfs pool by
  choice — instant, no data moved, at the cost of ~140 un-imported slskd folders showing
  as junk artists. Needs a **Scan Media Library** run to register.
  ([journal](journal/2026-08-31.md) · [docs](docs/08-music.md))

---

## 2026-08-15

### Fixed
- **qBittorrent had been dead for ~3 days** — gluetun's ProtonVPN NAT-PMP
  port-forwarding loop wedged on 08-12 (`recvfrom: connection refused` to
  `10.2.0.1:5351`) and never recovered, while the WireGuard tunnel stayed up. Because
  gluetun's healthcheck only tests outbound reachability, the container kept
  reporting `healthy` and `HEALTH_RESTART_VPN` never fired. Restarting
  `gluetun-qbit` then `qbittorrent` restored it: 151 stalled seeds and 7 stalled
  downloads went from 0 B/s to ~33 MB/s down. ([journal](journal/2026-08-15.md) ·
  [docs/06](docs/06-downloads-vpn.md))

### Added
- **Toshiba USB HDD wired up as overflow storage** — created directory structure on
  `/mnt/toshiba` (1.7 TB free) and added volume mounts + root folders to Sonarr,
  Radarr, Lidarr, and Immich. Jellyfin already had access via `/mnt:/mnt`. Toshiba
  stays **outside** the future mergerfs pool (USB disconnect risk).
  ([journal](journal/2026-08-15.md))

### Removed
- **PlexAmp** — deployed 2026-03-10 with an empty `PLEXAMP_CLAIM_TOKEN`, crash-looped
  **61,969 times**. Unused, removed.
- **Plex** — unused (Jellyfin + Infuse on Apple TV is the only media stack). Container
  removed, CasaOS app deleted. Appdata (83 MB) left at `/DATA/AppData/plex`.

### Documentation
- Documented the wedged-NAT-PMP failure mode, its signature logs, and the recovery
  procedure — `healthy` does **not** mean port forwarding works.
- Recorded that the qBit port-push scripts only *look* broken: they log
  `setPreferences ... [1]` when firing before qBit's WebUI is listening. Both
  verified working.
- Added `TODO.md`, `CHANGELOG.md`, and a whole-system `HANDOFF.md`.
- Updated `HANDOFF.md` with storage migration plan: Immich photos → toshiba, then
  mergerfs over NVMe drives only, then RAID in ~2 years (same mount path, zero
  app reconfiguration on transition).
- Fixed the stale git remote (`Friendly-Elec-CM5388` → `Friendly-Elec-CM3588`).

## 2026-07-17

### Changed
- **n8n owner password reset** via `n8n user-management:reset` — the password was
  forgotten and is stored only as a bcrypt hash, so it could not be recovered. All
  workflows, credentials, and executions preserved in Postgres. Owner account
  re-created with the same email. ([journal](journal/2026-07-17.md))

## 2026-06-21

### Fixed
- **eMMC disk-full incident** — moved the containerd image store off the 57 GB eMMC
  root onto NVMe via bind mount (`/var/lib/containerd` → `/mnt/drive1/containerd`).
  Both docker and containerd now depend on drive1.
- **Jellyseerr "offline" at home** — split-DNS gap: worked on cellular but not on the
  LAN because the AdGuard wildcard pointed at NPM with no matching proxy host. Added
  the missing host, then enabled HTTPS via Let's Encrypt DNS-01.
  ([journal](journal/2026-06-21.md))
- **slskd stale healthcheck port** (5030 → 5032) plus a seeding health check.

### Changed
- Service update pass across 8 `:latest` apps.

## 2026-06-06 → 2026-06-08

### Added
- **Voice assistant** — local Whisper (STT) + Piper (TTS) over Wyoming, wired into
  Home Assistant Assist with Gemini for intent handling. STT round-trip ~1.7 s.
- **Follow-Up Mode** — silent mic re-arm so the next command needs no wake word.

### Changed
- Prefer local intents for faster command handling; British voice
  (`en_GB-jenny_dioco`).
- Cut Echo Show `view_timeout` 120 s → 10 s (response text lingered).
- Split API keys so Hermes runs on the free tier and HA on the paid one — resolved
  to $0 with no Nabu Casa subscription.
- Added Jellyfin user Hendrix with Jellyseerr access.

### Fixed
- Missing weather in HA (the Met integration wasn't loaded).

## 2026-06-02 → 2026-06-04

### Added
- **Hermes Agent** — self-hosted AI agent on Telegram (Gemini 3.5 Flash), later
  redesigned to a single container. Can request movies/TV via Radarr + Sonarr,
  read n8n (then create/edit workflows with guardrails), and use the Todoist API.
- **Model auto-fallback chain** — 3.5-flash → 2.5-flash → lite.
- **rclone Google Drive sync** for the music library (server-side).

### Security
- Todoist token rotated after a leak; the leaked token was invalidated.
- Fixed `homelab-memory` permissions — Hermes runs with no homelab knowledge if
  `memories/USER.md` isn't uid 10000.

### Fixed
- Music library dedup + FLAC-only cleanup (5.1 GB reclaimed).
- Quarantined 44 flood-duplicate partial stubs (3.39 GB).

## 2026-06-01 → 2026-06-03

### Added
- **Lidarr** (music \*arr) and **Soularr** (Lidarr ↔ Soulseek bridge) — music stack
  complete.
- `sonarr-force-import.py` and a deliberate Remux → x265 re-grab workflow
  (Rick & Morty: 163 GB → 37 GB).

### Fixed
- **slskd VPN was dead** — a pinned custom WireGuard config pointed at a retired
  Proton server, failing silently with no failover. Switched to ProtonVPN
  **provider mode** so gluetun auto-rotates among healthy servers.
- slskd now runs as uid 1000 so Soularr/Lidarr can import its downloads.
- Moved slskd's incomplete dir out of the Drive-synced Soulseek folder.
- Lidarr/Soularr switched to request-only monitoring (stopped a download flood).

### Documentation
- **Hardlinking root cause + mergerfs migration plan** (`docs/16`). Diagnosis
  verified live; migration deliberately **not** executed. Still open — see
  [TODO.md](TODO.md).

## 2026-05-29 → 2026-05-31

### Added
- **n8n** workflow automation, migrated **SQLite → PostgreSQL**.
- Alert workflows: New Media, Torrent Done, Disk Guard, Soulseek Done — all to
  Telegram via `@ASJNOTI_BOT`.
- **Todoist capture bot** — text the bot a todo, Gemini parses it, task created with
  intent awareness (iCloud contacts → tap-to-call/text links) and auto-filing into
  sections. Plus a one-time Things → Todoist importer.
- **FlacPlayer TODO.md mirror** into Todoist (one-way, hourly, file is truth).
- **VPN-down Telegram alerting** (`vpn-healthcheck.sh`, 5-min cron) — written after a
  silent VPN death hid for ~3 weeks. This is what caught the 2026-08-15 outage.
- `qbit-cleanup.py` — needed because setting qBit share limits auto-removes imported
  torrents when the \*arr Completed Download Handling is on.

### Fixed
- **Recyclarr silent sync failure** + unblocked x265.
- **qBit gluetun migrated to native Proton provider** — a single pinned server is a
  silent single point of failure; provider mode gives auto-failover.
- **drive2 rebalanced 100% → 72%** across drive3/drive4.

## 2026-05-28

### Added
- Comprehensive repo rewrite: full CM5388 homelab setup guide (`docs/01`–`docs/21`).
- `journal/` folder for daily change logs.

## 2024-08-13

### Added
- Initial commit.
