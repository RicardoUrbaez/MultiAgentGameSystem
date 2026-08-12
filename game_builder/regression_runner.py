from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

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


def run_regression(case_name: str) -> RegressionResult:
    case = get_regression_case(case_name)
    started = time.monotonic()
    command = [sys.executable, "-m", "google.adk.cli", "run", "game_builder", case.prompt]
    completed = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
    result = RegressionResult(
        case=case.name,
        genre=case.genre,
        duration_seconds=round(time.monotonic() - started, 3),
        command_exit_code=completed.returncode,
    )
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / f"{case.name}.json").write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
    (RESULTS_DIR / f"{case.name}.log").write_text(completed.stdout + "\n" + completed.stderr, encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an ADK multi-genre regression case.")
    parser.add_argument("case", help="Case name, such as pong or breakout")
    parser.add_argument("--print-prompt", action="store_true", help="Print the resolved prompt without invoking ADK")
    args = parser.parse_args()
    case = get_regression_case(args.case)
    if args.print_prompt:
        print(case.prompt)
        return 0
    print(json.dumps(asdict(run_regression(case.name)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
