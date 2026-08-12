import asyncio
import os
import time

from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.tools.tool_context import ToolContext
from google.adk.workflow import START, Workflow

from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
)

from mcp import StdioServerParameters

from game_builder.schemas import GameManifest, ReviewDecision
from game_builder.tools import build_tools, preview_tools, workspace_tools


# =========================================================
# MODEL
# =========================================================

MODEL = "gemini-3.1-flash-lite"


# =========================================================
# DEVELOPMENT RATE LIMIT
# =========================================================
#
# Your current Gemini free-tier project allows 15 model
# requests per minute for this model.
#
# ADK agents that use tools may call the model multiple times
# during ONE agent turn:
#
# model -> tool -> model -> tool -> model
#
# Therefore we deliberately space ALL model requests.
#
# 5 seconds = at most ~12 requests/minute.
#
# This does NOT remove any agents, MCP, tools, or loops.
# It only slows model requests enough for local development.
# =========================================================

MIN_MODEL_INTERVAL_SECONDS = 5.0

_model_rate_lock = asyncio.Lock()
_last_model_call_time = 0.0


async def throttle_model_calls(callback_context, llm_request):
    """
    Rate-limit Gemini calls across all five ADK LlmAgents.

    This callback runs before every actual model invocation,
    including model continuations after tool calls.
    """

    global _last_model_call_time

    async with _model_rate_lock:
        now = time.monotonic()

        elapsed = now - _last_model_call_time

        wait_time = MIN_MODEL_INTERVAL_SECONDS - elapsed

        if wait_time > 0:
            print(
                f"[RATE LIMIT] Waiting {wait_time:.1f}s "
                f"before model call for "
                f"{callback_context.agent_name}"
            )

            await asyncio.sleep(wait_time)

        _last_model_call_time = time.monotonic()

    return None


# =========================================================
# PROJECT PATHS
# =========================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

GAME_WORKSPACE = os.path.join(
    PROJECT_ROOT,
    "game_workspace"
)

GAME_RUNS_DIR = os.path.join(
    GAME_WORKSPACE,
    "runs"
)

os.makedirs(
    GAME_RUNS_DIR,
    exist_ok=True,
)


# =========================================================
# GAME SERVER
# =========================================================
#
# Preview is started deterministically for the active run after
# typecheck and build pass.
#
# =========================================================

DEFAULT_PREVIEW_PORT = 5500


# =========================================================
# SHARED ADK STATE KEYS
# =========================================================

STATE_GAME_DESIGN = "game_design"
STATE_GAME_MANIFEST = "game_manifest"
STATE_TECHNICAL_PLAN = "technical_plan"
STATE_BUILD_SUMMARY = "build_summary"
STATE_TEST_REPORT = "test_report"
STATE_REVIEW_DECISION = "review_decision"
STATE_REVIEW_FEEDBACK = STATE_REVIEW_DECISION
STATE_CURRENT_RUN_ID = "current_run_id"
STATE_CURRENT_RUN_PATH = "current_run_path"
STATE_RUN_ID = "run_id"
STATE_RUN_PATH = "run_path"
STATE_CURRENT_ROUTE = "current_route"
STATE_ROUTE = STATE_CURRENT_ROUTE
STATE_ROUTE_HISTORY = "route_history"
STATE_ITERATION = "iteration"
STATE_ITERATION_COUNT = STATE_ITERATION
STATE_BUILD_RESULT = "build_result"
STATE_BUILD_GATE = STATE_BUILD_RESULT
STATE_BUILD_GATE_HISTORY = "build_gate_history"
STATE_TYPECHECK_RESULT = "typecheck_result"
STATE_PREVIEW_PORT = "preview_port"
STATE_PREVIEW_URL = "preview_url"
STATE_REPEATED_FAILURE_SIGNATURE = "repeated_failure_signature"
STATE_REPEATED_FAILURE_COUNT = "repeated_failure_count"
STATE_APPROVAL_STATUS = "approval_status"
STATE_WORKFLOW_STATUS = STATE_APPROVAL_STATUS
STATE_MAX_ITERATIONS = "max_iterations"
STATE_DEVELOPER_REVISION_COUNT = "developer_revision_count"
STATE_REPLAN_COUNT = "replan_count"
STATE_HUMAN_REVIEW_REQUIRED = "human_review_required"
STATE_HUMAN_REVIEW_REASON = "human_review_reason"
STATE_RUN_ID_ALIAS = STATE_RUN_ID
STATE_RUN_PATH_ALIAS = STATE_RUN_PATH

ROUTE_APPROVE = "APPROVE"
ROUTE_REVISE_DEVELOPER = "REVISE_DEVELOPER"
ROUTE_REPLAN = "REPLAN"
ROUTE_HUMAN_REVIEW = "HUMAN_REVIEW"

