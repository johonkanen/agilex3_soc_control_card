# Verifier v1_power: power and schematic claims

Board state: commit `ceb2746` (`review/inputs/COMMIT`, same as HEAD; U16/U18 are AP61203Z6 in this netlist).
Sources: `review/inputs/netlist.xml`, `agilex_3_soc.kicad_pcb` (read via pcbnew, read-only), Altera 813266 (2026.04.24),
813161 (2026.09.08), 813918 (2026.08.10), 821801 (2026.06.12), datasheets in `docs/datasheets/`, JLC API (2026-11-01).
Scratch files (text extracts, netlist and board helper scripts): `review/work/v1_power/`.
Device: A5EB013BB23BE6S, so E-Series, -6S: Table 32 in 813266 and Table 13 in 813918 apply.

Page numbers below are PDF pages.

## Summary

| Claim | Verdict | Severity | Fix type |
|---|---|---|---|
| A1-01 | CONFIRMED WITH CORRECTION (4 filter nodes, FB + 2x 47 uF; not 7 nodes / 4.7 uF + 100 nF) | SHOULD | new parts + copper (split balls off the planes) |
| A1-02 / A2-04 | CONFIRMED (and a bit worse: U42 also has an internal 71 k pull-down; the conclusion does not change) | SHOULD | value swap R247, C259 DNP |
| A2-01 | CONFIRMED | SHOULD | new parts + copper (input split) |
| A2-02 | CONFIRMED | SHOULD | copper only (tie Y2.1 to Y2.4), or one new resistor |
| A2-03 | PARTLY REFUTED. JTAG: refuted (the U1 inputs have internal 71 k pull-downs, so they sit low and do not float). UART: confirmed with correction (RX sits at a constant low, a break condition, not random noise) | SHOULD (UART), INFO (JTAG) | one new resistor (UART) |
| A2-05 | CONFIRMED (the datasheet also gives no PG state for EN low) | SHOULD | copper only (re-net R65.2 from 5V0 to 1V8) |
| A2-06 | CONFIRMED | SHOULD | 2 new 0402 parts + copper |
| A2-07 | CONFIRMED WITH CORRECTION (the ranges in the claim are the computed worst-case outputs, not the Agilex windows; 1V2 and VCORE pass; 3V3 still uses the PFM AP61202) | SHOULD (1V8, 3V3), INFO (1V1, 1V2, VCORE) | value swap (0.1 % resistors); optionally U8 to AP61203 |

Counts: 0 BLOCKER, 7 SHOULD (A2-03 rated by its UART half), plus INFO items inside A2-03 and A2-07.

---

## A1-01: PLL/ADC supply balls without isolation filters

**Verdict: CONFIRMED WITH CORRECTION.** The missing filters are real. The proposed topology was wrong: Altera asks for
four filter nodes (not seven), each made of one ferrite bead and 2x 47 uF 0603 (not 4.7 uF + 100 nF).

**Severity: SHOULD.** 813266 says "must ... with proper isolation filtering" for VCCPLLDIG_SDM and asks for filtering
on all seven balls. Leaving it out is unlikely to stop the board, but it puts switcher noise straight onto the PLL supplies.

**Evidence**
- Netlist (`u7_balls.csv`): VCCPLL1_HPS BF57, VCCPLL2_HPS BF52, VCCPLL_SDM CL46 and VCCADC CG52 are on net `1V8`
  (93 nodes). VCCPLLDIG1_HPS BB54, VCCPLLDIG2_HPS BB52 and VCCPLLDIG_SDM CL49 are on `VCORE`. No series element
  sits on any of them: the only ferrite bead on the board, FB1, is in the PHY 3V3 path.
- 813266 Table 12 (p.24-26): "VCCPLLDIG_SDM must be sourced from the same regulator as VCCL_SDM with proper
  isolation filtering". VCCPLL_SDM: "With proper isolation filtering ... same regulator as VCCPT". VCCADC: "Tie this
  pin to VCCPT with proper isolation filtering".
- 813266 Table 17 (p.44): VCCPLLDIG1/2_HPS "Connect this to the VCCL_HPS with proper isolation filtering". VCCPLL1/2_HPS
  may share a regulator with VCCPLL_SDM.
- 813266 Table 32 (p.70-71, -6S): "Filter" in the sharing column for VCCPLLDIG1/2_HPS, VCCPLLDIG_SDM, VCCPLL1/2_HPS
  and VCCADC/VCCPLL_SDM.
