# iOS prep — ordered fix plan

> **Status 2026-10-17:** P1, P2, P3, P4 and P5 are implemented on `feature/ios-prep`
> (web + Android code; verified with `npm run build`, `npm run lint` 190→160 errors,
> `pytest` 37→48 passed, and a Chrome smoke test against the local backend: Captura/Corpus
> scroll, one drill per "Nou drill" save with toast, "Nou test" on the dashboard,
> 422 on empty drill body, 401 on bad token, tombstone on delete).
> Not done: **P5.1 deletion** (the junk list is produced by
> `backend/tools/find_junk_drills.py --api …`; 3 candidates, ids 3063-3065, all tagged
> `tachelhit-demo`, owner decides), **P6** (needs a Mac — see `frontend/IOS_SETUP.md`),
> icon/splash source images, and the flagged blocking yt-dlp download in
> `/video-analysis/import-url`. Known gap: `utils/offlineCache.ts` still holds unused
> IndexedDB/Cache classes.

Source: section 5 of `docs/IOS_READINESS_REVIEW_2026-10-17.md` (every item below cites that review).
Branch: `feature/ios-prep` · worktree: `C:\Users\josep\app2\tachelhit-drills.worktrees\ios-prep` ·
base: `origin/main` @ 83e1e8f · ports: backend 8000, frontend 5173 (both free on 2026-10-17).

Working rules
- Run everything from the worktree. Backend venv: `backend\venv` (create if missing). Frontend: `npm install` once.
- One PR per phase (P1…P6) into `main`, same as the existing `fix/*` + PR convention. Each PR must keep
  `npm run build`, `npm run lint` (no NEW errors; baseline is 190) and `pytest tests -q` (37 pass) green.
- Web first: every phase P1–P5 is verifiable in Chrome against the local backend. P6 is the only phase that
  needs a Mac.
- Nothing here touches other app2 projects or `core/`.

Legend: `F/` = frontend/src, `B` = backend/main.py. Line numbers are as of 83e1e8f.

---

## P1 — Creation works on web (highest user impact)

| # | Change | Where | Done when |
|---|---|---|---|
| 1.1 | Create the drill first (POST once), keep its server id in state, then upload media/run AI against that id. Remove the `Date.now()` temp id. | `F/components/MobileDrillCreator.tsx:18,55,233,382` | Picking a photo/audio in "Nou drill" on web uploads with HTTP 200 and the drill shows the media after Desa. |
| 1.2 | `triggerSave` becomes create-or-update: POST only when there is no id, PUT afterwards. | `MobileDrillCreator.tsx:55` | Translate + transcribe + Desa on one sheet yields exactly ONE drill. |
| 1.3 | "Veu → Drill": upload the recording via `/upload-media/{id}/audio` and send the returned Cloudinary URL to `/transcribe/`, never a `blob:` URL. | `MobileDrillCreator.tsx:151,211,337,349` | Server log shows an `https://res.cloudinary.com/...` audio_url; text fills in. |
| 1.4 | Desa awaits the save before closing; show a spinner on the button. | `MobileDrillCreator.tsx:407` | Closing the sheet never loses a drill. |
| 1.5 | Editor: never PUT `blob:` or `convertFileSrc` paths. Upload first, then PUT the server URL (or keep the old URL until the upload resolves). | `F/components/MobileDrillEditor.tsx:86,216-218,363-366` | Editing a drill and picking a file leaves no `blob:`/`file:` string in the DB (`SELECT * FROM drills WHERE audio_url LIKE 'blob:%'` = 0 rows). |
| 1.6 | Replace `addLog`/console-only errors and `alert()` with the existing toast (`F/toast.ts`). | `MobileDrillCreator.tsx:37`, `VideoDrillCreator.tsx:457`, `DrillsGrid.tsx:204-213` | Every failed upload/trim/AI call shows a toast. |
| 1.7 | Stop appending translations in parentheses; replace the field unless the user holds a "keep" option. | `DrillsGrid.tsx:93-95,153-155` + both mobile components | Translating twice does not nest text. |
| 1.8 | Label the five media buttons (text under icon + `aria-label`). | `MobileDrillCreator.tsx:413-417` | Visible labels at 360 px width. |
| 1.9 | Require at least one of `text_catalan` / `text_tachelhit` before Desa (client) and reject fully-empty bodies server-side. | creator + `B:800-806` | `POST /drills/ {}` returns 422. |

