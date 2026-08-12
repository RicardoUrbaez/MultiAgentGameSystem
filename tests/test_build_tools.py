import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from game_builder.tools import build_tools


class BuildToolsTests(unittest.TestCase):
    def test_npm_build_returns_structured_result_and_writes_log(self):
        completed = types.SimpleNamespace(
            returncode=0,
            stdout="built",
            stderr="",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run_path = Path(tmp)

            with (
                mock.patch.object(
                    build_tools,
                    "get_run_path",
                    return_value=run_path,
                ),
                mock.patch.object(
                    build_tools,
                    "_resolve_command",
                    side_effect=lambda value: value,
                ),
                mock.patch.object(
                    build_tools.subprocess,
                    "run",
                    return_value=completed,
                ) as run_mock,
            ):
                result = build_tools.npm_build("run_20260812_001")

            self.assertTrue(result.success)
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.command, "npm run build-nolog")
            self.assertTrue((run_path / "logs" / "build.log").exists())
            run_mock.assert_called_once()
            call_kwargs = run_mock.call_args.kwargs
            self.assertFalse(call_kwargs["check"])
            self.assertEqual(call_kwargs["cwd"], run_path)
            self.assertNotIn("shell", call_kwargs)

    def test_npm_install_and_typecheck_use_explicit_argument_arrays(self):
        completed = types.SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="type error",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run_path = Path(tmp)

            with (
                mock.patch.object(
                    build_tools,
                    "get_run_path",
                    return_value=run_path,
                ),
                mock.patch.object(
                    build_tools,
                    "_resolve_command",
                    side_effect=lambda value: value,
                ),
                mock.patch.object(
                    build_tools.subprocess,
                    "run",
                    return_value=completed,
                ) as run_mock,
            ):
                install_result = build_tools.npm_install(
                    "run_20260812_001"
                )
                typecheck_result = build_tools.npm_typecheck(
                    "run_20260812_001"
                )

            install_command = run_mock.call_args_list[0].args[0]
            typecheck_command = run_mock.call_args_list[1].args[0]

            self.assertEqual(
                install_command,
                [
                    "npm",
                    "ci",
                    "--prefer-offline",
                    "--no-audit",
                    "--no-fund",
                ],
            )
            self.assertEqual(typecheck_command, ["npx", "tsc", "--noEmit"])
            self.assertFalse(install_result.success)
            self.assertFalse(typecheck_result.success)

    def test_get_build_log_returns_empty_string_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(
                build_tools,
                "get_run_path",
                return_value=Path(tmp),
            ):
                self.assertEqual(
                    build_tools.get_build_log("run_20260812_001"),
                    "",
                )


if __name__ == "__main__":
    unittest.main()
