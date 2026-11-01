# Stream C: fabrication, layout and SI review

Board: `agilex_3_soc.kicad_pcb` at HEAD 88d946c. The board file is byte-identical to the frozen commit 0aa9192
(`git diff --stat 0aa9192 HEAD` touches only README/.gitignore/review). Scripts, plots and raw outputs are in
`review/work/c/` (`scripts/`, `img/`, `*.txt`, `*.json`, `fab/`, `gerb/`).

## Summary

| Severity | Count | IDs |
|---|---|---|
| BLOCKER | 0 | – |
| SHOULD | 6 | C-01 … C-06 |
| INFO | 13 | C-07 … C-19 |

- **C-01 (SHOULD, highest priority):** the U15 power-ground island (B.Cu `Vcore_gnd`) reaches the GND planes through
  **one** 0.3/0.15 mm via. The whole VCORE return current (6-7 A) uses it. The TPS548A28 data sheet says at least six
  PGND vias are required.
- **C-02:** the 25 LPDDR4 vias at U7 that go from F.Cu to In5 switch the reference from GND to the In6 1V1 pour. The
  nearest 1V1-GND capacitor or 1V1 via is 7-9.7 mm away.
- **C-03:** the inner planes come to 0.18 mm from the 3.2 mm heatsink NPTHs H1/H2. JLC asks for 0.2 mm, and the
  keep-outs exist only on F/B.
- **C-04:** at U7, 6 F.Cu track-to-pad gaps are 0.075 mm and 4 more are 0.077-0.089 mm. JLC's minimum is 0.09 mm, and
  3 mil (0.0762 mm) is accepted only in BGA fan-outs.
- **C-05:** via hole to other copper is 0.175 mm in 199 track/via spots and in about 388 inner-plane antipads. JLC
  lists 0.2 mm for both.
- **C-06:** U7 decoupling departs from Altera 821801 Table 63. VCC/VCCP has no 10 µF 0402 under the BGA; the nearest
  bulk capacitor is 16 mm away.

The fabrication outputs are clean: 8 copper layers in the right order and polarity, every plane filled, a refilled copy
gives identical fills and an identical DRC, and drill counts match the board. Impedances agree with the documented field
solves. All LPDDR4 delay limits are met on the frozen copper.

What was not covered (details at the end):
- the JLC 8-layer stack-up page (it needs JavaScript);
- the heatsink drawing (not in the repo);
- the JLC online DFM (needs an upload);
- any new SI simulation (excluded by the brief).

## Findings

### C-01 — SHOULD — U15 PGND island connected to the GND planes by a single 0.15 mm via (verified; current/thermal = estimate)
- **Where:** B.Cu zone `Vcore_gnd` (GND, 44.5 mm², bbox 153.1,127.8–160.1,140.8). The following all sit on this
  island:
  - U15 PGND pads (pad "11" ×8 at x=159.51, y=133.0…135.9);
  - all VCORE bulk capacitors' GND pads: C123, C129-C132, C5-C7 (22 µF) and C124 (47 µF 1210);
  - all U15 input capacitors' GND pads: C224-C227 (2.2 µF) and C266/C267.
- The island has **exactly one** GND via, at (158.44, 132.33). Script `scripts/islands.py` lists 1 via and 0 THT pads,
  and `scripts/gndvias.py` finds no B.Cu GND track leaving the island. Plot: `img/u15w.png`. The only other GND via near
  U15 is the AGND via at (162.79, 133.00), which connects to AGND pin 2 and not to PGND.
- **Rule:** TPS548A28 data sheet (`docs/datasheets/TPS548A28_ti.pdf`, SNVSBB1D) Table 5-1 p4: "At least six PGND vias
  are required to be placed as close as possible to the PGND pins". The same requirement is in §10.1 Layout Guidelines,
  p39.
