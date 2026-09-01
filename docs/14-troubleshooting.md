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

> A container in this state **never recovers on its own** — `restart: unless-stopped`
> just retries forever. PlexAmp racked up 61,969 restarts over five months this way
> before anyone noticed (removed 2026-08-15). Worth periodically running
> `docker ps -a --format '{{.Names}} {{.Status}}' | grep -i restarting` — or checking
> restart counts directly:
>
> ```bash
> docker ps -a --format '{{.Names}}' | while read c; do
>   printf '%s %s\n' "$c" "$(docker inspect -f '{{.RestartCount}}' "$c")"
> done | sort -k2 -rn | head
> ```

## Gluetun says `healthy` but qBittorrent downloads nothing

**Cause:** the port-forwarding loop wedged while the tunnel stayed up. Gluetun's
healthcheck only tests outbound reachability, so the container stays green and
`HEALTH_RESTART_VPN=on` never fires.

**Fix:** `docker restart gluetun-qbit`, wait for healthy, then `docker restart
qbittorrent`. Full detail, signature logs and verification steps in
[docs/06-downloads-vpn.md](06-downloads-vpn.md#failure-mode-wedged-nat-pmp-gluetun-stays-healthy).

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

## Jellyseerr requests never reach the download client

**Symptom:** You request something in Jellyseerr, it shows as approved/processing,
but it never appears in Sonarr/Radarr and nothing lands in qBittorrent. Adding the
same title *directly* in Sonarr/Radarr works fine. Can persist for months unnoticed.

**Cause:** Jellyseerr stores its own root folder + quality profile rather than
reading them live from the *arr. If they drift (e.g. after the mergerfs pool
migration re-pointed roots to `/data/media/...`), every add is rejected with HTTP 400.

**Diagnose:**

```bash
docker logs jellyseerr --since 24h 2>&1 | grep -iE 'marking status as FAILED|RootFolderExists|QualityProfileExists'
```

Look for `Root folder '/mnt/...' does not exist` or `Quality Profile does not exist`.
Then compare against what the *arr actually has:

```bash
curl -s -H "X-Api-Key: $RADARR_KEY" http://192.168.50.178:7878/api/v3/rootfolder
curl -s -H "X-Api-Key: $RADARR_KEY" http://192.168.50.178:7878/api/v3/qualityprofile
```

**Fix — both places, or retries keep failing:**

1. Server defaults, for new requests. Settings → Services in the UI, or edit
   `/mnt/drive1/appdata/jellyseerr/settings.json` with the container **stopped**
   (`activeDirectory`, `activeProfileId`, `activeProfileName`).
2. Per-request snapshots, for anything already queued or failed:

```bash
docker stop jellyseerr
DB=/mnt/drive1/appdata/jellyseerr/db/db.sqlite3
cp -a "$DB" "$DB.bak-$(date +%Y%m%d-%H%M%S)"
sqlite3 "$DB" "UPDATE media_request SET rootFolder='/data/media/movies' WHERE type='movie' AND rootFolder LIKE '/mnt/%';
               UPDATE media_request SET rootFolder='/data/media/shows'  WHERE type='tv'    AND rootFolder LIKE '/mnt/%';"
docker start jellyseerr
```

3. Retry the failures (`filter=failed` lists them; the key is `main.apiKey` in
   `settings.json`):

```bash
curl -s -H "X-Api-Key: $JS_KEY" "http://192.168.50.178:5055/api/v1/request?take=100&filter=failed"
curl -s -X POST -H "X-Api-Key: $JS_KEY" "http://192.168.50.178:5055/api/v1/request/<id>/retry"
```

**Worth checking periodically** — there is no alerting on this today. A non-zero
`pageInfo.results` from the `filter=failed` call above means requests are being
dropped on the floor.

## Import fails with "Access to the path ... is denied" (mergerfs branch permissions)

**Symptom:** A torrent completes, but the *arr queue shows `importBlocked` and the
file never reaches the library or Jellyfin. Radarr/Sonarr logs show:

```
System.UnauthorizedAccessException: Access to the path '/data/media/movies/<Title>' is denied.
```

**Cause:** the pool uses `category.create=mfs`, so **new folders are created on
whichever branch has the most free space**. If that branch's `data/media/{movies,shows}`
is root-owned `755`, the *arr (uid 1000) cannot create the title folder there — even
though every other branch is fine. The failure follows free space, so it appears
out of nowhere when a different drive becomes the emptiest.

> `docker exec radarr id` reports **root** and is misleading — that's the exec shell,
> not the app. Check the process: `docker exec radarr ps -o user,uid -C Radarr`
> (LinuxServer images run as `PUID`, here 1000).

**Diagnose — compare every branch, not just the pool view:**

```bash
for d in /mnt/drive1 /mnt/drive2 /mnt/drive3 /mnt/drive4 /mnt/toshiba; do
  printf '%-14s ' "$d"; ls -ld $d/data/media/movies 2>&1
done
df -h /mnt/drive1 /mnt/drive2 /mnt/drive3 /mnt/drive4 /mnt/toshiba   # which is emptiest?
```

The pool path `/mnt/storage/media/movies` can look correct while a branch underneath
is wrong — mergerfs shows you the first branch it finds.

**Fix — bring the odd branch in line (`<branch>` = the offender):**

```bash
chown root:1002  <branch>/data <branch>/data/media
chmod 2755       <branch>/data <branch>/data/media
chown 1001:1002  <branch>/data/media/movies <branch>/data/media/shows
chmod 2777       <branch>/data/media/movies <branch>/data/media/shows
```

Then confirm as the app's uid and re-trigger the import:

```bash
setpriv --reuid=1000 --regid=1000 --clear-groups mkdir "/mnt/storage/media/movies/.wtest"
rmdir "/mnt/storage/media/movies/.wtest"
curl -s -X POST -H "X-Api-Key: $RADARR_KEY" -H 'Content-Type: application/json' \
  -d '{"name":"RefreshMonitoredDownloads"}' http://192.168.50.178:7878/api/v3/command
```

Worth re-checking after adding any new branch to the pool. See `journal/2026-09-01.md`.

## Downloads all crawl / torrent priority does nothing

**Symptom:** dozens of torrents each moving at a trickle; setting a torrent to top
priority changes nothing.

**Cause:** qBittorrent queueing disabled — `max_active_downloads` is then inert and
every torrent runs at once, splitting the line N ways. Priority only orders a queue,
so with no queue it has no effect.

**Fix:**

```bash
docker exec qbittorrent curl -s -X POST 'http://127.0.0.1:8090/api/v2/app/setPreferences' \
  --data-urlencode 'json={"queueing_enabled":true,"max_active_downloads":4,"max_active_uploads":-1,"max_active_torrents":-1,"dont_count_slow_torrents":true}'
```

**Keep `max_active_uploads` and `max_active_torrents` at `-1`.** Queueing counts
*seeding* torrents toward those caps, so a finite value pauses seeders to make room
for downloads — quietly wrecking private-tracker ratio. Only downloads should be capped.

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
