"""kicad-skew: length and skew checks on KiCad's own routed lengths."""
from .lengths import measure
from .rules import Relation, evaluate

__all__ = ["measure", "evaluate", "Relation", "board_nets"]
__version__ = "0.1.0"


def board_nets(path: str) -> list[str]:
    """Every net name in a .kicad_pcb file (KiCad 7-10 formats), without needing pcbnew."""
    import re
    return sorted(set(re.findall(r'\(net (?:\d+ )?"((?:[^"\\]|\\.)+)"\)', open(path, encoding="utf-8").read())))