- What Altera asks for: 821801 §10.4 (p.127-130), Table 66 / Table 67 and Figures 120-123:
  - Fig 120: VCCL -> FB BLM18SN220TZ1 (4 mOhm) -> VCCPLLDIG1_HPS + VCCPLLDIG2_HPS, C1 = C2 = 47 uF 0603.
  - Fig 121: VCCL -> FB BLM18SN220TZ1 -> VCCPLLDIG_SDM, 2x 47 uF 0603.
  - Fig 122: P1V8 -> FB BLM18KG260TN1 (7 mOhm) -> VCCPLL1_HPS + VCCPLL2_HPS, 2x 47 uF 0603.
  - Fig 123: P1V8 -> FB BLM18KG260TN1 -> VCCADC + VCCPLL_SDM, 2x 47 uF 0603.
  - "You can design the filter by combining or splitting these four power rails". The DC drop across the bead must
    be about 0.5 % or less. Remote sense must be taken before the filter, which it is here: VCCLSENSE BN46 sits on the
    package VCC.
  - Table 63 (p.121-122): additionally 1x 1 uF 0201 bottom-side cap per rail (VCCPLL1/2_HPS, VCCPLLDIG1/2_HPS,
    VCCPLLDIG_SDM, VCCADC, VCCPLL_SDM).
  - The only exemption is "If the power rail is using LDO, you do not need to use the LC filter". Here 1V8 comes from
    the AP61203 buck and VCORE from the TPS548A28 buck.
- Board: the balls sit under the BGA (BB52/BB54 at 159.7-160.5, 110.8; BF52/BF57 at 159.7/161.2, 111.6; CL46/CL49/CG52 at
  158.2-159.7, 116.2-117.0). The bottom side under them is fully populated with 100N decoupling caps on VCORE/1V8.

**Fix (new parts + copper)**
- Four new nets: `VCCPLLDIG_HPS_F` (BB52, BB54), `VCCPLLDIG_SDM_F` (CL49), `VCCPLL_HPS_F` (BF52, BF57) and
  `VCCPLL_SDM_ADC_F` (CL46, CG52). Each ball via needs an antipad in the VCORE/1V8 plane and a short trace on B.Cu or
  an inner layer to its node.
- Per node: 1x ferrite bead in series from the source plane, plus 2x 47 uF 0603 on the filtered side.
  - Bead: BLM18KG260TN1D, C88981 (extended, 59.8k free, 7 mOhm, 6 A). BLM18SN220TZ1D C710393 has 0 free. At the PLL
    currents (tens of mA) the drop is < 1 mV, so the KG260 can also serve the two VCORE nodes.
  - Capacitor: GRM188R60J476ME15D C140782 (extended, 247k free) or CL10A476MQ8QRNC C730416 (83.5k free).
- Per ball, a 1 uF 0201 at the ball on the filtered net. Existing parts can be reused by re-netting: C150, C147 or C136
  next to BB52/BB54, C193 next to CG52/CL46, C156 next to CL49. Swap them to 1 uF 0201 C272877 (already in the BOM).
- In total: 4 beads + 8x 0603 caps outside the BGA plus layout work. If space forces it, merge into two nodes
  (VCORE side and 1V8 side), which 821801 explicitly allows.

---

## A1-02 / A2-04: `eth_rst_n` idle level and C259 edge rate

**Verdict: CONFIRMED.** One correction that does not change the conclusion: U42's data pins also have a 71 kOhm
internal pull-down in parallel with R247.

**Severity: SHOULD.** During HPS configuration/boot the PHY reset input of U42 sits inside the undefined band, and while
C259 is fitted, every software edge breaks U42's input edge-rate limit by more than 1000x. The fix is a zero-cost value swap.

**Evidence**
- Netlist: `/eth_rst_n` = U7 AC75 (HPS_IOB_2, GPIO1_IO1), R247 10k (0201, C473048) to GND, C259 1 uF (0201, C272877)
  to GND, U42.12 B3. U42 DIR3 = GND, so B3 -> A3 = `/phy_rst_n` -> U10.12 PHYRSTB. U42 VCCB = 1V8, VCCA = 3V3, OE = GND (enabled).
