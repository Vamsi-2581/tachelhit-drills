# ASR bake-off, round 2 — 2026-10-19

Questions: (1) does any other engine beat Gemini Flash on our clips, (2) does preparing the
audio (slower, louder, voice only) help, (3) when the text is already known (on-screen
Tifinagh, lyrics, a channel's description), can a forced aligner give us the times of each
line — so we align instead of transcribe.

Method: `backend/tools/asr_bakeoff2.py`, the same 12-clip gold set as round 1 (rebuilt from
production by id: 7 animal words of *Vocabulary of Tamazight*, 3–4 s, one word over music;
5 items of *Lesson #02*, 4–18 s, the word spoken inside an English explanation) and the same
orthography-tolerant character error rate (`tools/asr_bakeoff.py`: transliteration spelling
key per word, hyphens dropped, immediate repeats collapsed). Local models ran on this PC's CPU
(no GPU) in a throwaway Python 3.11 venv; `tools/asr_local_runner.py` is the runner.
Per-clip output: `docs/asr_bakeoff/results2_centralatlas_2026-10-19.json`.

## 1. Engines and audio preparation

| engine | audio | mean CER | exact | s / clip | cost |
|---|---|---|---|---|---|
| Gemini 2.5 Flash | **tempo 0.85** (`atempo`) | **0.177** | **8 / 12** | 3.2 | ~$0.001 |
| Gemini 2.5 Pro | as is | 0.191 | 7 / 12 | 4.0 | ~10× Flash |
| Gemini 2.5 Flash | loudnorm (−16 LUFS) | 0.194 | 7 / 12 | 2.4 | ~$0.001 |
| Gemini 2.5 Flash (round-1 baseline) | as is | 0.197 | 6 / 12 | 2.5 | ~$0.001 |
| Gemini 2.5 Flash | vocals only (demucs htdemucs, CPU) | 0.210 | 6 / 12 | 2.6 + 34 s separation | free, slow |
| Meta MMS-1b-all, `shi` adapter, local CPU | as is | 0.496 | 5 / 12 | 42.7 (incl. 4 GB download + load; ~8 s/clip warm) | free |
| TutlaytAI/wav2vec2-berber, local CPU | as is | 0.749 | 0 / 12 | 16.9 | free |
| SoufianeDahimi/whisper-small-tamazight, local CPU | as is | 0.782 | 0 / 12 | 7.6 | free |
| Space hbouqssi/MMS_Tachelhit | — | not driveable | — | — | Gradio 3 websocket API; `gradio_client` 2.5 cannot talk to it and the legacy `/api/predict` returns HTTP 500 |

Reading the rows:

- **Slowing to 0.85 is the one preparation that helped, and only slightly**: 0.197 → 0.177,
  two more exact clips (`tawkt`, `agḍiḍ` kept their letters). Loudness normalisation did
  nothing; vocal separation made it marginally worse (the music is not what confuses the
  model, the separation smears the consonants). None of the three turns a wrong sentence
  into a right one — they move single letters.
- **Gemini Pro is not better than Flash** here (0.191 vs 0.197) and costs ten times more.
  It needs room to think (a 100-token budget returned no text at all).
- **MMS with the Tachelhit adapter is the surprise.** On the seven *word + music* clips it is
  at Flash's level: 0.238, five exact (`imudar`, `agmar`, `tafullust`, `tawkt`, `abgur`), and
  it is deterministic and free. On the five *lesson* clips it collapses (0.858) because it
  transcribes the English explanation as Tamazight sounds — it has no notion of "ignore the
  English", which the Gemini prompt gives for free. It is a second, independent listener for
  the agreement check, not a replacement. It runs on this PC's CPU in ~8 s per clip once
  loaded; the capture agent could host it.
- **The two fine-tuned community models are unusable** for us: Whisper-small-tamazight mixes
  English and Arabic into its output ("I'm a gamer. I'm a gamer." for `agmar`),
  wav2vec2-berber hallucinates extra syllables on every clip.

Decision: keep Gemini Flash as the listener; feed it audio slowed to 0.85 (cheap, no loss
anywhere); add MMS-`shi` as the second listener for word clips when the capture agent
machine can run it. Nothing in this round changes the round-1 verdict on **sentences**:
nobody transcribes narrated Tamazight sentences reliably, so for sentences the pipeline
must rely on known text + alignment (below) and on speakers.

## 2. Forced alignment: known text → times

Probe clip: Amazigh Studies `[016] Phrases 2` (mY5LgYAJ7XY, 60 s, English voice then the
Tamazight phrase, 11 phrases; the channel's description carries every phrase in Tifinagh).

| aligner | input | result | time |
|---|---|---|---|
| Space `Tamazight-NLP/NeMo-Forced-Aligner` (`/align`, Tifinagh text, split on newline) | wav + 12 Tifinagh lines | word-level and segment-level CTM for all 12 lines | 46 s |
| torchaudio `MMS_FA` (Meta forced aligner, local CPU, 1.2 GB model) + `uroman` on the Tifinagh | wav + 25 romanised words | start/end per word, regrouped per line | 45 s (warm: a few s) |

The two agree on where each phrase is (e.g. `ⵏⴽⴽⵉ ⴼⵔⵃⴰⵅ` 14.88–17.60 s vs 15.04–17.56 s;
`ⵢⴰⵖⵉⵢⵢⵉ ⵍⴰⵣ` 18.88–19.84 vs 17.96–19.80). Blind check: Gemini transcribed the cut
`nkki frḥaɣ` segment as "Nki frḥaɣ" (CER 0.11) and `yaɣ iyi irifi` as "Yaɣ yiri-sh" — the
segments contain the phrase. Where the English explanation surrounds the phrase, both
aligners stretch the first word over the English (the NeMo CTM gives `ⵀⴰⵢⵢⵉ` 0.00–3.68 s),
so word boundaries at the edges of a line are loose; inside a Tamazight-only stretch they
are tight. Files: `docs/asr_bakeoff/align/mY5LgYAJ7XY_nemo_*.ctm`; probe script
`backend/tools/mms_fa_probe.py`.

Conclusion: **forced alignment is usable now** for every source whose text we already have
— on-screen Tifinagh read by the frame reader, subtitle tracks, lyrics, the Amazigh Studies
descriptions. It gives line times good enough to cut clips (±0.3 s) and word times good
enough for the player's word highlighting when the audio is Tamazight only. The Space is
free and already running; the local MMS_FA needs a 1.2 GB model and `uroman`, both fine on
the capture-agent PC. Either removes the need to *transcribe* when the text is known: the
pipeline should align first and listen only when there is nothing to align.

## 3. What to change in the pipeline (proposed, not done here)

1. `transcribe` paths: slow the clip to 0.85 before sending it to Gemini.
2. New step `align`: when a capture has text lines without times (frame reader, description,
   lyrics), call the NeMo aligner Space (fallback: local MMS_FA on the agent) and take the line
   times from it instead of fuzzy-matching ASR segments (`_attach_lesson_lines`,
   `_align_lyrics_lines`).
3. Store word times from the aligner on the drill (new nullable column) so the player
   highlights real words instead of proportional guesses.
4. Second listener: MMS-`shi` on the agent PC for word clips; keep a draft only when the two
   listeners agree, as the verification queue already does with `[? a | b]`.

Failures to record: the `hbouqssi/MMS_Tachelhit` Space (old Gradio protocol), the
`ctc-forced-aligner` package (needs a C compiler on Windows; torchaudio's bundled MMS_FA
does the same job), and torchaudio 2.14's `load` (needs `torchcodec`; read with
`soundfile` instead).

## Round 3 (2026-10-19 evening): Meta Omnilingual ASR on this PC's CPU

Models: `csukuangfj/sherpa-onnx-omnilingual-asr-1600-languages-{300M,1B}-ctc-int8-2025-11-12`
(sherpa-onnx 1.13.8, int8, CPU), same 12 Central Atlas gold clips. Script and per-clip output:
scratchpad `omni_test.py`, `omni_300M.json`, `omni_1B.json`.

| model | output script | CER on the Latin key | CER on consonant skeletons* | exact skeletons | s / clip |
|---|---|---|---|---|---|
| Omnilingual CTC 300M int8 | Arabic, no short vowels | 1.0 (wrong script) | 0.62 | 2 / 12 | 3.0 |
| Omnilingual CTC 1B int8 | Arabic, no short vowels | 1.0 (wrong script) | 0.46 | 4 / 12 | 7.1 |

\* rough Arabic→Latin letter map, vowels stripped from both sides, first repeated chunk only.

- The CTC models choose **Arabic script** for Tachelhit and drop the vowels, like MMS: «توكت» for
  `tawkt`, «أبغور» for `abgur`, «تلست» for `tafullust`. Consonants are mostly right on the seven
  word clips, so as a *second listener on consonants* the 1B model is comparable to MMS-`shi`.
- On the five lesson clips (English voice, then the Tamazight word) they return nothing or English
  («abgen abgen black black» for ⴰⴱⵖⴰⵏ); the model has no language conditioning in the CTC
  variant (the LLM variant that MTNRA scored at 0.27 is not available as a CPU build).
- Verdict: not a replacement for Gemini Flash (0.18) nor a step up from MMS; not worth adding.
  The Tifinagh-writing NeMo model (`ayymen/stt_zgh_fastconformer_ctc_small`, Common Voice zgh,
  51 MB, CC BY 4.0) is the one going into the production Space, with forced alignment.
