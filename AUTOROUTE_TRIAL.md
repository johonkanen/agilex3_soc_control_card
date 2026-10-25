# LPDDR4 autoroute trial: KiCadRoutingTools

**Verdict: not a usable start for manual cleanup.** The router connects almost everything, but the copper it lays is the
wrong shape:
- nets loop around U12;
- bytes are split across layers;
- the length spread is 10–40 mm per byte, and the length matching can't fix it;
- the CK pair is never routed coupled;
- some In5 copper leaves the 1V1 pour.

Routing the interface by hand from the plan in `LPDDR4_SWIZZLE_PLAN.md` will be faster than untangling this.

This branch has two commits:
- `981fc51` is the best result with the old 50 Ω rules (run **c9**).
- The next commit is the best result with the Altera 821801 targets (run **n1**), and this file.

Neither should be merged.

## Tool and setup

- **Tool:** KiCadRoutingTools v0.23.7, commit `b232bac` (2026-10-25), with the prebuilt `grid_router` v0.23.7 for
  Linux x86_64. Cloned into a scratch dir, with a Python 3.10 venv for numpy, scipy, shapely, Pillow and ortools.
- **KiCad 10 files:** read and written without problems. Every result was checked with KiCad 10.0.7: `kicad-cli pcb
  drc --schematic-parity --refill-zones`, plus pcbnew scripts for lengths, layers, spacing, footprint moves and
  non-LPDDR copper.
- **Safety settings** were needed to keep the router to LPDDR4 copper. Without them it changes other things:
  - `KICAD_RECONCILE_RIP_ESCALATION=0`: without it, the run gave itself permission to rip `/HPS/sd_d0` and
    `Net-(U12B-ZQ0)`, and did rip sd_d0.
  - `KICAD_RIP_PREEXISTING=0`, `KICAD_PLANE_FINALIZE=0`, `KICAD_FINALIZE_RIP=0` and `KICAD_RESCUE_CAP_MOVE=0`: by
    default it moves caps and repairs planes.
  - `--keep-input-copper` and `--no-fix-drc-settings`.
  - The previous step's `.kicad_pro` has to be carried forward, because it holds the protected-net record. Without it
    the next step ripped and rerouted the DQS pairs.
- **Result of those settings:** in every committed run, no footprint moved, non-LPDDR copper is unchanged (checked
  segment by segment) and the zones are refilled.

## Tool skills (the repo's `.claude/skills/`)

The repo ships these skills:
- plan-pcb-routing
- review-routed-board
- diagnose-routing-failures
- find-high-speed-nets
- identify-diff-pairs
- analyze-power-nets
- recommend-plane-mappings
- recommend-stackup
- plan-pcb-placement
- stress-test-router
- make-3d-movie

**plan-pcb-routing** was read and followed where it doesn't conflict with our constraints:

| Skill step | What happened here |
|---|---|
| Bus between two arrays: use the experimental topological bus router `awx/route_bus.py` | Tried, failed. It forces F.Cu+B.Cu as routing layers (it can't do F.Cu/In2 alone), and its `joint`/`escape` modes fan out other nets and move passives. In `plain` mode it doesn't detect U7 as a ball array. **U12→U7** refused at the fanout audit ("dqs0 launch from the source's far face") and laid nothing in 413 s. **U7→U12** found 0 nets. |
| `bga_fanout.py` on the BGAs | On U7 it fans nothing: it sees a 0.209 mm "pitch" in the mixed hex grid. On U12, dogbone fans 55/55 balls with 5 grazes, but `route_diff` then couples 0 of 4 DQS pairs on the fanned board. So no fanout was used: `route.py --no-bga-zones` escapes both arrays itself with via-in-pad. |
| Skip the decap optimiser and plane steps | Not applicable: no moves and no planes allowed. |
| DQS pairs first, then `route.py` with `--length-match-group auto` | Auto grouping only grouped 4–13 nets per pass, so explicit per-byte groups were used. |
| Dense board: fab-floor sizes, grid 0.05, the "tuned bundle" env (`KICAD_GLOBAL_PLAN...`) | Grid 0.05 helped (open connections 15 → 10). The tuned env bundle was no better: 3 vs 2 failures. |

Compared with plain CLI use, the skills didn't improve the result:
- the tool the skill prefers for this case (the bus step) doesn't work on this board;
- the useful advice was general: small grid, explicit sizes, check with KiCad's DRC.

## Commands (final chain, per byte)

The DQS pair is routed first, then that byte's DQ/DM with a length group that includes the DQS (measured from the
board). Then CK, then CA/CKE/CS/RST with a group that includes CK.