- HPS pin state: 813266 note 10 (p.74), "All I/Os in the HPS pins are configured as the Schmitt trigger input with
  20-kOhm weak pull-up enabled after the device is powered up and during HPS or device configuration". 813918 Table 29
  (p.44): 20 kOhm RPU = 15 / 20 / 25 kOhm at VCCIO_HPS 1.8 V +-5 %.
- U42 input: SN74AXC4T774 §6.3 (p.5), VIL(data) = 0.35 x VCCI for VCCI 1.1-1.95 V, i.e. 0.60-0.66 V on 1V8, and
  delta-t/delta-v max 10 ns/V. §7.3.9 (p.21): 71 kOhm typical static pull-down on every data I/O.
- Idle level, with R247 10k parallel to the internal 71k (8.77 kOhm) against the 15-25 kOhm HPS pull-up, at 1.71-1.89 V:
  0.44-0.70 V. The worst case is above VIL(max) = 0.60 V at 1.71 V and 0.66 V at 1.89 V. Without the internal
  pull-down the range is 0.51-0.76 V, as the claim says.
- Edge rate: the HPS driver (tens of ohms) into 1 uF gives a time constant of tens of microseconds, i.e. about
  10-50 us/V through the threshold, against the 10 ns/V limit. TI §7.3.1 (p.20) says slow edges cause "excessive
  current consumption and oscillations".
- PHY timing without C259: RTL8211F §7.17 (datasheet p.30) requires PHYRSTB low for at least 10 ms and 50 ms before
  MDIO access. R247 holds the line low from the moment 1V8 is up. 3V3 (U42 VCCA, PHY supply) comes later (Group 2B).
  The line stays low until software drives GPIO1_IO1 high, which happens after SDM configuration plus FSBL/U-Boot,
  well over 10 ms. C259 contributes nothing to that; the 50 ms wait belongs in the device tree (`reset-assert-us` /
  `reset-deassert-us`). HPS_PINMUX.md already uses `reset-gpios = <&gpio1 1 GPIO_ACTIVE_LOW>`.

**Fix (value swap on existing pads)**
- R247: 10k -> 4.7k 0201, 0201WMF4701TEE C270346 (extended, 695k free). The idle level becomes 0.41-0.43 V at
  1.89 V (4.41 k against 15 k), below VIL 0.60 V with about 0.17 V margin. When the HPS drives high, the extra load is
  0.38 mA. For more margin, 3.3k gives 0.32 V.
- C259: DNP. Keep the pads.
- Bring-up note: set `reset-assert-us = <10000>` and `reset-deassert-us = <50000>` (or more) on the PHY node.

---

## A2-01: No protection on the 5V0 input

**Verdict: CONFIRMED.**

**Severity: SHOULD.** Both inputs are unkeyed headers, and one reversed plug-in puts -5 V on every regulator and on the
SoC rails. That destroys parts the user has already bought (U7, U11, U12, U2) and the assembled board.

**Evidence**
- Netlist: J4 (C2937625, PZ254V-11-03P plain 2.54 mm header): pin 1 GND, pin 2 GND, pin 3 5V0. J6 (C22438118, HX
  PZ1.27-2x3P straight header, no shroud): pins 1/3/5 GND, 2/4/6 5V0. Rotating J6 by 180° maps 1<->6, 3<->4, 5<->2,
  which swaps every GND with every 5V0. Reversing J4's 3-pin cable puts 5V0 on pin 1 and GND on pin 3.
- The 5V0 net (25 nodes) holds only connectors, regulator inputs and caps. There is no fuse, diode, FET or TVS anywhere
  in the netlist.
- Absolute maxima on 5V0: U6 NCP163 VIN and CE -0.3 to 6 V (datasheet p.2; CE is tied to 5V0). AP61202/AP61203 VIN
  -0.3 to 6.5 V DC / 7 V 400 ms, with OVP shutdown at 6.3 V typ (datasheet p.5). TPS548A28 VIN 18 V (p.5, but EN is
  at most 6 V). So the lowest maximum is 6.0 V (U6), and every IC is rated at most -0.3 V reverse.
- 5V0 caps: C157/C158/C160/C161 22 uF 6.3 V (C415703), C224-C227 2.2 uF CL05A225MQ5NSNC 6.3 V (C12530). The rest
  (C10, C162, C266, C267) are 16-50 V.
- A hot-plug into an MLCC-only input through a cable can ring up to about twice the supply voltage, i.e. about 10 V.
  That is closed-form LC reasoning, not simulated.

