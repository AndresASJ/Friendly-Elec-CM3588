# 14 — Troubleshooting

Common gotchas, in roughly the order you'll hit them.

## qBittorrent shows my real IP

**Symptom:** `docker exec qbittorrent curl ifconfig.me` returns your ISP-assigned IP, not ProtonVPN's.

**Cause:** Most likely `network_mode: service:gluetun` is missing, or qBit started before Gluetun was healthy.

**Fix:**
1. Verify in [`compose/qbittorrent-gluetun.yml`](../compose/qbittorrent-gluetun.yml):
   - qBit has `network_mode: service:gluetun` (no own ports)
   - Gluetun has the ports, not qBit
   - qBit `depends_on: gluetun: { condition: service_healthy }`
2. Recreate both: `docker compose up -d --force-recreate`

## Sonarr/Radarr "import failed" — file is not a hardlink

**Symptom:** Sonarr imports a file but logs say "copied instead of hardlinked," and disk usage doubles.

**Cause:** Sonarr's mount path doesn't share a filesystem with qBittorrent's complete path. Hardlinks only work within the same filesystem.

**Fix:**
- Both apps must mount `/mnt/drive1:/mnt/drive1` (not sub-paths)
- Verify: `docker exec sonarr stat /mnt/drive1/torrents/complete/some_file.mkv` should report the same inode as the qBit container sees.
- Both apps should use PUID/PGID `1000:1000` so file permissions match.

## Container can't reach another container by name

**Symptom:** Sonarr can't connect to qBittorrent at `http://qbittorrent:8090`.

**Cause:** Containers in **different Docker networks** can't resolve each other's names. CasaOS gives each app its own network by default.

**Fix:** Use the host LAN IP instead (`http://192.168.50.178:8090`). Or attach Sonarr to the qBittorrent network — but that gets brittle. LAN IP is simpler and works across reboots.

## Cloudflare Tunnel returns "Error 1033" or "no healthy origin"

**Cause:** Tunnel can't reach the service. Either the cloudflared container is down, or the **public hostname → service** mapping points to the wrong port/IP.

**Fix:**
- `docker logs cloudflared` — look for connection errors
- In Cloudflare Zero Trust dashboard → Tunnels → your tunnel → Public Hostnames — verify the service URL is `http://<homelab-lan-ip>:<port>` (not container name, not `localhost`)
- Test: `curl -I http://192.168.50.178:8096` from the homelab itself

## Service works on cellular but shows "You are offline" at home (split-DNS)

**Symptom:** A web app (e.g. Jellyseerr at `jellyseerr.asj.media`) loads fine on cellular / away from home, but on the home Wi-Fi it shows "You are offline" or won't load. Hitting the raw `http://192.168.50.178:<port>` works.

**Cause:** Split-horizon DNS mismatch. The service has a **Cloudflare Tunnel public hostname** (so the off-LAN path works), but **no matching proxy host in Nginx Proxy Manager**. At home, AdGuard's wildcard rewrite `*.asj.media → 192.168.50.178` sends every `*.asj.media` name to NPM — and if NPM has no entry for that hostname, the request lands nowhere. The result is a hostname that resolves on cellular (public Cloudflare IP → tunnel) but dead-ends at home (AdGuard → NPM → no host).

**Diagnose:**
```bash
# 1. App itself healthy?
curl -s -o /dev/null -w "%{http_code}\n" http://192.168.50.178:5055/api/v1/status   # 200 = app fine
# 2. Does NPM have the host? (list server_names)
docker exec nginxproxymanager sh -c 'grep -h server_name /data/nginx/proxy_host/*.conf'
# 3. Does the proxy path work end-to-end? (real Host header)
curl -s -o /dev/null -w "%{http_code}\n" -H "Host: jellyseerr.asj.media" http://192.168.50.178/api/v1/status
```

**Fix:** Add the missing proxy host in NPM (`http://192.168.50.178:81` → Hosts → Proxy Hosts → Add): domain = the hostname, scheme `http`, forward IP `192.168.50.178`, the service port, Websockets ✅.

**HTTPS at home needs a cert in NPM.** NPM hosts listen on `:80` only *unless* you give them a Let's Encrypt cert. Cloudflare's edge cert only covers the *tunnel* (off-LAN) path — so if you browse `https://host.asj.media` at home, AdGuard sends you to NPM, which has no cert for that name and the TLS handshake fails (the app then shows "offline"). Two options:
- **http only at home:** access `http://host.asj.media` (NPM redirects nothing; works but no TLS on-LAN).
- **https at home (preferred):** in the host's **SSL** tab → *Request a new SSL Certificate* → **DNS Challenge → Cloudflare**, paste the Cloudflare API token (same token obsidian/tailscale/jellyseerr use), enable **Force SSL**. This issues a real cert via DNS-01 and adds a `:443` listener, so it works identically on-LAN and off. See [`docs/04-networking.md`](04-networking.md#add-a-proxy-host).

