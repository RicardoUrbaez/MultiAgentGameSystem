from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import load_dotenv

from .regression_cases import get_regression_case

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "game_workspace" / "regressions"


@dataclass
class RegressionResult:
    case: str
    genre: str
    run_id: str | None = None
    build_success: bool | None = None
    browser_test_success: bool | None = None
    first_pass_approval: bool | None = None
    revision_count: int | None = None
    replan_count: int | None = None
    final_reviewer_score: int | None = None
    human_review_required: bool | None = None
    duration_seconds: float | None = None
    command_exit_code: int | None = None
    timed_out: bool = False


def run_regression(
    case_name: str,
    demo_mode: bool = False,
    timeout_seconds: int = 180,
) -> RegressionResult:
    case = get_regression_case(case_name)
    started = time.monotonic()
    load_dotenv(PROJECT_ROOT / "game_builder" / ".env")
    command = [
        sys.executable,
        "-m",
        "google.adk.cli",
        "run",
        "--state",
        json.dumps({"demo_mode": demo_mode}),
        "game_builder",
        case.prompt,
    ]
    timed_out = False
    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            check=False,
            timeout=timeout_seconds,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as error:
        timed_out = True
        stdout = error.stdout or ""
        stderr = (error.stderr or "") + f"\nRegression timed out after {timeout_seconds} seconds."
        exit_code = None
    result = RegressionResult(
        case=case.name,
        genre=case.genre,
        duration_seconds=round(time.monotonic() - started, 3),
        command_exit_code=exit_code,
        timed_out=timed_out,
    )
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / f"{case.name}.json").write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
    (RESULTS_DIR / f"{case.name}.log").write_text(stdout + "\n" + stderr, encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an ADK multi-genre regression case.")
    parser.add_argument("case", help="Case name, such as pong or breakout")
    parser.add_argument("--print-prompt", action="store_true", help="Print the resolved prompt without invoking ADK")
    parser.add_argument("--demo-mode", action="store_true", help="Request one real, controlled implementation defect for the revision-loop demonstration")
    parser.add_argument("--timeout", type=int, default=180, help="Maximum seconds for the real ADK command before preserving a timeout result")
    args = parser.parse_args()
    case = get_regression_case(args.case)
    if args.print_prompt:
        print(case.prompt)
        return 0
    print(json.dumps(asdict(run_regression(case.name, args.demo_mode, args.timeout)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
