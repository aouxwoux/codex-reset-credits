# Launch Notes

Use these snippets when publishing the repo.

## GitHub Description

Codex Reset Credits: a drop-in Codex skill that shows exact expiry times for banked reset credits, with privacy-safe local auth and public-event fallback inference.

## README Tagline

Know exactly when your Codex reset credits expire.

## X Post

I built a tiny Codex skill for everyone hoarding reset credits:

- shows exact granted/expires timestamps when local Codex auth can read them
- prints only sanitized fields, no tokens/raw payloads
- falls back to Tibo/OpenAI reset-event inference when exact account data is unavailable
- outputs Markdown/JSON for calendar/app ideas

Repo: <link>

## Short X Reply

If your Codex UI says you have reset credits but not when they expire, this shows the exact expiry rows locally.

No token printing, no raw payloads, read-only fetch, Markdown/JSON output.

Repo: <link>

## Demo Command

```bash
python track-codex-resets/scripts/fetch_account_resets.py --timezone Asia/Kolkata --format markdown
```

## Demo Output Shape

```text
Available reset credits: 2

Granted                  Expires                  Status
2026-06-12 01:33 UTC     2026-07-12 01:33 UTC     available
2026-06-27 00:39 UTC     2026-07-27 00:39 UTC     available
```
