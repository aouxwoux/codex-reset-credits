#!/usr/bin/env python3
"""Friendly command front door for Codex reset-credit expiry tools."""

from __future__ import annotations

import sys
from collections.abc import Sequence

import fetch_account_resets
import reset_expiry


ACCOUNT_ALIASES = {"account", "show", "status"}
ESTIMATE_ALIASES = {"estimate", "infer", "public"}
RENDER_ALIASES = {"render", "ledger", "file"}
COMMANDS = {
    "account": ACCOUNT_ALIASES,
    "estimate": ESTIMATE_ALIASES,
    "render": RENDER_ALIASES,
}


HELP_TEXT = """Codex reset credits

Usage:
  python scripts/codex_resets.py account [options]
  python scripts/codex_resets.py estimate --bank-count 3 [options]
  python scripts/codex_resets.py render --input account-resets.local.json [options]
  python scripts/codex_resets.py help [account|estimate|render]

Friendly commands:
  account    Fetch exact account-backed reset credits from local Codex auth.
             Aliases: show, status
  estimate   Estimate from public reset events, a visible bank count, or URLs.
             Aliases: infer, public
  render     Render a saved sanitized ledger or one-off reset timestamps.
             Aliases: ledger, file

Common examples:
  python scripts/codex_resets.py account --timezone Asia/Kolkata
  python scripts/codex_resets.py account --format ledger > account-resets.local.json
  python scripts/codex_resets.py estimate --bank-count 3 --timezone Asia/Kolkata
  python scripts/codex_resets.py render --input account-resets.local.json --timezone Asia/Kolkata

Tip:
  Add --help after a command for the full option list, e.g. account --help.
"""


TOPIC_HELP = {
    "account": """account: fetch exact account-backed reset credits

Default output is a compact Markdown view with the efficiency recommendation.

Examples:
  python scripts/codex_resets.py account --timezone Asia/Kolkata
  python scripts/codex_resets.py account --available-only --limit 2
  python scripts/codex_resets.py account --format ledger > account-resets.local.json

Full option list:
  python scripts/codex_resets.py account --help
""",
    "estimate": """estimate: infer reset expiries when exact account data is unavailable

Use this with a visible reset-bank count, known public events, or one-off status URLs.

Examples:
  python scripts/codex_resets.py estimate --bank-count 3 --timezone Asia/Kolkata
  python scripts/codex_resets.py estimate https://x.com/thsottiaux/status/2070653282440405046
  python scripts/codex_resets.py estimate --from-known-events --format markdown

Full option list:
  python scripts/codex_resets.py estimate --help
""",
    "render": """render: display a saved sanitized ledger or manual reset entries

Use this after account --format ledger, or when you already have exact grant/expiry data.

Examples:
  python scripts/codex_resets.py render --input account-resets.local.json
  python scripts/codex_resets.py render --input account-resets.local.json --format json
  python scripts/codex_resets.py render manual=2026-06-26T23:39:48Z

Full option list:
  python scripts/codex_resets.py render --help
""",
}


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"help", "-h", "--help"}:
        print_help(args[1:] if args and args[0] == "help" else [])
        return 0

    command = args.pop(0)
    canonical = canonical_command(command)
    if canonical is None:
        print(f"error: unknown command '{command}'", file=sys.stderr)
        print("Run `python scripts/codex_resets.py help` for common commands.", file=sys.stderr)
        return 2

    if canonical == "account":
        return run_nested(fetch_account_resets.main, "fetch_account_resets.py", account_defaults(args))
    if canonical == "estimate":
        return run_nested(reset_expiry.main, "reset_expiry.py", args)
    return run_nested(reset_expiry.main, "reset_expiry.py", args)


def print_help(args: Sequence[str]) -> None:
    if not args:
        print(HELP_TEXT)
        return
    topic = canonical_command(args[0])
    if topic in TOPIC_HELP:
        print(TOPIC_HELP[topic])
        return
    print(HELP_TEXT)


def canonical_command(value: str) -> str | None:
    normalized = value.strip().lower()
    for command, aliases in COMMANDS.items():
        if normalized in aliases:
            return command
    return None


def account_defaults(args: list[str]) -> list[str]:
    if any(option_present(args, option) for option in ("--help", "-h")):
        return args
    defaults = list(args)
    if not option_present(args, "--format"):
        defaults.extend(["--format", "markdown"])
    if not option_present(args, "--view"):
        defaults.extend(["--view", "compact"])
        if not option_present(args, "--hide-details"):
            defaults.append("--hide-details")
    return defaults


def option_present(args: Sequence[str], option: str) -> bool:
    return any(arg == option or arg.startswith(f"{option}=") for arg in args)


def run_nested(main_func, script_name: str, args: Sequence[str]) -> int:
    original_argv = sys.argv
    try:
        sys.argv = [script_name, *args]
        return int(main_func())
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        return 0 if exc.code is None else 1
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    raise SystemExit(main())
