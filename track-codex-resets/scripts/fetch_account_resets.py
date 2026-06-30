#!/usr/bin/env python3
"""Fetch and sanitize account-backed Codex reset-credit expiry data."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone, tzinfo
from pathlib import Path
from typing import Any

from reset_expiry import (
    MARKDOWN_VIEWS,
    ResetCredit,
    ResetError,
    format_days,
    parse_timezone,
    render_json,
    render_markdown,
    render_terminal,
    reset_from_mapping,
)


API_URL = "https://chatgpt.com/backend-api/wham/rate-limit-reset-credits"
DEFAULT_AUTH_PATH = Path.home() / ".codex" / "auth.json"
SAFE_CREDIT_FIELDS = {
    "status",
    "reset_type",
    "title",
    "granted_at",
    "expires_at",
    "used_at",
    "redeemed_at",
}


class FetchError(RuntimeError):
    pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read local Codex auth, fetch account-backed reset credits, and print only "
            "sanitized expiry fields."
        )
    )
    parser.add_argument("--auth-json", type=Path, default=DEFAULT_AUTH_PATH, help="Path to Codex auth.json.")
    parser.add_argument("--endpoint", default=API_URL, help="Read-only reset-credit endpoint.")
    parser.add_argument("--timezone", "-t", default="local", help="Display timezone, e.g. UTC or Asia/Kolkata.")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds.")
    parser.add_argument(
        "--format",
        choices=("terminal", "markdown", "json", "ledger"),
        default="terminal",
        help="Output format. ledger emits reset_expiry.py-compatible sanitized input JSON.",
    )
    parser.add_argument(
        "--input-response",
        type=Path,
        help="Use a saved sample response instead of making a network request. Intended for tests only.",
    )
    parser.add_argument("--available-only", action="store_true", help="Only show credits with status=available.")
    parser.add_argument("--dry-run", action="store_true", help="Validate auth shape and print no token values or network data.")
    parser.add_argument(
        "--view",
        choices=MARKDOWN_VIEWS,
        default="table",
        help="Markdown view: compact expiry list, readable table, or full provenance table.",
    )
    parser.add_argument("--limit", type=int, help="Show only the first N credits by expiry in human-readable output.")
    parser.add_argument("--hide-details", action="store_true", help="Hide per-credit provenance details in Markdown output.")
    args = parser.parse_args()

    try:
        display_tz = parse_timezone(args.timezone)
        if args.limit is not None and args.limit < 1:
            raise ResetError("--limit must be at least 1.")
        messages: list[str] = []
        if args.input_response:
            payload = read_json(args.input_response)
            messages.append("Loaded sanitized/test response from --input-response; no account request was made.")
        else:
            auth = read_auth(args.auth_json)
            if args.dry_run:
                print_dry_run(args, auth)
                return 0
            payload = fetch_reset_credits(args.endpoint, auth, args.timeout)

        available_count, resets, skipped = normalize_payload(payload, display_tz, args.available_only)
        messages.append(f"Available reset credits: {available_count}")
        if skipped:
            messages.append(f"Skipped {skipped} credit(s) without usable granted_at or expires_at.")
        if not resets:
            messages.append("No reset credits with usable expiry data were returned.")
    except (OSError, json.JSONDecodeError, ResetError, FetchError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc)
    resets = sorted(resets, key=lambda reset: reset.expires_at)
    expiry_days = 30.0
    if args.format == "ledger":
        print(render_ledger(resets, available_count, display_tz))
    elif args.format == "json":
        print(render_json(resets, now, display_tz, expiry_days, messages))
    elif args.format == "markdown":
        print(
            render_markdown(
                resets,
                now,
                display_tz,
                expiry_days,
                messages,
                view=args.view,
                limit=args.limit,
                show_details=not args.hide_details,
            )
        )
    else:
        print(render_terminal(resets, now, display_tz, expiry_days, messages, limit=args.limit))
    return 0


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_auth(path: Path) -> dict[str, str]:
    data = read_json(path)
    if not isinstance(data, dict):
        raise FetchError("auth.json must be a JSON object.")
    tokens = data.get("tokens")
    if not isinstance(tokens, dict):
        raise FetchError("auth.json does not contain a tokens object.")
    access_token = tokens.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise FetchError("auth.json does not contain tokens.access_token.")
    account_id = tokens.get("account_id")
    if account_id is not None and not isinstance(account_id, str):
        raise FetchError("auth.json contains a non-string tokens.account_id.")
    return {"access_token": access_token, "account_id": account_id or ""}


def fetch_reset_credits(endpoint: str, auth: dict[str, str], timeout: float) -> Any:
    headers = {
        "Authorization": f"Bearer {auth['access_token']}",
        "Accept": "application/json",
        "OpenAI-Beta": "codex-1",
        "originator": "Codex Desktop",
        "User-Agent": "track-codex-resets/0.1",
    }
    if auth.get("account_id"):
        headers["ChatGPT-Account-ID"] = auth["account_id"]

    request = urllib.request.Request(endpoint, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise FetchError(
                f"endpoint returned HTTP {exc.code}; Codex auth may be expired or missing the account header."
            ) from exc
        raise FetchError(f"endpoint returned HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise FetchError(f"request failed: {exc.reason}") from exc


def normalize_payload(
    payload: Any,
    display_tz: tzinfo,
    available_only: bool,
) -> tuple[int, list[ResetCredit], int]:
    data = unwrap_payload(payload)
    available_count = read_count(data)
    raw_credits = data.get("credits", data.get("items", []))
    if raw_credits is None:
        raw_credits = []
    if not isinstance(raw_credits, list):
        raise FetchError("reset-credit response credits field was not a list.")

    resets: list[ResetCredit] = []
    skipped = 0
    for index, raw_credit in enumerate(raw_credits, start=1):
        if not isinstance(raw_credit, dict):
            skipped += 1
            continue
        credit = {key: raw_credit.get(key) for key in SAFE_CREDIT_FIELDS if key in raw_credit}
        status = str(credit.get("status") or "").strip()
        if available_only and status != "available":
            continue
        if not credit.get("granted_at") and not credit.get("expires_at"):
            skipped += 1
            continue

        reset_type = str(credit.get("reset_type") or "codex_rate_limits")
        title = str(credit.get("title") or f"Account reset credit {index}")
        note_parts = [f"account status: {status or 'unknown'}", f"reset_type: {reset_type}"]
        used_at = credit.get("used_at") or credit.get("redeemed_at")
        if used_at:
            note_parts.append(f"used_at: {used_at}")

        mapping = {
            "label": title,
            "grant_at": credit.get("granted_at"),
            "expires_at": credit.get("expires_at"),
            "quantity": 1,
            "kind": "account_credit",
            "confidence": "exact",
            "credit_status": status,
            "source": "account reset-credit endpoint",
            "basis": "exact account expires_at" if credit.get("expires_at") else f"account grant_at + {format_days(30.0)}",
            "note": "; ".join(note_parts),
        }
        resets.append(reset_from_mapping(mapping, 30.0, display_tz))
    return available_count, resets, skipped


def unwrap_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise FetchError("reset-credit response must be a JSON object.")
    data = payload.get("data")
    if isinstance(data, dict) and ("credits" in data or "available_count" in data or "availableCount" in data):
        return data
    return payload


def read_count(data: dict[str, Any]) -> int:
    raw_count = data.get("available_count", data.get("availableCount", 0))
    try:
        return int(raw_count)
    except (TypeError, ValueError):
        return 0


def render_ledger(resets: list[ResetCredit], available_count: int, display_tz: tzinfo) -> str:
    payload = {
        "timezone": getattr(display_tz, "key", display_tz.tzname(None) or "local"),
        "expiry_days": 30,
        "available_count": available_count,
        "resets": [
            {
                "label": reset.label,
                "quantity": reset.quantity,
                "kind": reset.kind,
                "confidence": reset.confidence,
                "credit_status": reset.account_status,
                "grant_at": reset.grant_at.isoformat() if reset.grant_at else None,
                "expires_at": reset.expires_at.isoformat(),
                "source": reset.source,
                "basis": reset.basis,
                "note": reset.note,
            }
            for reset in resets
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def print_dry_run(args: argparse.Namespace, auth: dict[str, str]) -> None:
    account_header = "present" if auth.get("account_id") else "absent"
    print("Dry run only. No network request was made.")
    print(f"Auth file: {args.auth_json}")
    print(f"Endpoint: {args.endpoint}")
    print("Headers: Authorization=<redacted>, Accept=application/json, OpenAI-Beta=codex-1, originator=Codex Desktop")
    print(f"ChatGPT-Account-ID header: {account_header}")


if __name__ == "__main__":
    raise SystemExit(main())
