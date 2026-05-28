# 07 — Immich (Photos)

[Immich](https://immich.app) is a self-hosted Google Photos alternative — automatic phone backup, face recognition, object/text search, multi-user albums.

## Stack

Immich is **four containers** working together:

| Container | Image | Role |
|-----------|-------|------|
| `immich-server` | `altran1502/immich-server:v2.5.3` | API + web UI + uploader |
| `immich-machine-learning` | `altran1502/immich-machine-learning:v2.5.3` | Face/object/CLIP search |
| `immich-postgres` | `tensorchord/pgvecto-rs:pg14-v0.2.0` | DB with vector extension |
| `immich-redis` | `redis:6.2-alpine` | Cache + job queue |

All four live on a single Docker network called `immich`.

## Storage

| Path on host | What's there |
|--------------|--------------|
| `/mnt/drive1/Photos/` | Your actual photos + videos (~uploads/) |
| `/DATA/AppData/immich/pgdata/` | Postgres data |
| `/DATA/AppData/immich/redis/` | Redis persistence |
| `/DATA/AppData/immich/model-cache/` | Downloaded ML models |

**Back up `/DATA/AppData/immich/pgdata` along with `/mnt/drive1/Photos`** — otherwise you lose all face groupings, albums, and metadata even if the photo files survive.

## Hardware acceleration (RK3588)

The CM5388's RK3588 has a Mali GPU + NPU. The compose file passes these devices into `immich-server`:

```yaml
devices:
  - /dev/dri:/dev/dri              # GPU
  - /dev/mpp_service:/dev/mpp_service   # Rockchip MPP encoder
  - /dev/dma_heap:/dev/dma_heap
  - /dev/rga:/dev/rga              # 2D acceleration
group_add:
  - video
privileged: true
```

After install, in Immich → **Administration → Settings → Video Transcoding**:
- Hardware acceleration: **Rockchip MPP**
- Hardware decoding: ✅

For ML acceleration on the NPU, leave **Administration → Settings → Machine Learning → Device** at `cpu` for now — RKNN support in Immich is still experimental as of v2.5. CPU works fine on the RK3588 for the volume an individual library throws at it.

## Install

Use [`compose/immich.yml`](../compose/immich.yml) or install via CasaOS app store.

```bash
mkdir -p /DATA/AppData/immich/{pgdata,redis,model-cache}
chown -R 1000:1000 /mnt/drive1/Photos
```

Bring it up, then visit `http://<homelab-ip>:2283` and create the admin account.

## Mobile app

Install **Immich** from App Store / Play Store. Server URL: `https://photos.yourdomain.com` (via Cloudflare Tunnel) or the Tailscale hostname.

Turn on **Auto-backup** — phones will dump photos straight to `/mnt/drive1/Photos/upload/<user>/`.

## Expose via Cloudflare Tunnel

In your Cloudflare Tunnel dashboard:
- Hostname: `photos.yourdomain.com`
- Service: `http://192.168.50.178:2283`
- **Additional application settings → HTTP → Disable chunked encoding**: ✅ (required for large uploads)

## Performance tuning

- **Postgres tuning** — the compose file already sets `shared_buffers=512MB`, `max_wal_size=2GB`, vector preload. Good defaults for 16 GB RAM.
- **External library** — if you have a giant existing photo collection, mount it read-only as an **external library** instead of importing. Settings → External libraries → add path.
- **CLIP model** — by default Immich uses `ViT-B-32__openai`. For better search, switch to `ViT-L-14__openai` (slower, much better results) under Settings → Machine Learning.

---

## Next

→ [08 — Music](08-music.md)
