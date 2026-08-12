from __future__ import annotations

import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from .build_tools import _resolve_command
from .workspace_tools import get_run_path


_preview_processes: dict[str, subprocess.Popen] = {}
PREVIEW_STARTUP_TIMEOUT_SECONDS = 20.0
PREVIEW_POLL_INTERVAL_SECONDS = 0.2


def get_preview_url(run_id: str, port: int) -> str:
    get_run_path(run_id)
    return f"http://127.0.0.1:{port}/"


def _wait_for_preview(
    process: subprocess.Popen,
    preview_url: str,
    timeout_seconds: float,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = "preview server did not accept a connection"

    while time.monotonic() < deadline:
        exit_code = process.poll()
        if exit_code is not None:
            raise RuntimeError(
                f"Vite preview exited during startup with code {exit_code}."
            )
        try:
            with urlopen(preview_url, timeout=1) as response:
                if 200 <= response.status < 500:
                    return
                last_error = f"preview returned HTTP {response.status}"
        except (OSError, URLError) as error:
            last_error = str(error)
        time.sleep(PREVIEW_POLL_INTERVAL_SECONDS)

    raise TimeoutError(
        f"Vite preview was not ready within {timeout_seconds} seconds: "
        f"{last_error}"
    )


def start_preview(
    run_id: str,
    port: int,
    startup_timeout: float = PREVIEW_STARTUP_TIMEOUT_SECONDS,
) -> str:
    run_path = get_run_path(run_id)
    preview_url = get_preview_url(run_id, port)
    print(f"[PREVIEW] Starting Vite preview for {run_id} at {preview_url}")

    existing = _preview_processes.get(run_id)
    if existing and existing.poll() is None:
        _wait_for_preview(existing, preview_url, startup_timeout)
        return preview_url

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

    try:
        _wait_for_preview(process, preview_url, startup_timeout)
    except Exception:
        stop_preview(run_id)
        raise

    print(f"[PREVIEW] Vite preview ready for {run_id} at {preview_url}")
    return preview_url


def stop_preview(run_id: str) -> bool:
    process = _preview_processes.pop(run_id, None)
    if not process:
        return False

    if process.poll() is None:
        print(f"[PREVIEW] Stopping Vite preview for {run_id}")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    handle = getattr(process, "_codex_log_handle", None)
    if handle:
        handle.close()

    return True
