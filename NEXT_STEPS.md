# Where we left off (2026-10-24)

The schematic is up to date, and the PCB was synced from it (schematic parity 0, commit "PCB: sync with schematic").
The layout has **not** been cleaned up after that sync yet. DRC shows 576 violations and 64 unconnected items; before
the sync it was 496 and 48.

## Done in this session (all pushed)

- **LPDDR4:**
  - DQS labels fixed: each strobe is now in its own byte lane.
  - U12 is the SK hynix H9HCNNN8KUMLHR-NME and U2 the IS25WP128-RHLE.
  - Quartus confirmed the current pinout, and the planned BL6↔BL7 byte swap is also legal. See `LPDDR4_SWIZZLE_PLAN.md`.
  - Tag `pre-lpddr4-swizzle-reroute` marks the routing before any swizzle rework.
- **J3 (baseboard connector):**
  - A bottom-side 2x19 socket, numbered like the baseboard J11 (J3 pin n = J11 pin n). MDATA_ISO is on J3.6.
  - RN1–RN7 10k pull-downs on the 28 outputs (routed).
  - Mount the socket under a face-up card, like the Ti60 card.
- **Altera power/configuration review** (`AGILEX_POWER_CONFIG_CHECKLIST.md`):
  - VCCIO_HVIO_6A on 3V3; CE19 unused;
  - Y4 100 MHz -> `clk100` -> AE11 is the fabric clock;
  - MSEL = 011 (AS normal);
  - R264 pull-up on HPS_COLD_nRESET; R9/R10 DNP.
- **Power:**
  - U9 is now the LVDS AX3DAF1 (the HCSL part had no 50R to GND).
  - AP61202 dividers use 200k top; L2–L5 are 1 µH Cenker (as on the Agilex 3 card).
  - VCORE: R58 PGOOD pull-up moved to the TDA38812 VCC (PGOOD abs max 4 V); L1 is a Tai-Tech TMPC0503H 220 nH, 21 A.
- **PCB:** fiducials FID1–6 added, J3 edge-clearance warnings excluded.
- **Quartus test project:** `~/dev/agilex5_emif_test` (outside this repo).
  - EMIF variants A and B, 100 MHz refclk at 1600 MT/s, per-rail power.
  - Rebuild with `scripts/build.sh A|B`, with `REFCLK=`/`TAG=` overrides.

## Next steps, in order

1. **Clean up the PCB after the sync** (KiCad GUI):
   - **Power-supply corner on B.Cu:** the new L1 (5.7x5.2 mm) and L2–L5 (2016) pads short to `pg_all` / `Net-(U16-EN)`
     tracks and vias. They also overlap U8, U16, U18, U19, C159, C164, C165, C169, C170, C172 and C203. Re-place and
     reroute.
   - **U7 CL29/CT29:** the old 1V8 vias must go to 3V3.
   - **U7 CE19:** delete the leftover `sdm_clk25` via/track (CE19 is now unconnected).
   - **R45 pad 2:** the GND track must go to 1V8 (MSEL1 pull-up).
   - **R58 pad 1:** remove the 5V0 track; it connects to `tda_vcc` (U15 pin 19 / C201). It also sits in the
     `5v0_flood` zone.
   - **Place the new parts** (they are parked right of the board edge, x ≈ 215–221 mm):
     - Y4 + C260 + R263 near AE11 (bank 6G, fabric refclk);
     - R264 near the SDM pull-ups (HPS_COLD_nRESET).
   - Refill zones, then re-run DRC with schematic parity.
1b. **ADC front end** (commit 66ab8f1, schematic only): update the PCB from the schematic again for:
   - U3 (SN74LV4051A, same footprint) and U4 (OPA365, TSOT-23-5 -> SOT-23-5 footprint);
   - C1 (now 0603);
   - new parts R265–R267 (33R on the ADC SPI lines) and C261 (DVDD 1u);
   - U3 pin 6 -> GND, U5 DVDD -> 3V3.
   Place C1 4u7 right at U5 AVDD and C261 at DVDD.
1c. **Ethernet PHY RTL8211FDI-CG** (replaces the KSZ9031, schematic only): update the PCB for:
   - U10 (QFN-40 5x5 instead of QFN-48 7x7) and the new R268;
   - the DNP straps;
   - the PHY1V0/PHY_RG rails;
   - U42 ch3 -> phy_rst_n.
   Re-place and reroute the PHY area; the RGMII series resistors stay. See `ETH_PHY_REVIEW.md`.
2. **Route all LPDDR4 signals from scratch** (merged from branch `lpddr4-reroute-explore`, 2026-10-25).
   - All LPDDR4 copper is removed. The pinout is "variant R2": U12 moved 6 mm left (still −90°) with its decaps and
     fan-out; byte swizzle BL6↔BL7 with a new pin swizzle (Quartus-checked); refclk chain R25/R26/C8/C9 nudged
     down; zones refilled.
   - Follow the "Reroute plan" in `LPDDR4_SWIZZLE_PLAN.md`. Route each DQS on its own byte's layers; no P/N polarity
     swap is allowed.
3. **Recommended, not fitted yet:** ferrite + 4.7µ‖100n isolation filters on VCCPLL1/2_HPS, VCCADC and VCCPLL_SDM
   (1V8), and on VCCPLLDIG1/2_HPS and VCCPLLDIG_SDM (VCORE). There is a note on the `fpga_power` sheet and on the PCB
   Cmts.User layer.
4. **Remaining review items:**
   - C1, C2 and C4 have no value (and no LCSC number);
   - the Y3 crystal load caps (C251/C252 27p) vs the crystal;
   - Y2 SiT8924BA-73 is not stocked at JLC (alternative SiT8924BA-78-18E, C17247134);
   - J9 RJ45 is not stocked at JLC;
   - R25/R42/R51 use C_0402 footprints;
   - VCCPT 1V8 also feeds the board's 1.8 V loads (noted as a caution in the checklist).
5. **Later:** the eMMC instead of microSD (`SHARED_PARTS.md`), the schematic reorganisation (`SCHEMATIC_REORG_PLAN.md`),
   then the JLCPCB DFM check (via hole-to-track 0.2 mm question; order epoxy-filled and capped vias).

## For the FPGA/Quartus project later

- **EMIF:** LPDDR4 1x32, 1 rank, 4 Gb/channel, 1600 MT/s, refclk 100 MHz.
  - Set tRFCab 130 ns, tRFCpb 60 ns and tXSR 137.5 ns via the IP's JEDEC override table.
  - Swizzle strings are in `LPDDR4_SWIZZLE_PLAN.md`.
- **Add the Reset Release IP.**
- **Configuration:** AS x4 normal mode; SDM_IO0 = INIT_DONE, SDM_IO16 = CONF_DONE, SDM_IO10 = HPS_COLD_nRESET,
  SDM_IO15 = AS_nRST.
- **J3 HVIO outputs:** leave the weak pull-ups off and use Quartus ≥ 25.1.1.
