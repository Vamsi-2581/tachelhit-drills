"""ASR bake-off, round 2 (2026-10-19): more engines and audio preparation, same gold set
and the same orthography-tolerant CER as round 1 (tools/asr_bakeoff.py).

Gold set: the 12 Central Atlas clips of 2026-10-17, rebuilt from production by id
(7 animal words of "Vocabulary of Tamazight", 5 items of Lesson #02). Own work dir
(backend/bakeoff2/) so the full-corpus gold of tools/asr_bakeoff.py is untouched.

Usage (from backend/, venv active, .env present):
    python tools/asr_bakeoff2.py build                       # gold from production (read-only)
    python tools/asr_bakeoff2.py variants                    # tempo085 / loudnorm / vocals wavs
    python tools/asr_bakeoff2.py run gemini [--variant tempo085]
    python tools/asr_bakeoff2.py run gemini-pro
    python tools/asr_bakeoff2.py run space <owner>/<space> /api_name [--arg x]
    python tools/asr_bakeoff2.py run local <engine> --python <throwaway venv python> --runner <runner.py>
    python tools/asr_bakeoff2.py report
Local engines (whisper-small-tamazight, wav2vec2-berber, mms-shi) run in a separate
Python 3.11 venv with CPU torch; this file only orchestrates them and scores the output.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)
sys.path.insert(0, HERE)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from asr_bakeoff import cer, norm, engine_space  # noqa: E402  (loads .env, transliteration)

WORK = os.path.join(BACKEND, "bakeoff2")
GOLD = os.path.join(WORK, "gold.json")
RESULTS = os.path.join(WORK, "results.json")
API = os.environ.get("BAKEOFF_API", "https://tachelhit-drills-api.onrender.com")
GOLD_IDS = [3078, 3079, 3080, 3081, 3082, 3083, 3084, 3278, 3279, 3280, 3281, 3282]

WORD_PROMPT = ("Transcribe exactly the Tamazight word(s) spoken, in academic Latin (ɣ ḍ ḥ ṭ ẓ ɛ). "
               "Ignore any English. Answer with the transcription only.")


def engine_gemini(wav: str, model: str | None = None) -> str:
    from gemini_client import _generate_content
    with open(wav, "rb") as fh:
        data = base64.b64encode(fh.read()).decode()
    payload = {"systemInstruction": {"parts": [{"text": "You transcribe Moroccan Amazigh (Tamazight/Tachelhit) speech."}]},
               "contents": [{"role": "user", "parts": [{"inline_data": {"mime_type": "audio/wav", "data": data}}, {"text": WORD_PROMPT}]}],
               "generationConfig": {"maxOutputTokens": 100, "temperature": 0.0}}
    if (model or "").startswith("gemini-2.5-pro"):
        # Pro always thinks: leave room for it (the 100-token budget returned no parts)
        payload["generationConfig"] = {"maxOutputTokens": 4000, "temperature": 0.0, "thinkingConfig": {"thinkingBudget": 128}}
    else:
        payload["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}
    out = _generate_content(payload, 180, model=model)
    return "".join(p.get("text", "") for p in out["candidates"][0]["content"]["parts"]).strip()


def run_local(engine: str, wavs: list[str], python: str, runner: str) -> dict:
    """One process for all clips (the model loads once); the runner prints JSON {wav: hyp}."""
    out = subprocess.run([python, "-X", "utf8", runner, engine, *wavs], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3600)
    if out.returncode != 0:
        raise RuntimeError(f"runner failed: {out.stderr[-400:]}")
    return json.loads(out.stdout.strip().splitlines()[-1])


def cmd_build(_args) -> None:
    os.makedirs(WORK, exist_ok=True)
    rows = json.load(urllib.request.urlopen(f"{API}/drills/?ids={','.join(map(str, GOLD_IDS))}", timeout=120))
    gold = []
    for r in sorted(rows, key=lambda r: GOLD_IDS.index(r["id"])):
        url = r.get("video_url") or r.get("audio_url")
        text = r.get("text_tachelhit") or r.get("text_tachelhit_latin")
        wav = os.path.join(WORK, f"clip_{r['id']}.wav")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", url, "-vn", "-ac", "1", "-ar", "16000", wav], check=True, capture_output=True, timeout=300)
        gold.append({"id": r["id"], "wav": wav, "ref": text, "latin": r.get("text_tachelhit_latin"), "tag": r.get("tag")})
        print(f"#{r['id']} {text}  ({os.path.getsize(wav) // 32000}s)")
    json.dump(gold, open(GOLD, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"gold set: {len(gold)} clips -> {GOLD}")


def variant_path(wav: str, variant: str) -> str:
    base, _ = os.path.splitext(wav)
    return f"{base}.{variant}.wav" if variant else wav


def cmd_variants(args) -> None:
    gold = json.load(open(GOLD, encoding="utf-8"))
    for g in gold:
        w = g["wav"]
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", w, "-filter:a", "atempo=0.85", variant_path(w, "tempo085")], check=True, timeout=120)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", w, "-filter:a", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "16000", variant_path(w, "loudnorm")], check=True, timeout=120)
    print("tempo085 + loudnorm written for", len(gold), "clips")
    if args.demucs_python:
        # demucs writes <out>/htdemucs/<name>/vocals.wav
        out_dir = os.path.join(WORK, "demucs")
        cmd = [args.demucs_python, "-m", "demucs", "--two-stems", "vocals", "-n", "htdemucs", "-d", "cpu", "-o", out_dir, *[g["wav"] for g in gold]]
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        if r.returncode != 0:
            print("demucs failed:", r.stderr[-300:])
            return
        for g in gold:
            name = os.path.splitext(os.path.basename(g["wav"]))[0]
            voc = os.path.join(out_dir, "htdemucs", name, "vocals.wav")
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", voc, "-ac", "1", "-ar", "16000", variant_path(g["wav"], "vocals")], check=True, timeout=120)
        print(f"vocals written for {len(gold)} clips in {time.time() - t0:.0f}s")


def cmd_run(args) -> None:
    gold = json.load(open(GOLD, encoding="utf-8"))
    results = json.load(open(RESULTS, encoding="utf-8")) if os.path.exists(RESULTS) else {}
    variant = args.variant or ""
    wavs = [variant_path(g["wav"], variant) for g in gold]
    name = args.engine
    hyps: dict[str, str] = {}
    secs: dict[str, float] = {}
    if args.engine in ("gemini", "gemini-pro"):
        model = "gemini-2.5-pro" if args.engine == "gemini-pro" else None
        name = model or "gemini-2.5-flash"
        for w in wavs:
            t0 = time.time()
            try:
                hyps[w] = engine_gemini(w, model)
            except Exception as e:
                hyps[w] = f"<error: {str(e)[:60]}>"
            secs[w] = time.time() - t0
    elif args.engine == "space":
        extra = tuple(args.arg or [])
        name = f"{args.space}{args.api_name}" + (f" {' '.join(extra)}" if extra else "")
        for w in wavs:
            t0 = time.time()
            try:
                hyps[w] = engine_space(args.space, args.api_name, w, extra)
            except Exception as e:
                hyps[w] = f"<error: {str(e)[:60]}>"
            secs[w] = time.time() - t0
    elif args.engine == "local":
        name = args.space  # engine key for the runner
        t0 = time.time()
        try:
            got = run_local(name, wavs, args.python, args.runner)
            hyps = {w: got.get(w, got.get(os.path.basename(w), "<error: no output>")) for w in wavs}
        except Exception as e:
            hyps = {w: f"<error: {str(e)[:60]}>" for w in wavs}
        per = (time.time() - t0) / max(1, len(wavs))
        secs = {w: per for w in wavs}
    else:
        raise SystemExit("engine must be gemini, gemini-pro, space or local")
    if variant:
        name = f"{name} +{variant}"
    rows = []
    for g, w in zip(gold, wavs):
        hyp = hyps[w]
        c = 1.0 if str(hyp).startswith("<error") else round(cer(g["ref"], hyp), 3)
        rows.append({"id": g["id"], "ref": g["ref"], "hyp": hyp, "cer": c, "secs": round(secs[w], 1)})
        print(f"#{g['id']:<5} ref={norm(g['ref']):<16} hyp={str(hyp)[:40]!r:<44} cer={c:.2f}")
    mean = sum(r["cer"] for r in rows) / len(rows)
    print(f"== {name}: mean CER {mean:.3f} over {len(rows)} clips, {sum(r['secs'] for r in rows):.0f}s")
    results[name] = {"mean_cer": round(mean, 3), "rows": rows, "when": time.strftime("%Y-%m-%d %H:%M")}
    json.dump(results, open(RESULTS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def cmd_report(_args) -> None:
    results = json.load(open(RESULTS, encoding="utf-8"))
    print(f"{'engine':<58} {'mean CER':>8}  exact  s/clip")
    for name, r in sorted(results.items(), key=lambda kv: kv[1]["mean_cer"]):
        exact = sum(1 for x in r["rows"] if x["cer"] == 0)
        per = sum(x["secs"] for x in r["rows"]) / len(r["rows"])
        print(f"{name:<58} {r['mean_cer']:>8.3f}  {exact}/{len(r['rows'])}  {per:5.1f}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    v = sub.add_parser("variants"); v.add_argument("--demucs-python", help="python of a venv with demucs installed")
    r = sub.add_parser("run"); r.add_argument("engine"); r.add_argument("space", nargs="?"); r.add_argument("api_name", nargs="?")
    r.add_argument("--arg", action="append"); r.add_argument("--variant"); r.add_argument("--python"); r.add_argument("--runner")
    sub.add_parser("report")
    args = ap.parse_args()
    {"build": cmd_build, "variants": cmd_variants, "run": cmd_run, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    main()
