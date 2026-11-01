You are verifier **v1_power** (power and schematic claims). First read and follow
/home/jari/dev/agilex3_soc_control_card/review/prompts/verify_common.md. Your report is `review/v1_power.md`, your
scratch folder `review/work/v1_power/`.

Claims to verify (as the reviewers stated them):

- **A1-01:** PLL/ADC supply balls of U7 are connected to the shared rails without isolation filters: VCCPLL1/2_HPS,
  VCCPLL_SDM and VCCADC directly on 1V8, VCCPLLDIG1/2_HPS and VCCPLLDIG_SDM directly on VCORE, while Altera 813266
  (Tables 12/17/32) requires isolation filtering. Proposed fix was a ferrite bead + 4.7 uF + 100 nF per group (seven
  nodes). Verify the requirement and the topology/values Altera actually asks for, per ball group.
- **A1-02 / A2-04:** `eth_rst_n` (U7 ball AC75, HPS GPIO1_IO1) goes through level shifter U42 to the PHY reset. R247
  10k pull-down fights the HPS pin's 15-25 kOhm weak pull-up during boot, so the idle level is 0.51-0.76 V, above
  U42's VIL (0.63 V); C259 (1 uF) on the line violates U42's input edge-rate limit (10 ns/V). Proposed fix: R247 4.7k,
  C259 not fitted. Check the HPS pin's state during reset/boot, U42's input specs, and whether the PHY reset timing
  still works without C259.
- **A2-01:** 5V0 input has no over-voltage, reverse-polarity or fuse protection; J4 (GND/GND/5V0) and J6 (odd row GND,
  even row 5V0) can be mated reversed; the lowest absolute maximum on 5V0 is 6.0 V (U6 NCP163) and the 5V0 bulk
  capacitors are 6.3 V parts.
- **A2-02:** Y2 (SiT8924BA-78-18E, 25 MHz, the SDM configuration clock and HPS clock) is the output-enable variant and
  its pin 1 is left floating, while the datasheet asks for <= 10 kOhm to VDD (or the no-OE variant).
- **A2-03:** U1 A1-A3 (JTAG TDI/TCK/TMS from J1) and U42 A2 (UART RX from J10) float on the 3.3 V side when nothing is
  plugged in, so U1 drives random levels onto the SDM JTAG pins and UART RX noise can stop U-Boot's autoboot.
- **A2-05:** R65 pulls the Group-2B enable net (3V3/1V1/1V2 regulators' EN, driven by U18's open-drain PG) up to 5V0;
  the AP61202/AP61203 datasheet does not say PG is held low below its own POR, so on a slow 5V0 ramp 2B could start
  before VCORE/1V8. Proposed fix: R65 to 1V8.
- **A2-06:** VCORE (U15 TPS548A28) uses remote sense via VCCLSENSE/GNDSENSE (balls BN46/BN44); if a sense ball opens,
  feedback reads 0 V and U15 drives VCORE up without its OVP tripping. Proposed fix: 10 Ohm from local VCORE to
  `vcoresense_P` and from GND to `vcoresense_N`.
- **A2-07:** with the AP61202's +-2 % reference and 1 % divider resistors, worst-case DC accuracy does not guarantee the
  Agilex windows (1V8 1.741-1.861 V, 1V1 1.068-1.132 V, 3V3 3.196-3.437 V), and PFM ripple lands on the unfiltered PLL
  rail. U16/U18 have since become AP61203 (forced PWM). Verify what remains: the accuracy part, per rail, against the
  actual Agilex (813918) and LPDDR4/other-load tolerances, and whether 0.1 % divider resistors (or another fix) are
  needed.
