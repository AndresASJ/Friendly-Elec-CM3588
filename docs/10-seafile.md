# 10 — Seafile

Self-hosted file sync — like Dropbox but you own the data. Supports desktop + mobile clients with delta sync, end-to-end encrypted libraries, and selective sync.

## Stack

| Container | Image | Purpose |
|-----------|-------|---------|
| `big-bear-seafile` | `seafileltd/seafile-mc:11.0.13` | Seafile server (Memcached edition) |
| `big-bear-seafile-db` | `mariadb:10.11` | Database |
| `big-bear-seafile-memcached` | `memcached:1.6.39` | Cache (required for `-mc` server image) |

All on a private bridge network `big_bear_seafile_network`.

## Install

[`compose/seafile.yml`](../compose/seafile.yml).

```bash
mkdir -p /mnt/drive1/seafile/{shared,mysql}
```

Set these env vars in the compose file:

```yaml
big-bear-seafile:
  environment:
    DB_HOST: big-bear-seafile-db
    DB_ROOT_PASSWD: CHANGE_ME_DB_ROOT_PASSWORD
    SEAFILE_ADMIN_EMAIL: you@yourdomain.com
    SEAFILE_ADMIN_PASSWORD: CHANGE_ME_ADMIN_PASSWORD
    SEAFILE_SERVER_HOSTNAME: drive.yourdomain.com    # your public hostname
    SEAFILE_SERVER_LETSENCRYPT: "false"              # NPM/Cloudflare handles TLS
    TIME_ZONE: America/New_York

big-bear-seafile-db:
  environment:
    MYSQL_ROOT_PASSWORD: CHANGE_ME_DB_ROOT_PASSWORD  # ← must match DB_ROOT_PASSWD above
```

**Generate strong passwords:**
```bash
openssl rand -base64 32
```

## Volume strategy

Seafile mounts **all four** drives:

```yaml
volumes:
  - /mnt/drive1:/mnt/drive1
  - /mnt/drive2:/mnt/drive2
  - /mnt/drive3:/mnt/drive3
  - /mnt/drive4:/mnt/drive4
  - /mnt/drive1/seafile/shared:/shared
```

This lets you create libraries anywhere on any drive. Data blobs go into `/shared/seafile/seafile-data/`. The MariaDB data lives at `/mnt/drive1/seafile/mysql/`.

## First boot

1. Bring it up: `docker compose up -d`
2. Wait ~1 minute for the DB to initialize (watch logs)
3. Visit `http://<homelab-ip>:7777`
4. Log in as `SEAFILE_ADMIN_EMAIL` / `SEAFILE_ADMIN_PASSWORD`
5. **System Admin → Settings**:
   - SERVICE_URL: `https://drive.yourdomain.com`
   - FILE_SERVER_ROOT: `https://drive.yourdomain.com/seafhttp`

## Behind NPM + Cloudflare

In NPM:
- Domain: `drive.yourdomain.com`
- Forward to: `192.168.50.178:7777`
- Websockets: ✅
- **Custom Nginx config** (Advanced tab):
  ```nginx
  client_max_body_size 0;        # allow huge uploads
  proxy_request_buffering off;
  ```

In Cloudflare Tunnel:
- Hostname: `drive.yourdomain.com` → `http://192.168.50.178:7777`
- **Disable chunked encoding** under HTTP settings

## Desktop client

Download from [seafile.com/download](https://www.seafile.com/en/download/).

- Server: `https://drive.yourdomain.com`
- Email/password: your Seafile login
- Create a library, drag a folder in, watch it sync

## Backup

Two things to back up:
1. **Library data**: `/mnt/drive1/seafile/shared/seafile-data/`
2. **MariaDB**: `/mnt/drive1/seafile/mysql/`

Best practice is a hot DB dump:

```bash
docker exec big-bear-seafile-db \
  mysqldump -uroot -p"$DB_ROOT_PASSWD" --all-databases \
  > /mnt/toshiba/backups/seafile/seafile-$(date +%F).sql
```

---

## Next

→ [11 — Ghost blog](11-ghost.md)
