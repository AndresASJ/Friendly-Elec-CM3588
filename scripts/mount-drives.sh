#!/usr/bin/env bash
# Helper to find drive UUIDs and print the fstab lines you need.
#
# Run this once after partitioning + formatting your drives. It prints
# the lines you should add to /etc/fstab (it does NOT edit fstab itself —
# that's intentional, so you can review).
#
# Usage:  sudo bash scripts/mount-drives.sh

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Run as root: sudo $0"
  exit 1
fi

echo "==> Detected block devices:"
lsblk -f
echo

echo "==> Suggested /etc/fstab entries:"
echo "# (review carefully before adding to /etc/fstab)"
echo

n=1
for dev in /dev/nvme*n1p1 /dev/sd?1; do
  [ -b "$dev" ] || continue
  uuid=$(blkid -s UUID -o value "$dev" 2>/dev/null || true)
  fstype=$(blkid -s TYPE -o value "$dev" 2>/dev/null || true)
  [ -z "$uuid" ] && continue
  [ "$fstype" != "ext4" ] && continue

  label=$(blkid -s LABEL -o value "$dev" 2>/dev/null || true)
  if [ -n "$label" ] && [[ "$label" =~ ^drive[0-9]+$ ]]; then
    mountpoint="/mnt/$label"
  else
    mountpoint="/mnt/drive$n"
    n=$((n+1))
  fi

  printf "UUID=%-40s %-15s ext4   defaults,nofail   0  2\n" "$uuid" "$mountpoint"
done

echo
echo "After adding lines to /etc/fstab, run:"
echo "  sudo mkdir -p /mnt/drive{1,2,3,4} /mnt/toshiba /DATA"
echo "  sudo mount -a"
echo "  df -h"
