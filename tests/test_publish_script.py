from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


class PublishScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repo"
        self.bin_dir = Path(self.temporary.name) / "bin"
        self.logs_dir = Path(self.temporary.name) / "logs"
        (self.root / "scripts").mkdir(parents=True)
        self.bin_dir.mkdir()
        self.logs_dir.mkdir()
        self.publish_script = self.root / "scripts" / "publish.sh"
        self.dev_build_script = self.root / "scripts" / "dev-build.sh"
        self.publish_script.write_text(
            Path("/srv/repos/personal/argensonix/nico.com.ar/scripts/publish.sh").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        self.publish_script.chmod(self.publish_script.stat().st_mode | stat.S_IEXEC)
        self.dev_build_script.write_text(
            f"#!/usr/bin/env bash\nset -euo pipefail\necho build >> '{self.logs_dir / 'build.log'}'\n",
            encoding="utf-8",
        )
        self.dev_build_script.chmod(self.dev_build_script.stat().st_mode | stat.S_IEXEC)
        self._write_fake_command(
            "git",
            """#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = "-C" ] && [ "${3:-}" = "branch" ] && [ "${4:-}" = "--show-current" ]; then
  printf '%s\n' "${FAKE_GIT_BRANCH:-feat/bilingual-site}"
  exit 0
fi
echo "unexpected git call: $*" >&2
exit 1
""",
        )
        self._write_fake_command(
            "rsync",
            f"""#!/usr/bin/env bash
set -euo pipefail
echo rsync >> '{self.logs_dir / 'rsync.log'}'
exit 0
""",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_fake_command(self, name: str, content: str) -> None:
        path = self.bin_dir / name
        path.write_text(content, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IEXEC)

    def _run_publish(self, *, branch: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PATH"] = f"{self.bin_dir}:{env['PATH']}"
        env["FAKE_GIT_BRANCH"] = branch
        return subprocess.run(
            ["bash", str(self.publish_script)],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_refuses_to_publish_off_main_before_build_or_rsync(self) -> None:
        result = self._run_publish(branch="feat/bilingual-site")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Refusing to publish: current branch is 'feat/bilingual-site'", result.stderr)
        self.assertFalse((self.logs_dir / "build.log").exists())
        self.assertFalse((self.logs_dir / "rsync.log").exists())

    def test_allows_publish_on_main(self) -> None:
        result = self._run_publish(branch="main")

        self.assertEqual(result.returncode, 0)
        self.assertTrue((self.logs_dir / "build.log").exists())
        self.assertTrue((self.logs_dir / "rsync.log").exists())
        self.assertIn("Publish complete:", result.stdout)


if __name__ == "__main__":
    unittest.main()
