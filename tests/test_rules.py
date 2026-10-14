import pytest

from kicad_skew import board_nets
from kicad_skew.rules import MIL, evaluate, pair_nets

L = {"CK_P": 30.0, "CK_N": 30.2, "DQS_P": 25.0, "DQS_N": 25.1, "DQ0": 26.0, "DQ1": 40.0, "A0": 31.0, "A1": 29.0}
NETS = sorted(L) + ["DQ2"]          # DQ2 exists on the board but is unrouted


def test_pairs_group_spread_between():
    cfg = {"rules": [
        {"type": "pairs", "label": "pn", "match": "_P$", "p": "_P", "n": "_N", "max": 0.15},
        {"type": "group", "label": "byte", "members": ["^DQ\\d$"], "reference": ["^DQS_[PN]$"], "max": 5},
        {"type": "spread", "label": "ca", "members": ["^A\\d$"], "max": 1.5},
        {"type": "between", "label": "dqs-ck", "a": ["^DQS_"], "b": ["^CK_"], "max": 10},
    ]}
    rel = evaluate(cfg, L, NETS)
    by = {(r.rule, r.what.split(" ")[0]): r for r in rel}
    assert by[("pn", "CK_P")].value == pytest.approx(0.2) and not by[("pn", "CK_P")].ok
    assert by[("pn", "DQS_P")].ok
    assert by[("byte", "DQ0")].value == pytest.approx(26.0 - 25.05) and by[("byte", "DQ0")].ok
    assert not by[("byte", "DQ1")].ok
    assert by[("byte", "DQ2")].value is None and by[("byte", "DQ2")].missing == ["DQ2"] and not by[("byte", "DQ2")].ok
    sp = [r for r in rel if r.rule == "ca"][0]
    assert sp.value == pytest.approx(2.0) and not sp.ok
    bt = [r for r in rel if r.rule == "dqs-ck"][0]
    assert bt.value == pytest.approx(25.05 - 30.1) and bt.ok


def test_mil_units():
    rel = evaluate({"unit": "mil", "rules": [{"type": "pairs", "match": "_P$", "p": "_P", "n": "_N", "max": 12}]}, L, NETS)
    assert rel[0].limit == pytest.approx(12 * MIL)


def test_pair_nets():
    assert pair_nets({"rules": [{"type": "pairs", "match": "_P$", "p": "_P", "n": "_N", "max": 1}]}, NETS) == [("CK_P", "CK_N"), ("DQS_P", "DQS_N")]


def test_board_nets_old_and_new_formats(tmp_path):
    p = tmp_path / "b.kicad_pcb"
    p.write_text('(kicad_pcb (net 0 "") (net 1 "GND") (segment (net "DDR_DQ0")) (pad (net 3 "CK_P")))')
    assert board_nets(str(p)) == ["CK_P", "DDR_DQ0", "GND"]


def test_unknown_rule_type():
    with pytest.raises(ValueError):
        evaluate({"rules": [{"type": "nope", "max": 1}]}, L, NETS)


def test_board_nets_unescapes_backslashes(tmp_path):
    # KiCad writes the net A10\AP as "A10\\AP"; kicad-cli reports it as A10\AP
    p = tmp_path / "b.kicad_pcb"
    p.write_text('(kicad_pcb (net 1 "A10\\\\AP") (segment (net "A12\\\\~{BC}")))')
    assert board_nets(str(p)) == ["A10\\AP", "A12\\~{BC}"]


def test_unshared_ignores_same_layer_length_difference():
    from kicad_skew.layers import unshared
    # both legs on In9, one 2.2 mm longer there (made up on a skipped outer layer): not a layer split
    assert unshared({"In9.Cu": 71.7}, {"In9.Cu": 73.9}) == 0.0
    # legs on different inner layers: all of the shorter leg is unshared
    assert unshared({"In2.Cu": 40.0}, {"In5.Cu": 41.0}) == 40.0
    # a 3 mm section of one leg on another layer
    assert abs(unshared({"In2.Cu": 37.0, "In5.Cu": 3.0}, {"In2.Cu": 40.0}) - 3.0) < 1e-9
