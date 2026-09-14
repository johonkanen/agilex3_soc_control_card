# microSD interface

Documents the microSD card interface: what is currently built, what is
missing, and what would be required to run UHS-I speeds.

## Why a level translator is needed

The Agilex 5 HPS SD/MMC I/O only supports 1.8 V signalling. An SD card must
be powered and must communicate at 3.3 V signalling at insertion, regardless
of what speed mode it later negotiates. A translator between the two domains
is therefore mandatory, not optional.

## As built

| Part | Function |
|------|----------|
| U11  | Nexperia NXS0506GUX, SD 3.0 level translator, XQFN16 (SOT1161-1) |
| J8   | microSD socket, Wuerth 693072010801 |
| U40  | TI TPS2116DRLR, 2:1 supply mux, `3V3` / `1V8` -> `VDD_SD_IO` (U11 VCCB) |
| U41  | TI TPS22918DBVR, load switch, `3V3` -> `VDD_SD_CARD` (J8 pin 4) |
| R241 | 100k, `sd_vsel` pull-up to `1V8` (default: 3.3 V signalling) |
| R242 | 100k, U40 MODE pull-up to `1V8` (manual mode) |
| R243 | 100k, `sd_pwr_en` pull-up to `1V8` (default: card powered) |
| C240, C241 | 1u at U40 VIN1 / VIN2 |
| C242, C243 | 4u7 + 100n on `VDD_SD_IO` at U11 pin 14 |
| C244, C245 | 4u7 + 100n on `1V8` at U11 pin 15 |
| C246 | 10u at U41 VIN |
| C247, C248 | 10u + 100n on `VDD_SD_CARD` at J8 pin 4 |

The decoupling capacitors are drawn as a row on the schematic; on the PCB
they belong at the pins named above.

Signal path, verified pin by pin:

| Function | HPS (U7) | U11 host side | U11 card side | J8 |
|----------|----------|---------------|---------------|-----|
| CLK  | AC74 | 5  CLKA  | 8  CLKB  | 5 |
| CMD  | AK69 | 16 CMDA  | 13 CMDB  | 3 |
| DAT0 | AF75 | 3  DAT0A | 10 DAT0B | 7 |
| DAT1 | AC75 | 4  DAT1A | 9  DAT1B | 8 |
| DAT2 | AN64 | 1  DAT2A | 12 DAT2B | 1 |
| DAT3 | Y74  | 2  DAT3A | 11 DAT3B | 2 |

Supplies:

| Net | Feeds |
|-----|-------|
| `1V8` | U11 pin 15 (VCCA), host side; U40 VIN2 |
| `3V3` | U40 VIN1, U41 VIN |
| `VDD_SD_IO` | U11 pin 14 (VCCB), card-side signalling rail, 3.3 V or 1.8 V |
| `VDD_SD_CARD` | J8 pin 4 (card VDD), switched 3.3 V |
| `GND` | U11 pin 7, J8 pin 6 and shield, U40, U41, decoupling |

Control, both on HPS GPIO1 (IOB, 1.8 V bank):

| Signal | HPS pin | Drives | Idle (HPS in reset) |
|--------|---------|--------|---------------------|
| `sd_vsel` | F75, GPIO1_IO16 | U40 PR1: high = 3.3 V, low = 1.8 V | pulled high, 3.3 V |
| `sd_pwr_en` | AD71, GPIO1_IO17 | U41 ON: high = card powered | pulled high, on |

U40 ST (open-drain status) and U41 CT (slew) are left unconnected; U41 QOD
is tied to VOUT so the internal ~25 ohm discharge empties the card rail
when `sd_pwr_en` goes low.

Pin 6 (CLKFB) is tied to `sd_clk` together with CLKA, as the datasheet
recommends for higher clock rates.

No external pull-ups are fitted, and none are needed: the NXS0506GU has
integrated 70 kOhm (42-100 kOhm) pull-ups to VCCA on every host-side pin
except CLKA.

## Open items before fabrication

- [x] Decoupling on U11 (C242-C245) and at J8 (C247, C248) is in the
      schematic. Place them at the pins when the area is rerouted.
- [ ] **Update PCB from schematic.** U40, U41, R241-R243 and C240-C248
      exist only in the schematic until Tools -> Update PCB from Schematic
      is run, then need placing near U11 / J8.
- [ ] **No card detect.** J8's pin 2 is DAT3/CD and passes through the
      translator as an ordinary data line. This connector variant has no
      detect switch contact. Either detect in software from DAT3, or change
      to a connector variant with the switch.
