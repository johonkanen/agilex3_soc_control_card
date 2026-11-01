# A2 – Schematic outside U7: power tree, every other IC, connectors

Frozen state: commit `0aa9192` (`review/inputs/COMMIT`), netlist `review/inputs/netlist.xml` (the source of truth for
connectivity and part values). Scratch: `review/work/a2/` (`scripts/dump.py` parses the netlist into `nl.json`,
`scripts/show.py` prints a part pin by pin, `scripts/pg.py` / `page.py` search the page-split datasheet text in `txt/`,
image-only datasheets rendered in `img/`). No project file was edited; nothing was committed.

Document references used below: AP61202 = Diodes DS44251 Rev 3-2; TPS548A28 = TI SNVSBB1D; RTL8211F = Realtek
RTL8211F(I)/FD(I) datasheet Rev 1.4 (printed page numbers); AXC = TI SCES898C (SN74AXC4T774); SiT8924 = SiTime SiT8924B
Rev 1.72; Hynix = H9HCNNN8KUMLHR-NME datasheet (C2912103 PDF); KIOXIA = THGAMVG7T13BAIL (Sept 2021); ISSI = IS25WP128
Rev B4; 813918 / 813161 / 813266 / 813773 = Altera documents in `docs/`.

## Summary

| Severity | Count |
|---|---|
| BLOCKER | 0 |
| SHOULD | 7 |
| INFO | 11 |

- **No connectivity error found** in the power tree, the 16 ICs other than U7, the three oscillators/crystal or the
  connectors. Every pin of U1, U2, U3, U4, U5, U6, U8, U9, U10, U11, U12 (non-DQ), U15, U16, U18, U19, U42, Y2, Y3, Y4,
  J1–J6, J9, J10 was compared against its datasheet pin table. All regulator outputs are at the intended nominal
  voltage, the enable chain gives Group 1 → 2A → 2B, and AS-normal's 10 ms VCCIO_SDM rule is met.
- **SHOULD (7):** 5V0 has no over-voltage / reverse-polarity / fuse protection while J4 and J6 can be mated reversed
  (A2-01); Y2 is the Output-Enable variant with pin 1 floating (A2-02); the 3.3 V inputs of U1 (JTAG) and U42 (UART RX)
  float when nothing is plugged in (A2-03); A1-02 confirmed (A2-04); the 2B enable net is pulled to 5V0 instead of a
  sequenced rail (A2-05); VCORE has no fallback if a remote-sense ball opens (A2-06); the AP61202 cannot guarantee the
  1V8 / 1V1 / 3V3 Agilex windows and runs in PFM on the unfiltered PLL rail (A2-07).
- **Not covered / could not be verified:** layout, decoupling placement, PDN (stream C); footprints, LED/IC
  orientation, stock (stream B). DC-bias derating of the 0402/0201 MLCCs (not in the local datasheets; values below are
  marked assumption). Y3's 12 pF load (its datasheet is a generic series sheet). R41 2.49 kΩ (not in the local RTL8211F
  datasheet). Anything on the mating board behind J3/J6.

## Findings

### A2-01 — SHOULD — 5V0 input has no protection; J4 and J6 can be mated reversed (verified)
- **Where:** net `5V0` = J4.3, J6.2/4/6, U15.10 (VIN), U8/U16/U18/U19.3 (VIN), U6.1 (VIN) and U6.3 (EN), R291, R65
  and capacitors. There is no fuse, TVS, reverse-polarity element or eFuse on the net.
- **Polarity hazard:** J4 (1x3 2.54 mm) is GND/GND/5V0, so a 3-pin cable plugged the other way puts −5 V on the board.
  J6 (2x3 1.27 mm) has GND on the odd row (1/3/5) and 5V0 on the even row (2/4/6). If the mating connector is rotated
  180° or mirrored (bottom-side mounting), the rows swap and the board gets −5 V. I cannot check the mating side.
- **Over-voltage hazard:** the lowest absolute maximum on 5V0 is U6 NCP163 VIN 6.0 V (NCP163 datasheet, Absolute Maximum
  Ratings, p2). The AP61202 is 6.5 V DC / 7.0 V for 400 ms (DS44251 p4); its OVP shuts down at 6.3 V (p5, p14). The bulk
  capacitors C157, C158, C160, C161 (22 µF) and C224–C227 (2.2 µF) are 6.3 V parts (GRM155R60J226ME11D, CL05A225MQ5NSNC).
  A hot-plugged bench lead easily rings above 6 V into an all-ceramic input.
- **Fix:** add an eFuse/load switch with adjustable OVP (about 5.7 V) and reverse blocking, or at least a P-FET reverse
  protection plus a fuse. A plain 5 V TVS clamps near 9 V, so it does not protect U6 on its own. Key J6 mechanically, or
  document its orientation on the silkscreen-free board (e.g. a copper arrow). Use 10 V or 16 V parts for the 5V0 bulk.

