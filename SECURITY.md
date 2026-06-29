# Security

This project handles local Codex auth carefully because `~/.codex/auth.json` contains credentials.

## Safe behavior

- Read `auth.json` only in-process.
- Use the access token only for the read-only reset-credit GET request.
- Print only sanitized reset-credit fields.
- Ignore local account snapshots by default.

## Do not share

Never post or commit:

- `auth.json`
- access tokens
- refresh tokens
- account IDs
- cookies
- raw endpoint payloads
- credit IDs or profile IDs
- request headers with values

## Reporting issues

Open a GitHub issue for bugs that do not expose secrets. If a report includes private credentials or account data, rotate the affected credentials before sharing any details publicly.
