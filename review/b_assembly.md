# Stream B: footprints, BOM, assembly

Frozen input: commit `0aa9192` (board and schematic identical in `88d946c`, only README files differ). Work files in
`review/work/b/`: `fab/` (BOM, CPL, Gerbers and DRC from `tools/jlc/fab_outputs.sh` on a project copy), `board.json`
(every footprint and pad from pcbnew), `lcsc.json` (JLC data for every LCSC number), `stock5.txt`, `pinpad.txt`,
`drc_all.json`, `scripts/`.

## Summary

| Severity | Count |
|---|---|
| BLOCKER | 1 |
| SHOULD | 7 |
| INFO | 11 |

- **BLOCKER:** U5 ADS7056IRUGR (C2669798) cannot be ordered from JLC stock: orderable −30 (oversold), stock 2, minimum
  purchase 2. It is the only part on the board that fails the 5-board stock check.
- **SHOULD:** U15 and U5 footprint anchors are 6.0 mm and 4.6 mm away from the package centre, and the CPL point for U15
  is on top of L1. U5 and U15 (QFN-type custom footprints) and the four SOT-563 regulators get no JLC rotation offset
  and are probably placed 90° or 180° wrong. U9 (6-pin LVDS oscillator) is probably 90° wrong. U7 has no LCSC number
  and must be sourced through Global Sourcing or consigned. The U15 PGND land is 8 separate fingers, not TI's joined
  PGND pad. J3 has holes reduced to 0.6 mm and no part number, and it is still in the BOM and CPL.
- **Checked and found correct:** symbol pins match footprint pads for all 341 parts. U7 ball positions and pad
  sizes match Altera 838752 exactly, with no mirror. The U2/U11/U12 BGA packages, ball naming and pin 1 match their
  datasheets. The U10, U15, U5, J9, L1, Y2, Y3, Y4 and U9 land patterns and pinouts match their datasheets (small
  deviations are listed as INFO). The LCSC part, value, package and voltage match on all 70 BOM lines. Fiducials are
  3 top + 3 bottom. Only 1 DRC footprint item remains (J3, intentional).
- **Not checked:** the JLC 3D placement preview (it cannot be opened from here). The rotation findings are predictions
  from the KiCad-to-JLC orientation conventions, so the user must confirm them in the preview. 3D clearance clashes:
  U5, U15 and L1 have no 3D model. The J3 mating part (no part number). The U7 Global Sourcing price and
  availability. The U12 ball map was spot-checked (about 40 balls), not checked ball by ball, because A1 and the EMIF
  Quartus test cover the DRAM pinout.

## Findings

### B-01 BLOCKER: U5 ADS7056IRUGR is out of stock at JLC
- Ref: U5, LCSC C2669798, 1 per board.
- Evidence: `tools/jlc/stock_check.py fab/bom_jlcpcb.csv --boards 5` (`review/work/b/stock5.txt`) gives `free -30, need
  5, min purchase 2`. JLC API: stockCount 2, canPresaleNumber −30. `jlc_search.py ADS7056` returns only this one
  part number.
- Consequence: JLC cannot place U5 from stock. The order either stops at BOM review or U5 is left unplaced. An
  unplaced U5 is an X2QFN-8 1.5 × 1.5 mm with 0.4 mm-class pads, which cannot practically be hand-soldered afterwards.
- Options: pre-order through JLC Global Sourcing or a parts pre-order (lead time), or consign the parts. If the ADC is
  not needed on the first boards, mark U5 DNP on purpose.
- Verified (live JLC API, 2026-11-01 10:06 EET).

### B-02 SHOULD: U15 and U5 CPL positions are not the package centre (U15's point lands on L1)
- U15 (TDA38812 footprint, bottom): the footprint anchor is at local (0, 0), but the pads span x −1.8…+0.9 and
  y 4.3…7.7. The package centre is at board (160.862, 134.204) and the CPL says (160.4118, 128.2041): **6.02 mm off**.
  The CPL point is inside L1's pads/courtyard (L1 centre 161.142, 128.109).
