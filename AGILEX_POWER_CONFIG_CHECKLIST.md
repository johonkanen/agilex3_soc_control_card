# Agilex 5 (A5EB013B-B23B, -6S) power, configuration and power-up checklist

Generated from the schematic as of 2026-09-16 (root sheet, `fpga_power`, `fpga_gnd`, `sdm`, `ps`, `ps1`, `clk`, `hps`). Reference: Altera *Agilex 5 Power Management User Guide* (ID 813161, section 3.2 Power-Up Sequence Requirements, table 3) and the *Agilex 5 Pin Connection Guidelines* (ID 813266).

**Rechecked 2026-10-24** against the schematic netlist and the local copies listed in `docs/README.md`:
- Pin Connection Guidelines 813266 (2026.04.24): §1.5, table 32, power-supply sharing for -6S.
- Power Management UG 813161 (2026.09.08).
- Configuration UG 813773 (26.1.1): table 17 MSEL.
- Data Sheet 813918 (2026.08.10): tRAMP, POR delay.

The new findings are marked **(2026-10-24)**.

Legend: `[x]` verified correct in the schematic, `[ ]` open item / needs your decision, `[!]` error to fix.

---

## 1. Supply rails on the board

| Rail (net) | Source | Nominal | Enable | Loads |
|---|---|---|---|---|
| `5V0` / `5V` | J6 (2x3 header), also J4.3 | 5.0 V in | – | all regulators, U6 |
| `VCORE` | U15 TPS548A28RWWR buck (C5219375; was TDA38812, same land pattern), remote sense via `vcoresense_P/N` (VCCLSENSE BN46 / GNDSENSE BN44), FB divider R2 2.55k / R1 10k -> 0.6 V x (1 + 2.55/10) = **0.753 V** | 0.75 V | EN = `core_en`, divider R291 24.3k / R292 10k from 5V0 -> on at VIN 4.2 V | all Group 1 pins (see §2) |
| `1V8` | U18 AP61202Z6 buck, R82 200k / R80 100k (R81 DNP) -> 1.80 V | 1.8 V | EN = `PG-Core` (U15 PGOOD, open-drain, R58 10k to the U15 VCC LDO `tda_vcc` 3.0 V; was 5.6k to 5V0) | Group 2A pins, VCCIO_HVIO_6A, Y2 (SiT8924 1.8 V), QSPI flash U2, all SDM/JTAG pull-ups, U1/U42 B-side, PHY 1.8 V |
| `3V3` / `3v3` | U8 AP61202Z6, R85 200k / R83 44.2k -> 3.32 V | 3.3 V | EN = U18 PG (open-drain, R65 47k to 5V) | VCCIO_HVIO_6B..6H, U9 100 MHz LVDS osc, U1/U42 A-side, headers |
| `1V2` | U19 AP61202Z6, R88 200k / R86 200k -> 1.20 V | 1.2 V | EN = U18 PG | VCCRCORE, VCCIO_PIO_SDM, VCCIO_PIO_2A_T/B |
| `1V1` | U16 AP61202Z6, R91 200k / R89 240k -> 1.10 V | 1.1 V | EN = U18 PG | VCCIO_PIO_3A_T/B (LPDDR4), refclk bias divider |
| `3V3_analog` | U6 NCP163 LDO from 5V0 | 3.3 V intended | EN tied to 5V0 | ADC subsystem |

- [x] VCORE set point 0.753 V matches the -6S core voltage; remote sense goes to the device sense pins.
- [x] **(2026-10-24)** FPGA load per rail, from the Quartus Power Analyzer on the EMIF test build (HPS at the DE25-Nano clocks, EMIF 1600 MT/s active, nearly empty fabric; Maximum characteristics, Tj 100 °C):

  | Rail | Load | Note |
  |---|---|---|
  | 0.75 V | 4.75 A | about 3.9 A of it static; about 6–7 A with a full fabric design (EPE-style estimate) |
  | 1.8 V | 0.21 A | |
  | 1.2 V | 0.42 A | |
  | 1.1 V | 0.43 A | FPGA side only; add the LPDDR4 VDD2/VDDQ current |
  | 3.3 V | < 0.01 A | before I/O loads |

  The 2 A AP61202 rails have plenty of headroom.
