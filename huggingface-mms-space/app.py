"""MMS ASR for Amazigh varieties (Meta mms-1b-all, per-language adapters).

Exposes one Gradio endpoint `/transcribe(audio, lang)`:
  lang = "shi" (Tachelhit), "kab" (Kabyle), "taq" (Tamasheq)
Standard Moroccan / Central Atlas Tamazight has no MMS adapter; for that
variety the org's NeMo FastConformer Space (ayymen/stt_zgh_*) is the model.
"""
import os
import threading

import gradio as gr
import librosa
import torch
from transformers import AutoProcessor, Wav2Vec2ForCTC

MODEL_ID = os.getenv("MMS_MODEL_ID", "facebook/mms-1b-all")
LANGS = ["shi", "kab", "taq"]
DEFAULT_LANG = "shi"

print(f"[MMS] loading {MODEL_ID} ...", flush=True)
processor = AutoProcessor.from_pretrained(MODEL_ID)
model = Wav2Vec2ForCTC.from_pretrained(MODEL_ID)
model.eval()
_current = {"lang": None}
_lock = threading.Lock()


def _set_lang(lang: str) -> None:
    lang = lang if lang in LANGS else DEFAULT_LANG
    if _current["lang"] != lang:
        processor.tokenizer.set_target_lang(lang)
        model.load_adapter(lang)
        _current["lang"] = lang
        print(f"[MMS] adapter -> {lang}", flush=True)


def transcribe(audio_path: str, lang: str = DEFAULT_LANG) -> str:
    if not audio_path:
        return ""
    wav, _ = librosa.load(audio_path, sr=16000, mono=True)
    with _lock:
        _set_lang(lang)
        inputs = processor(wav, sampling_rate=16000, return_tensors="pt")
        with torch.no_grad():
            logits = model(**inputs).logits
        ids = torch.argmax(logits, dim=-1)[0]
        return processor.decode(ids).strip()


_set_lang(DEFAULT_LANG)
print("[MMS] ready", flush=True)

demo = gr.Interface(
    fn=transcribe,
    inputs=[gr.Audio(type="filepath", label="Audio (any format)"), gr.Dropdown(LANGS, value=DEFAULT_LANG, label="Variety (MMS code)")],
    outputs=gr.Textbox(label="Transcription"),
    title="MMS ASR — Amazigh varieties (shi / kab / taq)",
    description="Meta MMS-1B-all with the per-language adapter. Tachelhit = shi. Used by Tachelhit Drills for the ASR bake-off.",
    api_name="transcribe",
    allow_flagging="never",
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
