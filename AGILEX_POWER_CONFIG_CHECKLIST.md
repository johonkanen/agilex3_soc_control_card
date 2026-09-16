# Agilex 5 (A5EB013B-B23B, -6S) power, configuration and power-up checklist

Generated from the schematic as of 2026-09-16 (root sheet, `fpga_power`, `fpga_gnd`, `sdm`, `ps`, `ps1`, `clk`, `hps`). Reference: Altera *Agilex 5 Power Management User Guide* (ID 813161, section 3.2 Power-Up Sequence Requirements, table 3) and the *Agilex 5 Pin Connection Guidelines* (ID 813266).

Legend: `[x]` verified correct in the schematic, `[ ]` open item / needs your decision, `[!]` error to fix.

---

## 1. Supply rails on the board

| Rail (net) | Source | Nominal | Enable | Loads |
|---|---|---|---|---|
| `5V0` / `5V` | J6 (2x3 header), also J4.3 | 5.0 V in | – | all regulators, U6 |
| `VCORE` | U15 TDA38812XUMA1 buck, remote sense via `vcoresense_P/N` (VCCLSENSE BN46 / GNDSENSE BN44), FB divider R2 10k / R1 39k -> 0.6 V x (1 + 10/39) = **0.754 V** | 0.75 V | EN tied to 5V0 -> starts as soon as 5 V is present | all Group 1 pins (see §2) |
| `1V8` | U18 AP61202Z6 buck, R82 10k / (R80 ‖ R81 = 5k) -> 1.80 V | 1.8 V | EN = `PG-Core` (U15 PGOOD, open-drain, R58 5.6k to 5V0) | Group 2A pins, VCCIO_HVIO_6A, Y2 (SiT8924 1.8 V), QSPI flash U2, all SDM/JTAG pull-ups, U1/U42 B-side, PHY 1.8 V |
| `3V3` / `3v3` | U8 AP61202Z6, R85 10k / R83 2k2 -> 3.33 V | 3.3 V | EN = U18 PG (open-drain, R65 47k to 5V) | VCCIO_HVIO_6B..6H, U9 100 MHz LVDS osc, U1/U42 A-side, headers |
| `1V2` | U19 AP61202Z6, R88 10k / R86 10k -> 1.20 V | 1.2 V | EN = U18 PG | VCCRCORE, VCCIO_PIO_SDM, VCCIO_PIO_2A_T/B |
| `1V1` | U16 AP61202Z6, R91 10k / R89 12k -> 1.10 V | 1.1 V | EN = U18 PG | VCCIO_PIO_3A_T/B (LPDDR4), refclk bias divider |
| `3V3_analog` | U6 NCP163 LDO from 5V0 | 3.3 V intended | EN tied to 5V0 | ADC subsystem |

- [x] VCORE set point 0.754 V matches the -6S core voltage; remote sense goes to the device sense pins.
- [x] All AP61202 feedback dividers give the intended voltages (R84/R87/R90 are DNP).
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
| VCCLSENSE / GNDSENSE | BN46 / BN44 | vcoresense_P / vcoresense_N | [x] Kelvin sense to U15 FB / RGND |

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
| VCCIO_HVIO_6A | 2 (CL29, CT29) | **1V8** | [ ] see note below |

### Not sequenced

| Pin name | Ball | Net | |
|---|---|---|---|
| VCCBAT | CG49 | GND | [x] allowed when the BBRAM key is not used (UG 813161, 10/2025) |

