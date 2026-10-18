"""Copy captured drills from the local backend to production, and fill the catalog
fields (source title / channel / playlist, variety, licence) on drills that already
live there. Media is on Cloudinary, so only the rows travel.

    python tools/sync_drills_to_prod.py --tags conte-eriçó-i-llop,inerzaf-r12            # dry run
    python tools/sync_drills_to_prod.py --tags conte-eriçó-i-llop,inerzaf-r12 --apply
    python tools/sync_drills_to_prod.py --catalog --apply      # fill catalog fields on prod from local twins

Idempotent: a local drill is skipped when production already has a drill with the same
source_url + video_start_time + Tachelhit text (or, without a source, the same tag +
Catalan + Tachelhit). Production must run code that knows the source_* columns
(PR #80 or later), otherwise those fields are silently dropped by the API.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FIELDS = ["tag", "author", "text_catalan", "text_tachelhit", "text_arabic", "audio_url", "audio_tts_url",
          "audio_tts_shi_url", "video_url", "image_url", "is_correction_dataset", "video_start_time",
          "video_end_time", "text_tachelhit_latin", "text_tachelhit_suggested", "text_catalan_suggested",
          "variety", "region", "speaker", "source_url", "source_title", "source_channel", "source_playlist",
          "license", "verified"]
CATALOG = ["source_url", "source_title", "source_channel", "source_playlist", "variety", "license"]


def get(url):
    return json.load(urllib.request.urlopen(url, timeout=180))


def send(url, method, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method=method,
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=180))


def key(d):
    if d.get("source_url"):
        return ("src", d["source_url"], round(float(d.get("video_start_time") or 0), 1), (d.get("text_tachelhit") or "").strip())
    return ("txt", d.get("tag") or "", (d.get("text_catalan") or "").strip(), (d.get("text_tachelhit") or "").strip())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--local", default="http://127.0.0.1:8000")
    ap.add_argument("--prod", default="https://tachelhit-drills-api.onrender.com")
    ap.add_argument("--tags", help="comma-separated local tags to copy")
    ap.add_argument("--catalog", action="store_true", help="fill missing catalog fields on prod from local twins")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    local = get(f"{a.local.rstrip('/')}/drills/")
    prod = get(f"{a.prod.rstrip('/')}/drills/")
    print(f"local {len(local)} drills, prod {len(prod)} drills; prod knows source_title: {'source_title' in prod[0] if prod else '?'}")
    prod_by_key = {key(d): d for d in prod}

    if a.tags:
        tags = {t.strip() for t in a.tags.split(",") if t.strip()}
        rows = [d for d in local if (d.get("tag") or "") in tags]
        rows.sort(key=lambda d: (d.get("tag") or "", d.get("source_url") or "", float(d.get("video_start_time") or 0), d["id"]))
        new = [d for d in rows if key(d) not in prod_by_key]
        print(f"{len(rows)} local drills in {sorted(tags)}; {len(rows) - len(new)} already on prod; {len(new)} to create")
        for d in new:
            body = {k: d.get(k) for k in FIELDS if d.get(k) is not None}
            label = f"#{d['id']} [{d.get('video_start_time')}-{d.get('video_end_time')}] {(d.get('text_tachelhit') or '')[:30]!r} <- {(d.get('text_catalan') or '')[:30]!r}"
            if a.apply:
                created = send(f"{a.prod.rstrip('/')}/drills/", "POST", body)
                print(f"  created prod #{created['id']}  {label}")
            else:
                print(f"  would create  {label}")

    if a.catalog:
        local_by_text = {}
        for d in local:
            if d.get("source_url"):
                local_by_text.setdefault(((d.get("text_tachelhit") or "").strip(), d.get("source_url")), d)
        todo = []
        for p in prod:
            if not p.get("source_url"):
                continue
            twin = local_by_text.get(((p.get("text_tachelhit") or "").strip(), p["source_url"]))
            if not twin:
                continue
            patch = {k: twin.get(k) for k in CATALOG if twin.get(k) and not p.get(k)}
            if patch:
                todo.append((p, patch))
        print(f"catalog: {len(todo)} prod drills missing fields their local twin has")
        for p, patch in todo:
            if a.apply:
                send(f"{a.prod.rstrip('/')}/drills/{p['id']}", "PUT", patch)
                print(f"  updated prod #{p['id']}: {list(patch)}")
            else:
                print(f"  would update prod #{p['id']}: {patch}")


if __name__ == "__main__":
    main()
