# How to learn Tachelhit with this app — research notes (2026-10-17)

Evidence-based methodology for a drill app on an oral, low-resource language. Compiled from
primary sources on 2026-10-17; items marked **[spec]** are inference, not evidence.

## 1. What research says about audio + image + text units

- **Spacing beats massing** for L2 vocabulary (meta-analysis of 37 studies, Kim & Webb 2022,
  https://doi.org/10.1111/lang.12479). Nakata & Suzuki 2019: spaced retention ≈1.6× massed at one
  week, yet spaced learners *feel* they are doing worse — tell them why.
- **SM-2 vs FSRS**: no peer-reviewed comparison. The open benchmark (~10k Anki users) gives FSRS a
  better log-loss than naive baselines; vendor "20–30 % fewer reviews" claims are unverified
  (https://github.com/open-spaced-repetition/srs-benchmark). Verdict: keep SM-2 until per-drill
  review history is large (>10k reviews), then revisit.
- **Retrieval format**: recognition is best for form–meaning links, productive recall for spelling;
  equal vs expanding intervals make no difference (Nakata). Keep both test directions.
- **Semantic sets interfere**: grouping same-category words (all the colours, all the animals)
  raises confusion; thematic/story grouping does not (Tinkham 1997; Nakata & Suzuki 2019).
  Capture-by-video yields thematic sets naturally — do not auto-build "all the animals" decks.
- **Pictures**: mixed evidence; learners over-estimate pictured words and study them less
  (Carpenter & Olson 2012). Keep the illustration, never let it carry the meaning alone in a test.
- **L1 translation is fine** (Laufer & Shmueli 1997); the pitfall is learning a word only as a
  translation pair, never inside a phrase. Nation's four strands: deliberate study ≈25 % of time,
  the rest meaning-focused input, output and fluency.
- **Audio + text together** (reading while listening) strengthens the spoken–written link faster
  than text alone (SSLA 2024). For an oral language: audio first, text second **[spec]**.
- **Coverage target**: 95 % of conversation ≈ 2,000–3,000 word families (van Zeeland & Schmitt 2012).
- **Narrow listening**: many short clips on one topic, replayed at will; comprehension rises with
  listenings (Krashen 1996; Dupuy 1999). Fits captured stories directly.
- **Shadowing** improves comprehensibility, fluency, prosody (44-study review); **ASR feedback**
  meta-analysis g = 0.69, explicit corrective feedback beats a bare score. A single pronunciation
  number is the weakest form — say which syllable missed.
- Dictation/dictogloss: positive but small studies. Cloze vs cards: no controlled comparison.

## 2. Methods from other minority / oral languages

- **SaySomethingin (Welsh)**: audio only, learner builds the sentence aloud *before* hearing it;
  fast for conversation, no independent evaluation. **Pimsleur**: same anticipation principle plus
  graduated-interval recall. **Language Transfer**: free audio, sentences from cognates.
  **Glossika**: sentence repetition, criticised for errors.
- **Quechua RCT** (Peru, IDB): app + teacher guide gave gains in reading, listening, speaking
  (0.137 SD), largest for the weakest learners, and raised public use of the language. Lesson:
  app alone is weaker than app + human.
- **32 Indigenous-language apps reviewed** (UVic): pedagogical effect rarely measurable; the
  measurable win is community pride and participation — credit speakers by name, make
  contribution visible.
- **mydialect.io**: the closest competitor (Tachelhit, Rifain, Kabyle, Chaoui): 5-minute sessions,
  audio flashcards by real speakers, SRS, "use it on a family call after 50 words"; no pronunciation
  feedback. Their advice: speak first in Latin letters, learn Tifinagh later for signs.

## 3. Amazigh / Tachelhit specifics

- Tachelhit ≈ 5.2 M speakers (2024 census), majority in Souss-Massa; largest population in Casablanca.
- **Dialects**: Tachelhit and Central Atlas Tamazight form a continuum, Tarifit is a clear break
  (CoTaSS). Trap: IRCAM's *Standard Moroccan Amazigh* mixes the three and is what school and
  MOOC materials use — vocabulary in "Tamazight" lessons may not be what Souss speakers say.
  **Tag every drill with the speaker's variety/region** (done: `variety` on captures and profiles).
- **Script**: Tifinagh official in schools since 2003; day-to-day writing is Latin. No standard
  Tachelhit orthography. Latin as working script; Tifinagh as a later "read the signs" module.
- **Courses/data**: IRCAM MOOC (2024, free, beginner, separate Tachelhit track); Peace Corps
  Tashelhit textbook (~127 pp, Latin, no audio) and dictionary 2011 (3,000+ words,
  https://www.livelingua.com/courses/tashelhit); English–Tashlhit dictionary 8,629 headwords /
  46k example sentences Latin + Tifinagh (https://huggingface.co/datasets/Tamazight-NLP/English-Tashlhit-Dictionary,
  licence "other"); Tachelhit speech 15.5 h / 20k segments with Arabic transcription
  (https://huggingface.co/datasets/Tamazight-NLP/Tamazight-Speech-to-Arabic-Text); Col·lectivaT
  "amazic" proverbs with Catalan translations, CC-BY (https://huggingface.co/datasets/collectivat/amazic).
  No Tachelhit frequency list exists; build one from dictionary examples + own transcripts **[spec]**.

## 4. Recommendations for this app, in priority order

1. **Story/lesson → learning sequence**: (a) listen to the whole clip twice, no text; (b) listen with
   the Catalan gloss; (c) one sentence drill per cue — audio first, Latin on tap, Tifinagh optional;
   (d) cloze on the 1–2 content words; (e) dictation in Latin; (f) shadow, then "say it before you
   hear it", ASR with per-syllable feedback; (g) re-listen to the whole clip, log comprehension %.
   (Krashen narrow listening + Nakata retrieval + SSi anticipation; exact order **[spec]**.)
2. **The unit is the phrase, not the word.** Word drills only as children of a sentence drill.
3. **Beginner path**: 60–80 survival phrases from own recordings (greetings, numbers, family,
   market, directions; the Peace Corps lesson list), then a Souss-speaker frequency list toward
   500, then 2,000 for listening coverage. Tifinagh after the first 500 words. Standard-Amazigh
   lessons captured from YouTube must be labelled as such.
4. **Measure**: retention at 7 and 30 days per drill (not "reviews done"), comprehension % on
   re-listens, ASR match rate per phoneme, minutes of listening per week (four-strands balance).
5. **Native speakers**: every drill carries speaker + region + verification state; a review queue
   where two Souss speakers approve or re-record; public contributor credits. The 15.5 h speech
   set only as ASR training, never as drill audio without consent.
6. **Avoid**: auto-decks of same-category words; picture-only tests; one-number pronunciation
   scores; mixing standard-Amazigh vocabulary into Tachelhit drills unflagged.
7. **SRS**: keep SM-2, minimum first interval 1 day, both directions; revisit FSRS at >10k reviews.

Sources are linked inline; see also docs/ASR_BAKEOFF_2026-10-17.md for the speech-recognition side.
