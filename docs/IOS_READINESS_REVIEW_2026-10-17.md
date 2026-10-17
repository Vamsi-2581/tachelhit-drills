# Tachelhit Drills — usability + iOS readiness review (2026-10-17)

Scope: the whole app (web frontend, Android/Capacitor shell, FastAPI backend), reviewed
before starting an iOS version. Method: three code reviews (frontend UX, iOS/Capacitor
readiness, backend API) plus a live walk-through of https://tachelhit-drills.vercel.app
in Chrome and a build/lint/test health check. Nothing was changed.

Paths: `F=` tachelhit-drills/frontend/src, `B=` tachelhit-drills/backend/main.py.

## 0. Health check (run today)

| Check | Result |
|---|---|
| `npm run build` | passes; 1.1 MB ag-grid chunk statically imported by the home route |
| `npm run lint` | 190 errors, 14 warnings |
| `pytest tests -q` (backend) | 37 passed |
| Render API cold start | `/version` timed out at 60 s; `/health` answered after 22 s more |
| `GET /drills/` | 482 KB, 604 drills, no pagination |
| Corpus state (live) | 604 entries, 553 with audio, **0 verified**, 527 without variety/region/romanization |
| Data quality (live) | junk ASR drills in the corpus: English sentences and "R.R.R.R…" runs saved as Tachelhit (ids 3063–3065) |

## 1. Verdict

The learning loop (review mode + SRS + pronunciation) is good and worth porting.
The creation side is broken on web today, the layout has a page-level scroll bug, and the
backend lacks the basics a native client needs (fetch one drill, pagination, recoverable
identity, non-blocking background work). The right order is: fix the shared
backend/frontend problems first, then add the iOS shell. An iOS build on top of the
current code would inherit every bug below.

## 2. Hard blockers for iOS (ios-readiness review, verified where noted)

1. **Mac + Xcode + Apple Developer account required.** This machine is Windows. Options: a Mac, or a macOS CI runner (GitHub Actions `macos-*`) for builds and TestFlight.
2. **Capacitor 8 creates iOS projects with Swift Package Manager**; `capacitor-voice-recorder` 7.0.6 and `@capacitor-community/speech-recognition` 7.0.1 only ship CocoaPods specs and would be dropped. Use `npx cap add ios --packagemanager CocoaPods` or replace the plugins.
3. **Native mic + dictation never work (Android today, iOS tomorrow).** Code checks `Capacitor.isNative`, removed in Capacitor 8; only `isNativePlatform()` exists. VERIFIED: `F/components/MobileDrillCreator.tsx:42,52,169,216,219`, `F/components/MobileDrillEditor.tsx:76,227`. `F/config.ts:12` does it right. Consequence: permission requests never run, plugins fail with "Missing permission", native saves bypass the offline queue.
4. **YouTube embeds inside `capacitor://localhost` may refuse to play** (no http Referer, "Error 153"). `F/utils/youtubeUtils.ts:23`, `VideoLibraryPlayer.tsx:38` passes that origin. Must be tested on a device; fallback = iframe an https wrapper page on Vercel.

### Config-level work
- Info.plist usage strings: microphone, camera, photo library (+ additions), speech recognition.
- Safe areas: `index.html:6` has `viewport-fit=cover` but only `AiCopilot.tsx:85` uses the top inset. Sticky nav `F/App.tsx:138`, player header `DrillPlayer.tsx:721`, editor bottom bar `MobileDrillEditor.tsx:749`, grading bar `DrillPlayer.tsx:1591` all ignore insets.
- `playsinline: 1` on YouTube players (`DrillPlayer.tsx:317`, `VideoLibraryPlayer.tsx:32`, `DrillCard.tsx:512`) and `playsInline` on `VideoLoopPlayer.tsx:49`, or iPhone forces fullscreen.
- Remove `@capacitor-community/sqlite` (unused; pulls SQLCipher → export-compliance question).
- Add `@capacitor/keyboard` (copilot input hides under keyboard).
- No icon/splash source, no `cap sync` scripts; Android bundled assets date from May 22.

### Rework for iOS media
- iOS records MP4/AAC, code labels it WebM: `DrillPlayer.tsx:148` uploads `pronunciation.webm`; `VoiceDrillCreator.tsx:114` types video as `video/webm`; native recorder output is ADTS AAC saved as `.m4a` (`MobileDrillCreator.tsx:148`, `OfflineSyncManager.ts:255`).
- `webkitSpeechRecognition` (`VoiceDrillCreator.tsx:43`) does not exist in WKWebView.
- `<a download>` (`YouTubeShorts.tsx:399`) and `window.open(blob)` (`DrillsGrid.tsx:540`) do nothing useful in the shell.
- Offline store: whole drill list as one JSON value in Preferences (`OfflineSyncManager.ts:34`); videos written as base64 strings (`:318`) → memory kills.
- Backend rejects HEIC/HEIF images and `.caf` audio by extension (`B:1349-1455`); webm audio already in the corpus will not play in AVPlayer (needs Cloudinary `f_m4a`/`f_mp3` transform or transcode).