- **Why it matters:**
  - The DC return of the VCORE load (6-7 A worst case) runs from the U7 GND balls through In1/In4 into this one via.
    That is about 800 A/mm² in an 18 µm barrel, and roughly ten times the usual IPC rating of a 0.15 mm via.
  - The via adds about 1.5-3 mΩ plus plane spreading resistance. Remote sense compensates the DC part.
  - The via's inductance sits in series with the whole VCORE bulk capacitor bank (8 × 22 µF + 47 µF) as U7 sees it.
  - U15's heat has only one via path into the inner planes.
  - A closed-form conduction estimate gives only a few kelvin of via heating, so the board probably works. That is why
    this is SHOULD and not BLOCKER. It is still a single point of failure carrying the core current.
- **Fix (copper only, no BOM change):**
  - Add 8 or more 0.3/0.15 mm GND vias into `Vcore_gnd`: along x≈158.7-159.0 between the output-capacitor GND pads and
    the PGND pads, and in the free area at y 137-140.5 (x 153-157).
  - Add 2 or more next to the input capacitors' GND pads (x≈159.7, y 137-140).

### C-02 — SHOULD — LPDDR4 vias at U7 change reference from GND to the In6 1V1 pour with no 1V1/GND transfer path nearby (verified geometry; SI impact = assumption)
- **Where:** 25 LPDDR4 vias in U7 pads that go from F.Cu to In5, along the top rows of U7 (y≈101-106, x≈146-167).
  Examples:
  - ca3 (165.24, 101.26)
  - ca0 (163.95, 101.90)
  - cke (162.64, 101.26)
  - dq8 (163.65, 103.31)
  - dq13 (163.00, 105.26)
- **What changes at the via:** the F.Cu ball references In1 GND. In5 references In6 at 0.1 mm, here the `lpddr1v1` pour
  (1V1), and In4 GND at 0.357 mm.
- **Distances** (`scripts/v11.py`):
  - from these vias, the nearest 1V1-GND capacitor is 7.2 mm away (median) and up to 9.65 mm (C218, C74, C89);
  - the nearest 1V1 via (U7 VCCIO_PIO_3A) is 7-9 mm away;
  - at the U12 end the same transition has a capacitor within 1.3 mm (median, maximum 2.7 mm). That end is fine.
- **Rules:**
  - Altera 821801 §3.2 p10: signals refer to solid planes, ground reference preferred.
  - 821801 §6.1.3 p48: keep return-path stitching within 80 mil (2.03 mm) of signal transition vias.
- The IBIS simulation (`sim/lpddr4_si/README.md`, "What is modelled") uses uncoupled lines with lumped vias. It does not
  include return-path inductance, SSO or crosstalk, so these 25 transitions are not covered by it.
- **Fix:** place 0201 1V1-GND capacitors at the U7 north edge, B.Cu y≈96-100 between U12 and U7, close to the In5 via
  columns. The alternative is to accept the risk explicitly.

### C-03 — SHOULD — Heatsink holes H1/H2: inner planes 0.18 mm from the NPTH edge (verified)
- **Where:** H1 (171.44, 127.01) and H2 (141.59, 97.16), both 3.2 mm NPTH (`scripts/npth.py`, refilled copy). Copper
  comes to 0.18 mm from the hole edge on:
  - In1 GND, In3 1V8, In4 GND and In6 1V2 at H1;
  - In1 GND, In4 GND and In6 1V1 at H2.
- The rule areas `heatsink_pin_H1/H2` (6 × 6 mm: no tracks, vias or zone fills) exist only on F.Cu and B.Cu. On F/B the
  nearest copper is 1.57-2.44 mm from the hole edge.
- **Rule:** JLC capabilities page, Traces table, "NPTH to Track 0.2mm". The board uses the generic hole clearance of
  0.175 mm for NPTHs.
- **Why it matters:** the push pin and spring load the hole wall, and the hole position tolerance is ±0.075 mm (JLC,
  Drilling table). That leaves 0.105 mm of FR-4 between the hole wall and 1.8/1.2/1.1 V planes.
- **Fix:** make the two rule areas "all copper layers", or give the NPTHs a ≥0.5 mm clearance, then refill.

