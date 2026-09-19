# Ethernet PHY review – U10 KSZ9031RNX (eth.kicad_sch)

Reviewed 2026-09-19 against the KSZ9031RNX datasheet (DS00002117) and the Agilex 5 HPS EMAC0 pin mux (Altera GSRD, Terasic DE25-Nano baseline, same B23B package).

## Verified OK

| Item | Finding |
|---|---|
| RGMII → HPS | EMAC0 dedicated IO: TX_CLK BP75 (IOA_13), TX_CTL BL74, TXD0-3 BG74/AP75/BD75/AM74, RX_CLK BL75, RX_CTL AP74, RXD0-3 BD74/AN71/AJ74/AJ75, MDIO C74 (IOB_23), MDC D71 (IOB_24). INT_N → Y75 (GPIO1_IO4), RESET_N → K71 (GPIO1_IO18). |
| HPS IP settings | EMAC0 pin muxing = IO, EMAC0 mode = RGMII_with_MDIO, GPIO1:IO4 and GPIO1:IO18 enabled. |
| Straps | MODE[3:0] = 1111 (RGMII, all speeds), CLK125_EN = 0, LED_MODE = 1 (single LED), PHYAD = 000; 4k7 up / 1k down. |
| Pull-ups | MDIO, INT_N 4k7 to DVDDH (1.8 V) – datasheet range 1.0–4.7 kΩ. |
| ISET | 12k1 1 % (R41). |
| LDO_O | Left open – allowed with external 1.2 V (pin is an LDO controller output, never to be driven). |
| Crystal | 25 MHz ±50 ppm required; 27p load caps suit an 18 pF crystal (Abracon ABM8-25.000MHZ-B2-T, ECS-250-18-33-TR). |
| 1.2 V / 3.3 V decoupling | AVDDL_PLL 22u+100n, AVDDL 22u+100n, DVDDL 22u+5×100n, AVDDH 22u+2×100n. |
| Jack | Fixed earlier (CT 100n, GND/SH, green LED via U42 ch3). |

## Fixed in r16

1. **DVDDH (pins 16/34/40) had no decoupling** – C256/C257 100n (empty slots on the 1V8 bus) + C258 22u 6V3 added.
2. **Ferrite beads** FB1 (3V3 → PHY3V3 = AVDDH) and FB2 (1V2 → PHY1V2PLL = AVDDL_PLL), Murata BLM15PX121SN1 (0402, 120 Ω @ 100 MHz, 1.5 A). AVDDL (pins 4/9) left directly on 1V2; its PHY1V2 power symbols renamed 1V2.
3. **RESET_N** – R247 10k now pulls up to `pg_all` (power-good wired-AND on ps1, new global label on the root sheet) instead of 1V8, plus C259 1u to GND: reset stays asserted until 1V2/3V3/1V1 are good (1V2 comes up after 1V8, so a 1V8 pull-up released the PHY before its core supply existed). The HPS GPIO can still drive it.
4. **NC flags** on pins 13 and 47 (not bonded).
5. **22 Ω series resistors** R251–R256 (TX_EN, TXD0-3, GTX_CLK – place at the HPS end) and R257–R262 (RX_DV, RXD0-3, RX_CLK – place at U10). Optional at the ~10–20 mm PHY–HPS distance; fit 0R if not wanted.

## Software / PCB notes

- RGMII delay: the PHY adds 1.2 ns on RX_CLK by default (pad-skew MMD 2 reg 8, up to 2.58 ns) and nothing on the TX side, so the GTX_CLK delay must come from the HPS (IO output delay chain on HPS_IOA_13) or `phy-mode = "rgmii-id"` with the Micrel driver's pad-skew settings. Do not add trace-length delay.
- Linux: CONFIG_MICREL_PHY, PHY at address 0, `reset-gpios` = GPIO1_IO18, `interrupts` = GPIO1_IO4.
- Y3 is on B.Cu while U10 and C251/C252 are on F.Cu (XI/XO through vias) and it lies under the J9 through-hole area – consider moving it to F.Cu next to pins 45/46.
- 22u 0402 6.3 V caps lose roughly half their capacitance at 3.3 V bias – acceptable, just be aware.
