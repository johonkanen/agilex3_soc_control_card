# LPDDR4 routing: byte and pin swizzle plan

Starting point: tag `pre-lpddr4-swizzle-reroute` (commit a2e793e). All DQ/DMI are routed and length-tuned. The
8 DQS nets are unrouted since the label fix in 0c58584.

## Rules (Agilex 5 LPDDR4)

Sources: EMIF IP UG 817467 (LPDDR4 pin placement) and EMIF Design Example UG 817394 ("Configuring DQ Pin Swizzling").

- **Fixed lanes:** U12 runs as one x32 rank. CA, CS, CKE and CK are shared by channels A and B.
  - Data lanes: 3A_B BL0, BL1 (channel A) and 3A_T BL6, BL7 (channel B).
  - Address/command lanes: BL2 (AC0) and BL3 (AC1). No AC pin may move.
- **Inside a lane:**
  - DQS_T on lane pin 4, DQS_C on pin 5, DMI on pin 6. Pin 7 stays unused.
  - The 8 DQ go on pins 0–3 and 8–11 in **any order** (pin swizzle). They must all belong to that lane's memory byte.
- **Byte swizzle:** only BL0↔BL1 or BL6↔BL7. DQ, DQS and DMI always move together.
- **Not allowed:**
  - swapping DQS_T/C or CK_T/C polarity;
  - moving a byte across channels;
  - a strobe in a different lane from its DQ.
- **Quartus:** keep the pin locations from the placement rules. Describe the swaps in the IP's `PHY_SWIZZLE_MAP` with
  `BYTE_SWIZZLE_CH0` and `PIN_SWIZZLE_CH0_DQS0..3`.

## Geometry

U12 sits above U7 and is rotated −90°.

**U12, channel A (right, x ≈ 169–172 mm):**

| Byte | Position | Balls |
|---|---|---|
| A0 | far, top, y ≈ 85.7–87.3 | B2…F4, DQS D3/E3 |
| A1 | near, y ≈ 91.3–92.9 | B9…F11, DQS D10/E10 |

**U12, channel B (left, x ≈ 159.6–162.2 mm):**

| Byte | Position | Balls |
|---|---|---|
| B0 | far | AA2…U4, DQS W3/V3 |
| B1 | near | AA9…U11, DQS W10/V10 |

**U7 lanes** (U7's top edge faces U12):

| Lane | U7 rows | Position | Note |
|---|---|---|---|
| BL7 | A/B | edge rows, x 150.9–155.5 | nearest U12, escapes on the outer layer |
| BL6 | E–T | x 152.5–155.2 | |
| BL0 | E–T | x 160.9–163.7 | |
| BL1 | M–AB | x 158.8–163.7 | deepest; interleaved with BL0 |

## Ratsnest analysis

Count of crossing straight U7→U12 lines, with the best DQ order chosen per lane. DQS and DMI are fixed.

| Byte assignment | Within bytes | Channel A (BL0/BL1) | Channel B (BL6/BL7) | Total |
|---|---|---|---|---|
| Current: BL0=A0, BL1=A1, BL6=B0, BL7=B1 | 13 | 50 | 89 | 152 |
| Swap A: BL0=A1, BL1=A0 | 12 | 55 | 89 | 156 |
| **Swap B: BL6=B1, BL7=B0** | 12 | 50 | **18** | **80** |
| Swap both | 11 | 55 | 18 | 84 |

The straight-line count is only a proxy, but it matches the routing geometry:

- **Channel B:** BL7 is on the edge rows and furthest left. It should take the long path around U12's left side to the
  far byte B0. BL6 then goes straight up to the near byte B1, and the two bundles nest instead of crossing.
- **Channel A:** BL0 and BL1 are interleaved in U7, so some crossing remains whichever way round they go. Separate them
  by layer: BL0 escapes from the shallower rows, BL1 from the deeper rows on an inner layer. Swapping gains nothing,
  and the current A routing is done.

## Plan

1. **Channel A: keep it.** BL0=A0, BL1=A1, and the DQ routing stays as it is.
   - Route dqs0 with byte 0's layers (mostly In2), and dqs1 on byte 1's other layer (F.Cu or In5).
   - dqs0/dqs1 cross only in plan view, not on the same layer.
2. **Channel B: byte swizzle BL6↔BL7** (`BYTE_SWIZZLE_CH0`). BL7 → B0 (dq16–23, dm2, dqs2) and BL6 → B1 (dq24–31, dm3,
   dqs3).
   - Rip up the byte 2/3 DQ/DMI routing. That's about 1,350 segments, mostly In2 for byte 2 and F.Cu/In5 for byte 3.
   - Starting pin order (minimal straight-line crossings; adjust it to the real escape order while routing):
     - BL7 → B0: pin0 B33→DQ5 V4, pin1 A36→DQ4 U4, pin2 B30→DQ2 V2, pin3 A33→DQ3 U2, pin8 A22→DQ1 Y2, pin9 A23→DQ6 Y4,
       pin10 B22→DQ7 AA4, pin11 A20→DQ0 AA2
     - BL6 → B1: pin0 J35→DQ10 V11, pin1 G35→DQ13 V9, pin2 T32→DQ11 U11, pin3 M32→DQ12 U9, pin8 T24→DQ9 Y11,
       pin9 M24→DQ8 AA11, pin10 G24→DQ14 Y9, pin11 E24→DQ15 AA9
   - Better workflow: route channel B first with the U7-side nets unassigned. Read off which U7 lane pin each U12 ball
     reached, then write that order back into the schematic labels on the bank 3 sheet. Any order within a lane is legal.
3. **Schematic:** relabel only the U7 side (`a5e_kicad/iobank3.kicad_sch`). U12 and mem1 stay as they are.
   - BL6 pins 0–3/8–11: dq24–31 in the chosen order; pins 4/5: dqs3_P/N; pin 6: dm3.
   - BL7 pins 0–3/8–11: dq16–23; pins 4/5: dqs2_P/N; pin 6: dm2.
4. **Strobes, routed alongside their bytes:**
   - Same layers and vias as the byte's DQ.
   - Length-match each byte to its DQS, keeping the existing tuning profiles.
   - No P/N swap; fix any twist in the breakout.
5. **Quartus parameters:**
   - Set `BYTE_SWIZZLE_CH0` for BL6↔BL7.
   - Generate `PIN_SWIZZLE_CH0_DQS0..3` from the final netlist (U7 lane pin → memory DQ index).
6. **Check:**
   - The lane-by-byte netlist check (each lane = one memory byte, DQS/DMI on pins 4/5/6);
   - DRC, plus the length-tuning report;
   - Quartus fitter with the EMIF IP: the pin and swizzle settings must pass the IP's placement check.

## Open points

- The Agilex 5 docs only allow BL6↔BL7 as a byte swizzle. Confirm in the Quartus EMIF IP GUI that `BYTE_SWIZZLE_CH0`
  accepts the swap for a 1×32 LPDDR4 interface before ripping up.
- Whole-channel swap (A↔B) isn't documented as legal, so the plan doesn't use it. It wouldn't help anyway: channel A is
  already on the right, next to BL0/BL1.