### C-04 — SHOULD — U7 F.Cu track-to-pad clearances below JLC's minimum (verified)
- Strict DRC probe on a copy, with clearance ≥0.09 mm for tracks inside the U7 courtyard against pads/vias
  (`drc_strict.json`), found 10 spots:
  - 0.075 mm, 6 spots:
    - dq2 vs B45 and A45 (158.09, 101.26/101.91)
    - dq4 vs A60 (161.99, 101.26)
    - dq0 vs B73, D71 and A74 (165.3-166.7, 101.3-102.6)
  - 0.0766 mm: dq4 vs A60
  - 0.0831 mm: dq16 vs A10 (148.34, 101.26)
  - 0.0849 / 0.0888 mm: dq0 vs A73/A74
- All are row A/B escapes on F.Cu, next to the larger corner pads (A1-B notes 0.355/0.33 mm corner pads).
- **Rule:** JLC capabilities page, Traces table:
  - "Multilayer: 0.09/0.09 mm. 3 mil is acceptable in BGA fan-outs";
  - BGA row "BGA pad to trace clearance ≥ 0.1 mm (min. 0.09 mm for multilayer boards)";
  - "Pad to track clearance … Min. 0.09 mm locally for BGA pads".
  - 0.075 mm is below even the 3 mil (0.0762 mm) BGA allowance.
- The `.kicad_dru` (`lpddr_bga_clearance` note) already records this as known. The pads involved are mostly
  unconnected or GND, so a short only costs a spare ball or shorts to GND.
- **Fix:** move these 10 short segments to the middle of their channels (≥0.09 mm), or get JLC's written acceptance.

### C-05 — SHOULD — Via hole to copper 0.175 mm vs JLC's 0.2 mm (verified; JLC's measurement basis is ambiguous)
- **Tracks:** a strict DRC probe with `hole_clearance` 0.2 mm (`drc_strict.json`) reports 199 track/via spots at
  0.175-0.199 mm (76 at 0.1750 mm), all over the board. Examples:
  - XTAL vias (178.17/178.57, 96.06);
  - eMMC (169.99, 114.73);
  - LPDDR4 under U7/U12.
- **Planes:** `scripts/holeclr.py` finds about 388 inner-plane antipads where plane copper is 0.175-0.18 mm from the via
  drill. That is the 0.3 mm via pad plus 0.1 mm zone clearance.
- **Rule:** JLC capabilities page, Traces table: "Via hole to Track 0.2mm" and "Inner layer via hole to copper clearance
  0.2mm".
- JLC's own minimum via (0.15/0.25 mm) plus its 0.09 mm spacing gives 0.14 mm from hole edge to track, so the 0.2 mm
  figure may be measured differently. The `.kicad_dru` header already flags this.
- **Fix:**
  - Run JLC's online DFM on `review/work/c/fab/agilex_3_soc_gerbers.zip` before paying.
  - The 388 plane antipads can be widened cheaply by raising zone-to-via clearance on In1/In3/In4/In6 to 0.13 mm
    (antipad 0.2 mm from the drill). Track spots in the BGAs cannot move easily.

### C-06 — SHOULD — U7 board decoupling vs Altera 821801 Table 63 (verified placement; values belong to A2/B)
- **Rule:** 821801 Table 63, p121-122 (A5E013B B23B). Altera requires a PDN transient simulation if this is not followed
  (§10.2.4, p120).

| Rail (board net) | Altera, bottom side / periphery | On the board (`scripts/decap.py`) |
|---|---|---|
| VCC/VCCP merged (VCORE) | 4 × 10 µF 0402 under the BGA | 25 × 100 nF 0201 under U7; 8 × 22 µF 0402 + 1 × 47 µF 1210 at 16-25 mm from the U7 centre (C130 at 157.13,128.41 is the nearest). No 10 µF-class capacitor under U7. |
| VCCL_HPS, VCCL_SDM, VCCH_SDM … (also on VCORE) | 1-2 × 1 µF 0201 each, VCCL_HPS 2 × 10 µF + 22 µF | covered only by the 100 nF set above |
| VCCPT/VCCPT_HVIO/VCCIO_HPS/VCCIO_SDM … (1V8) | 4.7 µF / 1 µF 0201 + 10 µF 0402 | 11 × 100 nF 0201 + 1 × 22 µF (C102) under U7; 22 µF at 13-16 mm |
| VCCIO_PIO_3A (1V1) | 2 × 4.7 µF 0201 + 10 µF 0402 per bank | 4 × 100 nF 0201 under U7; bulk at 26 mm |
| VCCRCORE, VCCIO_PIO_2A, VCCIO_PIO_SDM (1V2) | 1 µF / 4.7 µF 0201 + 10 µF 0402 | 6 × 100 nF 0201 under U7; 22 µF at 14+ mm |
| VCCIO_HVIO 6A-6H (3V3) | 1 µF 0201 per bank | 10 × 100 nF 0201 under U7 |