### A2-02 — SHOULD — Y2 (SiT8924BA-78-18E) is the Output-Enable variant, but pin 1 is left floating (verified)
- **Where:** Y2.1 = `unconnected-(Y2-NC-Pad1)`; Y2.4 = 1V8; Y2.3 drives `osc_clk_25` (HPS_OSC_CLK AN67) and, via R246,
  OSC_CLK_1 DB72, the configuration clock.
- **Evidence:** SiT8924 p13 ordering code: `…-18E-…` = 1.8 V, feature pin **"E" = Output Enable** (`N` = No Connect).
  p2 Table 2 note 3: "In OE or ST mode, a pull-up resistor of 10 kΩ or less is recommended if pin 1 is not externally
  driven. If pin 1 needs to be left floating, use the NC option." The internal pull-up is only ~100 kΩ (p2, Z_in).
- **Effect:** a noise-coupled low on pin 1 tri-states the output, which stops both the SDM configuration clock and
  the HPS clock. The symbol calls the pin "NC", so the schematic hides the mismatch.
- **Fix:** connect Y2.1 to 1V8 (pin 4 is the adjacent pad), directly or through ≤10 kΩ, or order the `N` variant
  (SiT8924BA-78-18N-25.000000) if JLC can source it.

### A2-03 — SHOULD — U1 and U42 A-side inputs float when J1 / J10 are not plugged in (verified)
- **Where:**
  - U1 (VCCA = 3V3, VCCB = 1V8): DIR1–3 = 3V3, so A1 `jtag_tdi_3v3` (J1.1), A2 `jtag_tck_3v3` (J1.2) and A3
    `jtag_tms_3v3` (J1.3) are inputs. Each net has only the header pin and the U1 pin.
  - U42: DIR2 = 3V3, so A2 `hps_uart0_rx_3v3` (J10.2) is an input. The net has only J10.2 and U42.4.
- **Evidence:** AXC Table 7-1 note 2 (p22): "Pins configured as inputs should not be left floating". §5.3 note 2 (p5):
  unused inputs must be held at VCC or GND. Table 7-1 (p21): OE = L, DIR = H drives the B port.
- **Effect:** U1 drives whatever the floating inputs pick up onto TCK/TMS/TDI of the SDM, overriding R22 (1k TCK
  pull-down) and R19/R21 (10k pull-ups). The JTAG TAP is then clocked at random while the FPGA configures. On U42 the
  HPS UART0 RX sees noise, which can abort U-Boot's autoboot countdown.
- **Fix:** on the 3.3 V side add a 10 kΩ pull-up to 3V3 on `jtag_tdi_3v3`, `jtag_tms_3v3` and `hps_uart0_rx_3v3`, and a
  1–10 kΩ pull-down on `jtag_tck_3v3`. R22/R19/R21 on the 1.8 V side then only matter while 3V3 is off.

### A2-04 — SHOULD — A1-02 confirmed: `eth_rst_n` idle level and edge rate into U42 (verified)
- **Net:** `/eth_rst_n` = U7.AC75 (HPS_IOB_2) + R247 10k to GND + C259 1 µF to GND + U42.B3 (DIR3 = GND, so B→A) →
  `phy_rst_n` → U10.12 PHYRSTB.
- **Idle level:** the HPS weak pull-up is 15–25 kΩ (813918 Table 29, p44; 813266 §1.6 note 10, p74, says it is enabled
  during power-up and configuration). The divider gives 1.8 × 10/(10+25…15) = 0.51–0.72 V (0.76 V at 1.89 V). The
  U42 data-input VIL is 0.35 × VCCB = 0.63 V (AXC §5.3, p5). So `phy_rst_n` is undefined until software drives the pin.
- **Edge rate:** AXC Δt/Δv ≤ 10 ns/V (§5.3, p5). 1 µF on a GPIO gives edges in the 10–100 µs/V range.
- **PHY side:** RTL8211F needs PHYRSTB low ≥ 10 ms for a full reset (Table 5 p9, §7.17 p30). That only works if the
  line is defined.
- **Fix (as A1):** DNP C259, change R247 to 4.7 kΩ: 1.89 × 4.7/19.7 = 0.45 V < 0.63 V. Software then holds the PHY in
  reset until it releases it.

### A2-05 — SHOULD — the Group-2B enable net is pulled up to 5V0, so 2B start-up relies on unspecified PG behaviour (assumption)
- **Where:** U18.6 (PG of the 1V8 buck) = `Net-(U16-EN)` = U8.5, U16.5, U19.5 + R65 47k to **5V0**.
- **Evidence:** AP61202 PG is open drain with an internal 5 MΩ pull-up to VIN (DS44251 p14 §4, p3 block diagram). The
  datasheet does not say whether PG is held low below the VIN POR (2.0 V typ, 2.25 V max, p5). U8/U16/U19 have the same
  POR and an EN threshold of 0.91 V typ (p5). While 5V0 ramps through 2–2.25 V, if U18 releases PG later than U8, U16
  or U19 reach their POR, the 3V3/1V1/1V2 bucks start before VCORE (Group 1). That breaks 813161 Table 3 / p10. A slow
  bench supply makes the window longer.