Verification script for P1 (manual, Chrome, local backend): create a drill with photo + recording → Veu → Drill →
translate → Desa → reload → drill exists once, media plays, no console errors.

## P2 — Layout: scrolling, clipping, safe areas

| # | Change | Where | Done when |
|---|---|---|---|
| 2.1 | Drop `html, body { overflow: hidden }`; let the document scroll. Give the player/test immersive routes their own `overflow: hidden` container instead. | `frontend/index.html:17-23`, `App.css` `#root` | Captura, Corpus, Perfil and `/tests/:id` scroll with the wheel and by touch. |
| 2.2 | Replace `height: 100vh` under the sticky nav with `min-height: 100dvh` or `calc(100dvh - var(--nav-h))`. | `F/components/DrillsResponsive.tsx:295`, `TestsDashboard.tsx:237` | Last row/card fully visible at 360×640. |
| 2.3 | Safe-area insets: `padding-top: env(safe-area-inset-top)` on the sticky nav, player header, creator/editor headers; `padding-bottom: env(safe-area-inset-bottom)` on the editor bottom bar and grading bar. | `F/App.tsx:138`, `DrillPlayer.tsx:721,1591`, `MobileDrillEditor.tsx:749`, `MobileDrillCreator.tsx` header | Chrome device-mode iPhone 15 shows no overlap with the notch/home indicator. |
| 2.4 | Move the grading bar above the footer controls (or hide prev/play/next while grading). | `DrillPlayer.tsx:928,1591-1597` | Both bars reachable in review mode. |
| 2.5 | Decide mobile vs desktop by width + `navigator.maxTouchPoints > 1`, not UA. | `DrillsResponsive.tsx:95`, `DrillsGrid.tsx:43` | iPad (touch, Mac UA) gets the mobile list. |
| 2.6 | `lang="ca"` on `<html>`; `lang="ar"`/`dir="rtl"` on Arabic inputs. | `index.html`, editor/creator inputs | Arabic typing is RTL. |
| 2.7 | Touch targets ≥ 44 px for trim buttons and voice chips. | `MobileDrillEditor.tsx:531` | Lighthouse "tap targets" passes. |

## P3 — Capacitor correctness + media formats (unblocks Android today, iOS later)

| # | Change | Where | Done when |
|---|---|---|---|
| 3.1 | Replace every `Capacitor?.isNative` with a shared `isNativeApp()` from `F/config.ts:12`. | `MobileDrillCreator.tsx:42,52,169,216,219`, `MobileDrillEditor.tsx:76,227` | Grep for `\.isNative\b` returns only `config.ts`. On the Android APK, the mic permission prompt appears and a recording saves. |
| 3.2 | Derive file name + MIME from the actual blob (`blob.type`): `audio/mp4`→`.m4a`, `audio/webm`→`.webm`, `audio/aac`→`.aac`; pass a real filename to `/pronunciation/check`. | `DrillPlayer.tsx:148`, `VoiceDrillCreator.tsx:114`, `MobileDrillCreator.tsx:148`, `services/OfflineSyncManager.ts:255` | No file called `*.webm` is ever uploaded from Safari/WKWebView. |
| 3.3 | Backend: validate by content sniff + extension; accept `.heic/.heif` (convert to JPEG with Pillow-HEIF) and `.caf/.aac`; enforce the 100 MB cap with `Content-Length` + streamed read. | `B:1349-1455`, `/mobile-config` | `curl -F file=@x.heic` → 200; 120 MB file → 413. |
| 3.4 | Serve audio through a Cloudinary `f_m4a` (or `f_mp3`) transform in `getMediaUrl` when the stored URL ends in `.webm`. | `F/config.ts getMediaUrl` | Existing webm recordings play in Safari. |
| 3.5 | Remove `@capacitor-community/sqlite` and the Android registration; add `@capacitor/keyboard` and resize the copilot on `keyboardWillShow`. | `frontend/package.json`, `frontend/android/...`, `AiCopilot.tsx:127` | `npx cap sync android` succeeds; APK size drops. |
| 3.6 | Replace `webkitSpeechRecognition` with the Capacitor speech plugin on native and hide the button on web browsers without the API. | `VoiceDrillCreator.tsx:43` | No "undefined is not a constructor" in WKWebView. |
| 3.7 | `<a download>` / `window.open(blob)` → Filesystem write + Share sheet on native, keep anchor on web. | `YouTubeShorts.tsx:399`, `DrillsGrid.tsx:540` | Reel download works on the APK. |
| 3.8 | Add `cap:sync`, `cap:android` scripts and an `icon.svg` + `splash.svg` source at `frontend/resources/` (`@capacitor/assets`). | `frontend/package.json` | `npm run cap:sync` regenerates icons for both platforms. |

