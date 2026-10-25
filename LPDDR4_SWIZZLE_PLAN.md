# LPDDR4 routing: byte and pin swizzle plan

**Status (branch `lpddr4-reroute-explore`, 2026-10-25):** "variant R2" is in the schematic and on the PCB. It replaces
the earlier variant R, which had U12 at its old position. All LPDDR4 copper is removed, ready for a clean reroute.
- **U12 moved 6 mm left:** F.Cu, −90°, now at (159.792, 89.284), centred over bank 3A. Its decoupling block and power
  fan-out moved with it, and the zones are refilled. See "Move to −6 mm".
- **Byte swizzle:** BL6↔BL7. BL0/BL1 are unchanged.
- **Pin swizzle:** re-optimised for the new position.
- **Schematic/PCB sync:** the U7-side labels on `a5e_kicad/iobank3.kicad_sch` are relabelled, and the U7 pad nets on
  the PCB match them (schematic parity 0).
- **Quartus fitter:** **pass**, with the R2 strings (see "Quartus check").

Earlier starting points: tag `pre-lpddr4-swizzle-reroute` (commit a2e793e) has the old fully routed DQ/DMI. Commit
94e49d7 is the last one with the old routing.

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
- The Agilex 3 EMIF guide and TI's AM62x guide (SPRAD06C §3.16) say the same: bit swaps only within a byte, byte swaps
  only within a channel, never across channels. No source was found that allows an A↔B channel swap, so none is used.

## Research summary (2026-10-25)

What the public documents say, and how it applies here:

- **Topology:** Altera PCB guide 821801, "LPDDR4 Interface Design Guidelines" / "Memory Down Topology (up to 32 bits)".
  - Agilex 5 LPDDR4 is memory-down only, point-to-point FPGA↔DRAM.
  - Both thin and thick stack-ups are supported.
  - CA/CK/CTRL may be a T or daisy chain on stripline. Here, each CA has a short T to the channel-A and channel-B balls.
- **Breakout and layers:** 821801 §6.1.1 "FPGA DDR Break Out Routing" and the routing tables.
  - Altera's recommendation: stripline for inner GPIO pins, microstrip for GPIO pins at the edge of the device.
  - The routing tables specify each signal as break-out, main and break-in segments, with SL = stripline and
    US = upper-surface microstrip.
  - For this board: U7's two edge rows (A/B; BL7 and the CA pins) go out on F.Cu. Everything deeper goes to the
    stripline layers (In2/In5), plus B.Cu for CA, as on the existing board.
- **DQS/CK:** 821801 §6.1.1 and §6.1.2 "DRAM Break Out".
  - Route DQS/CK as differential pairs, with a symmetrical fan-out at the FPGA.
  - Inside the DRAM pin field the halves may run as single-ended traces, equal in length.
  - Dog-bone or via-in-pad at the DRAM.
- **Same-layer bytes:** TI SPRAD06C §2/§3.
  - Keep all signals of a byte on one layer, with the same number of vias.
  - Minimise layer transitions.
  - Adjacent DDR routing layers only as offset stripline.
  - Six layers is the minimum; dense boards need more.
- **Reset:** 1 kΩ pull-down, and 3×H spacing to other signals (821801).
- **Orientation:** none of the public documents gives an orientation rule for the 200-ball part.
  - The DE25-Nano layout files are not public. Altera's EMIF layout page (817467) is "visible to Intel only".
  - The only usable information is the JEDEC 200-ball ballout itself:
    - channel A is in rows A–K and channel B in rows P–AB;
    - in each channel, byte 0 is in columns 2–4 and byte 1 in columns 9–11;
    - CA/CK are in rows H/J (A) and P/R (B);
    - columns 6–7 and rows L–M are depopulated.
  - From that ballout, the rule follows: put the channel split (the long axis) **across** the FPGA side, so each
    channel faces its own pair of FPGA lanes. The data bytes then sit at the short ends, reachable from the sides and
    from the empty middle bands.

