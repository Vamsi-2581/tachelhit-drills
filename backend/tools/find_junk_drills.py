"""Find (and, only on explicit request, delete) junk drills left by auto-capture.

Auto-capture saved ASR output as Tachelhit even when the audio was English or
the model hallucinated repeated tokens ("R.R.R.R.R…", "la la la la"). This
tool lists those rows so the owner can decide; nothing is deleted unless
--delete is passed, and then only the ids that were listed.

Usage (from backend/, inside the venv):
    python tools/find_junk_drills.py                 # list, no changes
    python tools/find_junk_drills.py --json out.json # list + dump
    python tools/find_junk_drills.py --delete        # delete the listed ids

Works against the configured DATABASE_URL (SQLite drills.db by default).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sqlalchemy import create_engine, text as _t  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

# Same resolution as main.py, without importing the app (which starts it).
_url = os.getenv("DATABASE_URL", "sqlite:///drills.db")  # cwd-relative, same as main.py
if _url.startswith("postgres://"):
    _url = _url.replace("postgres://", "postgresql://", 1)
SessionLocal = sessionmaker(bind=create_engine(_url))

# --- heuristics -------------------------------------------------------------

REPEAT_RUN = re.compile(r"(?:\b(\w{1,3})\b[\s.,]*)(?:\1[\s.,]*){5,}", re.I)  # "R.R.R.R.R.R"
ENGLISH_HINTS = re.compile(r"\b(" + "the|and|you|that|this|with|have|from|they|what|about|going|actually|little|bit|bus|grab|called|can't|don't|didn't|won't|isn't|tell|i'm|i am|we are|it's|bear|fall|asleep|therefore|lost|because|would|could|should|there|here|where|when|then|than|your|their|just|like|know|think|want|need|make|take|come|some|thing|time|people|back|only|over|also|into|very|well|much|many|more|most|other|through|before|after|never|always|really|something|nothing|everything|world|life|love|heart|mind|night|every|again|please|thank|sorry|hello|goodbye" + r")\b", re.I)
TIFINAGH = re.compile(r"[ⴰ-⵿]")


def repeated_token_ratio(text: str) -> float:
    toks = re.findall(r"[^\W\d_]+", text.lower())
    if len(toks) < 6:
        return 0.0
    from collections import Counter

    top = Counter(toks).most_common(1)[0][1]
    return top / len(toks)


def english_score(text: str) -> int:
    return len(ENGLISH_HINTS.findall(text))


def classify(d: dict) -> list[str]:
    """Return the reasons this drill looks like junk (empty list = keep)."""
    t = (d.get("text_tachelhit") or "").strip()
    reasons: list[str] = []
    if not t:
        return reasons
    if REPEAT_RUN.search(t):
        reasons.append("repeated-run")
    if repeated_token_ratio(t) >= 0.4:
        reasons.append("repeated-tokens")
    if not TIFINAGH.search(t):
        hits = english_score(t)
        words = max(1, len(re.findall(r"[A-Za-z']+", t)))
        if hits >= 3 or (hits >= 2 and hits / words >= 0.25):
            reasons.append("looks-english")
    if len(t) > 600 and not TIFINAGH.search(t):
        reasons.append("very-long-latin")
    return reasons


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--delete", action="store_true", help="delete the listed drills (asks for confirmation)")
    ap.add_argument("--json", metavar="FILE", help="write the list as JSON")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation prompt (for scripted runs)")
    ap.add_argument("--api", metavar="URL", help="read-only: list via GET {URL}/drills/ instead of the database")
    args = ap.parse_args()

    if args.api:
        import urllib.request

        with urllib.request.urlopen(args.api.rstrip("/") + "/drills/", timeout=120) as r:
            rows = json.load(r)
        junk = [dict(id=d["id"], reasons=classify(d), tag=d.get("tag"), author=d.get("author"),
                     text_tachelhit=(d.get("text_tachelhit") or "")[:120], text_catalan=(d.get("text_catalan") or "")[:80],
                     has_audio=bool(d.get("audio_url"))) for d in rows]
        junk = [j for j in junk if j["reasons"]]
        print(f"{len(junk)} suspicious drills of {len(rows)} (via API, read-only)\n")
        for j in junk:
            print(f"#{j['id']:<6} {','.join(j['reasons']):<28} tag={j['tag'] or '-':<18} {j['text_tachelhit'][:70]!r}")
        if args.json:
            with open(args.json, "w", encoding="utf-8") as fh:
                json.dump(junk, fh, ensure_ascii=False, indent=2)
            print(f"\nwritten {args.json}")
        if args.delete:
            print("\n--delete is not available in --api mode; run against the database.")
        return 0

    db = SessionLocal()
    try:
        # Raw SQL on the few columns we need, so the tool also works on an
        # older local SQLite file that has not been column-synced by the app.
        rows = [dict(r._mapping) for r in db.execute(_t(
            "SELECT id, tag, author, text_tachelhit, text_catalan, audio_url FROM drills ORDER BY id"))]
        junk = []
        for d in rows:
            reasons = classify(d)
            if reasons:
                junk.append({
                    "id": d["id"],
                    "reasons": reasons,
                    "tag": d.get("tag"),
                    "author": d.get("author"),
                    "text_tachelhit": (d.get("text_tachelhit") or "")[:120],
                    "text_catalan": (d.get("text_catalan") or "")[:80],
                    "has_audio": bool(d.get("audio_url")),
                })
        print(f"{len(junk)} suspicious drills of {len(rows)}\n")
        for j in junk:
            print(f"#{j['id']:<6} {','.join(j['reasons']):<28} tag={j['tag'] or '-':<18} {j['text_tachelhit'][:70]!r}")
        if args.json:
            with open(args.json, "w", encoding="utf-8") as fh:
                json.dump(junk, fh, ensure_ascii=False, indent=2)
            print(f"\nwritten {args.json}")
        if not args.delete or not junk:
            return 0
        if not args.yes:
            ans = input(f"\nDelete these {len(junk)} drills? type DELETE to confirm: ")
            if ans.strip() != "DELETE":
                print("aborted")
                return 1
        ids = [j["id"] for j in junk]
        # Dependent rows first (SQLite has no cascade without PRAGMA); mirrors
        # the DELETE /drills/{id} handler.
        for tbl, col in (("drill_reviews", "drill_id"), ("review_logs", "drill_id"), ("recordings", "drill_id")):
            try:
                db.execute(_t(f"DELETE FROM {tbl} WHERE {col} IN :ids").bindparams(ids=tuple(ids)))
            except Exception as e:  # table may not exist on old DBs
                print(f"  (skip {tbl}: {e})")
        db.execute(_t("DELETE FROM drills WHERE id IN :ids").bindparams(ids=tuple(ids)))
        db.commit()
        print(f"deleted {len(ids)} drills")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
