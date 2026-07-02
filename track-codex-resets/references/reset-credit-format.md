# Reset Credit Format

Use this reference when changing the reset ledger schema, adding exporters, or building a UI around this skill.

## Source Priority

Prefer reset evidence in this order:

1. Exact account rows fetched by `scripts/fetch_account_resets.py`.
2. `expires_at` from Codex, a trusted collector, or a user-provided exact timestamp.
3. `grant_at` from a trusted source.
4. X/Twitter status URL. The script derives `grant_at` from the status ID timestamp and treats it as an announcement-based estimate.
5. Known public reset event catalog plus the user's visible reset-bank count.
6. Relative dates. Resolve them to exact timestamps before adding them to a ledger.

## JSON Schema

```json
{
  "timezone": "Asia/Kolkata",
  "expiry_days": 30,
  "efficiency_buffer_hours": 6,
  "resets": [
    {
      "label": "Tibo reset",
      "source": "https://x.com/thsottiaux/status/2070653282440405046",
      "quantity": 1,
      "note": "Estimated from announcement time."
    },
    {
      "label": "Codex UI reset",
      "grant_at": "2026-06-26T23:39:48Z",
      "expires_at": "2026-07-26T23:39:48Z",
      "quantity": 1
    }
  ]
}
```

Fields:

- `timezone`: Default display timezone for the ledger. CLI `--timezone` overrides it.
- `expiry_days`: Default expiry window. CLI `--expiry-days` overrides it.
- `efficiency_buffer_hours`: Safety buffer used for reset timing advice. CLI `--efficiency-buffer-hours` overrides it.
- `label`: Human-readable reset name.
- `source`, `url`, or `status_url`: Evidence link or collector source.
- `grant_at`: Exact grant timestamp. Naive values are interpreted in the display timezone.
- `grant_at_latest`: Latest plausible grant timestamp when rollout timing is uncertain.
- `grant_delay_hours`: Convenience field for deriving `grant_at_latest` from `grant_at`.
- `expires_at`: Exact expiry timestamp. Prefer this when known.
- `expires_at_latest`: Latest plausible expiry timestamp when the exact grant time is unknown.
- `quantity` or `count`: Number of reset credits represented by the entry.
- `kind`: Reset classification, such as `launch_banked`, `banked`, `likely_banked`, `immediate`, or `policy`.
- `confidence`: Human-readable confidence label.
- `credit_status`: Account endpoint status, such as `available`.
- `bankable`: Whether the event should be used by `--bank-count` inference.
- `note`: Short provenance or uncertainty note.

## Exact Account Fetch

Use this first when the user wants their own reset expiry details:

```bash
python scripts/codex_resets.py account --timezone Asia/Kolkata
```

The script reads `~/.codex/auth.json` in-process, sends only a GET request to `https://chatgpt.com/backend-api/wham/rate-limit-reset-credits`, and prints only sanitized fields:

- available reset-credit count
- `status`
- `reset_type`
- `title`
- `granted_at`
- `expires_at`
- `used_at` or `redeemed_at`, if returned

Never print or persist raw endpoint payloads, credit IDs, profile IDs, account IDs, access tokens, refresh tokens, cookies, or request headers with values.

To save a sanitized local ledger:

```bash
python scripts/codex_resets.py account --timezone Asia/Kolkata --format ledger > account-resets.local.json
python scripts/codex_resets.py render --input account-resets.local.json --format markdown
```

## Known Event Catalog

`assets/known-reset-events.json` is the machine-readable public-event catalog. Keep it conservative:

- Mark only saved reset credits as `bankable: true`.
- Keep immediate hard resets as `bankable: false`, even when they are useful history.
- Use `grant_delay_hours` when a public post says a reset will appear later, such as "in the next few hours" or "give us 24 hours."
- Prefer exact source URLs and status IDs over copied text.
- Update `updated_at` whenever adding newly discovered public events.

Use this command when the user says they can see a reset-bank count but not individual expiries:

```bash
python scripts/codex_resets.py estimate --bank-count 3 --timezone Asia/Kolkata
```

This is an inference, not account truth. If Codex later exposes per-credit expiry, replace inferred events with exact `expires_at` values.

Referral-earned resets are per-account. Do not infer their expiry from Tibo's public reset posts unless the user also provides the referral grant timestamp or an exact Codex UI expiry.

## Local Auth Files

`auth.json` is credential-bearing. Inspect only key names or redacted structure. Do not print, copy, commit, or transmit token values. In current Codex auth layouts it stores auth mode, tokens, account id, and refresh time; use it only to authenticate the read-only account reset-credit endpoint.

## Timezone Rules

Display at least one local timestamp and one UTC timestamp for each expiry. Use IANA names such as `Asia/Kolkata` when Python `zoneinfo` has timezone data installed; otherwise pass fixed offsets such as `+05:30`.

Do not round expiry instants to local calendar days unless Codex documents that behavior. The default rule is exact duration math: `grant_at + 30 * 24 hours`.

## Exporter Guidance

Calendar export should be built from the JSON renderer instead of reparsing terminal output. Use `expires_at` as the event end/alert anchor, add reminders at configurable windows such as 7 days and 24 hours, and include the reset source and basis in the event description.

The JSON renderer includes an `efficiency_recommendation` object with `recommended_reset_at`, `expiry_anchor_at`, `buffer_seconds`, `action`, and the selected credit label. Use this object when building reminder or scheduling tools.

GUI extensions should consume the JSON renderer, sort by `expires_at`, surface the next expiry first, show the efficiency recommendation, and preserve the `basis` field so users can distinguish exact app data from announcement-based estimates.
