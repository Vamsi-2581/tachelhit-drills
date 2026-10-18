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
# Second engine: Meta OmniASR CTC 300M (Apache-2.0, CPU-friendly) — lists Tachelhit (shi_Latn),
# Tarifit (rif_Latn / rif_Arab), Kabyle (kab_Latn). HF-transformers conversion by aadel4.
OMNI_ID = os.getenv("OMNI_MODEL_ID", "aadel4/omniASR-CTC-300M-v2")
OMNI_LANGS = ["shi_Latn", "rif_Latn", "rif_Arab", "kab_Latn", "taq_Latn"]

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

_omni = {"model": None, "processor": None}


def transcribe_omni(audio_path: str, lang: str = "shi_Latn") -> str:
    """OmniASR-CTC-300M; loaded on first use (keeps startup fast)."""
    if not audio_path:
        return ""
    with _lock:
        if _omni["model"] is None:
            try:
                print(f"[OMNI] loading {OMNI_ID} ...", flush=True)
                _omni["processor"] = AutoProcessor.from_pretrained(OMNI_ID)
                _omni["model"] = Wav2Vec2ForCTC.from_pretrained(OMNI_ID)
                _omni["model"].eval()
                print("[OMNI] ready", flush=True)
            except Exception as e:
                return f"<omniASR unavailable: {e}>"
        wav, _ = librosa.load(audio_path, sr=16000, mono=True)
        proc, mdl = _omni["processor"], _omni["model"]
        try:
            if hasattr(proc.tokenizer, "set_target_lang"):
                proc.tokenizer.set_target_lang(lang)
            if hasattr(mdl, "load_adapter"):
                mdl.load_adapter(lang)
        except Exception as e:
            print(f"[OMNI] language {lang} not switchable: {e}", flush=True)
        inputs = proc(wav, sampling_rate=16000, return_tensors="pt")
        with torch.no_grad():
            logits = mdl(**inputs).logits
        ids = torch.argmax(logits, dim=-1)[0]
        return proc.decode(ids).strip()

mms_tab = gr.Interface(
    fn=transcribe,
    inputs=[gr.Audio(type="filepath", label="Audio (any format)"), gr.Dropdown(LANGS, value=DEFAULT_LANG, label="Variety (MMS code)")],
    outputs=gr.Textbox(label="Transcription"),
    title="MMS-1B-all (shi / kab / taq)",
    api_name="transcribe",
    flagging_mode="never",
)
omni_tab = gr.Interface(
    fn=transcribe_omni,
    inputs=[gr.Audio(type="filepath", label="Audio (any format)"), gr.Dropdown(OMNI_LANGS, value="shi_Latn", label="Language (OmniASR code)")],
    outputs=gr.Textbox(label="Transcription"),
    title="OmniASR-CTC-300M (shi_Latn / rif / kab)",
    api_name="transcribe_omni",
    flagging_mode="never",
)
demo = gr.TabbedInterface([mms_tab, omni_tab], ["MMS-1B-all", "OmniASR-300M"],
                          title="Amazigh ASR — bake-off engines (Tachelhit Drills)")

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
