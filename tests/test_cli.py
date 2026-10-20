"""The command line, with KiCad's lengths stubbed so it runs without kicad-cli."""
import json
import sys

import pytest

from kicad_skew import cli

RULES = {"measure": ["CK_*"], "rules": [{"type": "pairs", "label": "P/N", "match": "_P$", "p": "_P", "n": "_N", "max": 0.2}]}


@pytest.fixture
def args(tmp_path, monkeypatch):
    board, rules = tmp_path / "b.kicad_pcb", tmp_path / "rules.json"
    board.write_text('(kicad_pcb (net 1 "CK_P") (net 2 "CK_N"))')
    rules.write_text(json.dumps(RULES))
    monkeypatch.setattr(cli, "measure", lambda *a, **k: {"CK_P": 30.0, "CK_N": 30.1})
    return [str(board), str(rules)]


def test_layers_without_pcbnew_says_skipped(args, tmp_path, monkeypatch, capsys):
    # a plain pip install: no pcbnew, so the layer check cannot run and must not read as "0 pairs split"
    monkeypatch.setitem(sys.modules, "pcbnew", None)
    out = tmp_path / "out.json"
    assert cli.main(args + ["--layers", "--json", str(out)]) == 0
    summary = capsys.readouterr().out.strip().splitlines()[-1]
    assert summary == ("PASS: 0 of 1 relations out of tolerance; layer check skipped "
                       "(needs KiCad's pcbnew module, run with KiCad's Python)")
    data = json.loads(out.read_text())
    assert data["layer_check"].startswith("skipped: ") and data["split_pairs"] == []


def test_layers_ran_reports_split_count(args, tmp_path, monkeypatch, capsys):
    import kicad_skew.layers
    monkeypatch.setattr(kicad_skew.layers, "split_pairs", lambda *a, **k: [])
    out = tmp_path / "out.json"
    assert cli.main(args + ["--layers", "--json", str(out)]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1] == "PASS: 0 of 1 relations out of tolerance; 0 pairs split across layers"
    assert json.loads(out.read_text())["layer_check"] == "ran"


def test_no_layers_flag_says_nothing_about_layers(args, capsys):
    assert cli.main(args) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1] == "PASS: 0 of 1 relations out of tolerance"
