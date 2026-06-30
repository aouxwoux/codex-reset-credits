from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]


class PackageSkillTests(unittest.TestCase):
    def test_package_contains_only_skill_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "track-codex-resets-skill.zip"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "package_skill.py"),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Packaged skill:", result.stdout)
            self.assertTrue(output.is_file())

            with ZipFile(output) as archive:
                names = set(archive.namelist())

        self.assertIn("track-codex-resets/SKILL.md", names)
        self.assertIn("track-codex-resets/scripts/reset_expiry.py", names)
        self.assertTrue(all(name.startswith("track-codex-resets/") for name in names))
        self.assertNotIn("README.md", names)
        self.assertNotIn("tools/package_skill.py", names)


if __name__ == "__main__":
    unittest.main()
