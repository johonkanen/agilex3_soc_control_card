# Verification v2_assembly: BOM, footprint and JLC placement claims (B-01 to B-08)

Board: `agilex_3_soc.kicad_pcb` at commit `ceb2746` (= `review/inputs/COMMIT`). The JLC BOM/CPL were regenerated
into `review/work/v2_assembly/` with `tools/jlc/jlc_bom_cpl.py` (331 parts, 77 lines; table offsets applied:
U42 +270, U1 +270, U3 +270, U4 +180, U6 +180, U10 +270; no LCSC: J3, U7).

## Method for the rotation claims

The placement JLC uses is the footprint in its own library (EasyEDA/LCSC) for the LCSC part. For every BOM part I pulled
that footprint (`easyeda.com/api/products/<LCSC>/components`, saved in the session scratchpad `easyeda/`). I then
matched its pads pin-for-pin against the real pad positions on the board (pcbnew), for rotations of 0/90/180/270
counter-clockwise. For bottom parts I compared against the board mirrored left-right, i.e. viewed from below
(scripts `audit.py` and `rotmatch.py` in the scratchpad).

**Calibration.** Where JLC's model has the pin-1 corner the offset table assumes, the method gives the same result as
the table, which has been confirmed in practice:
- U3 SN74LV4051 (TSSOP-16 `-BL`): +270;
- U10 RTL8211F (QFN-40 `-BL`): +270;
- U4 OPA365 (SOT-23-5 `-BR`): +180;
- U12 and U2 BGAs (`TL`): 0.

The bottom-side mirror convention reproduces the tool's offset-0 rule (180 − a): U15 → 0, Y3/L2 → 180, Y4 → 90 match.
That convention is also used by the current kicad-jlcpcb-tools (`fabrication.py` `_rotation_for_match`/`rotate`).
**One caveat:** kicad-jlcpcb-tools *adds* the package correction on the bottom; our `jlc_bom_cpl.py` *subtracts* it.
For ±90° offsets the two differ by 180°. The pad matching agrees with adding.

**Key finding of the method.** JLC's model orientation is per LCSC part, not per package. The pin-1 suffix in the model
name (`-BL`, `-TL`, `-BR`) varies within a package family. So the name-based table is wrong for some parts here, including
two it does match (U1/U42 `TSSOP-16…-TL`, U6 `SOT-23-5…-BL`).

## Findings

### B-01: U5 ADS7056IRUGR (C2669798) not orderable
- **Verdict:** CONFIRMED.
- **Severity:** BLOCKER, but only for the order as entered: JLC cannot assemble a part with negative orderable stock. It is
  caught at BOM upload and fixed by a part swap.
- **Evidence:** `jlc_search.py C2669798` (2026-11-01): extended part, `free = -30`, min 2.
  - ADS7056 pinout (TI SBAS769, Fig. 5-1): 1 CS, 2 SDO, 3 SCLK, 4 DVDD, 5 GND, 6 AVDD, 7 AINP, 8 AINM.
  - Netlist U5 matches: 4 = 3V3, 6 = 3V3_analog, 8 = GND.
- **Pin-compatible alternatives** (same RUG X2QFN-8 1.5×1.5 mm, same pinout per their datasheets, Fig. 5-1, "pin-to-pin
  compatible family"):
  - **ADS7052IRUGR, C2669879, 116 free:** 14-bit, single-ended, same 18-SCLK frame and 14-bit data as the ADS7056. But
    SCLK max is 24 MHz (vs 60 MHz) and throughput 1 MSPS (vs 2.5 MSPS). This is the nearest firmware-compatible drop-in.
  - **ADS7046IRUGR, C543003, 526 free:** 12-bit, single-ended, 3 MSPS, 60 MHz SCLK. Its frame is 15 SCLKs / 12 bits, so
    the FPGA-side frame needs a change.
  - Not drop-ins: ADS7054/ADS7057/ADS7047 (differential input; AINM is grounded here) and ADS7042/7041/7040 RUG (out of
    stock or too few).
- **Fix:** value/part swap on the existing pads: U5 → ADS7052IRUGR (C2669879), or ADS7046IRUGR (C543003) if 3 MSPS
  matters more than 14 bits. Its JLC model must be re-checked for rotation (same package, but see B-03). Other routes:
  - JLC Global Sourcing of ADS7056IRUGR: not verified here, the API covers only JLC stock;
  - DNP and hand-fit, which is impractical for an X2QFN.

### B-02: U15 and U5 footprint anchors are off the package centre
- **Verdict:** CONFIRMED.
- **Severity:** BLOCKER. JLC places on the CPL point as the part centre. U15 (the VCORE buck) would be aimed 6 mm away,
  into L1, and U5 4.6 mm off.
- **Evidence:** pcbnew, pad bounding box vs footprint position:
  - **U15** (`agilex_lib:TDA38812`, bottom, 180°):
    - anchor (160.412, 128.204); pad centre (160.862, 134.204); offset 6.017 mm.
    - In the library the pads sit at x −2.2…+1.3, y 4.15…7.85 from the origin.
    - The anchor lies inside L1's footprint (L1 at (161.142, 128.109); pads y 124.86–131.36; courtyard x 158.27–164.02,
      y 124.58–131.63).
    - CPL row: `U15,160.4118mm,-128.2041mm,Bottom,0.0`.
  - **U5** (`agilex_lib:ads7056`, top, 90°):
    - anchor (126.433, 129.949); pad centre (131.067, 129.949); offset 4.634 mm (library pads at y 3.96…5.31).
    - CPL row: `U5,126.4332mm,-129.9492mm,Top,90.0`.
  - Neither footprint has a courtyard, and both fab outlines are off the pads as well (U15 fab centre (160.412, 130.704)).
    DRC therefore cannot see their bodies.
  - Every other fitted SMD part has its anchor at the pad centre (audit of all 331 CPL rows). Through-hole headers anchor
    on pin 1: J1 5.08, J2/J4 2.54, J5 16.51, J6 1.42, J9 2.00, J10 1.27, J3 11.45 mm. JLC places these by hand into
    holes, so this is INFO.
