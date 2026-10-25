# Ethernet PHY review – U10 (eth.kicad_sch)

## 2026-10-25: U10 changed to Realtek RTL8211FDI-CG

The KSZ9031RNX had only 16 orderable at JLCPCB (the KSZ9131 75, the DP83867 9). It is replaced by the **RTL8211FDI-CG**
(C692886, 8.5k free; QFN-40 5x5, industrial temperature range). Checked against the RTL8211F(I)/FD(I) data sheet,
Rev 1.4.

- **Configured over MDIO; only two straps.**
  - CFG_LDO[1:0] = 10: R35 4K7 pull-down on LED1, R268 4K7 pull-up on LED2. This sets the internal RGMII/MDIO I/O LDO
    to 1.8 V; the default 01 would be 2.5 V.
  - Every other config pin keeps its internal default: PHY address 1 (it also answers broadcast address 0), RXDLY=1,
    TXDLY=0, CFG_EXT=0 (internal LDO), PLLOFF=0.
  - The KSZ strap resistors R29, R31–R34 and R37–R39 are DNP.
  - The pins were placed where the KSZ pins of the same function were, so the RGMII series resistors, MDI wiring,
    crystal and RSET (ex-ISET) stay as they were. The netlist was checked pin by pin.
- **Supplies:**
  - DVDD33 on 3V3; AVDD33 on PHY3V3 via FB1.
  - The internal LDO_OUT (pin 30) makes the 1.0 V net PHY1V0, which feeds only AVDD10/DVDD10. Its caps are the old
    1V2 PHY caps, with C21/C27 now 1u.
  - DVDD_RG (pin 28) is the 1.8 V I/O LDO output, net PHY_RG. It has caps only: C256/C257 100n and C258 1u.
  - No 1.2 V rail is needed any more: FB2/C18/C19 are DNP.
- **I/O levels:** RGMII, MDC, MDIO and INTB are in the 1.8 V domain, so they connect directly to the HPS.
- **MDIO pull-up:** R36 is now 1K5, as the data sheet asks.
- **PHYRSTB is a 3.3 V input** (VIH 2.0 V). U42 channel 3 (1.8 -> 3.3 V) now drives it:
  - HPS GPIO1_IO18 `eth_rst_n` -> U42 B3/A3 -> `phy_rst_n`.
  - R247 still holds `eth_rst_n` low until software releases it.
  - Hold low >= 10 ms, then wait >= 50 ms before MDIO access.
- **LED:** LED2 (1000M link/act, active low, 3.3 V) drives the J9 green LED directly. It previously went through
  U42 ch3.
- **RSET:** R41 is now 2K49 1 %. That is the usual reference value; check it against Realtek's reference schematic,
  because the data sheet text doesn't give it.
- **Linux:** `realtek.c`, `phy-mode = "rgmii-id"`, `reset-gpios` = GPIO1_IO18 (active low), PHY address 1.
- **Pin-compatible fallback:** Motorcomm YT8531C-CA (C22472312). It needs only CFG_LDO1 pulled up with an external
  DVDD_RGMII, plus an inductor on pin 30.

The KSZ9031 review below is kept for history.


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
3. **RESET_N** – R247 10k pulls down to GND, plus C259 1u to GND: the PHY stays in reset until software drives HPS GPIO1_IO18 (K71) high, so the processor has full control and the reset is released only after all rails are up (a 1V8 pull-up would release it before 1V2 exists). Software must hold it low >= 10 ms after power-up and drive it high to release (push-pull, not open-drain; Linux: `reset-gpios = <... 18 GPIO_ACTIVE_LOW>`), then wait >= 100 us before MDIO access. (Earlier revision: 10k to `pg_all`; changed 2026-10-23.)
4. **NC flags** on pins 13 and 47 (not bonded).
5. **22 Ω series resistors** R251–R256 (TX_EN, TXD0-3, GTX_CLK – place at the HPS end) and R257–R262 (RX_DV, RXD0-3, RX_CLK – place at U10). Optional at the ~10–20 mm PHY–HPS distance; fit 0R if not wanted.

## Software / PCB notes

- RGMII delay: the PHY adds 1.2 ns on RX_CLK by default (pad-skew MMD 2 reg 8, up to 2.58 ns) and nothing on the TX side, so the GTX_CLK delay must come from the HPS (IO output delay chain on HPS_IOA_13) or `phy-mode = "rgmii-id"` with the Micrel driver's pad-skew settings. Do not add trace-length delay.
- Linux: CONFIG_MICREL_PHY, PHY at address 0, `reset-gpios` = GPIO1_IO18, `interrupts` = GPIO1_IO4.
- Y3 is on B.Cu while U10 and C251/C252 are on F.Cu (XI/XO through vias) and it lies under the J9 through-hole area – consider moving it to F.Cu next to pins 45/46.
- 22u 0402 6.3 V caps lose roughly half their capacitance at 3.3 V bias – acceptable, just be aware.