## P4 — Backend basics a native client needs

| # | Change | Where | Done when |
|---|---|---|---|
| 4.1 | `GET /drills/{id}` and `GET /drills/?ids=1,2,3`. | `B` near 744 | `TestTaking.tsx:81-84` and the review player load only their drills. |
| 4.2 | `limit`/`offset` on `/drills/`, `/tests/`, `/test-attempts/`, `/shorts/` (default limit 100, max 500) + `X-Total-Count`. | `B:744,1458,1501` | `/drills/` default payload < 100 KB. |
| 4.3 | `updated_at` (server default, onupdate) on Drill, Test, DrillReview; `?since=` on list routes; `drill_tombstones` table written on delete. Column sync adds nullable columns automatically. | `models.py`, `B` | `/drills/?since=<ts>` returns only changed rows + tombstones. |
| 4.4 | Present-but-unknown `X-User-Token` → 401. | `B:693-699` | Pytest: stale token → 401, no header → anonymous. |
| 4.5 | Wrap blocking calls: `requests.post` in `process_video_analysis_task` (`B:1808`), Cloudinary upload (`B:1407`), trim (`B:4549`), gTTS — via `starlette.concurrency.run_in_threadpool` or move the task to `def` (sync BackgroundTask runs in the threadpool). Add `--workers 2` in `render.yaml` only if memory allows. | `B`, `backend/render.yaml:6` | While a capture job runs, `GET /health` answers < 1 s. |
| 4.6 | Stale-job reaper on startup: jobs in a non-terminal state older than 2 h → FAILED with message. Return a job id from `/generate-short` and `/generate-drillplayer-demo`. | `B` lifespan, 1645-1689 | No job stays TRANSCRIBING after a redeploy. |
| 4.7 | Delete drill: cascade `drill_reviews`, `review_logs`, `recordings` (or FK `ondelete=CASCADE`). | `B:927-934`, `models.py` | Pytest: delete a drill with a review → 204. |
| 4.8 | Test attempts keyed by `user_id` (keep `user_name` for display); `TestTaking` sends the token (already injected) and stops sending `user_name: null`. | `models.py:69`, `B:1508`, `TestTaking.tsx:260-273` | Profile shows "my attempts". |
| 4.9 | Batch grade endpoint `POST /reviews/grade-batch [{drill_id, grade, graded_at}]`, idempotent on `(user, drill, graded_at)`. | `B:3797` | Offline grades queued by the app sync without duplicates. |
| 4.10 | One error envelope `{detail, code}`; ISO-8601 UTC with `Z`; streaks on the user's `tz` (new nullable column, default Europe/Madrid). | `B:465-484,3920` | Pytest covers the envelope and a midnight-local streak. |

Tests to add in `backend/tests/test_api.py`: 4.1, 4.2, 4.4, 4.7, 4.9, 4.10.

## P5 — Data hygiene + learner-facing gaps (can run parallel to P4)