BUILD_ROUTE_SUCCESS = "BUILD_SUCCESS"
BUILD_ROUTE_FAILED = "BUILD_FAILED"

APPROVED = "APPROVED"
WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"

MAX_ROUTE_ITERATIONS = 3
MAX_REPEATED_FAILURES = 2

VALID_REVIEW_ROUTES = {
    ROUTE_APPROVE,
    ROUTE_REVISE_DEVELOPER,
    ROUTE_REPLAN,
    ROUTE_HUMAN_REVIEW,
}

PHASER_TEMPLATE_DIR = str(workspace_tools.PHASER_TEMPLATE_DIR)


def _first_route_label(text: str) -> str | None:
    for raw_line in text.splitlines():
        line = raw_line.strip().upper()
        if not line:
            continue
        if line in VALID_REVIEW_ROUTES:
            return line
        token = line.split()[0].rstrip(":")
        if token in VALID_REVIEW_ROUTES:
            return token
        return None
    return None


def choose_reviewer_route(
    review_feedback: str,
    iteration_count: int,
    repeated_failure_count: int,
) -> str:
    route = _first_route_label(review_feedback)

    if route == ROUTE_APPROVE:
        return ROUTE_APPROVE

    if (
        iteration_count >= MAX_ROUTE_ITERATIONS
        or repeated_failure_count >= MAX_REPEATED_FAILURES
    ):
        return ROUTE_HUMAN_REVIEW

    if route in VALID_REVIEW_ROUTES:
        return route

    return ROUTE_HUMAN_REVIEW


def failure_signature(text: str) -> str:
    normalized = " ".join(text.lower().split())
    return normalized[:240]


def update_repeated_failure_state(state, latest_failure_text: str) -> int:
    signature = failure_signature(latest_failure_text)
    previous_signature = state.get(STATE_REPEATED_FAILURE_SIGNATURE)
    previous_count = int(state.get(STATE_REPEATED_FAILURE_COUNT, 0) or 0)

    if signature and signature == previous_signature:
        count = previous_count + 1
    else:
        count = 1 if signature else 0

    state[STATE_REPEATED_FAILURE_SIGNATURE] = signature
    state[STATE_REPEATED_FAILURE_COUNT] = count
    return count


def record_route_state(state, route: str) -> None:
    history = list(state.get(STATE_ROUTE_HISTORY, []) or [])
    history.append(
        {
            "route": route,
            "iteration": int(state.get(STATE_ITERATION_COUNT, 0) or 0),
        }
    )
    state[STATE_ROUTE] = route
    state[STATE_CURRENT_ROUTE] = route
    state[STATE_ROUTE_HISTORY] = history


def _coerce_review_decision(review_feedback: str) -> ReviewDecision:
    feedback = str(review_feedback or "").strip()
    route = ROUTE_HUMAN_REVIEW if not feedback else choose_reviewer_route(
        review_feedback=feedback,
        iteration_count=int(
            __import__("builtins").locals().get("_state", {}).get(STATE_ITERATION_COUNT, 0) or 0
        ) if False else 0,
        repeated_failure_count=0,
    )
    defects: list[str] = []
    required_changes: list[str] = []
    for line in feedback.splitlines():
        clean = line.strip()
        if not clean:
            continue
        if clean.startswith(("APPROVE", "REVISE_DEVELOPER", "REPLAN", "HUMAN_REVIEW")):
            continue
        if clean.startswith(("1.", "2.", "-", "*")):
            defects.append(clean[2:].strip() if clean.startswith("1.") or clean.startswith("2.") else clean.strip("-* "))
        elif clean.lower().startswith("change:"):
            required_changes.append(clean.split(":", 1)[1].strip())
        elif clean.lower().startswith("required"):
            required_changes.append(clean)
    if not defects and "defect" in feedback.lower():
        defects.append(feedback)
    score = (
        90 if route == ROUTE_APPROVE
        else 75 if route == ROUTE_REVISE_DEVELOPER
        else 65 if route == ROUTE_REPLAN
        else 40
    )
    return ReviewDecision(
        route=route,
        score=score,
        reasoning=feedback or "No review reasoning supplied.",
        defects=defects,
        required_changes=required_changes,
    )