- U5 (ads7056 footprint, top): pads centred on local (0, 4.609). The package centre is at board (131.067, 129.949)
  and the CPL says (126.4332, 129.9492): **4.63 mm off**.
- Evidence: `review/work/b/board.json` (pad absolute positions); `agilex_lib.pretty/TDA38812.kicad_mod` and
  `ads7056.kicad_mod` (pads offset from origin; no F.Fab outline, no courtyard, no 3D model).
- Consequence: JLC places by the CPL Mid X/Y. Their engineers often snap parts to pads in DFM review, but if they do
  not, U15 is placed on top of L1 and U5 beside its pads.
- Fix: move each footprint anchor to the pad centre (re-centre the pads in the two library footprints and update the
  board), or correct these two CPL rows by hand to the centres above. Adding a body outline and courtyard to both
  footprints would also let DRC check their spacing (see B-13).
- Verified (geometry). Assumption: JLC uses the CPL point without snapping.

### B-03 SHOULD: U5 and U15 rotations get no QFN offset and are probably 270° wrong
- U5 `ads7056` and U15 `TDA38812` are QFN-type footprints drawn in the same orientation as KiCad's stock QFN: pin 1
  top-left, pins 1…n running down the left side. `jlc_bom_cpl.py` applies +270° to stock `QFN-*` footprints (U10 gets
  it) but does not match these names, so both get offset 0.
- CPL rotations written: U5 90° (top), U15 0° (bottom, 180 − 180). If JLC's VQFN-HR-21 and X2QFN-8 models follow the
  usual QFN convention, the correct values are probably U5 0° and U15 90°.
- Consequence of a 90° error: U15 (15 A buck, VIN 5V0 on pins 10/21, SW pin 20) would put VIN, SW and PGND on the
  wrong pads, so the VCORE rail would be destroyed or dead. U5 does not fit its pads at all.
- Fix: add a `JLC Rotation Offset` field (270) to U5 and U15, or fix these two rows by hand, and confirm in JLC's
  placement preview that the pin-1 dot sits at the pad-1 corner shown in the rotation table below.
- Assumption: JLC's model orientation for these two LCSC parts was not checked (no access to the preview).

### B-04 SHOULD: the SOT-563 regulators U8, U16, U18, U19 get no offset and are probably 180° wrong
- KiCad SOT-563 has the same pin layout as SOT-23-6 (pin 1 top-left, 1-2-3 down the left side). `^SOT-23` gets +180°
  in the correction table, but `SOT-563` matches no entry and gets 0°. All four are on the bottom at KiCad 90°, so the
  CPL says 90°.
- AP61202Z6 pinout (C5188956_mfr.pdf, Pin Descriptions p. 2): 1 FB, 2 GND, 3 VIN, 4 SW, 5 EN, 6 PG. A 180° error swaps
  1↔4, 2↔5 and 3↔6: 5V0 goes on PG and GND on EN. All four regulators would fail, and every rail they make with them.
- Fix: check in the preview; if the pin-1 dot is at the opposite corner from pad 1, set `JLC Rotation Offset` = 180
  on the four parts (CPL becomes 270°).
- Assumption: based on the SOT-23 table entry; not confirmed in JLC's preview.

### B-05 SHOULD: U9 AX3DAF1 6-pin oscillator is probably 90° wrong
- The stock footprint `Oscillator_SMD_SiTime_SiT9121-6Pin_3.2x2.5mm` is drawn portrait (2.5 × 3.2 mm), with pins 1-2-3
  down the left column. The Abracon drawing (AX3_abracon.pdf p. 13, Mechanical Dimensions; C2002827 package "SMD3225-6P")
  is landscape, with pins 1-2-3 along the long side. LCSC/EasyEDA 6-pin 3225 models are landscape with pin 1 at the
  bottom-left, the same relation as TSSOP, which gets +270°. U9 gets 0°, so the CPL says 0° (bottom, 180 − 180).