- The 0201 values can change without touching the copper: same footprint, and 1 µF 0201 (C272877) is already in the
  BOM.
- The layout part is the VCORE 4 × 10 µF 0402, which needs 0402 sites under or right next to U7. Today the closest bulk
  sits beyond the U15 output capacitors.
- 821801 p124 also recommends a bottom-layer VCCL flood. The board has one (`corezone` B.Cu, 149.5 mm²).

### C-07 — INFO — U15 switch node and input capacitor placement (verified; heating = estimate)
- **SW:** U15 SW pad 20 (160.56, 133.05) to L1 pad 1 (161.14, 130.36) is a 0.3 mm track. About 0.9 mm of it is outside
  the pads. There is no SW copper pour.
  - Estimate: 1.5 mΩ, about 70 mW at 7 A, a few kelvin of local heating.
  - TI SNVSBB1D §10.1 p39: the switch node "must be as short and wide as possible". Widening it to the pad and inductor
    width costs nothing.
- **VIN:** the input capacitors are 2.2 µF 0402 (C227/C226/C225/C224), 0.9-3.9 mm below the VIN pads. TI §10.1 asks for
  a 1 µF 0402 right at VIN pins 21 and 10.
- The two VIN pads are joined by a 0.1 mm track (161.16, 133.05-135.35) plus the 5V0 zone.

### C-08 — INFO — CKE on In5 runs along the edge of the In6 PHY GND island (verified)
- `/IOBANK 3/cke` on In5 at x=172.39, y 89.6-98.1 runs over `phy_gnd_in6`, about 0.05 mm inside its edge, for about
  8 mm. It crosses the 1V1→GND split at (171.93, 98.12) and (172.39, 90.01).
- In4 GND below is continuous. CKE is quasi-static.
- **Rule:** 821801 §3.2 p10 (do not cross split planes). INFO only.

### C-09 — INFO — eMMC on In5: split crossings and distant stitching (verified; already simulated)
- **Split crossings:**
  - In6 1V2→3V3 under U11 at x≈181.8: sd_d3, sd_d6, sd_d7, emmc_rst_n, sd_clk.
  - sd_cmd_hps 1V2→VCORE→1V2 under U7 at (162.91, 111.50) and (163.39, 109.88).
- **Stitching:** 40 eMMC vias change reference (GND→In6 1V2/3V3). 18 have no GND via within 1 mm, and 7 have none within
  2.03 mm:
  - sd_d6 (173.71, 113.13) 3.23 mm
  - sd_d5_hps (173.07, 111.56) 3.16 mm
  - sd_d2_hps 2.74 mm
  - sd_d0_hps 2.71 mm
  - emmc_ds_hps 2.56 mm
  - sd_d6_hps 2.56 mm
  - sd_clk (172.21, 112.01) 2.20 mm
- `sim/emmc_si/README.md` modelled exactly this (1V2/3V3 split, 0.5-4 nH per change). With the 33 Ω series resistors
  R280-R290 it passes. Accepted.

### C-10 — INFO — RGMII: reference changes and stitching (verified)
- 17 RGMII vias change reference. 11 have no GND via within 1 mm, and 5 have none within 2.03 mm (821801 §6.1.3 p48):
  - eth_rxd0 (173.22, 92.83) 3.15 mm
  - eth_rx_dv (173.01, 93.48) 2.72 mm
  - U10-TXD2 (169.97, 103.18) 2.66 mm, GND→In6 1V2
  - eth_rxd1 (173.22, 92.13) 2.51 mm
  - U10-TXD0 (169.42, 101.71) 2.05 mm, GND→In6 1V1