Links:
- Altera 821801 LPDDR4 interface guidelines: https://www.intel.com/content/www/us/en/docs/programmable/821801/current/lpddr4-interface-design-guidelines.html
- Altera 821801 table of contents (FPGA/DRAM breakout sections): https://docs.altera.com/r/docs/821801/current/pcb-design-guidelines-hssi-emif-mipi-true-differential-pdn-user-guide
- Altera 821801 FPGA DDR breakout: https://docs.altera.com/r/docs/821801/current/pcb-design-guidelines-hssi-emif-mipi-true-differential-pdn-user-guide/fpga-ddr-break-out-routing?contentId=4g_8u5NCvRuIQzMjZwDxcw
- Altera 821801 DRAM breakout: https://docs.altera.com/r/docs/821801/current/pcb-design-guidelines-hssi-emif-mipi-true-differential-pdn-user-guide/dram-break-out-in-layout-routing?contentId=OiiJ02kZtwhQMH0avG54Uw
- Altera 821801 LPDDR4 routing tables: https://www.intel.com/content/www/us/en/docs/programmable/821801/current/tables-for-comprehensive-routing-guidelines.html
- Agilex 3 EMIF "Configuring DQ Pin Swizzling": https://www.intel.com/content/www/us/en/docs/programmable/847458/25-3/configuring-dq-pin-swizzling.html
- TI SPRAD06C (AM62x DDR layout, LPDDR4 placement, byte/bit swapping): https://www.ti.com/lit/pdf/sprad06
- TI e2e, LPDDR4 channel swapping not allowed: https://e2e.ti.com/support/processors-group/processors/f/processors-forum/883650/am6546-lpddr4-channel-swapping-a-b

## Placement exploration (2026-10-25)

**Inputs:**
- Real pad coordinates from pcbnew.
- U12 at 0/90/180/−90°, at the original position and shifted 2/4/6/8 mm left. A finer 0.5 mm scan at −90° follows below. It can't move up (board edge) or
  down (U7).
- For each case, all 4 legal byte swizzles. For each lane, the pin swizzle comes from a pairwise-swap search starting
  from the order-sorted matching, minimising wORD + wSL.

**What is counted:** every U7→U12 connection, i.e. 8 DQ + DQS_T/C + DMI per byte, plus ca0–5, cke, cs, ck_t/c and
reset. CA nets go to the T-point of their two balls. P/N of the same pair are not counted against each other.

**Metrics:**
- **SL:** straight-line crossings.
- **ORD:** escape-order model. Each U7 ball escapes straight toward U12, ordered by x. Each U12 ball is entered from
  its nearest open side (left, bottom or right; the top is the board edge), ordered by perimeter position. A pair
  crosses when the two orders disagree.
- **ORDs:** ORD restricted to pairs in the same U7 escape class (edge rows A/B on F.Cu vs inner rows on stripline).
- **interORD:** ORD between different bytes. These are the crossings that force layer changes.
- **Weights (w…):** ×10 for a crossing between different bytes, ×3 for byte vs CA/CK, ×1 within a byte.

Results at the original position (best pin swizzle for each case). Byte swizzle column: `-`/`A` = BL0/BL1 kept/swapped,
`-`/`B` = BL6/BL7 kept/swapped.