- **Related, low risk:** U15 PGOOD (pin 9) is pulled up by R58 to its own VCC LDO. TPS548A28 PGOOD is only valid above
  VCC = 1.5 V (SNVSBB1D p8, "Minimum VCC for valid PGOOD output"). While VCC charges from 0.9 to 1.5 V (~0.1 ms), U18 EN
  can briefly see a high.
- **Fix:** move R65's top end from 5V0 to **1V8**. 1V8 only exists after VCORE PGOOD, and 1.8 V is above the 0.91 V EN
  threshold and below EN abs max VIN + 0.3 V. The 2B rails then cannot start early. Check the first board with a scope
  on a slow 5V0 ramp.

### A2-06 — SHOULD — VCORE has no fallback if a remote-sense ball opens (mechanism verified; fix is common practice)
- **Where:** U15 FB divider R2 2.55k from `vcoresense_P` (only U7.BN46 VCCLSENSE) and R1 10k to `vcoresense_N` (U7.BN44
  GNDSENSE + U15.6 VSNS−). No resistor ties `vcoresense_P` to the local VCORE plane or `vcoresense_N` to GND.
- **Evidence:** TPS548A28 output OVP/UVP and PGOOD are all derived from FB (SNVSBB1D p7 "OUTPUT OVP AND UVP", p16). If
  BN46 does not solder (BGA defect) or the sense trace opens, FB is pulled to VSNS− by R1. The loop then drives VCORE
  towards VIN = 5 V, and OVP never trips because FB is 0. That destroys U7.
- **Fix:** 10 Ω (0402) from VCORE at U15's output capacitors to `vcoresense_P`, and 10 Ω from GND to `vcoresense_N`.
  The divider current is 60 µA, so the regulation error stays negligible while the sense path is intact.

### A2-07 — SHOULD — AP61202 rails: worst-case accuracy exceeds the Agilex windows for 1V8, 1V1, 3V3, and PFM ripple lands on the unfiltered PLL rail (verified)
- **Accuracy:** AP61202 VFB = 0.588–0.612 V (±2 %, DS44251 p5) with 1 % dividers (UNI-ROYAL …WGF… = 1 %):

  | Rail | Divider | Nominal | Worst-case DC | Agilex window | Source |
  |---|---|---|---|---|---|
  | 1V8 (U18) | R82 200k / R80 100k | 1.800 | 1.741–1.861 | VCCPT/VCCPT_HVIO 1.75–1.85; Table 32 ±2.5 % = 1.755–1.845 | 813918 p29/p31; 813266 p71 |
  | 1V1 (U16) | R91 200k / R89 240k | 1.100 | 1.068–1.132 | VCCIO_PIO 1.1 V: 1.07–1.13 | 813918 p31 |
  | 3V3 (U8) | R85 200k / R83 44.2k | 3.315 | 3.196–3.437 | VCCIO_HVIO 3.3 V: 3.2–3.4 | 813918 p31 |
  | 1V2 (U19) | R88 200k / R86 200k | 1.200 | 1.164–1.236 | VCCRCORE 1.14–1.26; VCCIO_PIO_SDM 1.16–1.24 | OK |

  The Agilex limits include ripple and dynamic noise (813918 note 43). For 1V8, 1V1 and 3V3 the DC stack alone already
  reaches past them. Typical parts will be fine, but the datasheet does not guarantee it.
- **PFM:** the AP61202 is the PFM variant (AP61203 = forced PWM, same pinout incl. PG; DS44251 p1). The PFM/CCM boundary
  (Eq. 2, p13) is ~0.44 A for 1V8 and ~0.35 A for 1V2. The 1V8 load (VCCPT 0.21 A per Quartus + LPDDR4 VDD1 + eMMC
  VCCQ + flash) sits around that boundary. PFM bursts then land directly on VCCPLL_SDM / VCCPLL1/2_HPS / VCCADC, which
  have no filter (A1-01).
- **Fix / decision before ordering:** use AP61203Z6 for at least U18 (1V8) and U16 (1V1) if JLC stocks it. Change
  R80/R82 and R89/R91 to 0.1 % parts, which removes the divider share (±1.3 % → ±0.13 %). Optionally centre 3V3 (3.315 V
  nominal). Otherwise accept the risk and measure each rail at the balls on the first boards.
- Related, INFO: the output capacitance on these bucks is 5–7× the datasheet's 10–22 µF (1V8: 6 × 22 µF; 1V2: 6 × 22 µF;
  1V1: 5 × 22 µF + 4 × 1 µF + 32 × 100 nF). DS44251 gives no maximum (p17), so load-step stability is uncharacterised.
  Check it with a load step on the first board.

### A2-08 — INFO — 5V0 input capacitance after DC bias is below TI's and Diodes' minimum (assumption on derating)
- U15 local input: C224–C227 4 × 2.2 µF 0402 6.3 V X5R + C266/C267 2 × 1 µF 16 V X6S = 10.8 µF nominal. TPS548A28 asks
  for "at least 10 µF of ceramic capacitance" plus a 1 µF 16 V X6S at each VIN pin (SNVSBB1D §8.2.2.6, p29). At 5 V a
  2.2 µF/6.3 V 0402 keeps roughly 30–40 % (assumption, typical Samsung curve; not in the local PDF). That leaves about
  4–5 µF effective. C266/C267 meet the per-pin X6S rule if placed at pins 10 and 21 (stream C).