def record_reviewer_route(callback_context: Context):
    state = callback_context.state
    if state.get(STATE_ROUTE) == ROUTE_APPROVE:
        callback_context.actions.route = ROUTE_APPROVE
        state[STATE_WORKFLOW_STATUS] = APPROVED
        state[STATE_APPROVAL_STATUS] = APPROVED
        return None

    review_feedback = str(state.get(STATE_REVIEW_FEEDBACK, ""))
    repeated_failure_count = update_repeated_failure_state(
        state,
        review_feedback,
    )
    route = choose_reviewer_route(
        review_feedback=review_feedback,
        iteration_count=int(state.get(STATE_ITERATION_COUNT, 0) or 0),
        repeated_failure_count=repeated_failure_count,
    )
    decision = _coerce_review_decision(review_feedback)
    decision.route = route
    state[STATE_REVIEW_DECISION] = decision.model_dump()
    state[STATE_REVIEW_FEEDBACK] = review_feedback
    state[STATE_CURRENT_ROUTE] = route
    state[STATE_ROUTE] = route
    state[STATE_APPROVAL_STATUS] = APPROVED if route == ROUTE_APPROVE else WAITING_FOR_HUMAN if route == ROUTE_HUMAN_REVIEW else "IN_PROGRESS"
    state[STATE_HUMAN_REVIEW_REQUIRED] = route == ROUTE_HUMAN_REVIEW
    state[STATE_HUMAN_REVIEW_REASON] = (
        decision.reasoning if route == ROUTE_HUMAN_REVIEW else ""
    )
    state[STATE_MAX_ITERATIONS] = MAX_ROUTE_ITERATIONS
    record_route_state(state, route)
    callback_context.actions.route = route

    if route == ROUTE_APPROVE:
        state[STATE_WORKFLOW_STATUS] = APPROVED
        state[STATE_APPROVAL_STATUS] = APPROVED
    elif route == ROUTE_HUMAN_REVIEW:
        state[STATE_WORKFLOW_STATUS] = WAITING_FOR_HUMAN
        state[STATE_APPROVAL_STATUS] = WAITING_FOR_HUMAN

    return None


def _extract_design_field(design: str, field_name: str) -> str:
    prefix = f"{field_name}:"
    for line in design.splitlines():
        if line.strip().upper().startswith(prefix):
            return line.split(":", 1)[1].strip()
    return ""


def _default_manifest_from_state(state) -> GameManifest:
    design = str(state.get(STATE_GAME_DESIGN, ""))
    title = _extract_design_field(design, "TITLE") or "Generated Phaser Game"
    genre = _extract_design_field(design, "GENRE") or "Arcade"

    return GameManifest(
        title=title,
        genre=genre,
        player_count=1,
        camera="STATIC",
        physics="ARCADE",
        scenes=["Boot", "Preloader", "MainMenu", "Game", "GameOver"],
        mechanics=["player input", "scoring", "restart"],
        required_assets=[],
        acceptance_tests=[
            "Phaser app boots without runtime errors",
            "window.__GAME_TEST__ exposes getState, reset, and errors",
            "Controls produce observable runtime state changes",
            "Reset returns the game to a sensible initial state",
        ],
        has_menu=True,
        has_audio=False,
        has_particles=False,
        has_progression=False,
    )


def create_run_workspace(ctx: Context):
    """
    Create one isolated Phaser project for this user request.
    Revisions continue inside the same active run.
    """
    state = ctx.state
    state.setdefault(STATE_MAX_ITERATIONS, MAX_ROUTE_ITERATIONS)
    state.setdefault(STATE_ITERATION_COUNT, 0)
    state.setdefault(STATE_DEVELOPER_REVISION_COUNT, 0)
    state.setdefault(STATE_REPLAN_COUNT, 0)
    state.setdefault(STATE_HUMAN_REVIEW_REQUIRED, False)
    state.setdefault(STATE_HUMAN_REVIEW_REASON, "")
    state.setdefault(STATE_APPROVAL_STATUS, "PENDING")

    existing_run_id = state.get(STATE_CURRENT_RUN_ID) or state.get(STATE_RUN_ID)
    if existing_run_id:
        existing_run_path = workspace_tools.get_run_path(str(existing_run_id))
        state[STATE_CURRENT_RUN_ID] = str(existing_run_id)
        state[STATE_RUN_ID] = str(existing_run_id)
        state[STATE_CURRENT_RUN_PATH] = str(existing_run_path)
        state[STATE_RUN_PATH] = str(existing_run_path)
        return "RUN_WORKSPACE_EXISTS"

    run_id = workspace_tools.create_next_run_id()
    run_path = workspace_tools.create_run_from_phaser_template(run_id)
    manifest = _default_manifest_from_state(state)

    state[STATE_CURRENT_RUN_ID] = run_id
    state[STATE_RUN_ID] = run_id
    state[STATE_CURRENT_RUN_PATH] = str(run_path)
    state[STATE_RUN_PATH] = str(run_path)
    state[STATE_GAME_MANIFEST] = manifest.model_dump()
    state[STATE_PREVIEW_PORT] = DEFAULT_PREVIEW_PORT
    state[STATE_MAX_ITERATIONS] = MAX_ROUTE_ITERATIONS
    state[STATE_APPROVAL_STATUS] = "PENDING"

    return "RUN_WORKSPACE_CREATED"


