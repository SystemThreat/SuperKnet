# SuperKnet — the xCoin block explorer

[superknet.com](https://superknet.com) is the public block explorer for **xCoin (XCF)**, the post-quantum chain
(ML-DSA-65 / SLH-DSA witness v3 addresses, Keccak-based MetalDAG proof of work, 21,000,000 XCF cap).
It currently serves testnet A ("rehearsal", `txa1r…` addresses) and will serve mainnet (`xpa1r…`) once its genesis is mined.

This repository holds the two services behind the site:

| Directory | What it is | Runs on |
|---|---|---|
| [`explorer/`](explorer/) | The explorer itself — one Python file, no framework, no database | The New York node (`systemd`, behind a Cloudflare tunnel) |
| [`identicon/`](identicon/) | Deterministic tetromino identicons for xCoin addresses | Cloudflare Workers |

---

## 1. Explorer (`explorer/`)

### Design

`xcoin-explorer.py` is a self-contained HTTP server (Python 3.12 stdlib only — no pip dependencies).
It talks to a local `nexd` node over JSON-RPC, walks every block itself and maintains its **own UTXO set**
in memory. That is why balances, the rich list and every transaction fee are chain truth rather than
something the node was asked to estimate.

What it shows:

- **Blocks** and **transactions**, with the exact fee of every non-coinbase transaction
- **Addresses** — witness v3 (`OP_3 <32-byte Merkle root>`), the only spendable output type. Balance,
  unspent outputs, full history, and the address's identicon
- **Rich list** and **top miners**, plus the pool's live rigs (worker name, blocks, shares, hashrate, last seen)
- **Network panel** — `charter_hash`, `currency_id`, genesis, block subsidy at the tip (14 XCF in era 0)
- **Mempool**
- A chain selector by RPC port: rehearsal (19432, default) or mainnet (8332)

### Routes

| Path | Content |
|---|---|
| `/` | Overview: stats, latest blocks, top miners, active rigs |
| `/block/<height or hash>` | Block page |
| `/tx/<txid>` | Transaction page |
| `/address/<addr>` | Address page (identicon, balance, UTXOs, history) |
| `/richlist` | Richest addresses |
| `/mempool` | Pending transactions |
| `/search?q=` | Redirects to the block / tx / address that matches |
| `/api/stats` | JSON: tip height, supply, difficulty, etc. |
| `/api/network` | JSON: peers and network facts |
| `/api/charter` | JSON: `getcharter` from the node |
| `/api/block/<h>` | JSON block |
| `/robots.txt`, `/sitemap.xml` | For crawlers |

`/api/*` responses carry `Access-Control-Allow-Origin: *` so other xCoin sites can read them from the browser.

### Running locally

```bash
cd explorer
XCOIN_RPC_COOKIE=$HOME/.xcoin-rehearsal/node/testneta/.cookie \
XCOIN_CHAIN=rehearsal XCOIN_EXPLORER_PORT=3101 python3 xcoin-explorer.py
# open http://localhost:3101/
```

Configuration is entirely by environment variable:

| Variable | Default | Purpose |
|---|---|---|
| `XCOIN_CHAIN` | `rehearsal` | `rehearsal` or `mainnet`; picks the RPC port |
| `XCOIN_RPC_PORT` | by chain | 19432 rehearsal, 8332 mainnet |
| `XCOIN_RPC_HOST` | `127.0.0.1` | Node RPC host |
| `XCOIN_RPC_COOKIE` | — | Path to the node's `.cookie` (preferred — no password anywhere) |
| `XCOIN_RPC_USER` / `XCOIN_RPC_PASSWORD` | — | Fallback for local runs only |
| `XCOIN_EXPLORER_PORT` | `3101` | Listen port (3001, 3333, 9333, 9432 are refused) |
| `XCOIN_EXPLORER_BIND` | `127.0.0.1` | Bind interface |
| `XCOIN_EXPLORER_URL` | `http://localhost:<port>` | Canonical / OpenGraph base URL |
| `XCOIN_ADDRESS_HRP` | from node | Address prefix override |
| `XCOIN_MAX_SUPPLY` | `21000000` | Cap shown in the supply panel |
| `XCOIN_LEVY_BP` | `0` | Settlement levy in basis points (test chains only) |
| `XCOIN_ADDNODE` | — | Peer line suggested on the home page |
| `XCOIN_STATS_DIR` | `<here>/pool` | Directory where the pool writes miner stats |
| `XCOIN_WEB_POOL_STATS` | empty | Browser pool `/stats` URL |
| `XCOIN_EXPLORER_PUBLIC` | off | `1` enables analytics + forum embed (off so a local run cannot pollute live numbers) |

Tests:

```bash
cd explorer && python3 -m pytest tests/
```

`tests/test_v3_addresses.py` pins the founder's v2→v3 address conversion vector against the wallet CLI and
NerdMiner implementations; `tests/test_render.py` covers page rendering.

### Production deployment

On the node the explorer is installed at `/opt/xcoin/explorer/xcoin-explorer.py`, runs as user
`xcoin-explorer` under `xcoin-explorer.service`, binds `127.0.0.1:3101`, and is published by a Cloudflare
tunnel as `https://superknet.com`. RPC auth is the node's cookie file; no credentials live in this repo.

To deploy a change (over Tailscale, from a machine holding the VPS key):

```bash
scp -i ~/.ssh/id_ed25519_vps explorer/xcoin-explorer.py root@<node>:/root/xcoin-explorer.py
ssh -i ~/.ssh/id_ed25519_vps root@<node> \
  'install -o root -g xcoin-explorer -m 660 /root/xcoin-explorer.py /opt/xcoin/explorer/xcoin-explorer.py \
   && systemctl restart xcoin-explorer && sleep 3 && systemctl is-active xcoin-explorer'
```

If the service loops with `Set XCOIN_RPC_USER / XCOIN_RPC_PASSWORD`, an older build of the file was
installed — the production version reads `XCOIN_RPC_COOKIE`. Always deploy from this repository.

---

## 2. Identicons (`identicon/`)

Every address on the explorer is shown with a **deterministic tetromino identicon**: a 12×12 board tiled by
36 tetrominoes, coloured by piece family. The same address always renders the same picture, on any
implementation, so a user can recognise their address at a glance and spot a look-alike phishing address
instantly.

### How it looks on the explorer

- Miner and rich-list rows show a 44 px identicon with the worker name and truncated address stacked beside it
- Every other address link carries a small inline identicon
- Address pages show a 96 px identicon in the header
- Hovering any identicon pops up a 192 px enlargement (pure CSS + a few lines of JS; no extra requests)

Injection is centralised: the explorer's `_send` rewrites every `<a href="/address/…">` in HTML output, so
any future address link gets an icon automatically.

### The algorithm (V1 — frozen)

Full specification with worked example: [`identicon/SPEC.md`](identicon/SPEC.md).

1. **Seed** — decode the bech32m address to `(hrp, witver, program)`; require witness v3 with a 32-byte program.
   `seed = SHA256("XCOIN_IDENTICON_V1" || hrp || witver || program)`.
2. **Board** — 12×12 cells, filled by exactly 36 tetrominoes drawn from the 7 families (I, O, T, L, J, S, Z)
   in all orientations.
3. **Constraint** — two pieces of the same family may not share an orthogonal edge (diagonal contact is fine).
4. **Search** — deterministic backtracking. At each step pick the empty cell with the fewest legal placements,
   order the candidates by `SHA256(seed || step || placement)`, and prune any state that leaves a hole whose
   size is not a multiple of 4.
5. **Colours** — fixed per family:

   | I | O | T | L | J | S | Z |
   |---|---|---|---|---|---|---|
   | `#ff1400` | `#ff8a00` | `#fff200` | `#00e834` | `#113cff` | `#a61fff` | `#42107a` |

Anything that changes the output — seed formula, board size, colours, candidate ordering, hole pruning —
must become **V2**, never an in-place edit, so existing addresses keep their identicons forever.

### Implementations

| File | Language | Role |
|---|---|---|
| `worker.js` | JavaScript (Cloudflare Worker) | Production service; includes a compact synchronous SHA-256 and bech32m decoder |
| `xcoin_identicon.py` | Python 3 | Reference implementation; also renders PNG (Pillow) and SVG |
| `test.mjs` | Node | Asserts the JS port reproduces `sample_layout.json` piece-for-piece |

Both produce identical layouts. Generation takes ~20 ms.

### Service

Live at **https://xcoin-identicon.winnertakeall-17.workers.dev**

| Endpoint | Returns |
|---|---|
| `/` | Interactive page — paste an address, see its identicon |
| `/api/svg?a=<address>&cell=64` | `image/svg+xml`, `cell` = pixels per grid cell |
| `/api/json?a=<address>` | Layout JSON: seed, every piece (family, orientation, cells), board ownership |

Responses are `Cache-Control: immutable` (a layout can never change) and CORS-open. Invalid addresses
return HTTP 400 with a plain-text reason.

Embed anywhere:

```html
<img src="https://xcoin-identicon.winnertakeall-17.workers.dev/api/svg?a=txa1r4d9harwwtm39jp40r2e4wz84h2ehzt43fskh0wnye4x70e6f9hsskqvqwe">
```

### Deploying the worker

```bash
cd identicon
node test.mjs          # must print "pieces match true"
npx wrangler login     # first time only
npx wrangler deploy
```

To serve it from a superknet.com hostname, add a custom domain in the Cloudflare dashboard
(Workers → xcoin-identicon → Settings → Domains & Routes) and update `IDENTICON` in
`explorer/xcoin-explorer.py`.

### Python usage

```bash
pip install pillow
python3 xcoin_identicon.py txa1r4d9… --svg out.svg --png out.png --json out.json
```

---

## Related repositories

- [SystemThreat/xCoin](https://github.com/SystemThreat/xCoin) — node, pool, miner, wallet and browser extension

## License

See [LICENSE](LICENSE).
