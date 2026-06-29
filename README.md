# Codex Reset Credits

Unofficial Codex skill and CLI helper for seeing when banked Codex usage resets expire.

Codex reset credits can be easy to miss and harder to time. This project gives you a drop-in Codex skill plus safe local scripts that show exact account-backed expiry times when available, and fall back to public Tibo/OpenAI reset-event inference when exact account data is unavailable.

## Why people care

Tibo and the Codex team sometimes grant reset credits with a 30-day expiry. The practical problem is simple: if you have multiple resets, the UI may show the count without clearly showing each expiration. This tool turns that into a clean ledger.

Example output:

```text
Available reset credits: 2

Granted                  Expires                  Status
2026-06-12 01:33 UTC     2026-07-12 01:33 UTC     available
2026-06-27 00:39 UTC     2026-07-27 00:39 UTC     available
```

## Install the skill

Clone the repo, then run:

```bash
python tools/install_skill.py
```

This copies `track-codex-resets/` into your local Codex skills directory:

```text
~/.codex/skills/track-codex-resets
```

Then ask Codex:

```text
Use $track-codex-resets to show when my Codex reset credits expire.
```

Use `--target` if your Codex skills live somewhere else:

```bash
python tools/install_skill.py --target /path/to/skills
```

## Run directly

Exact account-backed expiry rows:

```bash
python track-codex-resets/scripts/fetch_account_resets.py --timezone Asia/Kolkata --format markdown
```

Sanitized local ledger output:

```bash
python track-codex-resets/scripts/fetch_account_resets.py --format ledger > account-resets.local.json
python track-codex-resets/scripts/reset_expiry.py --input account-resets.local.json --format markdown
```

Public-event inference when exact account fetch is unavailable:

```bash
python track-codex-resets/scripts/reset_expiry.py --bank-count 3 --timezone Asia/Kolkata
```

One-off Tibo/X status URL:

```bash
python track-codex-resets/scripts/reset_expiry.py --timezone Asia/Kolkata https://x.com/thsottiaux/status/2070653282440405046
```

## What it does

- Fetches exact personal reset-credit rows from the account reset-credit endpoint when local Codex auth is available.
- Prints only sanitized fields: count, status, title, `granted_at`, `expires_at`, and safe metadata.
- Computes expiry tables from `expires_at`, `grant_at + 30 days`, X/Twitter status IDs, or a known public reset-event catalog.
- Displays local and UTC expiry times.
- Emits terminal, Markdown, JSON, or sanitized ledger output.
- Keeps provenance visible so exact account data never looks like public-event estimation.

## Privacy model

`~/.codex/auth.json` contains credentials. The exact fetcher reads it only in-process to authenticate a read-only GET request.

The tool must not print, save, or commit:

- access tokens
- refresh tokens
- account IDs
- cookies
- request headers with values
- raw endpoint payloads
- credit IDs or profile IDs

Generated local snapshots such as `account-resets.local.json` are ignored by git.

## Output modes

```text
--format terminal   compact terminal table
--format markdown   shareable Markdown table
--format json       structured renderer output
--format ledger     sanitized input file for reset_expiry.py
```

## Public-event inference

If exact account data is unavailable, `--bank-count N` maps your visible reset-bank count to the latest active likely bankable events in `track-codex-resets/assets/known-reset-events.json`.

This is useful, but it is not account truth. Referral-earned resets and staged rollouts need account-specific grant timestamps.

## Validate

```bash
python tools/validate_repo.py
python /path/to/skill-creator/scripts/quick_validate.py track-codex-resets
```

Adjust the final validator path for your machine.

## Roadmap

- Calendar export with reminders before expiry.
- Tiny desktop/menu bar view.
- Codex app GUI panel.
- Community-maintained reset-event catalog.

## Disclaimer

This is an unofficial community project, not an OpenAI product. The account endpoint is used read-only and may change. If Codex exposes official per-credit expiry rows, this project should prefer that supported source.