def build_gate(ctx: Context):
    """
    Run after every GameplayDeveloper turn. A successful build
    automatically routes to Playtester for a real retest.
    """

    iteration_count = int(ctx.state.get(STATE_ITERATION_COUNT, 0) or 0) + 1
    ctx.state[STATE_ITERATION_COUNT] = iteration_count
    ctx.state[STATE_ITERATION] = iteration_count
    ctx.state[STATE_MAX_ITERATIONS] = MAX_ROUTE_ITERATIONS
    run_id = str(ctx.state.get(STATE_CURRENT_RUN_ID, ctx.state.get(STATE_RUN_ID, "")))

    if not run_id:
        ctx.state[STATE_TEST_REPORT] = (
            "OVERALL: FAIL\n"
            "PAGE_LOAD: NOT_RUN\n"
            "TEST_API: NOT_RUN\n"
            "RUNTIME_ERRORS: NO_ACTIVE_RUN\n"
            "CONTROLS: NOT_RUN\n"
            "RESET: NOT_RUN\n"
            "DESIGN_COMPLIANCE: NOT_RUN\n"
            "DEFECTS:\n1. No active generated run exists."
        )
        ctx.state[STATE_BUILD_RESULT] = {
            "success": False,
            "exit_code": 1,
            "command": "",
            "stdout": "",
            "stderr": "No active generated run exists.",
            "log_path": "",
            "status": BUILD_ROUTE_FAILED,
            "iteration": iteration_count,
        }
        ctx.state[STATE_BUILD_GATE] = ctx.state[STATE_BUILD_RESULT]
        ctx.route = BUILD_ROUTE_FAILED
        return "BUILD_GATE_FAIL"

    typecheck_result = build_tools.npm_typecheck(run_id)
    ctx.state[STATE_TYPECHECK_RESULT] = typecheck_result.model_dump()

    if not typecheck_result.success:
        output = "\n".join(
            str(part).strip()
            for part in [
                getattr(typecheck_result, "stdout", ""),
                getattr(typecheck_result, "stderr", ""),
            ]
            if str(part).strip()
        )
        build_record = typecheck_result.model_dump()
        build_record["iteration"] = iteration_count
        build_record["status"] = BUILD_ROUTE_FAILED
        history = list(ctx.state.get(STATE_BUILD_GATE_HISTORY, []) or [])
        history.append(build_record)
        ctx.state[STATE_BUILD_RESULT] = build_record
        ctx.state[STATE_BUILD_GATE] = build_record
        ctx.state[STATE_BUILD_GATE_HISTORY] = history
        ctx.state[STATE_TEST_REPORT] = (
            "OVERALL: FAIL\n"
            "PAGE_LOAD: NOT_RUN\n"
            "TEST_API: NOT_RUN\n"
            "RUNTIME_ERRORS: TYPECHECK_FAILED\n"
            "CONTROLS: NOT_RUN\n"
            "RESET: NOT_RUN\n"
            "DESIGN_COMPLIANCE: NOT_RUN\n"
            f"DEFECTS:\n1. Phaser TypeScript typecheck failed in "
            f"iteration {iteration_count}.\n\n{output[-2000:]}"
        )
        ctx.route = BUILD_ROUTE_FAILED
        return "BUILD_GATE_FAIL"

    result = build_tools.npm_build(run_id)

    output = "\n".join(
        str(part).strip()
        for part in [
            getattr(result, "stdout", ""),
            getattr(result, "stderr", ""),
        ]
        if str(part).strip()
    )
    build_record = result.model_dump()
    build_record["iteration"] = iteration_count
    build_record["status"] = (
        BUILD_ROUTE_SUCCESS
        if result.success
        else BUILD_ROUTE_FAILED
    )

    history = list(ctx.state.get(STATE_BUILD_GATE_HISTORY, []) or [])
    history.append(build_record)

    ctx.state[STATE_BUILD_RESULT] = build_record
    ctx.state[STATE_BUILD_GATE] = build_record
    ctx.state[STATE_BUILD_GATE_HISTORY] = history

    if result.success:
        port = int(ctx.state.get(STATE_PREVIEW_PORT, DEFAULT_PREVIEW_PORT))
        preview_url = preview_tools.start_preview(run_id, port)
        ctx.state[STATE_PREVIEW_URL] = preview_url
        ctx.route = BUILD_ROUTE_SUCCESS
        return "BUILD_GATE_PASS"

    ctx.state[STATE_TEST_REPORT] = (
        "OVERALL: FAIL\n"
        "PAGE_LOAD: NOT_RUN\n"
        "TEST_API: NOT_RUN\n"
        "RUNTIME_ERRORS: BUILD_FAILED\n"
        "CONTROLS: NOT_RUN\n"
        "RESET: NOT_RUN\n"
        "DESIGN_COMPLIANCE: NOT_RUN\n"
        f"DEFECTS:\n1. Phaser production build failed in iteration "
        f"{iteration_count}.\n\n{output[-2000:]}"
    )
    ctx.route = BUILD_ROUTE_FAILED
    return "BUILD_GATE_FAIL"


