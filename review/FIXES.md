# Pre-order fix list

The fixes proposed by the review (`a1_agilex.md`, `a2_schematic.md`, `b_assembly.md`, `c_layout.md`), as corrected by
the verification pass (`v1_power.md`, `v2_assembly.md`, `v3_layout.md`). Tick an item (`- [x]`) when it is done, and
put the commit after it. **Check** says how to confirm the fix in the board, the netlist or the JLC output.

Status 2026-11-01 (evening): sections 1 and 2 done in the working tree, not yet committed. New parts (section 3) are
deferred: not on this pass. Checked after the edits:
- DRC unchanged: the 3 known J3 warnings, 0 unconnected, 0 parity errors.
- ERC: 0 violations.
- Netlist: only R65.2 and Y2.1 changed net (both to 1V8).
- The LPDDR4 delay report passes; byte 0 spread went from 6.9 to 5.2 ps.

## 0. Decisions needed first

- [x] **U5 ADC (B-01, BLOCKER):** decided to keep the ADS7056; the user has sourced it (consign it, or JLC
  stock if it recovers). ADS7056IRUGR C2669798 is oversold at JLC (−30). The options were:
  - ADS7052IRUGR **C2669879** (116 in stock): same pins and frame, 1 MSPS, SCLK ≤ 24 MHz;
  - ADS7046IRUGR C543003: 12-bit, 15-clock frame (FPGA logic changes);
  - source the ADS7056 yourself and consign it.
- [x] **A2-01 5V0 protection on this revision?** Not now: new parts deferred (2026-11-01).
- [x] **A1-01 PLL/ADC filters on this revision?** No, omitted on purpose (decided 2026-11-02). See section 3.
- [ ] **Optional items:** U8 → AP61203 (A2-07); 4 × 10 µF under U7 (C-06); 1V1 stitching caps (C-02). Not decided; the last two are new parts.

## 1. Value, field and rule changes (no copper)

### Assembly blockers

- [x] **B-01:** U5 stays ADS7056IRUGR (C2669798), sourced by the user. Before ordering, check whether JLC stock
  recovered, or set the part up as consigned.
  *Check:* BOM U5 line; `tools/jlc/stock_check.py` shows stock ≥ 5.
- [x] **B-02:** moved the U5 and U15 footprint anchors to the package centre. Only the origin moved; no copper
  changed and no pad or graphic moved (checked with pcbnew). The library footprints `agilex_lib:ads7056` and
  `agilex_lib:TDA38812` were shifted the same way, and DRC shows no library mismatch.
  - U5: (131.042, 129.949). This is the centre of the side pins; the verifier's 131.067 included the pad-4
    offset (B-14).
  - U15: (160.862, 134.204).
  *Check:* the CPL rows for U5/U15 give those coordinates, and the anchor lies inside the package outline.
- [x] **B-04:** set `JLC Rotation Offset = 90` on U8, U16, U18 and U19 (SOT-563). The CPL should give **0**; it gives 90 now.
- [x] **B-03:** set `JLC Rotation Offset = 270` on U5. CPL **0** (now 90). U15 stays at 0.
- [x] **B-05:** set `JLC Rotation Offset = 90` on U9. CPL **270** (now 0).
- [x] **Other CPL rotations (v2 extra):** the CPL values are now:
  - [x] U1: **90** (was 0)
  - [x] U42: **90** (was 180)
  - [x] U6: **270** (was 180)
  - [x] RN1–RN7: **270** (was 0)
  - [x] THT headers: J1, J2, J5 and J10 are 0; J4 and J6 are 180.

  These come from `JLC Rotation Offset` fields on both the symbol and the footprint, with the values from v2's
  table. The regenerated CPL matches every target above. U15 got an explicit 0.
