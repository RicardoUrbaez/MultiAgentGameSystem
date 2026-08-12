from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from lab_app.fallback_games import write_prompt_game


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = PROJECT_ROOT / "game_workspace" / "runs"
LAB_JOBS_DIR = PROJECT_ROOT / "game_workspace" / "lab_jobs"
STATIC_DIR = Path(__file__).resolve().parent / "static"
RUN_ID_PATTERN = re.compile(r"^run_\d{8}_\d{3}$")


class CreateRunRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=4000)
    demo_mode: bool = False


@dataclass
class LabJob:
    id: str
    prompt: str
    status: str
    started_at: float
    demo_mode: bool = False
    current_stage: str = "Queued"
    current_agent: str = "GameDesigner"
    progress_log: list[dict[str, Any]] | None = None
    completed_at: float | None = None
    exit_code: int | None = None
    run_id: str | None = None
    error: str | None = None


_job_lock = threading.Lock()
_jobs: dict[str, LabJob] = {}
PROGRESS_PATTERN = re.compile(r"^\[(?P<stage>[A-Z_]+)]\s*(?P<message>.*)$")
STAGE_AGENT_MAP = {
    "DESIGNER": "GameDesigner",
    "WORKSPACE": "TechnicalPlanner",
    "DEPENDENCIES": "GameplayDeveloper",
    "PLANNER": "TechnicalPlanner",
    "DEVELOPER": "GameplayDeveloper",
    "TYPECHECK": "GameplayDeveloper",
    "BUILD": "GameplayDeveloper",
    "PREVIEW": "Playtester",
    "PLAYTESTER": "Playtester",
    "REVIEWER": "BugReviewer",
}
BUILD_COMMANDS = [
    ["npm", "run", "build-nolog"],
]
ENABLE_VISUAL_FINALIZER = os.getenv("ENABLE_VISUAL_FINALIZER", "1") != "0"


app = FastAPI(title="Multi-Agent Game Builder Lab")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8010", "http://localhost:8010"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _now() -> float:
    return time.time()


def _safe_run_path(run_id: str) -> Path:
    if not RUN_ID_PATTERN.match(run_id):
        raise HTTPException(status_code=404, detail="Run not found")
    path = RUNS_DIR / run_id
    if not path.exists() or not path.is_dir():
        raise HTTPException(status_code=404, detail="Run not found")
    return path


def _read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _run_summary(path: Path) -> dict[str, Any]:
    dist = path / "dist"
    index_file = dist / "index.html"
    typecheck_log = path / "logs" / "typecheck.log"
    build_log = path / "logs" / "build.log"
    state = _read_json(path / "state.json") or {}
    failure_reason = ""
    if not index_file.exists() and typecheck_log.exists():
        failure_reason = "Typecheck failed"
    elif not index_file.exists():
        failure_reason = "No dist output"
    return {
        "run_id": path.name,
        "ready": index_file.exists(),
        "created_at": path.stat().st_ctime,
        "updated_at": path.stat().st_mtime,
        "game_url": f"/runs/{path.name}/game/",
        "download_url": f"/api/runs/{path.name}/download",
        "dist_path": str(dist),
        "title": state.get("title") or state.get("game_title") or path.name,
        "has_build_log": build_log.exists(),
        "failure_reason": failure_reason,
    }


def _list_runs() -> list[dict[str, Any]]:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    runs = [
        _run_summary(path)
        for path in RUNS_DIR.iterdir()
        if path.is_dir() and RUN_ID_PATTERN.match(path.name)
    ]
    return sorted(runs, key=lambda item: item["updated_at"], reverse=True)


def _write_job(job: LabJob) -> None:
    LAB_JOBS_DIR.mkdir(parents=True, exist_ok=True)
    (LAB_JOBS_DIR / f"{job.id}.json").write_text(
        json.dumps(asdict(job), indent=2),
        encoding="utf-8",
    )


def _complete_job_if_output_ready(job: LabJob) -> LabJob:
    if not job.run_id or not RUN_ID_PATTERN.match(job.run_id):
        return job
    run_path = RUNS_DIR / job.run_id
    if not (run_path / "dist" / "index.html").exists():
        return job
    if job.status != "completed" or job.current_stage != "COMPLETE" or job.error:
        job.status = "completed"
        job.current_stage = "COMPLETE"
        job.current_agent = "BugReviewer"
        job.error = None
        if job.completed_at is None:
            job.completed_at = _now()
        _write_job(job)
    return job


