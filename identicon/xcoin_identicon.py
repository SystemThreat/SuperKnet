"""
xCoin deterministic tetromino identicon module (V1)

Rules:
- 12x12 board
- 36 tetrominoes
- fixed family->color mapping
- same family may not share an orthogonal edge
- diagonal contact is allowed
- deterministic from public address only

Designed to integrate with wallet_cli.py or other xCoin frontends.
"""

from __future__ import annotations
import hashlib
import json
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except Exception:
    Image = None
    ImageDraw = None


N = 12
FAMILY_COLORS = {'I': '#ff1400', 'O': '#ff8a00', 'T': '#fff200', 'L': '#00e834', 'J': '#113cff', 'S': '#a61fff', 'Z': '#42107a'}
_B32 = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
_BECH32M_CONST = 0x2bc830a3

SHAPES = {'I': [[(0, 0), (1, 0), (2, 0), (3, 0)], [(0, 0), (0, 1), (0, 2), (0, 3)]], 'O': [[(0, 0), (1, 0), (0, 1), (1, 1)]], 'T': [[(0, 0), (1, 0), (2, 0), (1, 1)], [(0, 0), (0, 1), (0, 2), (1, 1)], [(1, 0), (0, 1), (1, 1), (2, 1)], [(1, 0), (0, 1), (1, 1), (1, 2)]], 'L': [[(0, 0), (0, 1), (0, 2), (1, 2)], [(0, 0), (1, 0), (2, 0), (0, 1)], [(0, 0), (1, 0), (1, 1), (1, 2)], [(2, 0), (0, 1), (1, 1), (2, 1)]], 'J': [[(1, 0), (1, 1), (0, 2), (1, 2)], [(0, 0), (0, 1), (1, 1), (2, 1)], [(0, 0), (1, 0), (0, 1), (0, 2)], [(0, 0), (1, 0), (2, 0), (2, 1)]], 'S': [[(1, 0), (2, 0), (0, 1), (1, 1)], [(0, 0), (0, 1), (1, 1), (1, 2)]], 'Z': [[(0, 0), (1, 0), (1, 1), (2, 1)], [(1, 0), (0, 1), (1, 1), (0, 2)]]}


def _polymod(values):
    gen = (0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3)
    chk = 1
    for v in values:
        top = chk >> 25
        chk = ((chk & 0x1ffffff) << 5) ^ v
        for i in range(5):
            if (top >> i) & 1:
                chk ^= gen[i]
    return chk


def _hrp_expand(hrp):
    return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]


def _convertbits(data, frombits, tobits, pad):
    acc = bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for v in data:
        if v < 0 or (v >> frombits):
            return None
        acc = ((acc << frombits) | v) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret


def bech32m_decode(addr: str):
    addr = addr.strip().lower()
    pos = addr.rfind("1")
    if pos < 1:
        raise ValueError("malformed address")
    hrp, rest = addr[:pos], addr[pos+1:]
    data = [_B32.index(c) for c in rest]
    if _polymod(_hrp_expand(hrp) + data) != _BECH32M_CONST:
        raise ValueError("bad bech32m checksum")
    data_no_checksum = data[:-6]
    witver = data_no_checksum[0]
    program = bytes(_convertbits(data_no_checksum[1:], 5, 8, False))
    return hrp, witver, program


def identicon_seed_from_address(addr: str):
    hrp, witver, program = bech32m_decode(addr)
    if witver != 3 or len(program) != 32:
        raise ValueError("expected witness-v3 xCoin address with 32-byte program")
    return {
        "hrp": hrp,
        "witver": witver,
        "program_hex": program.hex(),
        "seed": hashlib.sha256(
            b"XCOIN_IDENTICON_V1" + hrp.encode() + bytes([witver]) + program
        ).digest(),
    }


def build_placements(n: int = N):
    placements = []
    cell_to_placements = [[] for _ in range(n*n)]
    for family, orientations in SHAPES.items():
        for orientation, points in enumerate(orientations):
            maxx = max(x for x, y in points)
            maxy = max(y for x, y in points)
            for oy in range(n - maxy):
                for ox in range(n - maxx):
                    cells = tuple(sorted((oy+y)*n + (ox+x) for x, y in points))
                    p = {
                        "family": family,
                        "orientation": orientation,
                        "cells": cells,
                        "anchor": (ox, oy),
                    }
                    idx = len(placements)
                    placements.append(p)
                    for c in cells:
                        cell_to_placements[c].append(idx)
    for p in placements:
        edge_neighbors = set()
        for c in p["cells"]:
            x, y = c % n, c // n
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < n and 0 <= ny < n:
                    nc = ny*n + nx
                    if nc not in p["cells"]:
                        edge_neighbors.add(nc)
        p["edge_neighbors"] = tuple(sorted(edge_neighbors))
    return placements, cell_to_placements


