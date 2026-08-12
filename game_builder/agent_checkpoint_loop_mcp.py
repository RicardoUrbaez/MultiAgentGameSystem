import os

from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent
from google.adk.tools.tool_context import ToolContext

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
)
from mcp import StdioServerParameters


# =========================================================
# MODEL
# =========================================================

MODEL = "gemini-3.5-flash"


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


# =========================================================
# REAL MCP FILESYSTEM TOOLSET
# =========================================================
#
# ADK will launch this MCP server automatically.
#
# It is restricted to:
#
# MultiAgentGameSystem/game_workspace
#
# The GameplayDeveloper can only see the filtered tools below.
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
    approves the current game specification.
    """

    print(
        f"[TOOL] exit_loop called by "
        f"{tool_context.agent_name}"
    )

    tool_context.actions.escalate = True
    tool_context.actions.skip_summarization = True

    return {
        "status": "loop_exited",
        "reason": "Game specification approved",
    }


# =========================================================
# AGENT 1
# Initial Gameplay Developer
#
# Runs ONCE before the revision loop.
#
# It intentionally creates an incomplete specification so
# that the reviewer is forced to reject it and the loop can
# be demonstrated clearly in ADK Web.
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

This is intentional because another agent will review your work.

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
# Bug Reviewer
#
# Evaluates the artifact independently.
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
# Gameplay Developer
#
# Revises failed work.
#
# Once approved, it uses the REAL filesystem MCP server
# to persist the approved artifact to disk.
# =========================================================

gameplay_developer = LlmAgent(
    name="GameplayDeveloper",
    model=MODEL,
    include_contents="none",
    instruction=f"""
You are the Gameplay Developer.

You are responsible for revising and persisting the game
specification.

CURRENT GAME SPECIFICATION:

{{current_game_spec}}

BUG REVIEW:

{{review_feedback}}

You have access to a real filesystem through MCP.

------------------------------------------------------------
IF THE BUG REVIEW IS NOT APPROVED
------------------------------------------------------------

Revise the current game specification so that it addresses
ALL reviewer feedback.

The revised specification MUST contain:

Title:
Objective:
Controls:
Scoring:
Win/Loss Condition:

Return only the revised game specification.

Do NOT call exit_loop while the reviewer still has defects.

------------------------------------------------------------
IF THE BUG REVIEW IS EXACTLY:
{APPROVED}
------------------------------------------------------------

You MUST perform these actions in this exact order:

1. Call list_allowed_directories to confirm the filesystem
   workspace you are permitted to access.

2. Call write_file.

3. Create this file inside the allowed workspace:

   game_spec.txt

4. Write the COMPLETE approved current game specification
   into that file.

5. Do NOT merely claim the file was saved.
   You MUST actually invoke the MCP write_file tool.

6. Only after write_file succeeds, call exit_loop.

Do not modify the approved specification after approval.
""",
    description=(
        "Revises failed game specifications and uses MCP "
        "to persist approved artifacts to the real filesystem."
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
# BugReviewer
#       |
#       v
# GameplayDeveloper
#       |
#       |
#       +--------------------+
#                            |
#        next iteration      |
#                            v
#                       BugReviewer
#
# until:
#
# - exit_loop is called
#
# OR
#
# - max_iterations is reached.
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
# ROOT AGENTIC WORKFLOW
# =========================================================
#
# InitialGameplayDeveloper
#          |
#          v
#    GameRevisionLoop
#          |
#          +--> BugReviewer
#          |
#          +--> GameplayDeveloper
#                    |
#                    +--> MCP filesystem tools
#                    |
#                    +--> exit_loop
#
# =========================================================

root_agent = SequentialAgent(
    name="GameBuilderAgenticLab",
    sub_agents=[
        initial_developer,
        revision_loop,
    ],
    description="""
A real Google ADK multi-agent workflow.

The system creates a browser-game specification, independently
reviews it, revises failed work through a LoopAgent, persists
approved artifacts through Model Context Protocol tools, and
terminates only after acceptance or the iteration limit.

This workflow is intended to demonstrate genuine agentic
orchestration rather than a single-pass AI assistant.
""",
)