**Fix (new parts + copper)**
- Smallest effective fix, all near J4/J6 (x about 191-195, y 136-146, front side):
  1. Split the connector pins onto a new net `5V0_IN` (J4.3, J6.2/4/6).
  2. Reverse-polarity P-FET from `5V0_IN` to `5V0`: AO3401A, C15127 (JLC basic, 1.68M free, -30 V, 60 mOhm at
     -4.5 V). Drain on `5V0_IN`, source on `5V0`, gate to GND through 10k C25744 (basic). At about 1.5 A the drop is
     90 mV and the dissipation 0.14 W. Vgs = -5 V is within its +-12 V rating, so no zener is needed.
  3. TVS on `5V0`: SMF5.0A, C193402 (extended, 489k free, SOD-123FL, VBR 6.4 V min). It clamps hot-plug ringing and
     ESD. It does not hold steady-state over-voltage below 6 V.
- If steady over-voltage (a wrong bench supply) must also be covered, a single eFuse with adjustable OVP and reverse
  blocking replaces items 2 and 3, e.g. TPS259474LRPWR C2864845 (extended, 3.5k free, 2x2 QFN). I did not verify it:
  its datasheet is not in `docs/`, so check its reverse-polarity rating before using it.
- Cheapest mitigation with no copper change: shrouded or keyed mates, plus a marking on the cable. It does not protect
  against a wrong source voltage.

---

## A2-02: Y2 OE pin floating

**Verdict: CONFIRMED.**

**Severity: SHOULD.** This is the only clock for the SDM (via R246 to SDM_OSC_CLK_1 DB72) and the HPS (AN67). It
goes against the datasheet's recommendation, and fixing it costs one short trace.

**Evidence**
- Netlist: Y2 SIT8924BA-78-18E-25.000000 (C17247134). Pin 1 is on `unconnected-(Y2-NC-Pad1)`, pin 4 on 1V8, pin 3 on
  `/osc_clk_25` (U7 AN67, and R246 to `/sdm_clk25` U7 DB72). The symbol description "NC pin1 (always enabled)" is wrong
  for this part number.
- SiT8924 ordering code (datasheet p.15): the letter after the voltage is the feature pin, "E" Output Enable, "S"
  Standby, "N" No Connect. So `-18E` is the OE variant.
- Datasheet p.2, Table 3 note 3: "In OE or ST mode, a pull-up resistor of 10 kOhm or less is recommended if pin 1 is
  not externally driven. If pin 1 needs to be left floating, use the NC option." The internal pull-up is only 100 kOhm
  typ (Z_in, p.2), and L disables the output (high-Z).
- The "N" variant in 2016 size at 1.8 V and 25 MHz is not stocked at JLC (search `SIT8924BA-78-18N-25`: 0 hits).

**Fix (copper only)**
- On B.Cu, draw a trace from Y2 pad 1 (170.09, 111.86) to Y2 pad 4 / 1V8 (170.09, 110.66), 1.2 mm straight. Tying OE
  directly to VDD meets "10 kOhm or less". Update the symbol description.
- Alternative: a 10k 0201 (C473048, already in the BOM) from pad 1 to pad 4. That is a new part with no benefit over the trace.

---

## A2-03: Floating 3.3 V-side inputs of U1 (JTAG) and U42 (UART RX)

**Verdict: JTAG part REFUTED. UART part CONFIRMED WITH CORRECTION.**

**Severity: SHOULD for the UART half** (deterministic autoboot abort and a constant break on the console when J10 is
unplugged; fix is one resistor). **INFO for JTAG.**

**Evidence**
- Netlist: J1.1/2/3 -> U1 A1/A2/A3 (DIR1/2/3 = 3V3, A -> B), with no other part on those nets. U1 B1/B2/B3 drive
  `/tdi` CC67, `/tck` CC64 and `/tms` CY67; the B-side pull resistors R19 / R22 1K0 / R21 are overridden by U1's
  push-pull outputs. J10.2 -> U42 A2 (DIR2 = 3V3) -> B2 `/hps_uart0_rx` -> U7 AJ75 (UART0 RX).
- SN74AXC4T774 §7.3.9 (p.21): "71 kOhm typical integrated weak pull-downs on all data I/Os. This feature allows all
  inputs to be left floating without the concern for unstable outputs or increased current consumption ... If an
  external pull-up is required, it should be no larger than 7 kOhm".
