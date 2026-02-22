# build.ps1 — PlatformIO CLI build/upload/monitor helper
#
# This script wraps the PlatformIO CLI (pio) for command-line use.
# Preferred workflow: VS Code + PlatformIO IDE extension (Ctrl+Alt+B / U / S).
#
# Usage:
#   powershell -File build.ps1              # compile (production env)
#   powershell -File build.ps1 -Upload      # compile + upload
#   powershell -File build.ps1 -Monitor     # compile + upload + open serial monitor
#   powershell -File build.ps1 -Debug       # compile debug env (FIRMWARE_DEBUG enabled)
#
# Prerequisites:
#   - PlatformIO Core CLI installed (comes with PlatformIO IDE extension)
#   - Add pio to PATH, or invoke via:  %USERPROFILE%\.platformio\penv\Scripts\pio.exe

param(
    [switch]$Upload,
    [switch]$Monitor,
    [switch]$Debug
)

$PIO = 'pio'   # relies on pio being on PATH; change to full path if needed
$ENV = if ($Debug) { 'esp32dev-debug' } else { 'esp32dev' }

Write-Host "[BUILD] Building TremoAI firmware — env: $ENV"
& $PIO run --environment $ENV
if ($LASTEXITCODE -ne 0) { Write-Host "[BUILD] FAILED"; exit 1 }
Write-Host "[BUILD] SUCCESS"

if ($Upload -or $Monitor) {
    Write-Host "[UPLOAD] Uploading to ESP32..."
    & $PIO run --environment $ENV --target upload
    if ($LASTEXITCODE -ne 0) { Write-Host "[UPLOAD] FAILED"; exit 1 }
    Write-Host "[UPLOAD] Done"
}

if ($Monitor) {
    Write-Host "[MONITOR] Opening serial monitor (Ctrl+C to exit)..."
    & $PIO device monitor --environment $ENV
}