## 3. Usability — what a user hits today

### Creation (drills)
- **Six creation paths** (manual sheet, voice, URL/file capture, auto capture queue, SRT import, copilot) with different behaviour; two of them (`/srt-import`, `/library`) have no link.
- **Web "Nou drill" sheet is broken three ways** (VERIFIED in source): uploads post to a `Date.now()` temp id and 404 (`MobileDrillCreator.tsx:233`, `B:1362`); "Veu → Drill" posts a browser `blob:` URL as `audio_url` to `/transcribe/` (`:337,:349`); every AI action calls `POST /drills/` so translate+transcribe+save = 2–4 duplicate drills (`:55`). Desa closes the sheet before the save finishes (`:407`). Nothing is required, so empty drills save.
- **Errors invisible**: creator/editor failures go to `console.log` via `addLog` (`:37`). Capture page reports success with `alert()` (`VideoDrillCreator.tsx:457`).
- **Editor writes local paths to the server**: picked files set `audio_url`/`image_url` to `blob:` URLs, native recordings to `convertFileSrc` paths, then PUT (`MobileDrillEditor.tsx:216-218,363-366,86`).
- **Media buttons are icon-only** (camera/video/mic/keyboard/folder, no label or aria-label, `MobileDrillCreator.tsx:413-417`). Seen live.
- **Translate/transcribe append in parentheses**, so fields accumulate "text (text (text))" (`DrillsGrid.tsx:93-95,153-155`, same in both mobile components).
- **Capture page**: two URL fields that behave differently; the top one needs the owner's local `capture_agent` or stays "pending" forever (`AutoCapturePanel.tsx:12,100-103`). Segment table is 640 px min in a 400 px box; no way to play a segment before selecting it; asks users for raw YouTube cookies.
- **No Arabic input** in the mobile creator/editor; no Latin→Tifinagh helper in the creator (editor has one: `TransliterationPreview.tsx`).
- **Mobile list**: "Veus" button does nothing (`DrillsGrid.tsx:528` vs `:805`); no multi-select → cannot build a test on a phone; "Crea un drill buit" leaves an empty row.
- **iPad gets the desktop AG Grid** (iPadOS reports a Mac UA; `DrillsResponsive.tsx:95`): double-tap inline edit, 430 px "Eines IA" column.

### Tests
- **Creation is desktop-only** (TestConfigPanel opens from grid selection only, `DrillsGrid.tsx:791`); Tests dashboard has no "new test" button; mobile only has "Test dels punts febles".
- Config is rich (text/audio/video, 4 directions, hint modes, timer, pass score) but **UI in English** (`TestConfigPanel.tsx:154-410`), as are test-taking, results, review and the public page. Seen live.
- **Answers are exact string match** after lowercasing (`TestTaking.tsx:170-182`); ca→shi expects Tifinagh, which iPhones have no default keyboard for; Latin not accepted; autocorrect not disabled (`:902-925`). Partial hints reshuffle on every keystroke (`:155-156,619`).
- **Dangling drill ids**: `drill_ids` is a CSV string with no FK (`models.py:63`); deleted drills vanish silently. Seen live: test "Amiga" says 6 drills, taking it says "Question 1 of 5". A drill missing a language leaves "Loading question…" with no exit (`:615-617`).
- **Results posted with `user_name: null`**, not linked to the user, do not feed SRS (`:260-273`). Share link uses `window.location.origin` → local origin inside a native shell (`TestsDashboard.tsx:477`).
- Edit panel drag uses the whole row with no touch delay (`TestEditPanel.tsx:149-153`) → fights scrolling.
- Duplicates in the list (two "ILLIS N WOUCHEN 01", 406 drills each) from SRT imports with auto-create-test.

### Learning loop (the strong part)
- Review mode: recall-first, 4 grades (buttons or keys 1–4), pronunciation check that suggests a grade, session recap, synthetic-voice badge, multi-speaker takes (`DrillPlayer.tsx:93-171,1590-1656`). Seen live, works.
- Gaps: "Again" does not re-queue in-session (`:568-573`); grading bar covers prev/play/next (`:1591-1597` vs `:928`); the review button hides itself when nothing is due (`App.tsx:46`) so there is no learner home; plain `/player` is unlinked; anonymous users share ONE review state (`B:3766`, `user_id NULL`) — the live "604 nous" badge is the communal pool.

