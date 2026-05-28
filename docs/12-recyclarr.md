# 12 — Recyclarr (Quality Profile Automation)

[Recyclarr](https://recyclarr.dev) is a small CLI tool that syncs Sonarr/Radarr quality profiles and custom formats from the community-maintained [TRaSH Guides](https://trash-guides.info/).

Without Recyclarr, you'd manually maintain ~100 custom formats per app and re-tune them every few months as new release groups emerge. With it, you set a profile once and Recyclarr keeps it current on a schedule.

## What this config does

- **Sonarr** → `WEB-1080p` profile, with **x265 preferred** (smaller files, same quality)
- **Radarr** → `SQP-1 (1080p)` profile (TRaSH's "Size Quality Preference" — streaming-grade releases at smallest acceptable size)

These are aggressive about size — good if you have hundreds of GB free, not TB. For lossless quality, swap to `WEB-2160p` / `SQP-2`.

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
    base_url: http://<SONARR_CONTAINER_IP>:8989   # see below
    api_key: YOUR_SONARR_API_KEY                  # ← from Sonarr → Settings → General

radarr:
  sqp-1-1080p:
    base_url: http://<RADARR_CONTAINER_IP>:7878
    api_key: YOUR_RADARR_API_KEY
```

> **Why use the container IP not localhost or LAN IP?** Recyclarr runs inside its own Docker network, so it can't see `localhost`. The host's LAN IP works *if* the Sonarr/Radarr ports are bound to it. Easiest is `docker inspect sonarr | grep IPAddress` and paste that — but those IPs can change on restart. The most stable answer is to attach Recyclarr to the same Docker network as Sonarr/Radarr, then use container names. See compose comments.

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