- AP61202 inputs share C157/C158/C160/C161 (22 µF 0402 6.3 V) + C10 1 µF. At 5 V the GRM155R60J226 keeps about 5–6 µF
  (assumption) against the datasheet's "10 µF or greater" (DS44251 p17).
- Input ripple at a 7 A VCORE load with ~5 µF effective is ≈ 7 × 0.13 / (1 MHz × 5 µF) ≈ 0.18 V p-p. That works, but
  use 10 µF/16 V 0603 or 22 µF/10 V 0805 parts here when A2-01 is fixed.

### A2-09 — INFO — power-down runs in forward order (G1 → 2A → 2B) (verified; LPDDR4 impact is an assumption)
- When 5V0 falls, U15 EN (R291/R292 divider, VEN(F) 0.97–1.07 V, SNVSBB1D p6) turns VCORE off at 5V0 ≈ 3.3–3.7 V.
  PGOOD then drops (≤ 5 µs, p8), which disables U18 (1V8, with active discharge per DS44251 p14). U18 PG then disables
  U8/U16/U19.
- 813161 §3.3 (p12) has no power-down requirement beyond "all rails down within 100 ms, the rest as fast as possible
  once one goes". The cascade meets that, so this is not an Agilex violation; the reverse order is only recommended.
- LPDDR4: Hynix §3.2.1.1 says VDD1 > VDD2 applies "between Ta and power-off (controlled or uncontrolled)". 1V8 (VDD1)
  is switched off before 1V1 (VDD2/VDDQ). If 1V1 is lightly loaded (1 kΩ discharge into ~60 µF ≈ 60 ms), VDD2 can
  stay above VDD1 for a while. Accept for a lab board, or reverse the shutdown order later.

### A2-10 — INFO — TPS548A28 details (verified)
- C200 (68 nF SS/REFIN → GND) is "not recommended" (SNVSBB1D §7.3.4, p15: put the SS cap to VSNS− only). It is
  harmless: with C199 the total is 136 nF → t_SS = 136 nF × 0.6 V / 36 µA = 2.27 ms. Cleaner: DNP C200, C199 = 150 nF.
- VCORE accuracy: VINTREF ±1 % (−40…125 °C) + SS-to-FB ±0.6 % (p6–7) + 1 % divider → 0.738–0.768 V against
  0.7275–0.7725 V (813918 Table 13 p28). That leaves 10.5 mV below and only 4.3 mV above for ripple and transients,
  because the nominal is 0.753 V. R2 = 2.49 kΩ (0.7494 V) centres the window.

### A2-11 — INFO — RTL8211FDI straps, supplies, reset (verified, except R41 and Y3 load)
- Straps (RTL8211F Table 10/11 p16–17): PHYAD = 001 (R32 up, R33/R31 down); PLLOFF 0 (R269); TXDLY 0 (R270); RXDLY 1
  (R39); CFG_EXT 0 (R271) = internal I/O LDO; CFG_LDO = 10 (R35 down on LED1, R268 up on LED2) = 1.8 V RGMII. All 4.7 kΩ
  as the datasheet asks. R34/R37 are DNP.
- A1 handoff: with the HPS 15–25 kΩ pull-up (813918 Table 29 p44), the pulled-down RX straps sit at ≤ 1.89 × 4.7/19.7 =
  0.45 V. The RTL8211F VIL for 1.8 V I/O is 0.5 V (Table 58, p56). This passes with 50 mV margin. The PHY's internal
  pull-downs on RXC/RXCTL/RXD1/RXD2 (Table 3, p8) only help.
- TXDLY = 0, RXDLY = 1: the MAC (or the PHY over MDIO) must add the TX clock delay. Linux `phy-mode = "rgmii-id"` makes
  the realtek driver program both delays, which overrides the straps.
- Supplies: DVDD33 (pin 29) on 3V3. AVDD33 (pins 11/40) on PHY3V3 via FB1 (BLM15PX121SN1D, 2 A, 70 mΩ max). LDO_OUT
  (pin 30) feeds only AVDD10/DVDD10 (`PHY1V0`), as §9.2 p51 requires, with C21 1 µF + 4 × 100 nF (≥ 0.1 µF required).
  DVDD_RG (pin 28) is the internal LDO output (CFG_EXT = 0), with caps only.
- 3V3 rise: RTL8211F needs ≥ 0.5 ms (0.1–0.5 ms conditionally, Table 53 note 1, p52–53). U8's soft-start is 0.5 ms typ
  (no minimum given), so it sits at the limit. Also, 3V3 must be off ≥ 100 ms before re-power (Rt2).
- RSET R41 2.49 kΩ 1 %: the local datasheet does not give the value. It matches the usual Realtek reference design
  (assumption).
