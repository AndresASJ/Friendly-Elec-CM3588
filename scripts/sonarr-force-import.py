#!/usr/bin/env python3
"""
sonarr-force-import.py — force Sonarr to import a downloaded season/episode folder
EVEN WHEN it's "not an upgrade" (i.e. a deliberate quality DOWNGRADE).

Why this exists
---------------
Sonarr's quality ladder treats e.g. Bluray-1080p Remux as strictly better than
Bluray-1080p (x265). So if you deliberately re-grab a smaller x265 pack to RECLAIM
DISK over a fat Remux, automatic import refuses it:
    "Not an upgrade for existing episode file(s). Existing quality: Bluray-1080p
     Remux. New Quality Bluray-1080p."
The file then just sits in the download client, never replacing the Remux.

This script drives Sonarr's *manual* import API, which lets you override that
rejection. With --mode move it relocates the new file into the library, Sonarr
deletes the old (larger) file, and the space is reclaimed. (Use move when you don't
need to keep seeding the source — e.g. a public tracker where ratio doesn't matter.)

Usage
-----
  ./sonarr-force-import.py --series-id 31 --folder "/mnt/drive1/torrents/complete/SomePack"
  ./sonarr-force-import.py --series-id 31 --folder "..." --mode copy   # keep seeding
  ./sonarr-force-import.py --series-id 31 --folder "..." --dry-run     # show mapping only

The Sonarr API key is read (in order) from: --api-key, $SONARR_API_KEY, or the
Sonarr config.xml (default /mnt/drive1/appdata/sonarr/config.xml). Never hard-coded.

Real-world note: cross-app container DNS is broken on this box, so default base URL
uses the LAN IP (192.168.50.178), not a container name. See docs/06-downloads-vpn.md.
"""
import argparse, json, sys, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET

def read_key_from_config(path):
    try:
        return ET.parse(path).getroot().findtext("ApiKey")
    except Exception:
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--series-id", type=int, required=True)
    ap.add_argument("--folder", required=True, help="download folder containing the new files")
    ap.add_argument("--base-url", default="http://192.168.50.178:8989")
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--config", default="/mnt/drive1/appdata/sonarr/config.xml")
    ap.add_argument("--mode", choices=["move", "copy"], default="move",
                    help="move = reclaim space (breaks seeding); copy = keep seeding")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    import os
    key = args.api_key or os.environ.get("SONARR_API_KEY") or read_key_from_config(args.config)
    if not key:
        sys.exit("No API key (use --api-key, $SONARR_API_KEY, or a readable config.xml)")
    base = args.base_url.rstrip("/") + "/api/v3"

    def api(method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(base + path, data=data,
              headers={"X-Api-Key": key, "Content-Type": "application/json"}, method=method)
        return json.load(urllib.request.urlopen(req, timeout=120))

    qs = urllib.parse.urlencode({"folder": args.folder, "filterExistingFiles": "false"})
    mapped = api("GET", "/manualimport?" + qs)
    files = []
    for f in mapped:
        eps = f.get("episodes") or []
        path = str(f.get("path", ""))
        if not eps or not path.lower().endswith((".mkv", ".mp4", ".avi")):
            continue
        rej = [r.get("reason", "") for r in f.get("rejections", [])]
        print(f"  map {[ (e.get('seasonNumber'), e.get('episodeNumber')) for e in eps]} "
              f"{f.get('quality',{}).get('quality',{}).get('name','?')} :: {path.split('/')[-1][:48]}"
              + (f"  [override: {rej}]" if rej else ""))
        files.append({
            "path": path, "folderName": f.get("folderName", ""),
            "seriesId": args.series_id, "episodeIds": [e["id"] for e in eps],
            "quality": f["quality"], "languages": f.get("languages") or [{"id": 1, "name": "English"}],
            "releaseGroup": f.get("releaseGroup", ""), "indexerFlags": 0,
        })
    if not files:
        sys.exit("No importable video files mapped (already imported, or none found).")
    if args.dry_run:
        print(f"[dry-run] would import {len(files)} files via mode={args.mode}")
        return
    cmd = api("POST", "/command", {"name": "ManualImport", "importMode": args.mode, "files": files})
    cid = cmd["id"]
    print(f"ManualImport command {cid} ({args.mode}) -> {cmd['status']}")
    for _ in range(40):
        time.sleep(2)
        st = api("GET", f"/command/{cid}")
        if st["status"] in ("completed", "failed"):
            print("=>", st["status"]); return
    print("=> still running (check Sonarr Activity)")

if __name__ == "__main__":
    main()
