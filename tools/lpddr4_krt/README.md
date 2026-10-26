# LPDDR4 CA trunks with KiCadRoutingTools

Routes the CA/CKE/CS (and RST) trunks from U7 to the T-vias under U12, after the
method of `~/dev/efinix_soc_board/tools/ddr/ca_tb_chain.sh`. Trial and results:
`NEXT_STEPS.md` item 2 (2026-10-26). Main holds variant v15: shortest routes, no
automatic matching, CK left for hand routing.

Setup: `export KICAD_APPRUN=<KiCad AppImage>/AppRun`; KRT checkout in
`~/dev/KiCadRoutingTools` with its `.venv` (or set `KRT`).

```
W=/some/workdir; mkdir -p $W; cp agilex_3_soc.kicad_pcb $W/in.kicad_pcb
$KICAD_APPRUN python3.11 tools/lpddr4_krt/prep.py $W/in.kicad_pcb $W/prep.kicad_pcb   # + $W/prep.json
tools/lpddr4_krt/run.sh $W v15                     # route (env LC, MATCH, NOCK; extra route.py args)
tools/lpddr4_krt/grade.sh $W v15                   # finish -> out.kicad_pcb, DRC, delays
$KICAD_APPRUN python3.11 tools/lpddr4_krt/merge.py $W/in.kicad_pcb $W/v15/out.kicad_pcb agilex_3_soc.kicad_pcb
```

- `prep.py`: U7 pad-to-die from the Quartus `.pin` (`~/dev/agilex5_emif_test/varA_bswap`); each shared CA/CK net's
  T-via becomes a temporary THT pad `TP_<net>` whose pad-to-die is the branch delay (T → U12 ball); branches go to
  `BR_<net>`, U12 pads to `TMP_<net>`, so the router can only end at the T point.
- `finish.py`: undoes that (T-vias back, branch ends snapped onto T), clamps F/B to 0.20 mm, refills zones.
- `merge.py`: the routed board minus the KRT CK copper (keeps the original CK branches).
- `report.py` / `paths.py`: KiCad's own delay per net (probe-rule trick) and a die → ball path trace.

Findings: connectivity is reliable (11/11 in ~35 s, needs F.Cu allowed for the pad escapes); time matching is not:
the far-side nets detour 30–40 mm, KRT finds no straight runs for the meanders the short nets need, and its F.Cu
delay is about 15 % low (no solder mask in its microstrip model). Results vary between runs.