def finalize_run(ctx: Context):
    ctx.state[STATE_WORKFLOW_STATUS] = APPROVED
    ctx.route = ROUTE_APPROVE
    return "FINALIZED"


def human_review(ctx: Context):
    ctx.state[STATE_WORKFLOW_STATUS] = WAITING_FOR_HUMAN
    ctx.route = ROUTE_HUMAN_REVIEW
    return "WAITING_FOR_HUMAN"


# =========================================================
# FILESYSTEM MCP
# =========================================================
#
# REAL MCP SERVER #1
#
# GameplayDeveloper uses this.
#
# We expose only two tools to reduce unnecessary
# model/tool round-trips:
#
# read_text_file
# write_file
#
# =========================================================

filesystem_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="cmd",
            args=[
                "/c",
                "npx",
                "-y",
                "@modelcontextprotocol/server-filesystem",
                GAME_RUNS_DIR,
            ],
        ),
    ),
    tool_filter=[
        "read_text_file",
        "write_file",
    ],
)


# =========================================================
# PLAYWRIGHT MCP
# =========================================================
#
# REAL MCP SERVER #2
#
# Playtester uses Microsoft's Playwright MCP.
#
# We intentionally expose only:
#
# browser_navigate
# browser_evaluate
#
# Instead of making 10+ browser calls, the Playtester runs
# one larger browser evaluation containing multiple tests.
#
# The browser remains headed so you can SEE it during the
# professor demonstration.
# =========================================================

playwright_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="cmd",
            args=[
                "/c",
                "npx",
                "-y",
                "@playwright/mcp@latest",
                "--browser",
                "msedge",
                "--isolated",
                "--console-level",
                "error",
                "--viewport-size",
                "1280x800",
            ],
        ),
    ),
    tool_filter=[
        "browser_navigate",
        "browser_evaluate",
    ],
)


# =========================================================
# REAL LOOP EXIT TOOL
# =========================================================
#
# ONLY BugReviewer receives this tool.
#
# Developer cannot approve itself.
# Playtester cannot approve the game.
#
# Reviewer alone controls approval.
# =========================================================

def exit_loop(tool_context: ToolContext):
    """
    Signal approval after independent browser testing passes
    and BugReviewer approves.
    """

    print(
        f"[TOOL] exit_loop called by "
        f"{tool_context.agent_name}"
    )

    tool_context.actions.escalate = True
    tool_context.actions.skip_summarization = True
    tool_context.actions.route = ROUTE_APPROVE
    record_route_state(tool_context.state, ROUTE_APPROVE)
    tool_context.state[STATE_WORKFLOW_STATUS] = APPROVED

    return {
        "status": "APPROVED",
        "reason": (
            "Independent browser testing passed and "
            "BugReviewer approved the implementation."
        ),
    }


# =========================================================
# AGENT 1 — GAME DESIGNER
# =========================================================

game_designer = LlmAgent(
    name="GameDesigner",
    model=MODEL,

    before_model_callback=throttle_model_calls,

    instruction="""
You are the Game Designer.

Interpret the user's natural-language request for a compact
2D browser game.

Produce a concise structured design containing:

TITLE:
GENRE:
OBJECTIVE:
CONTROLS:
CORE MECHANICS:
SCORING:
WIN CONDITION:
LOSS CONDITION:
RESTART BEHAVIOR:

Stay faithful to the user's request.

Do not write code.

Do not test anything.

Output only the game design.
""",

    description=(
        "Interprets the user's idea and produces the "
        "authoritative game-design specification."
    ),

    output_key=STATE_GAME_DESIGN,
)


# =========================================================
# AGENT 2 — TECHNICAL PLANNER
# =========================================================