- 0.10 mm lines are about 54 Ω (In2) and 59 Ω (F.Cu) against the usual 50 Ω. The routes are short (≈100 ps), so this
  is negligible at 125 MHz DDR.

### C-11 — INFO — Clocks and QSPI (verified)
- `/clk100` (Y4 100 MHz) on B.Cu crosses In6 1V1→1V8 at (148.90, 105.80). It is about 1 mm of a 2.7 mm route.
- The refclk pair `iob3A_refclk_P/N` (B.Cu, 0.10 mm, uncoupled, 58.6 Ω) runs entirely over In6 1V1, the bank 3A VCCIO.
  That is fine; `sim/refclk_si` covers it and requires RT_OFF.
- QSPI vias: qspi_D3 (179.99, 135.68) has its nearest GND via 2.24 mm away, and qspi_D2 (178.99, 135.68) 1.41 mm.
  QSPI otherwise stays on In2 over In1 GND.

### C-12 — INFO — LPDDR4 spacing vs Altera Tables 8/9 (verified; DRC warning-level rules pass)
- Scan outside the U7/U12 courtyards (`scripts/xtalk.py`), h = 0.1 mm, against 821801 Tables 8/9 p53-54:
  - **F.Cu DQ-DQ within a byte, microstrip 3h = 0.3 mm (Table 9):** dq20/dq21 0.26-0.28 mm over 3.5 mm (153.2-153.6,
    95.6-98.6), and dq2/dq3 0.27-0.29 mm over 2.1 mm (158.6-159.0, 96.6-97.2).
  - **Byte to byte, 3h:** dm0/dm1 on In2, 0.26-0.28 mm over 1.9 mm (159.3-159.5, 95.9-98.5).
  - **DQS to DQ, 3h (Table 8, M segment):** dqs2_N/dm2 on In2, 0.26-0.28 mm over 0.7 mm (155.3-155.7, 96.4), and
    dqs1_N/dm1 0.29 mm.
  - **CA within group, 2h:** ca4/ca5 on In5, 0.185 mm over 0.2 mm (164.97, 99.56).
- All are in the 4 mm gap between U12 and U7. The `.kicad_dru` applies 0.2 mm to DQS-DQ and to microstrip DQ-DQ, where
  Tables 8/9 ask for 3h.
- The deliberate 55/59 Ω trace impedance (Altera target 40 Ω SL / 45 Ω US, Tables 8/9) is justified by
  `sim/lpddr4_si/README.md` ("How narrow…", routed results 2026-10-31). It is noted here, not counted as a finding.

### C-13 — INFO — LPDDR4 delay report: frozen copper passes, committed report slightly stale (verified)
- `tools/lpddr4_delay/delay_report.py` was run once on the work copy; it is a single KiCad DRC probe, no simulation.
  Output: `review/work/c/delay_report.md`. Result: "all limits met".
- Byte 0 differs from the committed `LPDDR4_DELAY_REPORT.md`: dq0 −6.9 ps (was −4.5) and dq7 −1.6 ps (was −4.5). The
  spread is 6.9 ps, against a 10 ps target and the −68…+43 ps limit of Table 10 p55. CA, CK and DQS are unchanged.
- A1-03: the package-delay table in `LPDDR4_SWIZZLE_PLAN.md` (line 337) still lists dq9 = G56 108 and dq15 = E56 107.
  The board pads carry the correct values (E56 = dq9, die_delay 107; G56 = dq15, die_delay 108), and KiCad's tuning uses
  the pad values. The copper is right; only the document is stale (1 ps either way).

### C-14 — INFO — 1V8 tracks cut the In4 GND plane under U7 (verified)
- About 10 mm of 0.1 mm 1V8 track on In4 at (153.7-162.0, 110.8-119.0), plus a VCORE stub at (160.49, 117.77), slot the
  In4 GND plane under U7. In1 GND is intact there.
- The return-path scan found no In5/In3 high-speed trace crossing these slots: the LPDDR4 In5 escapes are at y≤106 and
  the eMMC In5 traces at x≥162.9.

