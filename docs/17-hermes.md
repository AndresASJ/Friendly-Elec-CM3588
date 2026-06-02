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
- **Dashboard is localhost-only** by design (it stores API keys). For remote access,
  add an authenticated NPM proxy host → `127.0.0.1:9119`; do **not** bind it to `0.0.0.0`.
- **Run as root inside the container** (`HERMES_UID=0`) so it can own the root-owned
  `/mnt/drive1/AppData/hermes` bind mount. It is otherwise containerized.

## ⚠️ Telegram bot must be dedicated

Telegram allows **only one** `getUpdates`/webhook consumer per bot token. If the same
bot is also used by an **n8n Telegram-trigger** node (see
[`docs/15-n8n.md`](15-n8n.md)), the two will fight over updates and one will silently
break. Hermes needs its **own** bot. (A bot used by n8n only to *send* notifications —
no trigger node — does not conflict.)

## Gotchas (learned during install)

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
