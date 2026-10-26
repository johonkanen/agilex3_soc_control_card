# HPS pin mux (U7 HPS IO, 1.8 V)

Changed 2026-10-26 so that the SD/MMC and Ethernet groups no longer cross on the PCB. The HPS balls are on U7's right
edge. HPS_IOA_1–12 are in the lower part (y ≈ 109–113 mm), toward the eMMC (U11, lower right). HPS_IOB_9–24 are in the
upper part (y ≈ 102–108 mm), toward the PHY (U10, upper right).

Sources: the Altera B23B pin list (HPS Function / Optional Function columns) and the pin connection guidelines 813266
(Table 21 HPS SDMMC pins; HPS_OSC_CLK may be on any of the 48 HPS IO).

| HPS IO | Ball | Function | Net |
|---|---|---|---|
| IOA_1 | BC64 | SDMMC_DATA0 | `sd_d0` |
| IOA_2 | BC67 | SDMMC_DATA1 | `sd_d1` |
| IOA_3 | AY67 | SDMMC_CLK | `sd_clk` |
| IOA_6 | BA75 | SDMMC_DATA2 | `sd_d2` |
| IOA_7 | BC71 | SDMMC_DATA3 | `sd_d3` |
| IOA_8 | AU74 | SDMMC_CMD | `sd_cmd` |
| IOA_9 | AY71 | SDMMC_DATA4 | `sd_d4` |
| IOA_10 | AU75 | SDMMC_DATA5 | `sd_d5` |
| IOA_11 | BC72 | SDMMC_DATA6 | `sd_d6` |
| IOA_12 | BP74 | SDMMC_DATA7 | `sd_d7` |
| IOA_13 | BP75 | GPIO0_IO12 | `emmc_rst_n` |
| IOA_16 | AP74 | SDMMC_DATA_STROBE | `emmc_ds` (HS400 strobe; R242 10k pull-down) |
| IOA_23 | AJ74 | UART0_TX | `hps_uart0_tx` |
| IOA_24 | AJ75 | UART0_RX | `hps_uart0_rx` |
| IOB_2 | AC75 | GPIO1_IO1 | `eth_rst_n` |
| IOB_4 | AN67 | HPS_OSC_CLK | `osc_clk_25` (unchanged) |
| IOB_5 | Y75 | GPIO1_IO4 | `~{eth_int}` (unchanged) |
| IOB_7 | Y74 | I2C1_SDA | `i2c_sda` |
| IOB_8 | AK69 | I2C1_SCL | `i2c_scl` |
| IOB_9 | U74 | MDIO2_MDIO | `eth_mdio` |
| IOB_10 | AK67 | MDIO2_MDC | `eth_mdc` |
| IOB_13 | L75 | EMAC2_TX_CLK | `eth_gtx_clk` |
| IOB_14 | N72 | EMAC2_TX_CTL | `eth_tx_en` |
| IOB_15 | N71 | EMAC2_RX_CLK | `eth_rx_clk` |
| IOB_16 | AD72 | EMAC2_RX_CTL | `eth_rx_dv` |
| IOB_17 | F75 | EMAC2_TXD0 | `eth_txd0` |
| IOB_18 | AD71 | EMAC2_TXD1 | `eth_txd1` |
| IOB_19 | K71 | EMAC2_RXD0 | `eth_rxd0` |
| IOB_20 | AK71 | EMAC2_RXD1 | `eth_rxd1` |
| IOB_21 | F74 | EMAC2_TXD2 | `eth_txd2` |
| IOB_22 | AA71 | EMAC2_TXD3 | `eth_txd3` |
| IOB_23 | C74 | EMAC2_RXD2 | `eth_rxd2` |
| IOB_24 | D71 | EMAC2_RXD3 | `eth_rxd3` |

Unused (no-connect): IOA_4, IOA_5, IOA_14, IOA_15, IOA_17–22, IOB_1, IOB_3, IOB_6, IOB_11, IOB_12.

## HPS IP settings (Platform Designer)

- `EMAC2_PinMuxing` IO, `EMAC2_Mode` RGMII_with_MDIO. EMAC0 and EMAC1 unused.
- `SDMMC_PinMuxing` IO, `SDMMC_Mode` 8-bit.
- `UART0_PinMuxing` IO, `UART0_Mode` No_flow_control. UART1 unused.
- `I2C1_PinMuxing` IO.
- `HPS_IO_Enable` (IOA_1…24, then IOB_1…24):

```
SDMMC:DATA0 SDMMC:DATA1 SDMMC:CCLK NONE NONE SDMMC:DATA2 SDMMC:DATA3 SDMMC:CMD SDMMC:DATA4 SDMMC:DATA5 SDMMC:DATA6 SDMMC:DATA7
GPIO0:IO12 NONE NONE SDMMC:DATA_STROBE NONE NONE NONE NONE NONE NONE UART0:TX UART0:RX
NONE GPIO1:IO1 NONE HCLK:HPS_OSC_CLK GPIO1:IO4 NONE I2C1:SDA I2C1:SCL MDIO2:MDIO MDIO2:MDC NONE NONE
EMAC2:TX_CLK EMAC2:TX_CTL EMAC2:RX_CLK EMAC2:RX_CTL EMAC2:TXD0 EMAC2:TXD1 EMAC2:RXD0 EMAC2:RXD1 EMAC2:TXD2 EMAC2:TXD3 EMAC2:RXD2 EMAC2:RXD3
```

## Software

- Ethernet is `gmac2` (not `gmac0`), with MDIO on the gmac2 MDIO bus.
- The PHY reset is GPIO1_IO1 (`reset-gpios = <&gpio1 1 GPIO_ACTIVE_LOW>`); the PHY interrupt is GPIO1_IO4.
- eMMC speed: HS200 (8-bit SDR, 200 MHz) needs no strobe. With DS on IOA_16 the board also allows HS400 (DDR,
  200 MHz); check driver support before enabling `mmc-hs400-1_8v`. Start with `mmc-hs200-1_8v`.
- The console is UART0. The eMMC reset is GPIO0_IO12; it only works after EXT_CSD[162] RST_n_FUNCTION is set.
- The RGMII TX clock delay now applies to HPS_IOB_13 (EMAC2_TX_CLK).

## Quartus check

Fit run 2026-10-26 in `~/dev/agilex5_emif_test` (Quartus Pro 26.1.1, A5EB013BB23BE6S). Build:
`HPS_BOARD=1 HPS_IO="$(tr '\n' ' ' < src/hps_io_board.txt)" TOP_V=$PWD/src/emif_test_top_board.v CSV=src/u7_bank3_pins_reroute2.csv TAG=_hpsmux REFCLK=100.0 scripts/build_csv.sh A`
(result in `varA_hpsmux/`). The top level exports every HPS IO, so none are swept away.

- Platform Designer, Synthesis and Timing Analyzer: 0 errors, 0 warnings. Fitter: 0 errors, 2 warnings:
  - 171167, invalid assignments from the HPS IP (the same as in the clean reference build);
  - 25315, no drive-strength/slew assignments on the HPS IO (the test project sets no I/O assignments).
- The fitter put all 32 HPS signals on the expected balls. A script checked them against the KiCad netlist: 0
  mismatches.
- Re-run 2026-10-26 with `SDMMC:DATA_STROBE` on IOA_16 (`TAG=_hpsds`, result in `varA_hpsds/`; the top level gains
  `HPS_SDMMC_STROBE`). Same result: 0 errors, the same 2 fitter warnings, and `HPS_SDMMC_STROBE` on AP74 (package delay
  93 ps).
