You are verifier **v2_assembly** (BOM, footprint and JLC placement claims). First read and follow
/home/jari/dev/agilex3_soc_control_card/review/prompts/verify_common.md. Your report is `review/v2_assembly.md`, your
scratch folder `review/work/v2_assembly/`. Generate your own JLC BOM/CPL with tools/jlc (see tools/jlc/README.md;
jlc_bom_cpl.py runs under the KiCad python) into your scratch folder; do not reuse other review work folders.

Claims to verify (as the reviewers stated them):

- **B-01 (BLOCKER):** U5 ADS7056IRUGR (C2669798) cannot be ordered from JLC stock (orderable -30, oversold). Check
  current stock, and find drop-in alternatives (same footprint/pinout) or other ways (global sourcing, consign, DNP).
- **B-02:** the U15 (TPS548A28, footprint agilex_lib:TDA38812) and U5 footprint anchors are 6.02 mm and 4.63 mm from
  the package centre, so the CPL position JLC places on is off-centre; U15's point lands on L1.
- **B-03:** U5 and U15 get no QFN rotation offset in the CPL (the tool's table only matches stock `QFN-*` footprint
  names), so they are probably 270 deg wrong in JLC's placement.
- **B-04:** the SOT-563 regulators U8, U16, U18, U19 get no rotation offset while SOT-23 gets +180 deg, so they are
  probably 180 deg wrong (5V0 on PG, GND on EN).
- **B-05:** U9 (Abracon AX3DAF1, 6-pin 3.2x2.5 mm oscillator) is probably 90 deg wrong: KiCad's footprint is portrait,
  JLC's model landscape.
- **B-06:** U7 A5EB013B-B23B has no LCSC number, so global sourcing or consignment must be arranged.
- **B-07:** U15's PGND land is 8 separate fingers instead of TI's joined PGND pad (TPS548A28 datasheet, RWW0021A land
  pattern, p47).
- **B-08:** J3 (2x19 1.27 mm socket on the bottom side) has 0.6 mm holes where the KiCad library has 0.7 mm, which may
  not take typical 1.27 mm socket tails; it has no part number and is still in the BOM and CPL.

For the rotation claims (B-03, B-04, B-05) work out JLC's convention from first principles: the footprint's pin-1
position and orientation in KiCad, the package drawing and tape orientation in the datasheet, and JLC's documented /
commonly used rotation rules (the offset table in tools/jlc and the kicad-jlcpcb-tools project it cites). State for each
part the rotation you expect JLC to need and what the CPL currently contains.
