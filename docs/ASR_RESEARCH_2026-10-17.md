# Speech recognition for Amazigh varieties — research notes (2026-10-17)

Companion to `ASR_BAKEOFF_2026-10-17.md` (our own measurements). Primary sources checked on
2026-10-17; items marked *(unverified)* could not be confirmed.

## 1. Models that exist

| Model | Variety / script | Data | Reported error | Licence | CPU |
|---|---|---|---|---|---|
| `ayymen/stt_zgh_fastconformer_ctc_small` (NeMo, 2024) — the production Space | zgh + kab, plus Tachelhit/Tarifit Bible readings, Tatoeba; refs in Tifinagh | CV18 zgh+kab | CV18 test WER 64.2 / CER 21.5 and WER 34.9 / CER 13.1 (card does not say which is zgh) | CC-BY-4.0 | yes, ~14 M params |
| `ayymen/stt_zgh_fastconformer_transducer_small` | same | same | not stated | CC-BY-4.0 | yes |
| **Meta OmniASR** (Nov 2025), `facebook/omniASR-CTC-300M` | has **shi_Latn, rif_Latn, rif_Arab, kab_Latn, taq_Latn, thv_Tfng**; no tzm/zgh | paper: languages under 10 h ≈ CER 18 | per-language shi/rif CER *(unverified)* | Apache-2.0 | 300 M, ~1.3 GB fp32, "low-power devices" |
| Meta MMS-1B-all | shi, kab, taq adapters | — | — | CC-BY-NC-4.0 | 1 B, slow on CPU |
| `nvidia/stt_kab_conformer_transducer_large` | Kabyle, Latin | CV10 kab, 131 h | WER 18.9 | CC-BY-4.0 | ~120 M |
| `aioxlabs/dvoice-kabyle` (SpeechBrain XLSR-53) | Kabyle | CV kab | WER 24.8 / CER 6.6 | see card | 300 M |
| `TutlaytAI/wav2vec2-berber` | kab + zgh Latin | CV17 + own set | no metrics | not stated | 300 M |
| `iukocha/mms-tachebdant-from-tarifit` (2026) | Tarifit, MMS adapter | 200 steps | WER 0.72 | CC-BY-NC-4.0 | 1 B |
| Whisper fine-tunes (Dahimi, Hillal-titouh, azhouas) | — | — | no metrics on cards | — | — |

Community manual ranking (MTNRA-Amazigh-IA/asr-manual-evaluation, 19 models, 10 clips, gated):
1) ayymen CTC, 2) an MMS adapter, 3) UBC-NLP Simba-M (MMS African adapter), 4–5) Sunbird; Whisper
fine-tunes last. Tiny sample.

Cloud APIs: Google Chirp 3 and Azure list no Amazigh language; AWS Transcribe has Kabyle only;
Whisper none. Zero-shot on CV19 zgh with Whisper-v3 / Seamless / XLS-R: WER 90–150, CER 72–124
("Voice of a Continent", EMNLP 2025, https://arxiv.org/html/2505.18436).

## 2. Datasets (Common Voice 27.0, 2026-09)

- **zgh** scripted: 2.22 h total, 1.46 h validated, 2,229 clips, 51 speakers, CC0.
- **kab** scripted: 694.6 h, 571.7 h validated, 1,608 speakers.
- **shi**: spontaneous-speech only, 2.73 h recorded, 0.01 h validated, 17 speakers. No tzm or rif locales.
- `TutlaytAI/moroccan_amazigh_asr`: 4,240 rows zgh Latin, CC-BY-NC-4.0, source unstated.
- `Ma-OpenHub/Tutlait-v1` (Cadi Ayyad, 2026): 20.9 h (Atlas 14.1 h + Souss 6.75 h), CC-BY-4.0 —
  **text is an Arabic translation, not a transcription**. Same for `SoufianeDahimi/Tamazight-ASR-Dataset-v2`
  (15.5 h Tachelhit, Arabic subtitles). Neither can be a fine-tuning target.
- IRCAM: text corpora only on the Hub; the Awal paper (arXiv 2510.27407) reports IRCAM did not answer
  collaboration requests. No FLEURS Tamazight; WAXAL is Sub-Saharan only.

## 3. Findings 2022–2026

- **Awal** (Öktem & Boudichat, 2025): 18 months of crowdsourcing gave 3 h of speech; speakers lack
  confidence writing Tamazight; no settled orthography → expect spelling noise in any Latin data.
- **Tarifit** (Daouad et al., 2025): Whisper encoder + classifier on 300 known words/sentences,
  98.5 % accuracy — closed-set classification, which shows the **known-vocabulary trick** works.
- **OmniASR paper**: under 10 h of data sits at CER ≈ 18; LLM-decoder variants beat CTC 2–3×;
  ten in-context examples cut unseen-language CER 26 → 14.
- **Dialect transfer**: no controlled shi↔tzm↔kab study; kab→zgh zero-shot still fails (WER > 90).
  Treat Kabyle checkpoints as pre-training only.

## 4. Recommendation, ranked

1. **Keep Gemini 2.5 Flash** as the transcriber for short clips (our CER 0.19 beats every open
   model); add a cheap local fallback (OmniASR-CTC-300M or the ayymen model).
2. **Stop doing open ASR when the text is known.** For pronunciation and for timing, use CTC
   **forced alignment** (torchaudio `MMS_FA`, 1,100+ languages, romanised text via uroman, CPU ok;
   pin torchaudio 2.8) to get per-word scores — this is what "say which syllable missed" needs.
   For free speech, **hotword-boosted decoding** (pyctcdecode `hotwords` = the drill vocabulary,
   weight ≈ 10) plus a KenLM n-gram built from our own drill texts, on ayymen or OmniASR logits.
3. **Fine-tune**: MMS-1B-all **shi adapter** (~2 M params) on our speaker pairs + CV zgh; hours on one
   GPU. Expected CER drop to ≈ 0.25–0.35 on in-domain audio *(extrapolated, unverified)*.
   Alternative: continue-train ayymen on Latin targets (tokenizer swap). **Normalise the informal
   Latin spelling first** (ɣ/gh, ḍ/d, ɛ/3, …) or CER is dominated by orthography.
4. **CPU budget**: ayymen (14 M) and OmniASR-CTC-300M run on CPU; MMS-1B and Whisper-large do not comfortably.
5. Do not use the Dahimi or Tutlait sets as transcription targets. Do contribute our verified
   recordings to Common Voice shi (0.01 h validated today).
