# xCoin tetromino identicon

Deterministic 12x12 tetromino identicon for xCoin witness-v3 addresses (V1 spec in `SPEC.md`).

- `worker.js` — Cloudflare Worker: `/api/svg?a=ADDRESS[&cell=64]`, `/api/json?a=ADDRESS`, `/` interactive page
- `xcoin_identicon.py` — reference Python implementation (same output)
- `test.mjs` — verifies the JS port against `sample_layout.json`

Deploy: `npx wrangler deploy`