| Byte | Layers | Layer costs |
|---|---|---|
| B1 | F.Cu+In2 | 4/1 |
| A0 | F.Cu+In2 | 4/1 |
| A1 | F.Cu+In5 | 4/1 |
| B0 | F.Cu+In2 | 1/4 |
| CK/CA | F.Cu+In2+In5 | 4/1/1 |

```
common:   --no-bga-zones --clearance 0.1 --via-size 0.3 --via-drill 0.15 --grid-step 0.05
          --escalation board --keep-input-copper --no-fix-drc-settings
pairs:    route_diff.py --nets "/IOBANK 3/dqsN_*" --layers .. --layer-costs .. --no-gnd-vias --diff-pair-intra-match
          50 ohm:  --track-width 0.12 --diff-pair-gap 0.2
          821801:  --track-width 0.18 --diff-pair-gap 0.1 --length-match-tolerance 0.05
byte:     route.py --nets <8 DQ> dmN dqsN_P dqsN_N --length-match-group <8 DQ> dmN "dqsN_*"
          50 ohm:  --track-width 0.12 --length-match-tolerance 0.25
          821801:  --track-width 0.1 --power-nets "/IOBANK?3/*" --power-nets-widths 0.18 --neckdown-length 3
                   --time-matching --time-match-tolerance 20 --keep-away <byte>:<other groups>:0.3
                   --keep-away-cost 1 --track-proximity-distance 0.25 --track-proximity-cost 0.5
```

The scratch scripts (`chain.sh` / `chain40.sh`, plus the evaluators) are not in the repo.

### Runs tried

