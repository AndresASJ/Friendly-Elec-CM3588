#!/usr/bin/env python3
# qBit old-torrent cleanup — homelab.
# Identifies torrents safe to remove and reclaim space, per the agreed policy:
#   (a) PUBLIC trackers (tv-sonarr, "radarr- Public"): complete + verified imported
#   (b) PRIVATE trackers (tv-sonarr-private, "radarr- Private"): ratio>=1.0 OR
#       seeded>=14d, AND verified imported  (keeps reward buffers until then)
#   (c) dead 0% stalledDL torrents
# Import = downloadId matches a "downloadFolderImported" event in Sonarr/Radarr
# history -> the library holds its own copy (there are NO hardlinks), so deleting
# the torrent's files is safe.
#
#   --report  (default) analyze only; write log + create a Todoist reminder task.
#   --apply              actually remove eligible torrents WITH files.
#   --from-cron          after a successful run, remove this job's own crontab line
#                        (one-shot reminder scheduled for 2026-06-14).
#
# Reads API keys from the *arr config.xml files (no secrets in this script / repo).
# qBit is reached via `docker exec qbittorrent curl 127.0.0.1:8090` (localhost auth
# bypass inside the VPN namespace). Installed by Claude 2026-05-31. See docs/15-n8n.md
# / docs/06-downloads-vpn.md.
import json, subprocess, sys, re, urllib.request, urllib.error, xml.etree.ElementTree as ET
from datetime import datetime

APPLY      = "--apply" in sys.argv
FROM_CRON  = "--from-cron" in sys.argv
LAN        = "192.168.50.178"
PRIV_CATS  = {"tv-sonarr-private", "radarr- Private"}
PUB_CATS   = {"tv-sonarr", "radarr- Public"}
RATIO_LIMIT = 1.0
SEED_LIMIT  = 14 * 86400          # seconds
LOG        = "/var/log/qbit-cleanup.log"
TODOIST_TOKEN_FILE = "/root/.config/flac-sync/todoist.token"
G = 1024 ** 3

def log(msg):
    line = f"{datetime.now().isoformat(timespec='seconds')}  {msg}"
    print(line)
    try:
        open(LOG, "a").write(line + "\n")
    except OSError:
        pass

def arr_key(path):
    try:
        return ET.parse(path).getroot().findtext("ApiKey")
    except Exception:
        return None

def http_get(url, key):
    req = urllib.request.Request(url, headers={"X-Api-Key": key})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def qbit(path, data=None):
    cmd = ["docker", "exec", "qbittorrent", "curl", "-s", "--max-time", "30",
           f"http://127.0.0.1:8090/api/v2/{path}"]
    if data:
        for k, v in data.items():
            cmd += ["--data-urlencode", f"{k}={v}"]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout
    return out

def imported_ids():
    ids = set()
    for host, conf in ((f"http://{LAN}:8989", "/mnt/drive1/appdata/sonarr/config.xml"),
                       (f"http://{LAN}:7878", "/mnt/drive1/appdata/radarr/config.xml")):
        key = arr_key(conf)
        if not key:
            log(f"WARN: no API key from {conf}")
            continue
        for pg in range(1, 16):
            try:
                d = http_get(f"{host}/api/v3/history?page={pg}&pageSize=250", key)
            except Exception as e:
                log(f"WARN: history fetch {host} pg{pg}: {e}")
                break
            recs = d.get("records", [])
            for r in recs:
                if r.get("eventType") == "downloadFolderImported" and r.get("downloadId"):
                    ids.add(r["downloadId"].upper())
            if pg * 250 >= d.get("totalRecords", 0):
                break
    return ids

def classify(torrents, ids):
    def imp(x): return x["hash"].upper() in ids
    pub = [x for x in torrents if x.get("category", "") in PUB_CATS
           and x.get("progress", 0) >= 1.0 and imp(x)]
    priv = [x for x in torrents if x.get("category", "") in PRIV_CATS and imp(x)
            and (x["ratio"] >= RATIO_LIMIT or x.get("seeding_time", 0) >= SEED_LIMIT)]
    dead = [x for x in torrents if x["state"] == "stalledDL" and x.get("progress", 0) < 1.0]
    return pub, priv, dead

def todoist(content, desc):
    try:
        tok = open(TODOIST_TOKEN_FILE).read().strip()
    except OSError as e:
        log(f"WARN: no Todoist token ({e}); skipping reminder task")
        return
    body = json.dumps({"content": content, "description": desc[:9000],
                       "labels": ["homelab"]}).encode()
    req = urllib.request.Request("https://api.todoist.com/api/v1/tasks", data=body,
                                 headers={"Authorization": "Bearer " + tok,
                                          "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            log(f"Todoist reminder created (HTTP {r.status})")
    except urllib.error.HTTPError as e:
        log(f"WARN: Todoist create failed HTTP {e.code}: {e.read().decode()[:200]}")

def remove(torrents):
    if not torrents:
        return
    hashes = "|".join(x["hash"] for x in torrents)
    qbit("torrents/delete", {"hashes": hashes, "deleteFiles": "true"})

def self_remove_cron():
    try:
        cur = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
        new = "".join(l for l in cur.splitlines(keepends=True) if "qbit-cleanup.py" not in l)
        subprocess.run(["crontab", "-"], input=new, text=True)
        log("Removed own crontab entry (one-shot reminder done).")
    except Exception as e:
        log(f"WARN: could not self-remove cron line: {e}")

def main():
    raw = qbit("torrents/info")
    try:
        torrents = json.loads(raw)
    except Exception:
        log(f"ERROR: could not read qBit torrents: {raw[:200]}")
        sys.exit(1)
    ids = imported_ids()
    pub, priv, dead = classify(torrents, ids)
    gb = lambda xs: sum(x.get("completed", 0) for x in xs) / G

    lines = [
        f"qBit cleanup {'APPLY' if APPLY else 'REPORT'} — {len(torrents)} torrents, "
        f"{len(ids)} imported IDs known",
        f"  PUBLIC complete+imported : {len(pub):>3}  {gb(pub):6.0f} GB",
        f"  PRIVATE >=1.0r or >=14d  : {len(priv):>3}  {gb(priv):6.0f} GB",
        f"  DEAD 0% stalled          : {len(dead):>3}  {gb(dead):6.0f} GB",
        f"  RECLAIMABLE TOTAL        :      {gb(pub)+gb(priv)+gb(dead):6.0f} GB",
    ]
    report = "\n".join(lines)
    for l in lines:
        log(l)

    if APPLY:
        remove(pub); remove(priv); remove(dead)
        log(f"APPLIED: removed {len(pub)+len(priv)+len(dead)} torrents with files.")
    else:
        todoist(f"Review qBit cleanup — ~{gb(pub)+gb(priv)+gb(dead):.0f} GB reclaimable",
                report + "\n\nRun `qbit-cleanup.py --apply` on the box to execute "
                         "(library keeps its copies; no hardlinks).")

    if FROM_CRON:
        self_remove_cron()

if __name__ == "__main__":
    main()
