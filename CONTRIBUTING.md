# Contributing

Thanks for helping make reset expiry tracking less mysterious.

## Local checks

```bash
python tools/validate_repo.py
```

This runs the unit tests, sample fixture commands, Python compilation, and repository structure checks.

If you have the Codex skill validator available:

```bash
python /path/to/skill-creator/scripts/quick_validate.py track-codex-resets
```

## Catalog updates

When updating `track-codex-resets/assets/known-reset-events.json`:

- Prefer source URLs with stable status IDs.
- Mark only saved reset credits as `bankable: true`.
- Keep immediate usage resets as `bankable: false`.
- Use `grant_delay_hours` when rollout timing is uncertain.
- Update `updated_at`.

## Privacy rules

Do not add tests, fixtures, screenshots, logs, or docs containing real tokens, account IDs, credit IDs, profile IDs, cookies, or raw endpoint payloads.
