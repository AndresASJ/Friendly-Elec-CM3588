# 17 — Hermes Agent

[Hermes Agent](https://github.com/NousResearch/hermes-agent) (Nous Research) — a
self-hosted autonomous AI agent with persistent memory, auto-generated skills, and a
messaging gateway. Reached over **Telegram**; brain is **Google Gemini 3.5 Flash**.
Installed 2026-06-02 (see [`journal/2026-06-02.md`](../journal/2026-06-02.md)).

## Stack

| Container | Image | Purpose |
|-----------|-------|---------|
| `hermes` | `hermes-agent:latest` (built locally) | Agent + Telegram gateway (`gateway run`) |
| `hermes-dashboard` | `hermes-agent:latest` | Web dashboard, **127.0.0.1:9119 only** |

Both use `network_mode: host` and share the data volume `/mnt/drive1/AppData/hermes`
→ `/opt/data`. Telegram runs in **long-polling** mode, so no inbound port / port-forward
is needed (works behind the LAN/NAT).

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

All config is injected via `env_file: /mnt/drive1/AppData/hermes/hermes.env`:

| Variable | What to set |
|----------|-------------|
| `GEMINI_API_KEY` | Google AI Studio key ([aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)) |
| `LLM_MODEL` | `google/gemini-3.5-flash` |
| `TELEGRAM_BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_ALLOWED_USERS` | Your numeric Telegram user ID (from [@userinfobot](https://t.me/userinfobot)) — **locks the bot to you** |
| `TELEGRAM_HOME_CHANNEL` | Chat for proactive/cron deliveries (usually your own ID) |

After editing the env file:

```bash
casaos-cli app-management restart hermes
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

## Verify

```bash
docker logs hermes 2>&1 | grep -i "telegram connected"   # gateway up
casaos-cli app-management list apps | grep hermes         # CasaOS sees it
```

Then message the bot in Telegram — a reply confirms the Gemini path end-to-end.
