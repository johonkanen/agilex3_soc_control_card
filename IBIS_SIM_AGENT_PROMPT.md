# Agent prompt: LPDDR4 IBIS simulation (40 vs 50 Ω)

Prompt for an agent that runs the IBIS simulation planned in `NEXT_STEPS.md` ("Open decision: 50 Ω LPDDR4 data
routing"). Written 2026-10-27. Before starting: if the SK hynix IBIS model has been obtained from an FAE, put it in
`sim/lpddr4_si/models/` and say so in the prompt.

```text
You are doing a signal-integrity (IBIS) simulation for the LPDDR4 interface of a KiCad board, to decide whether the
LPDDR4 data bytes can be routed at 50 ohm (thinner traces) instead of 40 ohm. Work in the repo
/home/jari/dev/agilex3_soc_control_card (KiCad 10). Read NEXT_STEPS.md, section "Open decision: 50 Ω LPDDR4 data
routing", first: it holds the plan this task follows. Background is in LPDDR4_SWIZZLE_PLAN.md (impedance, skew,
package delays, layer rules) and LPDDR4_SWIZZLE_RULES.md.

SYSTEM
- FPGA: Altera Agilex 5 A5EB013B, package B23B (U7). Memory: SK hynix H9HCNNN8KUMLHR-NME LPDDR4, x32, 2 channels,
  1 rank (U12). 1600 MT/s (800 MHz clock, UI 625 ps), point to point. CA/CKE/CS/CK go as a T to both channels.
- Stack-up JLC08161H-3313, 8 layers, 1.6 mm. Field-solved: In2/In5 stripline 0.18 mm = 39.8 ohm, 7.02 ps/mm;
  0.12 mm about 50 ohm. F.Cu/B.Cu microstrip with mask 0.20 mm = 44.3 ohm, 6.16 ps/mm; 0.15 mm about 51 ohm.
  Inside the BGA courtyards traces neck down to 0.10 mm for about 1-2 mm.
- Current EMIF settings (Quartus test project ~/dev/agilex5_emif_test, build varA_bswap): FPGA output 40 ohm
  (calibrated; 34 or 40 are the only options), FPGA DQ input termination 50 ohm, memory drive 40 ohm (MR3 PDDS 6),
  memory DQ ODT 48 ohm, memory CA ODT 80 ohm. Build varA_ron48 is the same but with memory drive 48 ohm (PDDS 5).
- Routed lengths: the CA trunks are on the board now (die->ball 237-388 ps; read lengths from the board with
  tools/lpddr4_krt/paths.py, or KiCad's net delay). The data bytes are not routed yet: assume 16-22 mm per DQ, mostly
  In2/In5, with a via-in-pad at each end. CA T-branches are about 1.8-2.5 mm on B.Cu, CK branches 2.0 mm on In2.

TOOLS
- KiCad 10.0.7 AppImage at ~/kicad/kicad-10.0.7-x86_64.AppImage (extract it with --appimage-extract into a scratch
  folder if it isn't already; then use squashfs-root/AppRun kicad-cli / python3.11). KiCad's schematic editor
  supports IBIS driver/receiver models (Simulation_SPICE library: IBIS driver, IBIS receiver, TLINE) and runs them
  with ngspice. FIRST verify that you can run this headless (kicad-cli or a SPICE netlist plus standalone ngspice).
  If the IBIS-to-SPICE conversion only happens in the GUI, find a working path, or stop and report what is possible.
- Quartus Pro 26.1.1 at /home/jari/altera_pro/26.1.1. Generate the Agilex 5 IBIS file for the real I/O
  configuration from the varA_ron48 (and varA_bswap) project: board-level / signal-integrity output, IBIS. Do not
  change the board or the Quartus build scripts for this. Build in a copy if you need to rerun anything.

MODELS
- Agilex 5: from Quartus as above. Use the LVSTL 1.1 V buffers with the OCT settings listed.
- SK hynix H9HCNNN8KUMLHR: probably not public. Search for it. If you can't get it, use a public LPDDR4 IBIS model
  from another vendor (e.g. Micron LPDDR4) as a stand-in, and say so clearly in the results.
- Check that every model loads and simulates. Some vendor IBIS files with zero-valued table entries make ngspice
  converge to 0. Fix or work around that, and report it.

CASES (run each with 40 ohm and with 50 ohm lines)
1. DQ write: FPGA driver 40 ohm -> package -> via -> 0.10 mm neck-down -> 20 mm line (also 16 and 22 mm) -> via ->
   memory package -> memory DQ ODT 48 ohm.
2. DQ read: memory driver 40 ohm (baseline) and 48 ohm -> same channel -> FPGA 50 ohm termination.
3. CA through the T: FPGA 40 ohm -> trunk (use a real CA trunk length from the board) -> T-via -> two equal
   branches -> two memory CA inputs with CA ODT 80 ohm; also try 60 ohm.
4. Optional: CK as a differential pair through its T.
Model the vias as small L/C (state the values), and take the package parasitics from the IBIS [Package] data.

MEASUREMENTS
- Stimulus: PRBS (e.g. PRBS7) at 1600 MT/s, plus a worst-case pattern if you can. Overlay the bits into an eye at
  the receiver die/pad.
- Report eye height and eye width against the LPDDR4 Rx mask (VdIVW/TdIVW for DQ, and the CA equivalent, from
  JEDEC JESD209-4 or the memory datasheet; state which numbers you used and where they came from). Also report
  overshoot/undershoot and ringing against the absolute max ratings.
- Give a table: case x line impedance x setting -> eye height, eye width, mask margin. Then a recommendation:
  is 50 ohm with memory drive 48 ohm close enough to 40 ohm in margin to switch the data bytes?

DELIVERABLES
- A small KiCad simulation project in sim/lpddr4_si/ (schematic, any scripts, and a README with how to rerun it),
  the results table, and eye plots as PNG.
- A short results section appended to NEXT_STEPS.md under the 50 Ω decision.

RULES
- The GitHub repo is PUBLIC. Do not commit vendor IBIS files or other vendor documents (Altera, SK hynix, Micron
  models are copyrighted). Keep them in a git-ignored folder (e.g. sim/lpddr4_si/models/, add it to .gitignore) and
  write in the README where each one comes from.
- Do not edit agilex_3_soc.kicad_pcb, the schematic, or the .kicad_pro/.kicad_dru. Never save a pcbnew board into
  the repo.
- Do not commit or push. Leave everything as uncommitted changes and list them at the end.
- If a step is impossible (no headless IBIS path, no usable memory model), stop at that point and report what you
  found, rather than guessing numbers.
```
