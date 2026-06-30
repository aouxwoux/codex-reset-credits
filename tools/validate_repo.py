#!/usr/bin/env python3
"""Lightweight repository validation for CI and contributors."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "track-codex-resets"


def main() -> int:
    checks = [
        check_required_files,
        check_skill_frontmatter,
        check_json_files,
        check_python_compile,
        check_sample_commands,
    ]
    for check in checks:
        check()
    print("Repository validation passed.")
    return 0


def check_required_files() -> None:
    required = [
        ROOT / "README.md",
        ROOT / "LICENSE",
        ROOT / "SECURITY.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "LAUNCH.md",
        SKILL / "SKILL.md",
        SKILL / "agents" / "openai.yaml",
        SKILL / "scripts" / "fetch_account_resets.py",
        SKILL / "scripts" / "reset_expiry.py",
        SKILL / "assets" / "known-reset-events.json",
        SKILL / "references" / "reset-credit-format.md",
        ROOT / "examples" / "account-resets.sample.json",
        ROOT / "examples" / "resets.example.json",
        ROOT / "tools" / "install_skill.py",
        ROOT / "tools" / "package_skill.py",
        ROOT / "tests" / "test_reset_expiry.py",
        ROOT / "tests" / "test_fetch_account_resets.py",
        ROOT / "tests" / "test_installer.py",
        ROOT / "tests" / "test_package_skill.py",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        fail("Missing required files: " + ", ".join(missing))


def check_skill_frontmatter() -> None:
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    openai_yaml = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail("SKILL.md must start with YAML frontmatter.")
    try:
        _, frontmatter, _ = text.split("---", 2)
    except ValueError:
        fail("SKILL.md frontmatter is not closed.")
    lines = {line.split(":", 1)[0].strip(): line for line in frontmatter.splitlines() if ":" in line}
    if "name" not in lines or "description" not in lines:
        fail("SKILL.md frontmatter must include name and description.")
    if "track-codex-resets" not in lines["name"]:
        fail("SKILL.md name must be track-codex-resets.")
    if "fetch exact account reset-credit expiries" not in lines["description"]:
        fail("SKILL.md description should advertise exact account fetching.")
    if "Codex Reset Credits" not in text:
        fail("SKILL.md should use the natural public title.")
    if 'display_name: "Codex Reset Credits"' not in openai_yaml:
        fail("agents/openai.yaml display_name should match the public title.")


def check_json_files() -> None:
    json_paths = [
        SKILL / "assets" / "known-reset-events.json",
        ROOT / "examples" / "account-resets.sample.json",
        ROOT / "examples" / "resets.example.json",
    ]
    for path in json_paths:
        with path.open("r", encoding="utf-8") as handle:
            json.load(handle)


def check_python_compile() -> None:
    run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(SKILL / "scripts" / "reset_expiry.py"),
            str(SKILL / "scripts" / "fetch_account_resets.py"),
            str(ROOT / "tools" / "install_skill.py"),
            str(ROOT / "tools" / "package_skill.py"),
            str(ROOT / "tools" / "validate_repo.py"),
        ]
    )
    run([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests")])


def check_sample_commands() -> None:
    run(
        [
            sys.executable,
            str(SKILL / "scripts" / "fetch_account_resets.py"),
            "--input-response",
            str(ROOT / "examples" / "account-resets.sample.json"),
            "--timezone",
            "UTC",
            "--format",
            "json",
        ]
    )
    run(
        [
            sys.executable,
            str(SKILL / "scripts" / "fetch_account_resets.py"),
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
        ]
    )
    run(
        [
            sys.executable,
            str(SKILL / "scripts" / "reset_expiry.py"),
            "--bank-count",
            "3",
            "--timezone",
            "UTC",
            "--format",
            "json",
            "--now",
            "2026-06-28T00:00:00Z",
        ]
    )
    run(
        [
            sys.executable,
            str(ROOT / "tools" / "install_skill.py"),
            "--target",
            str(ROOT / ".tmp-install"),
            "--dry-run",
        ]
    )
    run(
        [
            sys.executable,
            str(ROOT / "tools" / "package_skill.py"),
            "--output",
            str(ROOT / ".tmp-install" / "track-codex-resets-skill.zip"),
            "--dry-run",
        ]
    )


def run(command: list[str]) -> None:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if result.returncode != 0:
        fail(
            "Command failed: "
            + " ".join(command)
            + "\nSTDOUT:\n"
            + result.stdout
            + "\nSTDERR:\n"
            + result.stderr
        )


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    raise SystemExit(main())