- [ ] **Tool fix, `tools/jlc/jlc_bom_cpl.py`:** deferred. Every affected part now has an explicit field, so the
  current output is right; the formula change only matters for new bottom-side parts matched by the table. If it
  is fixed, the bottom-side field values must be recomputed with it.
  - it subtracts the rotation offset for bottom-side parts where it should add it (as kicad-jlcpcb-tools does);
  - its name-based package table is unreliable, so set explicit per-part fields instead.

  This is a change to the `tools/jlc` submodule.
  *Check:* regenerate the BOM/CPL; every row in the table in `v2_assembly.md` matches; then check the parts in JLC's 3D preview at order time.

### Schematic values

- [x] **A1-02 / A2-04:** R247 10k → **4.7k (C270346)**; C259 → DNP.
  *Check:* the netlist value; C259 is absent from the BOM.
- [x] **A2-07:** 0.1 % thin-film divider resistors, all Yageo RT, ±25 ppm:
  - [x] 1V8: R82 200k (C728556) and R80 100k (C852472). This rail failed the 1.75–1.85 V window on both sides.
  - [x] 3V3: R85 200k (C728556) and R83 44.2k (C705633). This rail was 37 mV high at worst case.
  - [x] 1V1: R91 200k (C728556) and R89 240k (C852659, 2,951 in stock). This rail was marginal, 2 mV over.

  The values read "200k 0.1%" and so on, so these stay separate BOM lines from the 1 % 200k parts on 1V2.
  - [ ] Optional: U8 (3V3) → AP61203Z6-7 C5244557 (forced PWM), like U16/U18.

  *Check:* the BOM shows 0.1 % parts with LCSC numbers in stock; the worst-case table in `v1_power.md` passes.
- [x] **C-06, U7 decoupling values (existing 0201 pads):** assigned by the nearest U7 ball's function.
  - 4.7 µF **C5969171** (17 parts):
    - VCC/VCCP: C137–C141, C144, C152, C156;
    - VCCL_HPS: C122, C147, C150;
    - VCCPT_HVIO: C191, C195;
    - VCCIO_PIO_2A: C209, C210;
    - VCCIO_PIO_3A: C218, C220.
  - 1 µF **C272877** (20 parts):
    - HPS core: C133, C134, C149, C151, C153, C155;
    - SDM: C135, C136, C146, C154;
    - VCCPT_HVIO: C175, C177, C179, C181, C183, C185, C187;
    - VCCADC: C193;
    - VCCIO_HPS: C197;
    - VCCRCORE: C206.
  - 1 µF 10 V **C76935** (10 parts): the 3V3 HVIO caps C174–C192.
  - Note: C191 sits at a VCCPT_HVIO ball and C193 at the VCCADC ball, not at VCCPT balls as v3 assumed. No
    bottom cap is next to a VCCPT ball, so two 4.7 µF parts on the shared 1V8 copper (C191, C195) stand in.

  *Check:* each rail's count against Table 63 in `v3_layout.md`.
- [x] **B-08:** set J3 LCSC to **C27985219** (HC-PM127-4.3H-2x19PZ), JLC Rotation Offset 270, or make J3 DNP.

### Design rules (.kicad_dru), then refill

- [x] **C-03:** NPTH `hole_clearance` 0.3 mm (H1/H2 inner planes are now 0.175 mm from the hole).
- [x] **C-05:** inner-layer antipads ≥ 0.2 mm from via drills (388 spots), set by rule, then refill.
- [x] **C-04 (rule part):** raise `lpddr_bga_clearance` to 0.09 mm, *after* the copper fix in section 2.

  *Check:* DRC clean, then a DRC diff against the previous state. Done: the rules are `jlc_inner_hole_to_zone` and
  `jlc_npth_clear`, then a refill. Measured after the refill:
  - via drill to a foreign inner zone: ≥ 0.200 mm (was 0.175);
  - H1/H2 NPTH to the planes: 0.300 mm (was 0.175).
- [ ] **New observation:** JLC lists "Inner layer PTH pad hole to copper clearance 0.3mm". The THT pad holes
  (J3 and the others) are 0.25 mm from the inner planes, both before and after these edits. The JLC DFM check
  will show whether this matters.

## 2. Small copper changes

