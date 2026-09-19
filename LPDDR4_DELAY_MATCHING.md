# LPDDR4 delay matching – JLCPCB JLC08161H-3313 stack-up

Written 2026-09-19. Source for the stack-up: JLCPCB impedance calculator (8 layers, 1.6 mm, 1 oz outer / 0.5 oz inner); JLCPCB material data from jlcpcb.com/impedance.

## 1. Stack-up now entered in the board file (Board Setup → Physical Stackup)

| Layer | Material | Thickness | Er (JLCPCB) |
|---|---|---|---|
| L1 F.Cu | copper 1 oz | 0.035 mm | |
| | prepreg 3313 | 0.0994 mm | 4.1 |
| L2 In1.Cu | copper 0.5 oz | 0.0152 mm | |
| | core | 0.100 mm | 4.6 |
| L3 In2.Cu | copper 0.5 oz | 0.0152 mm | |
| | prepreg 2116 ×3 | 0.1164 + 0.1240 + 0.1164 = 0.3568 mm | 4.16 |
| L4 In3.Cu | copper 0.5 oz | 0.0152 mm | |
| | core | 0.300 mm | 4.6 |
| L5 In4.Cu | copper 0.5 oz | 0.0152 mm | |
| | prepreg 2116 ×3 | 0.3568 mm | 4.16 |
| L6 In5.Cu | copper 0.5 oz | 0.0152 mm | |
| | core | 0.100 mm | 4.6 |
| L7 In6.Cu | copper 0.5 oz | 0.0152 mm | |
| | prepreg 3313 | 0.0994 mm | 4.1 |
| L8 B.Cu | copper 1 oz | 0.035 mm | |

Total 1.574 mm (JLCPCB: finished 1.57 mm ±10 %). Solder mask: 1.2 mil (0.03 mm) over substrate, 0.6 mil over copper, Er 3.8. Copper finish ENIG (JLCPCB default for 6+ layers). Core material Nan Ya NP-155F.

The pairs L2/L3 and L6/L7 sit on the thin 0.1 mm cores, so the natural signal/reference pairing is L1→L2, L3→L2, L6→L7, L8→L7 (the memory nets are currently on L1, L3, L6 and L8).

## 2. Propagation delay per layer (entered in the tuning profiles)

Calculated for the 50 Ω trace widths from the JLCPCB Er values (Hammerstad microstrip with solder mask; capacitance-weighted Er for the asymmetric striplines).

| Layer | Structure | Er_eff | Delay |
|---|---|---|---|
| F.Cu, B.Cu | microstrip over 0.0994 mm 3313, masked, 0.15 mm | ≈ 3.3 | **6.1 ps/mm** (5.9 bare) |
| In2.Cu, In5.Cu | stripline, 0.1 mm core one side / 0.357 mm 2116 other side | ≈ 4.51 | **7.08 ps/mm** |
| In3.Cu, In4.Cu | stripline, 0.3 mm core / 0.357 mm 2116 | ≈ 4.41 | **7.00 ps/mm** |
| In1.Cu, In6.Cu | (plane layers) 0.0994 mm 3313 / 0.1 mm core | ≈ 4.36 | 6.97 ps/mm |
| via | barrel in FR-4, incl. stub loading | | **7.2 ps/mm** of traversed height |

Rule of thumb from these numbers: **1 mm on L1/L8 ≈ 0.85 mm on L3/L6.** A 10 mm top-layer section is about 11 ps shorter in delay than the same length on an inner layer.

## 3. What is in the project file

Board Setup → Tuning Profiles (KiCad 10):

- `LPDDR4 SE 50R JLC08161H-3313` – single-ended 50 Ω, time-domain tuning enabled, the per-layer delays above, widths 0.15 mm on F/B.Cu and 0.12 mm on the inner layers, via delay 7.2 ps/mm.
- `LPDDR4 DIFF 100R JLC08161H-3313` – differential 100 Ω, same delays, 0.13 mm / 0.25 mm gap on F/B.Cu, 0.11 mm / 0.25 mm on the inner layers.

Widths are JLCPCB's own calculator results for JLC08161H-3313 (50 Ω: L1 0.1509 mm, L3/L6 0.1207 mm; 100 Ω at 0.25 mm gap: L1 0.1278 mm, L3 0.1082 mm; at 0.20 mm gap L6 0.1011 mm).

Breakout: inside the U7 and U12 courtyards the rule `lpddr_bga_neckdown` in `agilex_3_soc.kicad_dru` lets the router neck down to 0.1 mm (0.2 mm pair gap). Keep the neck as short as the escape needs and widen right after the breakout via; a few mm of 0.1 mm (≈62 Ω on top, ≈50 Ω inside) is electrically short compared with the LPDDR4 edge.

Net classes (Board Setup → Net Classes) and their patterns:

| Class | Pattern | Profile |
|---|---|---|
| `lpddr_dq` | `.*dq(0-31)$`, `.*/dm[0-3]$` | SE, width 0.12 |
| `lpddr_ca` | `.*/(ca[0-5]|cke|~{cs}|~{rst})$` | SE, width 0.12 |
| `lpddr_diff` | `.*/(dqs[0-3]|ck)_[PN]$` | DIFF, 0.11 / 0.25 |

With a profile assigned, the length tuner (`7` / `8` / `9`) reports and targets **ps** instead of mm, and via transitions are included using the stack-up heights (`use_height_for_length_calcs` is on). Delay constraints can be written in the custom rules in time units, e.g.

```
(rule "byte0 skew"
  (condition "A.NetClass == 'lpddr_dq' && A.Name matches '.*/(dq[0-7]|dm0)$'")
  (constraint skew (max 5ps) (within_diff_pairs no)))
```

## 4. How to use

1. Route each byte lane; it does not matter any more which layers a DQ uses, as long as the DQS pair of that lane sees a comparable via count.
2. Tune to the DQS of the lane in ps (Inspect → Net Inspector shows delay when a profile is assigned).
3. Add the Agilex 5 package delays from Quartus (Fitter → *.pin file / "Package skew" report) to the FPGA end – they are tens of ps and differ per ball – before comparing against the EMIF skew budget.
4. CA/CK: match CA and CKE to CK in ps; match DQS of every lane to CK within the EMIF guideline.

## 5. Impedance

Target: 50 Ω single-ended, 100 Ω differential (Agilex OCT / LPDDR4 ODT set to the 48–60 Ω options accordingly). Per-layer widths are in the tuning profiles (section 3). The existing 0.1 mm routing is ≈62 Ω on L1/L8 and ≈50 Ω on L3/L6, so inner-layer runs can stay at 0.1 mm if you prefer not to re-route them; top/bottom runs outside the BGAs should be widened to 0.15 mm.

Sources: JLCPCB impedance calculator (https://jlcpcb.com/pcb-impedance-calculator), JLCPCB controlled-impedance stack-up parameters (https://jlcpcb.com/impedance), KiCad source `common/project/tuning_profiles.cpp` (JSON layout of tuning profiles).
