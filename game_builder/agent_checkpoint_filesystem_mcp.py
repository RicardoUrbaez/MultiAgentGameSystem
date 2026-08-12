import os

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
# PROJECT PATHS
# =========================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

GAME_WORKSPACE = os.path.join(
    PROJECT_ROOT,
    "game_workspace"
)

# Make sure the sandbox directory exists.
os.makedirs(GAME_WORKSPACE, exist_ok=True)

GAME_INDEX_PATH = os.path.join(
    GAME_WORKSPACE,
    "index.html"
)


# =========================================================
# REAL MCP FILESYSTEM TOOLSET
# =========================================================
#
# Google ADK launches the filesystem MCP server as a
# subprocess and communicates with it over stdio.
#
# The MCP server is restricted to:
#
# MultiAgentGameSystem/game_workspace
#
# Only selected MCP tools are exposed to the agent.
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
# SHARED ADK STATE KEYS
# =========================================================

STATE_GAME_SPEC = "current_game_spec"
STATE_REVIEW = "review_feedback"

APPROVED = "APPROVED"


# =========================================================
# LOOP EXIT TOOL
# =========================================================

def exit_loop(tool_context: ToolContext):
    """
    Exit the real Google ADK LoopAgent after the reviewer
    approves the game specification and the game is built.
    """

    print(
        f"[TOOL] exit_loop called by "
        f"{tool_context.agent_name}"
    )

    tool_context.actions.escalate = True
    tool_context.actions.skip_summarization = True

    return {
        "status": "loop_exited",
        "reason": "Game approved and playable artifact created",
    }


# =========================================================
# AGENT 1
# INITIAL GAMEPLAY DEVELOPER
# =========================================================
#
# This agent runs ONCE before the LoopAgent.
#
# It intentionally creates an incomplete specification.
# This forces the reviewer to reject the first attempt,
# giving us visible proof of the agentic revision loop.
# =========================================================

initial_developer = LlmAgent(
    name="InitialGameplayDeveloper",
    model=MODEL,
    instruction="""
You are the Initial Gameplay Developer.

Read the user's browser-game request.

Create a deliberately incomplete first game specification.

The first specification must contain ONLY:

Title:
Objective:

Do NOT include:

- Controls
- Scoring
- Win condition
- Loss condition

This is intentional because another independent agent
will review your work.

Output only the game specification.
""",
    description=(
        "Creates the first intentionally incomplete "
        "browser-game specification."
    ),
    output_key=STATE_GAME_SPEC,
)


# =========================================================
# AGENT 2
# BUG REVIEWER
# =========================================================
#
# This agent independently evaluates the current game
# specification.
#
# It either:
#
# - produces corrective feedback
#
# OR
#
# - returns exactly APPROVED
# =========================================================

bug_reviewer = LlmAgent(
    name="BugReviewer",
    model=MODEL,
    include_contents="none",
    instruction=f"""
You are an independent Bug Reviewer.

Review the following current game specification:

{{current_game_spec}}

A valid browser-game specification MUST clearly contain:

1. Title
2. Objective
3. Controls
4. Scoring
5. Win or loss condition

If ANY requirement is missing or unclear:

Explain exactly which requirements are missing and what
the GameplayDeveloper must add.

If ALL five requirements are clearly satisfied:

Respond with exactly:

{APPROVED}

Do not add any other words when approving.

Output only the review result.
""",
    description=(
        "Independently evaluates the game specification "
        "against required acceptance criteria."
    ),
    output_key=STATE_REVIEW,
)


# =========================================================
# AGENT 3
# GAMEPLAY DEVELOPER
# =========================================================
#
# During failed iterations:
#
#   Reviewer -> Developer -> Reviewer
#
# The developer revises the specification.
#
# Once the reviewer returns APPROVED:
#
#   Developer
#       |
#       v
#   MCP write_file
#       |
#       v
#   real index.html
#       |
#       v
#   exit_loop
#
# The generated index.html contains HTML + CSS + JavaScript
# in ONE file to reduce API/tool calls during development.
# =========================================================

