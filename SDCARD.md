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
| `1V8` | U11 pin 15 (VCCA), host side |
| `3V3` | U11 pin 14 (VCCB), card side, and J8 pin 4 (card VDD) |
| `GND` | U11 pin 7, J8 pin 6 and shield |

Pin 6 (CLKFB) is unconnected. The datasheet permits this; connecting it to
the clock improves read timing at higher rates.

No external pull-ups are fitted, and none are needed: the NXS0506GU has
integrated 70 kOhm (42-100 kOhm) pull-ups to VCCA on every host-side pin
except CLKA.

## Open items before fabrication

- [ ] **Decoupling on U11 is absent.** Nothing within 6 mm of the part. Add
      100 nF + 4.7 uF at VCCA (pin 15) and at VCCB (pin 14). The 4.7 uF
      figure comes from the Nexperia application circuit.
- [ ] **No capacitance at J8.** Nothing within 8 mm; the card's VDD pin has
      no local decoupling. Add 10 uF + 100 nF at J8 pin 4. SD cards draw
      large current transients, particularly during initialisation.
- [ ] **No card detect.** J8's pin 2 is DAT3/CD and passes through the
      translator as an ordinary data line. This connector variant has no
      detect switch contact. Either detect in software from DAT3, or change
      to a connector variant with the switch.
- [ ] **SD traces need rerouting.** U11 was changed from a TXS0206A
      (DSBGA-20) to the NXS0506GUX (XQFN16). The footprint is much smaller,
      so the existing traces no longer reach the pads. They were left in
      place deliberately rather than deleted.

## Speed limitation as currently built

The card-side signalling rail (U11 VCCB) is tied permanently to 3.3 V, so
the interface is limited to default speed and high speed, roughly 50 MHz.
UHS-I modes (SDR50, DDR50, SDR104) require the bus to switch to 1.8 V
signalling after the card accepts the request, which fixed 3.3 V cannot do.

## Adding UHS-I support

The NXS0506GU itself supports UHS-I; the missing pieces are on the board.
Nexperia AN90037 covers this use of the part.

### Sequence

1. Host sets S18R in ACMD41; card responds S18A.
2. Host issues CMD11.
3. Card drives CMD and DAT[3:0] low.
4. Host stops SDCLK, switches the signalling rail 3.3 V -> 1.8 V.
5. After at least 5 ms, host restarts the clock at 1.8 V.
6. Card releases the lines within 1 ms. If it does not, the host must
   power-cycle the card and fall back to 3.3 V.

Only the signalling rail changes. Card VDD stays at 3.3 V throughout.

### Required changes

Split the two present uses of `3V3`:

| Net | Feeds | Behaviour |
|-----|-------|-----------|
| `3V3` (via load switch) | J8 pin 4, card VDD | fixed 3.3 V, gateable on/off |
| `VDD_SD_IO` (new) | U11 pin 14, VCCB only | switched 3.3 V / 1.8 V |
| `1V8` | U11 pin 15, VCCA | unchanged |

Both `3V3` and `1V8` already exist on the board, so no additional regulator
is needed. The signalling rail can be a 2:1 supply mux between them.

Two control signals are needed. Six HPS GPIOs are free, all on IOB / GPIO1,
the same 1.8 V bank as the SD signals: GPIO1_IO16 (F75), IO17 (AD71),
IO18 (K71), IO19 (AK71), IO20 (F74), IO21 (AA71).

| Signal | Controls | Linux binding |
|--------|----------|---------------|
| rail select | `VDD_SD_IO` 3.3 V / 1.8 V | `vqmmc-supply` |
| card power | J8 pin 4 on/off | `vmmc-supply` |

Card power gating is not optional. It is the specification's mandated
recovery path when a card fails to release the bus after CMD11, and it
appears in the NXP reference circuit (AN13031, figure 1).

### Parts

| Part | Function | Package | KiCad footprint |
|------|----------|---------|-----------------|
| TI TPS2116DRLR | 2:1 mux, `3V3` / `1V8` -> `VDD_SD_IO` | SOT-583 | `Package_TO_SOT_SMD:SOT-583-8` |
| TI TPS22918 | load switch on card VDD | SOT-23-6 | `Package_TO_SOT_SMD:SOT-23-6` |

**TPS2116.** Input range 1.6-5.5 V, covering both rails. Pull MODE high for
manual mode; PR1 then selects the input, high = VIN1, low = VIN2. PR1
switches around VREF (0.92-1.08 V), so an 1.8 V GPIO has ample margin.
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
  pull both control lines to the safe state: card powered, 3.3 V signalling.
  The part also requires VCCB >= VCCA, which an undefined VCCB would violate
  while VCCA is at 1.8 V.
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