- [x] **(2026-10-29) VCORE stage: U15 is now a TI TPS548A28RWWR (data sheet SNVSBB1D).** The TDA38812 is not available at JLC. The TPS548A28 has the same VQFN-HR-21 3 × 4 mm land pattern (pads compared one for one, the footprint `agilex_lib:TDA38812` is kept) and the same pin functions: CS -> TRIP, SS/VREF -> SS/REFIN, RGND -> VSNS–. The symbol is `agilex_5_lib:TPS548A28`.
  - **Rating:** 15 A part, 6–7 A worst-case load. VIN 5 V is inside 3.0–16 V (internal VCC LDO).
  - **MODE:** R57 60.4k to AGND = FCCM, 1 MHz (table 7-1). R56 stays DNP.
  - **Current limit:** R55 5.6k, valley OCL = 60000 / 5.6k = 10.7 A (TRIP range 4.0–14.7k).
  - **Soft-start:** C199 68n to VSNS– (the connection TI recommends) + C200 68n to GND: 136 nF × 0.6 V / 36 µA = 2.3 ms (internal minimum 1.5 ms).
  - **Divider:** R2 2.55k (C95596) / R1 10k -> 0.753 V, sensed differentially. TI asks for 1–20 kΩ on the bottom resistor, so the old 10k / 39k was changed.
  - **C198** (220 pF feed-forward across R2) is DNP: TI only suggests a feed-forward capacitor for Vout ≥ 2 V, and it feeds ripple into FB.
  - **EN:** TI recommends EN ≤ 5.5 V and not tied to VIN. R291 24.3k (C26969) / R292 10k divide 5V0: EN = 1.46 V at 5 V, on at VIN 4.2 V (1.22 V threshold), off at 3.5 V.
  - **Input capacitors:** TI requires a 1 µF 0402 X6S at each VIN pad (pins 10 and 21). C266 / C267 1 µF 16 V X6S (C393026) are added; place one at each pad. C224–C227 2.2 µF and the 22 µF bulk stay.
  - **Output filter (D-CAP3):** 220 nH and 1 MHz need 103–1150 µF effective output capacitance (LC pole between fSW/100 and fSW/30). VCORE has about 170 µF effective (8 × 22 µF 0402, 47 µF 1210, 25 × 100 nF). On-time 151 ns > 85 ns minimum.
  - **Output ripple:** about 2.9 A p-p at 1 MHz with 220 nH (29 % of 10 A, inside TI's 15–40 %), a few mV on VCORE, well inside ±3 %.
- [x] **(2026-10-24, still valid)** R58 10k pulls PGOOD (U15 pin 9) up to U15's own VCC LDO (3.0 V; TPS548A28 PGOOD abs max 6 V). The AP61202 EN threshold is 0.91 V, so U18 still enables.
- [!] -> [x] **(2026-10-24)** L1 must have Isat ≥ OCPmax + ripple = 12.4 + 2.9 ≈ 15.3 A. The old part (Cyntec CMLE051H, 250 nH) had no LCSC number and no known rating. It is now **Tai-Tech TMPC0503H-R22MG-D** (C357176): 220 nH, Isat 21 A, Irms 15.5 A, 3.7 mΩ, 5.7 × 5.2 mm. The new footprint `agilex_lib:L_TaiTech_TMPC0503H` follows the data sheet land pattern.
- [x] **(2026-10-24)** L2–L5 = 1 µH Cenker CKCS201610 (C97002: 2.05 A rated, 3.85 A saturation, 70 mΩ), the same as on the Agilex 3 card. The AP61202 data sheet asks for 1.0–1.5 µH and ≥ 1.35 × load; every rail stays well under 1.5 A. The DCR is above the data sheet's 50 mΩ efficiency suggestion, which costs little at these currents.
- [x] All AP61202 feedback dividers give the intended voltages (R81/R84/R87/R90 are DNP).
- [x] **(2026-10-24)** The dividers now use the AP61202 data sheet values (table 1: 200k top). With these, the 33 pF feed-forward capacitors C116–C119 put the zero where the data sheet intends (about 24 kHz). With the old 10k top resistors it sat at about 480 kHz.
- [x] U6 is `NCP163ASN330T1G` (3.3 V fixed) — was wrongly the 1.5 V `...150T1G` variant.
- [x] U19 / U8 / U16 `PG` pins (open drain) are wired-AND on `pg_all` with R249 10 k to 1V8 -> hierarchical `PG` -> root `pg_1v8` -> U42 channel 4 (1.8 V -> 3.3 V) -> `powergood` (SODIMM P1 pin 12, push-pull 3.3 V) and `pg_led` -> R16 -> D1. High only when 1V2, 3V3 and 1V1 are all in regulation (which implies VCORE and 1V8 are up).

## 2. Voltage per Agilex 5 supply pin group (from `fpga_power.kicad_sch`)

Rail groups are from table 3 of the Power Management UG. All pins of each group were checked; the count is the number of balls.

### Group 1 – core, must ramp first (all on `VCORE`, 0.75 V)

| Pin name | Balls | Net | |
|---|---|---|---|
| VCC | 21 | VCORE | [x] |
| VCCP | 7 | VCORE | [x] |
| VCCL_SDM | 4 | VCORE | [x] |
| VCCH_SDM | 1 (CD54) | VCORE | [x] (PCG: connect to VCCL_SDM when there are no transceivers) |
| VCC_IO_SDM | 1 (CT54) | VCORE | [x] sense pin, follows VCC |
| VCCL_ADC_SDM | 1 (CW52) | VCORE | [x] |
| VCCPLLDIG_SDM | 1 (CL49) | VCORE | [x] |
| VCCL_HPS | 4 | VCORE | [x] |
| VCCL_HPS_CORE0_CORE1 | 2 (AG46, AL46) | VCORE | [x] |
| VCCL_HPS_CORE2/3 | 4 (AL52, AL54, AR57, AW57) | VCORE | [x] (013B quad-core; on 008B these balls are GND) |
| VCCPLLDIG1_HPS / VCCPLLDIG2_HPS | 2 (BB54, BB52) | VCORE | [x] |
| VCC_HSSI_L | 2 (BJ54, BN54) | VCORE | [x] |
| VCCLSENSE / GNDSENSE | BN46 / BN44 | vcoresense_P / vcoresense_N | [x] Kelvin sense to U15 FB / VSNS– |

### Group 2A – 1.8 V, after Group 1 reaches 90 % (all on `1V8`)

| Pin name | Balls | Net | |
|---|---|---|---|
| VCCPT | 4 | 1V8 | [x] |
| VCCPT_HVIO | 10 | 1V8 | [x] |
| VCCIO_SDM | 1 (CW49) | 1V8 | [x] sets SDM I/O, JTAG, OSC_CLK_1 level = 1.8 V |
| VCCFUSEWR_SDM | 1 (CD52) | 1V8 | [x] |
| VCCPLL_SDM | 1 (CL46) | 1V8 | [x] |
| VCCADC | 1 (CG52) | 1V8 | [x] |
| VCCIO_HPS | 2 | 1V8 | [x] HPS I/O are 1.8 V only |
| VCCPLL1_HPS / VCCPLL2_HPS | 2 (BF57, BF52) | 1V8 | [x] |

### Group 2B – I/O, after Group 2A reaches 90 %

| Pin name | Balls | Net | |
|---|---|---|---|
| VCCRCORE | 3 | 1V2 | [x] 1.2 V |
| VCCIO_PIO_SDM | 1 (CW57) | 1V2 | [x] sense pin, follows VCCRCORE |
| VCCIO_PIO_2A_T / 2A_B | 4 | 1V2 | [x] |
| VCCIO_PIO_3A_T / 3A_B | 4 | 1V1 | [x] LPDDR4 (1.1 V) |
| VCCIO_HVIO_6B .. 6H | 14 | 3v3 | [x] 3.3 V LVCMOS banks |
| VCCIO_HVIO_6A | 2 (CL29, CT29) | 3v3 (was 1V8) | [x] (2026-10-24) see note below |

### Not sequenced

| Pin name | Ball | Net | |
|---|---|---|---|
| VCCBAT | CG49 | GND | [x] allowed when the BBRAM key is not used (UG 813161, 10/2025) |

**Note on VCCIO_HVIO_6A `[!]` (2026-10-24):** bank 6A was moved to 1.8 V so that the SDM 25 MHz clock can be fed to fabric PLL refclk pin CE19.
- **Order:** VCCIO_HVIO is a Group 2B rail. It now shares the 1V8 regulator with the Group 2A rails, so it ramps together with VCCPT instead of after it.
- **Sharing (decides it):** in the sharing table for -4S/-5S/-6S/-6X (813266 table 32), VCCIO_HVIO is regulator group 5, "**Isolate** – connect to a dedicated 3.3-V, 2.5-V, 1.8-V power supply". So sharing the VCCPT regulator is outside the guidelines.
- **Scope:** bank 6A carries nothing else. CE19 is its only connected pin; the `iob6a*` labels go nowhere.

Fixes:
1. Move VCCIO_HVIO_6A back to `3V3`, like banks 6B–6H, and disconnect `sdm_clk25` from CE19. The fabric then needs another reference clock: either a 3.3 V oscillator on AE11 (bank 6G, where the dangling `clk100` net already is, see §7) or the HPS h2f_user clocks. The HPS clocks only run once the HPS has booted, so they are not enough for PWM logic that has to run on its own.
2. Keep 6A at 1.8 V, but from its own small LDO fed from `3V3`. That makes it dedicated and Group 2B (it ramps after 3V3, which follows the 1V8 PG). CE19 keeps the 25 MHz clock, and `clk100` can be deleted.

The old option "a load switch from 1V8" no longer qualifies, because it is still the VCCPT regulator.

**Isolation filters `[!]` (2026-10-24):** table 32 marks these as "Filter", i.e. on the shared plane but "with proper isolation filtering":
- VCCPLL1_HPS, VCCPLL2_HPS, VCCADC and VCCPLL_SDM (on the VCCPT plane);
- VCCPLLDIG1_HPS, VCCPLLDIG2_HPS and VCCPLLDIG_SDM (on the VCC plane).

On this board all seven connect straight to `1V8` or `VCORE`. Add a ferrite bead plus local capacitor per pin or group, as on the PHY's FB1/FB2 (for example, BLM15PX121SN1 and 4.7 µF ‖ 100 nF).

**VCCPT regulator sharing `[ ]` (2026-10-24):** table 32 says to connect VCCPT to a dedicated 1.8 V supply, shared with VCCPT_HVIO, VCCIO_SDM, VCCIO_HPS and VCCFUSEWR_SDM. On this board, `1V8` also feeds:
- the QSPI flash and Y2;
- the PHY DVDDH and the level shifters' B side;
- the SD card mux and the pull-ups.

That is common practice, but those loads switch on the same regulator. Accept it, or give the board's 1.8 V I/O its own regulator in a later revision.

## 3. Power-up order implemented by the enable chain

```
5V0 applied
  |-- U6  3V3_analog LDO        (EN = VIN, immediately)
  |-- U15 VCORE 0.75 V          (EN = 5V0 / 3.43, on at VIN 4.2 V)  ... Group 1
        PGOOD (open drain, 10k to U15 VCC 3.0 V) ->
        U18 1V8                                                    ... Group 2A (+ VCCIO_HVIO_6A)
              PG (open drain, 47k to 5 V) ->
              U19 1V2  (VCCRCORE, VCCIO_PIO_SDM, 2A)   \
              U8  3V3  (HVIO 6B-6H)                     |  in parallel ... Group 2B
              U16 1V1  (3A / LPDDR4)                   /
```

- [x] Order is Group 1 -> 2A -> 2B as required (VCCIO_HVIO_6A excepted, see §2).
- [x] Each stage is gated by a PGOOD, so the "90 % before the next group starts" rule is met by construction (TPS548A28 and AP61202 PG assert at roughly 90–95 % of nominal).
- [x] All rails ramp monotonically (soft-start bucks, no pre-bias issues: every rail starts from 0 V because the previous rail's PG gates the next).
- [x] POR-monitored rails (VCCL_SDM, VCCPT, VCCIO_SDM, VCCADC, VCC, VCCL_HPS, VCCIO_PIO_SDM, VCCRCORE, VCC_IO_SDM) are all present and in the right groups.
- [x] The QSPI flash (1V8) and the 25 MHz oscillator Y2 (1V8) are up before the last Group 2B rail, so they are ready when the POR delay expires (AS fast mode, see §4).
- [x] **(2026-10-24)** Per-rail ramp: the data sheet tRAMP is 200 µs–100 ms for each supply.
  - AP61202 soft-start is 0.5 ms; its PG rises at 95 % of the target, 55 µs later (AP61202 data sheet).
  - TPS548A28: EN to first switching 0.93–2 ms, soft-start 2.3 ms (C199 + C200), PGOOD 1.06–1.4 ms after the output is in regulation.
- [!] **(2026-10-24)** AS fast mode (MSEL 001) requires **all** supplies to be fully ramped within 10 ms (813773 table 17 note 7; data sheet note 42). Here the regulators start one after another, gated by PG: VCORE soft-start + delay, then 0.5 ms (1V8), then 0.5 ms (1V2/3V3/1V1).
  - With the TPS548A28: VCORE PG after about 4.3–5.7 ms, then 1V8 (0.5 ms + 55 µs), then 1V2/3V3/1V1 (0.5 ms): about 5.4–6.8 ms in total, under 10 ms but without much margin.
  - AS normal mode (MSEL 011) only needs VCCIO_SDM to ramp within 10 ms, which the 0.5 ms 1V8 soft-start meets easily. The cost is a longer POR delay: 11.5–20.2 ms instead of 1.5–7.6 ms.
  - Table 17 labels fast mode "for CvP", which this board does not use. **Recommendation: change to AS normal mode.** See §4.
- [ ] Power-down: the UG only *recommends* the reverse order. Nothing on the board enforces it (all rails just decay when 5 V is removed). Acceptable for a lab board; if you want it, add a discharge/sequencer later.
- [ ] While 1V8 is up and 3V3 is not yet up, U1/U42 (SN74AXC4T774) see VCCB = 1.8 V and VCCA = 0 V – the AXC family is designed for this (Ioff, partial-power-down), no issue. The KSZ9031 PHY and the SD card mux likewise have their own supplies sequenced from 1V8/3V3 only.
- [ ] Reminder: during power-up no input pin may be driven above its bank's VCCIO. The 3.3 V UART header J10 and the JTAG header J1 are behind level shifters that are powered by the same rails, so this holds.

## 4. SDM / configuration pins (from `sdm.kicad_sch`)

| Pin | Ball | Schematic | Requirement | |
|---|---|---|---|---|
| nCONFIG | BK71 | `~{nconfig}`, R8 10k to 1V8, nothing else | 10 k pull-up to VCCIO_SDM; drive low to reconfigure | [x] (no push-button / test point – add one if you want to force reconfiguration from the bench) |
| nSTATUS | BM71 | `~{nstatus}`, R11 10k to 1V8 | 10 k pull-up, open-drain output | [x] |
| CONF_DONE | SDM_IO16 DA74 | `conf_done`, R10 10k to 1V8 (no LED; D1 is the power-good LED) | Output only. SDM_IO16 has an internal weak pull-down that holds CONF_DONE low until configuration (813773 §CONF_DONE/INIT_DONE note). The AS x4 reference circuit (figure 18) shows it as "optional monitoring", with no pull-up. Assign SDM_IO16 = CONF_DONE in Quartus. | [!] **(2026-10-24)** R10 overrides the internal pull-down, so the pin sits at ~1.2 V before configuration. Harmless, but the signal is meaningless until configured. Make R10 DNP, or remove it. |
| INIT_DONE | SDM_IO0 BK67 | `init_done`, R9 10k to 1V8 | Same as CONF_DONE: SDM_IO0's internal pull-down is "for the correct function of INIT_DONE during power up" (813266). Assign SDM_IO0 = INIT_DONE in Quartus. | [!] **(2026-10-24)** Make R9 DNP, or remove it. |
| MSEL0 | SDM_IO5 BY71 | R7 4k7 to 1V8 (shared with AS_nCSO0 / flash CS#) | 4.7 k pull | [x] = 1 |
| MSEL1 | SDM_IO7 CN67 | R45 4k7 to GND | 4.7 k pull | [x] = 0 now; **= 1 for AS normal mode** (R45 to 1V8) |
| MSEL2 | SDM_IO9 CN71 | R4 4k7 to GND | 4.7 k pull | [x] = 0 |
| MSEL[2:0] | | **001 = AS fast mode** (confirmed in 813773 table 17: AVST x16 101, AVST x8 110, AS fast 001 "for CvP", AS normal 011, JTAG only 111) | Fast mode needs all supplies fully ramped within 10 ms; normal mode only needs VCCIO_SDM within 10 ms (see §3). | [!] **(2026-10-24)** Change to **011** (AS normal): move R45 from GND to 1V8. |
| AS_CLK | SDM_IO2 CY69 | `qspi_CLK` -> U2 SCLK | | [x] |
| AS_DATA0..3 | SDM_IO4 / IO1 / IO3 / IO6 | `qspi_D0..D3` -> U2 SIO0..3; D2, D3 have 10 k pull-ups (R12, R14) | | [x] |
| AS_nCSO0 | SDM_IO5 | `~{qspi_CS}` -> U2 CS#, 4k7 pull-up | | [x] |
| AS_nRST | SDM_IO15 CY71 | `~{qspi_rst_n}` -> U2 RESET#, R15 10 k pull-up | | [x] |
| AS_nCSO3 | SDM_IO8 DB71 | NC | unused, internal weak pull-up | [x] |
| SDM_IO10 | CK69 | `~{hpscold_rstn}`. In the netlist it connects only to U7: no pull-up, and nothing drives it. | 813266: SDM_IO10 is a valid HPS_COLD_nRESET pin for AS x4. "Connect this pin through a 1–10-kΩ pull up to the VCCIO_SDM supply." The pin is bidirectional: the SDM pulses it low on an internal cold reset. Any external driver must be open-drain and release the pin. | [!] **(2026-10-24)** Add a 10 k pull-up to 1V8. Optionally add a push-button to GND, or a test point, for an HPS cold reset from the bench. |
| SDM_IO11, IO12, IO14 | DG71, BK69, BY69 | NC | unused | [x] |
| SDM_IO13 | DA75 | NC | unused | [x] |
| OSC_CLK_1 | DB72 | net `sdm_clk25` = 25 MHz from Y2 (SiT8924, 1.8 V) via R246 33 R | 25 / 100 / 125 MHz, 1.8 V CMOS, mandatory with EMIF | [x] |
| RREF | DH75 | R18 2k0 to GND | 2 kΩ ±1 % | [x] |
| VREFP_ADC, VREFN_ADC, VSIGP/N_0, VSIGP/N_1 | CF75, CF74, BW75, BW74, CJ74, CJ75 | GND | GND when the ADC is unused | [x] |
| TEMPDIODE0Ap / An | CK71, CN72 | NC | leave unconnected (external remote-diode temperature sensor input, unused) | [x] |
| JTAG TCK | CC64 | R22 1k0 to GND | 1 k pull-down | [x] |
| JTAG TMS, TDI | CY67, CC67 | R21, R19 10 k to 1V8 | 10 k pull-up | [x] |
| JTAG TDO | BY67 | R20 10 k to 1V8 | optional | [x] |
| JTAG header | J1 via U1 SN74AXC4T774 (1.8 V <-> 3.3 V) | | | [x] |
| VCCBAT | CG49 | GND | | [x] |
| QSPI flash | U2 IS25WP128-RHLE (128 Mbit, dedicated RESET# on A4; was MX25U25645G), VCC = 1V8 | 1.8 V flash required (SDM I/O are 1.8 V); SFDP and a dedicated reset pin for the generic-flash rule | | [x] |
| nCONFIG, nSTATUS | | R8, R11 10k to 1V8 | 813266: 10 kΩ to VCCIO_SDM (AS) | [x] (2026-10-24) |
| TCK / TMS / TDI | | 1k down / 10k up / 10k up | 813266: TCK 1 kΩ to GND (10 k up instead if attestation or BKP is used); TMS, TDI 1–10 kΩ up | [x] (2026-10-24) |
| RREF | | R18 2K0 | 2 kΩ ±1 %; check that the BOM part is 1 % | [x] (2026-10-24) |

## 5. Quartus / firmware settings implied by the schematic

- [ ] Configuration scheme: AS x4, normal mode once MSEL = 011 (fast mode as long as R45 still pulls down). Flash IS25WP128-RHLE (128 Mbit, generic SFDP flash, not on Altera's tested list; check that the Programmer accepts it).
- [ ] SDM I/O assignments: SDM_IO0 = INIT_DONE, SDM_IO16 = CONF_DONE, SDM_IO10 = HPS_COLD_nRESET, SDM_IO15 = AS_nRST (device-wide flash reset), others unused.
- [ ] OSC_CLK_1 frequency = 25 MHz.
- [ ] Banks 6A–6H = 3.3 V; fabric PLL refclk = AE11 `clk100` (100 MHz 3.3 V LVCMOS); CE19 unused; 2A = 1.2 V; 3A = 1.1 V (LPDDR4); HPS = 1.8 V.
- [ ] HPS clock: `hps_osc_clk25` on GPIO1_IO3 (AN67), 25 MHz.
- [ ] HPS GPIO1_IO14/IO15 = UART0 TX/RX (level-shifted by U42 to J10), GPIO1_IO18 = PHY reset.
- [ ] User LED D2 on CE6 (bank 6B, 3.3 V, ~2 mA source); D1 = power good (hardware, no assignment needed).

## 6. Summary of actions

1. `[x]` U6 value changed to `NCP163ASN330T1G` (3.3 V).
2. `[x]` NC flags added on SDM_TEMPDIODE0Ap / An (CK71, CN72).
3. `[x]` **(2026-10-24)** Fix 1 done: VCCIO_HVIO_6A on `3V3`, CE19 disconnected (no-connect flag), and Y4 (100 MHz 3.3 V CMOS, YXC OT3225100MJBA4SL, C4353707) drives `clk100` -> AE11 through R263 33 R.
4. `[x]` AP61202 PG pins wired-AND -> `powergood` (3.3 V via U42) + LED D1.
5. `[x]` `load_factory_image` label removed (SDM_IO13 NC); net renamed `sdm_clk25`.
6. `[x]` HPS_COLD_nRESET on SDM_IO10 is allowed for AS x4; MSEL 001 = AS fast is confirmed.
7. `[ ]` Optional: nCONFIG push-button / test point.
8. `[x]` **(2026-10-24)** MSEL = 011 (AS normal): R45 now to 1V8; R4 has its own GND.
9. `[x]` **(2026-10-24)** R264 10 k pull-up from `~{hpscold_rstn}` to 1V8 added.
10. `[x]` **(2026-10-24)** R9 (INIT_DONE) and R10 (CONF_DONE) are DNP.
11. `[ ]` **(2026-10-24)** Recommended, not fitted yet; a note is on the `fpga_power` sheet and on the PCB (Cmts.User): ferrite + capacitor isolation filters on VCCPLL1/2_HPS, VCCADC and VCCPLL_SDM (1V8), and on VCCPLLDIG1/2_HPS and VCCPLLDIG_SDM (VCORE).
12. `[x]` **(2026-10-24)** `clk100` (U7 AE11) is now driven by Y4 (§7).
13. `[ ]` **(2026-10-24)** Buck inductors L2–L5 (3V3, 1V8, 1V2, 1V1 regulators) have no value yet; size them from the AP61202 data sheet.

## 7. Fabric reference clocks (2026-10-24)

| Clock | Source | Destination | |
|---|---|---|---|
| `osc_clk_25` 25 MHz, 1.8 V | Y2 SiT8924 | HPS_OSC_CLK (AN67, GPIO1_IO3) | [x] |
| `sdm_clk25` | Y2 via R246 33 R | OSC_CLK_1 (DB72) only; CE19 is now unconnected | [x] OSC_CLK_1 needs 25/100/125 MHz when EMIF is used |
| `iob3A_refclk_P/N` 100 MHz LVDS | U9 AX3HAF1 via R25/R26, AC-coupled, biased by `VICM_REFCLK` | bank 3A CLK_B_3A_0 (B55/A58) | [x] LPDDR4 / HPS EMIF reference clock |
| `clk100` 100 MHz, 3.3 V CMOS | Y4 OT3225100MJBA4SL via R263 33 R (was: nothing) | AE11 (bank 6G PLLREFCLK1, 3.3 V) | [x] fabric PLL reference, independent of the HPS |

`clk100` sits on the clock sheet's `clk2_N` pin on the root sheet. Inside the clock sheet, `clk2_N` is a bare hierarchical label with no driver. It looks like a leftover from when `clk2` was meant as a differential pair. As it stands, AE11 floats.
- With fix 1 in §2, give it a real source: a 3.3 V CMOS oscillator (25 or 100 MHz) on AE11 becomes the fabric PLL reference, independent of the HPS. Remove the `clk2_N` sheet pin, and rename the net if the frequency changes.
- With fix 2, delete the `clk100` labels and the `clk2_N` sheet pin, and put a no-connect flag on AE11. The fabric then uses CE19 (25 MHz) as its PLL reference.