| U12 rotation | Fits? | Byte swizzle | SL | wSL | ORD | interORD | ORDs |
|---|---|---|---|---|---|---|---|
| 0° | no: 17.1 mm courtyard crosses the board edge (y 80.7 < 82.9) | AB (best) | 747 | 4681 | 563 | 322 | 254 |
| 90° | yes, but channel A ends up on the left over BL6/BL7 | -- (best) | 864 | 5934 | 878 | 589 | 454 |
| 180° | no: as 0° | -- (best SL) | 298 | 1137 | 577 | 322 | 335 |
| 180° | no | -B (best ORDs) | 347 | 1846 | 621 | 347 | 167 |
| −90° (original) | yes | -- (old variant A pinout, as routed) | 302 | 1714 | 268 | 105 | 89 |
| −90° | yes | -- | 266 | 1629 | 238 | 105 | 59 |
| **−90°** | **yes** | **-B (variant R)** | **213** | **910** | **229** | **80** | **75** |
| −90° | yes | A- | 275 | 1698 | 282 | 141 | 103 |
| −90° | yes | AB | 222 | 979 | 273 | 116 | 119 |

**Shifting U12 left at −90°** (0.5 mm steps, 0 to −12 mm, byte swizzle -B with re-optimised pins):

| Shift | 0 | −2 | −4 | −5 | **−6** | −6.5 | −7 | −8 | −9 | −10 | −12 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SL | 213 | 204 | 207 | 202 | **204** | 210 | 203 | 206 | 221 | 236 | 248 |
| wSL | 910 | 939 | 859 | 819 | **779** | 748 | 733 | 759 | 769 | 844 | 867 |
| ORD | 229 | 231 | 227 | 229 | **225** | 222 | 228 | 226 | 230 | 227 | 228 |
| mean / max length (mm) | 21.2 / 27.2 | 19.3 / 25.2 | 17.8 / 24.5 | 17.1 / 23.0 | **16.4 / 22.0** | 16.1 / 21.4 | 15.8 / 21.4 | 15.7 / 22.4 | 16.1 / 23.4 | 16.9 / 24.4 | 18.8 / 26.4 |

Notes on the table:
- Lengths are Manhattan, U7 ball to U12 ball.
- ORD (topology) is unchanged by a pure shift. The shift improves geometry: crossings go down, and the mean
  connection length drops by a quarter.
- −6 to −7 mm is best.
  - **−6 mm was chosen.** At −7 mm the decaps at U12's left end (C63/C67/C71) would land on the 1V1 buck output caps
    (C47, R46), and U9 would touch the ball field.
  - The metric difference between −6 and −7 is under 3 %.

The full table, with all positions, is reproducible with the scripts described at the end.

## Chosen configuration ("variant R2")

**Why this one:**
- **−90° is the only orientation that matches the FPGA.** Channel B (rows P–AB) is on the left, over BL6/BL7. CA is in
  the middle, and channel A is on the right, over BL0/BL1. Every other rotation makes at least one byte cross the other
  channel: 3× to 4× more inter-byte crossings in the order model. 0°/180° don't fit between the board edge and U7
  anyway.
- **6 mm left, centred over bank 3A:**
  - channel B now sits directly over BL6/BL7, and channel A over BL0/BL1;
  - weighted straight-line crossings −14 %;
  - mean length 21.2 → 16.4 mm, max 27.2 → 22.0 mm.
- **BL6↔BL7 byte swizzle** (results at −6 mm):

  | Byte swizzle | SL | wSL | ORD | interORD | ORDs |
  |---|---|---|---|---|---|
  | -- | 223 | 978 | 244 | 105 | 65 |
  | **-B (chosen)** | **204** | **779** | **225** | **80** | **71** |
  | A- | 212 | 890 | 286 | 141 | 107 |
  | AB | 193 | 691 | 267 | 116 | 113 |
  | variant R pins, unchanged, at −6 mm | 250 | 1034 | 229 | 80 | 75 |

  - BL7 (U7 edge rows, F.Cu) takes the far byte B0 around U12's left end. BL6 (inner rows) goes straight up to the
    near byte B1, so the bundles nest.
  - AB has slightly fewer straight-line crossings, but 36 more inter-byte crossings in the escape-order model.
- **BL0/BL1 stay as they are.** The 32 BL0×BL1 crossings that remain are inherent: the two lanes are interleaved in U7
  (BL0 rows E–T, BL1 rows M–AB, same x span). Resolve them by layer, BL0 and BL1 on different stripline layers.