- [x] **C-01:** ≥ 6 GND vias on the `Vcore_gnd` island (B.Cu) at x 158.85, y 132.8–136.8. The single via at
  (158.44, 132.33) carries 3.9–5.8 A today.
  *Check:* pcbnew count of the vias that join the island to the GND planes. Done: 8 vias added, 9 in total.
  - 5 at x 158.85, y 133.6–136.8;
  - 158.45, 131.6 and 158.45, 130.4;
  - 158.05, 138.4.

  (158.85, 132.8) was skipped: it is 0.15 mm from U15.19.
- [x] **A2-02:** connect Y2 pad 1 (OE) to pad 4 (1V8) with a trace, or add a ≤ 10k pull-up.
  *Check:* the netlist puts Y2.1 on 1V8. Done:
  - schematic: pin 1 of the symbol is now an `OE` input instead of NC (in the sheet and in `agilex_5_lib`), wired
    to 1V8;
  - board: a 0.2 mm B.Cu track joins pad 4 to pad 1.
- [x] **A2-05:** re-net R65 pad 2 from 5V0 to **1V8** (the Group-2B enable pull-up).
  *Check:* the netlist puts R65.2 on 1V8. Done:
  - schematic: a 1V8 power symbol replaces the 5V0 wire;
  - board: the 5V0 stub was removed, and a 0.15 mm B.Cu track runs west of R65 to the 1V8 via at
    (147.644, 128.786).
- [x] **C-04:** re-centre 8 F.Cu segments at U7 (dq0, dq2 and dq4 at 0.075 mm from pads), then the rule change from section 1.
  *Check:* minimum track-to-pad gap at U7 ≥ 0.09 mm. Done: dq0, dq2, dq4 and dq16 were rerouted locally and now
  clear by 0.100–0.123 mm. No LPDDR4 F.Cu gap under U7 is below 0.09 mm. Length changes: dq0 +0.28 mm, dq16
  +0.12 mm, dq2 +0.04 mm, dq4 0. The delay report passes.
- [ ] **JLC online DFM check:** run it for the via-drill-to-track spots (C-05, 444 spots).

## 3. New parts that need board space (deferred, 2026-11-01)

- [ ] **A2-03 (UART half):** 4.7k pull-up to 3V3 (C25900) on `hps_uart0_rx_3v3`. The JTAG half was refuted: U1 has 71k internal pull-downs.
- [ ] **A2-06:** two 10 Ω 0402 resistors (C25077):
  - local VCORE → `vcoresense_P`;
  - GND → `vcoresense_N`.
- [ ] **A2-01** (if yes in section 0): 5V0 input protection, e.g. AO3401A P-FET (C15127) + SMF5.0A TVS, or an eFuse.
- [x] **A1-01: omitted (decided 2026-11-02).** The PLL/ADC balls stay on the shared 1V8 and VCORE planes. Splitting them
  off under U7 would compromise the planes more than the beads would filter. What a fix would have needed (for a later revision):
  - three beads minimum (821801 §10.4): one for VCCPLL1/2_HPS + VCCPLL_SDM + VCCADC (the guide allows combining these),
    one for VCCPLLDIG1/2_HPS (Fig 120), one for VCCPLLDIG_SDM (Fig 121);
  - MPZ0603S121HT000 0201 (C695597) is enough: Quartus estimates ≈23 mA on the 1V8 group, ≈8 mA and ≈1 mA on the
    VCORE ones, so the drop stays under 0.5 % of the supply. 2 × 47 µF 0603 after each bead;
  - Trenz AXC3000, AXE5000 and AXE5 Falcon (same A5EE013BB23B as U7) all fit these filters.
  - Bring-up: if PLL jitter or ADC noise shows up, look here first.
- [x] **C-06 optional:** 4 × 10 µF 0402 (C15525) on the B.Cu VCORE copper at y ≈ 124.5.
  - [x] Schematic: C268–C271 (VCORE) and C272 (1V1, for VCCIO_PIO_3A) in `soc_power`, 2026-11-02.
  - [x] Board: placed (by hand, 2026-11-02). Free B.Cu VCORE copper is at x 154.8–158.2, y 123.6–127.9 (left of L1, above C130).
    Each GND pad needs its own via; avoid In2 `vcoresense_P/N` (x 157.69/157.94), In3 1V2 (x 154.50) and the
    In5 `fpga_led` track. C272 goes near the U7 1V1 caps C218–C221 (x ≈ 156, y ≈ 110).
