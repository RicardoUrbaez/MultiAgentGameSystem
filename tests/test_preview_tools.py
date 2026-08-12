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
                self.wait_calls = []

            def poll(self):
                return None if not self.terminated else 0

            def terminate(self):
                self.terminated = True

            def wait(self, timeout):
                self.wait_calls.append(timeout)

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

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
                mock.patch.object(
                    preview_tools,
                    "urlopen",
                    return_value=FakeResponse(),
                ) as urlopen_mock,
            ):
                url = preview_tools.start_preview(
                    "run_20260812_001",
                    5500,
                )
                stopped = preview_tools.stop_preview("run_20260812_001")

        self.assertEqual(url, "http://127.0.0.1:5500/")
        self.assertTrue(stopped)
        self.assertTrue(fake_process.terminated)
        self.assertEqual(fake_process.wait_calls, [5])
        popen_mock.assert_called_once()
        urlopen_mock.assert_called_once_with(
            "http://127.0.0.1:5500/",
            timeout=1,
        )
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

    def test_start_preview_times_out_and_terminates_process(self):
        class FakeProcess:
            def __init__(self):
                self.terminated = False

            def poll(self):
                return None if not self.terminated else 0

            def terminate(self):
                self.terminated = True

            def wait(self, timeout):
                return None

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
                ),
                mock.patch.object(
                    preview_tools,
                    "urlopen",
                    side_effect=OSError("not ready"),
                ),
                mock.patch.object(
                    preview_tools.time,
                    "sleep",
                ),
            ):
                with self.assertRaises(TimeoutError):
                    preview_tools.start_preview(
                        "run_20260812_001",
                        5500,
                        startup_timeout=0,
                    )

        self.assertTrue(fake_process.terminated)
        self.assertNotIn("run_20260812_001", preview_tools._preview_processes)


if __name__ == "__main__":
    unittest.main()
