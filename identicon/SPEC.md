# xCoin Deterministic Tetromino Identicon Package

This package contains a reusable deterministic identicon generator for xCoin addresses.

## What it does

Given a public xCoin witness-v3 address, it generates a **12x12 tetromino identicon** with these rules:

- The board is **12 x 12**
- It is completely filled by **36 tetrominoes**
- Each tetromino family has a **fixed color**
- Two tetrominoes of the **same family may not share an orthogonal edge**
- They **may** touch diagonally
- The same address always produces the same layout

## Included files

- `xcoin_identicon.py` — reusable module
- `wallet_cli_integration_example.py` — example integration points for `wallet_cli.py`
- `README.md` — package documentation
- `INTEGRATION.md` — step-by-step integration notes
- `sample_identicon.png` — rendered sample output
- `sample_layout.json` — sample layout data for the sample address

## V1 seed formula

The identicon seed is:

```text
SHA256("XCOIN_IDENTICON_V1" || hrp || witver || witness_program)
```

For the included sample address:

```text
txa1r4d9harwwtm39jp40r2e4wz84h2ehzt43fskh0wnye4x70e6f9hsskqvqwe
```

the seed is:

```text
8b2867268c8debd953c905bb346aff3fb65831a5c3c4324367fbc150f79734b1
```

## Fixed family -> color mapping

- I = #ff1400
- O = #ff8a00
- T = #fff200
- L = #00e834
- J = #113cff
- S = #a61fff
- Z = #42107a

## Quick usage

### Generate a PNG

```bash
python xcoin_identicon.py "txa1r4d9harwwtm39jp40r2e4wz84h2ehzt43fskh0wnye4x70e6f9hsskqvqwe" --png sample.png
```

### Generate an SVG

```bash
python xcoin_identicon.py "txa1r4d9harwwtm39jp40r2e4wz84h2ehzt43fskh0wnye4x70e6f9hsskqvqwe" --svg sample.svg
```

### Generate layout JSON

```bash
python xcoin_identicon.py "txa1r4d9harwwtm39jp40r2e4wz84h2ehzt43fskh0wnye4x70e6f9hsskqvqwe" --json sample.json
```

## Rendering style

This package renders the identicon:

- with **no white border**
- with **no black outlines**
- with **vibrant colors**
- as a flat, edge-to-edge mosaic

If you need the wallet to reproduce this exact look, freeze these settings in production.