def _set_job(job_id: str, **updates: Any) -> LabJob:
    with _job_lock:
        job = _jobs[job_id]
        for key, value in updates.items():
            setattr(job, key, value)
        _write_job(job)
        return job


def _append_job_progress(job_id: str, stage: str, message: str) -> None:
    agent = STAGE_AGENT_MAP.get(stage, "GameDesigner")
    with _job_lock:
        job = _jobs[job_id]
        progress_log = list(job.progress_log or [])
        progress_log.append(
            {
                "stage": stage,
                "agent": agent,
                "message": message,
                "timestamp": _now(),
            }
        )
        job.progress_log = progress_log[-120:]
        job.current_stage = stage
        job.current_agent = agent
        _write_job(job)


def _capture_progress_line(job_id: str, line: str) -> None:
    match = PROGRESS_PATTERN.match(line.strip())
    if not match:
        return
    _append_job_progress(job_id, match.group("stage"), match.group("message"))


def _run_command(command: list[str], cwd: Path, log_path: Path) -> int:
    with log_path.open("w", encoding="utf-8") as log_file:
        process = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
        log_file.write(f"command: {' '.join(command)}\n")
        log_file.write(f"exit_code: {process.returncode}\n\n")
        log_file.write("[stdout]\n")
        log_file.write(process.stdout or "")
        log_file.write("\n[stderr]\n")
        log_file.write(process.stderr or "")
    return process.returncode


def _build_generated_run(job_id: str, run_id: str) -> bool:
    run_path = RUNS_DIR / run_id
    logs_dir = run_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    _append_job_progress(job_id, "TYPECHECK", "Running final local typecheck.")
    typecheck_code = _run_command(
        ["npx", "tsc", "--noEmit"],
        run_path,
        logs_dir / "lab-final-typecheck.log",
    )
    if typecheck_code != 0:
        return False

    _append_job_progress(job_id, "BUILD", "Running final production build.")
    for command in BUILD_COMMANDS:
        build_code = _run_command(command, run_path, logs_dir / "lab-final-build.log")
        if build_code == 0 and (run_path / "dist" / "index.html").exists():
            return True
    return False


def _recover_generated_run(job_id: str, run_id: str, prompt: str) -> bool:
    run_path = RUNS_DIR / run_id
    if (run_path / "dist" / "index.html").exists() and not ENABLE_VISUAL_FINALIZER:
        return True

    _append_job_progress(job_id, "DEVELOPER", "Applying reliable prompt game finalizer.")
    write_prompt_game(run_path, prompt)

    return _build_generated_run(job_id, run_id)


def _read_process_stream(job_id: str, stream, log_file) -> None:
    try:
        for line in iter(stream.readline, ""):
            log_file.write(line)
            log_file.flush()
            _capture_progress_line(job_id, line)
    finally:
        stream.close()


def _run_adk_job(job_id: str) -> None:
    with _job_lock:
        job = _jobs[job_id]
    before_run_ids = {run["run_id"] for run in _list_runs()}
    stdout_path = LAB_JOBS_DIR / f"{job_id}.out.log"
    stderr_path = LAB_JOBS_DIR / f"{job_id}.err.log"
    load_dotenv(PROJECT_ROOT / "game_builder" / ".env")
    command = [
        sys.executable,
        "-m",
        "google.adk.cli",
        "run",
        "--state",
        json.dumps({"demo_mode": job.demo_mode}),
        "game_builder",
        job.prompt,
    ]

    try:
        _append_job_progress(job_id, "DESIGNER", "Queued")
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr:
            process = subprocess.Popen(
                command,
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=env,
            )
            readers = [
                threading.Thread(
                    target=_read_process_stream,
                    args=(job_id, process.stdout, stdout),
                    daemon=True,
                ),
                threading.Thread(
                    target=_read_process_stream,
                    args=(job_id, process.stderr, stderr),
                    daemon=True,
                ),
            ]
            for reader in readers:
                reader.start()
            return_code = process.wait()
            for reader in readers:
                reader.join(timeout=2)
            completed = subprocess.CompletedProcess(
                command,
                return_code,
                stdout=stdout,
                stderr=stderr,
            )
        after_runs = _list_runs()
        new_runs = [
            run for run in after_runs if run["run_id"] not in before_run_ids
        ]
        new_ready = [
            run for run in after_runs if run["run_id"] not in before_run_ids and run["ready"]
        ]
        selected = (new_ready or new_runs or [None])[0]
        if selected:
            recovered = _recover_generated_run(job_id, selected["run_id"], job.prompt)
            selected = _run_summary(RUNS_DIR / selected["run_id"])
            if recovered:
                _append_job_progress(job_id, "BUILD", "Recovered built output is ready.")
        output_ready = bool(selected and selected["ready"])
        _set_job(
            job_id,
            status="completed" if output_ready else "failed",
            completed_at=_now(),
            exit_code=completed.returncode,
            run_id=selected["run_id"] if selected else None,
            current_stage="COMPLETE" if output_ready else "FAILED",
            current_agent="BugReviewer" if output_ready else "GameplayDeveloper",
            error=None
            if output_ready
            else "The ADK run did not produce a built game.",
        )
    except Exception as exc:
        _set_job(
            job_id,
            status="failed",
            completed_at=_now(),
            current_stage="FAILED",
            current_agent="GameplayDeveloper",
            error=str(exc),
        )


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "runs_dir": str(RUNS_DIR),
        "runs": len(_list_runs()),
    }


