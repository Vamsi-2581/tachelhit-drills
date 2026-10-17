"""ASR bake-off: which speech model to trust, measured on drills whose text is known.

Builds a gold set from drills (their audio/video clip + text_tachelhit), runs an
engine on every clip and reports a character error rate per clip and per engine.
Everything is compared in Tifinagh (Latin goes through transliteration.to_forms),
so engines that output Latin and engines that output Tifinagh are comparable.

Usage (from backend/, venv active, .env present):
    python tools/asr_bakeoff.py build --ids 78,79,80 --api http://127.0.0.1:8000 [--variety tzm]
    python tools/asr_bakeoff.py run gemini
    python tools/asr_bakeoff.py run space Tamazight-NLP/ASR /predict
    python tools/asr_bakeoff.py run space <owner>/<space> /transcribe --arg shi      # e.g. an MMS Space
    python tools/asr_bakeoff.py report

On Git Bash pass endpoint names with MSYS_NO_PATHCONV=1 (it rewrites "/predict").
Results of 2026-10-17 (12 clips, Central Atlas Tamazight, "Tamazight For All"):
    gemini-2.5-flash (isolated words)           mean CER 0.19
    Tamazight-NLP/ASR (NeMo FastConformer zgh)  mean CER 0.76
    Tamazight-NLP/ASR-N-gram-Language-modeling  mean CER 0.74
    facebook/mms-1b-all (shi adapter)           not run: needs a paid Space to host
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
for line in open(os.path.join(BACKEND, ".env"), encoding="utf-8") if os.path.exists(os.path.join(BACKEND, ".env")) else []:
    if "=" in line and not line.startswith("#"):
        k, v = line.strip().split("=", 1)
        os.environ.setdefault(k, v.strip().strip('"'))
os.environ.setdefault("HF_TOKEN", os.environ.get("HUGGINGFACE_API_KEY", ""))

from transliteration import to_forms  # noqa: E402

WORK = os.path.join(BACKEND, "bakeoff")
GOLD = os.path.join(WORK, "gold.json")
RESULTS = os.path.join(WORK, "results.json")
TIF = re.compile(r"[ⴰ-⵿]")


def to_tif(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    if TIF.search(t):
        return "".join(ch for ch in t if TIF.match(ch) or ch == " ")
    return to_forms(t)["tifinagh"]


def norm(t: str) -> str:
    return " ".join(to_tif(t).split())


def cer(ref: str, hyp: str) -> float:
    import difflib
    ref, hyp = norm(ref), norm(hyp)
    if not ref:
        return 1.0 if hyp else 0.0
    sm = difflib.SequenceMatcher(None, ref, hyp)
    matches = sum(b.size for b in sm.get_matching_blocks())
    return max(0.0, 1.0 - matches / max(len(ref), len(hyp)))


# ---- engines ---------------------------------------------------------------------
def engine_gemini(wav: str) -> str:
    from gemini_client import _generate_content
    with open(wav, "rb") as fh:
        data = base64.b64encode(fh.read()).decode()
    payload = {"systemInstruction": {"parts": [{"text": "You transcribe Moroccan Amazigh (Tamazight/Tachelhit) speech."}]},
               "contents": [{"role": "user", "parts": [{"inline_data": {"mime_type": "audio/wav", "data": data}},
                                                        {"text": "Transcribe exactly the Tamazight word(s) spoken, in academic Latin (ɣ ḍ ḥ ṭ ẓ ɛ). Ignore any English. Answer with the transcription only."}]}],
               "generationConfig": {"maxOutputTokens": 100, "temperature": 0.0, "thinkingConfig": {"thinkingBudget": 0}}}
    out = _generate_content(payload, 120)
    return "".join(p.get("text", "") for p in out["candidates"][0]["content"]["parts"]).strip()


_clients: dict = {}


def engine_space(space: str, api_name: str, wav: str, extra=()) -> str:
    from gradio_client import Client, handle_file
    c = _clients.get(space)
    if c is None:
        c = Client(space, token=os.environ.get("HF_TOKEN") or None, verbose=False)
        _clients[space] = c
    res = c.predict(handle_file(wav), *extra, api_name=api_name)
    if isinstance(res, (list, tuple)):
        res = res[0]
    return str(res or "").strip()


# ---- commands --------------------------------------------------------------------
def cmd_build(args) -> None:
    os.makedirs(WORK, exist_ok=True)
    ids = args.ids
    rows = json.load(urllib.request.urlopen(f"{args.api.rstrip('/')}/drills/?ids={ids}", timeout=120))
    gold = []
    for r in sorted(rows, key=lambda r: r["id"]):
        url = r.get("video_url") or r.get("audio_url")
        text = r.get("text_tachelhit") or r.get("text_tachelhit_latin")
        if not url or not text:
            print(f"skip #{r['id']}: needs media and text")
            continue
        if url.startswith("/"):  # media served by the backend itself (speaker recordings)
            url = args.api.rstrip("/") + url
        wav = os.path.join(WORK, f"clip_{r['id']}.wav")
        try:
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", url, "-vn", "-ac", "1", "-ar", "16000", wav],
                           check=True, capture_output=True, timeout=300)
        except subprocess.CalledProcessError as e:
            print(f"skip #{r['id']}: media unreadable ({(e.stderr or b'').decode(errors='replace').strip()[:80]})")
            continue
        gold.append({"id": r["id"], "wav": wav, "ref": text, "latin": r.get("text_tachelhit_latin"),
                     "variety": args.variety or r.get("variety"), "seconds": [r.get("video_start_time"), r.get("video_end_time")]})
        print(f"#{r['id']} {text}  ({os.path.getsize(wav) // 32000}s)")
    json.dump(gold, open(GOLD, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"gold set: {len(gold)} clips -> {GOLD}")


def cmd_run(args) -> None:
    gold = json.load(open(GOLD, encoding="utf-8"))
    results = json.load(open(RESULTS, encoding="utf-8")) if os.path.exists(RESULTS) else {}
    if args.engine == "gemini":
        name, fn = "gemini-2.5-flash", engine_gemini
    elif args.engine == "space":
        space, api = args.space, args.api_name
        extra = tuple(args.arg or [])
        name = f"{space}{api}" + (f" {' '.join(extra)}" if extra else "")
        fn = lambda w: engine_space(space, api, w, extra)  # noqa: E731
    else:
        raise SystemExit("engine must be gemini or space")
    rows = []
    for g in gold:
        t0 = time.time()
        try:
            hyp = fn(g["wav"])
        except Exception as e:
            hyp = f"<error: {str(e)[:60]}>"
        c = 1.0 if hyp.startswith("<error") else round(cer(g["ref"], hyp), 3)
        rows.append({"id": g["id"], "ref": g["ref"], "hyp": hyp, "cer": c, "secs": round(time.time() - t0, 1)})
        print(f"#{g['id']:<5} ref={norm(g['ref']):<16} hyp={hyp[:40]!r:<44} cer={c:.2f}")
    mean = sum(r["cer"] for r in rows) / len(rows)
    print(f"== {name}: mean CER {mean:.3f} over {len(rows)} clips")
    results[name] = {"mean_cer": round(mean, 3), "rows": rows, "when": time.strftime("%Y-%m-%d %H:%M")}
    json.dump(results, open(RESULTS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def cmd_report(_args) -> None:
    results = json.load(open(RESULTS, encoding="utf-8"))
    print(f"{'engine':<60} {'mean CER':>8}  exact")
    for name, r in sorted(results.items(), key=lambda kv: kv[1]["mean_cer"]):
        exact = sum(1 for x in r["rows"] if x["cer"] == 0)
        print(f"{name:<60} {r['mean_cer']:>8.3f}  {exact}/{len(r['rows'])}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--ids", required=True); b.add_argument("--api", default="http://127.0.0.1:8000"); b.add_argument("--variety")
    r = sub.add_parser("run"); r.add_argument("engine"); r.add_argument("space", nargs="?"); r.add_argument("api_name", nargs="?"); r.add_argument("--arg", action="append")
    sub.add_parser("report")
    args = ap.parse_args()
    {"build": cmd_build, "run": cmd_run, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    main()