**Note on VCCIO_HVIO_6A:** bank 6A was moved to 1.8 V so that the SDM 25 MHz clock can be fed to fabric PLL refclk pin CE19. VCCIO_HVIO is a Group 2B rail, but it now shares the 1V8 regulator with the Group 2A rails, so it reaches 90 % at the same moment as VCCPT instead of after it. This is the only deviation from the published group order. Options, in order of effort:
1. Accept it (Altera's sharing table – which could not be retrieved while writing this – is the authority; if it allows a 1.8 V VCCIO to share the VCCPT regulator, nothing is needed).
2. Feed bank 6A through a small load switch from 1V8, enable driven by U18 PG: e.g. a second TPS22918 (already in the BOM for the SD card) – its soft start gives a clean, later ramp.
3. Move bank 6A back to 3.3 V and use another refclk pin (DP55 in bank 2A at 1.2 V, or BF23 / AE11 in 3.3 V banks).

## 3. Power-up order implemented by the enable chain

```
5V0 applied
  |-- U6  3V3_analog LDO        (EN = VIN, immediately)
  |-- U15 VCORE 0.75 V          (EN = VIN, immediately)            ... Group 1
        PGOOD (open drain, 5.6k to 5 V) ->
        U18 1V8                                                    ... Group 2A (+ VCCIO_HVIO_6A)
              PG (open drain, 47k to 5 V) ->
              U19 1V2  (VCCRCORE, VCCIO_PIO_SDM, 2A)   \
              U8  3V3  (HVIO 6B-6H)                     |  in parallel ... Group 2B
              U16 1V1  (3A / LPDDR4)                   /
```

- [x] Order is Group 1 -> 2A -> 2B as required (VCCIO_HVIO_6A excepted, see §2).
- [x] Each stage is gated by a PGOOD, so the "90 % before the next group starts" rule is met by construction (TDA38812 and AP61202 PG assert at roughly 90–95 % of nominal).
- [x] All rails ramp monotonically (soft-start bucks, no pre-bias issues: every rail starts from 0 V because the previous rail's PG gates the next).
- [x] POR-monitored rails (VCCL_SDM, VCCPT, VCCIO_SDM, VCCADC, VCC, VCCL_HPS, VCCIO_PIO_SDM, VCCRCORE, VCC_IO_SDM) are all present and in the right groups.
- [x] The QSPI flash (1V8) and the 25 MHz oscillator Y2 (1V8) are up before the last Group 2B rail, so they are ready when the POR delay expires (AS fast mode, see §4).
- [ ] The 10 ms total tRAMP limit only applies to CvP; not relevant here, but the total time from 5 V to the last PG is a few ms per stage – fine.
- [ ] Power-down: the UG only *recommends* the reverse order. Nothing on the board enforces it (all rails just decay when 5 V is removed). Acceptable for a lab board; if you want it, add a discharge/sequencer later.
- [ ] While 1V8 is up and 3V3 is not yet up, U1/U42 (SN74AXC4T774) see VCCB = 1.8 V and VCCA = 0 V – the AXC family is designed for this (Ioff, partial-power-down), no issue. The KSZ9031 PHY and the SD card mux likewise have their own supplies sequenced from 1V8/3V3 only.
- [ ] Reminder: during power-up no input pin may be driven above its bank's VCCIO. The 3.3 V UART header J10 and the JTAG header J1 are behind level shifters that are powered by the same rails, so this holds.

## 4. SDM / configuration pins (from `sdm.kicad_sch`)

| Pin | Ball | Schematic | Requirement | |
|---|---|---|---|---|
| nCONFIG | BK71 | `~{nconfig}`, R8 10k to 1V8, nothing else | 10 k pull-up to VCCIO_SDM; drive low to reconfigure | [x] (no push-button / test point – add one if you want to force reconfiguration from the bench) |
| nSTATUS | BM71 | `~{nstatus}`, R11 10k to 1V8 | 10 k pull-up, open-drain output | [x] |
| CONF_DONE | SDM_IO16 DA74 | `conf_done`, R10 10k to 1V8 (no LED; D1 is the power-good LED) | 10 k pull-up; assign SDM_IO16 = CONF_DONE in Quartus | [x] |
| INIT_DONE | SDM_IO0 BK67 | `init_done`, R9 10k to 1V8 | 10 k pull-up; assign SDM_IO0 = INIT_DONE in Quartus | [x] |
| MSEL0 | SDM_IO5 BY71 | R7 4k7 to 1V8 (shared with AS_nCSO0 / flash CS#) | 4.7 k pull | [x] = 1 |
| MSEL1 | SDM_IO7 CN67 | R45 4k7 to GND | 4.7 k pull | [x] = 0 |
| MSEL2 | SDM_IO9 CN71 | R4 4k7 to GND | 4.7 k pull | [x] = 0 |
| MSEL[2:0] | | **001 = Active Serial, fast mode** (011 would be AS normal mode, 111 JTAG only) | matches AS x4 flash on SDM_IO1..IO6 | [x] verify the value once against the Configuration UG (ID 813773) table – the docs site was down while this list was written |
| AS_CLK | SDM_IO2 CY69 | `qspi_CLK` -> U2 SCLK | | [x] |
| AS_DATA0..3 | SDM_IO4 / IO1 / IO3 / IO6 | `qspi_D0..D3` -> U2 SIO0..3; D2, D3 have 10 k pull-ups (R12, R14) | | [x] |
| AS_nCSO0 | SDM_IO5 | `~{qspi_CS}` -> U2 CS#, 4k7 pull-up | | [x] |
| AS_nRST | SDM_IO15 CY71 | `~{qspi_rst_n}` -> U2 RESET#, R15 10 k pull-up | | [x] |
| AS_nCSO3 | SDM_IO8 DB71 | NC | unused, internal weak pull-up | [x] |
| SDM_IO10 | CK69 | `~{hps_cold_rstn}` from the connectors sheet | HPS_COLD_nRESET must be assigned to this SDM_IO in Quartus; SDM_IO pins have internal weak pull-ups, so no external pull-up is required | [ ] check the assignment; check the driver on the connector side is open-drain/1.8 V |
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
| QSPI flash | U2 MX25U25645G, VCC = 1V8 | 1.8 V flash required (SDM I/O are 1.8 V) | | [x] |

## 5. Quartus / firmware settings implied by the schematic

- [ ] Configuration scheme: AS x4, fast mode; flash MX25U25645G (256 Mbit).
- [ ] SDM I/O assignments: SDM_IO0 = INIT_DONE, SDM_IO16 = CONF_DONE, SDM_IO10 = HPS_COLD_nRESET, SDM_IO15 = AS_nRST (device-wide flash reset), others unused.
- [ ] OSC_CLK_1 frequency = 25 MHz.
- [ ] Bank 6A VCCIO = 1.8 V, CE19 = `sdm_clk25` 1.8 V LVCMOS refclk; banks 6B–6H = 3.3 V; 2A = 1.2 V; 3A = 1.1 V (LPDDR4); HPS = 1.8 V.
- [ ] HPS clock: `hps_osc_clk25` on GPIO1_IO3 (AN67), 25 MHz.
- [ ] HPS GPIO1_IO14/IO15 = UART0 TX/RX (level-shifted by U42 to J10), GPIO1_IO18 = PHY reset.
- [ ] User LED D2 on CE6 (bank 6B, 3.3 V, ~2 mA source); D1 = power good (hardware, no assignment needed).

## 6. Summary of actions

1. `[x]` U6 value changed to `NCP163ASN330T1G` (3.3 V).
2. `[x]` NC flags added on SDM_TEMPDIODE0Ap / An (CK71, CN72).
3. `[ ]` Decide how to handle VCCIO_HVIO_6A on the shared 1V8 (§2 note).
4. `[x]` AP61202 PG pins wired-AND -> `powergood` (3.3 V via U42) + LED D1.
5. `[x]` `load_factory_image` label removed (SDM_IO13 NC); net renamed `sdm_clk25`.
6. `[ ]` Confirm HPS_COLD_nRESET on SDM_IO10 and the MSEL = 001 (AS fast) entry against the Configuration UG.
7. `[ ]` Optional: nCONFIG push-button / test point.
