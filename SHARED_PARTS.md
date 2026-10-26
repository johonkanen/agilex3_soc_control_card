# Parts shared with the Agilex 3 card and the Ti135 board

Three parts were picked on 2026-10-23 so that the same reel serves this board (Agilex 5 A5EB013B), the Agilex 3 card
(`~/dev/ti60f225_control_card`) and the planned Efinix Ti135N484I3 board (`~/dev/efinix_soc_board`, see its
`MIGRATION_PLAN.md`). All three are being bought from JLCPCB stock, through the parts pre-order into "My Parts Lib".
They are extended parts. Stock and prices are JLC's on 2026-10-23.

| Function | Part | LCSC | Package | JLC stock | Price each | Replaces here |
|---|---|---|---|---|---|---|
| LPDDR4, 1 GB | SK hynix H9HCNNN8KUMLHR-NME | C2912103 | 200-ball FBGA, 10 × 15 mm | 121 | $26.56 (30+: $25.14) | U12 IS43LQ32256A-062BLI |
| eMMC, 16 GB | KIOXIA THGAMVG7T13BAIL | C7599693 | 153-ball WFBGA, 11.5 × 13 mm | 179 | $23.11 (30+: $21.87) | microSD (J8, U11, U40, U41) |
| QSPI flash, 128 Mbit | ISSI IS25WP128-RHLE | C1349419 | 24-ball TFBGA, 6 × 8 mm | 68 | $4.57 (30+: $3.52) | U2 MX25U25645G |

The ISSI IS43LQ32256A and every other ISSI LPDDR4 part had 0 JLC stock on 2026-10-23. So did the MX25U25645G in the
24-ball package (only the 8-pin WSON was stocked, and it has no dedicated reset pin).

## LPDDR4: SK hynix H9HCNNN8KUMLHR-NME

Checked against the SK hynix data sheet (H9HCNNN8KUMLHR Series Rev 1.1, from LCSC):

- **LPDDR4, not LPDDR4X.** VDD1 / VDD2 / VDDQ = 1.8 / 1.1 / 1.1 V, the same rails as now (`1V8`, `1V1`).
- 8 Gb = 1 GB, x16 × 2 channels, **1 rank** (1 CS), 3733 Mbps, −25…85 °C.
- The standard JEDEC 200-ball 2-channel ball map. It matches the current U12 wiring:
  - ZQ0 on A5, A8 NC;
  - RESET_n on T11;
  - ODT_CA_A/B (G2/T2) tied to `1V1`;
  - CKE0/CS0 used, the CS1/CKE1 positions NC.
- Quartus EMIF: LPDDR4, 1 channel × 32, 1 rank. 8 Gb is the whole package: 4 Gb per channel (32,768 rows, 8 banks,
  x16). Enter 4 Gb where the IP asks for density per channel or per die.

The cheaper -NMO (C51891855) is **not** in the data sheet's ordering table, which lists only -NLE, -NME, -NLI and
-NMI, so it is not used. Single-rank was chosen on purpose: it was not confirmed whether the Agilex 5 EMIF supports
dual-rank LPDDR4.

Status on this board:

- [x] **U12 footprint changed to `agilex_lib:BGA-200_10x15mm_Layout12x22_P0.8x0.65mm`** (schematic and PCB). It is a
  copy of KiCad's `Package_BGA:BGA-200_10x14.5mm_Layout12x22_P0.8x0.65mm` with identical pads. The fab, silk and
  courtyard outlines are 0.25 mm longer at each end, for the 15 mm SK hynix body. Position, pads, nets and tracks were
  not touched. DRC: unconnected and parity counts unchanged.
- [ ] **Courtyard overlap U12 ↔ R43** (240 Ω ZQ resistor, x = 175.00 mm). U12 is rotated −90°, so its courtyard now ends
  at x = 174.29 mm. Move R43 about 0.25 mm in +X and fix its tracks.
- [ ] Five `lpddr_xtalk_spacing` violations on dq24/dq25/dq28 dropped out of DRC only because those segments now lie
  inside U12's larger courtyard, where `lpddr_bga_neckdown` applies. They were not re-routed.
- [x] U12 Value changed to H9HCNNN8KUMLHR-NME, LCSC C2912103 (schematic). The lib symbol is still the JEDEC-compatible
  `Memory_RAM:IS43LQ32256A-062BLI`; all 68 signal balls were checked against the SK hynix ballout. The PCB picks up the
  new value on the next "Update PCB from Schematic".

## eMMC: KIOXIA THGAMVG7T13BAIL

Checked against the KIOXIA data sheet (2021):

