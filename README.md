# agilex3_soc_control_card
agilex 3 soc platform based control card for ac in/out lab power supply

target is to create a Linux capable Control Board with ethernet connection using A3CW100BM16AE6S SoC
Alternatively I could use Agilex 5 A5E(E/B)008B23BE6SCS

Original board used Agilex 3 FPGA and had a few bugs in pin connections so this is second revision with SoC instead of FPGA


Main features :
1Gb ethernet
microSD
(1GB? 2GB?) LPDDR4
muxed adc block

Controls power electronics so mostly does generic io for pwm and spi/sdm adc
