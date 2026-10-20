"""kicad-skew command line."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__, board_nets
from .lengths import measure
from .rules import evaluate, pair_nets


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="kicad-skew", description="Check length matching on KiCad's own routed lengths "
                                 "(tracks + via barrels from the stack-up), against rules in a JSON file.")
    ap.add_argument("board", help=".kicad_pcb file")
    ap.add_argument("rules", help="rules JSON (see examples/ and the README)")
    ap.add_argument("--kicad-cli", help="path to kicad-cli (default: KICAD_CLI, PATH, usual install locations)")
    ap.add_argument("--layers", action="store_true", help="also report pairs whose legs run on different layers (needs pcbnew)")
    ap.add_argument("--layer-threshold", type=float, default=1.0, help="mm of unshared copper before a pair is reported (default 1.0)")
    ap.add_argument("--all", action="store_true", help="print every relation, not only failures and the worst per rule")
    ap.add_argument("--json", metavar="FILE", help="write lengths and relations as JSON")
    ap.add_argument("--map", metavar="PNG", help="draw the measured nets on the board, coloured by their worst relation (needs pcbnew and Pillow)")
    ap.add_argument("--map-full", action="store_true", help="draw the whole board instead of zooming to the measured nets")
    ap.add_argument("--version", action="version", version=f"kicad-skew {__version__}")
    a = ap.parse_args(argv)
    cfg = json.load(open(a.rules))
    try:
        L = measure(a.board, cfg["measure"], cfg.get("exclude"), a.kicad_cli)
    except (FileNotFoundError, RuntimeError) as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 2
    rels = evaluate(cfg, L, board_nets(a.board))
    print(f"measured {len(L)} nets (KiCad lengths: tracks + via barrels between the layers used)")
    worst: dict[str, object] = {}
    for r in rels:
        if r.value is not None and (r.rule not in worst or r.margin > worst[r.rule].margin):
            worst[r.rule] = r
    for name, r in worst.items():
        print(f"  {name:20s} worst {r.what}: {r.value:+.3f} mm ({100 * r.margin:.0f} % of {r.limit:.3f})")
    fails = [r for r in rels if not r.ok]
    for r in (rels if a.all else fails):
        tag = "ok  " if r.ok else ("MISS" if r.value is None else "FAIL")
        val = "missing " + ", ".join(r.missing) if r.value is None else f"{r.value:+.3f} mm (limit {r.limit:.3f})"
        print(f"{tag} [{r.rule}] {r.what}: {val}")
    split = []
    layers_skipped = None           # why --layers could not run; the summary must not read as "0 pairs split"
    if a.layers:
        try:
            from .layers import split_pairs
            split = split_pairs(a.board, pair_nets(cfg, board_nets(a.board)), a.layer_threshold)
        except ImportError as e:
            layers_skipped = "needs KiCad's pcbnew module, run with KiCad's Python"
            print(f"layer check skipped: {layers_skipped} ({e})")
        for p, n, d, lp, ln in split:
            fmt = lambda m: " ".join(f"{k}:{v:.1f}" for k, v in sorted(m.items()))
            print(f"SPLIT {p} / {n}: {d:.1f} mm on different layers  ({fmt(lp)} | {fmt(ln)})")
    if a.map:
        try:
            _map(a, L, rels, split)
            print(f"map: {a.map}")
        except ImportError as e:
            print(f"map skipped: {e}")
    status = "FAIL" if fails or split else "PASS"
    summary = f"{status}: {len(fails)} of {len(rels)} relations out of tolerance"
    if layers_skipped:
        summary += f"; layer check skipped ({layers_skipped})"
    elif a.layers:
        summary += f"; {len(split)} pairs split across layers"
    print(summary)
    if a.json:
        layer_check = "skipped: " + layers_skipped if layers_skipped else "ran" if a.layers else "not requested"
        json.dump({"lengths": L, "relations": [dict(r.__dict__, ok=r.ok) for r in rels], "layer_check": layer_check,
                   "split_pairs": [{"p": p, "n": n, "unshared_mm": d, "p_layers": lp, "n_layers": ln} for p, n, d, lp, ln in split]},
                  open(a.json, "w"), indent=1)
    return 1 if fails or split else 0


def _map(a, L, rels, split):
    import pcbnew
    from .render import AMBER, BLUE, GREEN, RED, draw, span
    worst: dict[str, float] = {}
    for r in rels:
        m = 9.9 if r.value is None else r.margin
        for n in r.nets:
            worst[n] = max(worst.get(n, 0.0), m)
    split_nets = {x for p, n, *_ in split for x in (p, n)}
    col = lambda n: BLUE if n in split_nets else (GREEN if worst.get(n, 0) < 0.5 else AMBER if worst.get(n, 0) <= 1.0 else RED)
    b = pcbnew.LoadBoard(a.board)
    lines = [((t.GetStart().x / 1e6, t.GetStart().y / 1e6), (t.GetEnd().x / 1e6, t.GetEnd().y / 1e6), t.GetWidth() / 1e6, col(t.GetNetname()))
             for t in b.GetTracks() if t.Type() != pcbnew.PCB_VIA_T and t.GetNetname() in L]
    legend = [(GREEN, "under half the limit"), (AMBER, "within the limit"), (RED, "over the limit")] + ([(BLUE, "legs on different layers")] if split_nets else [])
    draw(b, a.map, lines, legend=legend, title=f"kicad-skew: {len(L)} nets", crop=None if a.map_full else span(b, set(L)))


if __name__ == "__main__":
    raise SystemExit(main())