These are the 50 Ω runs (LPDDR4 open = KiCad's unconnected count, out of 66):

| Run | What changed | LPDDR4 open |
|---|---|---|
| r1–r3 | one byte only (A0): width/impedance and layer-cost tests | n/a |
| s2 | all bytes in one call | 24–27, and it ripped `/HPS/sd_d0` and the DQS pairs |
| s3 | as s2, with the safety settings | 25–35 |
| c1–c4 | per byte, grid 0.1; c2/c3 routed DQ before DQS | 15–23; with DQ first, all 4 DQS pairs then fail |
| c5 | per byte, grid 0.05, escalation off | 10 |
| c6 | as c5, plus via-cost 20 | 15 |
| c7 | grid 0.1, via-cost 20, meander amplitude 0.5 | 14 |
| c8 | grid 0.1, escalation board | 7 |
| **c9** | grid 0.05, escalation board | **5** |
| c10 | as c5, B0 first | 19 |
| c11 | as c5, meander amplitude 0.5 | 13 |

The 821801 runs:
- **n1/n2** (escalation board/fab): 8 open.
- **n3** (neck-down length 6): 9 open.

## Results

**Baselines:**
- 50 Ω: main with zones refilled has 218 violations and 196 unconnected. 66 of the unconnected are LPDDR4 (KiCad's
  count), and 0 of the violations are.
- 821801: the baseline was checked against a copy of the rule file rewritten to the 821801 targets (widths 0.18
  inner / 0.18–0.22 F.Cu, pair gap 0.1, skew 1 ps, 0.2 mm spacing warning).

| | c9 (50 Ω, old rule file) | n1 (821801 targets, rewritten rule file) |
|---|---|---|
| LPDDR4 connections open | 5 (of 66) | 8 (of 66) |
| Failed nets | CA step: 4 (CK pair not coupled, routed single-ended) | A1: 1, B0: 2, CA: 3; CK pair not coupled |
| New DRC violations, all LPDDR4 | 738 | 485 |
| …errors | track_width ≥199, diff gap 34, uncoupled 3, skew 2 | track_width ≥199, diff gap 60, uncoupled 4, skew 5 |
| …warnings | 499 crosstalk (<0.25 mm), 1 dangling via | 212 spacing (<0.2 mm), 5 dangling vias |
| Footprints moved / non-LPDDR copper changed | none / none | none / none |
| Forbidden layers | one 0-length segment on B.Cu; nothing on In1/3/4/6 | none |
| In5 outside the 1V1 pour outline | 84 of 3180 sample points | 68 of 2892 |
| Total LPDDR4 copper / vias | 1498 mm / 164 | 1494 mm / 177 |

The total copper compares with a Manhattan estimate of about 900 mm.

### Per-byte lengths and timing

Delays are approximate: 5.9 ps/mm on F.Cu, 6.9 ps/mm inner, no vias and no package delays. The board pads carry no
`die_delay`, so the tool can't include the FPGA package delays either.

**c9 (50 Ω):**

| Byte | DQ/DM length spread | DQ–DQ | DQ–DQS | DQS P–N | Layers (mm) |
|---|---|---|---|---|---|
| A0 | 3.9 mm | 36 ps | +36..+72 ps | 1.0 ps | In2 237, F 78 |
| A1 | 21.8 mm | 149 ps | −12..+138 ps | 0.7 ps | In5 266, F 48 |
| B0 | 42 mm | 245 ps | −87..+158 ps | 42 ps | F 309, In2 69 |
| B1 | 10.4 mm | 72 ps | −17..+55 ps | 3.4 ps | In2 147, F 42 |

CA/CK in c9:
- CLK→CA spans −72 to +351 ps.
- CK P–N skew is 268 ps; the pair is not coupled.

**n1 (821801):**

| Byte | DQ–DQ | DQ–DQS | DQS P–N | Main layer |
|---|---|---|---|---|
| A0 | 171 ps | +42..+213 ps | 3.4 ps | In2 |
| A1 | 286 ps | −142..+144 ps | 13 ps | In5 |
| B0 | 186 ps | −73..+113 ps | 63 ps | F.Cu |
| B1 | 131 ps | −18..+114 ps | 1.0 ps | In2 |

CA/CK in n1:
- CLK→CA spans +67 to +287 ps.
- CK P–N skew is 16 ps.

Against the 821801 limits:
- DQ–DQ < 43 ps: only c9 A0 meets it.
- DQ–DQS within −68/+43 ps: no byte meets it.
- CLK–CA ±34 ps: not met.
- DQS P–N < 1 ps: only B1, at 1.0 ps.

The DQS can't be meandered to its byte. `route.py` doesn't route pairs, and `route_diff.py` only meanders pairs it
routes in that same call. Routing the DQ first and the DQS afterwards leaves no room for any DQS pair.

### Do the 821801 widths fit?

Partly, and only through neck-downs:
- The 0.18 mm main segments never pass between U7 balls: 0.345 mm gap against 0.18 + 2 × 0.1. At U12 they only just
  fit: 0.38 mm against 0.38.
- The router lays a stepped taper (0.18 → 0.164 → … → 0.1, sometimes 0.09) near every pad.
- About 1900 segments are at full 0.18 mm and about 1100 are tapered or necked. Many of the necked ones lie outside the
  courtyards, which gives the ≥199 track-width errors.
- F.Cu is 0.18, not 0.20: the power-net width is one value for all layers.
- Completion is about the same as at 50 Ω (8 vs 5 open). The escape channels are not what limits it; the problem is
  the shape of the routes.

Spacing in n1, outside the courtyards (counted as segment pairs):
- 408 pairs are closer than 0.2 mm within a group;
- 33 pairs are closer than 0.3 mm between groups.

In c9 the counts are 1538 and 321. The 0.3 mm keep-away is soft and the 0.1 mm hard clearance is global; the tool has
no clearance per area or per class pair.

## Main problems

1. **Topology.** Many nets circle U12 or run the length of the package. Bytes don't stay on one layer, for example
   B0 is 309 mm on F.Cu and 69 mm on In2. A0 and A1 cross wherever they like.
2. **Length and timing.** Matching only meanders nets routed in the same call, and only up to the longest net, which
   is often a 40–60 mm detour. Meanders often find no straight run. DQS can't be matched to its byte.
3. **The CK pair** is never routed coupled in any run.
4. **Rules it can't express:**
   - widths per area or per layer, except through the impedance or power-net neck-down;
   - the U7/U12 courtyard clearances;
   - In5 restricted to the 1V1 pour;
   - B.Cu can only be avoided by leaving it out of the layer list.
5. **Risky defaults.** Out of the box it rips other nets, moves caps and repairs planes. These needed environment
   switches to turn off.

## Recommendation

Don't build on these boards. Route by hand from the reroute plan. If the tool is used at all, use it only for a single
easy byte (A0 came out reasonably: 3.9 mm spread, on In2), as a sketch to copy, not to clean up.
