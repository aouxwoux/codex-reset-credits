#!/usr/bin/env python3
"""Install the track-codex-resets skill into a local Codex skills directory."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


SKILL_NAME = "track-codex-resets"
REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / SKILL_NAME


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the track-codex-resets Codex skill.")
    parser.add_argument(
        "--target",
        type=Path,
        default=Path.home() / ".codex" / "skills",
        help="Codex skills directory. Defaults to ~/.codex/skills.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite an existing installed skill.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be copied without writing files.")
    args = parser.parse_args()

    if not (SOURCE / "SKILL.md").is_file():
        print(f"error: missing skill source at {SOURCE}", file=sys.stderr)
        return 2

    target_dir = args.target.expanduser().resolve()
    destination = target_dir / SKILL_NAME

    print(f"Source:      {SOURCE}")
    print(f"Destination: {destination}")

    if args.dry_run:
        print("Dry run only. No files were copied.")
        return 0

    if destination.exists():
        if not args.force:
            print("error: destination already exists. Re-run with --force to overwrite.", file=sys.stderr)
            return 2
        if not destination.is_dir():
            print("error: destination exists but is not a directory.", file=sys.stderr)
            return 2
        shutil.rmtree(destination)

    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    print("Installed.")
    print("Try: Use $track-codex-resets to show when my Codex reset credits expire.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