- Crystal Y3: pins 1/3 = crystal and 2/4 = GND, which matches the YSX321SL drawing. ESR ≤ 50 Ω at 16–31 MHz, as RTL
  Table 56 (p55) asks (≤ 50 Ω). C251/C252 15 pF C0G: 7.5 pF + 3–5 pF stray ≈ 10.5–12.5 pF, which fits a 12 pF crystal.
  **Not verified:** the local Y3 PDF is the generic YSX321SL sheet ("CL 10 pF, 20 pF, or specify"). The 12 pF load of
  X322525MOB4SI comes only from the part listing.
- J9 HR911130A (datasheet p1 schematic, read as image): P2/P3 = MDI0+/−, P4/P7 = MDI1+/−, P5/P6 = MDI2+/−, P8/P9 =
  MDI3+/−. All match U10 pins 1/2, 4/5, 6/7, 9/10. P1 = common chip-side centre tap → C255 100 nF to GND
  (voltage-mode PHY, correct). P10 = the Bob-Smith 1000 pF/2 kV → GND. Green LED: anode 11 (R250 330 Ω to 3V3), cathode
  12 → LED2 (active low because pulled high), ~3–4 mA. The yellow LED (13/14) is unused.

### A2-12 — INFO — J3 (2x19 1.27 mm socket, bottom) needs a part number, and several things depend on the mating board (cannot verify)
- J3 carries 32 HVIO signals (28 with RN1–RN7 10k pull-downs; pins 6, 12, 26, 34, 38 have none), 3 analog inputs to U3
  (pins 1/3/4 → `ad_ch6/4/7`) and only 2 GND pins (2, 5). It has no supply pins, so J3 cannot short a rail.
- **What the part needs:** 2 × 19, 1.27 mm pitch, female, through-hole (footprint
  `PinSocket_2x19_P1.27mm_Vertical`), with an LCSC/MPN chosen for the mating header's post length and stack height.
  Because J3 sits on the bottom, the pin-1 corner as seen from the mating board is mirrored: confirm against the mating
  board's drawing.
- The mating board must not drive HVIO pins or the U3 analog inputs before 3V3 / 3V3_analog are up: 813161 p11 says
  "do not drive the pin with any external voltage" while unpowered, and analog inputs must stay ≤ VDD. The board
  exports no power-good or reset on J3: `pg_all_3v3` only drives D1. The analog inputs have no series resistor or clamp.
- Two GND pins for 32 single-ended 3.3 V signals is a weak return path (stream C / mating board).

### A2-13 — INFO — header usability: J1 has no VREF, J10 has no GND, J5 exposes 3V3 (verified)
- J1 (TDI, TCK, TMS, TDO, GND) has no target-voltage pin. Intel/Altera download cables power their I/O from VCC(TRGT),
  so a wire to 3V3 (J5.1) is needed.
- J10 (TX, RX) has no GND. Use J1.5 or J2.3.
- J5.1 is 3V3 with no current limit. A short trips U8's hiccup OCP (DS44251 p14), which takes down HVIO, the PHY and the
  eMMC.

### A2-14 — INFO — A1-01 follow-up: what the PLL/ADC isolation filters need (verified rail capacity; part choice is a suggestion)
- Per filtered node: one ferrite bead **BLM15PX121SN1D** (C88970, already on the BOM as FB1: 120 Ω at 100 MHz, 2 A,
  DCR 55/70 mΩ) + **4.7 µF** (CL05A475MP5NRNC, C23733, 10 V, already on the BOM) + **100 nF** 0201 (C190183) at the
  ball. That is seven filters:
  - 1V8 side: CL46 VCCPLL_SDM, BF57 VCCPLL1_HPS, BF52 VCCPLL2_HPS, CG52 VCCADC (BF52/BF57 may share one bead).
  - VCORE side: BB54 VCCPLLDIG1_HPS, BB52 VCCPLLDIG2_HPS, CL49 VCCPLLDIG_SDM (must stay on the VCCL_SDM regulator,
    813266 p70).
- The rails can supply them: these balls draw tens of mA in total, a negligible share of U18's 2 A and U15's 15 A.
- IR drop on VCORE (813266 p70: "consider the IR drop across the filter"): 70 mΩ × 50 mA ≈ 3.5 mV. A2-10 leaves
  10.5 mV of low-side margin, so the filter fits, but a bead with lower DCR (e.g. BLM15PX330SN1D-class) is safer for
  VCCPLLDIG.
- A bead into a 4.7 µF ceramic can peak; a 1 Ω series damping resistor or a lossy bead avoids that. Placement is
  stream C.

### A2-15 — INFO — eMMC VDDi capacitor is close to its 1 µF minimum after derating (assumption on derating)
- U11.C2 VDDi: C246 2.2 µF 0201 6.3 V X5R (CL03A225MQ3CRNC). KIOXIA p3: CREG 1 µF min, 2.2 µF typ (recommended),
  4.7 µF max. A 2.2 µF/6.3 V 0201 at the ~1.2 V internal rail, at temperature, can approach 1 µF. Consider a 0402
  2.2 µF 10 V.

