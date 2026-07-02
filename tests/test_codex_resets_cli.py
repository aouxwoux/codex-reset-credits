from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "track-codex-resets" / "scripts" / "codex_resets.py"


class CodexResetsCliTests(unittest.TestCase):
    def test_help_command_shows_friendly_commands(self) -> None:
        result = run_cli("help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Friendly commands:", result.stdout)
        self.assertIn("account", result.stdout)
        self.assertIn("estimate", result.stdout)
        self.assertIn("render", result.stdout)

    def test_account_defaults_to_compact_markdown(self) -> None:
        result = run_cli(
            "account",
            "--input-response",
            str(ROOT / "examples" / "account-resets.sample.json"),
            "--timezone",
            "UTC",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# Codex Reset Credits", result.stdout)
        self.assertIn("## Efficiency Recommendation", result.stdout)
        self.assertIn("## Upcoming Expiries", result.stdout)
        self.assertNotIn("## Credits Table", result.stdout)

    def test_estimate_command_forwards_to_json_renderer(self) -> None:
        result = run_cli(
            "estimate",
            "--bank-count",
            "1",
            "--timezone",
            "UTC",
            "--format",
            "json",
            "--now",
            "2026-06-28T00:00:00Z",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("efficiency_recommendation", payload)
        self.assertEqual(len(payload["resets"]), 1)

    def test_status_alias_uses_account_command(self) -> None:
        result = run_cli(
            "status",
            "--input-response",
            str(ROOT / "examples" / "account-resets.sample.json"),
            "--timezone",
            "UTC",
            "--limit",
            "1",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Available reset credits: 2", result.stdout)
        self.assertIn("Showing first 1 of 2 credits by expiry.", result.stdout)


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


if __name__ == "__main__":
    unittest.main()