- **Fix:** no copper change. Move the origin of `agilex_lib.pretty/ads7056.kicad_mod` to the pad centre (0, 4.634) and
  of `TDA38812.kicad_mod` to (−0.45, 6.0). Add a courtyard while there. Then move the board footprints so the pads stay
  where they are:
  - U5 position → (131.067, 129.949);
  - U15 position → (160.862, 134.204).

  Updating from the library keeps the old anchor and would shift the pads, so verify with a pad-coordinate diff and DRC.
  The CPL rows must become:
  - `U5 131.0668mm, -129.9492mm`;
  - `U15 160.8618mm, -134.2042mm`.

### B-03: U5 and U15 get no QFN rotation offset
- **Verdict:** CONFIRMED WITH CORRECTION. True for U5; false for U15.
- **Severity:** SHOULD. U5 placed 90° wrong kills only the ADC; U5 is square, so the error is not visible in JLC's preview.
- **Evidence:**
  - **U5:** JLC model `X2QFN-8_L1.5-W1.5-P0.50-BL` has pin 1 at bottom-left with pins 1–3 along the bottom. The KiCad
    footprint has pin 1 top-left with 1–3 down the left side. The pin-for-pin match (8 pins, 0.04 mm error) gives a JLC
    rotation of **0**; the CPL has **90**. That is the missing +270, which places the part 90° off.
  - **U15:** JLC model `TQFN-21_L4.0-W3.0-P0.40-TL` has pin 1 top-left with 1–9 down the left side, the same as the
    footprint and TI's top view (SNVSBB1D Fig. 5-1). The match (11 unique pins, 0.15 mm error) gives **0** for the bottom
    view; the CPL has **0**, which is correct. A +270 table entry would make it wrong.
- **Fix:**
  - U5: footprint field `JLC Rotation Offset = 270` → CPL 0. Repeat the check if U5 becomes ADS7052/ADS7046 (B-01).
  - U15: leave at 0 (optionally an explicit `JLC Rotation Offset = 0`) once B-02 is fixed.

### B-04: SOT-563 regulators U8, U16, U18, U19 get no offset
- **Verdict:** CONFIRMED WITH CORRECTION. The CPL is wrong, but by **90°**, not 180°.
- **Severity:** BLOCKER. All four buck converters (5V0 in) would be placed with the pins on the wrong pads.
- **Evidence:**
  - KiCad `SOT-563`: pins 1–3 down the left side at x = −0.7125 (pin 1 top-left).
  - JLC models:
    - C5188956 (AP61202, U8/U19): `SOT-563-6_…-BL`;
    - C5244557 (AP61203, U16/U18): `SOT-563_…-BL`.

    In both, pin 1 is bottom-left with 1–3 along the bottom (y = +0.64/+0.72 mm).
  - The match (6 pins, 0.01–0.07 mm error) gives JLC rotation **0** for all four (bottom, KiCad 90°). The CPL has **90**.
  - So JLC's SOT-563 needs a ±90° correction, not the +180 the claim assumed. Even with the other bottom-mirror
    convention the answer would be 180, still 90° from the CPL.
- **Fix:** footprint field `JLC Rotation Offset = 90` on U8, U16, U18, U19. With the tool's bottom formula
  180 − 90 − 90 this gives CPL **0**. No copper change.