- **Pin swizzle:** each lane's DQ are matched in escape order to the byte's balls (see the table below). Compared with
  variant R, 19 U7 pins changed.

**Lane map** (lane pin: U7 ball → net (U12 ball)):

| Lane | Byte | 0 | 1 | 2 | 3 | 4 DQS_T | 5 DQS_C | 6 DMI | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BL0 | A0 | J65 dq0 (B2) | G65 dq1 (C2) | T62 dq7 (B4) | M62 dq6 (C4) | G62 dqs0_P (D3) | E62 dqs0_N (E3) | J59 dm0 (C3) | T56 dq5 (E4) | M56 dq2 (E2) | G56 dq4 (F4) | E56 dq3 (F2) |
| BL1 | A1 | AB62 dq8 (B11) | W62 dq15 (B9) | T65 dq9 (C11) | M65 dq14 (C9) | AB56 dqs1_P (D10) | W56 dqs1_N (E10) | T59 dm1 (C10) | AB48 dq13 (E9) | W48 dq12 (F9) | T51 dq10 (E11) | M51 dq11 (F11) |
| BL6 | B1 | J35 dq27 (U11) | G35 dq28 (U9) | T32 dq29 (V9) | M32 dq26 (V11) | G32 dqs3_P (W10) | E32 dqs3_N (V10) | J27 dm3 (Y10) | T24 dq25 (Y11) | M24 dq30 (Y9) | G24 dq24 (AA11) | E24 dq31 (AA9) |
| BL7 | B0 | B33 dq19 (U2) | A36 dq20 (U4) | B30 dq18 (V2) | A33 dq21 (V4) | B28 dqs2_P (W3) | A30 dqs2_N (V3) | A25 dm2 (Y3) | A22 dq17 (Y2) | A23 dq23 (AA4) | B22 dq22 (Y4) | A20 dq16 (AA2) |

**Quartus strings:** each list is ordered by lane pin 0,1,2,3,8,9,10,11, and each value is the x32 DQ index (channel B
= 16 + n).

```
BYTE_SWIZZLE_CH0=0 1 X X X X 3 2;PIN_SWIZZLE_CH0_DQS0=0 1 7 6 5 2 4 3;PIN_SWIZZLE_CH0_DQS1=8 15 9 14 13 12 10 11;PIN_SWIZZLE_CH0_DQS2=19 20 18 21 17 23 22 16;PIN_SWIZZLE_CH0_DQS3=27 28 29 26 25 30 24 31;
```

## Move to −6 mm: what changed on the PCB

**Done by script (pcbnew), then the board was saved.** `SaveBoard` reorders the whole file; that is expected on this
branch.

- **U12 block, moved by exactly −6.000 mm in x**, so every cap keeps its position relative to the balls:
  - U12;
  - all 33 B.Cu parts under it: 30× 100 nF 0201 between the balls, C48 22 µF (VDD1 1V8) at the top edge, C69, and the
    reset pull-down R44 (1k);
  - the 111 power/GND via-in-pad fan-out vias (1V1 46, GND 57, 1V8 8) and the 36 short fan-out tracks on F/B/In3.
- **Decoupling, following JEDEC / 821801 practice:**
  - The small 100 nF caps stay right under the balls of each supply group, on via-in-pad.
  - VDD1 has C48 22 µF next to the package.
  - VDD2/VDDQ (1V1) bulk is the 1V1 buck output bank (C47, C216, C217, C165, C164, 22 µF each). It is now 1–5 mm from
    U12's left edge (it was ~7–11 mm).
  - There are no 1 µF parts in the schematic, and none were added.
- **ZQ resistor R43** (240R, F.Cu) moved −5.55 mm, together with its 1V1 via and the ZQ track. This also clears its old
  courtyard overlap with U12.