technical_planner = LlmAgent(
    name="TechnicalPlanner",
    model=MODEL,

    before_model_callback=throttle_model_calls,

    include_contents="none",

    instruction="""
You are the Technical Planner.

GAME DESIGN:

{game_design}

LATEST REVIEW FEEDBACK:

{review_decision?}

Create a concise implementation plan for one isolated Phaser 2D
TypeScript project generated from the approved template.

The deterministic runtime will create:

game_workspace/runs/<current_run_id>/

The implementation should edit project files inside that active
run only, usually:

- src/game/scenes/Game.ts
- src/game/scenes/MainMenu.ts
- src/game/scenes/GameOver.ts
- src/game/main.ts
- public/style.css

Do not plan edits to game_templates/phaser-2d.
Do not choose another engine.

Define:

GAME MANIFEST:
engine must be PHASER_2D

ARCHITECTURE:
GAME STATE:
INPUT HANDLING:
GAME LOOP:
COLLISIONS / INTERACTIONS:
SCORING:
WIN / LOSS:
RESTART:
ACCEPTANCE TESTS:

The implementation MUST also expose:

window.__GAME_TEST__

with at least:

getState()
reset()
errors

getState() must return JSON-serializable REAL runtime state.

For a Pong-style game it should expose useful values such as:

player1Score
player2Score
leftPaddleY
rightPaddleY
ballX
ballY
running
gameOver
winner

The game must also capture JavaScript runtime errors into:

window.__GAME_TEST__.errors

Do not write the implementation.

If LATEST REVIEW FEEDBACK begins with REPLAN, revise the
technical plan to directly address the BugReviewer's defects
before GameplayDeveloper runs again.

Output only the technical plan.
""",

    description=(
        "Transforms the game design into implementation "
        "architecture and objective acceptance criteria."
    ),

    output_key=STATE_TECHNICAL_PLAN,
)


# =========================================================
# AGENT 3 — GAMEPLAY DEVELOPER
# =========================================================
#
# This agent is inside the ADK routing workflow.
#
# INITIAL ITERATION:
#
#   edits the active Phaser run through Filesystem MCP
#
# REVISION ITERATION:
#
#   reads existing active-run files through MCP
#   repairs it
#   writes replacements through MCP
#
# It CANNOT approve itself.
# =========================================================

gameplay_developer = LlmAgent(
    name="GameplayDeveloper",
    model=MODEL,

    before_model_callback=throttle_model_calls,

    include_contents="none",

    instruction=f"""
You are the Gameplay Developer.

GAME DESIGN:

{{game_design}}

TECHNICAL PLAN:

{{technical_plan}}

LATEST REVIEW FEEDBACK:

{{review_decision?}}

You have access to a REAL filesystem through Model Context
Protocol.

The production artifact is:

game_workspace/runs/{{current_run_id}}/

The Filesystem MCP root is scoped to:

{GAME_RUNS_DIR}

Use run-relative paths such as:

{{current_run_id}}/src/game/scenes/Game.ts
{{current_run_id}}/src/game/scenes/MainMenu.ts
{{current_run_id}}/src/game/scenes/GameOver.ts
{{current_run_id}}/public/style.css

Do not read or write game_templates/phaser-2d.

============================================================
INITIAL BUILD
============================================================

If LATEST REVIEW FEEDBACK is empty:

Create the first implementation.

Use the existing Phaser project inside the active run.
Call write_file for the TypeScript/CSS files that must change.

============================================================
REVISION
============================================================

If LATEST REVIEW FEEDBACK contains:

REVISE_DEVELOPER

or:

REPLAN

then this is a revision cycle.

First call read_text_file on:

the active run files you need to repair.

Study the existing implementation.

Then fix EVERY defect identified by BugReviewer.

Call write_file for the corrected complete files.

============================================================
GAME REQUIREMENTS
============================================================

The active run is a Phaser 2D TypeScript project.

Do NOT use:

- CDNs
- network requests
- server-side code
- new npm dependencies unless the TechnicalPlanner explicitly required them

The game must actually implement the Game Design and
Technical Plan.

It must contain:

- visible title
- visible instructions
- actual playable game
- working controls
- scoring where applicable
- win/loss behavior
- restart functionality
- clear game state

============================================================
MANDATORY TEST INTERFACE
============================================================

The game MUST expose:

window.__GAME_TEST__

It MUST provide:

window.__GAME_TEST__.getState()

window.__GAME_TEST__.reset()

window.__GAME_TEST__.errors

getState() must return REAL current game state.

Do not return hard-coded fake test values.

For Pong, expose at minimum:

player1Score
player2Score
leftPaddleY
rightPaddleY
ballX
ballY
running
gameOver
winner

============================================================
ERROR CAPTURE
============================================================

Capture runtime errors.

For example, the implementation should register handlers for:

window error events

and

unhandledrejection

and store useful messages inside:

window.__GAME_TEST__.errors

============================================================
IMPORTANT
============================================================

Do not merely describe the implementation.

You MUST actually call the MCP filesystem tool.

After the MCP write succeeds, return only a SHORT summary:

BUILD_COMPLETE

and one or two sentences describing what was created/fixed.

Do NOT output entire source files as your final message.

Do NOT call exit_loop.

Only BugReviewer may approve the game.
""",

    description=(
        "Creates and repairs the executable game using the "
        "real Filesystem MCP server."
    ),

    tools=[
        filesystem_mcp,
    ],

    output_key=STATE_BUILD_SUMMARY,
)


