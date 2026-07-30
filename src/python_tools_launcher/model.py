from __future__ import annotations

import json
import os
import shlex
import subprocess
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class Tool:
    name: str
    executable: str
    working_directory: str = ""
    arguments: str = ""
    id: str = ""

    def __post_init__(self) -> None:
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
    executable = tool.path
    if not executable.is_file():
        raise FileNotFoundError(f"Executable not found:\n{executable}")
    cwd = (
        Path(os.path.expandvars(os.path.expanduser(tool.working_directory)))
        if tool.working_directory
        else executable.parent
    )
    if not cwd.is_dir():
        raise FileNotFoundError(f"Working directory not found:\n{cwd}")
    arguments = [
        value[1:-1] if len(value) >= 2 and value[0] == value[-1] == '"' else value
        for value in shlex.split(tool.arguments, posix=False)
    ]
    subprocess.Popen(
        [str(executable), *arguments],
        cwd=cwd,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
