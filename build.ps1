$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Icon = Join-Path $ProjectRoot "assets\launcher-icon.ico"
$PngIcon = Join-Path $ProjectRoot "assets\launcher-icon.png"

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name PythonTools `
    --icon $Icon `
    --add-data "$PngIcon;assets" `
    --paths (Join-Path $ProjectRoot "src") `
    --distpath (Join-Path $ProjectRoot "dist") `
    --workpath (Join-Path $ProjectRoot "build") `
    --specpath $ProjectRoot `
    (Join-Path $ProjectRoot "build_entry.py")
