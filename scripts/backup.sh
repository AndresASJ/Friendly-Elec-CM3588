#!/usr/bin/env bash
# Nightly homelab backup.
#
# Backs up the irreplaceable stuff to /mnt/toshiba/backups/:
#   - Immich photos + Postgres dump
#   - Seafile data + MariaDB dump
#   - Ghost content + MySQL dump
#   - Home Assistant config
#   - *arr app configs (Sonarr, Radarr, Prowlarr, Jellyseerr)
#
# Cron it nightly:
#   0 3 * * *  /root/scripts/backup.sh >> /var/log/homelab-backup.log 2>&1
#
# BEFORE USING:
#   - Set DB passwords in the environment block below (or load from a
#     root-only .env file that's chmod 600 and OUTSIDE this repo)

set -euo pipefail

# ──────────────────────────────────────────────────────────────────────
# Config — fill these in (or source from /root/.homelab-backup.env)
# ──────────────────────────────────────────────────────────────────────
SEAFILE_DB_ROOT_PASSWD="${SEAFILE_DB_ROOT_PASSWD:-CHANGE_ME}"
GHOST_DB_ROOT_PASSWD="${GHOST_DB_ROOT_PASSWD:-CHANGE_ME}"

BACKUP_ROOT="/mnt/toshiba/backups"
DATE="$(date +%F)"

# Optional: source secrets from outside the repo
[ -f /root/.homelab-backup.env ] && . /root/.homelab-backup.env

mkdir -p \
  "$BACKUP_ROOT/Photos" \
  "$BACKUP_ROOT/immich" \
  "$BACKUP_ROOT/seafile" \
  "$BACKUP_ROOT/ghost/content" \
  "$BACKUP_ROOT/ghost/db" \
  "$BACKUP_ROOT/homeassistant" \
  "$BACKUP_ROOT/appdata"

echo "==> $(date)  Starting homelab backup"

# ──────────────────────────────────────────────────────────────────────
# Immich
# ──────────────────────────────────────────────────────────────────────
echo "==> Backing up Immich photos"
rsync -a --delete /mnt/drive1/Photos/ "$BACKUP_ROOT/Photos/"

echo "==> Dumping Immich Postgres"
docker exec immich-postgres pg_dump -U postgres -d immich -F c -f /tmp/immich.dump
docker cp immich-postgres:/tmp/immich.dump "$BACKUP_ROOT/immich/immich-$DATE.dump"
docker exec immich-postgres rm /tmp/immich.dump

# ──────────────────────────────────────────────────────────────────────
# Seafile
# ──────────────────────────────────────────────────────────────────────
echo "==> Backing up Seafile library data"
rsync -a --delete /mnt/drive1/seafile/shared/ "$BACKUP_ROOT/seafile/shared/"

echo "==> Dumping Seafile MariaDB"
docker exec big-bear-seafile-db \
  mysqldump -uroot -p"$SEAFILE_DB_ROOT_PASSWD" --all-databases \
  > "$BACKUP_ROOT/seafile/seafile-$DATE.sql"

# ──────────────────────────────────────────────────────────────────────
# Ghost
# ──────────────────────────────────────────────────────────────────────
echo "==> Backing up Ghost content"
rsync -a --delete /DATA/AppData/ghost/config/ "$BACKUP_ROOT/ghost/content/"

echo "==> Dumping Ghost MySQL"
docker exec ghost-db \
  mysqldump -uroot -p"$GHOST_DB_ROOT_PASSWD" ghost \
  > "$BACKUP_ROOT/ghost/db/ghost-$DATE.sql"

# ──────────────────────────────────────────────────────────────────────
# Home Assistant
# ──────────────────────────────────────────────────────────────────────
echo "==> Backing up Home Assistant config"
rsync -a --delete /mnt/drive1/homeassistant/config/ "$BACKUP_ROOT/homeassistant/"

# ──────────────────────────────────────────────────────────────────────
# *arr app configs
# ──────────────────────────────────────────────────────────────────────
echo "==> Backing up *arr configs"
rsync -a --delete /mnt/drive1/appdata/ "$BACKUP_ROOT/appdata/"

# ──────────────────────────────────────────────────────────────────────
# Prune old DB dumps (keep last 14)
# ──────────────────────────────────────────────────────────────────────
echo "==> Pruning old dumps"
find "$BACKUP_ROOT/immich"      -name "immich-*.dump" -mtime +14 -delete
find "$BACKUP_ROOT/seafile"     -name "seafile-*.sql" -mtime +14 -delete
find "$BACKUP_ROOT/ghost/db"    -name "ghost-*.sql"   -mtime +14 -delete

echo "==> $(date)  Backup complete"