- **100 MHz refclk chain:**
  - R25/R26 (33R) and C8/C9 (AC coupling) moved 1.1 mm down, clear of the moved decaps C82/C52 and R44.
  - U9 → R → C and C8/C9 → U7 were re-routed on B.Cu as before, 0.1 mm wide, with P/N kept in order.
  - refclk P/N from C8/C9 to B55/A58 is now 9.35/9.83 mm (was 10.09/9.71). U9, R27/R28, R244/R245 and C249/C250 did not
    move.
- **Bank 3A VCCIO_PIO (1V1):**
  - checked; unchanged. The 4 U7 balls (AR37/AR40/AW34/AW40) have C218–C221 100 nF directly under them, on the In6
    1V1 plane.
  - The In6 plane still covers both U7 bank 3A and U12.

**Planes** (checked with `board.Zones()`):

| Layer | Zone | Role here | Change |
|---|---|---|---|
| In1, In4 | GND `gndflood` | reference for F.Cu/In2 and In5 | removed the 0.1 mm 1V8 track on In4 from under U7 to U12's VDD1 ball (156.3,108.1 → 162.2,93.7). It cut the In4 GND plane under the LPDDR4 escape, and it was redundant with In3. |
| In3 | 1V8 `1v8_flood` | VDD1 supply; second reference for In2 | no outline change; it covers U12 (x ≥ 148.3) and the whole escape area |
| In6 | 1V1 `lpddr1v1` | VDD2/VDDQ + VCCIO_PIO_3A; reference for In5/B.Cu | no outline change; it covers U12 and bank 3A |
| In6 | 1V8 `1v8` (priority 2) | none | **deleted**. It sat under `lpddr1v1` (priority 4) and filled only 0.48 mm² of slivers. |
| B.Cu | `1v1bottom`, `1v1gnd`, `5v0_flood` | buck output / 5 V | no change; U12's left-end decaps stay ≥ 0.35 mm from them |

- **Refill:** all zones were refilled with `ZONE_FILLER`. This also cleared the stale fill left behind by the removed
  LPDDR4 vias and the old In6 dq8/dq23 tracks.
- **Result:** the GND planes on In1 and In4, In3 1V8 and In6 1V1 are solid under U12 and the U7→U12 corridor. The
  only openings are the via antipads.

**Checks:**
- `iobank3`: 19 labels renamed relative to variant R, as a permutation.
  - Netlist diff: only those 19 U7 pins changed.
  - ERC is identical (326).
- `kicad-cli pcb drc --schematic-parity`: **0 parity issues, 99 violations (was 171), 120 unconnected (was 120)**.
  - The 74 violations that went away were stale zone fills, mostly J3 pads vs the GND planes.
  - The 2 that look new are the same power-corner issues reported in a different form: L4/`pg_all` and L2/U8 mask.
  - No new violations at U12, its caps or the refclk chain.
  - The unconnected items are the 64 unrouted LPDDR4 connections plus the old 56 non-LPDDR ones. The pairs are
    identical; KiCad only reports some of them from different endpoints.

## Geometry (variant R2 placement)

U12 sits above U7, rotated −90°.
- Its courtyard is x 151.25–168.34, y 83.24–95.33. The board edge is 0.4 mm above it.
- U7's courtyard starts at y 99.62.
- F.Cu to the left of U12 (x 144–151) is free, which is the BL7 route around the left end.

**U12, channel A (right, x ≈ 163.4–166.6 mm):**

| Byte | Position | Balls |
|---|---|---|
| A0 | far, top, y ≈ 85.7–87.3 | B2…F4, DQS D3/E3 |
| A1 | near, y ≈ 91.3–92.9 | B9…F11, DQS D10/E10 |

**U12, channel B (left, x ≈ 153.0–156.2 mm):**

| Byte | Position | Balls |
|---|---|---|
| B0 | far | AA2…U4, DQS W3/V3 |
| B1 | near | AA9…U11, DQS W10/V10 |