- [ ] **SD traces need rerouting.** U11 was changed from a TXS0206A
      (DSBGA-20) to the NXS0506GUX (XQFN16). The footprint is much smaller,
      so the existing traces no longer reach the pads. They were left in
      place deliberately rather than deleted.

## UHS-I support

Without the rail switching below, the card-side signalling rail would sit at
a fixed 3.3 V and the interface would be limited to default speed and high
speed, roughly 50 MHz. UHS-I modes (SDR50, DDR50, SDR104) require the bus
to switch to 1.8 V signalling after the card accepts the request. The
NXS0506GU itself supports UHS-I; Nexperia AN90037 covers this use of the
part. The circuit described in this section is what is now drawn in
`hps.kicad_sch`.

### Sequence

1. Host sets S18R in ACMD41; card responds S18A.
2. Host issues CMD11.
3. Card drives CMD and DAT[3:0] low.
4. Host stops SDCLK, switches the signalling rail 3.3 V -> 1.8 V.
5. After at least 5 ms, host restarts the clock at 1.8 V.
6. Card releases the lines within 1 ms. If it does not, the host must
   power-cycle the card and fall back to 3.3 V.

Only the signalling rail changes. Card VDD stays at 3.3 V throughout.

### Rails

The two former uses of `3V3` are split:

| Net | Feeds | Behaviour |
|-----|-------|-----------|
| `3V3` (via load switch) | J8 pin 4, card VDD | fixed 3.3 V, gateable on/off |
| `VDD_SD_IO` (new) | U11 pin 14, VCCB only | switched 3.3 V / 1.8 V |
| `1V8` | U11 pin 15, VCCA | unchanged |

Both `3V3` and `1V8` already exist on the board, so no additional regulator
is needed. The signalling rail can be a 2:1 supply mux between them.

Two control signals are used, on the first two of the six free HPS GPIOs
(all on IOB / GPIO1, the same 1.8 V bank as the SD signals; IO18 (K71),
IO19 (AK71), IO20 (F74) and IO21 (AA71) remain free).

| Signal | HPS pin | Controls | Linux binding |
|--------|---------|----------|---------------|
| `sd_vsel` | GPIO1_IO16, F75 | `VDD_SD_IO` 3.3 V / 1.8 V | `vqmmc-supply` (gpio-regulator) |
| `sd_pwr_en` | GPIO1_IO17, AD71 | J8 pin 4 on/off | `vmmc-supply` (regulator-fixed with enable GPIO) |

Card power gating is not optional. It is the specification's mandated
recovery path when a card fails to release the bus after CMD11, and it
appears in the NXP reference circuit (AN13031, figure 1).

### Parts

| Ref | Part | Function | Package | KiCad footprint |
|-----|------|----------|---------|-----------------|
| U40 | TI TPS2116DRLR | 2:1 mux, `3V3` / `1V8` -> `VDD_SD_IO` | SOT-583 | `Package_TO_SOT_SMD:SOT-583-8` |
| U41 | TI TPS22918 | load switch on card VDD | SOT-23-6 | `Package_TO_SOT_SMD:SOT-23-6` |

Symbols `TPS2116DRL` and `TPS22918DBV` are in `agilex_5_lib`. Pin numbers
were taken from the TI pin-function tables (TPS2116: 1 GND, 2/7 VOUT,
3 VIN1, 4 PR1, 5 MODE, 6 VIN2, 8 ST; TPS22918: 1 VIN, 2 GND, 3 ON, 4 CT,
5 QOD, 6 VOUT).

**TPS2116.** Input range 1.6-5.5 V, covering both rails. MODE is pulled
to `1V8` (R242) for manual mode; it must not be tied to VIN1, which selects
priority mode instead. PR1 then selects the input, high = VIN1, low = VIN2.
PR1 switches around VREF (0.92-1.08 V), so an 1.8 V GPIO has ample margin.
Reverse current blocking (when VOUT > VINx, 2 us) and break-before-make are
both internal, which satisfies the first two constraints below with no
external parts.

**TPS22918.** 1-5.5 V, 2 A, ON threshold 1 V minimum and specified for use
with 1 V or higher GPIOs. Quick output discharge is roughly 25 ohm at 3.3 V.
The discharge matters: for a power-cycle recovery to reset the card, its VDD
has to reach near zero rather than float on its own decoupling.