- So the A-side inputs do not float. They sit low, and U1 drives TDI, TCK and TMS low.
- JTAG: with TCK held low there are no clock edges, so the TAP does not move. TCK low is the recommended idle state.
  The residual issues are cosmetic: TMS sits low instead of the usual pull-up, and R19 and R21 (10k to 1V8) each
  draw about 0.18 mA against U1's low output.
- UART: RX held low is a continuous break, not noise. The UART receives a 0x00 with BI/FE set, and U-Boot's
  `tstc()` sees a character during the boot delay and stops autoboot. A low RX is guaranteed on every boot without a
  cable, so this is more certain than the claim stated.

**Fix**
- UART (new part + copper): 4.7k 0402 from `/debug_status/hps_uart0_rx_3v3` (U42.4 / J10.2) to 3V3, 0402WGF4701TCE
  C25900 (JLC basic). It must be 7 kOhm or less per TI §7.3.9. The idle level is 3.3 x 71/(71+4.7) = 3.10 V, above
  VIH 2.0 V.
- JTAG: no change needed. Optional: a 4.7k pull-up from `jtag_tms_3v3` to 3V3 (C25900), so that TMS idles high.

---

## A2-05: R65 pulls the Group-2B enable up to 5V0

**Verdict: CONFIRMED.** One addition: the datasheet does not state PG behaviour with EN low (shutdown) either, and it
says PG has an internal 5 MOhm pull-up to VIN.

**Severity: SHOULD.** If PG is not actively low in that state, the Group 2B rails (1V1, 3V3, 1V2) can come up as soon
as 5V0 reaches the converters' POR (about 2.0-2.25 V), long before VCORE (U15 enables at 4.2 V). That violates the
mandatory Group 1 -> 2A -> 2B order. Moving one pad's connection removes the dependency.

**Evidence**
- Netlist: `Net-(U16-EN)` = R65.1 (47K, C25792; R65.2 on 5V0), U18.6 PG, and EN of U16 (1V1), U8 (3V3) and U19 (1V2).
  U18 (1V8) EN = `/pwr_rails/EN` = U15 PGOOD (R58 10k to `tda_vcc`). U15 EN = 5V0 x 10/34.3 (R291/R292), on at 4.2 V.
- AP61203 datasheet (DS44251 Rev 3-2):
  - p.3 pin table: PG is "pulled to GND when the output voltage is out of its regulation limits or during soft-start".
  - p.14 §4: "actively held low during the soft-start period ... The PG pin is connected to VIN through an internal
    5 MOhm pull-up resistor".
  - p.5: POR rising 2.00 typ / 2.25 max V, UVLO 1.84 V, EN high 0.91 V, IQ in shutdown 0.1 uA.
  - Nothing says PG is held low below POR or in shutdown (EN = 0).
- 813161 §3.2 (p.10): Group 2A only after all of Group 1 reach 90 %, and Group 2B only after all of Group 2A reach
  90 %. VCCIO_PIO (1V1, 1V2), VCCIO_HVIO (3V3) and VCCRCORE (1V2) are Group 2B (Table 3).
- With R65 on 5V0, any time U18's PG output is not actively low (VIN below U18's POR, or possibly while U18 is in
  shutdown), EN(2B) is pulled to 5V0 (> 0.91 V). The 2B converters, which have the same VIN and a possibly lower POR,
  then start.

**Fix (copper only)**
- Move R65 pad 2 (146.79, 133.80, B.Cu) from 5V0 to 1V8. The nearest 1V8 copper is the F.Cu track at (148.66, 131.03)
  next to R249, about 3.3 mm away, and a 1V8 via at (147.64, 128.79). Keep 47k.
- After the change, EN(2B) cannot rise before 1V8 exists, and 1V8 only exists after VCORE PGOOD. During U18's soft
  start PG is documented as actively low. The leakage through U18's internal 5 MOhm to 5V0 gives at most about 50 mV on
  EN against 47k to a discharged 1V8. All pins stay within VIN + 0.3 V.

---

## A2-06: VCORE remote sense has no local fallback

**Verdict: CONFIRMED.**

**Severity: SHOULD.** The probability is low (one BGA ball or one sense trace), but the consequence is VCORE driven
towards 5 V into a 1.21 V absolute-maximum rail with no OVP, which destroys U7. The fix is two basic 0402 resistors.

