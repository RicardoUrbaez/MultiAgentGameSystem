import types
import unittest
from unittest import mock

from game_builder import agent


class RoutingArchitectureTests(unittest.TestCase):
    def test_runtime_agents_are_the_required_five_agents(self):
        self.assertEqual(
            [runtime_agent.name for runtime_agent in agent.runtime_agents],
            [
                "GameDesigner",
                "TechnicalPlanner",
                "GameplayDeveloper",
                "Playtester",
                "BugReviewer",
            ],
        )

    def test_bug_reviewer_approve_route_finalizes_run(self):
        self.assertEqual(
            agent.choose_reviewer_route("APPROVE\nAll checks pass.", 1, 1),
            agent.ROUTE_APPROVE,
        )

        self.assertEqual(
            agent.root_agent.graph.get_next_pending_nodes(
                "BugReviewer",
                agent.ROUTE_APPROVE,
            ),
            ["finalize_run"],
        )

    def test_bug_reviewer_revise_developer_route_rebuilds_and_retests(self):
        self.assertEqual(
            agent.choose_reviewer_route(
                "REVISE_DEVELOPER\n1. Reset failed.",
                1,
                1,
            ),
            agent.ROUTE_REVISE_DEVELOPER,
        )

        self.assertEqual(
            agent.root_agent.graph.get_next_pending_nodes(
                "BugReviewer",
                agent.ROUTE_REVISE_DEVELOPER,
            ),
            ["GameplayDeveloper"],
        )
        self.assertEqual(
            agent.root_agent.graph.get_next_pending_nodes(
                "GameplayDeveloper",
                None,
            ),
            ["build_gate"],
        )
        self.assertEqual(
            agent.root_agent.graph.get_next_pending_nodes(
                "build_gate",
                agent.BUILD_ROUTE_SUCCESS,
            ),
            ["Playtester"],
        )
        self.assertEqual(
            agent.root_agent.graph.get_next_pending_nodes(
                "Playtester",
                None,
            ),
            ["BugReviewer"],
        )

    def test_bug_reviewer_replan_route_replans_then_rebuilds_and_retests(
        self,
    ):
        self.assertEqual(
            agent.choose_reviewer_route(
                "REPLAN\n1. Acceptance criteria missed the core mechanic.",
                1,
                1,
            ),
            agent.ROUTE_REPLAN,
        )

        self.assertEqual(
            agent.root_agent.graph.get_next_pending_nodes(
                "BugReviewer",
                agent.ROUTE_REPLAN,
            ),
            ["TechnicalPlanner"],
        )
        self.assertEqual(
            agent.root_agent.graph.get_next_pending_nodes(
                "TechnicalPlanner",
                None,
            ),
            ["GameplayDeveloper"],
        )
        self.assertEqual(
            agent.root_agent.graph.get_next_pending_nodes(
                "GameplayDeveloper",
                None,
            ),
            ["build_gate"],
        )
        self.assertEqual(
            agent.root_agent.graph.get_next_pending_nodes(
                "build_gate",
                agent.BUILD_ROUTE_SUCCESS,
            ),
            ["Playtester"],
        )

    def test_bug_reviewer_human_review_route_and_guardrails(self):
        self.assertEqual(
            agent.choose_reviewer_route(
                "HUMAN_REVIEW\nBuild is blocked by external runtime.",
                1,
                1,
            ),
            agent.ROUTE_HUMAN_REVIEW,
        )
        self.assertEqual(
            agent.choose_reviewer_route(
                "REVISE_DEVELOPER\nStill failing.",
                agent.MAX_ROUTE_ITERATIONS,
                1,
            ),
            agent.ROUTE_HUMAN_REVIEW,
        )
        self.assertEqual(
            agent.choose_reviewer_route(
                "REVISE_DEVELOPER\nStill failing.",
                1,
                agent.MAX_REPEATED_FAILURES,
            ),
            agent.ROUTE_HUMAN_REVIEW,
        )

        self.assertEqual(
            agent.root_agent.graph.get_next_pending_nodes(
                "BugReviewer",
                agent.ROUTE_HUMAN_REVIEW,
            ),
            ["human_review"],
        )

    def test_build_gate_records_iteration_and_success_routes_to_playtester(
        self,
    ):
        completed = types.SimpleNamespace(
            success=True,
            exit_code=0,
            command="npm run build-nolog",
            stdout="vite build ok",
            stderr="",
            log_path="build.log",
            model_dump=lambda: {
                "success": True,
                "exit_code": 0,
                "command": "npm run build-nolog",
                "stdout": "vite build ok",
                "stderr": "",
                "log_path": "build.log",
            },
        )

        class FakeContext:
            def __init__(self):
                self.state = {agent.STATE_CURRENT_RUN_ID: "run_20260812_001"}
                self.route = None

        ctx = FakeContext()

        with (
            mock.patch.object(
                agent.build_tools,
                "npm_typecheck",
                return_value=completed,
            ),
            mock.patch.object(
                agent.build_tools,
                "npm_build",
                return_value=completed,
            ),
            mock.patch.object(
                agent.preview_tools,
                "start_preview",
                return_value="http://127.0.0.1:5500/",
            ),
        ):
            self.assertEqual(agent.build_gate(ctx), "BUILD_GATE_PASS")

        self.assertEqual(ctx.route, agent.BUILD_ROUTE_SUCCESS)
        self.assertEqual(ctx.state[agent.STATE_ITERATION_COUNT], 1)
        self.assertEqual(
            ctx.state[agent.STATE_BUILD_GATE]["status"],
            agent.BUILD_ROUTE_SUCCESS,
        )
        self.assertEqual(
            ctx.state[agent.STATE_PREVIEW_URL],
            "http://127.0.0.1:5500/",
        )

    def test_route_history_records_route_and_iteration_in_shared_state(self):
        state = {agent.STATE_ITERATION_COUNT: 2}

        agent.record_route_state(state, agent.ROUTE_REPLAN)

        self.assertEqual(state[agent.STATE_ROUTE], agent.ROUTE_REPLAN)
        self.assertEqual(
            state[agent.STATE_ROUTE_HISTORY],
            [
                {
                    "route": agent.ROUTE_REPLAN,
                    "iteration": 2,
                },
            ],
        )

    def test_reviewer_route_callback_preserves_exit_loop_approval(self):
        class FakeContext:
            def __init__(self):
                self.state = {agent.STATE_ROUTE: agent.ROUTE_APPROVE}
                self.actions = types.SimpleNamespace(route=None)

        ctx = FakeContext()

        self.assertIsNone(agent.record_reviewer_route(ctx))
        self.assertEqual(ctx.actions.route, agent.ROUTE_APPROVE)
        self.assertEqual(ctx.state[agent.STATE_WORKFLOW_STATUS], agent.APPROVED)

    def test_only_developer_has_filesystem_and_only_reviewer_has_approval_tool(
        self,
    ):
        self.assertIn(agent.filesystem_mcp, agent.gameplay_developer.tools)
        self.assertNotIn(agent.filesystem_mcp, agent.playtester.tools)
        self.assertNotIn(agent.filesystem_mcp, agent.bug_reviewer.tools)
        self.assertIn(agent.exit_loop, agent.bug_reviewer.tools)
        self.assertNotIn(agent.exit_loop, agent.gameplay_developer.tools)
        self.assertNotIn(agent.exit_loop, agent.playtester.tools)


if __name__ == "__main__":
    unittest.main()
