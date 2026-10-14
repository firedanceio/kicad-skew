"""kicad-cli integration: a synthetic board with known geometry. Skipped without KiCad."""
import math
import os

import pytest

pcbnew = pytest.importorskip("pcbnew")
from kicad_skew.lengths import find_cli, measure

try:
    find_cli()
except FileNotFoundError:
    pytest.skip("kicad-cli not installed", allow_module_level=True)

mm = pcbnew.FromMM


def test_track_and_via_lengths(tmp_path):
    b = pcbnew.BOARD()
    nets = {}
    for k, n in enumerate(("SIG_A", "SIG_B"), 1):
        b.Add(pcbnew.NETINFO_ITEM(b, n, k))
        nets[n] = b.FindNet(n)

    def seg(net, a, c, layer="F.Cu"):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
        t.SetEnd(pcbnew.VECTOR2I(mm(c[0]), mm(c[1])))
        t.SetWidth(mm(0.2))
        t.SetLayer(b.GetLayerID(layer))
        t.SetNet(net)
        b.Add(t)

    seg(nets["SIG_A"], (0, 0), (30, 0))
    seg(nets["SIG_A"], (30, 0), (30, 40))                       # 70 mm, one layer
    seg(nets["SIG_B"], (0, 10), (20, 10))
    seg(nets["SIG_B"], (20, 10), (40, 10), "B.Cu")
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(mm(20), mm(10)))
    v.SetWidth(mm(0.6))
    v.SetDrill(mm(0.3))
    v.SetNet(nets["SIG_B"])
    b.Add(v)
    path = os.path.join(str(tmp_path), "t.kicad_pcb")
    b.Save(path)
    L = measure(path, ["SIG_*"])
    assert L["SIG_A"] == pytest.approx(70.0, abs=0.01)
    assert 40.0 < L["SIG_B"] < 42.0                              # 40 mm of track plus one barrel F.Cu -> B.Cu
    assert measure(path, ["SIG_*"], exclude=["SIG_B"]).keys() == {"SIG_A"}
