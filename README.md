# agilex3_soc_control_card
agilex 3 soc platform based control card for ac in/out lab power supply
Original board used Agilex 3 FPGA and had a few bugs in pin connections so this is second revision with SoC instead of just FPGA

target is to create a Linux capable Control Board with ethernet connection using A3CW100BM16AE6S SoC
Alternatively I could use Agilex 5 A5E(E/B)008B23BE6SCS

Main features :
Agilex 5 SoC (A5EB008B23BE6SCS)
1Gb ethernet
microSD
(1GB? 2GB? 4GB?) LPDDR4
muxed adc block

Controls power electronics so mostly does generic io for pwm and spi/sdm adc

## Credits

The Agilex 5 schematic sheets in `a5e_kicad/` started from the DBM_A5E013 example KiCad project by
Rolf (Altera), attached to his KiCad symbol library merge request
[kicad-symbols !5361](https://gitlab.com/kicad/libraries/kicad-symbols/-/merge_requests/5361), and have
since been heavily modified. The U7 symbol and the `Altera_B23B` footprint come from his Agilex symbol and
footprint generators ([kicad-symbols !5565](https://gitlab.com/kicad/libraries/kicad-symbols/-/merge_requests/5565),
[kicad-library-tools !2200](https://gitlab.com/kicad/libraries/kicad-library-tools/-/merge_requests/2200)).