- **VCCQ = 1.7–1.95 V only.** It is a 1.8 V-only I/O part (OCR bit 7), so it connects directly to the 1.8 V HPS SD/MMC
  pins. **No level translator, no 3.3 V / 1.8 V switching, no card detect.**
- VCC = 2.7–3.6 V (`3V3`).
- The data sheet requires host and device VCCQ from the same supply, so put the eMMC VCCQ on `1V8`.
- eMMC 5.1, 1/4/8-bit, all modes up to HS400 specified at 1.8 V.

Circuit:

| Item | Value |
|---|---|
| CMD pull-up to VCCQ | 4.7–100 kΩ |
| DAT0–7 pull-ups to VCCQ | 10–100 kΩ |
| DS (HS400 strobe) pull-down | 10–100 kΩ |
| VDDi | 2.2 µF (1–4.7 µF) |
| VCC | 4.7 µF + 0.22 µF |
| VCCQ | 4.7 µF + 0.1 µF |

RST_n is disabled by default (EXT_CSD[162] RST_n_FUNCTION = 0). Enable it from software if the HPS should be able to
reset the eMMC.

Status on this board (2026-10-26): **in the schematic** (`a5e_kicad/hps.kicad_sch`). The microSD subsystem is removed:
J8, U40, U41, C240, C241, C247 and C248 are gone. The eMMC reuses the ref **U11**, and some refs were reused for new
parts:

| Ref | Part | Net |
|---|---|---|
| U11 | THGAMVG7T13BAIL (C7599693), `Package_BGA:LFBGA-153_11.5x13mm_Layout14x14_P0.5mm` | VCC `3V3`, VCCQ `1V8`, VSS/VSSQ `GND` |
| R241, R272–R279 | 10k pull-ups to `1V8` | `sd_cmd`, `sd_d0`–`sd_d7` |
| R243 | 10k pull-up to `1V8` | `emmc_rst_n` (U7 AD71, GPIO1_IO17, was `sd_pwr_en`) |
| R242 | 10k pull-down | DS (HS400 strobe, unused) |
| C242, C243 | 4u7 + 100n | VCCQ `1V8` |
| C244, C245 | 4u7 + 220n (C16772) | VCC `3V3` |
| C246 | 2u2 | VDDi |

U7 F75 (GPIO1_IO16, was `sd_vsel`) is now unconnected. The PCB is **not** updated yet: run the sync, then place U11 and
its parts. Only about 20 balls are used: DAT0–7 are in rows A/B (edge); the supply, CMD/CLK/DS/RST_n balls are inside
the array and need via-in-pad at 0.5 mm pitch.

`SDCARD.md` says eMMC was not stocked in small quantities in September 2026. That is no longer true at JLC.
Also note the `SDCARD.md` remark that Agilex 5 engineering samples fail to boot from eMMC in HS200/HS400; production
devices are unaffected.

## QSPI flash: ISSI IS25WP128-RHLE

- 1.8 V (1.65–1.95 V), SFDP, **dedicated RESET# on ball A4**. These meet the Agilex 5 generic QSPI rule: SFDP and a
  dedicated reset pin (Configuration UG 813773, section 8.4).
- **Same ball map as the current U2 footprint and symbol** (`MX25U25645G_CSP24_6x8mm_P1.0mm`): A4 RESET#, B2 CLK, B3 GND,
  B4 VCC, C2 CS#, C4 DQ2, D2 DQ1, D3 DQ0, D4 DQ3. Swap the part only; footprint and wiring stay.
- **128 Mbit is enough.** The flash holds only the bitstream and boot loader; Linux goes on the eMMC. The A5E 013 RBF is
  at most 4 MB (UG 813773, Table 2), including the HPS FSBL, so a fallback image also fits. Below 256 Mbit the SDM stays
  in 3-byte addressing, which also avoids the known wrong address-mode field in the IS25WP256D's SFDP table.
- Not on Altera's tested-device list, only "generic". **Check on the first board** that the Quartus Programming File
  Generator / Programmer accept it for the .jic, and that AS ×4 configuration works.
- Drop-in fallback: Micron MT25QU256ABA8E12-1SIT (C2061023, Altera-tested, 248 pcs, ~$20), on the same footprint.
- The IS25WP family is also on Efinix's verified flash list for Titanium, which is why it was chosen over Winbond.

Status on this board:

- [x] U2 Value changed to IS25WP128-RHLE, LCSC C1349419 (schematic). Order the **H** package code (5x5 array); -RGLE is
  the 4x6 array and does not fit this footprint. The lib symbol is still `agilex_5_lib:MX25U25645G` (same ball map).
- [ ] Update `AGILEX_POWER_CONFIG_CHECKLIST.md` §4/§5, which still name the MX25U25645G (256 Mbit).
