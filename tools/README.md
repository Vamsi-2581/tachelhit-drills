# Local capture — download on your computer, process on the server

YouTube blocks `yt-dlp` from Render's datacenter IP, so URL capture done by the
server fails (and risks the server IP being banned). The **capture agent** runs on
your own computer instead: it downloads on your home IP and hands the file to the
backend, which does the rest — **transcribe → correct → translate → create drills**.
You only paste URLs in the app's *Captura* screen.

## Install it (one double-click)
Download from the GitHub release **`capture-agent`** (the *Captura* screen links to
it when no agent is connected):

| | File | Notes |
|---|---|---|
| Windows | `TachelhitCaptureAgent.exe` | SmartScreen may ask "Run anyway" (unsigned). |
| macOS | `TachelhitCaptureAgent-macos.zip` | Unzip → right-click → Open (not notarised). |

Double-click it **once**. It copies itself to a per-user folder
(`%LOCALAPPDATA%\TachelhitCapture` on Windows, `~/Library/Application Support/TachelhitCapture`
on macOS), registers itself to **start at login**, and lives in the **system tray**
(blue = idle, orange = downloading/uploading, red = error). The tray menu opens the
app, the log, and quits.

On first use it fetches `yt-dlp` (and the `deno` JS runtime YouTube now needs) from
their official releases into that folder; `yt-dlp` self-updates once a day.

The *Captura* screen shows a green dot "Agent de captura connectat" when it is polling.

### Uninstall
Run `TachelhitCaptureAgent.exe --uninstall` (removes the start-at-login entry), then
delete the folder above.

## Run it as a script instead
```
pip install requests yt-dlp pystray pillow
python tools/capture_agent.py --console                       # against Render
python tools/capture_agent.py --console --api http://127.0.0.1:8000   # local backend
```
Flags: `--api URL`, `--key X-API-KEY`, `--poll SECONDS`, `--once` (drain the queue and
exit), `--install` / `--uninstall` (packaged build only). Env vars `TACHELHIT_API`,
`TACHELHIT_API_KEY`, `CAPTURE_POLL_SECS` still work. Settings are remembered in
`config.json` in the agent folder.

`capture_agent.bat` / `start_agent_hidden.vbs` are the pre-installer way to run the
script on Windows; `capture_youtube.py` / `capture.bat` do one URL per run.

## How the builds are made
`.github/workflows/capture-agent.yml` packages `tools/capture_agent.py` with
PyInstaller on Windows and macOS runners and attaches both files to the
`capture-agent` release on every push to `main` that touches the agent.

## Notes
- The server still needs the ASR + translation HuggingFace Spaces awake.
- Nothing is uploaded anywhere except your own backend.
