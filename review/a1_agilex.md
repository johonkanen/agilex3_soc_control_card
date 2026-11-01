# A1 – Agilex 5 U7 (A5EB013B, B23B, -6S): ball-by-ball, configuration, HPS pin mux, full-pin Quartus fit

Frozen state: commit `0aa9192` (`review/inputs/COMMIT`), netlist `review/inputs/netlist.xml`, board
`agilex_3_soc.kicad_pcb` (read-only). Scratch/work: `review/work/a1/` (scripts in `scripts/`, Quartus copy in `qfit/`,
DRC copy in `drc/`, page-numbered document text in `txt/`).

## Summary

| Severity | Count |
|---|---|
| BLOCKER | 0 |
| SHOULD | 2 |
| INFO | 11 |

- **No connectivity error found on U7.** All 795 balls were checked against the Altera pin list. That covers 765 symbol
  pins and the 30 DNU/NC balls that have no symbol pin. Every power and ground ball is on the right rail for a -6S part.
  The reference, sense, strap and JTAG pins match 813266. The HPS pin mux and the LPDDR4 placement and swizzle are legal.
- **Full-pin Quartus Prime Pro 26.3 fit (A5EB013BB23BE6S): 0 errors, 0 critical warnings.** It used every pin that is
  connected on the board, with its real I/O standard. That is 170 signal balls: 55 HVIO fabric pins at 3.3-V LVCMOS,
  33 HPS IO, 69 LPDDR4 + refclk + RZQ, and the SDM configuration pins. The configuration matches the board: AS x4,
  OSC_CLK_1 25 MHz, AS_CLK 100 MHz, INIT_DONE SDM_IO0, CONF_DONE SDM_IO16, HPS_COLD_nRESET SDM_IO10, refclk RT_OFF.
  The bank voltages in Quartus's .pin file are the same as the board's, bank by bank.
- **SHOULD:** (A1-01) the seven PLL and ADC supply balls have no isolation filters. (A1-02) The `eth_rst_n` pull-down
  and 1 µF capacitor on HPS_IOB_2 do not give a guaranteed low level, and they break the input edge-rate limit of U42.
- **Not covered:** decoupling, PDN, layout and SI (stream C). The regulator maths and the power-up sequence (A2). The
  footprint (B). The Quartus run used the IP's default 800 MHz memory clock, not 2133 MT/s. The data rate does not change
  pin legality, but timing at 2133 was not re-run. The test design's fabric logic is a dummy, so its timing and CDC
  Design Assistant results mean nothing.

## Findings

### A1-01 — SHOULD — PLL/ADC supply balls connected to the shared rails without isolation filters (verified)
- **Where:** VCCPLL1_HPS BF57, VCCPLL2_HPS BF52, VCCPLL_SDM CL46 and VCCADC CG52 are directly on net `1V8`.
  VCCPLLDIG1_HPS BB54, VCCPLLDIG2_HPS BB52 and VCCPLLDIG_SDM CL49 are directly on `VCORE`. The netlist has no ferrite or
  filter part on any of them; the only ferrite on the board is FB1, at the PHY.
- **Evidence:**
  - 813266 Table 12, p23–26: VCCPT "with proper isolation filtering" for VCCPLL_SDM/VCCPLL_HPS/VCCADC; VCCPLLDIG_SDM
    "must be sourced from the same regulator as VCCL_SDM with proper isolation filtering"; VCCADC "tie to VCCPT with
    proper isolation filtering".
  - 813266 Table 17, p44: VCCPLLDIG1/2_HPS "Connect this to the VCCL_HPS with proper isolation filtering".
  - 813266 Table 32 / Figure 2, p70–72, the -6S example: these rails are marked "Filter".
- **Effect:** the board probably still works, but there is extra PLL jitter and ADC noise, and the design departs from
  Altera's mandated topology. `AGILEX_POWER_CONFIG_CHECKLIST.md` item 11 already lists this as open; the frozen netlist
  still has no filters.
