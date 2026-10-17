"""List drills whose media no longer exists: paths like /media/audio/x.webm were
served from the backend's own disk, which on Render is ephemeral — the files
disappeared with a redeploy. The text survives; the speaker's voice does not.

Usage (read-only, against any backend):
    python tools/find_dead_media.py --api https://tachelhit-drills-api.onrender.com
    python tools/find_dead_media.py --api ... --check     # also HEAD each URL (slow, exact)
    python tools/find_dead_media.py --api ... --json dead.json

Nothing is modified. The list is for the owner: those drills need a new
recording ("Veus" in the app, stored on Cloudinary), or their dead URLs cleared
so the app stops trying to download them (the offline sync logs a 404 each).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FIELDS = ("audio_url", "video_url", "image_url", "audio_tts_url", "audio_tts_shi_url")


def head_ok(url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as r:
            return 200 <= r.status < 400
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", required=True)
    ap.add_argument("--check", action="store_true", help="HEAD every relative URL instead of assuming it is dead")
    ap.add_argument("--json", metavar="FILE")
    args = ap.parse_args()
    api = args.api.rstrip("/")
    rows = json.load(urllib.request.urlopen(f"{api}/drills/", timeout=180))
    dead = []
    for r in rows:
        bad = []
        for f in FIELDS:
            u = (r.get(f) or "").strip()
            if not u:
                continue
            if u.startswith("/") or u.startswith("blob:") or u.startswith("file:") or u.startswith("capacitor:"):
                if args.check and u.startswith("/") and head_ok(api + u):
                    continue
                bad.append((f, u))
        if bad:
            dead.append({"id": r["id"], "text_tachelhit": r.get("text_tachelhit"), "text_catalan": r.get("text_catalan"),
                         "author": r.get("author"), "dead": bad,
                         "has_cloud_audio": bool((r.get("audio_tts_shi_url") or "").startswith("http") or (r.get("audio_url") or "").startswith("http"))})
    print(f"{len(dead)} of {len(rows)} drills reference media that no longer exists")
    by_field = {}
    for d in dead:
        for f, _ in d["dead"]:
            by_field[f] = by_field.get(f, 0) + 1
    print("by field:", by_field)
    for d in dead[:15]:
        print(f"#{d['id']:<6} {', '.join(f for f, _ in d['dead']):<28} {str(d['text_tachelhit'])[:30]!r:<34} by {d['author']}")
    if len(dead) > 15:
        print(f"... and {len(dead) - 15} more")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(dead, fh, ensure_ascii=False, indent=1)
        print("written", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