### B-05: U9 AX3DAF1 oscillator 90° wrong
- **Verdict:** CONFIRMED.
- **Severity:** SHOULD. The board's 100 MHz LVDS reference would be dead. Because the part is not square the mismatch is
  visible in JLC's preview and likely caught, but it must not be relied on.
- **Evidence:**
  - KiCad `Oscillator_SMD_SiTime_SiT9121-6Pin_3.2x2.5mm` is portrait: pads at x ±0.8, y ±1.125/0, pin 1 at (−0.8, −1.125).
  - JLC model C2002827 `OSC-SMD_6P-L3.2-W2.5-P1.20-BL` is landscape: pads at x ±1.2/0, y ±0.92, pin 1 bottom-left.
  - The match (6 pins, 0.14 mm error) gives **270** for the bottom view (KiCad 180°). The CPL has **0**.
- **Fix:** `JLC Rotation Offset = 90` on U9 (180 − 180 − 90 = −90 → CPL **270**).

### B-06: U7 A5EB013B-B23B has no LCSC number
- **Verdict:** CONFIRMED.
- **Severity:** SHOULD. This is a sourcing step, not a design defect, but the order cannot be assembled until it is
  arranged.
- **Evidence:**
  - Footprint U7 has no `LCSC` field; the tool lists it as "no LCSC number".
  - `jlc_search.py A5EB013B` / `A5EB013` find 0 hits.
  - BOM line: `A5EB013B-B23B,U7,Altera_B23B,` (empty LCSC).
  - CPL: `U7 Top 0.0`. JLC has no model for it, so its pin-A1 orientation cannot be checked here.
- **Fix:**
  - Buy through JLC Global Sourcing, or consign the part.
  - Put the complete Altera ordering code (with speed, temperature and power suffix) in `MPN`; "A5EB013B-B23B" is the
    die/package name, not an orderable code. I could not verify the exact orderable code.
  - Tell JLC that ball A1 is at the KiCad footprint's pin-1 corner (CPL rotation 0).

### B-07: U15 PGND land is 8 separate fingers
- **Verdict:** CONFIRMED WITH CORRECTION. The pads are 8 separate fingers (all numbered 11; pins 12–18 do not exist in the
  footprint). But the B.Cu GND zone fills the 0.2 mm gaps between them, so the copper is joined. Only the solder-mask
  openings and paste are split.
- **Severity:** INFO / low SHOULD. Electrically fine. Solder contact with the package's PGND bar is reduced: ~1.36 mm²
  of finger pads vs ~1.7 mm² for TI's joined land. With `pad_to_mask_clearance 0`, 0.2 mm mask webs cover the zone between
  the fingers. Worth fixing because B-02 edits this footprint anyway.
- **Evidence:**
  - TI SNVSBB1D p.46–47 (RWW0021A): PGND (pins 11–18) is one land, a 0.35 mm inner bar spanning pin 18 to pin 11 (3.15 mm)
    with 0.7 mm fingers. JLC's own model C5219375 has the same: bar 0.35 × 3.15 mm plus fingers.
  - Footprint: eight 0.8 × 0.2/0.3 mm pads at x = 0.9, y 4.8…7.7, and no bar.
  - `HitTestFilledArea(B.Cu)` at (159.512, 133.204/134.004/135.204) and (159.30/159.75, 133.204): GND zone present.
  - The VIN bars are both numbered "10" (TI 10 and 21). This is harmless.
- **Fix:** footprint copper/mask/paste change in `TDA38812.kicad_mod`. Add a rectangular pad "11", 0.35 × 3.15 mm, at
  library (0.675, 6.275) (package-relative +1.125, +0.275), joining the fingers like TI's land. Paste can stay on the
  fingers only, per TI's stencil (p.48: 89 % coverage).

### B-08: J3 0.6 mm holes, no part number, still in BOM/CPL
- **Verdict:** CONFIRMED WITH CORRECTION. The hole-size concern is refuted; the missing part number is confirmed.
- **Severity:** INFO. A part with an empty LCSC just goes unplaced at JLC.
- **Evidence:**
  - J3 pads: 0.9 mm with 0.6 mm drill. The KiCad library `PinSocket_2x19_P1.27mm_Vertical` has 1.0 mm / 0.7 mm. The
    README documents this as intentional.
  - The orderable 2×19 1.27 mm THT socket **HC-PM127-4.3H-2x19PZ, C27985219, 355 free** has 0.45 × 0.15 mm tails
    (0.47 mm diagonal) and a datasheet-recommended **Ø0.6 mm** hole.
  - JLC's own footprint for C27985219 uses 0.9 mm pads with a 0.6 mm drill, identical to J3. So 0.6 mm suits this
    socket. Square 0.4 mm tails (0.57 mm diagonal) would be tight, given JLC's PTH tolerance.
  - BOM: `2x19 1.27mm socket, bottom,J3,…,` (no LCSC); CPL `J3 Bottom 180.0`, at the pin-1 anchor (11.45 mm from the
    centre).
