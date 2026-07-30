# Python Tools Launcher

A Windows launcher that presents local GUI tools as a responsive home-screen grid.
It follows the Windows light/dark app theme and stores its tool list at:

```text
%LOCALAPPDATA%\PythonToolLauncher\tools.json
```

## Run from source

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[build]"
.\.venv\Scripts\python-tools.exe
```

## Build the standalone executable

```powershell
.\build.ps1
```

The finished application is written to `dist\PythonTools.exe`. The Windows executable
icon comes from `assets\launcher-icon.ico`; the Tk window and taskbar icon use
`assets\launcher-icon.png`.