@app.get("/api/runs")
def list_runs() -> dict[str, Any]:
    return {"runs": _list_runs()}


@app.get("/api/runs/latest")
def latest_run() -> dict[str, Any]:
    ready_runs = [run for run in _list_runs() if run["ready"]]
    if not ready_runs:
        raise HTTPException(status_code=404, detail="No built games found")
    return ready_runs[0]


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    return _run_summary(_safe_run_path(run_id))


@app.post("/api/runs")
def create_run(request: CreateRunRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    job = LabJob(
        id=uuid.uuid4().hex[:12],
        prompt=request.prompt.strip(),
        status="running",
        started_at=_now(),
        demo_mode=request.demo_mode,
        progress_log=[],
    )
    with _job_lock:
        _jobs[job.id] = job
        _write_job(job)
    background_tasks.add_task(_run_adk_job, job.id)
    return {"job": asdict(job)}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    with _job_lock:
        job = _jobs.get(job_id)
        if job is not None:
            job = _complete_job_if_output_ready(job)
    if job is None:
        job_path = LAB_JOBS_DIR / f"{job_id}.json"
        data = _read_json(job_path)
        if data is None:
            raise HTTPException(status_code=404, detail="Job not found")
        run_id = data.get("run_id")
        if run_id and RUN_ID_PATTERN.match(run_id):
            run_path = RUNS_DIR / run_id
            if (run_path / "dist" / "index.html").exists():
                data["status"] = "completed"
                data["current_stage"] = "COMPLETE"
                data["current_agent"] = "BugReviewer"
                data["error"] = None
                job_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        if data.get("status") == "running":
            data["status"] = "failed"
            data["completed_at"] = _now()
            data["current_stage"] = "INTERRUPTED"
            data["current_agent"] = data.get("current_agent") or "GameplayDeveloper"
            data["error"] = (
                "The lab server restarted while this ADK job was running. "
                "Start the lab without reload and run the build again."
            )
            job_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return {"job": data}
    return {"job": asdict(job)}


@app.get("/api/runs/{run_id}/download")
def download_run(run_id: str) -> FileResponse:
    run_path = _safe_run_path(run_id)
    dist_path = run_path / "dist"
    if not dist_path.exists():
        raise HTTPException(status_code=404, detail="This run has no built dist folder")
    archive_path = run_path / f"{run_id}-dist.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in dist_path.rglob("*"):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(dist_path))
    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename=f"{run_id}-dist.zip",
    )


@app.get("/runs/{run_id}/game/{file_path:path}")
def serve_game_file(run_id: str, file_path: str = "") -> FileResponse:
    run_path = _safe_run_path(run_id)
    dist_path = run_path / "dist"
    requested = (dist_path / (file_path or "index.html")).resolve()
    try:
        requested.relative_to(dist_path.resolve())
    except ValueError as error:
        raise HTTPException(status_code=404, detail="File not found") from error
    if requested.is_dir():
        requested = requested / "index.html"
    if not requested.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(requested)
