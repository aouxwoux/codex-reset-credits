#!/usr/bin/env python3
"""Render timezone-aware Codex reset-credit expiry ledgers."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any, Iterable

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover - Python < 3.9 fallback
    ZoneInfo = None  # type: ignore[assignment]

    class ZoneInfoNotFoundError(Exception):
        pass


TWITTER_EPOCH_MS = 1288834974657
STATUS_RE = re.compile(r"(?:x|twitter)\.com/([^/\s]+)/status/(\d+)|status/(\d+)")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
OFFSET_RE = re.compile(r"^([+-])(\d{2}):?(\d{2})$")


@dataclass(frozen=True)
class ResetCredit:
    label: str
    quantity: int
    grant_at: datetime | None
    expires_at: datetime
    source: str
    basis: str
    note: str = ""
    grant_at_latest: datetime | None = None
    expires_at_latest: datetime | None = None
    kind: str = "reset"
    confidence: str = "medium"
    account_status: str = ""

    def label_with_status(self) -> str:
        if not self.account_status:
            return self.label
        return f"{self.label} ({self.account_status})"


class ResetError(ValueError):
    pass


def main() -> int:
    known_events_default = Path(__file__).resolve().parents[1] / "assets" / "known-reset-events.json"
    parser = argparse.ArgumentParser(
        description="Render a clear expiry ledger for Codex reset credits.",
        epilog=(
            "Inputs may be ISO timestamps, X/Twitter status URLs, or label=value "
            "pairs such as tibo=https://x.com/thsottiaux/status/2070653282440405046."
        ),
    )
    parser.add_argument("resets", nargs="*", help="One-off reset sources.")
    parser.add_argument("-i", "--input", type=Path, help="JSON reset ledger file.")
    parser.add_argument("-t", "--timezone", help="Display timezone, e.g. UTC, Asia/Kolkata, or +05:30.")
    parser.add_argument("--expiry-days", type=float, help="Default expiry window in days (default: input file or 30).")
    parser.add_argument("--known-events", type=Path, default=known_events_default, help="Known public reset-event catalog.")
    parser.add_argument("--from-known-events", action="store_true", help="Render likely banked reset events from the catalog.")
    parser.add_argument("--bank-count", type=int, help="Infer active banked resets by selecting the latest N likely bankable events.")
    parser.add_argument("--include-immediate", action="store_true", help="Include immediate/non-banked reset events from the catalog.")
    parser.add_argument("--now", help="Override current time with an ISO timestamp for testing.")
    parser.add_argument("--format", choices=("terminal", "markdown", "json"), default="terminal")
    args = parser.parse_args()

    try:
        config = read_config(args.input)
        tz_name = args.timezone or config.get("timezone") or "local"
        display_tz = parse_timezone(tz_name)
        now = parse_datetime(args.now, display_tz).astimezone(timezone.utc) if args.now else datetime.now(timezone.utc)
        expiry_days = float(args.expiry_days if args.expiry_days is not None else config.get("expiry_days", 30.0))
        resets = load_resets(config, args.resets, expiry_days, display_tz)
        messages: list[str] = []
        if args.from_known_events or args.bank_count is not None:
            known_resets = load_known_events(args.known_events, expiry_days, display_tz, args.include_immediate)
            if args.bank_count is not None:
                if args.bank_count < 1:
                    raise ResetError("--bank-count must be at least 1.")
                candidates = [
                    reset
                    for reset in known_resets
                    if is_bankable(reset) and window_latest(reset) >= now
                ]
                selected = sorted(candidates, key=lambda reset: reset.grant_at or reset.expires_at)[-args.bank_count :]
                if len(selected) < args.bank_count:
                    messages.append(
                        f"Only found {len(selected)} active likely banked public event(s) for requested bank count {args.bank_count}."
                    )
                messages.append(
                    f"Inference mode: matched {len(selected)} visible banked reset(s) to the latest active likely bankable public event(s)."
                )
                resets.extend(selected)
            else:
                resets.extend([reset for reset in known_resets if args.include_immediate or is_bankable(reset)])
        if not resets:
            raise ResetError("No resets found. Pass a status URL, ISO timestamp, or --input JSON file.")
    except (OSError, json.JSONDecodeError, ResetError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    resets = sorted(resets, key=lambda reset: reset.expires_at)
    if args.format == "json":
        print(render_json(resets, now, display_tz, expiry_days, messages))
    elif args.format == "markdown":
        print(render_markdown(resets, now, display_tz, expiry_days, messages))
    else:
        print(render_terminal(resets, now, display_tz, expiry_days, messages))
    return 0


def read_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return {"resets": data}
    if not isinstance(data, dict):
        raise ResetError("Input JSON must be an object or a list of reset entries.")
    return data


def load_resets(
    config: dict[str, Any],
    cli_values: Iterable[str],
    expiry_days: float,
    display_tz: tzinfo,
) -> list[ResetCredit]:
    resets: list[ResetCredit] = []
    for item in config.get("resets", []):
        if not isinstance(item, dict):
            raise ResetError("Each JSON reset entry must be an object.")
        resets.append(reset_from_mapping(item, expiry_days, display_tz))

    for value in cli_values:
        label, source_value = split_label(value)
        resets.append(reset_from_value(source_value, label, expiry_days, display_tz))
    return resets


def load_known_events(
    path: Path,
    expiry_days: float,
    display_tz: tzinfo,
    include_immediate: bool,
) -> list[ResetCredit]:
    config = read_config(path)
    events = config.get("events", config.get("resets", []))
    if not isinstance(events, list):
        raise ResetError("Known reset-event catalog must contain an events list.")

    resets: list[ResetCredit] = []
    for item in events:
        if not isinstance(item, dict):
            raise ResetError("Each known reset event must be an object.")
        if not include_immediate and not bool(item.get("bankable", False)):
            continue
        resets.append(reset_from_mapping(item, expiry_days, display_tz))
    return resets


def reset_from_mapping(item: dict[str, Any], default_expiry_days: float, default_tz: tzinfo) -> ResetCredit:
    expiry_days = float(item.get("expiry_days", default_expiry_days))
    source = str(item.get("source") or item.get("url") or item.get("status_url") or "").strip()
    label = str(item.get("label") or "").strip()
    quantity = int(item.get("quantity", item.get("count", 1)))
    note = str(item.get("note") or "").strip()
    kind = str(item.get("kind") or "reset").strip()
    confidence = str(item.get("confidence") or "medium").strip()
    account_status = str(item.get("credit_status") or item.get("account_status") or item.get("status") or "").strip()

    grant_at = parse_optional_datetime(item.get("grant_at"), default_tz)
    grant_at_latest = parse_optional_datetime(item.get("grant_at_latest"), default_tz)
    expires_at = parse_optional_datetime(item.get("expires_at"), default_tz)
    expires_at_latest = parse_optional_datetime(item.get("expires_at_latest"), default_tz)
    basis = "provided expiry"

    if grant_at is None and source:
        grant_at = timestamp_from_status_url(source)
        if grant_at is not None:
            basis = "estimated from announcement URL"
    if "basis" in item:
        basis = str(item["basis"])

    if grant_at is not None and grant_at_latest is None and item.get("grant_delay_hours") is not None:
        grant_at_latest = grant_at + timedelta(hours=float(item["grant_delay_hours"]))

    if expires_at is None:
        if grant_at is None:
            raise ResetError(f"Reset entry needs expires_at, grant_at, or a status URL: {item}")
        expires_at = grant_at + timedelta(days=expiry_days)
        if basis == "provided expiry":
            basis = f"grant_at + {format_days(expiry_days)}"
    if expires_at_latest is None and grant_at_latest is not None:
        expires_at_latest = grant_at_latest + timedelta(days=expiry_days)
    if expires_at_latest is not None and expires_at_latest <= expires_at:
        expires_at_latest = None
    if grant_at_latest is not None and grant_at is not None and grant_at_latest <= grant_at:
        grant_at_latest = None
    if not label:
        label = label_from_source(source, grant_at)

    return ResetCredit(
        label=label,
        quantity=quantity,
        grant_at=grant_at,
        expires_at=expires_at.astimezone(timezone.utc),
        source=source,
        basis=basis,
        note=note,
        grant_at_latest=grant_at_latest,
        expires_at_latest=expires_at_latest.astimezone(timezone.utc) if expires_at_latest else None,
        kind=kind,
        confidence=confidence,
        account_status=account_status,
    )


def reset_from_value(value: str, label: str | None, expiry_days: float, default_tz: tzinfo) -> ResetCredit:
    value = value.strip()
    if not value:
        raise ResetError("Empty reset value.")

    grant_at = timestamp_from_status_url(value)
    source = value if grant_at else ""
    basis = "estimated from announcement URL" if grant_at else f"grant_at + {format_days(expiry_days)}"
    if grant_at is None:
        grant_at = parse_datetime(value, default_tz)
    return ResetCredit(
        label=label or label_from_source(source, grant_at),
        quantity=1,
        grant_at=grant_at,
        expires_at=grant_at + timedelta(days=expiry_days),
        source=source,
        basis=basis,
        kind="manual",
    )


def split_label(value: str) -> tuple[str | None, str]:
    if "=" not in value:
        return None, value
    label, raw_value = value.split("=", 1)
    label = label.strip()
    return label or None, raw_value.strip()


def timestamp_from_status_url(value: str) -> datetime | None:
    match = STATUS_RE.search(value)
    if not match:
        return None
    snowflake = int(match.group(2) or match.group(3))
    timestamp_ms = (snowflake >> 22) + TWITTER_EPOCH_MS
    return datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc)


def parse_optional_datetime(value: Any, default_tz: tzinfo) -> datetime | None:
    if value in (None, ""):
        return None
    return parse_datetime(str(value), default_tz)


def parse_datetime(value: str, default_tz: tzinfo) -> datetime:
    normalized = value.strip()
    if ISO_DATE_RE.match(normalized):
        normalized = f"{normalized}T00:00:00"
    normalized = normalized.replace(" UTC", "+00:00").replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ResetError(f"Could not parse datetime '{value}'. Use ISO format, e.g. 2026-06-26T23:39:48Z.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=default_tz)
    return parsed.astimezone(timezone.utc)


def parse_timezone(value: str) -> tzinfo:
    normalized = value.strip()
    if normalized.lower() in ("", "local"):
        return datetime.now().astimezone().tzinfo or timezone.utc
    if normalized.upper() in ("UTC", "Z"):
        return timezone.utc
    offset_match = OFFSET_RE.match(normalized)
    if offset_match:
        sign, hours, minutes = offset_match.groups()
        delta = timedelta(hours=int(hours), minutes=int(minutes))
        if sign == "-":
            delta = -delta
        return timezone(delta)
    if ZoneInfo is not None:
        try:
            return ZoneInfo(normalized)  # type: ignore[operator]
        except ZoneInfoNotFoundError as exc:
            raise ResetError(
                f"Timezone '{value}' was not found. Install Python's tzdata package or pass an offset like +05:30."
            ) from exc
    raise ResetError("Named timezones require Python 3.9+ zoneinfo. Pass an offset like +05:30 instead.")


def label_from_source(source: str, grant_at: datetime | None) -> str:
    if source:
        match = STATUS_RE.search(source)
        if match:
            handle = match.group(1) or "x"
            date = grant_at.date().isoformat() if grant_at else "unknown date"
            return f"{handle} reset {date}"
    if grant_at:
        return f"Codex reset {grant_at.date().isoformat()}"
    return "Codex reset"


def render_terminal(
    resets: list[ResetCredit],
    now: datetime,
    display_tz: tzinfo,
    expiry_days: float,
    messages: list[str] | None = None,
) -> str:
    next_reset = next((reset for reset in resets if reset.expires_at >= now), resets[0])
    lines = [
        "Codex reset credits",
        f"Timezone: {timezone_label(display_tz)}",
        f"Now: {format_dt(now, display_tz)}",
        f"Default rule: expires_at = grant_at + {format_days(expiry_days)} unless expires_at is provided",
        "",
        "Next reset credit to expire",
        f"  {next_reset.label} ({next_reset.quantity} credit{plural(next_reset.quantity)})",
        f"  Expires: {format_dt(next_reset.expires_at, display_tz)}",
        f"  UTC:     {format_dt(next_reset.expires_at, timezone.utc)}",
        f"  Left:    {format_duration(next_reset.expires_at - now)}",
        "",
    ]
    if messages:
        lines.extend(["Run notes", *[f"  {message}" for message in messages], ""])

    include_credit_status = any(reset.account_status for reset in resets)
    headers = ["Status"]
    if include_credit_status:
        headers.append("Credit status")
    headers.extend(["Credit", "Qty", "Kind", "Expires", "Time left", "Confidence", "Basis", "Source"])
    rows = []
    for reset in resets:
        row = [status_for(reset, now)]
        if include_credit_status:
            row.append(reset.account_status)
        row.extend(
            [
                reset.label,
                str(reset.quantity),
                humanize(reset.kind),
                format_window(reset.expires_at, reset.expires_at_latest, display_tz),
                format_duration_window(reset, now),
                humanize(reset.confidence),
                reset.basis,
                short_source(reset.source),
            ]
        )
        rows.append(row)
    lines.append(render_table(headers, rows))
    notes = [f"{reset.label}: {reset.note}" for reset in resets if reset.note]
    if notes:
        lines.extend(["", "Notes", *[f"  {note}" for note in notes]])
    return "\n".join(lines)


def render_markdown(
    resets: list[ResetCredit],
    now: datetime,
    display_tz: tzinfo,
    expiry_days: float,
    messages: list[str] | None = None,
) -> str:
    next_reset = next((reset for reset in resets if reset.expires_at >= now), resets[0])
    lines = [
        "# Codex Reset Credits",
        "",
        f"- Timezone: `{timezone_label(display_tz)}`",
        f"- Now: `{format_dt(now, display_tz)}`",
        f"- Default rule: `expires_at = grant_at + {format_days(expiry_days)}` unless `expires_at` is provided",
        f"- Next expiring credit: **{escape_md(next_reset.label)}** at `{format_dt(next_reset.expires_at, display_tz)}` ({format_duration(next_reset.expires_at - now)})",
        "",
    ]
    if messages:
        lines.extend(["## Run Notes", "", *[f"- {escape_md(message)}" for message in messages], ""])
    lines.extend(
        [
            "| Status | Credit | Qty | Kind | Granted | Expires | Expires UTC | Time left | Confidence | Basis | Source |",
            "| --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for reset in resets:
        lines.append(
            "| "
            + " | ".join(
                [
                    status_for(reset, now),
                    escape_md(reset.label_with_status()),
                    str(reset.quantity),
                    escape_md(humanize(reset.kind)),
                    format_window(reset.grant_at, reset.grant_at_latest, display_tz) if reset.grant_at else "",
                    format_window(reset.expires_at, reset.expires_at_latest, display_tz),
                    format_window(reset.expires_at, reset.expires_at_latest, timezone.utc),
                    format_duration_window(reset, now),
                    escape_md(humanize(reset.confidence)),
                    escape_md(reset.basis),
                    markdown_source(reset.source),
                ]
            )
            + " |"
        )
    notes = [f"- **{escape_md(reset.label)}:** {escape_md(reset.note)}" for reset in resets if reset.note]
    if notes:
        lines.extend(["", "## Notes", "", *notes])
    return "\n".join(lines)


def render_json(
    resets: list[ResetCredit],
    now: datetime,
    display_tz: tzinfo,
    expiry_days: float,
    messages: list[str] | None = None,
) -> str:
    payload = {
        "timezone": timezone_label(display_tz),
        "now": now.isoformat(),
        "default_expiry_days": expiry_days,
        "messages": messages or [],
        "resets": [
            {
                "label": reset.label,
                "quantity": reset.quantity,
                "kind": reset.kind,
                "confidence": reset.confidence,
                "account_status": reset.account_status,
                "grant_at": reset.grant_at.isoformat() if reset.grant_at else None,
                "grant_at_latest": reset.grant_at_latest.isoformat() if reset.grant_at_latest else None,
                "expires_at": reset.expires_at.isoformat(),
                "expires_at_latest": reset.expires_at_latest.isoformat() if reset.expires_at_latest else None,
                "expires_at_local": reset.expires_at.astimezone(display_tz).isoformat(),
                "expires_at_latest_local": (
                    reset.expires_at_latest.astimezone(display_tz).isoformat() if reset.expires_at_latest else None
                ),
                "remaining_seconds": int((reset.expires_at - now).total_seconds()),
                "remaining_seconds_latest": int((window_latest(reset) - now).total_seconds()),
                "status": status_for(reset, now),
                "basis": reset.basis,
                "source": reset.source,
                "note": reset.note,
            }
            for reset in resets
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def line(parts: list[str]) -> str:
        return "| " + " | ".join(part.ljust(widths[index]) for index, part in enumerate(parts)) + " |"

    divider = "| " + " | ".join("-" * width for width in widths) + " |"
    return "\n".join([line(headers), divider, *[line(row) for row in rows]])


def status_for(reset: ResetCredit, now: datetime) -> str:
    latest_expiry = window_latest(reset)
    remaining = reset.expires_at - now
    if latest_expiry < now:
        return "expired"
    if reset.expires_at < now <= latest_expiry:
        return "window"
    if remaining <= timedelta(days=1):
        return "today"
    if remaining <= timedelta(days=3):
        return "critical"
    if remaining <= timedelta(days=7):
        return "soon"
    if remaining <= timedelta(days=14):
        return "watch"
    return "ok"


def is_bankable(reset: ResetCredit) -> bool:
    return reset.kind in {"banked", "likely_banked", "launch_banked", "referral_banked"}


def window_latest(reset: ResetCredit) -> datetime:
    return reset.expires_at_latest or reset.expires_at


def format_window(earliest: datetime | None, latest: datetime | None, tz: tzinfo) -> str:
    if earliest is None:
        return ""
    if latest is None:
        return format_dt(earliest, tz)
    return f"{format_dt(earliest, tz)} -> {format_dt(latest, tz)}"


def format_duration_window(reset: ResetCredit, now: datetime) -> str:
    earliest = format_duration(reset.expires_at - now)
    if reset.expires_at_latest is None:
        return earliest
    latest = format_duration(reset.expires_at_latest - now)
    return f"{earliest} -> {latest}"


def format_duration(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    prefix = ""
    suffix = ""
    if total_seconds < 0:
        prefix = "expired "
        suffix = " ago"
        total_seconds = abs(total_seconds)
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return prefix + " ".join(parts) + suffix


def format_dt(value: datetime | None, tz: tzinfo) -> str:
    if value is None:
        return ""
    local = value.astimezone(tz)
    offset = local.strftime("%z")
    pretty_offset = f"{offset[:3]}:{offset[3:]}" if offset else "+00:00"
    name = local.tzname() or "UTC"
    return f"{local:%Y-%m-%d %H:%M:%S} {name} (UTC{pretty_offset})"


def timezone_label(tz: tzinfo) -> str:
    if hasattr(tz, "key"):
        return str(getattr(tz, "key"))
    return tz.tzname(None) or str(tz)


def short_source(source: str) -> str:
    if not source:
        return ""
    match = STATUS_RE.search(source)
    if match:
        handle = match.group(1)
        status_id = match.group(2) or match.group(3)
        if handle:
            return f"x.com/{handle}/status/{status_id}"
        return f"x.com/status/{status_id}"
    return source


def markdown_source(source: str) -> str:
    if not source:
        return ""
    label = escape_md(short_source(source))
    if source.startswith(("http://", "https://")):
        return f"[{label}]({source})"
    return label


def escape_md(value: str) -> str:
    return value.replace("|", "\\|")


def humanize(value: str) -> str:
    normalized = value.replace("_", " ").strip()
    if not normalized:
        return ""
    return normalized[:1].upper() + normalized[1:]


def format_days(value: float) -> str:
    return f"{int(value)} days" if value.is_integer() else f"{value:g} days"


def plural(quantity: int) -> str:
    return "" if quantity == 1 else "s"


if __name__ == "__main__":
    raise SystemExit(main())