# =========================================================
# AGENT 4 — PLAYTESTER
# =========================================================
#
# REAL ENVIRONMENT TESTER.
#
# This agent uses Playwright MCP.
#
# Instead of many small browser calls:
#
# navigate
# snapshot
# key
# key
# evaluate
# screenshot
# ...
#
# we intentionally use:
#
# 1. browser_navigate
# 2. browser_evaluate
#
# The evaluate call performs multiple checks in the actual
# browser environment and returns one evidence object.
# =========================================================

playtester = LlmAgent(
    name="Playtester",
    model=MODEL,

    before_model_callback=throttle_model_calls,

    include_contents="none",

    instruction=f"""
You are the independent Playtester.

You do NOT modify source code.

GAME DESIGN:

{{game_design}}

TECHNICAL PLAN:

{{technical_plan}}

BUILD SUMMARY:

{{build_summary}}

BUILD RESULT:

{{build_result?}}

Test the REAL generated game at:

{{preview_url}}

You have access to Microsoft's real Playwright MCP server.

============================================================
IMPORTANT QUOTA RULE
============================================================

Use ONLY TWO MCP calls unless something prevents testing:

CALL 1:
browser_navigate

CALL 2:
browser_evaluate

Do not make many small browser calls.

============================================================
CALL 1 — NAVIGATE
============================================================

Use browser_navigate to open:

{{preview_url}}

============================================================
CALL 2 — COMPLETE BROWSER TEST
============================================================

Then make ONE browser_evaluate call.

The JavaScript function passed to browser_evaluate should
perform a compact smoke test inside the REAL browser page.

It should inspect:

1. document.readyState

2. document.title

3. whether the visible game UI exists

4. whether window.__GAME_TEST__ exists

5. whether getState is a function

6. whether reset is a function

7. initial state from:

   window.__GAME_TEST__.getState()

8. runtime errors from:

   window.__GAME_TEST__.errors

9. control behavior

For keyboard games, dispatch realistic keyboard events
matching the controls from the Game Design.

Example pattern:

window.dispatchEvent(
    new KeyboardEvent(
        "keydown",
        {{ key: "w" }}
    )
)

Wait briefly if necessary.

Then dispatch keyup.

10. obtain state again after interaction

11. invoke:

window.__GAME_TEST__.reset()

12. obtain state after reset

Return ONE JSON-serializable object containing all evidence.

============================================================
PASS CRITERIA
============================================================

Return:

OVERALL: PASS

only if:

- page loaded
- game UI exists
- test API exists
- state is readable
- there are no critical captured runtime errors
- controls cause plausible state changes where applicable
- reset returns the game to a sensible initial state
- implementation reasonably matches the Game Design

Otherwise return:

OVERALL: FAIL

and clearly identify every observed defect.

Your final response must be concise and structured:

OVERALL:
PAGE_LOAD:
TEST_API:
RUNTIME_ERRORS:
CONTROLS:
RESET:
DESIGN_COMPLIANCE:
DEFECTS:

Never claim a test passed without browser evidence.
""",

    description=(
        "Uses real Playwright MCP browser automation to "
        "test the executable game environment."
    ),

    tools=[
        playwright_mcp,
    ],

    output_key=STATE_TEST_REPORT,
)


# =========================================================
# AGENT 5 — BUG REVIEWER
# =========================================================
#
# Independent authority.
#
# Developer cannot approve.
# Playtester cannot approve.
#
# Reviewer decides:
#
# APPROVE -> finalize the run
#
# REVISE_DEVELOPER -> send work back to GameplayDeveloper
#
# REPLAN -> send work back through TechnicalPlanner
#
# HUMAN_REVIEW -> stop autonomous routing for human inspection.
# =========================================================

