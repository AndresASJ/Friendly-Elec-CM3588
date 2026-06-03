#!/bin/bash
# Sync the Soulseek music library -> Google Drive (server-side, replaces the Mac).
# One-way mirror: Google Drive is made to match the local library. Deletions go to
# Drive's trash (recoverable) and are capped by --max-delete as a safety net.
# Installed by Claude 2026-06-03. Auth lives in /root/.config/rclone/rclone.conf (remote "gdrive").
set -uo pipefail

SRC="/mnt/drive1/Downloads/Soulseek"
REMOTE="gdrive:Soulseek"
LOG="/var/log/gdrive-music-sync.log"
FILTER="/usr/local/etc/gdrive-music-filter.txt"
LOCK="/run/lock/gdrive-music-sync.lock"

ts(){ date '+%F %T'; }

# Skip cleanly until the Google Drive remote has been authorized.
if ! rclone listremotes 2>/dev/null | grep -q '^gdrive:'; then
  echo "$(ts) remote 'gdrive' not configured yet — skipping (run the auth step)" >> "$LOG"
  exit 0
fi

# Don't overlap runs.
exec 9>"$LOCK" || exit 0
if ! flock -n 9; then
  echo "$(ts) previous sync still running — skip" >> "$LOG"
  exit 0
fi

echo "$(ts) === sync start ===" >> "$LOG"
rclone sync "$SRC" "$REMOTE" \
  --filter-from "$FILTER" \
  --transfers 4 --checkers 8 \
  --drive-use-trash \
  --max-delete 200 \
  --track-renames \
  --log-file "$LOG" --log-level INFO --stats 0
rc=$?
echo "$(ts) === sync done (rc=$rc) ===" >> "$LOG"
exit $rc