- **Fix:** a ferrite bead (for example BLM15PX121SN1D, already used as FB1) plus a local capacitor per ball or group.
  Account for the filter's IR drop on the 0.75 V VCCPLLDIG rails: 813266 p70 says to consider it.

### A1-02 — SHOULD — `eth_rst_n` (AC75, HPS_IOB_2 / GPIO1_IO1): idle level not a guaranteed low, and an over-slow edge into U42 (verified)
- **Net:** `/eth_rst_n` = U7.AC75 + R247 10k to GND + C259 1 µF to GND + U42.B3 (SN74AXC4T774, VCCB = 1V8, DIR3 = GND,
  so B→A, which drives `phy_rst_n` to the PHY).
- **Idle level:** during power-up and configuration every HPS pin is a Schmitt input with a 20 kΩ weak pull-up
  (813266 §1.6 note 10, p74). The pull-up range is 15–25 kΩ (813918 Table 29, p44). The divider with R247 gives
  1.8 V × 10/(10+15…25) = 0.51–0.72 V, or up to 0.76 V at VCCIO_HPS = 1.89 V. U42's VIL(max) is 0.35 × VCCB = 0.63 V
  (SN74AXC4T774 data sheet, §5.3 Recommended Operating Conditions). So the PHY reset is not reliably held during boot, as
  `ETH_PHY_REVIEW.md` claims.
- **Edge rate:** C259 1 µF sits directly on an HPS output and on a translator input. That input's limit is
  Δt/Δv ≤ 10 ns/V (same table). The RC and the pin drive give edges of about 10–100 µs/V, which risks multiple edges or
  oscillation at the translator.
- **Fix:** DNP C259. Change R247 to 4.7 kΩ: the worst case becomes 1.89 × 4.7/19.7 = 0.45 V, below VIL. If a hardware
  reset delay is wanted, put it on the 3.3 V `phy_rst_n` side behind a Schmitt input.

### A1-03 — INFO — LPDDR4 swizzle string in the docs and in the last Quartus run is stale for byte 1 (verified)
- The frozen netlist has G56 on `dq15`, which goes to U12.B9 DQ15_A, and E56 on `dq9`, which goes to U12.C11 DQ9_A.
- Correct string for the frozen board: `PIN_SWIZZLE_CH0_DQS1=10 8 13 14 12 11 15 9`. `LPDDR4_SWIZZLE_RULES.md` "Final",
  `LPDDR4_SWIZZLE_PLAN.md` lines 182/191/337/412 and `~/dev/agilex5_emif_test/varA_r2133rtoff/pins.tcl` all still have
  `... 9 15` (G56 = DQ9).
- The full string, regenerated by `gen_pins.py` from the frozen netlist and accepted by the fitter:
  `BYTE_SWIZZLE_CH0=1 0 X X X X 3 2;PIN_SWIZZLE_CH0_DQS0=5 6 7 0 3 2 1 4;PIN_SWIZZLE_CH0_DQS1=10 8 13 14 12 11 15 9;PIN_SWIZZLE_CH0_DQS2=20 19 21 18 22 17 23 16;PIN_SWIZZLE_CH0_DQS3=27 26 29 28 31 30 24 25;`
- The board is legal. This is a firmware/IP setting; a wrong map would affect LPDDR4 training. The package-delay table in
  the plan (line 337) also uses the old balls for dq9/dq15 (for stream C).

### A1-04 — INFO — refclk: P/N swap confirmed and harmless; RT_OFF works in Quartus (verified; the open note can be closed)
- **P/N swap:** U9 (AX3DAF1 = LVDS, 3.3 V, OE on pin 1). Pin 4 OUT → R25 → C8 → `iob3A_refclk_N` (A58, CLK_B_3A_0n), and
  pin 5 nOUT → R26 → C9 → `refclk_P` (B55). Pins 4 = Output and 5 = Complementary output per AX3_abracon.pdf, pin
  table. AC coupling makes the swap only a 180° phase inversion of the PLL reference, which does not matter.
