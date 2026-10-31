# QSPI configuration flash SI (U7 SDM AS x4 -> U2 IS25WP128)

Chooses the series resistors on the QSPI lines. Result: **22 Ω at U7** on AS_CLK, AS_nCSO0 and AS_DATA0-3
(R293-R298, 0201, C155743).

## What is modelled

- **Driver:** the Agilex 5 SDM I/O `1p8_io_d8s1` from the Quartus IBIS file (`../lpddr4_si/models/`, see that
  README): 1.8 V LVCMOS, 8 mA, fast slew, no OCT (configuration user guide 813773, Table 28). Its 20-80 % edges are
  ~0.10 ns and its output impedance ~20 Ω. Typ/min/max from the corner model files (`../lpddr4_si/corner_models.py`).
- **Line:** 0.10 mm on In2 (53.8 Ω, 7.08 ps/mm, field-solved), routed lengths CLK 26.7 mm (2 vias), D0 35.4 mm
  (2 vias), CS# 38.7 mm (3 vias); vias 0.15 nH / 0.4 pF. Optional series R at the driver.
- **Receiver: a stand-in.** No IBIS model of the IS25WP128 is public. The Agilex 1.8 V input `1p8_in_20wpu`
  (clamps, C_comp 4.4 pF) on a BGA pin, plus 1.6 pF to reach the flash's 6 pF input capacitance.
- **Rate:** 200 Mb/s PRBS (a 100 MHz clock): AS_CLK is limited to 100 MHz on the -6S (813773 note 15).
- **Not modelled:** the read direction (flash drives D0-D3; no model), crosstalk, the flash's own package.

## Result (`results.md`, worst over CLK/D0/CS# and the three corners)

| Series R | Peak (V) | Undershoot (V) | Edges |
|---|---|---|---|
| none | 2.01-2.58 | -0.39 ... -0.78 | monotonic |
| **22 Ω** | 1.69-2.15 | -0.07 ... -0.27 | clean everywhere |
| 33 Ω | 1.64-2.01 | -0.02 ... -0.13 | 45-52 mV steps in the threshold band on D0 at min (die) |
| 47-68 Ω | <= 1.95 | ~0 | over-damped: steps of up to 75 mV in the threshold band |

Without termination the peaks pass VCC + 0.5 V (the usual ISSI absolute maximum; the IS25WP128 data sheet itself
could not be downloaded, so this is from a sibling part). "Extra crossings" counts crossings of VIH (0.7 VDD) and
VIL (0.3 VDD) beyond one per edge: a step or ringback inside the threshold band.

## Rerun

    KICAD_APPRUN=<KiCad 10 AppImage>/AppRun python3 qspi_si.py

`work/` (netlists, KIBIS cache) is git-ignored.
