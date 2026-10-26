# LPDDR4 swizzle rules (Agilex 5, U7 ↔ U12)

The short version of what may be reordered. The full background and the current lane map are in
`LPDDR4_SWIZZLE_PLAN.md`. Sources: Altera EMIF IP UG 817467 and design-example UG 817394.

## The lanes

| Lane (U7) | Channel | Memory byte | Nets |
|---|---|---|---|
| BL0 | A | A1 | dq8–dq15, dqs1_P/N, dm1 |
| BL1 | A | A0 | dq0–dq7, dqs0_P/N, dm0 |
| BL6 | B | B1 | dq24–dq31, dqs3_P/N, dm3 |
| BL7 | B | B0 | dq16–dq23, dqs2_P/N, dm2 |
| BL2, BL3 | shared | CA | ca0–5, cke, cs, ck_P/N, rst |

Each data lane has 12 pins: 8 DQ, DQS_P, DQS_N, DMI and one unused pin.

## Rules

**1. DQ bits can swap freely within their byte.**
The 8 DQ of a byte may sit on the lane's 8 DQ pins (lane pins 0–3 and 8–11) in any order.
- OK: dq0 ↔ dq7 (both in BL1).
- OK: dq24 ↔ dq28 (both in BL6).
- Not OK: dq7 ↔ dq8. They are in different bytes (BL1 and BL0).

**2. Whole bytes can swap within a channel.**
Only BL0 ↔ BL1 or BL6 ↔ BL7. All 8 DQ, the DQS pair and DMI move together.
- OK: BL6 ↔ BL7 and BL0 ↔ BL1 (this board does both: B0 is on BL7, B1 on BL6, A0 on BL1, A1 on BL0).
- Not OK: BL1 ↔ BL6. That moves a byte to the other channel.

**3. DQS and DMI have fixed pins.**
DQS_P is on lane pin 4, DQS_N on pin 5 and DMI on pin 6. Pin 7 stays unused.
- Not OK: dm0 ↔ dq3. DMI cannot take a DQ pin.
- Not OK: dqs2 in BL6 while dq16–23 are in BL7. The strobe must be in the same lane as its byte.

**4. No polarity swaps.**
- Not OK: dqs0_P ↔ dqs0_N, ck_P ↔ ck_N.

**5. CA lanes don't move.**
ca0–5, cke, cs, ck and rst keep their U7 balls. There is no swizzle for them.

## Quartus must match the board

Every swap must be described in the EMIF IP's `PHY_SWIZZLE_MAP`.

- **`BYTE_SWIZZLE_CH0`:** for lanes BL0…BL7, the memory byte on each lane (X = not a data lane).
  This board has `1 0 X X X X 3 2`: BL0 holds byte 1 (dq8–15), BL1 holds byte 0 (dq0–7), BL6 holds byte 3 (dq24–31) and
  BL7 holds byte 2 (dq16–23).
- **`PIN_SWIZZLE_CH0_DQSn`:** for byte n, the DQ index on lane pins 0, 1, 2, 3, 8, 9, 10, 11.

**Example:** swap dq24 and dq28 in BL6. Right now dq28 is on G35 (lane pin 1) and dq24 on G24 (lane pin 10).

```
before: PIN_SWIZZLE_CH0_DQS3=27 28 29 26 25 30 24 31
after:  PIN_SWIZZLE_CH0_DQS3=27 24 29 26 25 30 28 31
```

## Checklist for each batch of swaps

1. Relabel the U7-side labels in `a5e_kicad/iobank3.kicad_sch`. U12 keeps its JEDEC names.
2. Update the PCB from the schematic, then check that schematic parity is 0.
3. Update the `PIN_SWIZZLE` / `BYTE_SWIZZLE` strings and the lane map in `LPDDR4_SWIZZLE_PLAN.md`.
4. Re-run the Quartus fit (`~/dev/agilex5_emif_test`, `scripts/build_csv.sh`) and confirm no errors.
5. Re-check skew: package delays belong to the U7 ball, so a swapped net takes on its new ball's delay (see "Package
   delays" in the plan).

## What can be swizzled

### Where the bytes are on U12 (as placed: −90°, viewed from the top, board edge up)

```
             channel B (left)               channel A (right)
        ┌──────────────────────────┐   ┌──────────────────────────┐
 top    │  byte 2  dq16–23         │   │  byte 0  dq0–7           │
        │  dqs2, dm2               │   │  dqs0, dm0               │
        └──────────────────────────┘   └──────────────────────────┘
                 ▲                                ▲
                 │ byte swap OK                   │ byte swap OK
                 ▼ (done: BL7 ↔ BL6)              ▼ (done: BL0 ↔ BL1)
        ┌──────────────────────────┐   ┌──────────────────────────┐
 bottom │  byte 3  dq24–31         │   │  byte 1  dq8–15          │
        │  dqs3, dm3               │   │  dqs1, dm1               │
        └──────────────────────────┘   └──────────────────────────┘

               ◄──── left ↔ right: NEVER (other channel) ────►
```

- **Byte swap:** top ↔ bottom on the same side only. Left ↔ right crosses channels and is never allowed.
- **Bit swap:** within each byte, the 8 DQ go to the 8 DQ pins of their FPGA lane in any order. DQS_P, DQS_N and DM
  keep their fixed lane pins.
- **Each byte is a small patch, not a whole quarter.** A byte is 11 balls (3 balls wide, 4 rows deep, about
  2.6 × 1.6 mm), at the outer end of each quarter: x 151.7–154.3 mm for bytes 2/3, x 161.4–164.0 mm for bytes 0/1,
  y 85.9–87.5 mm (top) and 91.5–93.1 mm (bottom), ball centres with U12 at (157.867, 89.484). The rest of each quarter is VDD, VSS and CA. The CA balls sit next to
  the centre gap and never move.

### Bit swaps: any order inside each group

| Byte | Lane | Swappable among themselves | Fixed |
|---|---|---|---|
| Byte 0 (A0) | BL1 | dq0 dq1 dq2 dq3 dq4 dq5 dq6 dq7 | dqs0_P, dqs0_N, dm0 |
| Byte 1 (A1) | BL0 | dq8 dq9 dq10 dq11 dq12 dq13 dq14 dq15 | dqs1_P, dqs1_N, dm1 |
| Byte 2 (B0) | BL7 | dq16 dq17 dq18 dq19 dq20 dq21 dq22 dq23 | dqs2_P, dqs2_N, dm2 |
| Byte 3 (B1) | BL6 | dq24 dq25 dq26 dq27 dq28 dq29 dq30 dq31 | dqs3_P, dqs3_N, dm3 |

### Byte swaps: whole byte, within its channel only

| Channel | Legal swap | Current state |
|---|---|---|
| A | byte 0 ↔ byte 1 (BL0 ↔ BL1) | **swapped** (byte 0 on BL1, byte 1 on BL0; 2026-10-26) |
| B | byte 2 ↔ byte 3 (BL7 ↔ BL6) | **swapped** (byte 2 on BL7, byte 3 on BL6) |

### Never swizzled

- Across channels: bytes 0/1 ↔ bytes 2/3.
- Any DQS P ↔ N, or ck_P ↔ ck_N.
- ca0 ca1 ca2 ca3 ca4 ca5, cke, cs, ck_P, ck_N, rst.