**Evidence**
- Netlist: `/soc_power/vcoresense_P` = U7 BN46 VCCLSENSE, R2 2.55k (top, to FB) and C198 220p. `/pwr_vcore/vcoresense_N`
  = U7 BN44 GNDSENSE, U15.6 VSNS-, R1 10k (bottom) and C199 68n (SS/REFIN). Neither net has any other connection to
  VCORE or GND.
- If BN46 or its trace opens, FB is pulled to VSNS- through R1, so FB reads about 0 V. If BN44 opens, VSNS- and the
  divider bottom float.
- TPS548A28 §7.3.12 (p.20): OVP and UVP both monitor "a resistor-divided feedback voltage", i.e. FB (OVP at 116 % of
  VINTREF). With FB at 0 V, OVP cannot trip. UVP is disabled during soft start, so on every start the loop drives
  maximum duty while FB stays below the SS ramp, and VCORE heads towards 5V0 within the soft-start time. UVP only trips
  (FB < 80 % for 68 us) after soft start ends, so the converter enters hiccup and repeats this every 14 ms. The damage
  is done in the first soft start.
- 813918 absolute maximum VCC 1.21 V (Table 1, p.12-14). 813266 Table 12 (p.25) requires that the VCCLSENSE/GNDSENSE
  pair be connected to the regulator's remote-sense inputs, so removing remote sense is not the fix.

**Fix (2 new parts + copper)**
- R_a 10 Ohm 0402 from local VCORE (output-cap side of L1, near C129/C123 at about 157, 130-132) to `vcoresense_P`
  at R2 pad 2 (163.49, 135.24). R_b 10 Ohm 0402 from GND to `vcoresense_N` at R1 pad 2 (165.34, 135.22). Part:
  0402WGF100JTCE C25077 (JLC basic, 2.5M free). The nearest VCORE via is at (156.79, 135.08), about 6.7 mm away.
- Effect with the sense lines intact: about 0.6 mV (60 uA divider current x 10 Ohm), plus a few tenths of a mV from
  sharing the plane drop. With a sense line open, the converter regulates at the local point.

---

## A2-07: DC accuracy of the AP6120x rails

**Verdict: CONFIRMED WITH CORRECTION.**
- The ranges in the claim (1.741-1.861, 1.068-1.132, 3.196-3.437 V) are the computed worst-case converter outputs. I
  reproduce them exactly. They are not the Agilex windows, which are 1.75-1.85, 1.07-1.13 and 3.20-3.40 V.
- With the AP61203 swap, PFM ripple no longer lands on 1V8. 3V3 (U8) and 1V2 (U19) are still AP61202 (PFM).

**Severity: SHOULD for 1V8 and 3V3.** The worst case leaves the window by 9-37 mV before any ripple, and a value swap
on existing pads recovers most of the margin. **INFO for 1V1, 1V2 and VCORE.**

**Evidence**
- AP6120x VFB 0.588 / 0.600 / 0.612 V (CCM, over TJ -40..125 °C, datasheet p.5). The dividers are 1 % thick-film
  (0402WGF...). Worst case: Vout = VFB x (1 + k x (1 +- 1 %)/(1 -+ 1 %)).

| Rail | Converter | Divider | Nominal | Worst case (1 %) | With 0.1 % resistors | Binding load window | Source |
|---|---|---|---|---|---|---|---|
| 1V8 | U18 AP61203 | R82 200k / R80 100k | 1.800 | 1.741-1.861 (fails both sides) | 1.762-1.838 (pass, about 12 mV each side) | VCCPT, VCCPT_HVIO 1.75-1.85 (VCCIO_SDM/HPS/PLL/ADC 1.71-1.89; LPDDR4 VDD1 1.70-1.95) | 813918 Table 13 (p.28-31); H9HCNNN8 p.1 |
| 1V1 | U16 AP61203 | R91 200k / R89 240k | 1.100 | 1.068-1.132 (fails by 2 mV) | 1.077-1.123 (pass, 7 mV) | VCCIO_PIO_3A 1.1 V: 1.07-1.13 (the ±5 % extension in note 49 is only for GPIO/PHYLITE/LVDS-RX, not the HPS EMIF); LPDDR4 VDD2/VDDQ 1.06-1.17 | 813918 Table 13, note 49 (p.31) |
| 3V3 | U8 AP61202 (PFM) | R85 200k / R83 44.2k | 3.315 | 3.196-3.437 (fails, high side by 37 mV) | 3.243-3.387 (pass, 13 mV) | VCCIO_HVIO 3.3 V: 3.20-3.40 | 813918 Table 13 |
| 1V2 | U19 AP61202 (PFM) | R88 200k / R86 200k | 1.200 | 1.164-1.236 (pass, 4 mV) | 1.174-1.226 | VCCIO_PIO_2A / VCCIO_PIO_SDM 1.16-1.24; VCCRCORE 1.14-1.26 | 813918 Table 13 |
| VCORE | U15 TPS548A28 | R2 2.55k / R1 10k | 0.753 | 0.746-0.760 (VINTREF ±0.5 % at TJ 0-85 °C) | n/a | VCC/VCCL_SDM etc. at -6S: 0.7275-0.7725 | TPS548A28 p.6-7; 813918 Table 13 |

