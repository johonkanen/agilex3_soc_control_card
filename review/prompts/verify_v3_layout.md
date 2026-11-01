You are verifier **v3_layout** (copper, fabrication and decoupling claims). First read and follow
/home/jari/dev/agilex3_soc_control_card/review/prompts/verify_common.md. Your report is `review/v3_layout.md`, your
scratch folder `review/work/v3_layout/`. Use pcbnew python on the board (read-only; filled zones as stored, or refill
a copy in your scratch folder).

Claims to verify (as the reviewers stated them):

- **C-01:** U15's (TPS548A28) power-ground copper on B.Cu (zone `Vcore_gnd`) connects to the GND planes through only
  one 0.3/0.15 mm via at (158.44, 132.33); U15's PGND pins, every VCORE bulk capacitor and every input capacitor ground
  to that copper, so all 6-7 A of VCORE return current flows through it. TI asks for at least six PGND vias (datasheet
  Table 5-1 p4, section 10.1 p39). Check every connection path from that copper to GND (vias, pads, through-hole
  parts, other layers) and the actual current.
- **C-02:** 25 LPDDR4 vias at U7's top rows go from F.Cu (GND reference) to In5 (referenced to the In6 1V1 pour); the
  nearest 1V1-to-GND capacitor or 1V1 via is 7-9.7 mm away, while Altera 821801 section 6.1.3 (p48) asks for return
  stitching within 2.03 mm.
- **C-03:** at the heatsink holes H1/H2 (3.2 mm NPTH), inner-plane copper comes to 0.18 mm from the hole edge; JLC asks
  for 0.2 mm (NPTH to copper), and the keep-out areas exist only on F.Cu/B.Cu.
- **C-04:** at U7, ten F.Cu track-to-pad gaps are 0.075-0.089 mm, six of them 0.075 mm (dq0/dq2/dq4/dq16 near rows
  A/B), below JLC's 0.09 mm minimum and below the 3 mil (0.0762 mm) JLC accepts in BGA fan-outs.
- **C-05:** via drill to copper is 0.175 mm in about 199 track/via spots and about 388 inner-plane antipads, where JLC
  lists 0.2 mm; how JLC measures it is unclear.
- **C-06:** U7 decoupling departs from Altera 821801 Table 63 (p121-122): VCC/VCCP has no 4 x 10 uF 0402 under the
  BGA (nearest 22 uF is 16 mm away), and the other rails use 100 nF where 1-4.7 uF 0201 plus 10 uF 0402 are
  recommended. Verify against the table for this device/package and check what physically fits under/around U7.

For C-03, C-04 and C-05, quote JLC's capabilities page exactly (values and wording) and say whether the board would
pass JLC's DFM as-is, with what risk.
