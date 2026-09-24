from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_ICON_COLOR = "#3478F6"


@dataclass(slots=True)
class Tool:
    name: str
    executable: str
    working_directory: str = ""
    arguments: str = ""
    id: str = ""
    icon_color: str = DEFAULT_ICON_COLOR

    def __post_init__(self) -> None:
        if not isinstance(self.icon_color, str) or not re.fullmatch(
            r"#[0-9a-fA-F]{6}", self.icon_color
        ):
            self.icon_color = DEFAULT_ICON_COLOR
        if not self.id:
            self.id = str(uuid.uuid4())

    @property
    def path(self) -> Path:
        return Path(os.path.expandvars(os.path.expanduser(self.executable)))


def config_path() -> Path:
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return local / "PythonToolLauncher" / "tools.json"


class ToolStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or config_path()
        self.tools: list[Tool] = []

    def load(self) -> list[Tool]:
        if not self.path.exists():
            return self.tools
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.tools = [Tool(**item) for item in data.get("tools", [])]
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ValueError(f"Could not read {self.path}: {exc}") from exc
        return self.tools

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "tools": [asdict(tool) for tool in self.tools]}
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)

    def add(self, tool: Tool) -> None:
        self.tools.append(tool)
        self.save()

    def update(self, tool: Tool) -> None:
        index = next(i for i, current in enumerate(self.tools) if current.id == tool.id)
        self.tools[index] = tool
        self.save()

    def remove(self, tool_id: str) -> None:
        self.tools = [tool for tool in self.tools if tool.id != tool_id]
        self.save()

    def move(self, tool_id: str, offset: int) -> None:
        index = next(i for i, tool in enumerate(self.tools) if tool.id == tool_id)
        destination = index + offset
        if 0 <= destination < len(self.tools):
            self.tools[index], self.tools[destination] = (
                self.tools[destination],
                self.tools[index],
            )
            self.save()


def launch(tool: Tool) -> None:
    target = tool.path
    if not target.is_file():
        raise FileNotFoundError(f"Program or Python script not found:\n{target}")
    cwd = (
        Path(os.path.expandvars(os.path.expanduser(tool.working_directory)))
        if tool.working_directory
        else target.parent
    )
    if not cwd.is_dir():
        raise FileNotFoundError(f"Working directory not found:\n{cwd}")
    arguments = [
        value[1:-1] if len(value) >= 2 and value[0] == value[-1] == '"' else value
        for value in shlex.split(tool.arguments, posix=False)
    ]
    command = [str(target), *arguments]
    if target.suffix.casefold() in {".py", ".pyw"}:
        command = [python_interpreter(), str(target), *arguments]
    subprocess.Popen(
        command,
        cwd=cwd,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def python_interpreter() -> str:
    """Return an interpreter suitable for launching a Python shortcut."""
    if os.name != "nt":
        return sys.executable

    # A normal source install has pythonw beside python. A frozen launcher does
    # not: sys.executable is the launcher itself, so look on PATH instead.
    if not getattr(sys, "frozen", False):
        sibling = Path(sys.executable).with_name("pythonw.exe")
        if sibling.is_file():
            return str(sibling)

    interpreter = shutil.which("pyw") or shutil.which("pythonw")
    if interpreter:
        return interpreter
    raise FileNotFoundError(
        "No Python interpreter was found. Install Python (including the Python "
        "launcher) or add pythonw.exe to PATH."
    )
