# Pre-order review

Independent review streams run by separate agents against one frozen board state, before the ~600 EUR JLCPCB order.
Each stream writes one report here (`review/<stream>.md`); findings are verified separately before anything is fixed.

## Frozen state

- Commit: `review/inputs/COMMIT` (the netlist and tables in `review/inputs/` were exported from it).
- `review/inputs/netlist.xml`, `netlist.net`: schematic netlist (KiCad XML / s-expression).
- `review/inputs/u7_balls.csv`: every U7 ball in the netlist with its net, symbol pin function, pin type, the other
  parts on the net, and the Altera pin-list columns (bank, pin name, optional, configuration and HPS functions).
- `review/inputs/u7_balls_not_in_netlist.csv`: Altera balls the U7 symbol does not have (20 DNU, 10 NC).
- Sources and tools: `docs/REVIEW_SOURCES.md`; datasheets `docs/DATASHEETS.md` / `docs/datasheets/`; Altera documents
  `docs/README.md`; pinout CSVs in `agilex_pinout_files/`.

## Rules for every stream

1. **Read-only.** Never edit or save `agilex_3_soc.kicad_pcb`, `.kicad_sch` files, `.kicad_pro`, `.kicad_dru`, or
   anything outside `review/`. Never commit or push. For KiCad CLI runs or Quartus builds, work on copies under
   `review/work/<stream>/` (git-ignored). Never save a board through `pcbnew.SaveBoard` except into your work folder.
2. **One report**, `review/<stream>.md`, in this format:
   - a short summary (counts per severity, what was and was not covered);
   - findings, most severe first, each with: an ID (`<stream>-NN`), **severity** (BLOCKER: the board will not work or
     cannot be built / SHOULD: fix before ordering / INFO), the exact reference (designator.pin, ball, net, coordinates),
     the **evidence** (document ID and page/table, or the netlist/board line), and whether it is **verified** (checked
     against the source) or an **assumption**;
   - a coverage list: what was checked and found correct, so a clean result is distinguishable from an unchecked one.
3. **The netlist and the copper are the truth.** Treat existing repo documents (`*_CHECKLIST.md`, `ETH_PHY_REVIEW.md`,
   `HPS_PINMUX.md`, `NEXT_STEPS.md`, ...) as claims to verify, not as facts.
4. **Stay in your lane.** Something that belongs to another stream gets one line under "For other streams" and no more.
5. When a source cannot be read or a check cannot be done, say so in the report instead of guessing.

## Tools

- KiCad 10 (unpacked AppImage): `K=<squashfs-root>/AppRun` (the first run used one unpacked in a session scratch folder;
  unpack a KiCad 10 AppImage with `--appimage-extract` if it is gone);
  `$K kicad-cli ...`, `$K python3.11` (has `pcbnew`). Headless ERC / DRC parity needs
  `KICAD10_SYMBOL_DIR="/mnt/c/Program Files/KiCad/10.0/share/kicad/symbols"`. Copy the whole project
  (`agilex_3_soc.*`, `*.kicad_sch`, `a5e_kicad/`, `agilex_5_lib/`, `agilex_lib.pretty/`, `agilex_lib.3dshapes/`,
  `sym-lib-table`, `fp-lib-table`) into your work folder and delete any `*.lck` there before running it.
- Quartus Prime Pro 26.3: `~/altera_pro/26.3`; the EMIF test project `~/dev/agilex5_emif_test` (copy it into your work
  folder, do not modify the original).
- `pdftotext` / `pdfinfo`; xlsx via `tools/datasheets/xlsx2csv.py`.

## Streams

| Stream | Scope | Report |
|---|---|---|
| A1 | Agilex 5 U7: every ball, configuration, HPS pin mux, full-pin Quartus fit | `a1_agilex.md` |
| A2 | Rest of the schematic: power tree, every other IC, connectors | `a2_schematic.md` |
| B | Footprints, BOM, assembly | `b_assembly.md` |
| C | Fabrication, layout, SI | `c_layout.md` |

## Status and how to rerun (2026-11-01)

First run on commit `0aa9192`; reports committed here: `a1_agilex.md` (0 BLOCKER / 2 SHOULD / 11 INFO),
`a2_schematic.md` (0 / 7 / 11), `b_assembly.md` (1 / 7 / 11), `c_layout.md` (0 / 6 / 13). Since then U16/U18 became
AP61203 (A2-07, part) and the converters, eMMC, flash and LPDDR4 were bought ahead. The verification pass
(`v1_power.md`, `v2_assembly.md`, `v3_layout.md`) is done; the confirmed fixes are tracked as a checklist in
**`FIXES.md`**.

To rerun a stream on a later commit:
1. commit, then `K=<squashfs-root>/AppRun python3 -I review/make_inputs.py` (rewrites `review/inputs/`);
2. start one agent per stream (Opus) with the prompt in `review/prompts/<stream>.md`, all in parallel; stream C must not
   run SI simulations (RAM and time);
3. each writes `review/<stream>.md`; earlier reports are in git history.
