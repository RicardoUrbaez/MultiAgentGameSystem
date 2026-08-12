import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from game_builder.tools import workspace_tools


class WorkspaceToolsTests(unittest.TestCase):
    def test_create_next_run_id_uses_next_daily_sequence(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs_dir = Path(tmp) / "runs"
            (runs_dir / "run_20260812_001").mkdir(parents=True)
            (runs_dir / "run_20260812_003").mkdir()

            with mock.patch.object(workspace_tools, "RUNS_DIR", runs_dir):
                self.assertEqual(
                    workspace_tools.create_next_run_id(
                        datetime(2026, 8, 12)
                    ),
                    "run_20260812_004",
                )

    def test_create_run_from_template_copies_only_project_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = root / "template"
            runs_dir = root / "runs"

            (template / "src").mkdir(parents=True)
            (template / "public").mkdir()
            (template / "node_modules").mkdir()
            (template / "dist").mkdir()
            (template / ".git").mkdir()
            (template / ".playwright-mcp").mkdir()
            (template / "src" / "main.ts").write_text(
                "console.log('ok')",
                encoding="utf-8",
            )
            (template / "README.md").write_text(
                "skip docs",
                encoding="utf-8",
            )
            (template / "log.js").write_text(
                "console.log('helper')",
                encoding="utf-8",
            )
            (template / "package.json").write_text(
                "{}",
                encoding="utf-8",
            )
            (template / "node_modules" / "large.js").write_text(
                "skip",
                encoding="utf-8",
            )

            with (
                mock.patch.object(
                    workspace_tools,
                    "PHASER_TEMPLATE_DIR",
                    template,
                ),
                mock.patch.object(workspace_tools, "RUNS_DIR", runs_dir),
            ):
                run_path = workspace_tools.create_run_from_phaser_template(
                    "run_20260812_001"
                )

            self.assertTrue((run_path / "src" / "main.ts").exists())
            self.assertTrue((run_path / "log.js").exists())
            self.assertTrue((run_path / "logs").is_dir())
            self.assertFalse((run_path / "README.md").exists())
            self.assertFalse((run_path / "node_modules").exists())
            self.assertFalse((run_path / "dist").exists())
            self.assertFalse((run_path / ".git").exists())
            self.assertFalse((run_path / ".playwright-mcp").exists())
            self.assertFalse((template / "logs").exists())

    def test_create_run_refuses_invalid_or_existing_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = root / "template"
            runs_dir = root / "runs"
            template.mkdir()
            (runs_dir / "run_20260812_001").mkdir(parents=True)

            with (
                mock.patch.object(
                    workspace_tools,
                    "PHASER_TEMPLATE_DIR",
                    template,
                ),
                mock.patch.object(workspace_tools, "RUNS_DIR", runs_dir),
            ):
                with self.assertRaises(ValueError):
                    workspace_tools.create_run_from_phaser_template(
                        "../bad"
                    )
                with self.assertRaises(FileExistsError):
                    workspace_tools.create_run_from_phaser_template(
                        "run_20260812_001"
                    )


if __name__ == "__main__":
    unittest.main()
