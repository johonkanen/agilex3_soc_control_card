# Where we left off (2026-10-27)

main = origin/main at `26cd28a` plus two uncommitted doc notes (this file and `LPDDR4_SWIZZLE_PLAN.md`). Board DRC:
289 violations, 260 unconnected, schematic parity 0. Silkscreen checks are ignored: the boards are ordered without silk.

## Done 2026-10-26/27 (pushed)

- eMMC: DS strobe on HPS_IOA_16 (HS400 possible), 0201 decaps on the U11 via-in-pad, 0402 4u7 bulk next to the array.
- HPS: stale SD/Ethernet copper at the U7 HPS balls deleted (rerouting still to do).
- LPDDR4: bytes 0↔1 swapped (`BYTE_SWIZZLE_CH0=1 0 X X X X 3 2`, Quartus-checked); CA and CK T-junctions under U12;
  CA/CKE/CS/RST trunks routed with KiCadRoutingTools (`tools/lpddr4_krt/`); U7 package delays on the pads as
  pad-to-die; tuning profiles and pre-defined widths for 40 Ω inner (0.18 mm) / ~44 Ω outer (0.20 mm, field-solved).
- U7 heatsink: NPTH 3.2 mm push-pin holes H1/H2 with 6 mm keep-outs.

## Open decision: 50 Ω LPDDR4 data routing (thinner traces)

- Quartus accepts 48 Ω memory drive (`MEM_ODT_DQ_X_RON=5`, MR3 PDDS 5): `~/dev/agilex5_emif_test/varA_ron48/`, 0 errors,
  timing identical to `varA_bswap`. With FPGA input termination 50 Ω and memory DQ ODT 48 Ω (both already set), reads
  are matched to a 50 Ω line; FPGA drive stays 40 Ω (34/40 are the only options), a mild source mismatch.
- Idea: route the data bytes and DQS at 50 Ω (0.12 mm inner / 0.15 mm outer); keep CA/CK as routed. Not applied: the
  KiCad tuning profiles and widths are still 40 Ω. Altera's guideline (821801) only allows 50 Ω for break-outs.
- **IBIS simulation before committing to 50 Ω** (or at least a calibration-margin test on the first boards):
  - models: Agilex 5 IBIS (Altera, for the A5EB013B B23B package, LVSTL 1.1 V, 40 Ω output / 50 Ω ODT settings) and the
    SK hynix H9HCNNN8KUMLHR IBIS (from SK hynix or a distributor FAE; it would also give the missing U12 package
    delays);
  - cases: one DQ byte write (FPGA 40 Ω → 50 Ω line → memory ODT 48 Ω) and read (memory 48 Ω → line → FPGA 50 Ω), and the
    CA bus at the T (FPGA 40 Ω → trunk → two branches → memory CA ODT 80 Ω); 1600 MT/s, eye height/width vs LPDDR4
    masks; compare 40 Ω and 50 Ω lines;
  - tool options (to be checked): an IBIS-capable SPICE flow (e.g. ngspice/Qucs-S IBIS support, or an IBIS-to-SPICE
    conversion for LTspice), or a commercial SI tool; also check what Altera provides for Agilex 5 EMIF board SI.

## Continue next time, in order

1. Decide 40 Ω vs 50 Ω for the data bytes (see above); if 50 Ω, switch the LPDDR4 profiles/widths and adopt
   `MEM_ODT_DQ_X_RON=5` in the real Quartus project.
2. Route CK by hand as a coupled pair (U7 G42/J42 → the two In2 T-vias), about 333 ps die→ball, then tune ca2–ca5 up
   (+28/+21/+52/+63 ps) with KiCad's time-domain tuner.
3. Route the data bytes from the U12 side and swizzle DQ within each lane; extend the dqs0 stubs to AB56/W56 and dqs1 to
   G62/E62. Then relabel `iobank3`, sync, regenerate `PIN_SWIZZLE`, re-run Quartus (see `LPDDR4_SWIZZLE_RULES.md`).
4. Route the eMMC (U11 signal vias are in, the traces are not) and the HPS SD/Ethernet/UART/eth_rst_n nets.
5. Power corner (item 1 below): keep L1 ≥ 3 mm from H1's centre (now 0.31 mm inside its keep-out ring).
6. Review the unmerged LPDDR4 escape-agent worktree (`.claude/worktrees/agent-a16b8e0ab24697630`) or drop it.

