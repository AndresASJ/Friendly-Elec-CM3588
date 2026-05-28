# 01 — Hardware & Operating System

## The board

The host is a **FriendlyElec CM5388** carrier board powered by a Rockchip RK3588 SoC.

| Component | Spec |
|-----------|------|
| SoC | Rockchip RK3588 (4× Cortex-A76 @ 2.4 GHz + 4× Cortex-A55 @ 1.8 GHz) |
| GPU | Mali-G610 MP4 (used by Immich + Jellyfin for HW transcoding) |
| NPU | 6 TOPS (used by Immich machine-learning container) |
| RAM | 16 GB LPDDR4 |
| eMMC | 64 GB (root filesystem) |
| NVMe | 4× M.2 slots on the carrier (used for `drive1`–`drive4`) |
| Ethernet | 2× 2.5 GbE |
| USB | 2× USB 3.0, 2× USB 2.0 |

The actual layout on this host:
- **eMMC** → root filesystem (Ubuntu)
- **NVMe 0 (1 TB)** → `/mnt/drive1` (main storage, app data, primary media)
- **NVMe 1–3** → `/mnt/drive2`, `/mnt/drive3`, `/mnt/drive4` (additional media)
- **USB SATA (Toshiba)** → `/mnt/toshiba` (cold backup)

## OS install

The board officially supports both Ubuntu and Debian builds from FriendlyElec.

This stack runs on **Ubuntu 22.04 LTS (Jammy) ARM64**.

### 1. Flash the image

Download the latest Ubuntu image from FriendlyElec's wiki and flash it to the eMMC using their `eflasher` utility (or directly using `dd` to an SD card if you want to boot from SD first).

```bash
# From a Linux workstation, with the CM5388 in mass-storage mode:
sudo dd if=ubuntu-jammy-cm5388.img of=/dev/sdX bs=4M status=progress conv=fsync
```

### 2. First boot

Default credentials are usually `pi:pi` or `root:fa`. Change them immediately:

```bash
passwd
sudo passwd root
```

### 3. Update everything

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt autoremove -y
```

### 4. Base packages

```bash
sudo apt install -y \
  curl wget git \
  htop iotop iftop ncdu \
  unzip zip \
  ca-certificates gnupg lsb-release \
  net-tools dnsutils \
  smartmontools \
  rsync \
  cron
```

### 5. Set the timezone

```bash
sudo timedatectl set-timezone America/New_York
```

### 6. Set hostname

```bash
sudo hostnamectl set-hostname homelab
```

Edit `/etc/hosts` and update the `127.0.1.1` line to match.

### 7. Enable SSH key auth

From your workstation:

```bash
ssh-copy-id user@homelab.local
```

Then on the homelab, disable password auth in `/etc/ssh/sshd_config`:

```
PasswordAuthentication no
PermitRootLogin no
```

```bash
sudo systemctl restart ssh
```

---

## Next

→ [02 — Storage layout](02-storage.md)
