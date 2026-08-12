from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PHASER_TEMPLATE_DIR = PROJECT_ROOT / "game_templates" / "phaser-2d-production"
GAME_WORKSPACE = PROJECT_ROOT / "game_workspace"
RUNS_DIR = GAME_WORKSPACE / "runs"

RUN_ID_PATTERN = re.compile(r"^run_\d{8}_\d{3}$")

EXCLUDED_NAMES = {
    ".git",
    ".playwright-mcp",
    ".venv",
    "dist",
    "node_modules",
    "logs",
    "__pycache__",
    ".pytest_cache",
}

ALLOWED_ROOT_NAMES = {
    "index.html",
    "log.js",
    "package-lock.json",
    "package.json",
    "public",
    "src",
    "vite",
}

ALLOWED_ROOT_PREFIXES = (
    "tsconfig",
    "vite.config",
)


def validate_run_id(run_id: str) -> str:
    if not isinstance(run_id, str):
        raise ValueError("run_id must be a string")
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError(
            "run_id must use the format run_YYYYMMDD_NNN, "
            "for example run_20260812_001"
        )
    return run_id


def get_run_path(run_id: str) -> Path:
    run_id = validate_run_id(run_id)
    return RUNS_DIR / run_id


def validate_run_path(run_id: str) -> Path:
    if not isinstance(run_id, str):
        raise ValueError("run_id must be a string")
    if "/" in run_id or "\\" in run_id or ".." in run_id:
        raise ValueError("unsafe run_id contains path traversal")

    run_path = get_run_path(run_id).resolve()
    runs_root = RUNS_DIR.resolve()

    if run_path == runs_root or runs_root not in run_path.parents:
        raise ValueError("run path must stay inside game_workspace/runs")

    return run_path


def create_next_run_id(now: datetime | None = None) -> str:
    now = now or datetime.now()
    prefix = f"run_{now:%Y%m%d}_"
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    existing_numbers = []
    for child in RUNS_DIR.iterdir():
        if child.is_dir() and child.name.startswith(prefix):
            suffix = child.name.removeprefix(prefix)
            if suffix.isdigit():
                existing_numbers.append(int(suffix))

    next_number = max(existing_numbers, default=0) + 1
    return f"{prefix}{next_number:03d}"


def _ignore_template_artifacts(directory: str, names: list[str]) -> set[str]:
    ignored = {name for name in names if name in EXCLUDED_NAMES}

    directory_path = Path(directory).resolve()
    if directory_path == PHASER_TEMPLATE_DIR.resolve():
        for name in names:
            allowed = (
                name in ALLOWED_ROOT_NAMES
                or name.startswith(ALLOWED_ROOT_PREFIXES)
            )
            if not allowed:
                ignored.add(name)

    return ignored


def create_run_from_phaser_template(run_id: str) -> Path:
    run_path = validate_run_path(run_id)
    template_path = PHASER_TEMPLATE_DIR.resolve()

    if not template_path.exists():
        raise FileNotFoundError(f"Phaser template not found: {template_path}")

    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    if run_path.exists():
        raise FileExistsError(f"Run already exists: {run_path}")

    shutil.copytree(
        template_path,
        run_path,
        ignore=_ignore_template_artifacts,
        dirs_exist_ok=False,
    )
    logs_dir = run_path / "logs"
    logs_dir.mkdir(exist_ok=False)

    return run_path
