"""torchaudio MMS_FA forced alignment (no C build needed) on the Amazigh Studies clip:
Tifinagh lines -> uroman -> align -> per-line start/end."""
import os, re, json, time, sys
import torch, torchaudio
SP = r"C:\Users\josep\AppData\Local\Temp\claude\C--Users-josep-app2\104dfaed-6dfd-4f67-bac4-fece7f991424\scratchpad"
desc = json.load(open(os.path.join(SP, "ytsamples", "mY5LgYAJ7XY.json"), encoding="utf-8"))["description"]
lines = [m.group(0).strip() for m in re.finditer(r"[\u2D30-\u2D7F][\u2D30-\u2D7F\s]*", desc)]
lines = [l for l in lines if len(l) > 1]
from uroman import Uroman
ur = Uroman()
rom = [ur.romanize_string(l).lower() for l in lines]
print("romanized:", rom[:4])
bundle = torchaudio.pipelines.MMS_FA
model = bundle.get_model(with_star=False).eval()
import soundfile as sf; _a, sr = sf.read(os.path.join(SP, "ytsamples", "mY5LgYAJ7XY.wav"), dtype="float32"); wav = torch.from_numpy(_a).unsqueeze(0)
wav = torchaudio.functional.resample(wav, sr, bundle.sample_rate)
tokenizer = bundle.get_tokenizer(); aligner = bundle.get_aligner()
words = [w for l in rom for w in l.split()]
words = [re.sub(r"[^a-z' ]", "", w) for w in words]
words = [w for w in words if w]
t0 = time.time()
with torch.inference_mode():
    emission, _ = model(wav)
    spans = aligner(emission[0], tokenizer(words))
ratio = wav.shape[1] / emission.shape[1] / bundle.sample_rate
print(f"aligned {len(words)} words in {time.time()-t0:.0f}s")
# group words back into lines
i = 0
for l, r in zip(lines, rom):
    n = len([w for w in r.split() if re.sub(r"[^a-z' ]", "", w)])
    ws = spans[i:i+n]; i += n
    if not ws: continue
    s, e = ws[0][0].start * ratio, ws[-1][-1].end * ratio
    print(f"{s:6.2f}-{e:6.2f}  {l}  ({r})")
