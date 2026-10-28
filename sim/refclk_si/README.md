# LPDDR4 EMIF refclk: LVDS oscillator into the Agilex 5 True Differential input

KiCad 10 + ngspice simulation of the 100 MHz refclk chain (2026-10-28): U9 (Abracon AX3DAF1, LVDS, 3.3 V) → R25/R26
33 Ω → C8/C9 100 nF → B.Cu 9.6 mm → via → U7 B55/A58 (bank 3A, 1.1 V True Differential Signaling), with R27/R28
50 Ω from each leg to a 0.875 V bias (1V1 × 3k9 / (1k + 3k9), C249 1 µF + C250 100 nF).

```sh
export KICAD_APPRUN=.../squashfs-root/AppRun     # see ../lpddr4_si/README.md; uses its models/agilex5_lpddr4.ibs
python3 refclk_si.py                              # 4 schematics x 21 channels, results/results.csv + results.md
SI_REUSE=1 python3 refclk_si.py                   # re-analyse the saved waveforms
python3 refclk_si.py --show I_400:v250_built_rd60 # one case in a window (die voltages and Vp - Vn)
```

## Models

- **Receiver: Agilex 5 IBIS** `tds11_in_e0t100` on B55 and A58 (the Quartus EMIF test build, see `../lpddr4_si`).
  Its on-chip 100 Ω differential termination (RD OCT) is an `[R Series]` model that KiCad's parser rejects; it is a
  resistor across the pins here, at 60/100/140 Ω (data sheet 813918 Table 20: ±40 %).
- **Source: no IBIS model.** Abracon publishes none for the AX3. A data-sheet LVDS source instead: VOD 250/350/450 mV
  into 100 Ω, 20–80 % edges 150 and 400 ps, VOS 1.25 V, as two bounds for the unknown output impedance:
  `I` = ideal current steering (worst for a low load, and it does not back-terminate the line: more ringing),
  `V` = 100 Ω differential Thevenin source.
- Each square wave is built from two PULSE sources so the operating point is the zero-mean AC-coupled steady state
  (a single PULSE starts the 100 nF caps charged to one level; they would need ~100 µs to settle).

## Limits

Data sheet 813918, Table 42, True Differential Signaling 1.1 V (receiver only): VID 100–454 mV, VICM(DC) 0.80–0.95 V;
over/undershoot not beyond 1.177 / 0.573 V. VICM ≤ 1.2 V when RD OCT is off.

## Results

| termination | worst case | VID settled | result |
|---|---|---|---|
| **as built**: R27/R28 + RD OCT (Quartus default `PHY_TERM_X_R_T_REFCLK_INPUT_OHM = RT_DIFF`) | RD 60 Ω, VOD 250 mV | 92–93 mV (82 mV right after the edge) | **fails VID ≥ 100 mV** |
| as built, RD 100 Ω (typ) | VOD 250 mV | 116–124 mV | passes, little margin |
| **RD OCT off (`RT_OFF`)**, R27/R28 only | all | 188–446 mV, legs 604–1136 mV | **passes every case** |
| RD OCT only, R27/R28 → 1 k bias | RD 140 Ω, VOD 450 mV | 583 mV, leg max 1196 mV | fails VID ≤ 454 mV and 1.177 V |

VICM 0.87 V in every case. Full table: `results/results.md`.

**Fix: set `PHY_TERM_X_R_T_REFCLK_INPUT_OHM = RT_OFF` for the LPDDR4 EMIF in the real Quartus project and keep
R27/R28.** No board change. Worst case then: VID 446 mV (8 mV under the 454 mV maximum, with the ideal current
source at the data sheet's maximum VOD) and 1136 mV per leg (41 mV under 1.177 V).

Not modelled: the oscillator's real output stage, coupling between the legs, the exact route (the pair is currently
unrouted on the board; 9.6 mm of B.Cu as in the earlier route), jitter.
