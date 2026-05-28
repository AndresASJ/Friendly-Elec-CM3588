# 13 — Backups & Maintenance

## What's actually irreplaceable

Not everything needs backing up. Media files (movies, TV) can be re-downloaded. App configs, databases, and personal data **cannot**.

| Tier | What | Where | Strategy |
|------|------|-------|----------|
| 🔴 Critical | Personal photos (Immich), Seafile libraries, HA config, Ghost content | `/mnt/drive1/Photos`, `/mnt/drive1/seafile`, `/mnt/drive1/homeassistant`, `/DATA/AppData/ghost` | 3-2-1: local + USB + offsite (B2 / S3) |
| 🟡 Important | Database dumps (Immich Postgres, Seafile MariaDB, Ghost MySQL) | hot-dump nightly to `/mnt/toshiba/backups/` | nightly to USB |
| 🟢 Replaceable | App configs (Sonarr, Radarr, Prowlarr, etc.) | `/mnt/drive1/appdata/` | weekly snapshot to USB |
| ⚪ Skip | Media library (movies/TV/torrents/cache) | — | re-download if needed |

## Hot-dump databases

Live containers can't be backed up by copying files — you'll get a corrupted database. Always use the DB's own dump tool.

### Immich Postgres

```bash
docker exec immich-postgres pg_dump -U postgres -d immich -F c -f /tmp/immich.dump
docker cp immich-postgres:/tmp/immich.dump /mnt/toshiba/backups/immich/immich-$(date +%F).dump
docker exec immich-postgres rm /tmp/immich.dump
```

### Seafile MariaDB

```bash
docker exec big-bear-seafile-db \
  mysqldump -uroot -p"$DB_ROOT_PASSWD" --all-databases \
  > /mnt/toshiba/backups/seafile/seafile-$(date +%F).sql
```

### Ghost MySQL

```bash
docker exec ghost-db \
  mysqldump -uroot -p"$ROOT_PASSWD" ghost \
  > /mnt/toshiba/backups/ghost/ghost-$(date +%F).sql
```

## File backups (rsync)

Everything else is just files — `rsync` handles it.

```bash
# Photos (largest — Immich)
rsync -a --delete /mnt/drive1/Photos/ /mnt/toshiba/backups/Photos/

# Home Assistant
rsync -a --delete /mnt/drive1/homeassistant/config/ /mnt/toshiba/backups/homeassistant/

# Ghost content
rsync -a --delete /DATA/AppData/ghost/config/ /mnt/toshiba/backups/ghost/content/

# *arr app configs (low data, fast)
rsync -a --delete /mnt/drive1/appdata/ /mnt/toshiba/backups/appdata/
```

## Cron schedule

Combine the above into a single script and schedule it.

[`scripts/backup.sh`](../scripts/backup.sh) — sample backup script.

Run it nightly:

```bash
crontab -e
# Add:
0 3 * * * /root/scripts/backup.sh >> /var/log/homelab-backup.log 2>&1
```

## Offsite (B2 / S3)

For the truly irreplaceable tier, use [`rclone`](https://rclone.org) to push to Backblaze B2 (~$0.005/GB/month).

```bash
# One-time setup
rclone config   # add a "b2" remote

# In the backup script, after the local rsyncs:
rclone sync /mnt/toshiba/backups/immich/ b2:my-bucket/immich/ \
  --transfers 4 --checkers 8 --bwlimit 50M --progress
```

## Restoring

Each service-specific doc explains its own restore. The general pattern:

1. Stop the container
2. Restore the data directory from backup
3. Restore the DB from the dump
4. Start the container

For Immich specifically:

```bash
docker compose -f /var/lib/casaos/apps/immich/docker-compose.yml down
rsync -a /mnt/toshiba/backups/Photos/ /mnt/drive1/Photos/
docker compose -f /var/lib/casaos/apps/immich/docker-compose.yml up -d immich-postgres
sleep 30
docker exec -i immich-postgres pg_restore -U postgres -d immich --clean \
  < /mnt/toshiba/backups/immich/immich-2026-05-20.dump
docker compose -f /var/lib/casaos/apps/immich/docker-compose.yml up -d
```

## Routine maintenance

### Weekly

- Glance at CasaOS dashboard: any containers in restart-loop?
- Check `df -h` — any drive >85% full?
- Update CasaOS app store apps via UI

### Monthly

- `sudo apt update && sudo apt upgrade`
- Check SMART status on every drive:
  ```bash
  sudo smartctl -H /dev/nvme0n1
  sudo smartctl -H /dev/sda
  ```
- Restart the host to apply kernel updates

### Quarterly

- **Test a restore.** Pick one service, restore from backup to a temp location, verify it works. Backups you don't test aren't backups.
- Review NPM SSL certs — Let's Encrypt should auto-renew, but check the expiry dates
- Audit running containers — anything unused? Remove it.

## Logs and disk usage

Container logs can grow huge. Limit them in `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  }
}
```

Then `sudo systemctl restart docker`. Existing containers keep their old log settings until recreated.

Prune unused images/volumes weekly:

```bash
docker system prune -af --volumes
```

> Don't run that with `--volumes` if you have any compose stack stopped — `--volumes` removes volumes not attached to a running container, including those of stopped stacks. Use `docker image prune -af` only if you're unsure.

---

## Next

→ [14 — Troubleshooting](14-troubleshooting.md)