### A2-16 — INFO — `pg_all` rises too slowly for U42's input (verified)
- `pg_all` is three open-drain PG pins + R249 10k to 1V8 into U42.B4. With roughly 20–30 pF the rise is ~0.2 µs, i.e.
  ~100 ns/V against the AXC limit of 10 ns/V (§5.3, p5). It only drives D1 (power-good LED), so the worst case is a
  brief LED glitch.

### A2-17 — INFO — connector current margin on 5V0 (verified ratings; load is an estimate)
- Estimated 5V0 input: VCORE 7 A × 0.753 V / ~0.88 ≈ 6 W, plus 1V1/1V8/3V3/1V2 ≈ 4.3 W → ≈ 2.1–2.5 A at 5 V.
- J6 (HX PZ1.27-2x3P, 1 A per pin, datasheet §5.2) has 3 pins on 5V0 = 3 A. J4 (PZ254, 3 A) has 1 pin on 5V0. Both
  are adequate but without much margin.

### A2-18 — INFO — stale claims in repo documents (verified)
- `AGILEX_POWER_CONFIG_CHECKLIST.md`:
  - L2–L5 are listed as "Cenker CKCS201610, 70 mΩ, 3.85 A". The netlist part (C97002) is Sunlord **WPN201610H1R0MT**:
    1.0 µH, DCR 75 typ / 90 mΩ max, Isat 3.35/3.85 A, Irms 2.05/2.35 A (Sunlord WPN catalogue p2). It is still
    adequate: peak ≈ 1.5 A on 1V1.
  - "powergood → SODIMM P1 pin 12" is gone; `pg_all` only drives D1.
  - "PHY 1.8 V / DVDDH on 1V8" belongs to the old KSZ9031.
  - "GPIO1_IO18 = PHY reset" is wrong; it is GPIO1_IO1 (A1-06).
- `ETH_PHY_REVIEW.md`: "R247 still holds eth_rst_n low" is not true (A2-04); `reset-gpios = GPIO1_IO18` is wrong
  (A1-06).

## Coverage list (checked and found correct)

**Regulator outputs (nominal):**
- U15 VCORE = 0.6 × (1 + 2.55/10) = 0.753 V, sensed differentially. Bottom resistor 10 kΩ, inside TI's 1–20 kΩ
  (SNVSBB1D p15).
- U18 1V8 = 1.800 V, U8 3V3 = 3.315 V, U19 1V2 = 1.200 V, U16 1V1 = 1.100 V. R81/R84/R87/R90 are DNP and go only to GND.
- C116–C119 33 pF feed-forward with 200 kΩ top resistors, as in DS44251 Table 1 (p16).
- U6 NCP163ASN330 is fixed 3.3 V: pin 1 IN = 5V0, pin 3 EN = 5V0 (abs max 6 V), pin 4 NC open, pin 5 OUT. Output
  4.7 µF + 2 × 100 nF, input 1 µF as the datasheet asks (≥ 1 µF each, p1/p13).

**TPS548A28 configuration (SNVSBB1D):**
- Pinout matches Table 5-1 (p3–4). The footprint repeats pad 10 (VIN 10/21) and pad 11 (PGND 11–18), so every VIN/PGND
  pad is connected.
- MODE: R57 60.4 kΩ = FCCM, 1 MHz (Table 7-1 p17).
- TRIP: R55 5.6 kΩ, inside 4.0–14.7 kΩ → valley OCL 10.7 A (−15/+18.8 %), load OCL ≈ 10.5–14 A against a 4.75 A
  Quartus load / 6–7 A estimate.
- EN: R291/R292 = 1.46 V at 5 V. On at 5V0 ≈ 4.0–4.36 V, which satisfies "VIN ≥ 3.0 V before enable". EN ≤ 5.5 V and not
  tied to VIN (p4).
- VCC: C201 2.2 µF 6.3 V as required (p4). BOOT: C202 100 nF 16 V.
- PGOOD: R58 10k to VCC → 0.3 mA, under the 10 mA limit.
- SS: 2.27 ms, inside 1 nF–1 µF (p15). On-time 151 ns > 85 ns minimum.

