# Validation

What we checked before release, why, and what happened. Run on 2026-10-14 with KiCad 10.0.6 on macOS.

## What was needed

kicad-skew was written against one board, ours. Before sharing it we needed to see it work on other people's memory
layouts, with their net names and their rules, and to confirm that the lengths it reports are what KiCad means by
length and nothing else.

## 1. Unit tests

`pytest`: 8 passed, two of them added for the bugs below.

## 2. Open-source boards

| Board | Rules | Result |
|---|---|---|
| [Antmicro LPDDR4 test board](https://github.com/antmicro/lpddr4-test-board) (8 layers, commit 5c8b5d3) | `examples/antmicro-lpddr4-test-board.json` | PASS: 0 of 31 out, no split pairs |
| [Antmicro DDR4 RDIMM tester](https://github.com/antmicro/data-center-dram-tester) (12 layers, commit e7c85eb) | `examples/antmicro-ddr4-rdimm-tester.json` (new) | PASS: 0 of 116 out, no split pairs; worst nibble 0.06 mm from its strobe |
| Our own board (FirePod spin 2, r3) | `examples/lpddr4-rockchip.json` | 0 of 68 out, 4 of 6 clock/strobe pairs split across layers: the same as our review found |

## 3. What KiCad's length contains

On the DDR4 tester, KiCad's lengths ran 12 to 27 mm longer than the copper. We accounted for every millimetre:

- the FPGA's package lengths, which Antmicro entered on the pads (KiCad's pad-to-die length), 9.6 to 25.7 mm per net
- the two vias on each net: 0.5 to 2.9 mm after the package lengths are taken off, on a 1.74 mm board

So the length kicad-skew reports is track + package + via barrel, and nothing else. Matching the copper alone would have
been off by up to 16 mm.

## 4. Bugs found and fixed

1. **Net names with a backslash were reported missing.** The DDR4 tester has nets `A10\AP` and `A12\~{BC}`. The board
   file stores them escaped (`"A10\\AP"`), kicad-cli reports them unescaped, and kicad-skew compared one with the other.
   Names read from the board file are now unescaped the way KiCad reads them.
2. **A same-layer length difference was reported as a split pair.** DQS0 on the DDR4 tester has both legs on In9, one
   2.2 mm longer there, with the difference made up on the outer layer the check skips. The old measure summed the
   per-layer differences, so it reported "1.1 mm on different layers". The check now counts only copper a leg runs
   without its partner on the same layer. Rechecked on our own board: the same 4 split pairs are still found.