- **Bias:** R244 1k from 1V1 / R245 3k9 gives VICM = 0.876 V (0.85–0.90 V over the 1V1 tolerance). That is inside
  0.8–0.95 V for 1.1-V True Differential Signaling (813918 Table 42, p54–55). VID = LVDS 250–450 mV, inside the
  100–454 mV range.
- **Quartus:** with `PHY_TERM_X_R_T_REFCLK_INPUT_OHM=RT_OFF`, also listed in `ANALOG_PARAM_DERIVATION_PARAM_NAME`, the
  .ip keeps RT_OFF. The fitter reports B55/A58 as 1.1-V True Differential Signaling with termination Off. The real
  project must carry this setting.

### A1-05 — INFO — settings the real Quartus project must use; the test project differs (verified)
`~/dev/agilex5_emif_test/scripts/create_project.tcl` holds DE25-Nano values that do not fit this board. My copy used the
board values below, and Quartus accepted all of them:
- `USE_HPS_COLD_RESET SDM_IO10`: the test project has SDM_IO11, but the board uses CK69 = SDM_IO10.
- `USE_INIT_DONE SDM_IO0`: missing from the test project.
- `DEVICE_INITIALIZATION_CLOCK OSC_CLK_1_25MHZ`: the test project has 125 MHz, but Y2 is 25 MHz. 813773 p54 says a wrong
  frequency makes configuration fail.
- `ACTIVE_SERIAL_CLOCK` at most 100 MHz: the test project has 125 MHz, but -6S supports only 25/50/100 MHz (813773 p53
  note 4, p70 note 12).
- `USE_CONF_DONE SDM_IO16`, refclk RT_OFF (A1-04), and the swizzle from A1-03.

### A1-06 — INFO — stale claims in repo documents (verified)
- `HPS_PINMUX.md`: the table, the `HPS_IO_Enable` string and `src/hps_io_board.txt` still list I2C1 on IOB_7/IOB_8
  (`i2c_sda`/`i2c_scl`). In the frozen netlist Y74 and AK69 are unconnected and no I2C net exists. Set both to `NONE` in
  the HPS IP. Everything else in `HPS_PINMUX.md` matches the netlist.
- `ETH_PHY_REVIEW.md` item 3 says the PHY reset is "HPS GPIO1_IO18 (K71)". K71 is HPS_IOB_19 = `eth_rxd0`. The reset is
  HPS_IOB_2 = GPIO1_IO1 (AC75), as `HPS_PINMUX.md` correctly says. Use `<&gpio1 1 ...>` in the device tree.

### A1-07 — INFO — 240 Ω on RZQ pins that are not used as RZQ (verified)
- **M42** (RZQ_T_3A) has R248 240R to GND. The HPS EMIF uses only T48 (RZQ_B_3A, R23); Quartus reports M42 as
  RESERVED_INPUT.
- **DP58** (RZQ_B_2A) has R24 240R to GND, but bank 2A has no I/O in use.
- 813266 Table 8, p17: "When you do not use these pins as dedicated input for the external precision resistor or as I/O
  pins, leave these pins unconnected." This is harmless, about 0.1 mA through the weak pull-up during configuration. DNP
  them or keep them as a spare.

### A1-08 — INFO — two orphan labels on bank 6C (verified)
- H11 `/fpga_bank6cd/iob6c1` and H14 `/fpga_bank6cd/iob6c2` are labelled single-pin nets with no other member. The labels
  are local in `fpga_bank6cd.kicad_sch` (lines ~15081/15121) and the `{iob6c}` bus was removed in the reorg.
- Their pads on the board have no copper attached, which is electrically the same as unconnected and legal. Remove the
  labels, or route them out if they were meant to reach a header.

### A1-09 — INFO — LPDDR4 RESET_n pull-down margin (verified)
- M48 `~{rst}`: R44 1k to GND against the HSIO weak pull-up of 3–30 kΩ during configuration (813918 Table 22, p42).
  That gives 0.04–0.28 V.
