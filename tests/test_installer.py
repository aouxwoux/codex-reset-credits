from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def test_installer_copies_skill_to_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / "skills"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "install_skill.py"),
                    "--target",
                    str(target),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((target / "track-codex-resets" / "SKILL.md").is_file())
            self.assertIn("Installed.", result.stdout)


if __name__ == "__main__":
    unittest.main()
