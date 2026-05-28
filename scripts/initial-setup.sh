#!/usr/bin/env bash
# Initial host setup for the FriendlyElec CM5388 homelab.
# Run after a fresh Ubuntu install.
#
# Usage:  sudo bash scripts/initial-setup.sh

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Run as root: sudo $0"
  exit 1
fi

echo "==> 1/6  Updating system"
apt update
apt full-upgrade -y
apt autoremove -y

echo "==> 2/6  Installing base tools"
apt install -y \
  curl wget git \
  htop iotop iftop ncdu tree \
  unzip zip \
  ca-certificates gnupg lsb-release \
  net-tools dnsutils \
  smartmontools \
  rsync \
  cron

echo "==> 3/6  Setting timezone"
timedatectl set-timezone America/New_York

echo "==> 4/6  Installing Docker"
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
  usermod -aG docker "${SUDO_USER:-root}"
fi

echo "==> 5/6  Configuring Docker log rotation"
cat > /etc/docker/daemon.json <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  }
}
EOF
systemctl restart docker

echo "==> 6/6  Installing CasaOS"
if [ ! -d /var/lib/casaos ]; then
  curl -fsSL https://get.casaos.io | bash
fi

echo
echo "Initial setup complete."
echo "Next steps:"
echo "  1. Mount your drives (see docs/02-storage.md and scripts/mount-drives.sh)"
echo "  2. Open CasaOS at http://$(hostname -I | awk '{print $1}')"
echo "  3. Follow docs/03-casaos.md onward"