- [x] **U1 bypass (new, 2026-11-02):** U1 (JTAG SN74AXC4T774) had no supply caps; the nearest were 7 mm away.
  - [x] Schematic: C273 100 nF on 1V8 (VCCB, pin 15) and C274 100 nF on 3V3 (VCCA, pin 16), C1525, in `debug_status`.
  - [x] Board: placed (by hand, 2026-11-02) at U1 pins 15/16 (U1 at 180.49, 127.70, top side). U42 already has C253/C254, on
    the top side above its pins.
- [x] **3V3 B.Cu pour to the PHY (2026-11-02):** new zone `3v3_phy` (priority 0, below every other B.Cu pour)
  along the 0.3 mm 3V3 track: a strip under U7's bottom via row (y 106–107.3), then a block x 164–172, y 94.6–100.3
  around U9, with a stub to the PHY 3V3 via at (174.47, 97.58). Keeps clear of the RGMII TX resistors. DRC unchanged.
- [ ] **C-02 optional:** 1V1–GND 0201 caps and 1V1 vias under the U7 top rows.

## 4. Before ordering

- [ ] ERC clean, DRC clean (`kicad-cli`, with `KICAD10_SYMBOL_DIR` set), and a netlist diff that shows only the intended changes.
- [ ] Rerun the affected review streams (`review/README.md`, "how to rerun"), at least B for the BOM/CPL.
- [ ] **B-06:** set up U7 through JLC Global Sourcing or consignment:
  - put the full Altera ordering code (speed, temperature, power suffix) in `MPN`;
  - ball A1 is at the footprint's pin-1 corner (CPL 0).
- [x] Recheck stock for all lines for 5 boards (B-11), done 2026-11-01:
  - C124 (47 µF 1210, C84494) was oversold at −540; changed to GRM32EC81C476KE15L **C162512** (16 V X6S, 48k in
    stock).
  - Still short at JLC, all sourced by the user: U5 ADS7056 (−30), U8/U19 AP61202 (0), U16/U18 AP61203 (0). Set
    them up as consigned parts.
- [ ] Order settings:
  - JLC08161H-3313 stack-up, ENIG;
  - impedance control for the MDI only (0.12/0.25 mm);
  - epoxy-filled and capped vias, 0.15 mm holes;
  - no silkscreen Gerbers.
- [ ] Check every rotation in JLC's 3D placement preview: U5, U15, the SOT-563s, U9, U1, U42, U6, RN1–RN7 and U7.
- [ ] Budget check: the estimate is about US$700–750 for parts plus assembly, against the ~600 EUR budget.

## 5. Firmware, Quartus and documents (do not block the order)

- [ ] **A1-03:** the real Quartus project uses `PIN_SWIZZLE_CH0_DQS1 = 10 8 13 14 12 11 15 9`.
- [ ] **A1-05:** the real Quartus project:
  - HPS cold reset on SDM_IO10;
  - OSC_CLK_1 at 25 MHz;
  - AS clock ≤ 100 MHz;
  - INIT_DONE on SDM_IO0.
- [ ] Confirm that VCCH_SDM on VCORE is allowed for A5EB013B (no transceivers).
- [ ] Update or delete the stale `AGILEX_POWER_CONFIG_CHECKLIST.md`, plus the stale claims in A1-06 and A2-18.

## Closed by verification (no action)

- **A2-03, JTAG half:** refuted. U1's internal 71k pull-downs hold the inputs low.
- **C-02:** downgraded to INFO. Altera's GND-stitching rule is met at 0.64–0.92 mm.
- **B-07:** downgraded to INFO. The B.Cu zone joins U15's PGND fingers; only the mask and paste are split.
- **U15 rotation (B-03):** already correct at 0.
- **B-08 holes:** 0.6 mm fits C27985219.
