"""Production clean-up approved by the owner on 2026-10-18.

1. Every "(Tifinagh …)" bracket inside text_tachelhit is a pasted CA->Ta translation, not
   what the speaker said: move it to text_tachelhit_suggested, keep the spoken Latin.
2. Reviewed drills 616-645: replace junk ASR text, fix the Arabic of 618, blank the
   mismatched meaning of 620, delete the duplicate 645.

    python tools/clean_pasted_translations.py            # dry run
    python tools/clean_pasted_translations.py --apply
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = "https://tachelhit-drills-api.onrender.com"
BRACKET = re.compile(r"\s*\(([^()]*[ⴰ-⵿][^()]*)\)")

REVIEWED = {
    623: {"text_tachelhit": "nkki riɣ ad ẓrɣ tswira n lqum", "text_tachelhit_latin": "nkki riɣ ad ẓrɣ tswira n lqum"},
    625: {"text_tachelhit": "ar nnayɣ irumin", "text_tachelhit_latin": "ar nnayɣ irumin"},
    618: {"text_arabic": "عصير البرتقال"},
    # the Catalan/Arabic did not match the recording (it is about stones and soil); the speaker redoes it
    620: {"text_catalan": "", "text_arabic": "", "text_tachelhit_suggested": "nks as iẓran ar d iṭṭar wakal"},
}
DELETE = [645]  # same audio file and text as 628


def req(method, path, body=None):
    r = urllib.request.Request(API + path, data=json.dumps(body).encode() if body is not None else None,
                               method=method, headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=120))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    prod = req("GET", "/drills/")
    by_id = {d["id"]: d for d in prod}
    changes = []
    for d in prod:
        ta = d.get("text_tachelhit") or ""
        found = BRACKET.findall(ta)
        if not found:
            continue
        spoken = BRACKET.sub("", ta).strip()
        pasted = " / ".join(dict.fromkeys(x.strip() for x in found))  # dedupe, keep order
        patch = {"text_tachelhit": spoken}
        if not (d.get("text_tachelhit_suggested") or "").strip():
            patch["text_tachelhit_suggested"] = pasted
        changes.append((d["id"], patch, f"{ta!r} -> {spoken!r}  (suggestion: {pasted!r})"))
    for did, patch in REVIEWED.items():
        if did in by_id:
            changes.append((did, patch, f"reviewed: {patch}"))
    print(f"{len(changes)} updates, {len(DELETE)} deletions")
    for did, patch, label in changes:
        print(f"  #{did}: {label}")
        if a.apply:
            req("PUT", f"/drills/{did}", patch)
    for did in DELETE:
        if did in by_id:
            print(f"  delete #{did}: {by_id[did].get('text_catalan')!r} {by_id[did].get('text_tachelhit')!r}")
            if a.apply:
                req("DELETE", f"/drills/{did}")
    print("APPLIED" if a.apply else "dry run only")


if __name__ == "__main__":
    main()
