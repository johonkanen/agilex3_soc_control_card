# Verification v3_layout: copper, fabrication and decoupling claims (C-01 ... C-06)

Board state: `agilex_3_soc.kicad_pcb` as committed at `ceb2746` (the same file as at `review/inputs/COMMIT`; the PCB has
no changes in the working tree). Measured with pcbnew 10.0.7 (KiCad AppImage) on the board as stored, and on a refilled
copy in `review/work/v3_layout/proj/`. Scripts are in `review/work/v3_layout/` (`c01*.py` ... `c06*.py`, `geom.py`).
One kicad-cli DRC was run on the unmodified copy: 3 warnings (J3 edge clearance x2 and a library mismatch, all known),
0 unconnected. A second DRC with zone refill was run on the copy with two test rules (C-03/C-05 fix, below).

JLC capabilities page: https://jlcpcb.com/capabilities/pcb-capabilities, fetched 2026-11-01 (text copy in
`review/work/v3_layout/jlcpage/cap.txt`). Lines quoted below are exact.

Summary: 6 claims checked. 1 CONFIRMED, 5 CONFIRMED WITH CORRECTION, 0 REFUTED. My severities: 0 BLOCKER, 5 SHOULD,
1 INFO (C-02). Every fix is a copper change, a rule change or a value swap on existing pads. None needs board space
except the optional 10 uF 0402 parts in C-06.

---

## C-01: U15 PGND island has one via to the GND planes

**Verdict: CONFIRMED** (small correction: the via carries about 83 % of the load current, not all of it).

**Severity: SHOULD.** TI says six PGND vias are "required". One 0.15 mm via survives the current thermally, but it
puts PGND about 1.4 mOhm and roughly 0.5 nH away from the planes. It also leaves the IC (mounted on B.Cu) with almost no
thermal path into the planes. The fix is copper only.

**Evidence**
- Zone `Vcore_gnd` (net GND, B.Cu only, priority 6). Its fill is one polygon of 44.5 mm2, bbox (153.05, 127.85) -
  (160.05, 140.85). A refill gives the same 44.5 mm2.
- Everything that touches that fill: one GND via, 0.3/0.15 mm, at (158.442, 132.334), F.Cu-B.Cu. It connects to
  `gndflood` on In1 and In4. There are no GND tracks, no other GND zone, no through-hole pads and no other via.
- SMD pads on the island: U15 pad 11, all eight PGND pads (159.51, 133.0-135.9). The GND pads of the VCORE output caps
  C5, C6, C7, C123, C129, C130, C131, C132 (22 uF 0402) and C124 (47 uF 1210). The GND pads of the 5V0 input caps C224-C227
  (2.2 uF) and C266/C267 (1 uF).
- U15 AGND (pad 2, 162.21, 133.0) has its own GND via at (162.79, 133.00). It is not on the island.
- TPS548A28 data sheet SNVSBB1D (docs/datasheets/TPS548A28_ti.pdf), Table 5-1 (p4): "At least six PGND vias are
  required to be placed as close as possible to the PGND pins". Section 10.1 (p39): "At least six PGND vias are required
  to be placed as close as possible to the PGND pins (pin 11 to pin 15). This minimizes parasitic impedance and also
  lowers thermal resistance."
- Current (assumption; the figures come from the repo checklist, not from a power estimate I ran):
  AGILEX_POWER_CONFIG_CHECKLIST.md gives VCORE 4.75 A (3.9 A static) and 6-7 A with a full fabric design. By KCL on the
  island, the via carries I_out - I_in. I_in = 0.753 V x I_out / (5 V x 0.88) = 0.17 x I_out. So the via carries
  **3.9-5.8 A DC**.
  - The switching loops close on the island: input caps to PGND, and inductor ripple through the output caps. The via
    carries the DC and the load-step current, not the 1 MHz pulses.
- Via estimate: JLC plating "Average Hole Plating Thickness 18μm". The barrel section is about 7.5e-3 mm2, which gives
  about 2.3 mOhm/mm. From B.Cu to In4 is 0.6 mm (stack-up), so about 1.4 mOhm.
  - At 5.8 A that is about 8 mV and 47 mW.
  - Barrel temperature rise, closed form with both ends held by the planes: P x R_th / 8 = about 1-2 K. So the via
    will not fuse.
  - The real costs: PGND sits about 0.5 nH from the planes (AGND is on the planes, so load steps make PGND-AGND bounce),
    and the B.Cu island is U15's only heat spreader.

