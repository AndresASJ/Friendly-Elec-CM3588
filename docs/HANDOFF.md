# Handoff — n8n automation + Todoist/contacts (as of 2026-05-31)

Everything built in this stretch, where it lives, how to operate it, and what's
still open. Full narrative is in `journal/2026-05-29.md` and `journal/2026-05-31.md`;
service details in `docs/15-n8n.md`.

---

## 1. What exists now

**n8n** (CasaOS app, compose at `/var/lib/casaos/apps/n8n/`)
- Backend migrated **SQLite → PostgreSQL** (`n8n-postgres` container, on the
  `n8n_default` docker network; no host port published).
- Reverse-proxied at `https://n8n.asj.media` — **LAN-only** (AdGuard rewrite + NPM;
  not public). This is why all triggers are inbound-from-LAN or outbound-polling,
  never inbound-from-internet.

**Active workflows** (n8n REST: activate via `POST /rest/workflows/<id>/activate`
with a `versionId` body — `PATCH active:true` silently no-ops):

| Workflow | ID | Trigger | Does |
|---|---|---|---|
| New Media → Telegram | `7o9QYSRy2zTWulS6` | webhook `/webhook/media-added` | Sonarr/Radarr import → Telegram |
| Torrent Done → Telegram | `vwf32DYBUuWosw38` | webhook `/webhook/torrent-done` | qBit completion → Telegram |
| Disk Guard → Telegram | `LTZCtH8lwn0uBUJK` | webhook `/webhook/disk-report` | drive >85% alert (host cron feeds it) |
| Soulseek Done → Telegram | `3EnwgGNZMNkK0S7Z` | schedule 5 min | slskd new downloads → Telegram |
| Todo Capture → Todoist | `r5gc1hgtCyimoN5v` | schedule 1 min (Telegram poll) | text bot → Gemini → Todoist task (+contact links) |
| Things → Todoist Import | `EsEMth8aREpDrYcn` | webhook `/webhook/things-import` | one-time Things migration (done) |

**Telegram bot:** `@ASJNOTI_BOT` ("ASJ Noti"). Sends all alerts; also *receives*
todos for the capture bot (via outbound `getUpdates` polling, not a webhook).

**Todoist:** capture bot + mirrors live here. Structure is **Inbox + Sections**
(Kord, Blog, Church, Coding, Routines) — free plan caps at 5 projects, so we use
sections/labels, not projects.

**FlacPlayer:** the 78 open items from the private `AndresASJ/FlacPlayer` repo's
`TODO.md` are mirrored into Todoist (label `FlacPlayer`, in the **Kord** section),
one-way (file = source of truth), hourly.

**Smart capture:** texting "call hendrix later" → task "Call Hendrix" with
tap-to-`tel:`/`sms:` links, number looked up from iCloud contacts (CardDAV).

---

## 2. Cron jobs (root crontab)

```
*/5  * * * *  gluetun-qbit port update           (pre-existing)
*/30 * * * *  /usr/local/bin/n8n-disk-report.sh   -> feeds Disk Guard webhook
7    * * * *  /usr/local/bin/flacplayer-todo-sync.py  -> FlacPlayer TODO.md -> Todoist
0    4 * * *  /usr/local/bin/contacts-sync.py      -> iCloud contacts -> Postgres `contacts`
```

Host scripts also tracked in the repo under `scripts/`.

---

## 3. Secrets — where they live (NONE in the repo)

| Secret | Location |
|---|---|
| n8n encryption key | pinned in compose env + `/mnt/drive1/AppData/n8n/config` |
| Postgres password | n8n compose env; n8n "n8n Postgres (contacts)" credential |
| Telegram bot token | n8n "Telegram - ASJ Noti bot" credential (+ in capture getUpdates URL) |
| Gemini API key | n8n "Gemini API key" credential (`gemini-3.5-flash`, AI Studio free tier) |
| Todoist API token | n8n "Todoist API" credential **and** `/root/.config/flac-sync/todoist.token` |
| slskd API key | n8n credential + `slskd.yml` (private-net CIDR) |
| Proton SMTP token | n8n "Proton SMTP" credential (from the abandoned Things-email path) |
| iCloud app-specific pw | `/mnt/drive1/AppData/contacts-sync/icloud.cred` (chmod 600) |

Repo exports are sanitized (`CHANGE_ME`); every push is secret-scanned.
**Note:** the user's *main* Apple ID password was shared in chat during setup and
should be rotated (the app-specific one is what's actually used).

---

## 4. How to operate / verify

- **n8n API from the box:** login `POST /rest/login` with the owner creds, then
  use `/rest/workflows`, `/rest/executions?filter={"workflowId":"…"}`, etc.
  Execution data is **flatted**-encoded JSON (custom decode needed).
- **Capture bot test:** text `@ASJNOTI_BOT` a todo; it processes **one per minute**
  and only marks a message read *after* the Todoist task is created (no loss/dupes).
- **FlacPlayer sync:** `/usr/local/bin/flacplayer-todo-sync.py` — idempotent
  (re-run = `created=0 completed=0`). File is source of truth.
- **Contacts:** `/usr/local/bin/contacts-sync.py` rebuilds the `contacts` table;
  verify with `docker exec n8n-postgres psql -U n8n -d n8n -c "select count(*) from contacts;"`

---

## 5. Hard-won gotchas (don't relearn these)

- **n8n image is hardened:** no Execute Command node; Code node can't `require`/read
  fs. → host scripts do OS-level work and feed n8n via webhook or Postgres.
- **n8n expression `}}` collision:** building JSON inline as `={{ JSON.stringify({…}) }}`
  breaks on nested `}}`. Build the body string in a Code node, reference it.
- **Telegram offset:** advance it only *after* the task is created (final node), else
  rate-limited/failed messages are silently lost.
- **Todoist strips `@word`/`#word`** from task content (label/project syntax) →
  backslash-escape them; match by an `fpid:<hash>` in the description, not the title.
- **Todoist API moved to `/api/v1/`** (the old `/rest/v2/` is 410). Paginates 50/page
  via `next_cursor`.
- **Gemini:** the consumer subscription has no API — use an AI Studio **API key**.
  `gemini-3.5-flash` is current.
- **Apple/iCloud:** Things has no API (used iPhone Shortcut for the migration);
  contacts reachable via CardDAV with an **app-specific** password (partition host
  like `p141-contacts.icloud.com` discovered at runtime).
- **n8n-postgres has no host port** → write to it from host scripts via `docker exec`.

---

## 6. Open items / next steps

- ⚠️ **drive2 is 100% full (~8 GB free)** — genuine risk, untouched. Top priority.
- Add `/mnt/drive1/AppData/n8n-postgres/` (or a `pg_dump`) to `scripts/backup.sh`.
- Easy wins teed up: `email → mailto:` intent, then `directions → Maps`,
  `meet → calendar` (framework already in the capture flow).
- Optional: capture bot drain >1 msg/poll; Music Assistant rescan on Soulseek done.
- Rotate the Apple ID password (see §3).

---

## 7. Repo

`https://github.com/AndresASJ/Friendly-Elec-CM5388` (push via the box's `gh` auth).
Latest relevant commits: Postgres migration → 4 alert workflows → Todoist capture +
Things importer → FlacPlayer mirror → intent-aware capture (`6fc21ed`).
Workflow: every change → repo update + journal entry + push.
