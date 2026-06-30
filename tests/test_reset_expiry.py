from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "track-codex-resets" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import reset_expiry  # noqa: E402


class ResetExpiryTests(unittest.TestCase):
    def test_x_status_id_decodes_to_announcement_timestamp(self) -> None:
        timestamp = reset_expiry.timestamp_from_status_url(
            "https://x.com/thsottiaux/status/2070653282440405046"
        )

        self.assertIsNotNone(timestamp)
        self.assertEqual(timestamp.isoformat(), "2026-06-26T23:39:48.068000+00:00")

    def test_grant_delay_creates_expiry_window(self) -> None:
        reset = reset_expiry.reset_from_mapping(
            {
                "label": "Tibo reset",
                "grant_at": "2026-06-26T23:39:48Z",
                "grant_delay_hours": 4,
            },
            30,
            timezone.utc,
        )

        self.assertEqual(reset.expires_at.isoformat(), "2026-07-26T23:39:48+00:00")
        self.assertEqual(reset.expires_at_latest.isoformat(), "2026-07-27T03:39:48+00:00")
        self.assertEqual(reset_expiry.status_for(reset, datetime(2026, 7, 27, 1, tzinfo=timezone.utc)), "window")

    def test_known_event_catalog_has_bankable_resets(self) -> None:
        events = reset_expiry.load_known_events(
            ROOT / "track-codex-resets" / "assets" / "known-reset-events.json",
            30,
            timezone.utc,
            include_immediate=False,
        )

        self.assertGreaterEqual(len(events), 3)
        self.assertTrue(all(reset_expiry.is_bankable(event) for event in events))

    def test_markdown_renderer_uses_natural_copy(self) -> None:
        reset = reset_expiry.ResetCredit(
            label="Full reset",
            quantity=1,
            grant_at=datetime(2026, 6, 12, 3, 38, 11, tzinfo=timezone.utc),
            expires_at=datetime(2026, 7, 12, 3, 38, 11, tzinfo=timezone.utc),
            source="account reset-credit endpoint",
            basis="exact account expires_at",
            confidence="exact",
            account_status="available",
            kind="account_credit",
        )

        output = reset_expiry.render_markdown(
            [reset],
            datetime(2026, 6, 28, tzinfo=timezone.utc),
            timezone.utc,
            30,
            ["Available reset credits: 1"],
        )

        self.assertIn("# Codex Reset Credits", output)
        self.assertIn("## Next To Expire", output)
        self.assertIn("Full reset (available)", output)
        self.assertIn("Available reset credits: 1", output)
        self.assertIn("| # | Status | Qty | Expires Local | Expires UTC | Time Left | Confidence |", output)
        self.assertIn("Rule: `expires_at = grant_at + 30 days`", output)
        self.assertNotIn("| Status | Credit | Qty | Kind | Granted | Expires |", output)

    def test_json_renderer_is_machine_readable(self) -> None:
        reset = reset_expiry.reset_from_mapping(
            {
                "label": "Exact reset",
                "grant_at": "2026-06-12T03:38:11Z",
                "expires_at": "2026-07-12T03:38:11Z",
                "credit_status": "available",
                "confidence": "exact",
            },
            30,
            timezone.utc,
        )

        output = reset_expiry.render_json([reset], datetime(2026, 6, 28, tzinfo=timezone.utc), timezone.utc, 30)
        payload = json.loads(output)

        self.assertEqual(payload["resets"][0]["account_status"], "available")
        self.assertEqual(payload["resets"][0]["confidence"], "exact")

    def test_markdown_views_and_limit_give_user_control(self) -> None:
        resets = [
            reset_expiry.reset_from_mapping(
                {
                    "label": "First reset",
                    "grant_at": "2026-06-12T03:38:11Z",
                    "expires_at": "2026-07-12T03:38:11Z",
                    "credit_status": "available",
                    "confidence": "exact",
                },
                30,
                timezone.utc,
            ),
            reset_expiry.reset_from_mapping(
                {
                    "label": "Second reset",
                    "grant_at": "2026-06-18T00:17:14Z",
                    "expires_at": "2026-07-18T00:17:14Z",
                    "credit_status": "available",
                    "confidence": "exact",
                },
                30,
                timezone.utc,
            ),
        ]

        compact = reset_expiry.render_markdown(
            resets,
            datetime(2026, 6, 28, tzinfo=timezone.utc),
            timezone.utc,
            30,
            ["Available reset credits: 2"],
            view="compact",
            show_details=False,
        )
        self.assertIn("## Upcoming Expiries", compact)
        self.assertIn("First reset (available)", compact)
        self.assertIn("Second reset (available)", compact)
        self.assertNotIn("## Credits Table", compact)
        self.assertNotIn("## Details", compact)

        full_limited = reset_expiry.render_markdown(
            resets,
            datetime(2026, 6, 28, tzinfo=timezone.utc),
            timezone.utc,
            30,
            ["Available reset credits: 2"],
            view="full",
            limit=1,
        )
        self.assertIn("## Full Ledger", full_limited)
        self.assertIn("Showing first 1 of 2 credits by expiry.", full_limited)
        self.assertIn("First reset (available)", full_limited)
        self.assertNotIn("Second reset (available)", full_limited)


if __name__ == "__main__":
    unittest.main()