**Fix (copper only).** Add at least six 0.3/0.15 mm GND vias on the island, in a column next to the PGND pad ends at
x = 158.85, y = 132.8 / 133.6 / 134.4 / 135.2 / 136.0 / 136.8.
- I checked every site against other-net copper on all layers. The minimum gap is 0.46 mm, except (158.85, 132.8), which
  is 0.15 mm from U15.19 (tda_vcc).
- Further clear sites near the output caps: (158.45, 128.4 / 130.4 / 131.6). Near the input caps: (158.05, 138.4 / 139.6).
- The vias pass the In6 VCORE pour (`corezone_in6`) through antipads.
- Refill, then confirm with DRC. With 8-10 vias the via resistance drops below 0.2 mOhm.

---

## C-02: LPDDR4 vias at U7's top rows, F.Cu -> In5, 1V1-referenced

**Verdict: CONFIRMED WITH CORRECTION.** The geometry is as stated, but the cited Altera rule is met. 821801 6.1.3 asks
for *ground* stitching vias within 80 mil, and there is a GND via 0.64-0.92 mm from every one of the 25 vias. The
distances in the claim are also off: the nearest 1V1 via is 4.3-9.1 mm away and the nearest 1V1-GND capacitor 3.9-9.7 mm.

**Severity: INFO.** No Altera guideline is violated, and the In5-under-1V1 layer plan is deliberate (the
`lpddr_layers` comment in the .kicad_dru). The return path through the 1V1 pour costs some margin, which the existing
SI simulation did not model.

**Evidence**
- 25 LPDDR4 vias are via-in-pad on U7 balls with their trace on In5. Nets: dq8-dq15, dq24-dq31, ck_P/N, cke, ca0-ca5.
  They sit in rows y = 101.25-105.26, x = 152.50-165.24.
- Nearest GND via: 0.64-0.92 mm (the GND-ball via-in-pads).
- 821801 section 6.1.3, p48 (exact): "For better return path and signal integrity performance, keep the distance between
  the ground stitching vias and signal transition vias within 80 mil." The chapter has no rule about power-plane
  references for EMIF.
- Stack-up: In5 is 0.100 mm from In6 and 0.357 mm from In4 (GND). The In5 runs of these 25 nets total 611 mm over In6
  zone `lpddr1v1` (1V1), 8 mm over In6 GND, and 22 mm where the sample points fell in In6 gaps or antipads.
  - Closed-form estimate: about 70-80 % of the return current flows on the 1V1 pour.
- Nearest 1V1 via: 4.27-9.14 mm. These are U7's VCCIO_PIO_3A 1V1 ball vias, which are a legitimate return for the
  driver's pull-up current.
- Nearest 1V1-GND capacitor: 3.93-9.65 mm, either C220/C221 under U7 (155.6-156.0, 108.9-110.1) or the U12 group at
  y = 86-94.
- B.Cu has no GND pour under U7's top rows, so In6-to-GND plane capacitance does not help there.

**Fix (optional).** Add 2-4 100 nF 0201 caps (C190183, already on the BOM) from 1V1 to GND on B.Cu under the top rows.
Each needs a new 1V1 via into the In6 pour.
- An automated all-layer search found only a few free through-via sites: (155.7, 102.4-103.2), (156.0-156.4, 100.3-100.8)
  and (162.1-162.5, 106.2-106.7). This would be hand-placed copper plus new parts in tight space.
- I would not hold the order for it.

---

## C-03: Inner-plane copper 0.18 mm from the H1/H2 NPTH edge

**Verdict: CONFIRMED WITH CORRECTION.** The measured gap is exactly 0.175 mm. That is the board hole-clearance setting:
the zones keep no extra margin from NPTH, because the rule areas `heatsink_pin_H1/H2` (6 x 6 mm) cover only F.Cu and B.Cu.

**Severity: SHOULD.** It is 0.025 mm below JLC's listed 0.2 mm. The electrical risk is low:
- The hole is not plated, so a drill that grazes copper connects nothing.
- A metal push pin could still touch plane copper exposed in the wall. At H1, In1 GND, In3 1V8, In4 GND and In6 1V2 are
  all at 0.175 mm.
