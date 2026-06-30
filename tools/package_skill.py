#!/usr/bin/env python3
"""Package the track-codex-resets skill as a skill-only release zip."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


SKILL_NAME = "track-codex-resets"
ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / SKILL_NAME
DEFAULT_OUTPUT = ROOT / "dist" / f"{SKILL_NAME}-skill.zip"
REQUIRED_FILES = [
    "SKILL.md",
    "agents/openai.yaml",
    "assets/known-reset-events.json",
    "references/reset-credit-format.md",
    "scripts/fetch_account_resets.py",
    "scripts/reset_expiry.py",
]
IGNORED_DIRS = {"__pycache__", ".pytest_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a release zip containing only the Codex skill folder.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output zip path. Defaults to {DEFAULT_OUTPUT.relative_to(ROOT)}.",
    )
    parser.add_argument("--dry-run", action="store_true", help="List files that would be packaged without writing.")
    args = parser.parse_args()

    try:
        files = collect_skill_files(SKILL_DIR)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        print("Dry run only. The release zip would contain:")
        for path in files:
            print(f"  {zip_name(path)}")
        return 0

    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, zip_name(path))

    print(f"Packaged skill: {output}")
    print(f"Files: {len(files)}")
    print(f"Install by extracting {SKILL_NAME}/ into ~/.codex/skills/")
    return 0


def collect_skill_files(skill_dir: Path) -> list[Path]:
    if not skill_dir.is_dir():
        raise OSError(f"missing skill directory: {skill_dir}")

    missing = [relative for relative in REQUIRED_FILES if not (skill_dir / relative).is_file()]
    if missing:
        raise OSError("missing required skill file(s): " + ", ".join(missing))

    files: list[Path] = []
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(skill_dir).parts
        if any(part in IGNORED_DIRS for part in relative_parts):
            continue
        if path.suffix in IGNORED_SUFFIXES:
            continue
        files.append(path)
    return files


def zip_name(path: Path) -> str:
    return f"{SKILL_NAME}/{path.relative_to(SKILL_DIR).as_posix()}"


if __name__ == "__main__":
    raise SystemExit(main())