- The Agilex limits are "measured between the PCB power and ground ball ... includes both regulator DC ripple and the
  dynamic noise" (813918 note 43). The AP6120x ±2 % reference alone uses 1.8 of the 2.8 % window on 1V8. Even with 0.1 %
  resistors only about 12 mV is left for ripple and load transients. Forced-PWM ripple, estimated in closed form from
  ΔI ≈ 0.89 A and about 65 uF of derated MLCC at 1.3 MHz, is about 1-2 mV plus ESL.
- Statistically (RSS of the ±2 % reference and two 1 % resistors) 1V8 lands at 1.760-1.840. Typical parts will be inside
  the window, but this is not a guarantee.
- 3V3 also sits 15 mV above centre (200k/44.2k), and U8 is still PFM. At the probable light HVIO+PHY load (< 0.43 A,
  half the about 0.86 A ripple current) it runs in PFM all the time, with larger, load-dependent ripple and a VFB that
  the datasheet does not specify in PFM.

**Fix (value swap on existing pads)**
- 1V8: R82 200k 0.1 % RT0402BRD07200KL C728556 (20.8k free), R80 100k 0.1 % RT0402BRD07100KL C852472 (862k free).
- 3V3: R85 200k C728556, R83 44.2k 0.1 % RT0402BRD0744K2L C705633 (7.1k free).
- 1V1 (optional, recovers 7 mV): R91 200k C728556, R89 240k 0.1 % RT0402BRD07240KL C852659 (2.95k free).
- 3V3 (and optionally 1V2): if the bought AP61203 quantity covers it, swap U8 (and U19) to AP61203Z6 (same SOT-563
  footprint, part swap) to remove PFM ripple from VCCIO_HVIO.
- All are extended parts (one feeder fee per unique value). The converter's ±2 % reference stays the dominant term. A
  tighter converter would be the only complete fix, and is not justified given the parts already bought.

---

## For other streams

- AGILEX_POWER_CONFIG_CHECKLIST.md row `1V8` still says "U18 AP61202Z6" and lists "VCCIO_HVIO_6A" on 1V8. The netlist
  has U18 = AP61203 and all VCCIO_HVIO_6A-6H balls on 3V3. The document is stale; the design is fine.
- VCCH_SDM CD54 is on VCORE (0.753 V). 813918 Table 13 allows 0.7275-0.7725 V only "without transceiver"; with GTS it
  is 0.98-1.02. Stream A1 should confirm that A5EB013B has no GTS.

## Coverage

Checked and found as the claims describe, or correct:
- every U7 PLL/ADC supply ball and its net;
- the `eth_rst_n` / `phy_rst_n` nets, U42 DIR/OE strapping, and the RTL8211F reset timing;
- all 25 nodes of 5V0 with their absolute maxima and cap ratings, and the J4/J6 pinout;
- the Y2 net, part code and fan-out;
- the U1/U42 directions and every A-side net;
- the whole enable/PG chain U15 -> U18 -> U16/U8/U19;
- the U15 FB/VSNS network;
- the divider values and resistor tolerances on all four AP6120x;
- Agilex E-Series -6S windows and LPDDR4 windows.

Not checked:
- the 5V0 load current from a power estimate (the AO3401A sizing assumes 1.5 A or less);
- the board space for the A1-01 filter parts and the A2-01 parts (needs a layout pass);
- PG behaviour of the AP6120x below POR or in shutdown (not in the datasheet; would need a bench test or a vendor answer).