- Hynix H9HCNNN8KUMLHR §3.2.1: RESET_n is "recommended to be LOW (≤0.2 x VDD2)" = 0.22 V while power ramps. VIL(DC) is
  0.35 × VDD2 = 0.385 V, so the level is a valid low but can exceed the recommended level at the weakest pull-up. A 470 Ω
  pull-down would give margin. Low impact.

### A1-10 — INFO — speed grade not fixed in the schematic (verified)
- U7 value `A5EB013B-B23B` has no orderable code: speed grade, power grade and temperature are unspecified.
- VCORE is 0.6 × (1 + 2.55/10) = 0.753 V, set by U15's FB divider R2/R1 through VCCLSENSE BN46 / GNDSENSE BN44. That is
  valid only for -6S/-6X; -4S needs 0.8 V and -5S 0.78 V (813918 Table 13, p28–30). Put the full ordering code (for
  example A5EB013BB23BE6S…) in the symbol or BOM.

### A1-11 — INFO — no external control of nCONFIG / HPS_COLD_nRESET (verified)
- nCONFIG BK71 has only R8 10k to 1V8, and HPS_COLD_nRESET CK69 has only R264 10k to 1V8. There is no button or header,
  so reconfiguration or a cold reset needs JTAG, software or a power cycle. Both are legal (813266 Table 2 p9; Table 14
  p37).

### A1-12 — INFO — CONF_DONE/INIT_DONE pull-ups R10/R9 are DNP (verified, correct)
- R9 (SDM_IO0) and R10 (SDM_IO16) are 10k pull-ups to 1V8, marked `dnp` in the netlist. Fitted, they would override the
  internal 20 kΩ pull-downs that keep CONF_DONE/INIT_DONE low before configuration (813773 §5.9.1 p94; 813266 Table 14
  p35–36). Keep them DNP.

### A1-13 — INFO — TCK 1k pull-down rules out attestation/BKP (verified)
- CC64 TCK has R22 1k to GND, as 813266 Table 2 p8 asks. The same row says that if attestation or Black Key Provisioning
  is ever used, TCK must instead have a 10k pull-up to VCCIO_SDM. Note it as a security-feature constraint.

## Coverage list (checked and found correct)

**Ball inventory**
- 795 balls in the pin list, 765 symbol pins and 30 balls with no symbol pin (20 DNU, 10 NC).
- The symbol pin names match Altera's pin name, optional function and bank on every ball. The HSIO IO index matches on
  all 192 bank 2A/3A pins (`scripts/join.py`, `scripts/idx.py`).
- PCB pad nets match the netlist on all 795 U7 pads, and on all 1599 nodes of the 434 nets that touch U7
  (`scripts/pcb_u7b.py`, `scripts/parity.py`).
- DRC of a board copy with zones refilled: 0 unconnected items. The 8 violations are footprint-library items, for stream B.

**DNU/NC on copper**
- All 30 pads have no net, no track or via within pad radius + 50 µm, and no F.Cu zone fill.
- No track exists on any `unconnected-*` net. 813266 Table 11, p21, satisfied.

**Ground**
- All 230 GND balls are on GND.
- VCCBAT CG49 is on GND (no BBRAM key; 813266 p25, 813918 note 47).
- VREFP_ADC/VREFN_ADC (CF75/CF74) and VSIGP/N_0/1 (BW75/BW74/CJ74/CJ75) are on GND (813266 Table 6, p15).

**VCORE (0.753 V; -6S needs 0.7275–0.7725 V)**
- The rail carries VCC×21, VCCP×7, VCCL_HPS×4, VCCL_HPS_CORE0_CORE1×2, CORE2×2, CORE3×2, VCCL_SDM×4, VCCH_SDM,
  VCC_HSSI_L1×2, VCC_IO_SDM, VCCL_ADC_SDM, plus the VCCPLLDIG ×3 balls (A1-01).
- Sharing is allowed by 813266 Table 32 p70 and Tables 12/15/17. VCCH_SDM may merge with VCCL_SDM on a device without
  transceivers (p70, 813161 p14 note 3). VCC_HSSI is not grounded (p39).
