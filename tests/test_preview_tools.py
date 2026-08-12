import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game_builder.tools import preview_tools


class PreviewToolsTests(unittest.TestCase):
    def test_start_preview_returns_url_and_stop_terminates_process(self):
        class FakeProcess:
            def __init__(self):
                self.terminated = False

            def poll(self):
                return None

            def terminate(self):
                self.terminated = True

        fake_process = FakeProcess()

        with tempfile.TemporaryDirectory() as tmp:
            run_path = Path(tmp)

            with (
                mock.patch.object(
                    preview_tools,
                    "get_run_path",
                    return_value=run_path,
                ),
                mock.patch.object(
                    preview_tools,
                    "_resolve_command",
                    side_effect=lambda value: value,
                ),
                mock.patch.object(
                    preview_tools.subprocess,
                    "Popen",
                    return_value=fake_process,
                ) as popen_mock,
            ):
                url = preview_tools.start_preview(
                    "run_20260812_001",
                    5500,
                )
                stopped = preview_tools.stop_preview("run_20260812_001")

        self.assertEqual(url, "http://127.0.0.1:5500/")
        self.assertTrue(stopped)
        self.assertTrue(fake_process.terminated)
        popen_mock.assert_called_once()
        self.assertEqual(
            popen_mock.call_args.args[0],
            [
                "npm",
                "run",
                "dev-nolog",
                "--",
                "--host",
                "127.0.0.1",
                "--port",
                "5500",
            ],
        )


if __name__ == "__main__":
    unittest.main()
