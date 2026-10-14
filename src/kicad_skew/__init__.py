"""kicad-skew: length and skew checks on KiCad's own routed lengths."""
from .lengths import measure
from .rules import Relation, evaluate

__all__ = ["measure", "evaluate", "Relation", "board_nets"]
__version__ = "0.1.0"


def board_nets(path: str) -> list[str]:
    """Every net name in a .kicad_pcb file (KiCad 7-10 formats), without needing pcbnew. Names are unescaped the way
    KiCad reads them (``"A10\\\\AP"`` in the file is the net ``A10\\AP``), so they match kicad-cli's reports."""
    import re
    raw = re.findall(r'\(net (?:\d+ )?"((?:[^"\\]|\\.)+)"\)', open(path, encoding="utf-8").read())
    return sorted({re.sub(r"\\(.)", r"\1", n) for n in raw})
