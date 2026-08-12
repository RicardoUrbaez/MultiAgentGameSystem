import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from lab_app.fallback_games import write_prompt_game
from lab_app import main


class LabAppTests(unittest.TestCase):
    def test_lists_and_serves_built_game_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs_dir = Path(tmp) / "runs"
            dist_dir = runs_dir / "run_20260812_001" / "dist"
            dist_dir.mkdir(parents=True)
            (dist_dir / "index.html").write_text("<h1>Built Game</h1>", encoding="utf-8")

            with mock.patch.object(main, "RUNS_DIR", runs_dir):
                client = TestClient(main.app)

                runs = client.get("/api/runs")
                self.assertEqual(runs.status_code, 200)
                self.assertEqual(runs.json()["runs"][0]["run_id"], "run_20260812_001")
                self.assertTrue(runs.json()["runs"][0]["ready"])

                game = client.get("/runs/run_20260812_001/game/index.html")
                self.assertEqual(game.status_code, 200)
                self.assertIn("Built Game", game.text)

    def test_fallback_writer_handles_non_car_prompts(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_path = Path(tmp)
            write_prompt_game(run_path, "Build a maze treasure game with keys")

            menu_source = (run_path / "src" / "game" / "scenes" / "MenuScene.ts").read_text(encoding="utf-8")
            game_source = (run_path / "src" / "game" / "scenes" / "GameScene.ts").read_text(encoding="utf-8")

            self.assertIn("Maze Treasure Keys", menu_source)
            self.assertIn("Collect every key", game_source)
            self.assertIn("window.__GAME_TEST__", game_source)

    def test_fallback_writer_handles_shooter_prompts(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_path = Path(tmp)
            write_prompt_game(run_path, "Build a space alien shooter")

            game_source = (run_path / "src" / "game" / "scenes" / "GameScene.ts").read_text(encoding="utf-8")

            self.assertIn("Space fires", game_source)
            self.assertIn("bulletCount", game_source)
            self.assertIn("enemyCount", game_source)

    def test_fallback_writer_handles_pong_prompts(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_path = Path(tmp)
            write_prompt_game(run_path, "Build a compact arcade pong game")

            game_source = (run_path / "src" / "game" / "scenes" / "GameScene.ts").read_text(encoding="utf-8")

            self.assertIn("leftPaddleY", game_source)
            self.assertIn("rightPaddleY", game_source)
            self.assertIn("ballX", game_source)

    def test_fallback_writer_handles_maze_prompts(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_path = Path(tmp)
            write_prompt_game(run_path, "Build a maze escape game with keys and traps")

            game_source = (run_path / "src" / "game" / "scenes" / "GameScene.ts").read_text(encoding="utf-8")

            self.assertIn("totalKeys", game_source)
            self.assertIn("Collect every key", game_source)
            self.assertIn("enemyCount", game_source)

    def test_fallback_writer_handles_snake_prompts(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_path = Path(tmp)
            write_prompt_game(run_path, "Build a neon snake game")

            game_source = (run_path / "src" / "game" / "scenes" / "GameScene.ts").read_text(encoding="utf-8")

            self.assertIn("length", game_source)
            self.assertIn("Eat stars", game_source)
            self.assertIn("window.__GAME_TEST__", game_source)

    def test_fallback_writer_handles_platform_runner_prompts(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_path = Path(tmp)
            write_prompt_game(run_path, "Build a mario style platform runner")

            game_source = (run_path / "src" / "game" / "scenes" / "GameScene.ts").read_text(encoding="utf-8")

            self.assertIn("Space/click jumps", game_source)
            self.assertIn("distance", game_source)
            self.assertIn("window.__GAME_TEST__", game_source)


if __name__ == "__main__":
    unittest.main()
