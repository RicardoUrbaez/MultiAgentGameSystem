from __future__ import annotations

import subprocess
from pathlib import Path

from .build_tools import _resolve_command
from .workspace_tools import get_run_path


_preview_processes: dict[str, subprocess.Popen] = {}


def get_preview_url(run_id: str, port: int) -> str:
    get_run_path(run_id)
    return f"http://127.0.0.1:{port}/"


def start_preview(run_id: str, port: int) -> str:
    run_path = get_run_path(run_id)

    existing = _preview_processes.get(run_id)
    if existing and existing.poll() is None:
        return get_preview_url(run_id, port)

    logs_path = run_path / "logs"
    logs_path.mkdir(parents=True, exist_ok=True)
    log_file: Path = logs_path / "preview.log"
    handle = log_file.open("ab")

    command = [
        _resolve_command("npm"),
        "run",
        "dev-nolog",
        "--",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]

    process = subprocess.Popen(
        command,
        cwd=run_path,
        stdout=handle,
        stderr=subprocess.STDOUT,
    )
    process._codex_log_handle = handle
    _preview_processes[run_id] = process

    return get_preview_url(run_id, port)


def stop_preview(run_id: str) -> bool:
    process = _preview_processes.pop(run_id, None)
    if not process:
        return False

    if process.poll() is None:
        process.terminate()

    handle = getattr(process, "_codex_log_handle", None)
    if handle:
        handle.close()

    return True
