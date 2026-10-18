# Keeps the local dev servers alive: restarts Vite (5173) and the FastAPI backend (8000)
# whenever they stop answering (for example after the machine runs low on memory).
# Start detached:  Start-Process pwsh -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',"$PSScriptRoot\dev_watchdog.ps1" -WindowStyle Hidden
# Stop:            Get-Process pwsh | Where-Object { $_.CommandLine -like '*dev_watchdog*' } | Stop-Process
param(
    [string]$Root = (Split-Path $PSScriptRoot -Parent),
    [string]$Python = 'C:\Users\josep\app2\tachelhit-drills\backend\venv\Scripts\python.exe',
    [int]$EverySeconds = 15
)
$log = Join-Path $env:TEMP 'tachelhit-dev-watchdog.log'
function Say($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m" | Out-File -Append -FilePath $log -Encoding utf8 }
function Up($url) { try { (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 4).StatusCode -eq 200 } catch { $false } }

Say "watchdog started, root=$Root"
$lastVite = Get-Date '2000-01-01'; $lastApi = Get-Date '2000-01-01'
while ($true) {
    if (-not (Up 'http://127.0.0.1:5173/') -and ((Get-Date) - $lastVite).TotalSeconds -gt 60) {
        Say 'vite down -> starting'
        Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', 'npm run dev -- --host 127.0.0.1 --port 5173 >> "%TEMP%\tachelhit-vite.log" 2>&1' `
            -WorkingDirectory (Join-Path $Root 'frontend') -WindowStyle Hidden
        $lastVite = Get-Date
    }
    if (-not (Up 'http://127.0.0.1:8000/health') -and ((Get-Date) - $lastApi).TotalSeconds -gt 60) {
        Say 'backend down -> starting'
        Start-Process -FilePath $Python -ArgumentList 'main.py' -WorkingDirectory (Join-Path $Root 'backend') `
            -WindowStyle Hidden -RedirectStandardOutput (Join-Path $env:TEMP 'tachelhit-backend.log') -RedirectStandardError (Join-Path $env:TEMP 'tachelhit-backend.err.log')
        $lastApi = Get-Date
    }
    Start-Sleep -Seconds $EverySeconds
}