- **Fix:** choose one:
  - (a) Set J3 `LCSC = C27985219` with `JLC Rotation Offset = 270`. The pad match gives **270** for the bottom view,
    where the CPL now has 180. JLC will also need the centre (126.957, 95.174), i.e. CPL Mid Y −95.1742, or it will
    correct by hand.
  - (b) Mark J3 DNP / exclude from BOM and fit it by hand.

  Either is a field-only change on the existing pads.

## Additional rotation errors found by the full CPL audit (same lane)

All are field-only fixes (`JLC Rotation Offset`; values are for the current tool formula):

| Ref | JLC model | Side, KiCad angle | CPL now | Needed | Field value |
|---|---|---|---|---|---|
| U1 SN74AXC4T774 (C1849453) | TSSOP-16 `-TL` | top, 90 | 0 | **90** | 0 (the table's +270 is wrong for this part) |
| U42 same part | TSSOP-16 `-TL` | bottom, 90 | 180 | **90** | 0 |
| U6 NCP163 (C603656) | SOT-23-5 `-BL` | top, 0 | 180 | **270** | 270 (the table's +180 is wrong for this part) |
| RN1–RN7 4×10k (C25725) | 0402×4 array, landscape | bottom, 180 | 0 | **90 or 270** | 90 |
| J1, J2, J5, J10 headers | THT | top, 90 | 90 | 0/180 | 270 |
| J4, J6 headers | THT | top, −90 | 270 | 180 | 270 |

- U1 and U42 are the SN74AXC4T774 level shifters; RN1–RN7 are the J3 pull-downs; the headers are hand-placed by JLC.
- RN1–RN7: the board pads are portrait, JLC's model landscape. With the 0° in the CPL the parts would not fit their pads.

Separately, `tools/jlc/jlc_bom_cpl.py` subtracts the package offset on the bottom side. kicad-jlcpcb-tools now adds it,
and the pad matching agrees with adding. Today this only affects U42; the field values above are for the tool as it is.

## Coverage

- **Checked and correct:** all 2-terminal passives with a JLC model, and every other part not listed above, including:
  - U3, U4, U10, U12 (LPDDR4), U2 (QSPI), U15 (rotation only), Y3, Y4, L1–L5, J9 (RJ45), FB1, LEDs.

  That is 237 parts matched OK.
- **Anchor offsets:** checked on all 331 placements.
- **Not checked:**
  - JLC models could not be downloaded (API rate-limit) for U11 eMMC (C7599693, user-supplied), R2, R18, R41, R89,
    R241–R243, R245, R247, R250, R272–R279 (0201/0402 resistors; 2-pad standard footprints, low risk);
  - U7 and J3 have no LCSC part.
- **Assumptions:**
  - JLC places with the EasyEDA footprint of the LCSC part.
  - Its CPL rotation is counter-clockwise.
  - Bottom parts are viewed mirrored left-right.

  These are consistent with the table calibration and kicad-jlcpcb-tools, but not with JLC documentation. **Check every
  part above in JLC's placement preview**, especially bottom-side U8/U16/U18/U19, U9, U15, U42 and RN1–RN7.

## Summary

| Claim | Verdict | Severity | Fix type |
|---|---|---|---|
| B-01 | CONFIRMED | BLOCKER | Part swap on same pads (ADS7052IRUGR C2669879 or ADS7046IRUGR C543003) |
| B-02 | CONFIRMED | BLOCKER | Footprint origin move for U5/U15, no copper change (CPL to pad centre) |
| B-03 | CONFIRMED WITH CORRECTION (U5 yes, U15 no) | SHOULD | Field: U5 `JLC Rotation Offset` 270; U15 stays 0 |
| B-04 | CONFIRMED WITH CORRECTION (90° wrong, not 180°) | BLOCKER | Field: offset 90 on U8/U16/U18/U19 → CPL 0 |
| B-05 | CONFIRMED | SHOULD | Field: U9 offset 90 → CPL 270 |
| B-06 | CONFIRMED | SHOULD | Sourcing: Global Sourcing/consign with full ordering code |
| B-07 | CONFIRMED WITH CORRECTION (zone joins copper; mask/paste split) | INFO | Footprint copper: add 0.35×3.15 mm PGND bar pad |
| B-08 | CONFIRMED WITH CORRECTION (0.6 mm hole fits C27985219; part number missing) | INFO | Field: LCSC C27985219 + offset 270, or DNP |
| (extra) | U1, U42, U6, RN1–RN7, THT headers wrong in CPL | SHOULD | Fields: rotation offsets (see table) |
