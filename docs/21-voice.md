# 21 — Local Voice Assistant (Home Assistant Assist)

A private, low-cost voice assistant for Home Assistant on the repurposed **Echo Show 8**
(LegionOS / Android, running [View Assist](https://github.com/dinki/View-Assist) as the
front-end). Local speech in/out, **Gemini Flash** as the conversation brain. Replaces the
Nabu Casa cloud STT/TTS so the subscription can be dropped.

> **Goal & status:** see the checklist at the bottom. This doc doubles as the build log.

## Architecture

```
Echo Show 8 (LegionOS + View Assist)
        │  mic / speaker
        ▼
Home Assistant "Assist" pipeline
   ├─ STT  → faster-whisper  (Wyoming, 127.0.0.1:10300)   [local]
   ├─ brain→ Home Assistant intents first  →  Gemini Flash fallback  [local + cloud]
   └─ TTS  → piper           (Wyoming, 127.0.0.1:10200)   [local]
        │
        └─ (stretch) agentic jobs → Hermes via MCP
```

- **Why local STT/TTS:** drops the ~$6.50/mo Nabu Casa sub (remote access is already covered
  by Cloudflare Tunnel + Tailscale), keeps voice on-box/private.
- **Why Gemini for the brain, not local:** the RK3588 can run a small LLM but it's slow and
  weak at device control; Gemini Flash is ~$2/mo at this volume and far better. Device
  commands are still handled by HA's **local** intent engine first — Gemini only catches the
  fuzzy/Q&A requests.

## STAGE 1 — local STT/TTS (DONE)

Both run as one CasaOS stack, [`compose/wyoming-voice.yml`](../compose/wyoming-voice.yml):

| Container | Image | Wyoming port | Model |
|-----------|-------|--------------|-------|
| `faster-whisper` | `lscr.io/linuxserver/faster-whisper` | 10300 | `base-int8` (en) |
| `piper` | `lscr.io/linuxserver/piper` | 10200 | `en_US-lessac-medium` |

- Data: `/mnt/drive1/AppData/{faster-whisper,piper}` → `/config` (model caches).
- HA is `network_mode: host`, so it reaches both at `127.0.0.1`. Verified "Ready" + ports
  listening. If Whisper feels slow on the RK3588, drop `WHISPER_MODEL` to `tiny-int8`.

## STAGE 2 — wire into HA  ⏳ (needs the HA UI — owner step)

All of this is in the HA web UI at `http://192.168.50.178:8123`. Config was backed up first
to `/mnt/drive1/AppData/_ha-config-backups/` (critical-infra guardrail).

**2a. Add the two Wyoming engines**
- Settings → Devices & Services → **Add Integration** → **Wyoming Protocol**
  - Host `127.0.0.1`, Port `10300`  → registers faster-whisper (STT)
  - Add it again: Host `127.0.0.1`, Port `10200`  → registers piper (TTS)

**2b. Add the Gemini brain**
- Settings → Devices & Services → **Add Integration** → **Google Generative AI**
- Paste a Gemini API key. The existing one is on the box at
  `/mnt/drive1/AppData/hermes/hermes.env` (`GEMINI_API_KEY=`) — **but** it shares Hermes'
  free-tier quota. For reliability, generate a *separate* key (or enable billing) so HA voice
  and Hermes don't fight over the same daily limit. Set a **spend cap** in Google AI
  Studio / Cloud billing (target ≈ $2/mo, hard ceiling ~$10).
- In the integration options, pick a **Flash** model and **"Prefer handling commands
  locally"** (so "turn on the lights" stays on HA's local intents; Gemini only handles the
  rest). Expose the entities/areas you want it to control.

## STAGE 3 — the Assist pipeline + wake word  ⏳ (owner step)

- Settings → Voice assistants → **Add assistant** (or edit the existing one):
  - Conversation agent: **Google Generative AI** (with local-first as set above)
  - Speech-to-text: **faster-whisper**
  - Text-to-speech: **piper**
  - Wake word: add **openWakeWord** if you want hands-free (needs a `wyoming-openwakeword`
    container — see Stage 5).
- Point **View Assist** on the Show at this pipeline; verify a spoken reply comes back.

## STAGE 4 — decommission Nabu Casa  ⏳ (owner step)

Once Stages 2–3 verify: switch the default pipeline off the `home_assistant_cloud`
STT/TTS engines, confirm nothing else depends on Nabu Casa, then cancel the subscription.

## STAGE 5 — stretch goals (later)

- **Wake word:** add `wyoming-openwakeword` to the CasaOS stack (port 10400), register via
  Wyoming, select in the pipeline.
- **Hermes via MCP:** expose Hermes' tools as an MCP server and add HA's MCP Client
  integration, so a voice command can trigger agentic homelab jobs ("add a to-do",
  "download X"). Hermes ships `mcp_serve.py`.

## Done-when checklist

- [x] **1. Local STT/TTS live** — faster-whisper :10300 + piper :10200 running, models loaded.
- [ ] **1b.** Both added to HA via the Wyoming integration (Stage 2a — owner).
- [ ] **2. Brain = Gemini Flash** — Google Generative AI agent, local-first, key + spend cap (Stage 2b — owner).
- [ ] **3. Smart-home control by voice** — WiZ lights + Music Assistant respond, local/fast.
- [ ] **4. General Q&A** — answered via Gemini.
- [ ] **5. Hands-free on the Show** — wake word → Assist → spoken reply (Stages 3 + 5).
- [ ] **6. Homelab reach (stretch)** — an agentic task routed to Hermes via MCP.
- [ ] **7. Subscription killed** — Nabu Casa STT/TTS decommissioned, sub cancelled.
- [x] **8. Documented + pushed** — this doc + journal; `wyoming-voice` in CasaOS.