- JLC states "Hole Position Tolerance ±0.075 mm".

The fix is one rule.

**Evidence**
- H1 (171.44, 127.01) and H2 (141.59, 97.16): NPTH, 3.2 mm, no net.
- Hole edge to copper:
  - H1: In1 GND 0.175, In3 1V8 0.175, In4 GND 0.175, In6 1V2 0.175.
  - H2: In1 GND 0.175, In4 GND 0.175, In6 1V1 0.175.
  - F.Cu, B.Cu, In2 and In5: 1.27 mm or more.
- These are the only NPTHs on the board with copper under 0.2 mm. J9's 3.25 mm holes are at 1.6 mm or more.
- JLC, exact: "NPTH to Track" / "0.2mm". Also: "NPTH pad annular ring ≧0.45mm Recommended 0.45 mm or more. This is to
  allow a 0.2 mm ring of copper to be removed around the hole for the sealing film to attach." (That line is about
  NPTH pads, which H1/H2 do not have.)

**Would it pass JLC DFM as-is?** Probably with a warning, or an engineering question that delays the order. It is
unlikely to be refused, because JLC routinely pulls plane copper back around NPTH.

**Fix (rule plus refill, copper only).** Add to `agilex_3_soc.kicad_dru`:
```
(rule "jlc_npth_clear"
	(condition "A.Pad_Type == 'NPTH, mechanical' || B.Pad_Type == 'NPTH, mechanical'")
	(constraint hole_clearance (min 0.3mm)))
```
Then refill. I tested it on the copy (`review/work/v3_layout/proj`, `kicad-cli pcb drc --refill-zones --save-board`):
H1 and H2 go to 0.300 mm on every inner layer, DRC is unchanged (3 known warnings) and there are 0 unconnected items.
Extending the rule areas to all copper layers would also work, but it cuts 6 x 6 mm holes in the planes.

---

## C-04: F.Cu track-to-pad gaps under 0.09 mm at U7

**Verdict: CONFIRMED WITH CORRECTION.**
- 8 track/pad pairs (13 segment instances) are below 0.09 mm. **6 pairs are at 0.075 mm, all dq0, dq2 or dq4.**
- dq16 is not at 0.075: its worst gap is 0.0831 mm, to A10.
- 0.075 mm is 2.95 mil, 1.2 um under 3 mil (0.0762).
- The `.kicad_dru` comment is stale: the U7 pads are 0.355 mm round, not 0.4 mm. So a centred 0.1 mm track has
  0.0975 mm per side, and all the sub-0.09 gaps come from off-centre segments.

**Severity: SHOULD.** It is below JLC's BGA pad-to-trace figure, and the fix is a small nudge of 8 segments.

**Evidence** (gap, track net, pad, segment):

| Gap (mm) | Track | Pad (net) | Segment |
|---|---|---|---|
| 0.075 | dq2 | A45 (n/c) and B45 (n/c) | (158.369, 100.732)-(158.369, 102.020), plus (158.369, 102.020)-(158.042, 102.348) |
| 0.075 | dq4 | A60 (n/c) | (161.817, 101.038)-(161.692, 101.163). The 0.0766 one is (161.817, 99.233)-(161.817, 101.038) |
| 0.075 | dq0 | D71 (eth_rxd3) | (165.260, 102.234)-(164.513, 102.980) |
| 0.075 | dq0 | B73 (no net) | (166.038, 101.555)-(165.392, 102.202) |
| 0.075 | dq0 | A74 (GND) | (166.428, 100.898)-(166.428, 101.348) |
| 0.0831 | dq16 | A10 (n/c) | (146.542, 99.859)-(148.238, 101.555) |
| 0.0849 / 0.0879 | dq0 | A73 (GND) | (166.221, 101.555)-(166.038, 101.555), plus the B73 segment above |
| 0.0888 | dq0 | A74 (GND) | (166.428, 101.348)-(166.221, 101.555) |

All other LPDDR/U7 F.Cu gaps are 0.0927 mm or more. Arcs were measured as arcs.