**L1 TMPC0503H-R22MG-D (TAI-TECH table):**
- Isat 21 A / Irms 15.5 A / DCR 3.7–4.4 mΩ.
- Ripple ΔI = 2.9 A (inside TI's 15–40 % of 7–10 A).
- Peak at maximum OCL ≈ 12.7 + 3.6 = 16.3 A < 21 A.

**VCORE output filter:**
- LC double pole in [fsw/100, fsw/30] needs 104–1150 µF effective (SNVSBB1D p17–18).
- Fitted: 8 × 22 µF + 47 µF 1210 + 25 × 100 nF ≈ 190 µF effective at 0.75 V (assumption on bias). The checklist's
  103–1150 µF claim is confirmed.

**AP61202 (DS44251):**
- Pinout matches (p1/p3): FB/GND/VIN/SW/EN/PG.
- VIN 5 V inside 2.3–5.5 V. On-times (169–508 ns) > 70 ns minimum.
- PG pull-ups: `Net-(U16-EN)` to 5V0 (PG abs max 6 V) and `pg_all` to 1V8.
- Inductors 1 µH, inside 1.0–1.5 µH (p16). Every rail's peak current (≤ 1.5 A) < Isat 3.35 A and below Irms 2.05 A.
- Loads: 1V1 ≈ 0.43 A FPGA + LPDDR4 IDD4R VDD2 345 mA + VDDQ 368 mA max (Hynix IDD table) ≈ 1.15 A; 1V8 ≈ 0.5 A;
  3V3 ≈ 0.5 A; 1V2 0.42 A. All < 2 A.

**Sequencing (813161 Table 3 p10):**
- Group 1 (VCORE: VCC, VCCP, VCCL_SDM, VCCH_SDM, VCC_IO_SDM, VCCL_ADC_SDM, VCCL_HPS*, VCCPLLDIG*, VCC_HSSI) →
  U15 PGOOD.
- Group 2A (1V8: VCCPT, VCCPT_HVIO, VCCIO_SDM, VCCIO_HPS, VCCFUSEWR_SDM, VCCPLL*, VCCADC) → U18 PG.
- Group 2B (3V3 VCCIO_HVIO, 1V1 VCCIO_PIO_3A, 1V2 VCCRCORE/VCCIO_PIO_SDM/VCCIO_PIO_2A).
- The 90 % gate holds: TPS548A28 PGOOD rises only 1.06–1.4 ms after soft-start ends (p8, p16); AP61202 PG at 95 % +
  55 µs (p5).

**Ramp times:**
- Per rail: VCORE 2.27 ms, AP61202 0.5 ms typ. Both inside tRAMP 200 µs–100 ms (813918 p32); the AP61202 has no
  minimum tSS, so 2.5× margin is by typical value only.
- AS normal (813773 p57 note 8): VCCIO_SDM (1V8) ramps in 0.5 ms and is fully up ≈ 5–6.2 ms after U15 EN (EN→switching
  ≤ 2 ms + 2.27 ms SS + ≤ 1.4 ms PGOOD delay + 0.5 ms). That is < 10 ms whether counted from its own ramp or from the
  first rail.
- LPDDR4 tINIT0 (Ta→Tb ≤ 20 ms) ≈ 1 ms. VDD1 (1V8) ramps before VDD2 = VDDQ (1V1), as Hynix §3.2.1.1 requires.

**Regulator sharing (813266 Table 32 p70–71):**
- 1V2 and 1V1 carry no non-memory loads except R54/R46 to the ADC mux and the VICM divider.
- 3V3 HVIO is not shared with another Agilex rail group. 1V8 also feeds board 1.8 V parts (U2, Y2, U11 VCCQ, U12 VDD1,
  U1/U42 VCCB), which is an accepted deviation, already open in the checklist.

**3V3_analog vs U3 select lines (A1 handoff):**
- 3V3_analog comes from 5V0 directly (U6 EN = 5V0). 3V3 cannot exist without 5V0 and only starts after two PG stages,
  so U3's VDD is always up before the FPGA can drive A/B/C.
- On power-down, 3V3 is disabled by the cascade while U6 still regulates.
- The SN74LV4051A control inputs are 5.5 V tolerant at any VCC (ROC p6). No issue.

**MLCC voltage ratings:**
- Every non-DNP capacitor's rated voltage ≥ its net voltage (Yageo code 5 = 6.3 V, 6 = 10 V; Samsung Q = 6.3 V,
  P = 10 V, O = 16 V, A = 25 V, B = 50 V):
  - 0201s: 100 nF/10 V up to 3V3; 1 µF/6.3 V on ≤ 1.8 V nets; 220 nF/6.3 V on 3V3; 2.2 µF/6.3 V on VDDi.
  - 15 pF C0G/50 V.
- The only parts at ≥ 79 % of rating are the 6.3 V parts on 5V0 (A2-01/A2-08).

**U1/U42 SN74AXC4T774 (SCES898C):**
- VCCA = 3V3, VCCB = 1V8 on both. OE = GND (enabled). DIR pins tied to VCCA/GND (referenced to VCCA).
- U1: DIR1–3 = H (A→B: TDI, TCK, TMS to U7), DIR4 = L (B→A: TDO).
- U42: DIR1 = L (UART TX → J10.1), DIR2 = H (J10.2 → UART RX), DIR3 = L (`eth_rst_n` → PHYRSTB), DIR4 = L (`pg_all` →
  LED).
- VCC isolation (< 100 mV → Hi-Z) and Ioff cover 1V8-before-3V3 and back-powering from cables.
- Data-input VIH/VIL hold for 3.3 V and 1.8 V sources.

