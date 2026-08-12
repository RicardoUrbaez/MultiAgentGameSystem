import os

from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
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
# PROJECT CONFIGURATION
# =========================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

GAME_WORKSPACE = os.path.join(
    PROJECT_ROOT,
    "game_workspace"
)

os.makedirs(GAME_WORKSPACE, exist_ok=True)

GAME_INDEX_PATH = os.path.join(
    GAME_WORKSPACE,
    "index.html"
)

GAME_URL = "http://127.0.0.1:5500/index.html"


# =========================================================
# SHARED ADK STATE
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
# Used only by GameplayDeveloper.
#
# This is the real Model Context Protocol filesystem server.
# It is restricted to game_workspace.
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
        "edit_file",
        "list_directory",
        "list_allowed_directories",
    ],
)


# =========================================================
# PLAYWRIGHT MCP
# =========================================================
#
# Used only by Playtester.
#
# ADK launches Microsoft's Playwright MCP server over stdio.
#
# The browser is HEADED so it can be visibly demonstrated.
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
        "browser_snapshot",
        "browser_click",
        "browser_press_key",
        "browser_evaluate",
        "browser_console_messages",
        "browser_take_screenshot",
    ],
)


# =========================================================
# INITIALIZE SHARED STATE
# =========================================================

def initialize_workflow_state(
    callback_context: CallbackContext,
):
    """
    Initialize state needed before the first build/test loop.
    """

    callback_context.state[STATE_REVIEW_FEEDBACK] = (
        "INITIAL_BUILD: No previous implementation exists. "
        "Create the first complete implementation."
    )

    callback_context.state[STATE_TEST_REPORT] = (
        "No browser test has been executed yet."
    )

    callback_context.state[STATE_BUILD_SUMMARY] = (
        "No game has been built yet."
    )

    return None


# =========================================================
# REAL LOOP EXIT TOOL
# =========================================================

def exit_loop(tool_context: ToolContext):
    """
    Stop the ADK build/test/review loop after the
    BugReviewer determines that the generated game passes.
    """

    print(
        f"[TOOL] exit_loop called by "
        f"{tool_context.agent_name}"
    )

    tool_context.actions.escalate = True
    tool_context.actions.skip_summarization = True

    return {
        "status": "approved",
        "reason": (
            "Browser tests passed and the BugReviewer "
            "approved the generated game."
        ),
    }


# =========================================================
# AGENT 1
# GAME DESIGNER
# =========================================================

game_designer = LlmAgent(
    name="GameDesigner",
    model=MODEL,
    instruction="""
You are the Game Designer.

Interpret the user's natural-language browser-game request.

Create a clear game design containing:

Title
Genre
Objective
Player controls
Core mechanics
Scoring
Progression
Win condition
Loss condition
Restart behavior

Stay faithful to the user's requested game.

Do not write code.

Output only the structured game design.
""",
    description=(
        "Transforms the user's game idea into a concrete "
        "game-design specification."
    ),
    output_key=STATE_GAME_DESIGN,
)


# =========================================================
# AGENT 2
# TECHNICAL PLANNER
# =========================================================

technical_planner = LlmAgent(
    name="TechnicalPlanner",
    model=MODEL,
    include_contents="none",
    instruction="""
You are the Technical Planner.

GAME DESIGN:

{game_design}

Convert the approved design into an implementation plan
for a compact browser game.

The game will be implemented as ONE self-contained:

index.html

The file must contain:

- HTML
- CSS inside <style>
- JavaScript inside <script>

Define:

1. Required UI elements
2. Game state
3. Core update loop
4. Input handling
5. Collision/interaction logic
6. Scoring logic
7. Win/loss logic
8. Restart logic
9. Acceptance tests
10. Test instrumentation requirements

The implementation MUST expose:

window.__GAME_TEST__

with:

getState()
reset()

getState() must return a JSON-serializable object describing
the current runtime state.

For games with scoring, include score information.

For games with terminal states, include:

gameOver
winner

Do not write the actual implementation.

Output only the technical plan.
""",
    description=(
        "Converts the game design into implementation "
        "requirements and browser acceptance tests."
    ),
    output_key=STATE_TECHNICAL_PLAN,
)