JLC, exact:
- Traces: "Multilayer: 0.09 / 0.09 mm (3.5 / 3.5 mil). 3 mil is acceptable in BGA fan-outs."
- BGA: "② BGA pad to trace clearance ≥ 0.1 mm (min. 0.09 mm for multilayer boards)".
- Pad to track clearance (1oz): "Min. 0.1 mm (stay well above if possible). Min. 0.09 mm locally for BGA pads".

**Would it pass JLC DFM as-is?** The page contradicts itself: 3 mil is "acceptable in BGA fan-outs", but BGA pad to
trace is "min. 0.09 mm". 0.075 mm is at the 3 mil figure, so it most likely passes, perhaps with a DFM warning. The risk
is a pad-to-trace short or an engineering question at 6 spots. With "Track width tolerance ±20%", a 0.1 mm track can come
out 0.12 mm, which leaves about 0.065 mm.

**Fix (copper only).**
- Move the vertical segments to the channel centre: dq2 x 158.369 -> 158.415, dq0 x 166.428 -> 166.405, dq4 x 161.817
  -> 161.665.
- Reshape the diagonal dq0 segments near D71/B73/A73 and the dq16 diagonal near A10 to 0.0975 mm.
- Then raise `lpddr_bga_clearance` from 0.075 to 0.09 mm, so DRC holds it.

This changes dq0/dq2/dq4/dq16 length by micrometres. Rerun the delay report afterwards.

---

## C-05: Via drill to copper 0.175 mm, against JLC's 0.2 mm

**Verdict: CONFIRMED WITH CORRECTION.** The antipad count is exact. The track count depends on how you count.
- All 859 vias are 0.3/0.15 mm. The board hole clearance is 0.175 mm (0.075 mm ring + 0.1 mm).
- Drill edge to other-net *track* under 0.2 mm: **444 via/layer/net spots on 284 vias**. 328 are at exactly 0.175 mm,
  116 at 0.176-0.199 mm. 193 of the 284 vias are under the U7 courtyard. By layer: In2 343, In5 297, F.Cu 198, B.Cu 44
  (segment counts).
- Drill edge to other-net *pad* under 0.2 mm: 4 spots, the smallest 0.175 mm.
- Inner-zone antipads at 0.175 mm: **388 (97 vias x In1/In3/In4/In6)**. These vias have no ring on those layers, so the
  zone stops at the hole clearance.

**Severity: SHOULD** for the 388 inner-zone antipads, because the fix is free. **INFO** for the track spots: they cannot
be fixed without re-routing the BGA fan-out, and JLC's own minima suggest the 0.2 mm figure is not measured from the
drill.

**Evidence (JLC, exact):**
- "Via hole to Track" / "0.2mm".
- "Inner layer via hole to copper clearance" / "0.2mm".
- "Inner layer PTH pad hole to copper clearance" / "0.3mm".
- "Min. Via hole size/diameter 0.15/0.25mm" and "① Via diameter should be 0.1mm(0.15mm preferred) larger than Via hole
  size."
- "Multilayer: 0.09 / 0.09 mm".

The page does not say how "via hole to track" is measured. Its own minimum via (0.25/0.15, 0.05 mm ring) plus the 0.09 mm
spacing would give 0.14 mm drill-to-track, so the 0.2 mm is either conservative or measured differently. I cannot verify
how JLC's DFM measures it.

**Would it pass JLC DFM as-is?**
- Track spots: probably yes. 0.3/0.15 vias with 0.1 mm spacing (0.175 mm drill-to-track) are very common on JLC boards.
  This is an assumption, not verified.
- Inner layers: "Inner layer via hole to copper clearance 0.2mm" is explicit, and 388 antipads are 0.025 mm short.
  Expect a DFM warning. JLC may pull the copper back itself. The risk to the board is small (a drill-wander short to a
  plane needs more than 0.175 mm of error, against ±0.075 mm position tolerance).

**Fix.**
1. Zero cost, copper only: add
   ```
   (rule "jlc_inner_hole_to_zone"
   	(condition "A.Type == 'Zone' || B.Type == 'Zone'")
   	(constraint hole_clearance (min 0.2mm)))
   ```
   and refill. I tested it on the copy together with the C-03 rule: every via drill to foreign inner zone is now
   ≥ 0.200 mm (0 below), and DRC is unchanged with 0 unconnected. The In1 `gndflood` area is 4240.7 mm2, a negligible
   change.