- Consequence: a 90° error does not fit the pads (portrait pads, landscape body). A 180°/270° error puts 3V3 on GND/OUT.
- Fix: check in the preview; expected correction `JLC Rotation Offset` = 270 (or 90). Assumption.

### B-06 SHOULD: U7 A5EB013B-B23B has no LCSC number
- Ref: U7. The BOM line has an empty LCSC column; `jlc_search.py A5EB013B` returns 0 hits.
- JLC will treat it as a Global Sourcing or consigned part. Arrange that before ordering: quote, lead time,
  moisture-sensitivity handling (MSL; consigned BGAs may need baking), and the exact ordering code (A1 covers the
  device choice). Without it the board cannot be built.
- Verified (BOM, JLC search). The cost is not included in the estimate below.

### B-07 SHOULD: U15 PGND land is 8 separate fingers instead of TI's joined PGND pad
- TPS548A28_ti.pdf p. 47 (RWW0021A Example Board Layout): pins 11–18 are one copper land: a 0.35 mm strip
  along the inside joined to eight 0.2 mm fingers, 3X (1.9) long. The package (p. 46) has the same continuous PGND
  bar. Footprint `TDA38812`: eight separate 0.8 × 0.2 mm pads at x = 0.9, 0.2 mm apart, all numbered 11.
- Everything else matches: pins 1–9 at 0.5/0.4/…/0.5 pitch, 3.4 mm span; pins 1, 9 and 19 are 0.3 mm wide, the rest
  0.2; column spacing 2.7 mm. Pin 21 (VIN, numbered 10 in the footprint) is at x −0.75, pin 20 (SW) at −0.15, pin 10
  (VIN) at −0.75 lower, bars 0.3 wide. Small differences: pads 0.8 long vs 0.7, VIN/SW bars 1.8 long vs 1.9.
- Consequence: less solder contact on the low-side MOSFET ground of the VCORE stage, so higher resistance and worse
  heat transfer. The package bar partly sits over the gaps.
- Fix: add one rectangular pad numbered 11, about 0.35 × 3.3 mm, on the inner side joining the fingers (TI layout
  p. 47), with paste per the stencil drawing p. 48.
- Verified (geometry against TI p. 46–47).

### B-08 SHOULD: J3 has smaller holes than the library, no part number, and is still in the BOM and CPL
- J3 `PinSocket_2x19_P1.27mm_Vertical`, bottom, THT: pads 0.9 mm with **0.6 mm drill**; the stock library uses
  1.0 mm / 0.7 mm. This is the DRC lib_footprint_mismatch, intentional per the brief.
- 1.27 mm headers and sockets typically have 0.4 mm square tails (0.57 mm diagonal). For example, the J6 header
  datasheet (C22438118 p. 1) shows SQ 0.40 and recommends a hole of about 0.65 mm. With JLC's PTH tolerance, a 0.6 mm
  finished hole can come out below 0.57 mm and the tail will not go in. Check the chosen socket's tail size before
  ordering.
- J3 has no LCSC number but is written to the BOM (empty LCSC) and the CPL (bottom, 180°). JLC will flag a missing
  part. If it is to be hand-soldered later, run `fab_outputs.sh … --skip J3` (or mark it DNP), so that the order is
  not held for it.
- Verified (board pads, library, CPL). Assumption: the socket's tail size (no part chosen).

### B-09 INFO: RN1–RN7 resistor arrays may be 90° off
- `R_Array_Convex_4x0402` is portrait in KiCad (pads 1–4 down one side); JLC's 4×0402 array is usually landscape. CPL
  says 0° (bottom, KiCad 180°). A 180° error is harmless (4 × 10 k, same value). A 90° error would not fit the pads
  and would show in the preview. Check. Assumption.