# =========================================================
# AGENT 3
# GAMEPLAY DEVELOPER
# =========================================================
#
# This agent runs INSIDE the real LoopAgent.
#
# First iteration:
#     Creates index.html.
#
# Later iterations:
#     Reads reviewer feedback and fixes index.html.
#
# All file operations happen through filesystem MCP.
# =========================================================

gameplay_developer = LlmAgent(
    name="GameplayDeveloper",
    model=MODEL,
    include_contents="none",
    instruction=f"""
You are the Gameplay Developer.

GAME DESIGN:

{{game_design}}

TECHNICAL PLAN:

{{technical_plan}}

LATEST REVIEW FEEDBACK:

{{review_feedback}}

You have access to a REAL filesystem through MCP.

Your responsibility is to create or repair the playable game.

The only production file is:

{GAME_INDEX_PATH}

============================================================
IMPLEMENTATION REQUIREMENTS
============================================================

Use the MCP filesystem tools.

First call:

list_allowed_directories

Then inspect the workspace with:

list_directory

If index.html already exists and this is a revision:

Use read_text_file to inspect the existing implementation.

Then use write_file or edit_file to repair it.

If this is the initial build:

Use write_file to create index.html.

index.html MUST be a complete self-contained browser game.

It must contain:

- <!DOCTYPE html>
- complete HTML
- CSS inside <style>
- JavaScript inside <script>

Do NOT use:

- external libraries
- CDN resources
- external JavaScript
- external stylesheets
- external network requests
- server-side code

The game MUST implement the Game Designer's specification.

It must include:

- visible title
- visible instructions
- working controls
- actual gameplay
- scoring where required
- win/loss behavior
- restart behavior
- clear playable area

============================================================
TEST INSTRUMENTATION
============================================================

The game MUST expose:

window.__GAME_TEST__

It MUST contain:

getState()
reset()

Example shape:

window.__GAME_TEST__ = {{
    getState: () => ({{
        running: true,
        score: {{
            player1: 0,
            player2: 0
        }},
        gameOver: false,
        winner: null
    }}),

    reset: () => {{
        // actually reset the game
    }}
}};

The exact state fields may vary with the game,
but they must accurately describe the actual runtime.

Do NOT fake test results.

============================================================
REVISION BEHAVIOR
============================================================

If LATEST REVIEW FEEDBACK begins with or contains:

REVISE_DEVELOPER

you MUST modify the existing implementation to address
every reported defect.

Do not simply explain the fix.

Actually edit the file through MCP.

============================================================
FINISH
============================================================

After writing or editing index.html:

Call list_directory.

Verify that index.html exists.

Then return a short BUILD SUMMARY describing what changed.

Do NOT call exit_loop.

Only the BugReviewer is allowed to approve the game.
""",
    description=(
        "Creates and repairs the actual executable browser "
        "game using the filesystem MCP server."
    ),
    tools=[
        filesystem_mcp,
    ],
    output_key=STATE_BUILD_SUMMARY,
)


# =========================================================
# AGENT 4
# PLAYTESTER
# =========================================================
#
# This agent uses Microsoft's REAL Playwright MCP server.
#
# It does not inspect source code and guess.
#
# It opens the running game in a browser and interacts
# with the real environment.
# =========================================================