**Analog block:**
- U3 SN74LV4051A pinout: X4/X6/X/X7/X5/INH/VEE/GND/C/B/A/X3/X0/X1/X2/VDD. INH, VEE = GND.
- Channels: ch0 VCORE via 100 Ω, ch1 3V3/2 (1k/1k), ch2 1V8, ch3 1V2, ch5 1V1 (via 1 kΩ). All ≤ 3.3 V.
- U4 OPA365 SOT-23-5 pinout (OUT 1, V− 2, +IN 3, −IN 4, V+ 5) as a unity-gain buffer. 33 Ω isolates C3 680 pF.
- U5 ADS7056 pinout (CS 1, SDO 2, SCLK 3, DVDD 4, GND 5, AVDD 6, AINP 7, AINM 8). AINM = GND; input range 0–AVDD,
  where AVDD = 3V3_analog is also the reference. DVDD = 3V3, the same rail as the HVIO host, so digital inputs never
  exceed DVDD + 0.3 V. AVDD has C1 4.7 µF (TI asks 3.3 µF, §8.3.2) and DVDD has C261 1 µF.

**U12 LPDDR4:**
- VDD1 = 1V8 (1.7–1.95 V), VDD2 = VDDQ = 1V1 (1.06–1.17 V).
- ZQ0 (A5): R43 240 Ω 1 % to VDDQ, as the Hynix pin description requires.
- ODT_CA_A/B (G2/T2) on VDD2 (single rank, rank-0 die). DNU/NC balls are open. CS shared A/B.
- RESET_n: R44 1k down. A1-09 agreed: 0.04–0.28 V vs the recommended ≤ 0.22 V.
- CKE/CS/CA/CK are driven from bank 3A on the same 1V1 rail as VDD2, which meets "between VSS and VDD2 during ramp".

**U11 eMMC:**
- VCC = 3V3 (2.7–3.6 V), VCCQ = 1V8 (1.7–1.95 V).
- CVCC 4.7 µF + 220 nF and CVCCQ 4.7 µF + 100 nF, as KIOXIA p3 recommends. VDDi see A2-15.
- RST_n: R243 10k to VCCQ, driven by HPS GPIO0_IO12.
- CMD (R241) and DAT0–7 (R272–R279) 10k to VCCQ. DS 10k down. CLK has no pull. Series 33 Ω.

**U2 IS25WP128-RHLE:**
- `-RHLE` = 24-ball TFBGA 6 × 8 mm **5 × 5** array with a dedicated RESET# on **A4** (ISSI p8 table "Pin3/Ball A4 =
  RESET#, option R or P"; p107 ordering).
- Symbol balls match the 5 × 5 map: B2 SCK, C2 CE#, B4 VCC, B3 GND, D3 SI/IO0, D2 SO/IO1, C4 WP#/IO2, D4 HOLD#/IO3.
  VCC = 1V8 (1.65–1.95 V). RESET# R15 10k up + SDM_IO15.

**Oscillators:**
- U9 AX3DAF1 = LVDS, 3.3 V (option A), ±25 ppm −40…85 °C, OE on pin 1 active high (Abracon p331 ordering). Pin 1 = 3V3,
  pin 2 NC open, pin 6 = 3V3.
- Y4 OT3225100MJBA4SL (YSO110TR series): pin 1 tri-state = 3V3 (enable high/floating), 2 GND, 3 OUT, 4 VDD = 3V3. The
  series supports 1.8–3.3 V CMOS; that this ordering code is 3.3 V is an assumption.
- Y2: see A2-02. 1.8 V, ±30 ppm.

**LEDs:**
- D1/D2 150060RS75000 (red, VF 2.0 V typ / 2.4 V max at 20 mA, IF max 30 mA). Cathode (pin 1) to GND, anode via 680 Ω.
- D1 driven by U42.A4 (3.3 V), D2 by U7.CE6 (3.3 V HVIO). ≈ 2 mA each.
- J9 green LED polarity: see A2-11.

**Connectors:**
- J1 JTAG and J10 UART pin assignments match the U1/U42 channels.
- J2 FPGA UART: 2 HVIO pins with 10k pull-ups to 3V3, plus GND.
- J5: 3V3, GND, 12 HVIO.
- J4/J6 power pinout as described in A2-01. J3 as A2-12. J9 as A2-11.

## For other streams
- B: U2's footprint is `MX25U25645G_CSP24_6x8mm_P1.0mm`. Confirm it is the **5 × 5** ball array (IS25WP128 package H),
  not 4 × 6.
- B: U15 uses the `TDA38812` footprint. Confirm the pad geometry against TPS548A28 RWW (SNVSBB1D p3, VQFN-HR-21).
- B: L2–L5 use footprint `L_Cenker_CKCS201610`, but the part is Sunlord WPN201610H1R0MT (2.0 × 1.6 mm). Confirm the
  land pattern.
- B: LED D1/D2 cathode-mark orientation; Y2/Y3/Y4/U9 pin-1 orientation; J9 footprint pin numbering against the
  HR911130A drawing (p2).
- C:
  - Place C266/C267 at U15 pins 10 and 21.
  - Route the VCCLSENSE/GNDSENSE pair, with A2-06's fallback resistors at U15.
  - Place C1 at U5 AVDD.
  - Place the A1-01/A2-14 filters at the balls.
  - J3 has only 2 GND pins for 32 signals.
