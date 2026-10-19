# Drill pictures: audit and redraw (2026-10-18)

Every drill picture that was not a frame cut from the source video (496 of 917) was scored
by Gemini 2.5 Flash looking at the picture next to the sentence: *relevance* 1–5 (could a
learner guess the meaning from the picture?), *has_text*, *quality*. Frames from videos
(421) were left alone: they are the real context, and the app now blurs them wherever
the answer is hidden because song frames carry the subtitle.

| relevance (before) | pictures |
|---|---|
| 1 | 140 |
| 2 | 4 |
| 3 | 118 |
| 4 | 24 |
| 5 | 209 |

160 pictures had written text in them; 140 were unrelated to the sentence (SD-Turbo drew a
coyote for "they like you", Pexels returned a "mind your head" sign for "What is your name?").

## What changed on production

350 drills were drawn with `backend/illustrate.py` (Gemini image model, one flat
flashcard style, Moroccan Amazigh setting, no text) and stored as 800 px WebP:

| previous picture | drills |
|---|---|
| SD-Turbo | 187 |
| none | 72 |
| Pexels | 69 |
| speaker photo | 22 |

Rule for replacing: generated/stock pictures with relevance ≤ 3, visible text, or quality ≤ 2;
speaker-uploaded photos only when unrelated (relevance ≤ 2) or a screenshot; plus drills
with a Catalan sentence and no picture at all. Grammar-label drills ("Verb comprar — temps
verbals"), one-word chants and the few non-Catalan strays ("acnyal", "q") were not drawn.

The new pictures were audited the same way: {1: 58, 2: 2, 3: 85, 4: 23, 5: 182} (relevance → count).
The 62 that scored ≤ 2 or showed text were drawn again (and 20 abstract phrases a third time with a hand-written scene, see `hint` in the JSON) after the scene step was
added to the illustrator (a text call names one concrete scene before the image model
draws it), which is what fixed "Afilat" → a knife and "Dibuixem" → children drawing.

`image_review_2026-10-18.json` lists every change with the old URL, the new URL and the
first audit's scores, so any picture can be put back with one `PUT /drills/{id}`.

After the pass: 350 illustrations, 421 video frames, 218 kept photos/stock, 32 without a picture (of 1021 drills).