- No GTS, VCCERT or VCCEHT balls exist on this package.

**1V8**
- VCCPT×4, VCCPT_HVIO×10, VCCIO_SDM, VCCIO_HPS×2 and VCCFUSEWR_SDM share one regulator, as required (813266 p23, p26,
  Table 32 p71).
- VCCPLL1/2_HPS, VCCPLL_SDM and VCCADC are also on 1V8 (A1-01).

**1V2 and 1V1**
- 1V2: VCCRCORE×3, VCCIO_PIO_SDM (= VCCRCORE without AVST x16, p24) and VCCIO_PIO_2A_T/B×4 (bank unused, 1.2 V allowed,
  p23).
- 1V1: VCCIO_PIO_3A_T/B×4, T and B at the same level, LPDDR4 LVSTL 1.1 V.

**3V3**
- VCCIO_HVIO_6A–6H, 16 balls (813266 p26). Every connected HVIO load is 3.3 V: J3/J5/J2 headers, U5 DVDD 3V3, U3
  4051 (3V3_analog), Y4 3.3 V CMOS, LED.

**Sense, reference and calibration pins**
- VCCLSENSE BN46 and GNDSENSE BN44 go to U15 FB (via R2/R1) and VSNS-, not to rails (813266 p25).
- RREF_SDM DH75: R18 2k0 1 % (C4109) to GND (Table 13, p27).
- RZQ T48: R23 240R 1 % to GND (Table 8, p17).
- TEMPDIODE0Ap/n CK71/CN72 left open (Table 7, p16).

**Clocks**
- OSC_CLK_1 DB72 and HPS_OSC_CLK (HPS_IOB_4, AN67) both come from Y2, 25 MHz 1.8 V (25/100/125 MHz allowed, 813773 p54;
  HPS 25–125 MHz, 813918 p109). The EMIF is used, so OSC_CLK_1 is required (813266 p9).
- clk100 goes to AE11 (HVIO_6G_9, PLLREFCLK1) at 3.3 V.
- The EMIF refclk is on CLK_B_3A_0p/n (A1-04).

**Configuration**
- MSEL[2:0] = 011, AS normal: SDM_IO9 R4 4k7 down, SDM_IO7 R45 4k7 up, SDM_IO5 R7 4k7 up (813773 Table 17 p56–57;
  813266 p28–30).
- nCONFIG and nSTATUS have 10k to VCCIO_SDM (813266 p9).
- AS x4 pin map to U2: SDM_IO2→SCLK, IO4→SIO0, IO1→SIO1, IO3→SIO2 (10k up), IO6→SIO3 (10k up), IO5→CS# (22R),
  IO15 AS_nRST→RESET# (10k up). This is per 813773 Table 30 p77 and Fig. 18 p72; U2 is 1.8 V.
- HPS_COLD_nRESET is on SDM_IO10 (valid for ASx4) with 10k up. It is not on the QSPI reset (813266 p37–38).
- INIT_DONE is on SDM_IO0 and CONF_DONE on SDM_IO16 (A1-12).
- Unused SDM_IO8, IO11–IO14 are open: in AS mode they are driven or weakly pulled (813773 Table 29 p76).
- Boot combination AS/QSPI + SD/eMMC is supported in both FPGA-first and HPS-first modes (813762 Table 5 p12,
  Table 8 p21). An A5E 013 RBF is 2–4 MB (813773 Table 2 p22), which fits the 16 MB flash.

**JTAG**
- TCK has 1k down (A1-13), TMS and TDI have 10k up, TDO has 10k up (813266 Table 2 p8).
- U1 directions: DIR1–3 = A→B into U7, DIR4 = B→A for TDO, OE active low tied to GND.