### C-15 — INFO — Small regulators' ground connections (verified)
- U8 (3V3) and U18 (1V8) GND pin 2 have no GND via within 2.5 mm. U8 reaches GND vias at about 2.6 mm through 0.2 mm
  tracks.
- `1v1gnd` (U16, 1V1) has 1 via; `1v8gndflood` has 3.
- These are AP61202 parts (2 A max) at estimated loads of 1 A or less, so this is acceptable. One or two more vias per
  regulator would be cheap.

### C-16 — INFO — Remote sense routed as a pair (A1 request) (verified)
- `/soc_power/vcoresense_P` (U7.BN46 VCCLSENSE) and `/pwr_vcore/vcoresense_N` (U7.BN44 GNDSENSE → U15.6 VSNS−) run
  together on In2 over In1 GND:
  - 0.10 mm tracks, about 0.15 mm gap, 26.0 / 29.3 mm long;
  - 0.68 mm apart inside the U7 ball field;
  - separate for the last 1-2 mm at R2/C198/C199.
- This meets 813266 p25 ("route these connections as differential pair traces").
- The pair passes under L1 with In4 GND between them and L1 on B.Cu.
- TI §10.1 p39 suggests ≥12 mil for sense traces. 0.10 mm is acceptable because the traces carry no current.

### C-17 — INFO — Mechanical: heatsink and connectors (partly verified)
- **Heatsink holes:** H1 and H2 are diagonal at ±14.93 mm from the U7 centre (board note on User.Comments). The
  Wakefield 960-23-33-D-AB-0 drawing is not in the repo, so the hole pitch, pin grip range and spring diameter could
  not be checked.
- **Parts near H1/H2:**
  - U42 (B.Cu) has its courtyard edge 3.24 mm from the H1 centre (y = 123.77 vs 127.01), just outside the 6 mm
    keep-out square. The rule area does not disallow footprints in any case.
  - The bottom-side spring/clip needs a clear radius; check it against the drawing.
- The older note that L1 sits in H1's keep-out is **resolved**: L1's body is more than 5 mm from H1, and L1 is at
  158.27-164.02 × 124.58-131.63.
- **Board:** no mounting holes other than H1/H2. The outline is a plain 76.000 × 65.125 mm rectangle with no slots.
- **Edges:**
  - J9 (RJ45) overhangs the right edge by 4.9 mm (bbox to x=204.9). Not checked against the HR911130A drawing.
  - J3 pins 37/38 are 0.41 mm from the edge (known, excluded; still ≥0.2 mm for JLC).

### C-18 — INFO — Ordering notes (verified against JLC capabilities page, 2026-11-01)
- **Stack-up:** select JLC08161H-3313, 1.6 mm, outer 1 oz, inner 0.5 oz, ENIG. ENIG is needed for the 0201s and BGAs,
  and HASL is not offered for 6+ layers.
- **Impedance control** (JLC ±10%):
  - The only line drawn to a standard target is the MDI: 100 Ω differential on L1, 0.12/0.25 mm. JLC's own calculator
    gives 0.1278 mm for this (`LPDDR4_DELAY_MATCHING.md:52`), so 0.12 mm is about +3 Ω.
  - Tell JLC that the 0.10 mm lines (55/59 Ω by design) must not be resized.
- **Vias:** 0.3/0.15 mm. The 0.15 mm hole "will cost more, select the via size option".
  - Via-in-pad: 417 vias in U7 pads, 162 in U12, 33 in U11, 9 in U2, and about 100 bottom-side 0201 capacitors sitting
    on vias.
  - Select "Epoxy Filled & Capped" (JLC default for 6+ layers; board setup has filling = yes, capping = yes).
  - Annular ring 0.075 mm (≥0.05; "0.15 mm larger preferred" is met). Aspect ratio 10.7:1.
- **Silkscreen:** the Gerber zip contains F/B silkscreen with content. If the boards are to be ordered without silk
  (project memory), drop those two files or accept that JLC prints them.
- **J3 annular ring:** 38 pads with 0.6 mm drill on 0.9 mm pads give 0.15 mm, JLC's absolute minimum for multilayer
  (0.20 recommended).

