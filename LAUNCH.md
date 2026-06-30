# Launch Notes

Use these snippets when publishing the repo.

## GitHub Description

Codex Reset Credits: a drop-in Codex skill that shows exact expiry times for banked reset credits, with privacy-safe local auth and public-event fallback inference.

## README Tagline

Know exactly when your Codex reset credits expire.

## Reference X Post

Made an unofficial Codex skill for reset credits.

It shows when banked resets expire, uses local Codex auth only for sanitized expiry rows, and falls back to Tibo/OpenAI reset-event inference when exact data isn't available.

MIT: https://github.com/aouxwoux/codex-reset-credits

## Longer X Post

I built an unofficial Codex skill for tracking reset credits:

- exact expiry rows when local Codex auth can read them
- no token printing, raw payloads, IDs, or cookies
- Tibo/OpenAI event inference as a fallback
- Markdown/JSON output
- skill-only OSS release

https://github.com/aouxwoux/codex-reset-credits

## Short X Reply

If your Codex UI says you have reset credits but not when they expire, this shows the exact expiry rows locally.

No token printing, no raw payloads, read-only fetch, Markdown/JSON output.

https://github.com/aouxwoux/codex-reset-credits

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
