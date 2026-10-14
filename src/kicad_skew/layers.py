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


def split_pairs(board_path: str, pairs: list[tuple[str, str]], threshold: float = 1.0,
                skip_layers: tuple[str, ...] = ("F.Cu", "B.Cu")) -> list[tuple[str, str, float, dict, dict]]:
    """[(p, n, mm not shared, p per layer, n per layer)] for pairs whose legs differ by more than ``threshold`` mm.
    Outer layers are skipped by default: that is where breakout stubs live."""
    pl = per_layer(board_path, {x for p in pairs for x in p}, skip_layers)
    res = []
    for p, n in pairs:
        lays = set(pl.get(p, {})) | set(pl.get(n, {}))
        diff = sum(abs(pl.get(p, {}).get(L, 0.0) - pl.get(n, {}).get(L, 0.0)) for L in lays) / 2
        if diff > threshold:
            res.append((p, n, diff, dict(pl.get(p, {})), dict(pl.get(n, {}))))
    return res
