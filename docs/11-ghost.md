# 11 — Ghost Blog

[Ghost](https://ghost.org) — open-source publishing platform. Used here as a personal blog.

## Stack

| Container | Image | Purpose |
|-----------|-------|---------|
| `ghost` | `ghost:5-alpine` | The blog itself |
| `ghost-db` | `mysql:8.0` | Database |

Both live on `ghost-network` (internal bridge).

## Install

[`compose/ghost.yml`](../compose/ghost.yml).

```bash
mkdir -p /DATA/AppData/ghost/{config,mysql}
```

Fill in passwords in the compose file:

```yaml
ghost:
  environment:
    database__connection__password: CHANGE_ME_GHOST_DB_PASSWORD
    url: https://blog.yourdomain.com    # ← your public URL

ghost-db:
  environment:
    MYSQL_PASSWORD: CHANGE_ME_GHOST_DB_PASSWORD       # ← must match above
    MYSQL_ROOT_PASSWORD: CHANGE_ME_GHOST_ROOT_PASSWORD
```

Generate strong passwords:
```bash
openssl rand -base64 24
```

## First boot

1. `docker compose up -d`
2. Wait ~30 seconds for MySQL to init
3. Visit `http://<homelab-ip>:2368/ghost` to set up the admin account

## The `url` environment variable matters

Ghost bakes the `url` value into every generated link — feeds, sitemaps, OG tags, etc. **Set it to the final public URL** before publishing any posts. Changing it later requires rewriting URLs across the database.

## Behind NPM + Cloudflare

In NPM:
- Domain: `blog.yourdomain.com`
- Forward to: `192.168.50.178:2368`
- **SSL** → Request Let's Encrypt cert
- Websockets: ✅

In Cloudflare Tunnel (alternative — pick one path or chain them):
- Hostname: `blog.yourdomain.com` → `http://192.168.50.178:2368`

## Mail (for newsletters)

Ghost can email newsletters. Add SMTP config to `/DATA/AppData/ghost/config/config.production.json`:

```json
{
  "mail": {
    "transport": "SMTP",
    "options": {
      "service": "Mailgun",
      "host": "smtp.mailgun.org",
      "port": 465,
      "secureConnection": true,
      "auth": {
        "user": "postmaster@yourdomain.com",
        "pass": "CHANGE_ME_MAILGUN_PASS"
      }
    }
  }
}
```

Restart Ghost: `docker restart ghost`.

## Backup

```bash
# Content (uploaded images, themes, settings):
rsync -a /DATA/AppData/ghost/config/ /mnt/toshiba/backups/ghost/content/

# Database:
docker exec ghost-db mysqldump -uroot -p"$ROOT_PASSWD" ghost \
  > /mnt/toshiba/backups/ghost/ghost-$(date +%F).sql
```

---

## Next

→ [12 — Recyclarr](12-recyclarr.md)
