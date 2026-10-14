"""Length relations: what must match what, and by how much.

A rules file is JSON:

{
  "measure": ["DDR_*"],                    KiCad net patterns to measure (wildcards * and ?)
  "exclude": ["DDR_ZQ*"],                  optional, fnmatch patterns to drop
  "unit": "mm",                            "mm" (default) or "mil" for every "max" below
  "rules": [
    {"type": "pairs", "match": "DDR_.*_P$", "p": "_P", "n": "_N", "max": 0.3},
    {"type": "group", "label": "byte 0", "members": ["DDR_DQ[0-7]$", "DDR_DM0$"], "reference": ["DDR_DQS0_[PN]$"], "max": 15},
    {"type": "spread", "label": "CA", "members": ["DDR_A\\\\d+$"], "max": 12.7},
    {"type": "between", "label": "DQS0 vs CK", "a": ["DDR_DQS0_[PN]$"], "b": ["DDR_CK_[PN]$"], "max": 30}
  ]
}

pairs    every net matching ``match`` (a regex) against its partner (``p`` replaced by ``n``): |P - N|
group    every member net against the mean of the reference nets: member - mean(reference)
spread   max - min over the member nets
between  mean(a) - mean(b)
Member/reference/a/b entries are regexes searched in the full net name. A relation whose nets are not all measured is
reported as missing (an unrouted net is a failure, not a pass).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

MIL = 0.0254


@dataclass
class Relation:
    rule: str          # rule label
    kind: str          # pairs / group / spread / between
    what: str          # human-readable, e.g. "DDR_DQ3 vs mean(DDR_DQS0_P, DDR_DQS0_N)"
    value: float | None  # mm; None when a net is missing
    limit: float       # mm
    missing: list[str]
    nets: list[str] = field(default_factory=list)   # every net the relation involves

    @property
    def ok(self) -> bool:
        return self.value is not None and abs(self.value) <= self.limit

    @property
    def margin(self) -> float | None:
        return None if self.value is None else abs(self.value) / self.limit


def _sel(nets, pats):
    return sorted(n for n in nets if any(re.search(p, n) for p in pats))


def evaluate(cfg: dict, lengths: dict[str, float], all_nets: list[str] | None = None) -> list[Relation]:
    """``all_nets``: every net name on the board that the rules may refer to (so unrouted nets are seen as missing)."""
    scale = MIL if cfg.get("unit", "mm") == "mil" else 1.0
    universe = sorted(set(all_nets or []) | set(lengths))
    out: list[Relation] = []
    for k, r in enumerate(cfg.get("rules", [])):
        kind = r["type"]
        lim = float(r["max"]) * scale
        label = r.get("label", f"{kind} {k + 1}")
        mean = lambda ns: sum(lengths[n] for n in ns) / len(ns)
        if kind == "pairs":
            for pn in _sel(universe, [r["match"]]):
                nn = pn[: len(pn) - len(r["p"])] + r["n"] if pn.endswith(r["p"]) else pn.replace(r["p"], r["n"])
                miss = [x for x in (pn, nn) if x not in lengths]
                out.append(Relation(label, kind, f"{pn} vs {nn}", None if miss else lengths[nn] - lengths[pn], lim, miss, [pn, nn]))
        elif kind == "group":
            mem, ref = _sel(universe, r["members"]), _sel(universe, r["reference"])
            rmiss = [x for x in ref if x not in lengths]
            for m in mem:
                miss = rmiss + ([m] if m not in lengths else [])
                val = None if (miss or not ref) else lengths[m] - mean(ref)
                out.append(Relation(label, kind, f"{m} vs mean({', '.join(ref)})", val, lim, miss or ([] if ref else ["(no reference net)"]), [m] + ref))
        elif kind == "spread":
            mem = _sel(universe, r["members"])
            miss = [x for x in mem if x not in lengths]
            got = [lengths[x] for x in mem if x in lengths]
            out.append(Relation(label, kind, f"spread of {len(mem)} nets", None if (miss or not got) else max(got) - min(got), lim, miss, mem))
        elif kind == "between":
            a, b = _sel(universe, r["a"]), _sel(universe, r["b"])
            miss = [x for x in a + b if x not in lengths]
            val = None if (miss or not a or not b) else mean(a) - mean(b)
            out.append(Relation(label, kind, f"mean({', '.join(a)}) vs mean({', '.join(b)})", val, lim, miss, a + b))
        else:
            raise ValueError(f"unknown rule type {kind!r}")
    return out


def pair_nets(cfg: dict, universe: list[str]) -> list[tuple[str, str]]:
    pairs = []
    for r in cfg.get("rules", []):
        if r["type"] == "pairs":
            for pn in _sel(universe, [r["match"]]):
                pairs.append((pn, pn[: len(pn) - len(r["p"])] + r["n"] if pn.endswith(r["p"]) else pn.replace(r["p"], r["n"])))
    return pairs
