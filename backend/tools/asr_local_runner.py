"""Local ASR runner for the bake-off (runs in the throwaway Python 3.11 venv with CPU torch).
Usage: python asr_local_runner.py <engine> wav1 wav2 ...   -> last stdout line is JSON {wav: hyp}
engines: whisper-small-tamazight | wav2vec2-berber | mms-shi
"""
import json, os, sys, time
import numpy as np
import soundfile as sf
import torch

engine, wavs = sys.argv[1], sys.argv[2:]
torch.set_num_threads(max(1, os.cpu_count() or 4))
out = {}
t0 = time.time()

def load(wav):
    a, sr = sf.read(wav, dtype="float32")
    if a.ndim > 1:
        a = a.mean(axis=1)
    if sr != 16000:
        import librosa
        a = librosa.resample(a, orig_sr=sr, target_sr=16000)
    return a

if engine == "whisper-small-tamazight":
    from transformers import WhisperProcessor, WhisperForConditionalGeneration
    name = "SoufianeDahimi/whisper-small-tamazight"
    proc = WhisperProcessor.from_pretrained(name)
    model = WhisperForConditionalGeneration.from_pretrained(name).eval()
    for w in wavs:
        feats = proc(load(w), sampling_rate=16000, return_tensors="pt").input_features
        with torch.no_grad():
            ids = model.generate(feats, max_new_tokens=60)
        out[w] = proc.batch_decode(ids, skip_special_tokens=True)[0].strip()
        print(os.path.basename(w), "->", out[w], file=sys.stderr)
elif engine in ("wav2vec2-berber", "mms-shi"):
    from transformers import Wav2Vec2ForCTC, AutoProcessor
    if engine == "wav2vec2-berber":
        name = "TutlaytAI/wav2vec2-berber"
        proc = AutoProcessor.from_pretrained(name)
        model = Wav2Vec2ForCTC.from_pretrained(name).eval()
    else:
        name = "facebook/mms-1b-all"
        proc = AutoProcessor.from_pretrained(name)
        model = Wav2Vec2ForCTC.from_pretrained(name).eval()
        proc.tokenizer.set_target_lang("shi")
        model.load_adapter("shi")
    for w in wavs:
        inputs = proc(load(w), sampling_rate=16000, return_tensors="pt")
        with torch.no_grad():
            logits = model(**inputs).logits
        ids = torch.argmax(logits, dim=-1)
        out[w] = proc.batch_decode(ids)[0].strip()
        print(os.path.basename(w), "->", out[w], file=sys.stderr)
else:
    raise SystemExit("unknown engine")
print(f"{engine}: {len(wavs)} clips in {time.time() - t0:.0f}s (incl. model load)", file=sys.stderr)
print(json.dumps(out, ensure_ascii=False))
