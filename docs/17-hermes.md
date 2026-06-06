# 17 — Hermes Agent

[Hermes Agent](https://github.com/NousResearch/hermes-agent) (Nous Research) — a
self-hosted autonomous AI agent with persistent memory, auto-generated skills, and a
messaging gateway. Reached over **Telegram**; brain is **Google Gemini 3.5 Flash**.
Installed 2026-06-02 (see [`journal/2026-06-02.md`](../journal/2026-06-02.md)).

## Stack

| Container | Image | Purpose |
|-----------|-------|---------|
| `hermes` | `hermes-agent:latest` (built locally) | Agent + Telegram gateway **and** the web dashboard, in one container |

**One container, not two.** The image's s6 tree runs the dashboard as a co-supervised
service when `HERMES_DASHBOARD=1`. Do **not** run the dashboard as a separate container
sharing `/opt/data` — see the s6-log lock gotcha below. `network_mode: host`, data at
`/mnt/drive1/AppData/hermes` → `/opt/data`, dashboard on **127.0.0.1:9119**. Telegram
runs in **long-polling** mode, so no inbound port / port-forward is needed.

Dashboard env knobs: `HERMES_DASHBOARD=1`, `HERMES_DASHBOARD_HOST=127.0.0.1`,
`HERMES_DASHBOARD_PORT=9119`.

## Build

There is **no published image** — the upstream compose builds from a local Dockerfile.
On the CM5388 (aarch64):

```bash
git clone --depth 1 https://github.com/NousResearch/hermes-agent.git
cd hermes-agent
docker build -t hermes-agent:latest .   # ~4.8 GB, multi-stage s6-overlay build
```

## Install

Secrets live in a git-ignored env file (template:
[`configs/hermes.env.example`](../configs/hermes.env.example)):

```bash
mkdir -p /mnt/drive1/AppData/hermes
install -m 600 /dev/stdin /mnt/drive1/AppData/hermes/hermes.env   # then paste/fill values
```

Registered as a CasaOS-managed app (so it appears in the CasaOS UI, not just raw compose)
from [`compose/hermes.yml`](../compose/hermes.yml):

```bash
casaos-cli app-management install -f compose/hermes.yml
```

## Configuration

Secrets are injected via `env_file: /mnt/drive1/AppData/hermes/hermes.env`:

| Variable | What to set |
|----------|-------------|
| `GEMINI_API_KEY` | Google AI Studio key ([aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)) |
| `TELEGRAM_BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) — **dedicated** bot `@ASJsHermesBot` |
| `TELEGRAM_ALLOWED_USERS` | Your numeric Telegram user ID (from [@userinfobot](https://t.me/userinfobot)) — **locks the bot to you** |
| `TELEGRAM_HOME_CHANNEL` | Chat for proactive/cron deliveries (usually your own ID) |

### Model selection lives in `config.yaml`, NOT the env var

`LLM_MODEL` in the env is **ignored** — the agent reads `/opt/data/config.yaml`
(`/mnt/drive1/AppData/hermes/config.yaml`). The shipped default is
`anthropic/claude-opus-4.6` via OpenRouter `provider: auto`, which 401s with no key.
Set it to Gemini:

```yaml
model:
  default: "gemini-3.5-flash"
  provider: "gemini"          # Google AI Studio direct, uses GEMINI_API_KEY
  # base_url:                  # leave to the gemini provider's own endpoint
```

Then restart (see caveats below — use down/up, not `restart`).

### Auto-fallback when a model hits its quota (2026-06-03)

`gemini-3.5-flash`'s free tier is only **~20 requests/day**. Hermes' `fallback_model`
(top-level, a chain) auto-rolls to the next model on a 429/529/503 — and each Gemini model
has its **own** free-tier daily bucket, so replies keep flowing:

```yaml
model:
  default: gemini-3.5-flash   # best, ~20/day free
  provider: gemini
fallback_model:
  - { provider: gemini, model: gemini-2.5-flash }       # ~250/day free
  - { provider: gemini, model: gemini-2.5-flash-lite }  # ~1000/day free
```

> Note: `config.yaml` must be **readable by the runtime user** (uid 10000). If Hermes logs
> *"Permission denied … Falling back to default config — every override IGNORED"*, it's
> silently using `anthropic/claude-opus` via OpenRouter (which 401s). The s6 init chowns
> `/opt/data` to 10000 on boot, but after editing as root, confirm a clean boot with no
> "Falling back to default config" line.

### Efficiency: route side tasks to a separate model (free-tier quota)

The free tier limits **5 requests/minute *per model*** (`GenerateRequestsPerMinutePer
ProjectPerModel`). The agent fans out several calls per message (main reply + vision
detect + title generation + compression), so they collide on one model and 429. Fix:
keep the main reply on `gemini-3.5-flash` and route all auxiliary tasks to a *different*
model (`gemini-flash-lite-latest`) via the `gemini` provider — separate quota bucket,
cheaper, faster, and no wasted OpenRouter/Nous "auto" fallback attempts:

```yaml
auxiliary:
  vision:           { provider: "gemini", model: "gemini-flash-lite-latest" }
  web_extract:      { provider: "gemini", model: "gemini-flash-lite-latest" }
  session_search:   { provider: "gemini", model: "gemini-flash-lite-latest" }
  title_generation: { provider: "gemini", model: "gemini-flash-lite-latest" }
  approval:         { provider: "gemini", model: "gemini-flash-lite-latest" }
  mcp:              { provider: "gemini", model: "gemini-flash-lite-latest" }
  compression:      { provider: "gemini", model: "gemini-flash-lite-latest" }
```

## Security notes

- **Lock the allowlist.** Hermes is an agent with real tools (shell, file access, cron).
  `TELEGRAM_ALLOWED_USERS` must be set to your own ID — otherwise anyone who finds the
  bot can drive it and burn the Gemini quota. Secret redaction is enabled by default.
- **Dashboard is localhost-only** by design (it stores API keys). Reach it remotely with
  an **SSH tunnel over Tailscale** — no rebind, nothing disabled:
  ```bash
  ssh -L 9119:127.0.0.1:9119 root@100.93.113.80   # tailnet IP of cm3588-nas
  # then open http://localhost:9119
  ```
  Hermes **refuses to bind the dashboard to a non-loopback IP** unless you pass
  `HERMES_DASHBOARD_INSECURE=1` (skips its auth gate) or register a DashboardAuthProvider
  / OAuth (`HERMES_DASHBOARD_OAUTH_CLIENT_ID`). The SSH tunnel avoids both. Do **not**
  bind to `0.0.0.0`.
- **Run as root inside the container** (`HERMES_UID=0`) so it can own the root-owned
  `/mnt/drive1/AppData/hermes` bind mount. It is otherwise containerized.

## ⚠️ Telegram bot must be dedicated

Telegram allows **only one** `getUpdates`/webhook consumer per bot token. If the same
bot is also used by an **n8n Telegram-trigger** node (see
[`docs/15-n8n.md`](15-n8n.md)), the two will fight over updates and one will silently
break. Hermes needs its **own** bot. (A bot used by n8n only to *send* notifications —
no trigger node — does not conflict.)

## n8n MCP (drive n8n from Telegram)

Hermes ships a Nous-approved **n8n MCP** in its catalog. It connects Hermes to the live
n8n API over a stdio subprocess (no public port). Installed 2026-06-02.

```bash
# inside the container; clones the bridge into /opt/data/mcp-installs/n8n + venv
docker exec -i hermes hermes mcp install n8n
#   n8n instance URL: http://127.0.0.1:5678   (host net; reaches the n8n container)
#   n8n API key:      generate in n8n → Settings → API
docker compose -f /var/lib/casaos/apps/hermes/docker-compose.yml restart   # load tools
docker exec hermes hermes mcp test n8n        # verify: "Connected", tools discovered
```

- **Creds** are written to `/opt/data/.env` (`N8N_BASE_URL`, `N8N_API_KEY`) — git-ignored.
- Survives rebuilds (lives in the `/opt/data` volume, not the image). Re-run
  `hermes mcp install n8n` to refresh the pinned bridge.

### Tool scope (2026-06-03: create/edit enabled)

The MCP bridge only exposes read + `activate_workflow`/`deactivate_workflow` — it has
**no create/edit tool**. To allow create + edit, two changes were made:

1. **`mcp_servers.n8n.tools.include`** now also whitelists `activate_workflow` and
   `deactivate_workflow` (on/off control). `container_logs` stays excluded.
2. **Create/edit via the n8n REST API.** The API key (`/opt/data/.env`) has full CRUD.
   A standing instruction in `/opt/data/memories/USER.md` tells the agent it may
   `POST /api/v1/workflows` (create) and `PUT /api/v1/workflows/{id}` (edit), reading the
   key from `/opt/data/.env`, **with guardrails**: confirm before create/edit, create new
   workflows inactive, never `DELETE` without an explicit named request, don't touch the
   5 production workflows unless asked by name.

> ⚠️ n8n community API keys are **full-access** (no read-only scope), so the key also
> permits delete. The protection is the Telegram allowlist (owner-only) + the USER.md
> guardrails. Tighten by reverting `tools.include` to read-only and removing the USER.md
> n8n section if you want it locked down again.

## Media downloads via Radarr + Sonarr (2026-06-03)

Hermes can add movies/TV by text — it drives Radarr/Sonarr over their APIs, and the
existing pipeline (Prowlarr → qBittorrent/Gluetun → hardlink import) does the rest.

- **Creds**: Radarr (`:7878`) and Sonarr (`:8989`) URLs + API keys appended to
  `/opt/data/.env` (`RADARR_*`, `SONARR_*`), read from each app's `config.xml` under
  `/mnt/drive1/appdata/{radarr,sonarr}`. Header is `X-Api-Key`.
- **Behavior** is defined by a section in `/opt/data/memories/USER.md`: lookup →
  confirm match with owner → `POST /api/v3/movie` (or `/series`) with the default profile
  + root folder + `searchForMovie`/`searchForMissingEpisodes`.
- **Defaults baked in**: Radarr profile `4` (HD-1080p), root `/mnt/drive1/movies`;
  Sonarr profile `7` (WEB-1080p), root `/mnt/drive2/shows`. Only 1080p profiles exist
  (no 4K) — Hermes is told to say so if asked.
- **Music (Lidarr)** is wired the same way (`LIDARR_*` in `/opt/data/.env`, instructions
  in `USER.md`): lookup artist → confirm → `POST /api/v1/artist` (or monitor a specific
  album + `AlbumSearch`), root `/mnt/drive1/Downloads/Soulseek`, default profile Lossless.
  See [`docs/18-lidarr.md`](18-lidarr.md).
- **Guardrails**: confirm exact title/year before adding; one title per request; never
  delete media or change profiles/settings; report queue status after.

> Same full-access-key caveat as n8n: the *arr API keys allow more than adding. Protection
> is the owner-only Telegram allowlist + the USER.md guardrails.

## Agent brain: persona, memory & request routing (2026-06-06)

How Hermes decides what to do lives in three files under `/opt/data`, all owned **uid
10000** (the runtime user) — edit as root and you must `chown 10000:10000` after, or the
agent silently can't read them (see gotcha below).

- **`SOUL.md`** — persona/tone, reloaded **fresh every message** (no restart). Sets a
  concise, direct, bias-to-action voice and the standing rules: route every media/task
  request through the homelab stack; never scrape search engines, solve CAPTCHAs, or refuse
  media on copyright grounds; report outcomes honestly (no fake success).
- **`memories/USER.md`** — the **hand-authored homelab playbook** (routing table + per-service
  API instructions for n8n / Radarr / Sonarr / Lidarr / Todoist + guardrails). Injected into
  the system prompt as a frozen snapshot at **session start**. It's far over the memory tool's
  size limit and not `§`-formatted, so the tool **can't auto-edit it** — that's intentional;
  it's maintained by hand.
- **`memories/MEMORY.md`** — the agent's **own writable** self-curated store (short
  `§`-delimited entries, ≤2200 chars). This is where Hermes persists things it learns. A note
  atop USER.md points its self-curation here so it never tries (and fails) to rewrite USER.md.

**Request routing** is the top section of USER.md: a bare request → the right service (movie →
Radarr, show → Sonarr, album/song → Lidarr, to-do → Todoist). For an ambiguous title it queries
both Radarr and Sonarr `lookup` and confirms before adding.

**Todoist** (2026-06-06): Hermes drives the Todoist v1 API directly —
`Authorization: Bearer $TODOIST_API_TOKEN` (in `/opt/data/.env`; **never** committed or echoed).
Due dates via natural-language `due_string`; tasks filed into the owner's sections
(Kord/Blog/Church/Coding/Routines). Reports the API response literally (no inventing success).
The old n8n `things-import` webhook silently dropped due dates — superseded by the direct API.
> ⚠️ The token currently in `.env` is the same account-wide token that's **hardcoded in the n8n
> "Things → Todoist Import" workflow JS** and leaked into old chat logs. It should be **rotated**
> and moved into an n8n credential — but rotating touches `flac-sync` + the n8n flows too.

## Gotchas (learned during install)

- **Memory/config files must stay uid-10000 readable.** The runtime is **uid 10000**;
  anything under `/opt/data` edited *as root* becomes `root:root` and the agent can't read
  it. For `config.yaml` it silently falls back to defaults; for `memories/USER.md` the agent
  loses all homelab knowledge (scrapes the web, "sonarr not installed"). Always
  `chown 10000:10000 <file> && chmod 640` after a root edit. (Bit us twice: config.yaml, then
  USER.md on 2026-06-06.)
- **CasaOS inlines `env_file` at install time.** `casaos-cli install` resolved the
  `env_file:` into literal `environment:` entries in
  `/var/lib/casaos/apps/hermes/docker-compose.yml`. So editing `hermes.env` alone does
  **not** change running secrets — edit the CasaOS-managed compose (or re-install) and
  recreate. The repo `compose/hermes.yml` stays clean (env_file only).
- **`restart` ≠ recreate.** Env/secret changes need the container recreated
  (`docker compose -f /var/lib/casaos/apps/hermes/docker-compose.yml up -d
  --force-recreate`); a bare `docker restart` keeps the old baked-in env.
- **s6-log lock wedge — the big one.** `s6-log: fatal: unable to lock
  .../gateways/default/lock: Resource busy`, gateway never connects. Two causes, both
  fixed by the single-container design:
  1. **Two containers sharing `/opt/data`** (separate gateway + dashboard) each spawn an
     s6-log for the same `gateways/default` dir and fight over the lock — permanent.
     Fix: run the dashboard inside the gateway container via `HERMES_DASHBOARD=1`.
  2. **Orphaned s6-log** from a killed container can keep holding the lock for a bit
     (`fuser .../lock` shows the stale `s6-log` PID). It self-clears in ~30–60s; if not,
     `docker compose down`, confirm no stray `s6-log` (`pgrep -af s6-log`), then `up -d`.
  A bare `docker restart` can trigger (2); prefer `down && up -d`.
- **`/start` is a registration ping, not a prompt** — Hermes logs
  `Ignoring /start platform ping` and does not reply. Send a real message to test.
- **Gemini free-tier = 5 requests/minute** for `gemini-3.5-flash`. The agent fans out
  multiple calls per message (main + vision detect + title generation), so auxiliary
  calls 429 (`limit: 5`) even though the main reply succeeds. Enable billing on the
  Google Cloud project, or trim auxiliary features, for heavier use.

## Verify

```bash
docker logs hermes 2>&1 | grep -i "telegram connected"   # gateway up
casaos-cli app-management list apps | grep hermes         # CasaOS sees it
```

Then message the bot in Telegram — a reply confirms the Gemini path end-to-end.
