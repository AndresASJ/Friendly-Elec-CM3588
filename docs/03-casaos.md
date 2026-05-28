# 03 — CasaOS

[CasaOS](https://casaos.io/) is a web-based management UI for Docker containers. It runs on top of Docker Compose, so anything you can do in a compose file works here, but you get a nice dashboard, app store, and built-in reverse-proxy hostname setup.

## Why CasaOS

- **Visual install** for common apps (Immich, Jellyfin, Home Assistant, Seafile, etc.) — no manual compose writing for the common stuff
- **Per-app icon and hostname** baked into compose `x-casaos:` metadata
- **Dashboard** showing disk usage, RAM, CPU, network at a glance
- **File browser** rooted at `/DATA`
- Plays nicely with manually-deployed `docker-compose.yml` files alongside its own apps

## Install

After Docker is running:

```bash
curl -fsSL https://get.casaos.io | bash
```

The script installs CasaOS as a systemd service. UI is at `http://<your-ip>` (port 80).

> The installer also opens port 80. If you plan to run Nginx Proxy Manager on the same port, **install NPM through CasaOS first**, then point your hostname-based routing through NPM. CasaOS's own UI listens on its internal `:80` only — NPM will take ownership of the public port 80/443.

## App store sources

CasaOS ships with the official app store. The "Big Bear" community store has more apps (including Seafile, Music Assistant, kord-lastfm). Add it from:

**Settings → App Store → Add → ** `https://github.com/bigbeartechworld/big-bear-casaos`

## Installing a CasaOS app

Each app installed through CasaOS lands in `/var/lib/casaos/apps/<name>/docker-compose.yml`. You can:

1. Install via UI → tweak ports/volumes in the wizard
2. Edit the compose file directly (CasaOS picks up changes on restart)
3. Use **Import → docker-compose.yml** to bring in a custom compose file

## Importing the compose files from this repo

For each service in [`compose/`](../compose/):

1. Open CasaOS → **+** (top right) → **Install a customized app**
2. Switch to YAML mode
3. Paste the contents of the compose file
4. Replace any `CHANGE_ME` / `YOUR_*` placeholders with your real values
5. **Install**

CasaOS will deploy it and add it to your dashboard.

## App configs location

| Source | Path |
|--------|------|
| CasaOS-managed apps | `/DATA/AppData/<app>/` (i.e. `/mnt/drive1/DATA/AppData/<app>/`) |
| LinuxServer.io stack | `/mnt/drive1/appdata/<app>/` |
| Manually deployed via CLI | `/mnt/drive1/AppData/compose/<app>/` |

Don't mix them — pick one location per app and stick with it.

## CasaOS gotchas

- **Don't update CasaOS-managed apps with `docker pull`** — use the CasaOS UI. Otherwise CasaOS's internal metadata can get out of sync.
- The hostname field in `x-casaos:` only sets the dashboard label/link. Actual DNS routing happens in NPM (see [docs/04-networking.md](04-networking.md)).
- CasaOS auto-generates a `<app>_default` Docker network for each app. To make services talk to each other across apps (e.g. Sonarr → qBittorrent), use the **host IP** rather than container names, or attach them to a shared network.

---

## Next

→ [04 — Networking](04-networking.md)
