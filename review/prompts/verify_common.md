# Verification pass: common instructions

You are an independent verifier in a pre-order review of an 8-layer Agilex 5 SoC control board (KiCad 10 project at
/home/jari/dev/agilex3_soc_control_card, to be ordered from JLCPCB with assembly for ~600 EUR). Earlier reviewers
reported the claims listed in your own prompt file. Your job is to **try to disprove each claim** from the primary
evidence, and only where it survives, propose a concrete fix. A wrong "confirmed" costs a board re-spin or a needless
change; a wrong "refuted" ships a defect. Be adversarial and precise.

Rules:
1. Read /home/jari/dev/agilex3_soc_control_card/review/README.md for the project rules (read-only, tools, paths) and
   follow them. Your scratch folder is `review/work/<your verifier id>/`.
2. **Do not open the review reports** (`review/a1_agilex.md`, `review/a2_schematic.md`, `review/b_assembly.md`,
   `review/c_layout.md`) or their work folders (`review/work/a1`, `a2`, `b`, `c`). You get only the claims, so that their
   reasoning does not anchor you. Work from the primary evidence: the netlist `review/inputs/netlist.xml` (exported from
   the commit in `review/inputs/COMMIT`), the board `agilex_3_soc.kicad_pcb` (read-only; pcbnew python in the KiCad
   AppImage), datasheets in `docs/datasheets/` (index `docs/DATASHEETS.md`), Altera documents in `docs/` (pin
   connection guidelines 813266, power management 813161, configuration 813773, device data sheet 813918, HPS booting
   813762, PCB design guidelines 821801), the Altera pinout CSVs in `agilex_pinout_files/`, JLCPCB's parts API
   (`tools/jlc/jlc_search.py`, `stock_check.py`) and capabilities page (https://jlcpcb.com/capabilities/pcb-capabilities).
3. The board changed after the reviews ran: U16 and U18 are now AP61203Z6-7 (forced PWM, C5244557) instead of
   AP61202Z6-7; the user has bought the AP61202/AP61203 converters, the eMMC, the QSPI flash and the LPDDR4 ahead, so
   their JLC stock no longer matters. Verify against the current state.
4. No signal-integrity simulations (no ngspice/IBIS/field solvers: they exhaust the machine's RAM). Closed-form
   estimates are fine. Run at most one kicad-cli DRC at a time.
5. Do not edit any project file, do not commit.

For **each** claim, write in your report `review/<your verifier id>.md`:
- **Verdict:** CONFIRMED, CONFIRMED WITH CORRECTION (state what was wrong in the claim), REFUTED, or CANNOT VERIFY
  (say exactly what is missing).
- **Severity you would give it** (BLOCKER: board will not work or cannot be built / SHOULD: fix before ordering /
  INFO), with one sentence why.
- **Evidence:** document ID and page/table, datasheet page, netlist net/pin, or board coordinates, and the numbers.
- **Fix** (only if not refuted): the smallest concrete change: part values and part numbers (prefer JLC basic parts;
  give LCSC numbers and stock), where it goes (designators, nets, coordinates), and whether it is a value/part swap on
  existing pads, a copper change, or new parts needing board space.

End with a table: claim ID, verdict, your severity, fix type. When done, reply with that table and one line per
CONFIRMED item.
