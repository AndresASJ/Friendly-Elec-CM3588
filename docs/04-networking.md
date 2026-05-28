# 04 — Networking

This is the layer that makes the homelab reachable — from inside the LAN, from your phone over Tailscale, and (for select public services) from the open internet via Cloudflare.

## Layout

```
Internet
   │
   ├──── Cloudflare Tunnel ───► cloudflared container ───┐
   │       (no open ports)                                │
   │                                                      ▼
   └──── Tailscale ──────────► tailscale container ──► Nginx Proxy Manager
                                                          ▲       ┌─────────────┐
                                                          ├──────►│  Jellyfin   │
LAN clients                                               ├──────►│  Immich     │
   │                                                      ├──────►│  Seafile    │
   ▼                                                      ├──────►│  Ghost      │
AdGuard Home (DNS @ :53) ─────► resolves *.yourdomain ────┴──────►│  Jellyseerr │
                                  to homelab LAN IP              │  ...        │
                                                                  └─────────────┘
```

## The four pieces

| Service | Role | Port(s) |
|---------|------|---------|
| **AdGuard Home** | Network-wide DNS + ad/tracker blocking | 53 (DNS), 3000 (admin) |
| **Nginx Proxy Manager** (NPM) | TLS termination + hostname routing | 80, 443 (public), 81 (admin) |
| **Cloudflare Tunnel** | Public access without open router ports | — (outbound only) |
| **Tailscale** | Encrypted mesh VPN for personal devices | 5252 (admin UI) |

---

## AdGuard Home

Acts as the LAN's DNS resolver. Blocks ads/trackers at the DNS level and adds **rewrites** so `jellyfin.yourdomain.com` resolves to the homelab's LAN IP from inside the network (instead of going out to the internet and back).

### Setup

1. Install **AdGuard Home** from CasaOS
2. On first boot, visit `http://<homelab-ip>:3000`
3. Pick port 53 for DNS and a port for the admin UI (3000 is fine)
4. Set upstream DNS to `tls://1.1.1.1` and `tls://1.0.0.1` (Cloudflare DoT)
5. Enable the default blocklists

### DNS rewrites (the important bit)

In AdGuard → **Filters → DNS rewrites**, add a wildcard:

```
*.yourdomain.com → 192.168.50.178   # ← your homelab LAN IP
```

Then in your router's DHCP settings, set the primary DNS to the homelab's LAN IP. Every device on the LAN now resolves your subdomains locally — no need to round-trip through Cloudflare.

See [`compose/adguard-home.yml`](../compose/adguard-home.yml).

---

## Nginx Proxy Manager

NPM does two things:
1. Terminates TLS (Let's Encrypt certs, auto-renewed)
2. Routes incoming requests by hostname to the correct container

### Setup

1. Install **Nginx Proxy Manager** from CasaOS
2. Visit `http://<homelab-ip>:81`
3. Default login: `admin@example.com` / `changeme` — change it immediately

### Add a proxy host

For each service:

| Field | Value |
|-------|-------|
| Domain Names | `jellyfin.yourdomain.com` |
| Scheme | `http` |
| Forward Hostname / IP | `192.168.50.178` (the LAN IP, *not* container name) |
| Forward Port | `8096` |
| Block Common Exploits | ✅ |
| Websockets Support | ✅ (for Jellyfin, Immich, etc.) |
| SSL → Request Let's Encrypt | ✅ (use DNS challenge if you've set up a Cloudflare API token) |

> **Why LAN IP, not container name?** NPM and each app run in different Docker networks. Using the host's LAN IP is the simplest cross-network path. If you'd rather use container names, attach NPM to each app's network (more brittle).

See [`compose/nginx-proxy-manager.yml`](../compose/nginx-proxy-manager.yml).

---

## Cloudflare Tunnel (cloudflared)

For services you want to expose to the open internet without opening any ports on your router.

### Setup

1. Install **Cloudflared** from CasaOS (the `wisdomsky/cloudflared-web:latest` image has a web UI)
2. Visit the cloudflared web UI
3. Log into your Cloudflare account → **Zero Trust → Networks → Tunnels → Create a tunnel**
4. Copy the tunnel token; paste it into the cloudflared web UI
5. In Cloudflare's tunnel dashboard, add **Public Hostnames**:
   - `blog.yourdomain.com` → `http://192.168.50.178:2368` (Ghost)
   - `photos.yourdomain.com` → `http://192.168.50.178:2283` (Immich)
   - `drive.yourdomain.com` → `http://192.168.50.178:7777` (Seafile)
   - etc.

Cloudflare handles SSL termination at the edge — you don't need NPM in the path for public services (though you can keep it in the chain for internal access).

See [`compose/cloudflared.yml`](../compose/cloudflared.yml).

> **Don't expose Sonarr, Radarr, qBittorrent, or any admin UI through Cloudflare Tunnel.** Keep those Tailscale- or LAN-only.

---

## Tailscale

For accessing the homelab from your phone, laptop, or remote workstation as if you were on the LAN.

### Setup

1. Install **Tailscale** from CasaOS (image `tailscale/tailscale:latest`)
2. Container needs `network_mode: host` *or* `cap_add: NET_ADMIN` + `/dev/net/tun`
3. Open the container logs — copy the authentication URL → open in browser → log in
4. Approve the device in your Tailscale admin console
5. (Optional) Enable **subnet routing** so other LAN devices are reachable: add `--advertise-routes=192.168.50.0/24` to the tailscale `up` command, then approve the route in admin console
6. (Optional) Enable **MagicDNS** — gives every Tailscale device a `.ts.net` hostname

See [`compose/tailscale.yml`](../compose/tailscale.yml).

---

## Port reference (full LAN-visible list)

| Port | Service | Notes |
|------|---------|-------|
| 53/tcp + udp | AdGuard Home | DNS |
| 80, 443 | Nginx Proxy Manager | Public reverse proxy |
| 81 | NPM Admin | Keep LAN-only |
| 853 | AdGuard Home | DNS-over-TLS |
| 2283 | Immich | Photo backup |
| 2368 | Ghost | Blog |
| 3000 | AdGuard Home Admin | Keep LAN-only |
| 5032 | slskd (via gluetun) | Soulseek UI |
| 5055 | Jellyseerr | Public-ish (behind Cloudflare Access) |
| 5252 | Tailscale | Admin UI |
| 7777 | Seafile | File sync |
| 7878 | Radarr | Admin — LAN only |
| 8000 | 2FAuth | 2FA codes |
| 8090 | qBittorrent (via gluetun) | Admin — LAN only |
| 8096 | Jellyfin | Media |
| 8191 | FlareSolverr | Internal-only (Prowlarr → here) |
| 8787 | kord-lastfm | Last.fm scrobble bridge |
| 8989 | Sonarr | Admin — LAN only |
| 9696 | Prowlarr | Admin — LAN only |
| 50300 | slskd (via gluetun) | Soulseek peer port |

---

## Next

→ [05 — Media stack](05-media-stack.md)
