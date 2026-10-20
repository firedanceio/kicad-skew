# Changelog

## 0.1.0 (unreleased)
- First release: KiCad-native routed lengths through kicad-cli, JSON rules (pairs, group vs reference, spread,
  between), missing/unrouted nets fail, pair layer-parity report, JSON output, `--map` board view. Example rules for LPDDR4 and USB 2.0, and for Antmicro's open-source LPDDR4 test board.
- Net names with a backslash (e.g. `A10\AP`) are matched: names read from the board file are unescaped the way KiCad
  reads them, so they agree with kicad-cli's reports. Before, such nets were reported as missing.
- The layer check counts only copper a leg runs without its partner on the same layer. A length difference on a
  shared layer (made up on a skipped outer layer, say) was being reported as a split pair.
- Example rules and a worked example for Antmicro's 72-bit DDR4 RDIMM tester.
- `--layers` without KiCad's `pcbnew` module (a plain pip install, say) now ends with "layer check skipped" and the
  reason, instead of "0 pairs split across layers". The JSON output says whether the layer check ran
  (`layer_check`).