- **CA/CK:** in the middle, x ≈ 157.5–162.1.
  - ca0/ca1/cs/cke are on the far side (columns 2/4).
  - ca2–5 and CK are on the near side (columns 8–11).
- **Empty bands** (correcting the earlier text): columns 6–7 and rows L–M are depopulated.
  - That leaves a 2.4 mm-pitch gap between columns 5 and 8 (y 88.1 → 90.5) across the whole package.
  - It also leaves a 1.95 mm gap between rows N and K, down the middle between the channels.
  - Both bands are mostly free; only a few GND stitching vias sit in them. They are useful for reaching the far bytes and
    ca0/ca1 on inner layers.

**U7 lanes** (U7's top edge faces U12):

| Lane | U7 rows | Position | Carries (variant R2) |
|---|---|---|---|
| BL7 | A/B | edge rows, x 150.9–155.5 | B0 (far), F.Cu around U12's left end |
| BL6 | E–T | x 152.5–155.3 | B1 (near), stripline straight up |
| BL0 | E–T | x 160.9–163.7 | A0 (far) |
| BL1 | M–AB | x 158.8–163.7 | A1 (near); deepest, interleaved with BL0 |

## Reroute plan

1. **Channel B first.**
   - BL7 → B0 on F.Cu: leave U7's edge rows, run left/up around U12's left end, and enter B0 from the left. The
     leftmost U7 ball (A20) goes to the outermost ball (AA2).
   - BL6 → B1 on one stripline layer (In2 or In5), straight up, entering B1 from below or the left with via-in-pad.
2. **Channel A.**
   - BL0 → A0 and BL1 → A1 on the two stripline layers, one lane per layer (the interleave crossing is inherent).
   - Both go straight up (channel A is now directly above them), past CA, to U12's right end.
   - A0 (far) enters from the right end or from the middle band; A1 from below or the right.
3. **CA/CK/CKE/CS:**
   - CA pins on U7's edge rows: F.Cu out, then B.Cu as before, with a short T to the H/J and P/R balls.
     The refclk pair now runs on B.Cu at y 95.5–97.6 below U12, so cross it on F.Cu or the inner layers.
   - ck from G42/J42 as a stripline pair. The far-side ca0/ca1/cs/cke are reached through the middle band.
4. **Each DQS on its byte's layer and vias.** No P/N swap. Length-match each byte to its DQS with the existing tuning
   profiles.
5. **Checks:**
   - DRC and schematic parity;
   - the length-tuning report (`LPDDR4_DELAY_MATCHING.md`);
   - re-run the lane-by-byte check: each lane carries one memory byte, with DQS/DMI on pins 4/5/6.

If the reroute finds a better DQ order within a lane, any order is legal. Relabel `iobank3` to match, sync the U7 pad
nets, and regenerate `PIN_SWIZZLE_CH0_DQS*` (see the scripts below).

## Quartus check

The test project is in `~/dev/agilex5_emif_test` (not in this repo):
- Quartus Pro 26.1.1, A5EB013BB23BE6S;
- `emif_io96b_hps` 5.0.0, LPDDR4 1×32, 1 rank, 4 Gb per channel;
- 1600 MT/s with a 100 MHz refclk.

**Variant R2 (this branch, current, 2026-10-25):** synthesis and the full fitter pass (0 errors, the same 2
warnings).
- The swizzle string is in the generated `emif_io96b_hps.ip`.
- The pins agree with the exported KiCad netlist (44/44).
  `BYTE_SWIZZLE_CH0=0 1 X X X X 3 2;PIN_SWIZZLE_CH0_DQS0=0 1 7 6 5 2 4 3;PIN_SWIZZLE_CH0_DQS1=8 15 9 14 13 12 10 11;PIN_SWIZZLE_CH0_DQS2=19 20 18 21 17 23 22 16;PIN_SWIZZLE_CH0_DQS3=27 28 29 26 25 30 24 31;`

**Variant R (superseded; U12 at its old position):** synthesis and the full fitter pass (0 errors). The 2 fitter warnings are
the same as in variants A/B: the SDC refclk duplicate and ignored assignments.
- The swizzle string is in the generated `emif_io96b_hps.ip`.
- Fitter pin report: e.g. LPDDR4_DQ[24] on M32 in `gen_byte_conns[6]`, LPDDR4_DQS[2] on B28 in BL7.
- The pins were generated from the new pin table. They were checked against the exported KiCad netlist: all 44
  DQ/DQS/DMI agree.
- Note: `REFCLK` has to be passed as `100.0`. With `100`, the IP rejects it as out of range.
  `BYTE_SWIZZLE_CH0=0 1 X X X X 3 2;PIN_SWIZZLE_CH0_DQS0=0 1 7 6 4 5 2 3;PIN_SWIZZLE_CH0_DQS1=8 9 15 14 13 11 10 12;PIN_SWIZZLE_CH0_DQS2=19 21 22 20 17 18 23 16;PIN_SWIZZLE_CH0_DQS3=28 29 30 24 27 26 25 31;`

**Variant A, old board (2026-10-24):** passes synthesis and the full fitter.
- The pinout is ball-for-ball the DE25-Nano's, and so is its swizzle:
  `PIN_SWIZZLE_CH0_DQS0=5 4 0 7 1 6 2 3;PIN_SWIZZLE_CH0_DQS1=15 8 14 9 12 13 11 10;PIN_SWIZZLE_CH0_DQS2=18 22 19 20 21 23 16 17;PIN_SWIZZLE_CH0_DQS3=27 29 28 26 24 25 31 30;`

**Variant B, BL6↔BL7 with the earlier pin order (2026-10-24):** the IP accepts the byte swizzle, and synthesis and
fit pass:
  `BYTE_SWIZZLE_CH0=0 1 X X X X 3 2;PIN_SWIZZLE_CH0_DQS2=21 20 18 19 17 22 23 16;PIN_SWIZZLE_CH0_DQS3=26 29 27 28 25 24 30 31;` (DQS0/1 as in A).
- In qsys-script, write the byte list with spaces. With commas it is mangled and generation fails.

**Negative control:** variant B pins without the byte swizzle make the fitter fail (`Error 14566 … 2 BYTE(s)`), so the
placement check is real.

**Other results:**
- **Refclk:** 100 MHz is legal at 800 MHz (1600 MT/s) and 1066.667 MHz (2133 MT/s), the only two rates the IP allows on -6S.
- **Refresh timings:** set tRFCab 130 ns, tRFCpb 60 ns and tXSR 137.5 ns through the IP's JEDEC override table. Without
  that, the IP keeps the DE25-Nano's 8 Gb-per-channel values.
- **Reset Release IP:** add it in the real design (Critical Warning 20759).

## Reproducing

- **Exploration scripts:** pcbnew pad dump → `evalcfg.py` (the metrics above) → `apply.py` (label permutation,
  copper strip, U7 pad re-net) → `move.py` (block move, refclk chain, planes, refill, save).
  - These ran from a scratch directory and are not in the repo. The method is fully described above.
- **Quartus:**
  - `~/dev/agilex5_emif_test/src/u7_bank3_pins_reroute2.csv` is the variant R2 pin table (net → U7 ball).
    `..._reroute.csv` is variant R.
  - `scripts/build_csv.sh` is a copy of `build.sh` that takes `CSV=`.
  - Run: `CSV=$PWD/src/u7_bank3_pins_reroute2.csv REFCLK=100.0 TAG=_reroute2 scripts/build_csv.sh A`. `gen_pins.py`
    variant A takes the balls as given in the CSV and derives the byte/pin swizzle from them. Output goes to
    `varA_reroute2/`.