| # | Change | Where | Done when |
|---|---|---|---|
| 5.1 | Junk-corpus pass: list drills whose Tachelhit text is English or contains runs like `(R\.){5,}`; present the list; delete only after the owner says yes. | `backend/tools/find_junk_drills.py` (new) | Corpus no longer shows ids ~3063-3065 and their siblings. |
| 5.2 | Auto-capture guard: drop segments whose ASR output is detected as English (langdetect) or has > 30 % repeated tokens; never save them as drills. | `B` create-drills path ~2700 | A re-run of the same video yields no junk. |
| 5.3 | Tests: accept Latin and Tifinagh answers (compare both via `transliteration.py` phonemic key); disable autocorrect/autocapitalize; compute hints once per question. | `TestTaking.tsx:170-182,155-156,902-925` | Typing `azul` passes a Tifinagh answer. |
| 5.4 | Dead-end guard: skip drills missing prompt/answer at load time with a toast. | `TestTaking.tsx:615-617` | No "Loading question…" lock. |
| 5.5 | Catalan strings for tests, results, review and public test page. | `TestConfigPanel.tsx`, `TestTaking.tsx:348,549`, `PublicTestView.tsx` | No English UI strings (`grep -n "Submit Answer\|Exit Test\|Your answer"` empty). |
| 5.6 | Mobile test creation: a "Nou test" button on the Tests dashboard that opens TestConfigPanel with a drill picker (search + tag filter). | `TestsDashboard.tsx:266,360`, `TestConfigPanel.tsx` | A test can be created at 360 px width. |
| 5.7 | Learner home: keep the review button visible ("Repassa" with "0 pendents"), add a "Practica" entry for plain `/player`. | `App.tsx:46` | A new user sees a way into practice. |
| 5.8 | Offline queue: append new actions to a separate list while syncing, merge after; cap retries at 5 and park failures in a `dead` list shown in Perfil. | `services/OfflineSyncManager.ts:132-172` | Unit test: enqueue during sync → not lost. |
| 5.9 | Remove dead routes/components: `/demo-videos`, `/media-test`, unused `DrillCard.tsx`, `MobileBottomNav.tsx`, `ImageGenerationModal.tsx`; link or remove `/srt-import` and `/library`. | `App.tsx:65-71`, components | `npm run build` smaller; no orphan routes. |
| 5.10 | Token recovery: show the token again in Perfil behind a tap-to-reveal, "Copy" + "Export to Files" on native; store it in Preferences (Keychain on iOS) not localStorage. | `ProfilePage.tsx:142-167`, `config.ts:31-66` | Reinstall + paste restores SRS stats. |

## P6 — iOS platform (needs a Mac or a macOS CI runner)

| # | Change | Done when |
|---|---|---|
| 6.1 | Decide the build host: a Mac with Xcode 16, or GitHub Actions `macos-15` with Fastlane `match` + TestFlight upload. Record the choice in this file. | A signed build can be produced from `main`. |
| 6.2 | `npx cap add ios --packagemanager CocoaPods` (voice-recorder + speech-recognition have no SPM). | `ios/` committed; `npx cap sync ios` clean. |
| 6.3 | `capacitor.config.ts`: `ios: { contentInset: 'always' }` (or keep insets from P2), `server.hostname` left default. | Status bar no longer overlaps. |
| 6.4 | Info.plist: `NSMicrophoneUsageDescription`, `NSCameraUsageDescription`, `NSPhotoLibraryUsageDescription`, `NSPhotoLibraryAddUsageDescription`, `NSSpeechRecognitionUsageDescription` (Catalan text). | App Store validation passes. |
| 6.5 | `playsinline: 1` on all YouTube players (`DrillPlayer.tsx:317`, `VideoLibraryPlayer.tsx:32`, `DrillCard.tsx:512` if kept) and `playsInline` on `VideoLoopPlayer.tsx:49`. | Video stays inline on iPhone. |
| 6.6 | Device test of YouTube embeds from `capacitor://localhost`. If "Error 153": host `frontend/public/yt.html` on Vercel and iframe it with `origin=https://tachelhit-drills.vercel.app`. | Reels + drill videos play on an iPhone. |
| 6.7 | Store the user token in Keychain via `@capacitor/preferences` (iOS backs it with UserDefaults; for Keychain use `capacitor-secure-storage-plugin`). | Token survives reinstall when iCloud Keychain is on. |
| 6.8 | First-launch cold-start UX: if `/health` has not answered in 3 s show "Despertant el servidor…" with the cached drill list. | No blank screen during Render wake-up. |
| 6.9 | Export-compliance answer in App Store Connect: "uses only HTTPS" (true once SQLCipher is gone, P3.5). | Build accepted. |

## Suggested sequencing

```
week 1  P1 (web creation)  ──►  PR #1
        P2 (layout)        ──►  PR #2            P4 backend in parallel (separate PRs 4.1-4.5, then 4.6-4.10)
week 2  P3 (Capacitor/media) ─► PR #3, test on Android APK
        P5 (hygiene + tests + offline) ─► PRs
week 3  P6 on a Mac / CI
```

## How to work in this worktree

```powershell
cd C:\Users\josep\app2\tachelhit-drills.worktrees\ios-prep
# backend
cd backend; python -m venv venv; .\venv\Scripts\Activate.ps1; pip install -r requirements.txt; python main.py   # :8000
# frontend (second shell)
cd frontend; npm install; npm run dev   # :5173, talks to :8000
# checks before every PR
npm run build; npm run lint; cd ..\backend; python -m pytest tests -q
```
Open PRs against `main` of `runningcostabrava/tachelhit-drills`. Remove the worktree with
`git worktree remove ../tachelhit-drills.worktrees/ios-prep` when the branch is merged.