### B-10 INFO: rotations that are probably right but must be checked in the preview
- BGAs U7, U11, U12, U2: offset 0. LCSC/EasyEDA BGA models put A1 top-left like KiCad (U7's footprint is A1/A3 at
  top-left after the Altera Y-up conversion, see coverage).
- Y2, Y3, Y4: 4-pin 3225/2016 parts, pin 1 bottom-left at 0° as in the LCSC models. A 90° error on Y4 or Y2
  puts 3V3/1V8 on GND or OUT. A 90° error on Y3 puts the crystal across GND.
- D1, D2: LED_0603 pin 1 = K (cathode), to GND, at the right (board +x) at 180°. Check the cathode mark in the
  preview.
- U10: QFN-40 with +270° (table entry). The pin-1 dot must be at the board corner listed below.

### B-11 INFO: low stock margins (5 boards)
- Orderable / need: THGAMVG7T13BAIL 23 / 5, AP61202Z6-7 72 / 20, IS25WP128-RHLE 58 / 5, H9HCNNN8KUMLHR-NME 79 / 5,
  WPN201610H1R0MT 639 / 20. Enough today, but thin. Order soon or pre-book.

### B-12 INFO: C1 pad 0.20 mm from U5 pad 4 (different nets)
- C1 pad 1 (3V3_analog) to U5 pad 4 (3V3, DVDD): 0.20 mm edge to edge. Every other part-to-part pad gap on the
  board is ≥ 0.295 mm (`scripts/spacing.py`). DRC does not see this because U5 has no courtyard (missing courtyard
  is set to ignore). A solder bridge would short 3V3 to 3V3_analog. The bodies are 0.5 mm apart. Verified.

### B-13 INFO: U5 and U15 footprints have no fab outline, courtyard or 3D model; L1 has no 3D model
- `ads7056.kicad_mod`, `TDA38812.kicad_mod`: pads only. No courtyard means DRC cannot check overlaps. I checked by
  hand: no courtyard comes within 0.25 mm of the U15 body (3 × 4 mm), and only C1 is near U5 (B-12). No 3D model,
  so the 3D view cannot show clashes for U5, U15 or L1. Verified.

### B-14 INFO: U5 pad 4 off-centre by 0.05 mm
- ADS7056_ti.pdf p. 34 (RUG0008A land pattern): pins 8 and 4 are symmetric about the centre (about ±0.65). The
  footprint has pin 8 at −0.65 and pin 4 at +0.70 from the centre of pins 1–3. All other pads match: 0.55 × 0.25 for
  pins 1/3/5/7, 0.55 × 0.2 for 2/6, 0.3 × 0.6 for 4/8, 0.5 pitch, 1.35 column spacing; pin 1 top-left. Harmless.
  Verified.

### B-15 INFO: small land-pattern deviations that are compatible
- L2–L5 WPN201610H1R0MT on `L_Cenker_CKCS201610`: Sunlord recommends pads 0.7 wide, 1.7 high, 0.7 gap
  (C97002 p. 2, WPN201610H row). The footprint has 1.1 × 2.1 pads with a 0.3 gap (same 1.4 mm pitch). Larger pads,
  OK for reflow.
- Y4 OT3225 (YXC YSO110TR datasheet p. 3, 3.2 × 2.5): recommended 1.3 × 1.2 pads, gaps 0.8 / 0.7. The Abracon ASE
  footprint has 1.3 × 1.1 pads at ±1.05 / ±0.825. Compatible.
- U9 AX3 (AX3_abracon.pdf p. 13): pin pitch 1.2, row spacing 1.6. The SiT9121 footprint has pitch 1.125, row spacing
  1.6; corner pads 1.0 × 1.05, centre pads 1.0 × 0.65. Compatible.
- U11 eMMC: stock pad Ø0.24 for Ø0.30 balls (Kioxia p. 4), about 80 %. Fine for 0.5 mm pitch.
- U2: pad Ø0.40 for Ø0.40 nominal balls at 1.0 mm pitch (ISSI p. 105). Fine.