### Layout (VERIFIED live)
- `index.html:17-23` sets `html, body { overflow: hidden }`; pages using `minHeight: 100vh` without an inner scroller **cannot be scrolled**: Capture (`VideoDrillCreator.tsx:480`), Profile (`ProfilePage.tsx:124`), Corpus (`CorpusPage.tsx:111`), public test. Confirmed in Chrome: 10 wheel ticks on Capture and Corpus moved nothing.
- Drills/Tests pages use `height: 100vh` under the sticky nav → bottom clipped (`DrillsResponsive.tsx:295`, `TestsDashboard.tsx:237`).
- `MobileBottomNav` is never mounted; the only nav is a horizontally scrolling pill bar.
- Window resize to 412 px did not take in the test browser, so phone-width screenshots are from the Android shell perspective only via code; re-check on device.
- Small targets: trim buttons ~24 px (`MobileDrillEditor.tsx:531`), 10 px tile labels. Page is `lang="en"`.

### Offline
- Whole drill/test lists as single JSON blobs in Preferences (`OfflineSyncManager.ts:33-52`); **lost-write race**: queue re-read and overwritten after long uploads (`:132-172`); no retry cap (404 uploads retry forever); UPDATE PUTs whole object, last-write-wins. `offlineCache.ts` IndexedDB/Cache classes unused; player downloads the full file on every online play (`:336-342`) and never reads the Filesystem copies. Review/grading/tests are online-only.

### Identity
- Token-only, shown once, no recovery (`ProfilePage.tsx:142-167`); invalid token → profile spins forever (`:42,52-61`); backend treats unknown tokens as anonymous silently (`B:693-699`). Delete "password" is the client string "borrar" (`DrillsGrid.tsx:262`). API key is in the bundle.

### Dead/half-built
- `/demo-videos` placeholder, `/media-test` Spanish debug page, `/library` and `/srt-import` orphaned, `DrillCard.tsx` (1,831 lines) unused, `VoiceDrillCreator` flag never set true (`DrillsResponsive.tsx:98,422`), "Copia l'enllaç filtrat" copies an unfiltered URL, boot fetches all drills twice (`App.tsx:93`, `DrillsResponsive.tsx:185`).

## 4. Backend gaps an iOS client would hit (ranked)

1. **Event loop blocked**: `process_video_analysis_task` is `async def` (`B:1782`) but calls blocking `requests.post(..., timeout=600)` to the ASR Space (`B:1808`). Render runs one uvicorn worker (`backend/render.yaml:6`). One capture can freeze every request for up to 10 min. Same pattern: Cloudinary upload (`B:1407`), trim (`B:4549`). VERIFIED.
2. **No `GET /drills/{id}`, no batch by ids, no pagination** on `/drills/`, `/tests/`, `/test-attempts/`, `/shorts/`. Only `/corpus/search` paginates.
3. **No account recovery / rotation**; reinstall = lost SRS history. Needs Keychain storage + recovery code or Sign in with Apple.
4. **Unknown token → anonymous** instead of 401.
5. **No delta sync**: no `updated_at` anywhere, no ETag, no `since=`, no tombstones. Offline grading needs an idempotent batch-grade endpoint.
6. **Jobs are in-process**: restart/spin-down leaves jobs stuck; shorts/demo have no job id; image-fill status in a global dict.
7. **Media**: extension-only validation, HEIC/.caf rejected, 100 MB "limit" never enforced, files read whole into memory, trim overwrites originals.
8. **No ownership**: anyone with the shared key can edit/delete any drill/test/recording; attempts keyed by free-text `user_name`; delete drill leaves FK rows (`B:927-934`, likely 500 on Postgres — not tested).
9. **Long synchronous HF calls** (`/transcribe/`, `/pronunciation/check`, `/tts/tachelhit`, `/translate`) can run 1–9 min while a Space wakes; longer than URLSession defaults.
10. **Three error shapes, no API version, naive UTC datetimes, UTC-midnight streaks.** `ionic://localhost` missing from CORS (irrelevant for a native URLSession client).

What already works well: per-user SM-2 with streaks and weakest-card tests (tested); hashed tokens; DB-backed auto-capture job (good for a share extension); ffmpeg `.m4a` and H.264/AAC clips; `/health/spaces` + selective wake; `/version` feature flags; `/corpus/search` pagination.

## 5. Recommended order before the iOS shell

1. Fix the web creation sheet (temp-id upload, blob URL, duplicate POSTs) and surface errors as toasts.
2. Fix page scrolling (`html/body overflow`) and the 100vh clipping; add safe-area insets.
3. Replace `Capacitor.isNative` with `isNativePlatform()`; fix media mime/extension labelling.
4. Backend: `GET /drills/{id}` + `?ids=`, pagination, `updated_at`, 401 on bad token, run blocking calls in a threadpool (`run_in_threadpool`/`to_thread`) or a real worker.
5. Data hygiene: a corpus pass to delete junk ASR drills; verification queue is at 0/604.
6. Then: `npx cap add ios --packagemanager CocoaPods`, Info.plist strings, `playsinline`, remove sqlite plugin, add keyboard plugin, test YouTube embed on a device, set up a macOS build path (Mac or CI).