bug_reviewer = LlmAgent(
    name="BugReviewer",
    model=MODEL,

    before_model_callback=throttle_model_calls,
    after_agent_callback=record_reviewer_route,

    include_contents="none",

    instruction="""
You are the independent Bug Reviewer and routing authority.

GAME DESIGN:

{game_design}

TECHNICAL PLAN:

{technical_plan}

REAL BROWSER TEST REPORT:

{test_report}

TYPECHECK RESULT:

{typecheck_result?}

BUILD RESULT:

{build_result?}

Evaluate the Playtester's evidence.

You alone control production routing.

Your final response MUST begin with exactly one route label:

APPROVE
REVISE_DEVELOPER
REPLAN
HUMAN_REVIEW

============================================================
APPROVE
============================================================

Approve ONLY if the report contains:

OVERALL: PASS

and there are no critical defects.

If the game passes:

Call exit_loop.

Then begin your final answer with:

APPROVE

Do not request unnecessary cosmetic changes.

============================================================
REVISE_DEVELOPER
============================================================

If browser evidence shows implementation defects that the
current technical plan can still support:

Do NOT call exit_loop.

Return exactly this routing label first:

REVISE_DEVELOPER

Then provide a concise defect list containing only
evidence-supported problems.

Example:

REVISE_DEVELOPER

1. Restart did not reset both scores.
2. Right paddle did not respond to ArrowDown.
3. Runtime error occurred during collision.

Do not modify the game yourself.

Do not invent defects.

============================================================
REPLAN
============================================================

If the test/build evidence shows the implementation plan is
wrong, incomplete, or missing acceptance criteria, do NOT call
exit_loop.

Return exactly this routing label first:

REPLAN

Then provide concise plan-level defects that TechnicalPlanner
must address.

============================================================
HUMAN_REVIEW
============================================================

If failures are repeated, unrecoverable, blocked by the runtime,
or unsafe to continue autonomously, do NOT call exit_loop.

Return exactly this routing label first:

HUMAN_REVIEW

Then explain what a human must inspect.
""",

    description=(
        "Independently evaluates browser-test evidence and "
        "controls whether the workflow revises or exits."
    ),

    tools=[
        exit_loop,
    ],

    output_key=STATE_REVIEW_FEEDBACK,
)


# =========================================================
# ROOT GOOGLE ADK ROUTING WORKFLOW
# =========================================================
#
# This is NOT frontend logic and not a simulated router.
# It is the actual Google ADK Workflow graph.
#
# START
#   -> GameDesigner
#   -> create_run_workspace
#   -> TechnicalPlanner
#   -> GameplayDeveloper
#   -> build_gate
#        BUILD_SUCCESS -> Playtester -> BugReviewer
#        BUILD_FAILED  -> BugReviewer
#
# BugReviewer emits exactly one production route:
#
# APPROVE
#   -> finalize_run
#
# REVISE_DEVELOPER
#   -> GameplayDeveloper -> build_gate -> Playtester -> BugReviewer
#
# REPLAN
#   -> TechnicalPlanner -> create_run_workspace -> GameplayDeveloper
#      -> build_gate -> Playtester -> BugReviewer
#
# HUMAN_REVIEW
#   -> human_review
#
# The graph preserves route traceability through ADK events
# with actions.route.
# =========================================================

root_agent = Workflow(
    name="MultiAgentGameBuilder",

    edges=[
        (
            START,
            game_designer,
            create_run_workspace,
            technical_planner,
            gameplay_developer,
            build_gate,
            {
                BUILD_ROUTE_SUCCESS: playtester,
                BUILD_ROUTE_FAILED: bug_reviewer,
            },
        ),
        (
            playtester,
            bug_reviewer,
        ),
        (
            bug_reviewer,
            {
                ROUTE_APPROVE: finalize_run,
                ROUTE_REVISE_DEVELOPER: gameplay_developer,
                ROUTE_REPLAN: technical_planner,
                ROUTE_HUMAN_REVIEW: human_review,
            },
        ),
    ],

    description="""
A genuine Google ADK multi-agent software-engineering system.

Five specialized agents collaborate to:

1. design a browser game
2. create a technical plan
3. implement executable code
4. run a production build gate
5. test the real browser environment
6. independently review the evidence
7. route through approval, developer revision, replanning, or human review
8. automatically rebuild every developer revision
9. automatically retest every successful rebuild

The runtime uses:

- Google Agent Development Kit
- LlmAgent
- Workflow
- shared session state
- before-model callbacks
- after-agent route callbacks
- Filesystem MCP
- Microsoft Playwright MCP
- real filesystem operations
- Phaser production build workflow
- real browser execution
- objective runtime evidence
- reviewer-controlled routing
- bounded autonomous iteration

The UI does not simulate these actions.
Google ADK executes the workflow graph.
""",
)


# Backward-compatible alias for docs/tests that still look for
# the Phase 1 loop symbol. Production routing uses root_agent.
build_test_review_loop = root_agent


runtime_agents = [
    game_designer,
    technical_planner,
    gameplay_developer,
    playtester,
    bug_reviewer,
]