### B-16 INFO: BOM text details
- C124 comment contains a TAB: `GRM32ER71A476KE15L<TAB> 47uF 2mR` (from the schematic Value). It is harmless in the
  CSV but shows up in JLC's matcher; clean it up if JLC rejects the line.
- R27, R28 value "50R" with part C25120 = 49.9 Ω 1 %. Consistent with intent; the label differs.
- DNP, not in BOM or CPL (JLC leaves the pads bare): R9, R10, R34, R37, R56, R81, R84, R87, R90, C198.

### B-17 INFO: the DRC footprint items A1 saw were an environment artefact
- A1's run (`review/work/a1/drc/drc.json`) had 6 × "configuration does not include the footprint library
  'agilex_lib'" plus the J3 item: that copy had no project `fp-lib-table`. With the table, DRC compares all 7
  agilex_lib footprints with the library and reports no difference. The only footprint item left is J3's
  lib_footprint_mismatch (B-08), plus the 2 excluded J3 copper_edge_clearance items. Verified (`drc_all.json`,
  `fab/drc.rpt`).

### B-18 INFO: rough cost for 5 assembled boards (excluding PCB fabrication and U7)
- Parts at JLC prices incl. attrition: about **US$476**. The largest are U12 133, U11 116, U5 40, U9 31, the 33 × 22 µF
  0402 26, U2 23, U10 19.
- Unique parts: 18 basic, 3 preferred extended, **49 extended**. At about US$3 per extended part that is about
  **US$147** in loading fees.
- 331 placements per board (83 top, 248 bottom). 1990 SMD joints/board, about US$17 for 5 boards. 49 THT joints/board
  (J1, J2, J4, J5, J6, J9, J10; J3 excluded), a few dollars plus the manual THT fee.
- Two-sided Standard PCBA (BGAs require Standard): set-up and stencil for both sides, roughly US$60–80.
- Estimate: about **US$700–750 for assembly and parts**, before the 8-layer PCB and before U7. This is already above
  the ~600 EUR budget mentioned in the brief. Assumption: JLC fee schedule from memory, not fetched.

### B-19 INFO: two-sided assembly notes
- The bottom carries 248 parts, including U15 (VQFN-HR), U42 TSSOP-16, U9/Y2/Y3/Y4, L1 (5.7 × 5.2 × 2.8 mm, the
  heaviest bottom part), C124 1210, L2–L5, the RN arrays, 4 × SOT-563, and J3 (THT, not placed by JLC). None is too
  heavy for a second reflow. J3 must be hand-soldered after assembly.
