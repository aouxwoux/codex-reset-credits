from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import timezone


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "track-codex-resets" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import fetch_account_resets  # noqa: E402


class FetchAccountResetsTests(unittest.TestCase):
    def test_normalize_payload_sanitizes_sensitive_fields(self) -> None:
        payload = {
            "available_count": 1,
            "credits": [
                {
                    "id": "RateLimitResetCredit_secret",
                    "profile_id": "profile_secret",
                    "status": "available",
                    "reset_type": "codex_rate_limits",
                    "title": "Full reset",
                    "granted_at": "2026-06-12T03:38:11Z",
                    "expires_at": "2026-07-12T03:38:11Z",
                }
            ],
        }

        count, resets, skipped = fetch_account_resets.normalize_payload(payload, timezone.utc, available_only=False)
        ledger = fetch_account_resets.render_ledger(resets, count, timezone.utc)

        self.assertEqual(count, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(resets[0].account_status, "available")
        self.assertNotIn("RateLimitResetCredit_secret", ledger)
        self.assertNotIn("profile_secret", ledger)

    def test_available_only_filters_used_credits(self) -> None:
        payload = {
            "available_count": 1,
            "credits": [
                {
                    "status": "used",
                    "title": "Used reset",
                    "granted_at": "2026-06-01T00:00:00Z",
                    "expires_at": "2026-07-01T00:00:00Z",
                },
                {
                    "status": "available",
                    "title": "Available reset",
                    "granted_at": "2026-06-12T00:00:00Z",
                    "expires_at": "2026-07-12T00:00:00Z",
                },
            ],
        }

        _, resets, _ = fetch_account_resets.normalize_payload(payload, timezone.utc, available_only=True)

        self.assertEqual(len(resets), 1)
        self.assertEqual(resets[0].label, "Available reset")

    def test_read_auth_returns_only_needed_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            auth_path = Path(tmp_dir) / "auth.json"
            auth_path.write_text(
                json.dumps(
                    {
                        "auth_mode": "chatgpt",
                        "tokens": {
                            "access_token": "access-secret",
                            "refresh_token": "refresh-secret",
                            "account_id": "account-secret",
                        },
                    }
                ),
                encoding="utf-8",
            )

            auth = fetch_account_resets.read_auth(auth_path)

        self.assertEqual(auth, {"access_token": "access-secret", "account_id": "account-secret"})

    def test_cli_accepts_markdown_view_controls(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "fetch_account_resets.py"),
                "--input-response",
                str(ROOT / "examples" / "account-resets.sample.json"),
                "--timezone",
                "UTC",
                "--format",
                "markdown",
                "--view",
                "compact",
                "--limit",
                "1",
                "--hide-details",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("## Upcoming Expiries", result.stdout)
        self.assertIn("Showing first 1 of 2 credits by expiry.", result.stdout)
        self.assertNotIn("## Credits Table", result.stdout)
        self.assertNotIn("## Details", result.stdout)


if __name__ == "__main__":
    unittest.main()