2. Before ordering, upload the Gerbers to JLC's online DFM and read its "via to track" result for the 0.175 mm spots. Do
   not re-route the U7 fan-out unless JLC objects.

---

## C-06: U7 decoupling against 821801 Table 63

**Verdict: CONFIRMED WITH CORRECTION.**
- The device is A5EB013B in B23B (netlist value `A5EB013B-B23B`). Table 63 row "FPGA A5E013B B23A/B32A/M16A/B23B/B18A
  Fabric, Merged VCC and VCCP: 4x 10 uF 0402 bottom side, no periphery capacitor". The claim's 4 x 10 uF is right for
  this device.
- The distance in the claim is wrong. The nearest VCORE bulk cap (C130, 22 uF) is **9.9 mm** from the nearest VCORE ball
  (16 mm is from the U7 centre).
- All eight 22 uF caps plus C124 sit at U15. They are regulator caps, which Table 63 excludes: "This table does not
  include recommended decoupling/bulk capacitors at voltage regulators."
- The other-rails part of the claim is right.

**Severity: SHOULD.** 821801 10.2.4 (p120): "You must perform the PDN transient simulation if your design is not
following the recommendation". Table 62 gives a VCC/VCCP step of 1.5 A at 50 A/us for A5E013B. Most of the fix is value
swaps on existing 0201 pads.

**Board vs Table 63** (B.Cu under U7, from the board; "rail balls" = U7 balls with that Altera pin name):

| Rail (net) | Table 63 bottom / periphery | On the board |
|---|---|---|
| VCC+VCCP (VCORE) | 4x 10 uF 0402 / none | 25x 100 nF 0201 under U7 (C122, C133-C156) on VCORE in total, no µF-class part. Nearest 22 uF is 9.9 mm away, at U15 |
| VCCL_HPS (VCORE) | 2x 10 uF 0402 or 3x 4.7 uF 0201 / 1x 22 uF 0603 | 100 nF only (C122, C147, C150 at 0.4 mm) |
| VCCL_HPS_CORE*, VCCL_SDM, VCCH_SDM, VCC_IO_SDM, VCCL_ADC_SDM (VCORE) | 1 uF 0201 each (VCCL_SDM 2x) | 100 nF only |
| VCCPT (1V8) | 2x 4.7 uF 0201 / 1x 10 uF 0402 | C191, C193 100 nF. C102 22 uF 0402 at 0.4 mm from the 1V8 balls, so the periphery 10 uF is covered |
| VCCPT_HVIO (1V8) | 2x 1 uF 0201 per bank | 100 nF |
| VCCRCORE (1V2) | 1x 1 uF 0201 / 1x 10 uF 0402 | C206-C208 100 nF. Nearest 1V2 bulk C196 22 uF, 8.9 mm |
| VCCIO_PIO 2A (1V2) | 2x 4.7 uF 0201 / 1x 10 uF 0402 per bank | C209, C210, C215 100 nF |
| VCCIO_PIO 3A (1V1, LPDDR4) | 2x 4.7 uF 0201 / 1x 10 uF 0402 per bank | C218-C221 100 nF. Nearest 1V1 µF part is 20.3 mm away (C263 1 uF at U12) |
| VCCIO_HVIO 6A-6H (3V3) | 1x 1 uF 0201 per bank | 100 nF (C174-C192) |
| VCCIO_SDM, VCCFUSEWR_SDM, VCCPLL_SDM, VCCADC, VCCIO_HPS, VCCPLL1/2_HPS (1V8) | 1 uF 0201 (+10 uF / 4.7 uF periphery for VCCIO_SDM / FUSEWR) | 100 nF, plus C102 22 uF within 0.4-2.4 mm |

**What fits.**
- Every U7 bottom cap is a C_0201 footprint, and 0201 parts go up to 4.7 uF, so the 0201 rows are pad-compatible swaps.
- An automated search found no free 0402 site among the U7 ball vias: no VCORE/GND via pair 0.85-1.05 mm apart with
  other-net copper cleared. C102 and the second 22 uF under U7 took the rare spots.
