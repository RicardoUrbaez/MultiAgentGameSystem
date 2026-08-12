from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from pydantic import BaseModel

from .workspace_tools import get_run_path


class BuildResult(BaseModel):
    success: bool
    exit_code: int
    command: str
    stdout: str
    stderr: str
    log_path: str


def _resolve_command(command: str) -> str:
    candidates = [command]
    if not command.endswith(".cmd"):
        candidates.insert(0, f"{command}.cmd")

    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    return command


def _run_npm_command(
    run_id: str,
    args: list[str],
    log_filename: str,
    timeout: int = 120,
) -> BuildResult:
    run_path = get_run_path(run_id)
    logs_path = run_path / "logs"
    logs_path.mkdir(parents=True, exist_ok=True)
    log_path = logs_path / log_filename

    command = [_resolve_command(args[0]), *args[1:]]
    print(f"[BUILD] Starting {' '.join(args)} for {run_id}")
    try:
        completed = subprocess.run(
            command,
            cwd=run_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        exit_code = completed.returncode
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
    except subprocess.TimeoutExpired as error:
        exit_code = 124
        stdout = error.stdout or ""
        stderr = (error.stderr or "") + (
            f"\nCommand timed out after {timeout} seconds."
        )
    print(
        f"[BUILD] Finished {' '.join(args)} for {run_id} "
        f"with exit code {exit_code}"
    )

    log_path.write_text(
        "\n".join(
            [
                f"command: {' '.join(args)}",
                f"exit_code: {exit_code}",
                "",
                "[stdout]",
                stdout,
                "",
                "[stderr]",
                stderr,
            ]
        ),
        encoding="utf-8",
    )

    return BuildResult(
        success=exit_code == 0,
        exit_code=exit_code,
        command=" ".join(args),
        stdout=stdout,
        stderr=stderr,
        log_path=str(log_path),
    )


def npm_install(run_id: str) -> BuildResult:
    return _run_npm_command(
        run_id,
        ["npm", "ci", "--prefer-offline", "--no-audit", "--no-fund"],
        "npm-install.log",
        timeout=180,
    )


def npm_typecheck(run_id: str) -> BuildResult:
    return _run_npm_command(
        run_id,
        ["npx", "tsc", "--noEmit"],
        "typecheck.log",
    )


def npm_build(run_id: str) -> BuildResult:
    return _run_npm_command(
        run_id,
        ["npm", "run", "build-nolog"],
        "build.log",
    )


def get_build_log(run_id: str, filename: str = "build.log") -> str:
    log_path = get_run_path(run_id) / "logs" / filename
    if not log_path.exists():
        return ""
    return log_path.read_text(encoding="utf-8")
