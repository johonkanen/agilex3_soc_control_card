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

- `LPDDR4 SE 0.10mm 55R JLC08161H-3313` – single-ended (DQ/DM, CA/CKE/CS), time-domain tuning enabled, the per-layer delays above, via delay 7.2 ps/mm. Width 0.10 mm on every layer (2026-10-28, from the IBIS simulation in `sim/lpddr4_si`): ≈54–55 Ω stripline on In2/In5, ≈59 Ω microstrip on F/B.Cu. Target field 55 Ω.
- `LPDDR4 DIFF 0.10-0.10mm 87R JLC08161H-3313` – DQS/CK: 0.10 mm with a 0.10 mm gap, same delays. Field-solved (`tools/kicad_ibis_simulation`, `zsolve --gap`): 44 Ω odd mode, 87 Ω differential on In2/In5, 88 Ω on F/B.Cu; odd-mode delay 6.97 ps/mm inner, 6.06 ps/mm outer.
- Until 2026-10-27 these were `LPDDR4 SE 40R-45R …` / `LPDDR4 DIFF 40R-45R …` (0.18 mm inner / 0.20 mm outer, Altera 821801 targets; 68 Ω differential at a 0.10 mm gap).
- Earlier these were `LPDDR4 SE 50R …` (0.15/0.12 mm) and `LPDDR4 DIFF 100R …` (0.13/0.11 mm, 0.25 mm gap).

Widths are JLCPCB's own calculator results for JLC08161H-3313 (50 Ω: L1 0.1509 mm, L3/L6 0.1207 mm; 100 Ω at 0.25 mm gap: L1 0.1278 mm, L3 0.1082 mm; at 0.20 mm gap L6 0.1011 mm).

Breakout: inside the U7 and U12 courtyards the rule `lpddr_bga_neckdown` in `agilex_3_soc.kicad_dru` lets the router neck down to 0.1 mm (0.2 mm pair gap). Keep the neck as short as the escape needs and widen right after the breakout via; a few mm of 0.1 mm (≈62 Ω on top, ≈50 Ω inside) is electrically short compared with the LPDDR4 edge.

Net classes (Board Setup → Net Classes) and their patterns:

| Class | Pattern | Profile |
|---|---|---|
| `lpddr_dq` | `.*dq(0-31)$`, `.*/dm[0-3]$` | SE, 0.10 mm |
| `lpddr_ca` | `.*/(ca[0-5]|cke|~{cs}|~{rst})$` | SE, 0.10 mm |
| `lpddr_diff` | `.*/(dqs[0-3]|ck)_[PN]$` | DIFF, 0.10 / 0.10 mm |

With a profile assigned, the length tuner (`7` / `8` / `9`), the Net Inspector and DRC work in **ps**, and via
transitions are included using the stack-up heights.

**Package delay is on the board.** Every LPDDR4 ball of U7 has its Agilex 5 package delay as the pad's `die_delay`
(pad-to-die delay, from the Quartus `.pin` "Package Delay" column). KiCad adds it to every delay it shows, so all
numbers are die → U12 ball. Checked 2026-10-28: the 58 values equal the routed Quartus build (`varA_routed`), and
stripping them lowers each net's KiCad delay by exactly its value. U12 (SK hynix) has no package data; its 5–15 ps
spread is margin.

## 4. How to tune (2026-10-28)

**Budgets** (Altera 821801, ps, FPGA package included): DQ–DQS −68 … +43 per byte, CA–CK ±34, CS/CKE–CK ±85,
CK–DQS −340 … +170, P/N < 1, T-branches < 1.

**Rules in `agilex_3_soc.kicad_dru`:**
- `lpddr_pair_skew`: DQS and CK P/N within 1 ps.
- `lpddr_byteN_skew`: DQ/DM of each byte within 10 ps. KiCad keeps only one skew rule per net and the pair rule
  needs both halves, so DQS is not in these groups.
- The generated block `delay_report targets`: one delay window per LPDDR4 net, which the length tuner uses as its
  target. DQ/DM/DQS ±5 ps, CA/CK ±10 ps, CS/CKE ±30 ps. Do not edit it by hand.

**Report and targets:** `tools/lpddr4_delay/delay_report.py` (needs `KICAD_APPRUN` or `KICAD_CLI`):

```
python3 tools/lpddr4_delay/delay_report.py -o LPDDR4_DELAY_REPORT.md          # report only
python3 tools/lpddr4_delay/delay_report.py --dru -o LPDDR4_DELAY_REPORT.md    # + rewrite the target block
```

- It reads KiCad's own delays from a DRC run with a probe rule, so the numbers are exactly what the tuner shows.
- CA/CKE/CS/CK are T-nets, and KiCad sums trunk + both branches. The script computes the branches from the copper:
  its own total reproduces KiCad's to < 1.2 ps. It reports die → ball per channel, and flags T-branches more than
  1 ps apart.
- **Targets are lengthen-only.** Each byte goes to its slowest net (DQS included). CA/CKE/CS/CK go to the slowest
  die → ball delay, plus each net's own branch for KiCad's total. If shortening one long net is easier (e.g. dqs0 in
  byte 0), reroute it and rerun with `--dru`: the targets follow.

**Order:**
1. P/N of each DQS pair and of CK (≤ 1 ps).
2. Each byte to its target (`8` single track, `9` skew).
3. CK by hand as a coupled pair. At 2026-10-28 it needs about +136 ps (≈ 19 mm on In2) to meet the CA group. Then
   ca1–ca5/cke/cs to their targets. Fix the `~{cs}` T: its branches are 40.7 / 11.1 ps, because the trunk joins near
   R4.
4. Rerun the report. Done when it says "all limits met" and DRC has no `skew_out_of_range` / `length_out_of_range`.

## 5. Impedance

Target: 50 Ω single-ended, 100 Ω differential (Agilex OCT / LPDDR4 ODT set to the 48–60 Ω options accordingly). Per-layer widths are in the tuning profiles (section 3). The existing 0.1 mm routing is ≈62 Ω on L1/L8 and ≈50 Ω on L3/L6, so inner-layer runs can stay at 0.1 mm if you prefer not to re-route them; top/bottom runs outside the BGAs should be widened to 0.15 mm.

Sources: JLCPCB impedance calculator (https://jlcpcb.com/pcb-impedance-calculator), JLCPCB controlled-impedance stack-up parameters (https://jlcpcb.com/impedance), KiCad source `common/project/tuning_profiles.cpp` (JSON layout of tuning profiles).