playtester = LlmAgent(
    name="Playtester",
    model=MODEL,
    include_contents="none",
    instruction=f"""
You are an independent browser-game Playtester.

GAME DESIGN:

{{game_design}}

TECHNICAL PLAN:

{{technical_plan}}

BUILD SUMMARY:

{{build_summary}}

You have access to a REAL browser through Playwright MCP.

Test this URL:

{GAME_URL}

You MUST actually use the browser tools.

============================================================
REQUIRED TEST PROCESS
============================================================

1. Call browser_navigate and open:

{GAME_URL}

2. Call browser_snapshot.

Confirm that the game UI actually loaded.

3. Call browser_console_messages.

Look specifically for JavaScript errors.

4. Call browser_evaluate and verify:

- document.readyState
- the main game area exists
- window.__GAME_TEST__ exists
- window.__GAME_TEST__.getState is a function
- window.__GAME_TEST__.reset is a function

5. Call browser_evaluate:

window.__GAME_TEST__.getState()

Record the initial runtime state.

6. Use browser_snapshot to locate any Start or Restart control.

If a Start/Restart button exists, click it using browser_click.

7. Exercise keyboard controls.

For a Pong-style game, test at least:

W
S
ArrowUp
ArrowDown

Use browser_press_key.

For another game type, use the controls from the Game Design.

8. Call browser_evaluate again:

window.__GAME_TEST__.getState()

Confirm the game is still running and state can be read.

9. Call browser_evaluate:

window.__GAME_TEST__.reset()

Then call getState() again.

Verify reset behavior.

10. Call browser_console_messages again.

11. Take a screenshot using browser_take_screenshot.

============================================================
TEST REPORT
============================================================

Return a structured report containing:

OVERALL: PASS or FAIL

PAGE_LOAD:
PASS/FAIL plus evidence

CONSOLE:
PASS/FAIL plus errors found

CONTROLS:
PASS/FAIL plus actions performed

GAME_STATE:
PASS/FAIL plus observed state

RESET:
PASS/FAIL plus evidence

DESIGN_COMPLIANCE:
PASS/FAIL

DEFECTS:
List every defect.

Do NOT report PASS unless you actually performed
the browser interactions.

Do NOT modify the game.
You are a tester only.
""",
    description=(
        "Uses a real Playwright MCP browser session to "
        "test the generated game and produce evidence."
    ),
    tools=[
        playwright_mcp,
    ],
    output_key=STATE_TEST_REPORT,
)


# =========================================================
# AGENT 5
# BUG REVIEWER
# =========================================================
#
# Reviewer gets the real browser test evidence.
#
# PASS:
#     calls exit_loop
#
# FAIL:
#     writes REVISE_DEVELOPER feedback
#
# The next LoopAgent iteration sends that feedback back
# to GameplayDeveloper.
# =========================================================

bug_reviewer = LlmAgent(
    name="BugReviewer",
    model=MODEL,
    include_contents="none",
    instruction="""
You are the independent Bug Reviewer.

GAME DESIGN:

{game_design}

TECHNICAL PLAN:

{technical_plan}

PLAYTEST REPORT:

{test_report}

Evaluate the evidence.

You are NOT allowed to edit the game.

============================================================
APPROVAL RULES
============================================================

Approve only if:

- the page loaded
- there are no critical JavaScript errors
- required controls worked
- runtime game state was accessible
- reset worked
- the implementation reasonably matches the design
- the Playtester reported OVERALL: PASS

If all approval requirements pass:

Call exit_loop.

Do not request unnecessary changes.

============================================================
FAILURE RULES
============================================================

If ANY critical requirement fails:

Do NOT call exit_loop.

Return:

REVISE_DEVELOPER

followed by a precise list of defects the developer
must correct.

Use the Playtester's actual evidence.

Do not invent defects.

Do not repair anything yourself.
""",
    description=(
        "Evaluates real browser-test evidence and either "
        "approves the game or routes defects back to the "
        "GameplayDeveloper."
    ),
    tools=[
        exit_loop,
    ],
    output_key=STATE_REVIEW_FEEDBACK,
)


# =========================================================
# REAL BUILD -> TEST -> REVIEW AGENTIC LOOP
# =========================================================
#
#
# GameplayDeveloper
#       |
#       | Filesystem MCP
#       v
# real index.html
#       |
#       v
# Playtester
#       |
#       | Playwright MCP
#       v
# real browser
#       |
#       v
# BugReviewer
#       |
#       +---- PASS ----> exit_loop
#       |
#       +---- FAIL
#                |
#                +-------------------------+
#                                          |
#                         next ADK iteration
#                                          |
#                                          v
#                               GameplayDeveloper
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
# ROOT GOOGLE ADK WORKFLOW
# =========================================================

root_agent = SequentialAgent(
    name="MultiAgentGameBuilder",
    sub_agents=[
        game_designer,
        technical_planner,
        build_test_review_loop,
    ],
    before_agent_callback=initialize_workflow_state,
    description="""
A genuine Google ADK multi-agent software-engineering system.

Five specialized agents collaborate to design, plan, build,
browser-test, review, and revise a browser game.

The workflow uses:

Google ADK
SequentialAgent
LoopAgent
shared session state
filesystem MCP
Microsoft Playwright MCP
real browser interaction
real executable artifacts
reviewer-controlled revision
bounded iteration
automatic retesting

The web interface does not simulate these steps.
The ADK runtime executes them.
""",
)