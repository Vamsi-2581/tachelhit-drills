# System review — 2026-10-19 (evening)

What the catalogue holds, what works, what does not, and what to improve next. Numbers from
production at 18:15 (847 drills).

## The catalogue in numbers

| | count | note |
|---|---|---|
| drills | 847 | 522 by the owner (no author set), 248 automatic captures, 77 by named contributors |
| with a recording | 530 | the gold: a speaker's voice |
| with a video clip | 263 | captured songs/lessons; the clip's sound is the voice |
| synthetic voice only | 6 → 32 | 26 text-only drills are getting a v2 voice tonight |
| no sound at all | 48 → 22 | the 22 left have no Tamazight text either |
| no Tamazight text | 77 | 49 have a recording and a machine draft (meaning check running); 28 have neither |
| Tamazight written in Tifinagh | 170 | the rest (600) is the owner's ad-hoc Latin; Tifinagh is derived |
| Catalan meaning | 802 | 45 without |
| picture | 812 | |
| subjects (`topics`) | 795 | 52 unclassifiable (no text) |
| variety set | 247 | **600 drills have no variety**; the owner's own recordings are Azilal–Kelaat M'Gouna speech and should say so |
| verified | 0 | the `verified` flag is never used |
| collections (`tag`) | 39 | median 8 drills each |

## What works (verified today)

- Capture on the owner's PC through the 2.6.0 agent (local backend, drills copied to production), serial, ~1–4 min per video.
- Frame reading of **Amazigh written on screen** (alphabet, vocabulary, seasons, greetings): good drills with clips.
- **Subtitled songs with real subtitle tracks** («line (meaning)» / «line | meaning»): the Fadma re-capture gave 13 correct lines.
- Subject catalogue (29 subjects), lexicon grounding of the tutor (Oulhaj dictionary + IRCAM tables), NeMo Tifinagh ASR Space with `/align`, synthetic voice from standard Tifinagh.

## What does not work, and the fix

| problem | evidence | fix |
|---|---|---|
| Darija-narrated lessons produce junk | request #25: Arabic heading written in Tifinagh ×6 | language guard (#116, merged); keep them out of the queue |
| Amazigh-only subtitles dropped | `79 readings -> 0 cues`, request #33 | #117 merged |
| Lesson listening silently disabled | UTF-8 print crash (#120 merged); malformed JSON (#123 open) | merge #123; re-capture the word videos |
| Screen letters vs heard spelling | fox sign ≠ «abaɣuɣ» | #121: screen wins for the same word; different word flagged for review. Gemini cannot read stylised Tifinagh reliably |
| Narrated **page** videos (texts, 87 fables) | Gemini misreads dense Tifinagh pages | fuse Feraoun-36M page OCR + NeMo ASR of the narration + Gemini reconciliation + `/align` (next build; branch `feature/page-text-capture` holds the page detection) |
| Machine listening of Central Atlas speech | CER 0.18 at best (Gemini, slowed) | never a drill text without a speaker's confirmation (policy in place: drafts only) |

## Improvements, in order of value

1. **Variety on the owner's 600 drills.** One decision by the owner (they are their own recordings) and a bulk update; until then the variety filter is nearly useless and the tutor cannot say which variety a form belongs to.
2. **Confirm or reject the 49 drafts** on the owner's recordings (meaning check running; the «Verifica» queue shows them). Each confirmation turns a recording-only drill into a full drill.
3. **Page videos** (texts + fables of Tamazight For All): the fusion reader above. This unlocks ~100 narrated videos with written text.
4. **Verified flag**: a one-tap «Verificat» on the card for the owner, so tests can prefer verified drills and the catalogue can show how much is speaker-confirmed.
5. **Dedupe repeats** in captured songs (chorus lines appear 2–3 times: 3674/3676, 3682/3686): keep one drill per distinct line, reference the other clip times.
6. **Capture queue UI**: show the queue (pending/claimed/done with drill counts) in the Captura tab instead of only on the agent's log, and never expose `GET /capture/pending` to a browser (it claims).
7. **CI keystore**: set `ANDROID_DEBUG_KEYSTORE_B64` to the owner's debug keystore so CI APKs install over the phone app.
8. **Render memory**: the meaning-check thread plus a pipeline job restarted the service twice on 10-19; keep heavy work on the local agent (already the default) and cap concurrent jobs on Render to 1.
9. **Lexicon coverage**: 20 % of the owner's tokens hit the Souss dictionary; a Central Atlas word list (Taïfi, Alalou) would raise it. Needs a source with a usable licence.
10. **Tests from subjects**: «Afegeix-los tots» exists; add «Test del tema» buttons on the subject chips to create one in one tap.