### C-19 — INFO — Pads smaller than JLC's listed minimum SMD pad (verified; footprints are stream B)
- 169 SMD pads have a short side under 0.25 mm (JLC "Minimum SMD pad: 0.25mm × 0.25mm", Traces table). Examples: U15
  pins at 0.20 mm, U10 QFN pins.
- The SMD pad-to-pad spacing probe (≥0.15 mm between different nets) gave 0 violations.

## Coverage (checked and found correct, with the evidence)

**Stack-up**
- The board setup has 8 layers: F 35 µm / 3313 0.0994 / In1 15.2 µm / core 0.1 / In2 / 2116×3 0.3568 / In3 / core 0.3 /
  In4 / 2116×3 0.3568 / In5 / core 0.1 / In6 / 3313 0.0994 / B 35 µm. Total 1.574 mm of copper and dielectric, plus mask
  (setup 1.6 mm).
- Er 4.1 (3313) and 4.16 (2116) match JLC's capabilities page ("FR-4 Dielectric Constants"). The core thicknesses
  0.10/0.30 mm appear in JLC's core list ("0.10mm/0.30mm H/HOZ without copper").
- The ordered layer function is In1/In4 GND, In3/In6 split power, and In2/In5/F/B signal.

**Impedance** (field solve from the repo vs an IPC-2141 closed-form check)

| Line | Field solve | Closed form |
|---|---|---|
| F.Cu 0.10 mm | 58.6 Ω | 61 Ω without mask, about 59 Ω with mask |
| In2/In5 0.10 mm | 53.8-55.3 Ω | asymmetric stripline 52.6 Ω |
| MDI 0.12/0.25 mm on F.Cu | 100.8 Ω diff | about 103 Ω |
| LPDDR4 pairs 0.10/0.10 mm on In2/In5 | 87 Ω diff | 87 Ω |

- All agree within 5%.
- All 95 MDI segments are 0.12 mm on F.Cu over In1 GND; the gap is enforced by error-level DRC (0.2-0.3 mm), which
  passes.
- The LPDDR4, QSPI, eMMC, RGMII and refclk widths are all 0.10 mm.
- JLC's ±20% width tolerance moves Z by about ±4 Ω.

**Manufacturing limits** (full-board scan, `feat.txt`)
- Tracks: minimum 0.10 mm (≥0.09).
- Clearance: board minimum 0.09 mm, except C-04.
- Vias: 859, all through, 0.3/0.15 mm.
- PTH drills: 0.6-1.63 mm. NPTH: 3.2/3.25 mm (≥0.5). No slots, plated or not.
- Via-via hole spacing: minimum 0.251 mm (≥0.2). Nothing under 0.25 mm anywhere. PTH pad holes ≥0.62 mm apart (J6,
  ≥0.45).
- PTH annular ring ≥0.15 mm.
- Copper to edge ≥0.41 mm (J3, excluded) and 0.5 mm elsewhere (≥0.2).
- SMD pad-to-pad spacing ≥0.15 mm (strict DRC probe: 0 violations).
- Mask: 1:1 expansion, allowed since JLC's June 2025 LDI upgrade.
- Board size: within limits.

**Fabrication outputs**
- `tools/jlc/fab_outputs.sh` was run on a refilled copy → `review/work/c/fab/`.
- Gerber job: 8 copper layers L1-L8 in the order F, In1…In6, B, all Positive; masks Negative; Profile is one rectangle
  76.0 × 65.125 mm; thickness 1.6 mm, ENIG.
- Drill files:
  - PTH: 946 hits over 7 tools (0.15 mm × 859, 0.6 mm × 38, 0.65 mm × 6, 0.89 mm × 10, 1.0 mm × 27, 1.02 mm × 4,
    1.63 mm × 2).
  - NPTH: 4 hits (3.2 mm × 2, 3.25 mm × 2). Identical to the board scan.
- Every plane zone is filled. The refill on the copy changed none of the 23 zone fill areas (Δ = 0.000 mm²).
- DRC with `--severity-all` and parity, committed copy vs refilled copy: identical. That is 3 warnings (2 J3 edge
  exclusions and 1 J3 lib mismatch), 0 unconnected, 0 parity, and no new items.

