# iOS build — steps to run on a Mac (or a macOS CI runner)

Everything below is phase P6 of `../docs/IOS_FIX_PLAN.md`. Phases P1–P5 are in the
shared code and already run on web/Android; nothing here changes them.

## 0. Prerequisites
- macOS with Xcode 16+, CocoaPods (`sudo gem install cocoapods` or `brew install cocoapods`).
- An Apple Developer account (TestFlight needs a paid team).
- Node 20+, then in `frontend/`: `npm install`.

## 1. Add the platform — with CocoaPods, not SPM
Capacitor 8 creates iOS projects with Swift Package Manager by default. Two plugins
this app uses (`capacitor-voice-recorder`, `@capacitor-community/speech-recognition`)
ship only CocoaPods specs and would be silently dropped, so:

```sh
npx cap add ios --packagemanager CocoaPods
npm run cap:ios          # = build + cap sync ios + open Xcode
```

## 2. Info.plist usage descriptions (App Store rejects the build without them)
In Xcode: `App/App/Info.plist` → add:

| Key | Value (Catalan) |
|---|---|
| `NSMicrophoneUsageDescription` | Per enregistrar la teva veu en els drills i comprovar la pronunciació. |
| `NSCameraUsageDescription` | Per fer fotos i vídeos que acompanyin els drills. |
| `NSPhotoLibraryUsageDescription` | Per triar fotos, àudios i vídeos de la galeria per als drills. |
| `NSPhotoLibraryAddUsageDescription` | Per desar els reels generats a la teva galeria. |
| `NSSpeechRecognitionUsageDescription` | Per dictar el text en català en lloc d'escriure'l. |

Also set `UIViewControllerBasedStatusBarAppearance` = `YES` (default) and leave
`ITSAppUsesNonExemptEncryption` = `NO` (the app only uses HTTPS; the SQLCipher
plugin that would have changed that answer was removed in P3).

## 3. Already handled in code
- `capacitor.config.ts`: `ios.contentInset = 'never'` + the app pads its own
  headers with `env(safe-area-inset-top)`; Keyboard plugin `resize: 'native'`.
- Inline playback flags (`playsinline`) on every YouTube/HTML5 player.
- Recordings are named by their real MIME type (iOS → `.m4a`/`.mp4`).
- Downloads go through the native share sheet (`src/utils/download.ts`).
- Identity token mirrored to the native store (`restoreUserIdentity()` in `main.tsx`).
- Cold-start banner while the Render backend wakes up.

## 4. Must be tested on a real device (cannot be verified from Windows)
1. **YouTube embeds** from the `capacitor://localhost` origin (Reels, drill videos,
   video library). If YouTube answers "Error 153", host `public/yt.html` on the
   Vercel site and iframe it with `origin=https://tachelhit-drills.vercel.app`.
2. Microphone permission prompt on first "Veu" tap in Nou drill; recording saves
   and plays back; pronunciation check returns a score.
3. Share sheet on "Descarrega el Short".
4. Keyboard does not cover the copilot input or the editor's bottom bar.
5. Status bar / Dynamic Island never overlaps the sticky nav or the player header.

## 5. Icons & splash
Put a 1024×1024 `icon.png` (and optionally `icon-foreground.png`, `splash.png`)
in `frontend/resources/` and run `npm run cap:assets`.

## 6. Release
Xcode → Product → Archive → Distribute → TestFlight. For CI, GitHub Actions
`macos-15` + Fastlane `match` for certificates; keep the signing identity out of
the repo.