> Rule of thumb: **every Cloudflare Tunnel public hostname needs a matching NPM proxy host** (or an AdGuard rewrite exception), or it'll work remotely but break at home.

## Immich uploads time out on large videos

**Cause:** Cloudflare's default 100 MB upload limit, or chunked encoding being re-buffered.

**Fix:**
- In Cloudflare Tunnel hostname settings → **HTTP → Disable chunked encoding**: ✅
- For Cloudflare Free plan, upload cap is 100 MB. Workarounds:
  - Upload from inside the LAN (no proxy)
  - Use Tailscale instead of Cloudflare for big uploads
  - Upgrade to Cloudflare Pro ($20/mo, lifts to 500 MB)

## AdGuard Home → "DNS server isn't responding"

**Causes:**
1. AdGuard not running on port 53 (something else bound it)
2. Your router still points clients at the ISP DNS
3. AdGuard container restarted and lost its DHCP lease

**Fix:**
1. `sudo ss -tulpn | grep :53` — should show only AdGuard
2. Disable any host-side resolver: `sudo systemctl disable --now systemd-resolved`
3. In your router DHCP settings, set primary DNS to the homelab's LAN IP

## CasaOS app won't start — "port already in use"

**Cause:** Another container or host service is bound to the same port.

**Fix:**
```bash
sudo ss -tulpn | grep :<port>
docker ps --format '{{.Names}} {{.Ports}}' | grep <port>
```
Either change the port in the new app's compose, or stop the other thing.

## Recyclarr can't reach Sonarr/Radarr

**Symptom:** `recyclarr sync` errors with `Connection refused` or `Name or service not known`.

**Cause:** Recyclarr's `base_url` is wrong. Container-to-container `localhost` doesn't work, and CasaOS gives each app its own network.

**Fix:** Use the container's IP from `docker inspect sonarr | grep IPAddress`, or attach Recyclarr to the same network. Or simplest: use the host's LAN IP — `http://192.168.50.178:8989` — as long as Sonarr publishes its port to the host (it does, by default).

## Plex / PlexAmp endlessly restart

**Cause:** Plex claim token expired or never set.

**Fix:**
1. Visit https://plex.tv/claim → copy the token
2. Add to the compose file: `environment: { PLEX_CLAIM: "claim-xxxxxxxxxxxxxxxxxxxx" }`
3. `docker compose up -d --force-recreate plex`
4. The token is single-use and expires in 4 minutes — claim and recreate quickly

## Home Assistant can't see new Wi-Fi devices

**Cause:** Container is on a bridge network instead of host networking.

**Fix:** Container needs `network_mode: host`. mDNS / SSDP discovery needs broadcast — bridge networks don't forward broadcast.

## Drive 100% full — `/var` filling up

**Common culprit:** Docker logs.

```bash
sudo du -sh /var/lib/docker/containers/*/ | sort -h | tail -20
```

Fix log size globally in `/etc/docker/daemon.json` (see [docs/13](13-backups-and-maintenance.md) → Logs and disk usage).

## Containers won't start after reboot

**Cause:** Drives didn't mount before Docker tried to start.

**Fix:**
- All drive mounts in `/etc/fstab` need `nofail` (boot continues if a drive is missing)
- All compose `restart: unless-stopped` policies should handle the rest
- If a drive failed: `dmesg | grep -i nvme` to check for hardware issues

## "No such file or directory" mounting `/dev/dri` (HW transcoding)

**Cause:** Kernel module isn't loaded or user isn't in the `video` group.

**Fix:**
```bash
ls -la /dev/dri    # should show card0, renderD128
# If missing:
sudo modprobe rockchip-vpu
# In compose:
group_add:
  - video
```

## Anything else

Check logs first — they almost always tell you what's wrong:

```bash
docker logs <container> --tail 100 -f
journalctl -u docker.service -n 100 -f
journalctl -u casaos -n 100
```

If a container loops on restart:
```bash
docker logs <container>    # without -f, to see the crash
```

If the host itself is unhappy:
```bash
htop
df -h
dmesg | tail -50
```
