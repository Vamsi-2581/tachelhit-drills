"""Corpus-wide listening review: for every production drill with a recording, what the
machine listeners HEAR, compared with the stored Tachelhit text.

Two listeners per clip (no human ear is involved, and Claude cannot hear audio):
  plain  - Gemini 2.5 Flash on the audio alone
  guided - Gemini 2.5 Flash told the Catalan/Arabic meaning first (resolves ambiguous sounds,
           but can also be led by the meaning, so it is never trusted alone)
When the two agree the reading is written as "[heard text]"; when they disagree as
"[? guided | plain]". With --apply the bracket goes to text_tachelhit_suggested (never
text_tachelhit), in front of any suggestion already there.

    python tools/review_heard.py run [--ids 1,2] [--limit N]     # resumable, writes bakeoff/review_heard.json
    python tools/review_heard.py report                           # docs/ASR_REVIEW_2026-10-18.md
    python tools/review_heard.py apply                            # suggestions -> production
"""
from __future__ import annotations

import argparse
import base64
import difflib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, BACKEND)
import asr_bakeoff as bk  # noqa: E402  loads .env, engine_gemini, norm, WORK
from gemini_client import _generate_content  # noqa: E402

API = os.environ.get("REVIEW_API", "https://tachelhit-drills-api.onrender.com")
OUT = os.path.join(bk.WORK, "review_heard.json")
REPORT = os.path.join(os.path.dirname(BACKEND), "docs", "ASR_REVIEW_2026-10-18.md")


def get(path):
    return json.load(urllib.request.urlopen(API + path, timeout=180))


def put(did, body):
    r = urllib.request.Request(f"{API}/drills/{did}", data=json.dumps(body).encode(), method="PUT",
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=120))


def guided(wav, ca, ar):
    with open(wav, "rb") as fh:
        data = base64.b64encode(fh.read()).decode()
    meaning = (f"in Catalan: «{ca}»" if ca else "") + (f"{' and ' if ca else ''}in Arabic: «{ar}»" if ar else "")
    prompt = ("A native speaker of Moroccan Amazigh (Tachelhit, Souss) records one sentence for a language-learning app. "
              + (f"The sentence is supposed to MEAN {meaning}. " if meaning else "")
              + "Transcribe exactly what is SAID in Tachelhit (not a translation), in academic Latin (ɣ ḍ ḥ ṭ ẓ ɛ, š for sh). "
              "Ignore repetitions, Catalan or Arabic asides and background speech. If the meaning does not match what is said, "
              "still transcribe what is said. Answer as JSON {\"latin\": \"...\", \"matches_meaning\": true|false|null}")
    payload = {"systemInstruction": {"parts": [{"text": "You transcribe Tachelhit speech faithfully."}]},
               "contents": [{"role": "user", "parts": [{"inline_data": {"mime_type": "audio/wav", "data": data}}, {"text": prompt}]}],
               "generationConfig": {"maxOutputTokens": 200, "temperature": 0.0, "thinkingConfig": {"thinkingBudget": 0},
                                    "responseMimeType": "application/json"}}
    out = _generate_content(payload, 120)
    txt = "".join(p.get("text", "") for p in out["candidates"][0]["content"]["parts"]).strip()
    try:
        j = json.loads(txt)
        return str(j.get("latin") or "").strip(), j.get("matches_meaning")
    except Exception:
        m = re.search(r'"latin"\s*:\s*"([^"]*)', txt)  # truncated/invalid JSON: salvage the latin field
        return (m.group(1).strip() if m else ""), None


def sim(a, b):
    a, b = bk.norm(a), bk.norm(b)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def collapse(t):
    """Drop immediate repeats ('x x' -> 'x') and trailing punctuation for the bracket."""
    words, out = (t or "").replace(".", " ").split(), []
    for w in words:
        if out and bk.norm(out[-1]) == bk.norm(w):
            continue
        out.append(w)
    return " ".join(out).strip(" ,;")


def clean(t, limit=110):
    """A bracket must be a reading, never a JSON fragment or a paragraph."""
    t = collapse(t)
    if not t or any(c in t for c in '{}"[]'):
        return ""
    return t if len(t) <= limit else t[:limit].rsplit(" ", 1)[0] + "…"


def bracket(r):
    g, p = clean(r["guided"]), clean(r["plain"])
    if not g and not p:
        return None
    if g and p and r["agree"] >= 0.75:
        return f"[{g}]"
    if g and p:
        return f"[? {g} | {p}]"
    return f"[? {g or p}]"