gameplay_developer = LlmAgent(
    name="GameplayDeveloper",
    model=MODEL,
    include_contents="none",
    instruction=f"""
You are the Gameplay Developer.

CURRENT GAME SPECIFICATION:

{{current_game_spec}}

BUG REVIEW:

{{review_feedback}}

You have access to a REAL filesystem through Model Context
Protocol (MCP).

============================================================
CASE 1: THE BUG REVIEW IS NOT APPROVED
============================================================

If the bug review is NOT exactly:

{APPROVED}

then revise the current game specification.

Address ALL reviewer feedback.

The revised specification MUST clearly contain:

Title:
Objective:
Controls:
Scoring:
Win/Loss Condition:

Return only the revised game specification.

Do NOT create game files yet.

Do NOT call exit_loop.

============================================================
CASE 2: THE BUG REVIEW IS APPROVED
============================================================

If the bug review is exactly:

{APPROVED}

the specification has passed review.

Now build the REAL playable browser game.

You MUST use the MCP write_file tool.

Create exactly ONE self-contained file:

{GAME_INDEX_PATH}

The file must be named:

index.html

The index.html file MUST contain EVERYTHING required
to run the game:

- complete HTML
- complete CSS inside a <style> element
- complete JavaScript inside a <script> element

Do NOT create:

- style.css
- game.js
- external libraries
- CDN dependencies
- server-side code

Do NOT make external network requests.

The game MUST actually implement the approved specification.

It must include:

1. A visible game title.

2. Visible gameplay instructions.

3. The approved controls.

4. The approved objective.

5. Working player movement.

6. Working game mechanics.

7. Working collision behavior where applicable.

8. Working scoring.

9. A visible score display.

10. The approved win/loss condition.

11. A game-over or victory state.

12. A restart/play-again control.

13. A playable game area.

For a Pong-style game specifically:

- create two paddles
- create a moving ball
- implement paddle collision
- implement top/bottom wall collision
- award points when the ball passes a paddle
- reset the ball after scoring
- end the match when a player reaches the required score
- allow the match to restart

Use plain ASCII text for labels.

For example:

Use:

Up / Down

instead of Unicode arrow characters.

IMPORTANT:

Do not merely SAY that you created the game.

You MUST actually invoke the MCP write_file tool.

Pass the COMPLETE HTML document as the file content.

The HTML must begin with a valid document structure such as:

<!DOCTYPE html>
<html>
...
</html>

After the MCP write_file operation succeeds:

Call exit_loop.

Do not call exit_loop before the MCP write_file operation
successfully completes.
""",
    description=(
        "Revises rejected game specifications and, once "
        "approved, uses MCP to create a real playable "
        "self-contained browser game."
    ),
    tools=[
        filesystem_mcp,
        exit_loop,
    ],
    output_key=STATE_GAME_SPEC,
)


# =========================================================
# REAL GOOGLE ADK AGENTIC LOOP
# =========================================================
#
# ADK executes:
#
#
#        BugReviewer
#             |
#             v
#     GameplayDeveloper
#             |
#             |
#             +------------------+
#                                |
#                         next iteration
#                                |
#                                v
#                           BugReviewer
#
#
# Example:
#
# ITERATION 1
#
# BugReviewer
#     |
#     | FAIL
#     v
# GameplayDeveloper
#     |
#     | revises specification
#     |
#
# ITERATION 2
#
# BugReviewer
#     |
#     | APPROVED
#     v
# GameplayDeveloper
#     |
#     | MCP write_file
#     v
# index.html
#     |
#     v
# exit_loop
#
#
# The loop is bounded by max_iterations=3.
# =========================================================

revision_loop = LoopAgent(
    name="GameRevisionLoop",
    sub_agents=[
        bug_reviewer,
        gameplay_developer,
    ],
    max_iterations=3,
)


# =========================================================
# ROOT GOOGLE ADK WORKFLOW
# =========================================================
#
#
#                 USER REQUEST
#                      |
#                      v
#          InitialGameplayDeveloper
#                      |
#                      v
#            GameRevisionLoop
#                      |
#               +------+------+
#               |             |
#               v             v
#          BugReviewer   GameplayDeveloper
#               ^             |
#               |             |
#               +----- LOOP --+
#                             |
#                             v
#                         McpToolset
#                             |
#                             v
#                     Filesystem MCP Server
#                             |
#                             v
#                     game_workspace/
#                       index.html
#                             |
#                             v
#                         exit_loop
#
# =========================================================

root_agent = SequentialAgent(
    name="GameBuilderAgenticLab",
    sub_agents=[
        initial_developer,
        revision_loop,
    ],
    description="""
A real Google ADK multi-agent workflow for generating browser games.

The workflow uses:

- Google Agent Development Kit
- multiple specialized LLM agents
- shared ADK session state
- a real LoopAgent
- independent reviewer feedback
- repeated revision
- bounded iterations
- real agent tools
- Model Context Protocol
- a real filesystem MCP server
- real executable browser artifacts
- an explicit loop termination tool

The web interface does not simulate the workflow.
The underlying Google ADK runtime performs the workflow.
""",
)