- The top THT connectors (J1, J2, J4, J5, J6, J9, J10) are anchored at pin 1 (J5's anchor is 16.5 mm from its centre).
  JLC fits THT by hand, but the preview will show them offset.
- J9 overhangs the board edge by 4.86 mm (front of the jack, x 204.9 vs edge 200.04), as an edge RJ45 should.
- U7's 3D model is the stock FCPBGA-780 23 × 23 mm model (body size right, ball map not).

## For other streams
- A2: Y2 SiT8924BA-78-**18E** is the OE variant (datasheet Ordering Information p. 11, "E" = output enable); pin 1 is
  unconnected. The datasheet recommends a ≤10 kΩ pull-up if pin 1 is not driven (Table 2 note 3).
- A2: 6.3 V parts on 5V0: C157, C158, C160, C161 (22 µF 0402 6.3 V) and C224–C227 (2.2 µF 0402 6.3 V). They are
  within rating, but DC-bias derating leaves little of the capacitance.
- A2: U15 pin 9 (PGOOD) drives `/pwr_rails/EN`. Check that this is the intended sequencing.

## Rotation and pin-1 table (CPL as written)

"Pin 1" is where pad 1 (A1/A2/A3 for BGAs) sits relative to the package centre on the board, seen from the top. For
bottom parts the "from below" column is what JLC's bottom preview should show. The offset comes from the
`jlc_bom_cpl.py` table; bottom rotation = 180 − KiCad − offset.

| Ref | Footprint | Side | KiCad rot | CPL rot | Offset | Pin 1 (top view) | Pin 1 (from below) | Assessment |
|---|---|---|---|---|---|---|---|---|
| U7 | Altera_B23B | top | 0 | 0 | 0 | A3 top-left | – | probably right (B-10) |
| U12 | BGA-200 10×15 | top | 270 | 270 | 0 | A1 top-right | – | probably right (B-10) |
| U11 | LFBGA-153 | top | 90 | 90 | 0 | A1 bottom-left | – | probably right (B-10) |
| U2 | CSP24 6×8 | top | 90 | 90 | 0 | A2 (A1 depopulated) bottom-left | – | probably right (B-10) |
| U10 | QFN-40 5×5 | top | 180 | 90 | +270 | bottom-right | – | table entry; check |
| U5 | ads7056 (X2QFN-8) | top | 90 | 90 | 0 | bottom-left | – | **likely wrong (B-03)**, anchor off 4.6 mm (B-02) |
| U15 | TDA38812 (VQFN-HR 3×4) | bottom | 180 | 0 | 0 | top-right | top-left | **likely wrong (B-03)**, anchor off 6.0 mm (B-02) |
| U8, U16, U18, U19 | SOT-563 | bottom | 90 | 90 | 0 | bottom-right | bottom-left | **likely 180° wrong (B-04)** |
| U4 | SOT-23-5 | top | 270 | 90 | +180 | top-right | – | table entry; check |
| U6 | SOT-23-5 | top | 0 | 180 | +180 | top-left | – | table entry; check |
| U1 | TSSOP-16 | top | 90 | 0 | +270 | bottom-left | – | table entry; check |
| U3 | TSSOP-16 | top | 0 | 270 | +270 | top-left | – | table entry; check |
| U42 | TSSOP-16 | bottom | 90 | 180 | +270 | bottom-right | bottom-left | table entry; check |
| U9 | SiT9121 6-pin 3225 | bottom | 180 | 0 | 0 | top-right | top-left | **likely 90° wrong (B-05)** |
| Y2 | SiT PQFN-4 2016 | bottom | 180 | 0 | 0 | bottom-right | bottom-left | probably right; check |
| Y3 | Crystal 3225-4 | bottom | 0 | 180 | 0 | top-left | top-right | probably right; check |
| Y4 | Abracon ASE 3225-4 | bottom | 90 | 90 | 0 | bottom-left | bottom-right | probably right; check |
| D1, D2 | LED_0603 | top | 180 | 180 | 0 | K at right | – | check cathode mark |
| FB1 | 0402 | top | 270 | 270 | 0 | – | – | non-polar |
| L1 | TMPC0503H | bottom | 90 | 90 | 0 | – | – | non-polar |
| L2–L5 | CKCS201610 | bottom | 0 | 180 | 0 | – | – | non-polar |
| RN1–RN7 | 4×0402 array | bottom | 180 | 0 | 0 | top-right | top-left | 180° harmless, 90° not (B-09) |
| J1, J2, J10, J5 | 2.54 headers | top | 90 | 90 | 0 | pin 1 left end | – | THT; anchor at pin 1 |
| J4 | 1×3 header | top | 270 | 270 | 0 | pin 1 right end | – | THT |
| J6 | 2×3 1.27 header | top | 270 | 270 | 0 | top-right | – | THT; keyless, any rotation that fits is electrically the same orientation as the board |
| J9 | HR911130A | top | 270 | 270 | 0 | bottom-left | – | THT, keyed by pegs |
| J3 | 2×19 1.27 socket | bottom | 0 | 180 | 0 | bottom-right | bottom-left | no part; skip (B-08) |
| R*, C* (316 parts) | 0201/0402/0603/1210 | both | – | – | 0 | – | – | non-polar; all ceramic, no electrolytic or tantalum on the board |

## Coverage (checked and found correct)

**Symbol pins vs footprint pads, all parts** (`scripts/pinpad.py`, result in `pinpad.txt`)
- All 341 netlist components are on the board with the same footprint name. No symbol pin lacks a pad.
- All pad nets equal the netlist nets. The only differences are the `/` vs `{slash}` escaping in 10 net names.
- Pads without symbol pins: U7 30 balls, exactly the 20 DNU + 10 NC in `u7_balls_not_in_netlist.csv`; U11 120 balls,
  all NC/RFU/VSF/DNU per Kioxia "Pin Connection" p. 1, all unconnected. No unnumbered pad carries copper on a net.
  U10's numberless pads are paste-only.
- Exposed and thermal pads: U10 EP (pad 41) = GND (RTL8211F p. 6, "41 GND (Exposed Pad)"), EP 3.6 mm vs package
  D2/E2 3.45–3.95 (nom 3.70, §11.1 p. 61), paste 9 × 0.97 mm ≈ 65 %. U15 VIN bars (pins 10/21) = 5V0, SW (20) =
  `core sw`, PGND (11–18) = GND, AGND (2) = GND. J9 shield pins = GND.
- Pinouts checked against datasheets: U2 IS25WP128-RHLE all 24 balls incl. A4 = RESET# (ISSI p. 8, package H
  5×5). U11 all 33 functional balls (Kioxia p. 1 table). U10 pins 1–18 (Realtek p. 6, Fig. 4). U15 all pins (TI
  Table 5-1 p. 3–4). U5 all pins (ADS7056 Pin Functions p. 3). U4 OPA365 and U6 NCP163 SOT-23-5. U8 AP61202 (p. 2).
  Y2 SiT8924 (Table 2). Y3 (YXC: #1/#3 crystal, #2/#4 GND). Y4 (YXC: 1 tri-state, 2 GND, 3 OUT, 4 VDD). U9 AX3 Case 1
  (1 OE, 2 NC, 3 GND, 4 OUT, 5 OUT#, 6 VDD). J9 HR911130A P1–P10 and LEDs 11–14 (Hanrun p. 1 schematic). D1/D2 K = pin 1.
  U12 spot-check of about 40 balls (rows A, B, F, G, T and the VDD1/VDD2/VDDQ/VSS pattern) against SK hynix §2.1.1
  p. 6: all match.

**Land patterns**
- U7 Altera_B23B vs 838752 (`agilex5_b23b_ball_coordinates_land_pattern.*.csv`, xlsx Overview image): all 795 balls
  present. Positions equal Altera (−x, y) to < 1e-15 mm. Altera's frame is Y-up with pin 1 bottom-right (Overview
  figure), so the KiCad (Y-down) footprint is the Altera top view rotated 180°: no mirror. Row A is at the top,
  columns increase to the right, A1 corner top-left, which is the standard JEDEC top view. The Fab chamfer is at the
  same corner. Pad sizes match the guidance exactly: 769 × 305 µm, 17 × 330 µm, 9 × 355 µm (the corner balls listed in
  the sheet, e.g. A3, B2, C1, DN1, DP2, A74, B75, DN75, DP74 = 355). The stencil guidance (image10 in the xlsx) equals
  the pad sizes; the footprint paste = pad. Mask +0.05 mm (NSMD/MD; Altera allows MD or SMD). Body 23 × 23 mm,
  courtyard 25 × 25.
- U12 BGA-200 vs SK hynix §2.2 p. 7: 10 × 15 mm, 0.8 (x) × 0.65 (y) pitch, 12 × 22 grid with columns 6/7 and rows
  L/M depopulated = 200 pads. Array centred (0.6 / 0.675 margins). Ball Ø0.30, pad Ø0.27. A1 top-left.
- U11 LFBGA-153 vs Kioxia p. 4: 11.5 × 13 mm, 0.5 pitch, 14 × 14 array centred (2.50 / 3.25 margins), ball Ø0.30,
  pad Ø0.24.
- U2 vs ISSI §10.6 p. 105: 6 × 8 mm, 5 × 5 at 1.00 mm, A1 depopulated, ball Ø0.40, pad Ø0.40. The array is in the
  8 mm direction as in the drawing. Pin-1 chamfer top-left. The footprint name says MX25U25645G, but the geometry is
  ISSI package "H", which RHLE uses (ordering table p. 106).
- U10 stock QFN-40 5 × 5 0.4: e = 0.40, b = 0.20 (pads 0.25), L = 0.40 (pads 0.825 extending outside).
- U15 vs TI RWW0021A p. 46–47: see B-07 (everything except the PGND strip).
- U5 vs TI RUG0008A p. 34: see B-14.
- J9 vs Hanrun p. 2 (image-only, read as an image at 400 dpi): signal pins Ø0.89, two rows 6.35 / 8.89 behind the
  pegs, 1.27 pitch, pin 1 at x +5.715. LED pins Ø1.02 at ±4.085 / ±6.625, 4.90 in front of the pegs. Pegs Ø3.25 NPTH
  at ±5.715 (11.43). Shield Ø1.63 at ±7.745 (15.49), 3.05 behind. Front 10.92 from the pegs. All match the footprint.
- L1 TMPC0503H vs Tai-Tech p. 1: L 6.5, G 2.5, H 1.8 → pads 2.0 × 1.8 at ±2.25. Matches.
- Y2 vs SiTime p. 10 (2.0 × 1.6): 1.5 × 1.2 pitch, pads 0.9 × 0.8. Matches.
- Y3 X322525MOB4SI (C9006; JLC's datasheet is the YXC YSX321SL family sheet, image-only, read as an image): suggested
  1.4 × 1.2 pads, gaps 0.8 / 0.5. Matches the stock footprint exactly. Pin 1 bottom-left.
- Y4, U9, L2–L5: see B-15. J6: the HX PZ1.27 datasheet (image) shows SQ 0.40 pins on 1.27 pitch; the footprint drill
  is 0.65 mm.

**BOM / LCSC** (`lcsc.json`)
- All 70 BOM lines: LCSC part = schematic value; the package matches the footprint (0201 ↔ 0201, 0402 ↔ 0402, 0603,
  1210, SOT-23-5, SOT-563, TSSOP-16, X2QFN-8, VQFN-21-HR 3×4, QFN-40, SMD3225-4P/6P, SMD2016-4P, 0806 for 2016
  inductors). Voltage and dielectric match where the value states them ("22U 6V3" = 6.3 V X5R). The schematic MPN
  field matches the LCSC model for every IC, oscillator and connector. No 0402 part number on a 0201 footprint or the
  other way round.
- Stock for 5 boards: 69 of 70 lines OK by orderable quantity, minimum purchase 1 (except ADS7056, B-01). The
  headers have a minimum of 2 but a reel of stock.
- Parts without an LCSC number: U7 (B-06) and J3 (B-08). DNP list: B-16.
- 331 placements, 83 top and 248 bottom. The CPL count equals the BOM part count. Pos-file rotation equals the
  footprint orientation for all parts, so the bottom-side 180 − a conversion is applied once.

**Physical**
- DRC with the project rules: courtyards_overlap is an error and reports 0. The only footprint item is J3 (B-08, B-17).
- Part-to-part pad gaps: one at 0.20 mm (B-12); all others ≥ 0.295 mm.
- Fiducials: FID1–3 top, FID4–6 bottom. 1 mm copper, 2 mm mask opening, spread over three corners per side, outside
  the BOM/CPL.
- 3D models exist for all parts except U5, U15 and L1 (B-13). A visual 3D clash review was not done.