def cmd_run(a):
    os.makedirs(bk.WORK, exist_ok=True)
    done = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    plain_cache = {}
    if os.path.exists(bk.RESULTS):
        for name, res in json.load(open(bk.RESULTS, encoding="utf-8")).items():
            if name.startswith("gemini"):
                plain_cache = {row["id"]: row["hyp"] for row in res["rows"] if not str(row["hyp"]).startswith("<error")}
    drills = [d for d in get("/drills/") if d.get("audio_url") or d.get("video_url")]
    if a.ids:
        keep = {int(x) for x in a.ids.split(",")}
        drills = [d for d in drills if d["id"] in keep]
    drills.sort(key=lambda d: d["id"])
    todo = [d for d in drills if str(d["id"]) not in done]
    if a.limit:
        todo = todo[: a.limit]
    print(f"{len(drills)} drills with a recording, {len(done)} already reviewed, {len(todo)} to do")
    for n, d in enumerate(todo, 1):
        did = d["id"]
        url = d.get("audio_url") or d.get("video_url")
        wav = os.path.join(bk.WORK, f"clip_{did}.wav")
        if not os.path.exists(wav):
            try:
                subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", url, "-vn", "-ac", "1", "-ar", "16000", "-t", "40", wav],
                               check=True, capture_output=True, timeout=300)
            except Exception as e:
                done[str(did)] = {"id": did, "error": f"media: {str(e)[:60]}"}
                continue
        secs = os.path.getsize(wav) / 32000
        t0 = time.time()
        try:
            g, matches = guided(wav, d.get("text_catalan") or "", d.get("text_arabic") or "")
        except Exception as e:
            g, matches = "", None
            err = str(e)[:80]
        else:
            err = None
        p = plain_cache.get(did)
        if p is None:
            try:
                p = bk.engine_gemini(wav)
            except Exception:
                p = ""
        stored = d.get("text_tachelhit") or d.get("text_tachelhit_latin") or ""
        r = {"id": did, "secs": round(secs, 1), "ca": d.get("text_catalan"), "ar": d.get("text_arabic"), "stored": stored,
             "stored_suggested": d.get("text_tachelhit_suggested"), "plain": p, "guided": g, "matches_meaning": matches,
             "agree": round(sim(g, p), 2), "vs_stored": round(sim(g, stored), 2) if stored else None, "error": err}
        r["verdict"] = ("empty" if not stored.strip() else "ok" if r["vs_stored"] >= 0.6 else "differs") if g else "unreadable"
        r["bracket"] = bracket(r) if g else None
        done[str(did)] = r
        json.dump(done, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"{n}/{len(todo)} #{did} {r['verdict']:<10} agree={r['agree']:.2f} stored={stored[:28]!r} heard={r['bracket']!r} ({time.time()-t0:.0f}s)", flush=True)


def cmd_report(_a):
    done = json.load(open(OUT, encoding="utf-8"))
    rows = [r for r in done.values() if "verdict" in r]
    by = {}
    for r in rows:
        by.setdefault(r["verdict"], []).append(r)
    lines = ["# Listening review of every recorded drill (2026-10-18)", "",
             "Two machine listeners per clip (Gemini 2.5 Flash alone, and told the Catalan/Arabic meaning); no human ear.",
             "`[heard]` = the two agree (ratio ≥ 0.75 on transliteration keys); `[? a | b]` = they disagree. Verdict `ok` = the",
             "guided reading matches the stored text at ≥ 0.6; `differs` = it does not; `empty` = no stored text.", "",
             "| verdict | drills |", "|---|---|"] + [f"| {k} | {len(v)} |" for k, v in sorted(by.items())] + [""]
    for k in ("differs", "empty", "unreadable"):
        if not by.get(k):
            continue
        lines += [f"## {k} ({len(by[k])})", "", "| id | Catalan | stored | heard | agree |", "|---|---|---|---|---|"]
        for r in sorted(by[k], key=lambda x: x["id"]):
            lines.append(f"| {r['id']} | {(r['ca'] or '')[:40]} | {(r['stored'] or '')[:40]} | {(r['bracket'] or r.get('error') or '')[:60]} | {r['agree']} |")
        lines.append("")
    open(REPORT, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    print(f"{len(rows)} rows ->", REPORT, {k: len(v) for k, v in by.items()})


def cmd_apply(_a):
    done = json.load(open(OUT, encoding="utf-8"))
    prod = {d["id"]: d for d in get("/drills/")}
    n = 0
    for r in done.values():
        if not r.get("bracket") or r["id"] not in prod:
            continue
        cur = (prod[r["id"]].get("text_tachelhit_suggested") or "").strip()
        if cur.startswith("["):
            cur = cur.split("]", 1)[1].strip(" ·")  # replace an earlier bracket
        new = r["bracket"] + (f" · {cur}" if cur else "")
        if new != (prod[r["id"]].get("text_tachelhit_suggested") or "").strip():
            put(r["id"], {"text_tachelhit_suggested": new})
            n += 1
    print(f"suggestions written: {n}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("--ids"); r.add_argument("--limit", type=int)
    sub.add_parser("report"); sub.add_parser("apply")
    a = ap.parse_args()
    {"run": cmd_run, "report": cmd_report, "apply": cmd_apply}[a.cmd](a)


if __name__ == "__main__":
    main()