**HPS pin mux**
- All 30 used HPS functions exist in the Altera optional-function column of their ball (`u7_balls.csv` check):
  - EMAC2 RGMII on IOB_13–24 with MDIO2 on IOB_9/10, the same controller as required (813266 Tables 24–25 p53–57).
  - SDMMC group 1 on IOA_1–3/6–12 with DATA_STROBE IOA_16 (Table 21 p47–48).
  - UART0 group 2 on IOA_23/24 (Table 29 p62).
  - GPIOs: eMMC reset GPIO0_IO12 (IOA_13), PHY reset GPIO1_IO1 (IOB_2), PHY interrupt GPIO1_IO4 (IOB_5).
- Far-end pins match through the series resistors to U10 TXC/TXCTL/TXD0–3/RXC/RXCTL/RXD0–3/MDC/MDIO/INTB and U11
  CLK/CMD/DAT0–7/DS/RST_n. U42 directions for the UART are correct.
- Pull resistors: CMD 10k up (Table 21), MDIO 1k5 up (p56), DS 10k down.
- 17 unused HPS IO are left open (pins are tri-stated with weak pull-ups, p46).
- VCCIO_HPS is 1.8 V, the same as eMMC VCCQ and PHY_RG.

**LPDDR4**
- Lane map: BL0 = byte 1, BL1 = byte 0, BL6 = byte 3, BL7 = byte 2. In each lane DQS_P/N/DMI sit on lane pins 4/5/6 and
  pin 7 is unused. CA/CKE/CS/CK/RESET are in BL2/BL3.
- Every DQ stays in its own byte and channel, with no P/N swap (`scripts/ddr.py`). Every U7 net index equals the U12 DQ
  index. CA, CKE and CS are shared by channels A and B (1x32).
- Quartus placed every EMIF pin on the assigned balls: LVSTL 1.1 V, Differential LVSTL for CK/DQS, RZQ on T48. The
  unused lane pins are EMIF `g_UNUSED` pads, open on the board.

**Unused I/O**
- 37 unused 3A pins, 95 unused 2A pins and 124 unused HVIO pins are open. That is allowed: 813266 Tables 1, 4, 5 and 9
  (Quartus defaults). Quartus reports none of them as needing a board connection.

**Self-nets**
- Every signal net has exactly one U7 ball. No net joins two U7 balls except the power and ground rails.

**Quartus run**
- `review/work/a1/qfit/varA_frozen`: qsys 325 s, synthesis, fit and STA all ran. Fitter: 0 errors, 2 warnings:
  - 25315: no drive/termination settings on the dummy fabric outputs;
  - 171167: the HPS IP's own ignored `Global Signal` assignment, the same as in the reference build.
- No critical warnings. The `.pin` file bank voltages are 2A 1.2 V, 3A 1.1 V and 6A–6H 3.3 V, which match the board.
- Comparing all 795 `.pin` rows to the netlist (`fit_vs_board.txt`): every board-connected signal ball is used by the fit
  at the expected location. The four exceptions are A1-07 (M42, DP58) and A1-08 (H11, H14).
- Every power-ball name in the `.pin` file maps to the expected rail.

## For other streams
- A2: the RTL8211F strap pull-downs (R31/R33/R269/R270, 4.7k) work against the HPS 15–25 kΩ weak pull-ups during reset,
  giving ≤0.45 V at the strap. Check against the PHY's strap VIL.
- A2: AS normal mode needs VCCIO_SDM fully ramped within 10 ms (813773 p57 note 8). Check the ramp and the Group
  1→2A→2B sequence (813161 Table 3 p10).
- A2: check that U2 IS25WP128-RHLE ball A4 is RESET# in this ordering variant.
- A2: U3 select inputs are driven from 3V3 HVIO while U3 runs from 3V3_analog. Check that this supply cannot be off
  while the FPGA drives them.
- B: U7 corner pads are larger (9 × 0.355 mm, 17 × 0.33 mm, the rest 0.305 mm). Check them against Altera land pattern
  838752. DRC also reports 7 lib_footprint_issues and 1 lib_footprint_mismatch.
- C: route VCCLSENSE/GNDSENSE as a differential pair (813266 p25). The package-delay table in `LPDDR4_SWIZZLE_PLAN.md`
  uses the old balls for dq9/dq15 (A1-03).
