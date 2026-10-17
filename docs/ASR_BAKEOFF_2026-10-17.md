# ASR bake-off — 2026-10-17

Question: which speech model should turn a clip into Tamazight text, and for which variety?
Method: `backend/tools/asr_bakeoff.py` — a gold set of drills whose text is known, every engine
run on the same clips, character error rate (CER) computed in Tifinagh (Latin output goes
through `transliteration.to_forms`). Lower is better; 0 = exact.

## Gold set
12 clips from "Tamazight For All" (Standard Moroccan / Central Atlas Tamazight): the seven
animal words of *Vocabulary of Tamazight* (3–5 s, one spoken word with music) and the five
items of *Lesson #02* (4–18 s, the word spoken inside English explanation).

## Results

| Engine | Mean CER | Exact clips | Notes |
|---|---|---|---|
| Gemini 2.5 Flash, prompted for isolated words | **0.19** | 6 / 12 | errors are single letters (agmar→"Agnar", agḍiḍ→"agdid"); the title card and the lone letter are its misses |
| `Tamazight-NLP/ASR` (NeMo FastConformer CTC small, Common Voice zgh) — the production Space | 0.76 | 0 / 12 | invents extra words on every clip; on clips with English around the word it produces whole sentences |
| `Tamazight-NLP/ASR-N-gram-Language-modeling` (same + KenLM beam) | 0.74 | 0 / 12 | the language model does not rescue it |
| Meta MMS-1B-all, `shi` (Tachelhit) adapter | not run | — | needs a Gradio Space; HuggingFace requires a paid plan for new Gradio/Docker Spaces on both the org and the personal account (verified in the UI on 2026-10-17). The Space code is ready in `huggingface-mms-space/`: push it to a Gradio Space once hosting exists |

Earlier in the day, on whole story sentences (hedgehog story, Arabic subtitles as meaning anchor),
Gemini's transcriptions were unrelated to the subtitle in 9 of 14 samples. So: Gemini is usable
for **isolated words**, nobody is usable for **narrated sentences** yet.

## Decisions taken
1. `/transcribe/` uses Gemini for clips ≤ 20 s (`ASR_GEMINI_MAX_SECS`), the Space beyond.
2. The "correction" that mapped the Space output onto the nearest known phrase is only accepted
   when the similarity is ≥ 0.6 (`ASR_CORRECTION_MIN_SCORE`); below that the rough output is kept.
   It had turned a squirrel clip into the video's title.
3. Narration drafts for stories stay off (`NARRATION_DRAFTS=1` to experiment).
4. Every capture carries the variety the source teaches (panel dropdown; inherited per channel),
   so a Central Atlas word is never served as Tachelhit by accident.

## What would move the needle
- A hosted MMS Space (paid plan, or an org member with rights) to measure the Tachelhit adapter.
- Speaker-verified pairs: each corrected drill (text + clip, variety on the speaker's profile)
  is a fine-tuning example; `/corpus/flywheel?format=jsonl` exports them. ~50 per variety is a
  first batch. Today: 0 verified, 0 variety-labelled on production.
- Re-run: `python tools/asr_bakeoff.py build --ids <known drills>` then `run …` per engine, `report`.