def _hashed_order(seed: bytes, step: int, cands, placements):
    def key(pi):
        p = placements[pi]
        encoded = f'{p["family"]}|{p["orientation"]}|{",".join(map(str, p["cells"]))}'.encode()
        return hashlib.sha256(seed + step.to_bytes(2, "little") + encoded).digest()
    return sorted(cands, key=key)


def generate_layout(addr: str, n: int = N):
    parsed = identicon_seed_from_address(addr)
    seed = parsed["seed"]
    placements, cell_to_placements = build_placements(n)
    occ = [-1] * (n*n)
    placed = []

    adjacency = [[] for _ in range(n*n)]
    for c in range(n*n):
        x, y = c % n, c // n
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < n and 0 <= ny < n:
                adjacency[c].append(ny*n + nx)

    def legal(pi):
        p = placements[pi]
        for c in p["cells"]:
            if occ[c] != -1:
                return False
        fam = p["family"]
        for nc in p["edge_neighbors"]:
            other_id = occ[nc]
            if other_id != -1 and placed[other_id]["family"] == fam:
                return False
        return True

    def holes_ok():
        seen = set()
        for c in range(n*n):
            if occ[c] == -1 and c not in seen:
                stack = [c]
                seen.add(c)
                comp_size = 0
                while stack:
                    u = stack.pop()
                    comp_size += 1
                    for v in adjacency[u]:
                        if occ[v] == -1 and v not in seen:
                            seen.add(v)
                            stack.append(v)
                if comp_size % 4 != 0:
                    return False
        return True

    def choose_cell():
        best_cell = None
        best_cands = None
        for c in range(n*n):
            if occ[c] != -1:
                continue
            cands = [pi for pi in cell_to_placements[c] if legal(pi)]
            if not cands:
                return c, []
            if best_cands is None or len(cands) < len(best_cands):
                best_cell, best_cands = c, cands
                if len(best_cands) == 1:
                    break
        return best_cell, best_cands

    def solve(step=0):
        if step == (n*n)//4:
            return True
        _, cands = choose_cell()
        if not cands:
            return False
        for pi in _hashed_order(seed, step, cands, placements):
            p = placements[pi]
            piece_id = len(placed)
            for c in p["cells"]:
                occ[c] = piece_id
            placed.append(p)
            if holes_ok() and solve(step+1):
                return True
            placed.pop()
            for c in p["cells"]:
                occ[c] = -1
        return False

    if not solve():
        raise RuntimeError("No valid layout found")

    return {
        "address": addr,
        "hrp": parsed["hrp"],
        "witver": parsed["witver"],
        "program_hex": parsed["program_hex"],
        "seed_hex": parsed["seed"].hex(),
        "pieces": placed,
        "board_owner": occ,
    }


def render_png(layout, out_path: str | Path, n: int = N, cell: int = 64):
    if Image is None:
        raise RuntimeError("Pillow is required for PNG rendering: pip install pillow")
    out_path = Path(out_path)
    img = Image.new("RGB", (n*cell, n*cell), "white")
    draw = ImageDraw.Draw(img)
    occ = layout["board_owner"]
    pieces = layout["pieces"]
    for y in range(n):
        for x in range(n):
            pid = occ[y*n + x]
            fam = pieces[pid]["family"]
            color = FAMILY_COLORS[fam]
            x0 = x * cell
            y0 = y * cell
            x1 = x0 + cell - 1
            y1 = y0 + cell - 1
            draw.rectangle([x0, y0, x1, y1], fill=color)
    img.save(out_path)
    return out_path


def render_svg(layout, out_path: str | Path, n: int = N, cell: int = 64):
    out_path = Path(out_path)
    width = n * cell
    height = n * cell
    occ = layout["board_owner"]
    pieces = layout["pieces"]
    rects = []
    for y in range(n):
        for x in range(n):
            pid = occ[y*n + x]
            fam = pieces[pid]["family"]
            color = FAMILY_COLORS[fam]
            rects.append(
                f'<rect x="{x*cell}" y="{y*cell}" width="{cell}" height="{cell}" fill="{color}"/>'
            )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        + "".join(rects)
        + "</svg>"
    )
    out_path.write_text(svg)
    return out_path


def layout_to_json(layout, out_path: str | Path):
    out_path = Path(out_path)
    out_path.write_text(json.dumps(layout, indent=2))
    return out_path


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Generate a deterministic xCoin tetromino identicon")
    p.add_argument("address")
    p.add_argument("--png", help="write PNG to this path")
    p.add_argument("--svg", help="write SVG to this path")
    p.add_argument("--json", help="write layout JSON to this path")
    p.add_argument("--cell", type=int, default=64)
    args = p.parse_args()

    layout = generate_layout(args.address)
    print("seed:", layout["seed_hex"])
    if args.png:
        render_png(layout, args.png, cell=args.cell)
        print("png:", args.png)
    if args.svg:
        render_svg(layout, args.svg, cell=args.cell)
        print("svg:", args.svg)
    if args.json:
        layout_to_json(layout, args.json)
        print("json:", args.json)
