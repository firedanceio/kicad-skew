"""Routed net lengths exactly as KiCad computes them, read back from kicad-cli.

KiCad's length (used by its length-tuning tools and its DRC length rules) counts tracks, arcs and, for each via, the
barrel actually travelled between the two copper layers the net uses, from the board's stack-up heights; pad-to-die
lengths set on pads are included too. Re-implementing that is error-prone (a flat "0.5 mm per via" model was off by
more than a millimetre per via on an 8-layer board), so this asks KiCad itself: the board is copied to a scratch
directory with a design-rule file that gives every selected net a 0.001 mm maximum length, kicad-cli runs DRC, and
each net's "actual" length is parsed from the length violations.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import shutil
import subprocess
import tempfile

CLI_CANDIDATES = [
    "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
    "/usr/bin/kicad-cli",
    "/usr/local/bin/kicad-cli",
    r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
    r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
    r"C:\Program Files\KiCad\8.0\bin\kicad-cli.exe",
]


def find_cli(explicit: str | None = None) -> str:
    for c in [explicit, os.environ.get("KICAD_CLI"), shutil.which("kicad-cli"), *CLI_CANDIDATES]:
        if c and os.path.exists(c):
            return c
    raise FileNotFoundError("kicad-cli not found: pass --kicad-cli or set KICAD_CLI")


def _rule(patterns: list[str]) -> str:
    cond = " || ".join(f"A.NetName == '{p}'" for p in patterns)
    return f'(version 1)\n(rule "kicad-skew measure"\n  (condition "{cond}")\n  (constraint length (max 0.001mm)))\n'


def measure(board: str, patterns: list[str], exclude: list[str] | None = None, cli: str | None = None) -> dict[str, float]:
    """{net: routed length in mm} for every net matching one of ``patterns`` (KiCad wildcards: * and ?) that has any
    routed copper. ``exclude`` drops nets by fnmatch pattern."""
    cli = find_cli(cli)
    with tempfile.TemporaryDirectory() as d:
        shutil.copy(board, os.path.join(d, "k.kicad_pcb"))
        pro = os.path.splitext(board)[0] + ".kicad_pro"
        if os.path.exists(pro):
            shutil.copy(pro, os.path.join(d, "k.kicad_pro"))
        else:
            open(os.path.join(d, "k.kicad_pro"), "w").write("{}")
        open(os.path.join(d, "k.kicad_dru"), "w").write(_rule(patterns))
        out = os.path.join(d, "drc.json")
        r = subprocess.run([cli, "pcb", "drc", "--format", "json", "--severity-all", "-o", out, os.path.join(d, "k.kicad_pcb")],
                           capture_output=True, text=True)
        if not os.path.exists(out):
            raise RuntimeError(f"kicad-cli DRC failed: {r.stderr.strip() or r.stdout.strip()}")
        data = json.load(open(out))
    lengths: dict[str, float] = {}
    for v in data.get("violations", []):
        if v.get("type") != "length_out_of_range":
            continue
        m = re.search(r"actual ([\d.]+) ?mm", v.get("description", ""))
        n = re.search(r"\[([^\]]+)\]", " ".join(i.get("description", "") for i in v.get("items", [])))
        if m and n:
            lengths[n.group(1)] = float(m.group(1))
    if exclude:
        lengths = {k: v for k, v in lengths.items() if not any(fnmatch.fnmatchcase(k, e) for e in exclude)}
    return lengths