Availability as of September 2026: TPS2116DRLR, 66k at DigiKey and 2.4k at
Mouser, around $0.50. TPS22918 is stocked as TPS22918TDBVTQ1, the Q1
automotive grade, around 5.9k at DigiKey; the plain TPS22918DBVT was not
stocked.

Confirm before ordering:

- The stocked load switch is the `T` variant (TPS22918TDBVTQ1). Check its
  rise time and QOD behaviour against the base TPS22918 datasheet cited here.
- KiCad's `SOT-583-8` footprint carries a description referencing the
  TPS62933, not the TPS2116. It is the same JEDEC package and the land
  pattern measures 2.15 x 1.80 mm at 0.5 mm pitch, but cross-check it
  against TI's TPS2116 land pattern before fabrication.

### Design notes

- **Reverse blocking on the 1.8 V leg.** A plain P-FET or a load switch
  without reverse blocking will conduct through its body diode from the
  output back into `1V8` whenever the rail sits at 3.3 V. Use back-to-back
  FETs or a switch that blocks reverse current. The 3.3 V leg is inherently
  safe because 3.3 V > 1.8 V keeps its body diode reverse biased.
- **Break before make.** `3V3` and `1V8` must never be connected together.
  Handled internally by the TPS2116; only relevant if built from discretes.
- **Default state at reset.** HPS GPIOs are high impedance during reset, so
  both control lines are pulled (R241, R243) to the safe state: card
  powered, 3.3 V signalling. The translator also requires VCCB >= VCCA,
  which an undefined VCCB would violate while VCCA is at 1.8 V. The
  TPS22918 ON pin has no internal pull and must not float.
- **Falling transition.** Switching to the 1.8 V rail discharges the VCCB
  capacitance into `1V8` through the closed switch, roughly 7 uC for 4.7 uF,
  which is negligible against the board's 1.8 V bulk. Note that an LDO with
  a switched feedback divider would *not* behave this way: its output would
  float down at the load current, needing around 1.4 mA of bleed to meet the
  5 ms window. This is a reason to prefer the mux.
- **Signal integrity.** SDR104 clocks at 208 MHz, four times the present
  rate. Length matching, controlled impedance, short stubs and minimal added
  capacitance all become relevant. Worth routing for this when the traces are
  redone.
- **Silicon revision.** Agilex 5 engineering samples are documented as
  failing to boot from SD in SDR104 (and eMMC in HS200/HS400). Production
  devices are unaffected. Confirm the stepping before relying on it.

### Alternative part

NXP NVT4857UK integrates the switchable LDO and a card detect pin, removing
the external mux. It is WLCSP20, 0.4 mm pitch, 1.7 x 2.1 mm.

## eMMC as an alternative

eMMC has a separate I/O supply (VCCQ) that can run at 1.7-1.95 V while the
NAND core (VCC) runs at 3.3 V, so it connects directly to the 1.8 V HPS pins
with no translator, no card detect problem and no voltage switching. The
Agilex 5 HPS SD/MMC controller supports eMMC, and its HS200/HS400 modes
require 1.8 V signalling in any case.

`sd_d4` through `sd_d7` are already named and brought out to U7 (U74, AK67,
P75, P74) but connect to nothing else, so the 8-bit bus an eMMC would need
is partly prepared.

Sourcing is the obstacle. As of September 2026, 8 GB eMMC in single-digit
quantities was not stocked at DigiKey, Mouser or LCSC across parts from
Kingston, Micron, KIOXIA, Swissbit, FORESEE and MK; the low densities are
being discontinued. Franchise distributors (Arrow, Avnet, Future) quote
small quantities against stock that does not appear in the catalogues.

## References

- Nexperia NXS0506 datasheet — https://assets.nexperia.com/documents/data-sheet/NXS0506.pdf
- Nexperia AN90037, NXS0506 SD-card voltage level translator — https://assets.nexperia.com/documents/application-note/AN90037.pdf
- Nexperia SOT1161-1 package / land pattern — https://www.nxp.com/docs/en/package-information/SOT1161-1.pdf
- NXP AN13031, Recommendations for SD Connections to 1.8 V SDHC Interfaces — https://www.nxp.com/docs/en/application-note/AN13031.pdf
- NXP NVT4857UK datasheet — https://www.nxp.com/docs/en/data-sheet/NVT4857UK.pdf
- Altera SD/eMMC controller documentation — https://altera-fpga.github.io/rel-26.1/linux-embedded/drivers/sd-emmc/sd-emmc/
