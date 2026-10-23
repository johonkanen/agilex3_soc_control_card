# agilex3_soc_control_card
Agilex 5 SoC based control card for an AC in/out lab power supply.
The original board used an Agilex 3 FPGA and had a few bugs in the pin connections, so this second revision
uses an SoC instead of just an FPGA. The target is a Linux-capable control board with an Ethernet connection.

Main features:
- Agilex 5 E-Series SoC A5EB013B (quad-core HPS), B23B 795-ball package, -6S speed grade
- 1 GB LPDDR4 (ISSI IS43LQ32256A, x32)
- 1 Gb Ethernet (KSZ9031RNX RGMII PHY)
- microSD
- muxed ADC block (ADS7056)

Controls power electronics, so it mostly does generic I/O for PWM and SPI/SDM ADCs.
Built by JLCPCB (8-layer, JLC08161H-3313 stack-up).

## Credits

The Agilex 5 schematic sheets in `a5e_kicad/` started from the DBM_A5E013 example KiCad project by
Rolf (Altera), attached to his KiCad symbol library merge request
[kicad-symbols !5361](https://gitlab.com/kicad/libraries/kicad-symbols/-/merge_requests/5361), and have
since been heavily modified. The U7 symbol and the `Altera_B23B` footprint come from his Agilex symbol and
footprint generators ([kicad-symbols !5565](https://gitlab.com/kicad/libraries/kicad-symbols/-/merge_requests/5565),
[kicad-library-tools !2200](https://gitlab.com/kicad/libraries/kicad-library-tools/-/merge_requests/2200)).
