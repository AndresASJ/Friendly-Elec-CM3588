#!/bin/sh
# Reports usage of all /mnt data drives to the n8n "Disk Guard" workflow.
# n8n decides thresholds + de-dupes + sends Telegram. Read-only (df only).
# Installed by Claude on 2026-05-29. See docs/15-n8n.md.

URL="http://localhost:5678/webhook/disk-report"

DRIVES=$(df -P -BG | awk '
  NR>1 && $6 ~ /^\/mnt\// && $6 !~ /docker/ {
    gsub("G","",$4); gsub("%","",$5);
    printf "%s{\"mount\":\"%s\",\"usePct\":%s,\"availGb\":\"%s\"}", (c++ ? "," : ""), $6, $5, $4
  }')

curl -s -m 10 -X POST "$URL" \
  -H "Content-Type: application/json" \
  -d "{\"drives\":[$DRIVES]}" >/dev/null 2>&1