- Just south of the ball field there is free space: the B.Cu VCORE pour `corezone` is solid copper at x = 155-163,
  y = 123.5-127 with no parts. It is about 0.5-4 mm outside the U7 courtyard edge (y = 124.7) and roughly 6 mm from the
  nearest VCORE ball.

**Fix.**
1. Value swaps on existing 0201 pads (no copper change):
   - VCORE: 8 of the VCC/VCCP caps (for example C137, C138, C139, C140, C141, C144, C152, C156) and the 3 VCCL_HPS caps
     (C122, C147, C150) -> **4.7 uF 0201 6.3 V X5R**, LCSC **C5969171** (Samsung CL03A475MQ5C65C, extended, 133,895
     free) or C335103 (GRM035R60J475ME15D, 112,159 free). That gives 8 x 4.7 uF, about 38 uF at 0.75 V, in place of
     4 x 10 uF, and lower ESL.
   - The HPS-core and SDM caps (C133, C134, C149, C151, C153, C155, C146, C154, C135, C136) -> **1 uF 0201**,
     **C272877** (CC0201MRX5R5BB105, already on the BOM, 239,314 free).
   - Keep the other VCORE caps at 100 nF.
   - 1V8: C191, C193 -> 4.7 uF (C5969171). The VCCPT_HVIO caps -> 1 uF (C272877).
   - 1V2: one of C206-C208 -> 1 uF. C209 and C210 -> 4.7 uF.
   - 1V1: C218 and C220 -> 4.7 uF (C221/C219 stay 100 nF).
   - 3V3 HVIO caps (C174-C192) -> 1 uF **10 V** 0201 (C76935 GRM033R61A105ME44D, 246,358 free), because a 6.3 V 0201
     loses most of its capacitance at 3.3 V.
   - All 0201 µF parts are JLC extended, so this adds 2-3 new extended lines.
2. Optional, new parts: 4 x 10 uF 0402 **C15525** (CL05A106MQ5NUNC, **basic**, 8,875,763 free) on B.Cu at about
   y = 124.5, x = 155.5-161.5. VCORE pad on `corezone`, GND pad with its own GND via (passing In6 VCORE through an
   antipad). This gives the VCC/VCCP rail the four 10 uF parts Table 63 lists, close to the ball field.
3. One 10 uF 0402 (C15525) on 1V1 near U7's VCCIO_PIO_3A balls, if a site can be found. Otherwise the 4.7 uF swaps plus
   the U12 1V1 group have to do.

---

## Results

| Claim | Verdict | My severity | Fix type |
|---|---|---|---|
| C-01 | CONFIRMED (via carries ~83 % of I_out, 3.9-5.8 A) | SHOULD | Copper: add ≥ 6 GND vias on the `Vcore_gnd` island (x = 158.85, y = 132.8-136.8) |
| C-02 | CONFIRMED WITH CORRECTION (Altera's GND-stitching rule is met at 0.64-0.92 mm; 1V1 via/cap 3.9-9.7 mm) | INFO | Optional: 1V1-GND 0201 caps plus new 1V1 vias under the U7 top rows (new parts) |
| C-03 | CONFIRMED WITH CORRECTION (0.175 mm, set by the board hole clearance) | SHOULD | Rule + refill (`hole_clearance` 0.3 mm for NPTH), tested |
| C-04 | CONFIRMED WITH CORRECTION (6 pairs at 0.075 mm are dq0/dq2/dq4; dq16 is 0.083 mm; pads are 0.355 mm) | SHOULD | Copper: re-centre 8 segments, raise the `lpddr_bga_clearance` rule to 0.09 mm |
| C-05 | CONFIRMED WITH CORRECTION (444 track spots on 284 vias; 388 antipads exact) | SHOULD (antipads) / INFO (tracks) | Rule + refill for zones (tested); JLC online DFM check for the track spots |
| C-06 | CONFIRMED WITH CORRECTION (A5E013B: 4 x 10 uF is right; the bulk is 9.9 mm from the nearest VCORE ball, not 16) | SHOULD | Value swaps on existing 0201 pads (4.7 uF C5969171, 1 uF C272877); optional 4 x 10 uF 0402 C15525 (new parts) |

Not covered: JLC's actual DFM verdict (needs the Gerbers uploaded), PDN transient simulation, and a power estimate for
VCORE (taken from the repo checklist, marked as an assumption).