# Earlier: where we left off (2026-10-24)

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
1b. **Synced 2026-10-25** (schematic parity 0): ADC front end, RTL8211FDI-CG with straps, Y2/R56/R57, L1–L5, and
   the U12 1u caps C262–C265. The layout is NOT cleaned up yet (DRC 223, 196 unconnected).
   - **PHY:** U10 is now QFN-40 5x5 at the old position. Re-place and reroute it: the old KSZ tracks dangle and short.
     Old 1V2 copper is now on PHY1V0/PHY_RG nets (C27–C32, C256–C258); fix it.
   - **New parts, parked right of the board (x ≈ 230+):** R268–R271 (PHY straps/LED), R265–R267 (ADC SPI 33R), C261
     (ADC DVDD), C262–C265 (U12 1u, place under/near the U12 1V1 balls on B.Cu).
   - **ADC:** U4 is now SOT-23-5 and C1 is 0603 (put C1 at U5 AVDD); U5's SPI goes through R265–R267; U3 pin 6 -> GND.
   - **U42 ch3** is now eth_rst_n -> phy_rst_n; the old LED track to J9 must go.
1c. **eMMC replaces the microSD (2026-10-26, PCB synced in cb66bdc):** U11 is now the THGAMVG7T13BAIL (LFBGA-153).
   J8, U40, U41, C240, C241, C247 and C248 are removed. New: R272–R279; R241–R243 and C242–C246 changed value/net.
   The old SD copper is deleted. Place and fan out U11 near the HPS SD/MMC pins (inner balls need via-in-pad), and route
   `emmc_ds` to U7 AP74 (HPS_IOA_16, HS400 strobe). See `SHARED_PARTS.md`.
1d. **HPS pin mux changed (2026-10-26, PCB synced in 1204a4d):** SD/MMC moved to HPS_IOA_1–12 and Ethernet to EMAC2 on
   HPS_IOB_13–24, so they no longer cross. The stale copper at the U7 HPS balls is deleted (all RGMII/MDIO, `eth_rst_n`,
   `hps_uart0_tx/rx` and the old SD routing); route these nets again. DRC now: 261 violations, 312 unconnected, parity 0. See `HPS_PINMUX.md`.
2. **Route all LPDDR4 signals from scratch** (merged from branch `lpddr4-reroute-explore`, 2026-10-25).
   - All LPDDR4 copper is removed. The pinout is "variant R2": U12 moved 6 mm left (still −90°) with its decaps and
     fan-out; byte swizzle BL6↔BL7 with a new pin swizzle (Quartus-checked); refclk chain R25/R26/C8/C9 nudged
     down; zones refilled.
   - 2026-10-26: bytes 0/1 swapped (A0 on BL1, A1 on BL0; Quartus-checked, `BYTE_SWIZZLE_CH0=1 0 X X X X 3 2`). The
     dqs0/dqs1 routes were trimmed at U7's courtyard and must be extended to their new balls. CA and CK T-junctions
     under U12 are in.
   - 2026-10-26: CA trunks (ca0–5, cke, ~{cs}) and ~{rst} routed with KiCadRoutingTools (trial v15: shortest routes, no
     automatic matching) and merged; U7 pads carry the Quartus package delays as pad-to-die. Still to do: CK as a hand-routed
     coupled pair (U7 G42/J42 → the two In2 T-vias), then tune with KiCad's time-domain tuner. With CK at about 333 ps
     die→ball, ca2 needs about +28 ps, ca3 +21, ca4 +52, ca5 +63 (die→ball now: ca0 367, ca1 306, ca2 272, ca3 279,
     ca4 247, ca5 237, cke 303, ~{cs} 388 ps; limits CA−CK ±34, CKE/CS−CK ±85).
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

- **HPS pin mux:** SD/MMC 8-bit on HPS_IOA_1–12, Ethernet on EMAC2 (HPS_IOB_13–24, MDIO2 on IOB_9/10), UART0 on
  IOA_23/24, I2C1 on IOB_7/8. The full table and the `HPS_IO_Enable` string are in `HPS_PINMUX.md`.

- **EMIF:** LPDDR4 1x32, 1 rank, 4 Gb/channel, 1600 MT/s, refclk 100 MHz.
  - Refresh timings: tRFCab 180 ns, tRFCpb 90 ns, tXSR 187.5 ns (the IP default). The H9HCNNN8KUMLHR is "8Gb, DDP, 2Ch 1CS"
    with 4 Gb per channel, so the per-die density is ambiguous; 180/90/187.5 is correct for either case. Do NOT use
    130/60/137.5, which is only valid for 4 Gb dies (2 Gb per channel).
  - Swizzle strings are in `LPDDR4_SWIZZLE_PLAN.md`.
- **Add the Reset Release IP.**
- **Configuration:** AS x4 normal mode; SDM_IO0 = INIT_DONE, SDM_IO16 = CONF_DONE, SDM_IO10 = HPS_COLD_nRESET,
  SDM_IO15 = AS_nRST.
- **J3 HVIO outputs:** leave the weak pull-ups off and use Quartus ≥ 25.1.1.
