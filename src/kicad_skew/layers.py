"""Pair legs on different layers.

Two legs can match in length and still not match in time: different layers have different propagation velocity (an
inner stripline is slower than an embedded or surface microstrip), and legs on different layers are not coupled at
all. This compares, per pair, how much copper each leg has on each layer and reports the length that is not shared.
Needs KiCad's pcbnew module.
"""
from __future__ import annotations

from collections import defaultdict


def per_layer(board_path: str, nets: set[str], skip_layers: tuple[str, ...] = ()) -> dict[str, dict[str, float]]:
    import pcbnew
    b = pcbnew.LoadBoard(board_path)
    out: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T or t.GetNetname() not in nets:
            continue
        if pcbnew.BOARD.GetStandardLayerName(t.GetLayer()) in skip_layers:   # outer layers by KiCad's own name
            continue
        L = b.GetLayerName(t.GetLayer())
        out[t.GetNetname()][L] += t.GetLength() / 1e6
    return out


def unshared(p: dict[str, float], n: dict[str, float]) -> float:
    """mm of the shorter leg that has no partner on the same layer. A length difference on a shared layer (one leg
    meandered more, or made up on a skipped outer layer) is not counted: that is a skew question, not a layer one."""
    shared = sum(min(p.get(L, 0.0), n.get(L, 0.0)) for L in set(p) | set(n))
    return max(0.0, min(sum(p.values()), sum(n.values())) - shared)


def split_pairs(board_path: str, pairs: list[tuple[str, str]], threshold: float = 1.0,
                skip_layers: tuple[str, ...] = ("F.Cu", "B.Cu")) -> list[tuple[str, str, float, dict, dict]]:
    """[(p, n, mm not shared, p per layer, n per layer)] for pairs with more than ``threshold`` mm of leg routed
    without its partner on the same layer. Outer layers are skipped by default: that is where breakout stubs live."""
    pl = per_layer(board_path, {x for p in pairs for x in p}, skip_layers)
    res = []
    for p, n in pairs:
        lp, ln = dict(pl.get(p, {})), dict(pl.get(n, {}))
        diff = unshared(lp, ln)
        if diff > threshold:
            res.append((p, n, diff, lp, ln))
    return res
