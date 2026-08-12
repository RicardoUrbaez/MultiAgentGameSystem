import json
import unittest
from pathlib import Path
from unittest import mock

from game_builder import agent
from game_builder.regression_cases import REGRESSION_CASES, get_regression_case
from game_builder.schemas import ReviewDecision, TestReport
from game_builder.tools import asset_tools, workspace_tools


class GameQualityContractTests(unittest.TestCase):
    def test_production_template_includes_test_bridge_and_buildable_scene_flow(self):
        template = workspace_tools.PHASER_TEMPLATE_DIR
        bridge = (template / "src/game/systems/TestBridge.ts").read_text(encoding="utf-8")
        scene = (template / "src/game/scenes/GameScene.ts").read_text(encoding="utf-8")
        self.assertIn("getState", bridge)
        self.assertIn("reset", bridge)
        self.assertIn("getErrors", bridge)
        self.assertIn("this.state = createInitialState()", scene)
        self.assertIn("triggerWin", scene)
        self.assertIn("triggerLoss", scene)

    def test_asset_manifest_entries_are_valid_local_files(self):
        manifest_path = asset_tools.get_asset_manifest_path()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["assets"]), 6)
        for entry in data["assets"]:
            self.assertTrue(entry["key"])
            self.assertTrue(entry["type"])
            self.assertTrue(entry["tags"])
            asset_path = workspace_tools.PHASER_TEMPLATE_DIR / "public" / entry["path"]
            self.assertTrue(asset_path.exists(), entry["path"])

    def test_invalid_asset_keys_are_rejected(self):
        with self.assertRaises(ValueError):
            asset_tools.validate_asset_keys(["not-an-approved-asset"])

    def test_structured_test_report_requires_every_quality_category(self):
        report = TestReport(
            build="PASS", page_load="PASS", console="PASS", controls="PASS",
            mechanics="PASS", scoring="PASS", win_loss="PASS", reset="PASS",
            design_compliance="PASS", performance_sanity="PASS", fresh_for_iteration=1,
        )
        self.assertTrue(report.success)

    def test_approval_needs_fresh_complete_browser_evidence(self):
        decision = ReviewDecision(route="APPROVE", score=90, reasoning="All evidence passed.")
        state = {
            agent.STATE_TYPECHECK_RESULT: {"success": True},
            agent.STATE_BUILD_RESULT: {"success": True},
            agent.STATE_ITERATION_COUNT: 2,
            agent.STATE_STRUCTURED_TEST_REPORT: TestReport(
                build="PASS", page_load="PASS", console="PASS", controls="PASS",
                mechanics="PASS", scoring="PASS", win_loss="PASS", reset="PASS",
                design_compliance="PASS", performance_sanity="PASS", fresh_for_iteration=2,
            ).model_dump(),
        }
        self.assertTrue(agent.approval_evidence_is_fresh(state, decision))
        state[agent.STATE_STRUCTURED_TEST_REPORT]["fresh_for_iteration"] = 1
        self.assertFalse(agent.approval_evidence_is_fresh(state, decision))

    def test_reviewer_quality_score_is_parsed(self):
        decision = agent._coerce_review_decision("APPROVE\nSCORE: 91\nAll categories passed.")
        self.assertEqual(decision.score, 91)

    def test_multi_genre_regression_catalog_has_required_cases(self):
        names = {case.name for case in REGRESSION_CASES}
        self.assertTrue({"pong", "breakout", "asteroid_survival", "top_down_shooter", "maze"}.issubset(names))
        self.assertEqual(get_regression_case("pong").genre, "paddle game")


if __name__ == "__main__":
    unittest.main()
