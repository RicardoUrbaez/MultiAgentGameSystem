import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game_builder import agent
from game_builder.schemas import GameManifest, ReviewDecision


class ProductionContractTests(unittest.TestCase):
    def test_game_manifest_forces_phaser_engine(self):
        manifest = GameManifest(
            title="Pong",
            genre="Arcade",
            player_count=2,
            camera="STATIC",
            physics="ARCADE",
            scenes=["Boot", "Game"],
            mechanics=["paddle movement"],
            required_assets=[],
            acceptance_tests=["Game boots"],
            has_menu=True,
            has_audio=False,
            has_particles=False,
            has_progression=False,
        )
        self.assertEqual(manifest.engine, "PHASER_2D")

    def test_review_decision_schema_tracks_required_fields(self):
        decision = ReviewDecision(
            route="REVISE_DEVELOPER",
            score=82,
            reasoning="Paddle reset bug remains.",
            defects=["Reset bug"],
            required_changes=["Reset both scores"],
        )
        self.assertEqual(decision.route, "REVISE_DEVELOPER")
        self.assertGreaterEqual(decision.score, 0)
        self.assertIn("required_changes", decision.model_dump())

    def test_run_workspace_state_tracks_runtime_keys(self):
        class FakeContext:
            def __init__(self):
                self.state = {}

        ctx = FakeContext()
        with (
            mock.patch.object(
                agent.workspace_tools,
                "create_next_run_id",
                return_value="run_20260812_099",
            ),
            mock.patch.object(
                agent.workspace_tools,
                "create_run_from_phaser_template",
                return_value=agent.GAME_RUNS_DIR + "/run_20260812_099",
            ),
        ):
            agent.create_run_workspace(ctx)

        self.assertEqual(ctx.state["run_id"], "run_20260812_099")
        self.assertEqual(ctx.state["run_path"], agent.GAME_RUNS_DIR + "/run_20260812_099")
        self.assertEqual(ctx.state["max_iterations"], agent.MAX_ROUTE_ITERATIONS)
        self.assertFalse(ctx.state.get("human_review_required", False))

    def test_phaser_template_copy_is_deterministic_and_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = root / "template"
            runs_dir = root / "runs"
            template.mkdir()
            (template / "src").mkdir()
            (template / "src" / "main.ts").write_text("console.log('ok')")
            (template / "node_modules").mkdir()
            (template / "public").mkdir()
            (template / "package.json").write_text("{}")
            (template / "log.js").write_text("console.log('log')")
            (template / "dist").mkdir()
            (template / ".git").mkdir()

            with (
                mock.patch.object(agent.workspace_tools, "PHASER_TEMPLATE_DIR", template),
                mock.patch.object(agent.workspace_tools, "RUNS_DIR", runs_dir),
            ):
                run_path = agent.workspace_tools.create_run_from_phaser_template("run_20260812_001")

            self.assertTrue((run_path / "src" / "main.ts").exists())
            self.assertFalse((run_path / "node_modules").exists())
            self.assertFalse((run_path / "dist").exists())
            self.assertFalse((run_path / ".git").exists())
            self.assertFalse((template / "logs").exists())

    def test_path_traversal_and_unsafe_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            agent.workspace_tools.validate_run_path("../escape")
        with self.assertRaises(ValueError):
            agent.workspace_tools.validate_run_path("run_20260812_001/../../evil")

    def test_build_gate_fails_without_typecheck_and_blocks_playtester(self):
        class FakeCtx:
            def __init__(self):
                self.state = {agent.STATE_CURRENT_RUN_ID: "run_20260812_001"}
                self.route = None

        ctx = FakeCtx()
        with (
            mock.patch.object(agent.build_tools, "npm_typecheck", return_value=mock.Mock(success=False, model_dump=lambda: {"success": False, "exit_code": 2, "stdout": "", "stderr": "TS2345"})),
            mock.patch.object(agent.build_tools, "npm_build"),
            mock.patch.object(agent.preview_tools, "start_preview"),
        ):
            result = agent.build_gate(ctx)

        self.assertEqual(result, "BUILD_GATE_FAIL")
        self.assertEqual(ctx.route, agent.BUILD_ROUTE_FAILED)
        self.assertIn("typecheck", str(ctx.state[agent.STATE_TEST_REPORT]).lower())

    def test_route_decisions_follow_required_review_contract(self):
        self.assertEqual(agent.choose_reviewer_route("APPROVE\nAll checks pass.", 1, 1), agent.ROUTE_APPROVE)
        self.assertEqual(agent.choose_reviewer_route("REVISE_DEVELOPER\nFix reset.", 1, 1), agent.ROUTE_REVISE_DEVELOPER)
        self.assertEqual(agent.choose_reviewer_route("REPLAN\nBad plan.", 1, 1), agent.ROUTE_REPLAN)
        self.assertEqual(agent.choose_reviewer_route("REVISE_DEVELOPER\nStill failing.", agent.MAX_ROUTE_ITERATIONS, 1), agent.ROUTE_HUMAN_REVIEW)

    def test_human_review_is_set_after_max_iterations(self):
        state = {agent.STATE_ITERATION_COUNT: 3}
        route = agent.choose_reviewer_route("REVISE_DEVELOPER\nStill failing.", 3, 1)
        self.assertEqual(route, agent.ROUTE_HUMAN_REVIEW)
        self.assertIn(route, {agent.ROUTE_HUMAN_REVIEW})

    def test_repeated_critical_failure_forces_human_review(self):
        self.assertEqual(
            agent.choose_reviewer_route("REVISE_DEVELOPER\nSame error again.", 1, agent.MAX_REPEATED_FAILURES),
            agent.ROUTE_HUMAN_REVIEW,
        )

    def test_revision_requires_fresh_browser_evidence(self):
        state = {
            agent.STATE_CURRENT_RUN_ID: "run_20260812_001",
            agent.STATE_ITERATION_COUNT: 1,
            agent.STATE_BUILD_GATE: {"status": agent.BUILD_ROUTE_SUCCESS},
            agent.STATE_TEST_REPORT: "OVERALL: PASS",
        }
        self.assertIn("OVERALL: PASS", state[agent.STATE_TEST_REPORT])
        state[agent.STATE_TEST_REPORT] = "OVERALL: FAIL\nDEFECTS:\n1. Reset bug"
        self.assertNotIn("OVERALL: PASS", state[agent.STATE_TEST_REPORT])

    def test_role_tool_boundaries_are_enforced(self):
        self.assertIn(agent.filesystem_mcp, agent.gameplay_developer.tools)
        self.assertNotIn(agent.filesystem_mcp, agent.playtester.tools)
        self.assertNotIn(agent.filesystem_mcp, agent.bug_reviewer.tools)
        self.assertIn(agent.exit_loop, agent.bug_reviewer.tools)
        self.assertNotIn(agent.exit_loop, agent.playtester.tools)


if __name__ == "__main__":
    unittest.main()
