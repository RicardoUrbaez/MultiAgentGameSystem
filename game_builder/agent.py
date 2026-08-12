import asyncio
import os
import time

from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent
from google.adk.tools.tool_context import ToolContext

from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
)

from mcp import StdioServerParameters


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

os.makedirs(
    GAME_WORKSPACE,
    exist_ok=True,
)

GAME_INDEX_PATH = os.path.join(
    GAME_WORKSPACE,
    "index.html",
)


# =========================================================
# GAME SERVER
# =========================================================
#
# Keep this running separately:
#
# python -m http.server 5500 --directory .\game_workspace
#
# =========================================================

GAME_URL = "http://127.0.0.1:5500/index.html"


# =========================================================
# SHARED ADK STATE KEYS
# =========================================================

STATE_GAME_DESIGN = "game_design"
STATE_TECHNICAL_PLAN = "technical_plan"
STATE_BUILD_SUMMARY = "build_summary"
STATE_TEST_REPORT = "test_report"
STATE_REVIEW_FEEDBACK = "review_feedback"


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
                GAME_WORKSPACE,
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
    Exit the real Google ADK LoopAgent after independent
    browser testing passes and BugReviewer approves.
    """

    print(
        f"[TOOL] exit_loop called by "
        f"{tool_context.agent_name}"
    )

    tool_context.actions.escalate = True
    tool_context.actions.skip_summarization = True

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

Create a concise implementation plan for ONE completely
self-contained browser file:

index.html

The file must contain:

- HTML
- CSS inside <style>
- JavaScript inside <script>

No external dependencies are permitted.

Define:

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
# This agent is INSIDE the LoopAgent.
#
# INITIAL ITERATION:
#
#   writes index.html through Filesystem MCP
#
# REVISION ITERATION:
#
#   reads existing index.html through MCP
#   repairs it
#   writes replacement through MCP
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

{{review_feedback?}}

You have access to a REAL filesystem through Model Context
Protocol.

The production artifact is:

{GAME_INDEX_PATH}

============================================================
INITIAL BUILD
============================================================

If LATEST REVIEW FEEDBACK is empty:

Create the first implementation.

Call write_file exactly once.

Write a complete self-contained index.html.

============================================================
REVISION
============================================================

If LATEST REVIEW FEEDBACK contains:

REVISE_DEVELOPER

then this is a revision cycle.

First call read_text_file on:

{GAME_INDEX_PATH}

Study the existing implementation.

Then fix EVERY defect identified by BugReviewer.

Call write_file exactly once to replace index.html with
the corrected complete implementation.

============================================================
GAME REQUIREMENTS
============================================================

index.html must contain:

- <!DOCTYPE html>
- complete HTML
- CSS inside <style>
- JavaScript inside <script>

Do NOT use:

- external libraries
- external scripts
- external stylesheets
- CDNs
- network requests
- server-side code

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

Do NOT output the entire source code as your final message.

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

Test the REAL generated game at:

{GAME_URL}

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

{GAME_URL}

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
# PASS -> exit real LoopAgent
#
# FAIL -> REVISE_DEVELOPER
#
# The LoopAgent then automatically starts another iteration.
# =========================================================

bug_reviewer = LlmAgent(
    name="BugReviewer",
    model=MODEL,

    before_model_callback=throttle_model_calls,

    include_contents="none",

    instruction="""
You are the independent Bug Reviewer and routing authority.

GAME DESIGN:

{game_design}

TECHNICAL PLAN:

{technical_plan}

REAL BROWSER TEST REPORT:

{test_report}

Evaluate the Playtester's evidence.

============================================================
APPROVE
============================================================

Approve ONLY if the report contains:

OVERALL: PASS

and there are no critical defects.

If the game passes:

Call exit_loop.

Do not request unnecessary cosmetic changes.

============================================================
REVISE
============================================================

If any important test failed:

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
# REAL GOOGLE ADK AGENTIC LOOP
# =========================================================
#
# This is NOT frontend logic.
#
# This is the actual Google ADK LoopAgent.
#
#
#       GameplayDeveloper
#              |
#              | Filesystem MCP
#              v
#        real index.html
#              |
#              v
#         Playtester
#              |
#              | Playwright MCP
#              v
#         real browser
#              |
#              v
#         BugReviewer
#              |
#         +----+----+
#         |         |
#       PASS       FAIL
#         |         |
#         v         |
#     exit_loop     |
#                   |
#                   +------------+
#                                |
#                         ADK next iteration
#                                |
#                                v
#                       GameplayDeveloper
#
# =========================================================

build_test_review_loop = LoopAgent(
    name="BuildTestReviewLoop",

    sub_agents=[
        gameplay_developer,
        playtester,
        bug_reviewer,
    ],

    max_iterations=3,
)


# =========================================================
# ROOT MULTI-AGENT WORKFLOW
# =========================================================
#
#
#               USER REQUEST
#                    |
#                    v
#              GameDesigner
#                    |
#                    v
#            TechnicalPlanner
#                    |
#                    v
#       +--- BuildTestReviewLoop ---+
#       |                           |
#       | GameplayDeveloper         |
#       |      |                    |
#       |      | Filesystem MCP     |
#       |      v                    |
#       | real game                 |
#       |      |                    |
#       |      v                    |
#       | Playtester                |
#       |      |                    |
#       |      | Playwright MCP     |
#       |      v                    |
#       | real browser              |
#       |      |                    |
#       |      v                    |
#       | BugReviewer               |
#       |      |                    |
#       | PASS / REVISE             |
#       |      |                    |
#       |      +-------- LOOP ------+
#       |
#       +---------------------------+
#
# =========================================================

root_agent = SequentialAgent(
    name="MultiAgentGameBuilder",

    sub_agents=[
        game_designer,
        technical_planner,
        build_test_review_loop,
    ],

    description="""
A genuine Google ADK multi-agent software-engineering system.

Five specialized agents collaborate to:

1. design a browser game
2. create a technical plan
3. implement executable code
4. test the real browser environment
5. independently review the evidence
6. revise failed implementations
7. automatically retest revisions
8. stop only after approval or the iteration bound

The runtime uses:

- Google Agent Development Kit
- LlmAgent
- SequentialAgent
- LoopAgent
- shared session state
- before-model callbacks
- Filesystem MCP
- Microsoft Playwright MCP
- real filesystem operations
- real browser execution
- objective runtime evidence
- reviewer-controlled approval
- bounded autonomous iteration

The UI does not simulate these actions.
Google ADK executes the workflow.
""",
)