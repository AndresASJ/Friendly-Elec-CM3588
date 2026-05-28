# 02 — Storage Layout

All persistent data lives off the eMMC. The eMMC holds only the OS — drives hold everything else.

## Physical layout

| Device | Mount | Size | Purpose |
|--------|-------|------|---------|
| `mmcblk0` | `/` | 64 GB | OS (eMMC) |
| `nvme0n1p1` | `/mnt/drive1` + `/DATA` | 1.0 TB | Main: app data, primary media, photos, downloads |
| `nvme1n1p1` | `/mnt/drive3` | 1.0 TB | Additional media |
| `nvme2n1p1` | `/mnt/drive2` | 250 GB | Working space |
| `nvme3n1p1` | `/mnt/drive4` | 1.0 TB | Additional media |
| `sda1` | `/mnt/toshiba` | 2 TB | USB cold backup |

All drives are **ext4**.

## Partition + format a new drive

If you're starting from a blank NVMe:

```bash
# Identify the drive
sudo lsblk -f

# Partition (single partition, full disk)
sudo parted /dev/nvme0n1 --script mklabel gpt mkpart primary ext4 0% 100%

# Format
sudo mkfs.ext4 -L drive1 /dev/nvme0n1p1
```

## Get the UUID

```bash
sudo blkid /dev/nvme0n1p1
```

Copy the `UUID="..."` value — you'll use it in `/etc/fstab` so the mount survives a drive-letter reshuffle.

## /etc/fstab

Make mounts persistent across reboots. Here's the actual `fstab` from this host (UUIDs replaced with placeholders):

```fstab
UUID=ROOT_UUID                                /              ext4   defaults,commit=120,errors=remount-ro  0 1
tmpfs                                          /tmp           tmpfs  defaults,nosuid                         0 0
UUID=DRIVE1_UUID                               /mnt/drive1    ext4   defaults,nofail                         0 2
UUID=DRIVE2_UUID                               /mnt/drive2    ext4   defaults,nofail                         0 2
UUID=DRIVE3_UUID                               /mnt/drive3    ext4   defaults,nofail                         0 2
UUID=DRIVE4_UUID                               /mnt/drive4    ext4   defaults,nofail                         0 2
UUID=TOSHIBA_UUID                              /mnt/toshiba   ext4   defaults,nofail                         0 2
/mnt/drive1/DATA                               /DATA          none   bind                                    0 0
```

Key flags:
- **`nofail`** — boot continues even if a drive is missing (critical for the USB drive)
- **`bind`** — the last line bind-mounts `/mnt/drive1/DATA` onto `/DATA`. This is how CasaOS sees app data while we keep everything physically on `drive1`.

After editing:

```bash
sudo mkdir -p /mnt/drive{1,2,3,4} /mnt/toshiba /DATA
sudo mount -a
df -h
```

## The `/DATA` bind mount

CasaOS hard-codes `/DATA` as its data directory. Rather than waste eMMC space, we bind-mount it onto `drive1`. Everything CasaOS thinks is at `/DATA/AppData/whatever` actually lives at `/mnt/drive1/DATA/AppData/whatever`.

This is invisible to the containers but lets you reset the OS without losing app data.

## Folder layout on drive1

```
/mnt/drive1/
├── DATA/                  → bind-mounted to /DATA
│   ├── AppData/           ← CasaOS app configs
│   │   ├── adguard-home/
│   │   ├── ghost/
│   │   ├── immich/
│   │   ├── nginxproxymanager/
│   │   ├── plex/
│   │   ├── tailscale/
│   │   └── ...
│   └── Media/             ← Plex/Jellyfin media root
├── AppData/               ← Manually-deployed app configs
│   ├── compose/           ← Custom docker-compose deployments
│   │   ├── slskd/
│   │   └── slskd-vpn/
│   ├── gluetun-qbit/
│   ├── gluetun-slskd/
│   ├── kord-lastfm/
│   ├── qbittorrent/
│   └── slskd/
├── appdata/               ← LinuxServer-style configs
│   ├── radarr/
│   ├── sonarr/
│   ├── prowlarr/
│   └── jellyseerr/
├── Downloads/
│   └── Soulseek/
├── Movies/
├── Music/
├── Photos/                ← Immich upload target
├── torrents/
│   ├── incomplete/
│   └── complete/
├── homeassistant/config/
├── music-assistant/data/
├── seafile/
└── obsidian-vault/
```

> **Note on casing:** there are both `AppData/` and `appdata/` directories — this is because CasaOS uses the former and LinuxServer.io image conventions use the latter. They're not the same folder.

## Hardlink considerations

For the `*arr` apps to import downloads as **hardlinks** (no double storage), Sonarr/Radarr and qBittorrent must mount the **exact same parent path**. That's why every relevant compose file mounts `/mnt/drive1:/mnt/drive1` rather than picking sub-paths.

If you mount qBit at `/downloads` and Sonarr at `/tv`, hardlinks will **silently fail** and double your disk usage on import.

## Permissions

Containers run as PUID/PGID `1000:1000`. Make sure your media directories are owned the same way:

```bash
sudo chown -R 1000:1000 /mnt/drive1/{Movies,torrents,Photos,Music}
```

---

## Next

→ [03 — CasaOS](03-casaos.md)
