# 12 — Recyclarr (Quality Profile Automation)

[Recyclarr](https://recyclarr.dev) is a small CLI tool that syncs Sonarr/Radarr quality profiles and custom formats from the community-maintained [TRaSH Guides](https://trash-guides.info/).

Without Recyclarr, you'd manually maintain ~100 custom formats per app and re-tune them every few months as new release groups emerge. With it, you set a profile once and Recyclarr keeps it current on a schedule.

## What this config does

- **Sonarr** → `WEB-1080p` profile, with `x265 (HD)` **un-blocked** (see warning below)
- **Radarr** → `SQP-1 (1080p)` profile (TRaSH's "Size Quality Preference" — streaming-grade releases at smallest acceptable size)

These are aggressive about size — good if you have hundreds of GB free, not TB. For lossless quality, swap to `WEB-2160p` / `SQP-2`.

> ⚠️ **x265 gotcha:** the `x265 (HD)` custom format ships from TRaSH at score **−10000**. With `minFormatScore: 0` that *rejects every 1080p x265 release* — so naively adding it to "prefer smaller files" actually **blocks** x265 entirely. To allow x265 you must override its score to a small positive (this config uses `+100`). Even then the WEB Tier formats (1600–1700) keep good h264 WEB releases dominant; +100 just makes x265 *eligible* and a mild tiebreak. (Discovered 2026-05-31 — the live profile had silently been rejecting x265 for weeks; see `journal/2026-05-31.md`.)

## Install

Recyclarr ships as a Docker image with a built-in cron schedule.

[`compose/recyclarr.yml`](../compose/recyclarr.yml).

```bash
mkdir -p /root/recyclarr
```

Copy the example config:

```bash
cp configs/recyclarr.yml.example /root/recyclarr/recyclarr.yml
```

Then edit `/root/recyclarr/recyclarr.yml`:

```yaml
sonarr:
  web-1080p:
    base_url: http://192.168.50.178:8989          # host LAN IP — see below
    api_key: YOUR_SONARR_API_KEY                  # ← from Sonarr → Settings → General

radarr:
  sqp-1-1080p:
    base_url: http://192.168.50.178:7878
    api_key: YOUR_RADARR_API_KEY
```

> **Use the host LAN IP, not the container IP.** Recyclarr runs in its own Docker network so `localhost` won't work, but the **host LAN IP (`192.168.50.178`)** does — the Sonarr/Radarr ports are published there. Do **not** paste the Docker container IP (`docker inspect sonarr | grep IPAddress`): those change on restart, and when they do **Recyclarr fails sync silently** — no error surfaces, the profile just quietly drifts. This actually happened here (Sonarr drifted to `172.17.0.7`, the config still pointed at `.9`), which is how `x265 (HD)` sat un-corrected at −10000 for weeks. The LAN IP is stable across restarts.

## Run it once manually

```bash
docker exec recyclarr recyclarr sync
```

You should see output like:

```
[INF] Custom Format Updates
  Added:    [Required] Golden Rule HD
  Updated:  HD Bluray Tier 01
  ...
[INF] Quality Profile Updates
  Updated:  WEB-1080p
```

## On a schedule

The official `recyclarr` image runs `sync` on a cron schedule (default daily at 02:00 host time). Logs go to `/config/logs/`. The deployment at this host runs at 02:00 every day — you can see logs at `/root/recyclarr/logs/cli/`.

To change the cron, set env vars in the compose file:

```yaml
recyclarr:
  environment:
    CRON_SCHEDULE: "0 4 * * 0"   # Sunday 4am instead of daily 2am
```

## API keys — keep them out of the repo

The real `recyclarr.yml` is in `.gitignore`. The repo only ships [`configs/recyclarr.yml.example`](../configs/recyclarr.yml.example). When updating the repo, never commit `recyclarr.yml`.

## Picking a different profile

Browse [TRaSH Guides](https://trash-guides.info/) → find a profile that matches your storage budget → grab the `trash_id` for the quality profile and custom formats → paste into your `recyclarr.yml`.

Common alternatives:

| Profile | Use when |
|---------|----------|
| `WEB-1080p` | Streaming-quality, balanced size/quality (~3–5 GB/movie) |
| `WEB-2160p` | 4K HDR, no concern for size |
| `Remux-1080p` | Bluray remuxes, ~20 GB/movie |
| `Anime` | Sonarr only, separate naming/format rules |

---

## Next

→ [13 — Backups & maintenance](13-backups-and-maintenance.md)
