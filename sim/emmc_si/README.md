# eMMC (U11) signal integrity: can the bus run on In5?

Question (2026-10-29): the eMMC bus U7 (HPS SDMMC) -> U11 (Kioxia THGAMVG7T13BAIL) is partly routed on In5. In5's
closest plane is In6 (0.1 mm), a split power layer: 1V2 under most of the route, 3V3 near U11, gaps between them and
under the U11 via field. In2 (next to solid In1 GND) is the clean alternative. Does In5 work?

## Answer

- **The layer is not the problem; the missing termination is.** The HPS SDMMC driver (`1p8_io_d8s1`, about 20 ohm,
  100-140 ps edges) into a 25 mm unterminated line rings on *any* layer: 2.8 V overshoot and -0.9 V undershoot at the
  eMMC pin even over a solid plane, with the ring-back after a rising edge only 8 mV above VIH.
- **Without a series resistor, In5 is worse.** The 88 ohm gap sections and the return-path inductance at each
  reference change push the ring-back into the VIL..VIH band: -28 to -37 mV at 0-0.5 nH per change, -119 mV at
  2 nH. There are no false edges in any case, but the margin is gone.
- **With 22-33 ohm in series at the HPS ball, In5 is fine.** At 2 nH per reference change, ring-back margin is
  +279 / +330 mV (solid plane: +285 / +295), overshoot is 2.29 / 2.13 V and undershoot -0.38 / -0.21 V. HS400
  timing margin is about 1.5 ns either way.
- **Resistor position (33 ohm on F.Cu with a via down and up again, In5 at 2 nH).** Ring-back margin / overshoot /
  undershoot at each distance along the 24.4 mm route:

  | distance | ring-back margin | overshoot | undershoot |
  |---|---|---|---|
  | at U7 | +330 mV | 2.13 V | -0.21 V |
  | 5 mm | +290 mV | 2.27 V | -0.34 V |
  | 10 mm (mid-route) | +297 mV | 2.29 V | -0.36 V |
  | 15 mm | +255 mV | 2.48 V | -0.55 V |
  | 20 mm | +236 mV | 2.55 V | -0.63 V |

  Mid-route is close to placement at the driver; past the middle, overshoot grows. The schematic has R280-R290 (33R
  0201) between the `<net>_hps` (U7) and `<net>` (U11) nets. They are to be placed about mid-route, or nearer U7.
- Eyes are wide open in every case. Against the HS400 data mask (VIH-VIL = 0.54 V, tISU + tIH = 0.8 ns at 2.5 ns
  UI), the timing margin is >= 1.45 ns, even in the deliberately bad case (15 mm over a gap, 10 nH per change).
  At 400 MT/s the eye does not decide this; ring-back and overshoot do.

## What is modelled

| part | model |
|---|---|
| driver | Agilex 5 HPS `1p8_io_d8s1`, pin AU74 (HPS_SDMMC_CMD) with its [Pin] package R/L/C, from the Quartus IBIS of `~/dev/agilex5_emif_test/varA_hpsmux` (SDMMC on the board's balls). Validated: 50 ohm load levels exact, t20-80 104 / 140 ps vs the table's 105 / 139 ps (`results/validate_driver.md`). Corners typ / min / max (`vcc rpin lpin cpin`). |
| eMMC input | 6 pF (JEDEC eMMC 5.1 C_DEVICE max) or 2 pF (light load, more ringing), **no clamp diodes**: the real part's ESD / clamp structure would cut the overshoot, so Vmax / Vmin are pessimistic. |
| pull-up | 10k to 1V8 on a 1 mm B.Cu stub at U11 (as on the board) |
| lines (0.10 mm, `kicad_ibis.zsolve`) | F.Cu breakout 1 mm: 58.6 ohm, 6.14 ps/mm. In5 (or In2) stripline: 53.8 ohm, 7.00 ps/mm. In5 over an In6 gap (In4 only, 0.357 mm): 88.5 ohm, 6.53 ps/mm. |
| route (sd_cmd as routed) | 1V2 12.6 mm, gap 1.2 mm (1V2/3V3 split), 3V3 8.1 mm, gap 2.5 mm (U11 via field), 24.4 mm in total. `solid` is the same length over one plane. |
| vias | 0.5 nH / 0.4 pF (estimate, as in sim/lpddr4_si) |
| return path | series L at each reference change: U7 via (GND -> In6 1V2), the 1V2/3V3 split and the U11 via (3V3 -> GND). Swept 0 / 0.5 / 1 / 2 / 4 nH each. **Estimate**: about 0.3 nH of In4-In6 cavity plus the decoupling cap's ESL (0.3-0.5 nH) when a cap is within a few mm, so 1-2 nH is a realistic value. |
| stimulus | PRBS7 at 400 MT/s (HS400 data; CMD / CLK edges are a subset), 150 bits |

200 ohm damping resistors sit across every lumped L. Without them, the 10+ GHz via tanks stop ngspice, and at the
signal frequencies (|jwL| < 10 ohm) they have no effect.

Not modelled:
- the read direction (eMMC driver -> HPS) and the data strobe (DS), because Kioxia has no public IBIS model;
- crosstalk and plane-cavity noise;
- the min-corner thresholds, which stay at the 1.8 V levels.

## Files and rerun

```
python3 prep_models.py <quartus ibis>/emif_test_emif_test_a5eb013bb23be6s.ibs    # -> models/ (git-ignored)
KICAD_APPRUN=.../squashfs-root/AppRun python3 run_si.py --validate
KICAD_APPRUN=.../squashfs-root/AppRun python3 run_si.py          # results/summary.md, eye_*.png (1 min)
python3 ringback.py                                               # results/ringback.md
```

`prep_models.py` keeps only `1p8_io_d8s1` and its pins, because KiCad 10.0.7's IBIS parser throws on the full Quartus
file (vector range check).

| file in `models/` | source |
|---|---|
| `agilex5_hps_sdmmc.ibs` | Quartus Pro 26.1.1, from a copy of `~/dev/agilex5_emif_test/varA_hpsmux`: `quartus_eda emif_test -c emif_test --board_signal_integrity=on --format=ibis --output_directory=ibis`, then `prep_models.py` |