**Return paths** (`scripts/retpath.py`, 0.05 mm sampling of every segment; centre and both edges +0.05 mm on the
adjacent plane; own-via antipads excluded)
- F.Cu: LPDDR4, MDI, RGMII and sense are all over In1 GND. Outside courtyards there are only antipad edge touches of
  ≤0.45 mm.
- In2: LPDDR4, QSPI, eMMC, RGMII and sense are all over In1 GND.
- In5: LPDDR4 is only over In6 1V1, apart from C-08. eMMC is over 1V2/3V3 (C-09).
- B.Cu: LPDDR4 CA branches and refclk are over In6 1V1.
- The only reference-net changes along a trace are those listed in C-08, C-09 and C-11.
- Stitching: all 62 LPDDR4 plane-changing vias have a GND via within 1.94 mm (inside 821801's 2.03 mm). The REFCLK vias
  are within 0.92 mm.

**Power**
- VCORE copper from L1 to U7:
  - B.Cu and In6 are each about 8.1 mm wide for y 119-127, and 2.5-8 mm wide inside the ball field.
  - 50 via-in-pad VCORE ball vias plus 5 B.Cu↔In6 vias at the output capacitors.
  - IR estimate: about 0.7 mΩ (≈5 mV at 7 A), inside the remote-sense loop.
- Other rails, vias from regulator to plane:
  - 1V1: 3 at L5, then 58 in the In6 pour;
  - 1V8: 2 at L3, then 49 on In3 and 9 on In6;
  - 1V2: 2 + 11 + 4;
  - 3V3: 21 + 19;
  - 5V0: B.Cu flood of 651 mm² fed from J4/J6.
  - All are adequate for loads at or under the 2 A converters' rating.
- Zone connections at U15 are solid (`Vcore_gnd`/`corezone` pad connection FULL).
- All copper islands are connected (`phy_gnd_bcu` sub-islands reach GND through tracks or pads).

**EMIF**
- DRC pair, skew, uncoupled, delay-window and 2h/3h warning rules pass.
- `delay_report.py` result: all limits met.
- Layer rules (no LPDDR4 on In1/In3/In4/In6) are enforced and pass.

**Thermal and mechanical**
- U7 has 237 GND balls with via-in-pad to In1/In4.
- U15's heat path is limited by C-01.
- H1/H2 F/B keep-outs are clear of tracks and vias. L1 is outside the H1 keep-out.

## Not checked / could not check
- **JLC 8-layer stack-up table** (`jlcpcb.com/impedance`): needs JavaScript. The board's thicknesses come from the repo
  notes, and only Er and core thicknesses were cross-checked against JLC's pages.
- **JLC online DFM:** needs an upload. Recommended for C-04 and C-05.
- **Heatsink (Wakefield 960-23-33-D-AB-0):** no drawing. Hole pitch, pin grip, spring diameter and thermal interface
  were not checked. U7 power and thermal budget were not checked.
- **SI:** no new simulation, per the brief. The return-path inductance and SSO in C-02, and the crosstalk in C-12, are
  not quantified.
- **Land patterns and BOM values:** U15 footprint, decoupling capacitor values and the 4-pad 0201 footprints belong to
  stream B/A2.
- **J9 RJ45 overhang:** not compared with the HR911130A drawing.

## For other streams
- **B:** U15 TPS548A28 (RWW) uses footprint `agilex_lib:TDA38812`. Check the pad map: VIN pin 21 appears as a second pad
  "10", PGND 11-18 as eight pads "11". Several 0201 capacitors (e.g. C62) have 4 pads, 2 of them unnumbered. 169 SMD
  pads are under 0.25 mm (C-19).
- **A2/B:** U7 decoupling values against 821801 Table 63 (C-06): 100 nF 0201 where 1-4.7 µF 0201 and 10 µF 0402 are
  recommended.
- **A2:** VCCPLL_SDM, VCCADC and VCCPLL1/2_HPS are on the 1V8 net, and VCCPLLDIG_SDM/HPS are on VCORE. Table 63 lists
  "LC filter capacitors" for these; check whether the filters exist in the schematic.
