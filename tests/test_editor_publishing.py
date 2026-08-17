from __future__ import annotations

import subprocess
import unittest

from editor.publishing import START_COMMAND, STATUS_COMMAND, SystemdPublisher


class SystemdPublisherTests(unittest.TestCase):
    def test_uses_only_fixed_systemd_commands(self) -> None:
        calls: list[tuple[str, ...]] = []

        def runner(command, **kwargs):
            calls.append(tuple(command))
            if tuple(command) == STATUS_COMMAND:
                return subprocess.CompletedProcess(command, 0, stdout="inactive\n", stderr="secret=hidden")
            if tuple(command) == START_COMMAND:
                return subprocess.CompletedProcess(command, 0, stdout="ignored", stderr="ignored")
            raise AssertionError(f"Unexpected command: {command!r}")

        result = SystemdPublisher(runner=runner).deploy()
        self.assertTrue(result.success)
        self.assertEqual(calls, [STATUS_COMMAND, START_COMMAND])
        self.assertNotIn("ignored", result.message)
        self.assertNotIn("secret", result.message)

    def test_command_failure_is_sanitized(self) -> None:
        def runner(command, **kwargs):
            if tuple(command) == STATUS_COMMAND:
                return subprocess.CompletedProcess(command, 0, stdout="inactive\n", stderr="")
            return subprocess.CompletedProcess(command, 1, stdout="WEATHERAPI_KEY=value", stderr="private path")

        result = SystemdPublisher(runner=runner).deploy()
        self.assertFalse(result.success)
        self.assertNotIn("WEATHERAPI", result.message)
        self.assertNotIn("private path", result.message)


if __name__ == "__main__":
    unittest.main()
