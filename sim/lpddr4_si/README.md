# LPDDR4 IBIS simulation: 40 Ω vs 50 Ω data lines

KiCad 10 + ngspice IBIS simulation of the U7 (Agilex 5 A5EB013B, B23B) ↔ U12 (LPDDR4 x32, 2 channels) interface at
1600 MT/s. It answers the "Open decision: 50 Ω LPDDR4 data routing" in `NEXT_STEPS.md`. Results and the recommendation
are in `NEXT_STEPS.md` (section "IBIS simulation results") and `results/`.

## Files

| file | what |
|---|---|
| `lpddr4_si.kicad_sch` / `.kicad_pro` | the baseline circuit (40 Ω, 20 mm DQ): every case as one channel of KiCad IBIS driver/receiver, TLINE and L/C symbols. Opens and simulates in Eeschema (Inspect → Simulator, `.tran` directive on the sheet). |
| `gen_sch.py` | writes that schematic; parameters `--zdq --ldq --zca --via-dq --corner`, `--validate` for the driver check circuit |
| `prep_models.py` | builds the two IBIS files used, from the vendor originals (see Models) |
| `run_si.py` | sweep: schematic per point → `kicad-cli sch export netlist --format spice` (this runs KiCad's IBIS-to-SPICE converter, KIBIS) → ngspice (the libngspice inside the KiCad AppImage) → eyes, Rx-mask margins, over/undershoot. `--validate` checks the converted drivers against the IBIS V-t tables. |
| `report.py` | `results/results.csv` → `results/results.md` |
| `zsolve.py` | 2D field solve: trace width → Z0 and ps/mm for In2/In5 and F.Cu/B.Cu |
| `show_eye.py` | opens the worst eye (or a given CSV row) in an interactive matplotlib window |
| `../../tools/kicad_ibis_simulation` | git submodule with the generic parts (`kicad_ibis`: schematic writer, kicad-cli/KIBIS export, ngspice runner, eye analysis); `git submodule update --init` after cloning |
| `results/` | `results.csv` (every receiver, ball and die), `results.md`, `eye_*.png` (20 mm points, receiver die), `validate_drivers.png/.md` |
| `models/`, `work/` | git-ignored: vendor models, generated netlists/waveforms |

## Rerun

```sh
# KiCad 10.0.7 AppImage, extracted once
cd /some/scratch && ~/kicad/kicad-10.0.7-x86_64.AppImage --appimage-extract
export KICAD_APPRUN=/some/scratch/squashfs-root/AppRun

cd sim/lpddr4_si
# 1. models (see below), then
python3 prep_models.py models/agilex5_varA_ron48_quartus.ibs models/w66cl2nquafj_a001.ibs
# 2. check the converted drivers, then the sweep (12 points, about 10 min on 16 cores), then the table
python3 run_si.py --validate
python3 run_si.py            # --quick: 40/50 Ω at 20 mm only
python3 run_si.py --zsweep   # also --zlimit (80-150 Ω), --zfail (long mismatched lines), --casweep (all at 0.10 mm)
SI_RATE=2133.333 python3 run_si.py   # any of the above at 2133 MT/s (the -6S maximum); files get an _2133.33 suffix
python3 report.py [results/results_x.csv]
python3 show_eye.py          # worst eye in a window; --all includes the deliberately bad sweeps
```

Needs python3 with numpy and matplotlib. `kicad-cli` resolves the IBIS paths in the schematic relative to the current
directory, so `run_si.py` runs it inside `work/` (paths `../models/...`); the committed schematic uses `models/...` and is
meant to be opened from this folder. KIBIS writes its subcircuits to `~/.cache/kicad/10.0/ibis/`; `run_si.py` clears and
copies them per point.

## Models (not in git: copyrighted)

| file in `models/` | source |
|---|---|
| `agilex5_varA_ron48_quartus.ibs` | Quartus Pro 26.1.1, from a copy of `~/dev/agilex5_emif_test/varA_ron48`: `quartus_eda emif_test -c emif_test --board_signal_integrity=on --format=ibis --output_directory=ibis`. Gives the real output buffers of the build: `lvstl11_io_s3r40c_doff` (LVSTL 1.1 V, 40 Ω calibrated, fastest slew, de-emphasis off) for DQ/DQS/CA/CK, with per-pin package R/L/C. |
| (Quartus install) `quartus/common/misc/ibis_writer/input_files/agilex_5_device_emif_ami.ibs` | `prep_models.py` copies the read receiver `lvstl11_in_e0g50c` (50 Ω calibrated parallel OCT, no Rx equalisation) and `dlvstl11_in_e0g50c` from here: the Quartus-written file has only the output models of the build. The AMI (DLL) part is dropped. |
| `w66cl2nquafj_a001.ibs` | **Stand-in for the SK hynix H9HCNNN8KUMLHR, whose IBIS model is not public.** Winbond W66CL2NQUAFJ (4 Gb LPDDR4 x32, 2 channels, 200-ball DDP, 1600 MHz), public: `https://www.winbond.com/resource-files/W66xLxNxUAxx_ibis.zip` (listed on winbond.com as "W66 ... LPDDR4 ... IBIS Model", DA03-GAA101). Models used: `ODT_48` (DQ ODT), `PD40_ODT80_VOH25` / `PD48_ODT80_VOH25` (DQ drive 40/48 Ω, pull-up calibrated to VDDQ/2.5 as MR3 OP0 = 1 in the Quartus build), `CA_ODT_80` / `CA_ODT_60`. |
| `agilex5_lpddr4.ibs`, `w66_lpddr4.ibs` | written by `prep_models.py`. |

If the SK hynix model arrives from an FAE: put it in `models/`, check its [Pin] header spelling and package section the
same way, and change `MEM`/`DQ_MEM`/`CA[..]['mem']` and the model names in `gen_sch.py`.

### KiCad 10 IBIS converter: problems found and the workarounds

- `[Pin]` column names are matched case-sensitively (`R_pin`): Winbond writes `R_Pin` → "Invalid field name in [Pin]",
  the whole file is rejected. `prep_models.py` rewrites the header.
- `[R Series]` (Altera's REFCLK series model) is an unknown keyword → file rejected. Dropped with its
  `[Series Pin Mapping]` (not an LPDDR4 pin).
- `[Define Package Model]` matrices are parsed but not used for the pins; Winbond's `[Package]` is all zero, so the DRAM
  package would be missing. `prep_models.py` writes the matrix diagonal (self R/L/C) into the `[Pin]` columns (DQ ≈
  0.73 Ω / 1.24 nH / 0.54 pF, CA ≈ 1.7 Ω / 3.0 nH / 1.15 pF). Coupling terms are not modelled.
- The headless CLI only prints the parser's last message ("Invalid IBIS file ..."); the bisection to find the above
  was done with `kicad-cli` on trimmed files.
- KIBIS writes the driver switching coefficients Ku/Kd as PWL sources with ~1e5 points (every 0.8 ps IBIS sample), so
  one 96 ns transient did not finish in 10 min; they also carry narrow solver spikes (−0.9…+1.3 for a few ps, where the
  two-waveform equations are ill-conditioned). `run_si.py` resamples them to 0.5 ps, median-filters over 2.5 ps and
  simplifies to 1e-3: about 18 k points, about 1 min per run. `SI_RAW_KUKD=1` skips this; the driver check is the same
  with and without it.
- No zero-valued-table / converge-to-0 problem was seen with these files.
- Corners: KIBIS compares the `vcc`/`rpin`/`lpin`/`cpin` value with `"MIN"`/`"MAX"` in upper case, while the parameter's
  own enum (and the Eeschema dialog) offers `min`/`max`; lower case silently gives typ. `gen_sch.py` writes upper case.
  C_comp is typ in every corner (KiCad 10 limitation); corners switch the I-V/V-t columns, supply and pin R/L/C.
- `Sim.Params` `f0` of a PRBS driver is the bit rate (1.6 G), not a clock. KIBIS' PRBS is PRBS7 (x⁷+x⁶+1).

Driver check (`results/validate_drivers.md`, converted model without package into 50 Ω to GND vs the IBIS table): levels
match to 1 mV; 20–80 % edges match within 1–4 ps, except the Winbond PD48 falling edge (39 ps vs 28 ps in the table),
which makes the 48 Ω read case slightly pessimistic.

## What is modelled

Per channel, all uncoupled: IBIS driver (pin package R/L/C, C_comp) → via (π: C/2, L, C/2) → 1.5 mm 0.10 mm neck-down
→ line → neck-down → via → IBIS receiver (package, C_comp, clamp/ODT I-V). Lines are lossless TLINE (ngspice LTRA,
R = G = 0); at 800 MHz over ≤ 28 mm the loss is a few hundredths of a dB.

| item | value | source |
|---|---|---|
| stripline In2/In5 | 0.18 mm = 39.8 Ω, 0.12 mm ≈ 50 Ω, 7.02 ps/mm | field solve (`LPDDR4_SWIZZLE_PLAN.md`) |
| microstrip B.Cu | 0.10 mm ≈ 60 Ω (estimate), 6.16 ps/mm | extrapolated from 0.20 mm = 44.3 Ω, 0.15 mm ≈ 51 Ω |
| neck-down, inner | 0.10 mm ≈ 55 Ω (estimate), 1.5 mm at each BGA | extrapolated from the 0.18/0.12 mm solves |
| via 0.3/0.15 mm, F.Cu ↔ In2 ("short") | L 0.15 nH, C 0.40 pF incl. stub | estimate (0.2·h·(ln(4h/d)+1), coax C with 0.5 mm antipad) |
| via, F.Cu ↔ In5 / In2 ↔ B.Cu / B.Cu ↔ F.Cu ("long") | L 0.50 nH, C 0.40 pF | estimate, reduced from the 1.2 nH isolated-via value for the BGA ground-via field |
| DQ | U7 T62 (DQ[9], largest package L·C of the DQ pins: 2.11 Ω, 6.43 nH, 2.77 pF) ↔ U12 DQ9_A; 16/20/22 mm, long vias (In5) both ends; `short` = In2 | data bytes not routed yet |
| CA0 | U7 B66 → In2 27.99 mm (0.171 mm) → T-via → 2 × B.Cu 2.43 mm (0.10 mm) → via → U12 H2 / R2 | board, 2026-10-27 (`tools/lpddr4_krt/paths.py`) |
| CA5 | U7 A66 → In2 10.77 mm → T-via → 2 × B.Cu 1.76 mm → via → U12 J11 / P11 | board |
| "50 Ω" point | DQ line and CA trunk at 50 Ω, same delay per mm | |

Not modelled: crosstalk (single uncoupled lines), power-supply noise / SSO, driver and receiver jitter, DQS/CK timing,
the real SK hynix buffers and package, C_comp corners.

## Masks and limits used

| | mask | where | source |
|---|---|---|---|
| DQ write (DRAM Rx) | rectangle VdIVW 140 mV × TdIVW 0.22 UI (137.5 ps) | DRAM ball and die | JEDEC JESD209-4 LPDDR4 Rx mask, 1600 column, as reproduced in TI SPRAD66B ("LPDDR4 eye mask requirements"); check against the SK hynix datasheet |
| CA (DRAM Rx) | rectangle VcIVW 175 mV × TcIVW 0.30 UI (187.5 ps) | DRAM ball and die | same |
| DQ read (FPGA Rx) | diamond 140 mV × 0.42 UI | FPGA ball and die | TI SPRAD66B SoC-side read mask, used as a proxy: Altera publishes no Agilex 5 LVSTL Rx mask |
| over/undershoot, DRAM | −0.4 … 1.5 V | | JEDEC DC absolute maximum, VIN/VOUT (check the SK hynix datasheet, incl. AC overshoot area) |
| over/undershoot, FPGA | −0.3 … VCCIO + 0.25 V (100 % of the time) | | Agilex 5 data sheet 813918, "Maximum Allowed Overshoot", Table 7 (1.1 V HSIO) |

Eye metrics per receiver node, after the first 12 bits: eye height = largest vertical opening; eye width = widest
zero-height opening at the best Vref; mask margins = the mask placed at its best position and Vref (Vref is trained on
LPDDR4): voltage margin = opening over the mask window minus the mask height (for the diamond: uniform shrink), time
margin = eye width at the mask height minus the mask width. Bits come from the driver's own die waveform; the receiver
is aligned by cross-correlation. The margins are SI only (reflections, ISI, package, buffer edges): jitter, crosstalk,
SSO and the DRAM/FPGA timing budgets (tDQSQ, tDIVW, training resolution) still have to fit inside them.

## How narrow can the data traces be (2026-10-27)

`zsolve.py`: 2D finite-difference field solve of one trace in this stack-up (same numbers as the earlier solve
within ~2 %: 0.18 mm In2 = 40.7 Ω vs 39.8, 0.12 mm = 49.7 vs 48.6, F.Cu 0.15 mm = 49.6 vs 51). The range is the
lower plane under In2 being In3 or In4:

| width | In2/In5 stripline | F.Cu/B.Cu microstrip (30 µm mask) |
|---|---|---|
| 0.18 mm | 40.7–42.1 Ω, 7.01 ps/mm | |
| 0.15 mm | 44.7–46.2 Ω | 49.6 Ω, 6.16 ps/mm |
| 0.12 mm | 49.7–51.2 Ω | 54.6 Ω |
| 0.10 mm | 53.8–55.3 Ω, 7.00 ps/mm | 58.6 Ω, 6.14 ps/mm |
| 0.09 mm | 56.2–57.7 Ω | 60.9 Ω |
| 0.08 mm | 58.8–60.3 Ω | |

`run_si.py --zsweep` (DQ line and neck-downs at 55/60/65/70 Ω, 20 mm, typ and min corner; `results/results_zsweep.csv`),
worst of ball/die, compared with 40 Ω:

| DQ line | write: EH, margin V / t, Vmax / Vmin | read 48 Ω: EH, margin V / t |
|---|---|---|
| 40 Ω | 626 mV, +482 mV / +424 ps, 672 / −27 mV | 344 mV, +205 mV / +271 ps |
| 50 Ω | 627, +485 / +422, 702 / −49 | 344, +205 / +264 |
| 55 Ω | 626, +485 / +418, 714 / −56 | 344, +205 / +262 |
| 60 Ω | 625, +484 / +416, 721 / −61 | 344, +205 / +260 |
| 70 Ω | 626, +482 / +413, 728 / −65 | 344, +205 / +256 |

The min corner moves every row by the same ~−28 mV (write) / −8 mV (read). The channel is short (≈140 ps of line) and
terminated at both ends close to the line impedance (40 Ω source, 48/50 Ω ODT), so a mismatched line costs only
small reflections: ~10–15 ps of time margin and ~55 mV more write overshoot going from 40 to 70 Ω. SI does not set
the width limit in the range JLC can make; manufacturing does (JLC: 0.09 mm minimum trace on multilayer boards).

**Recommendation: route the data bytes (DQ/DM/DQS) at 0.10 mm on In2/In5 (≈54–55 Ω) and on F.Cu/B.Cu (≈59 Ω).** That
is the width already used for the BGA neck-downs and the Default net class, so a byte becomes one width end to end, with
no neck-down steps. Do not go below 0.10 mm for whole routes: 0.09 mm is JLC's floor and gains nothing in SI; keep it
for local squeezes only. Delay per mm is unchanged (7.00 / 6.14 ps/mm), so the length/delay tuning stays valid.
Not simulated: crosstalk (narrower traces at the same pitch leave more gap, so it should not get worse; the 2h/3h
spacing rules still apply), DQS/CK as coupled pairs, and SSO.

## Maximum data rate, the failure limit and the CA bus at 0.10 mm (2026-10-27)

The -6S EMIF IP allows 1600 and 2133 MT/s only. At 2133 MT/s (UI 469 ps; masks kept at the 1600 values in UI,
not checked against JEDEC's 2133 column) everything still passes. Worst of ball/die, typ, mask margin V / t:

| DQ line | 1600: write | 1600: read 48 Ω | 2133: write | 2133: read 48 Ω |
|---|---|---|---|---|
| 40 Ω | +484 / +424 | +205 / +271 | +465 / +286 | +202 / +158 |
| 55 Ω | +486 / +418 | +205 / +262 | +454 / +284 | +200 / +156 |
| 70 Ω | +484 / +413 | +205 / +256 | +427 / +284 | +193 / +151 |
| 100 Ω | +476 / +404 | +204 / +237 | +400 / +271 | +186 / +134 |
| 150 Ω | +434 / +376 | +184 / +187 | +316 / +247 | +152 / +71 |

On a 20 mm route impedance alone never closes the eye (the line is ~140 ps). `--zfail` shows the analysis does fail
when it should: 150 Ω with 40-80 mm of line fails the read mask at both rates (e.g. 2133, 80 mm: −4 mV, no width).

`--casweep` (DQ 55 Ω, CA trunk 55/60 Ω, typ/min/max): worst margins 1600 / 2133 MT/s: DQ write +457/+416,
+427/+282; DQ read +197/+260, +192/+153; CA0 ODT 80 +318/+302, +230/+196; all inside abs max. **0.10 mm is fine for
DQ/DM/DQS and the CA trunk at the maximum data rate.**

DQS/CK pairs at 0.10 mm with a 0.10 mm gap (`zsolve --gap` in tools/kicad_ibis_simulation): 44 Ω odd mode, 87 Ω
differential on In2/In5 (88 Ω on F/B.Cu); the old 0.18/0.10 mm pairs were 34 Ω / 68 Ω. Driven differentially, each
leg sees Zodd, which is inside the simulated 40-70 Ω range, so the pairs are covered by the sweeps above by
equivalence; P/N skew, mode conversion and crosstalk into the pair are not simulated (the skew/spacing rules cover
them). The board rules were switched to 0.10 mm on 2026-10-28.

Bit labels: the eyes are labelled with the KIBIS PRBS7 itself (x^7+x^6+1, fixed rotation), aligned to the driver
die waveform; sampling the driver die directly flipped bits on badly mismatched lines and gave false fails.

## Corner models and the routed board after tuning (2026-10-31)

**Corner files.** KiCad's corner keywords (`vcc=MIN/MAX rpin=...`) are right only into the 50 Ω V-t fixture
(tools/kicad_ibis_simulation CLAUDE.md). `corner_models.py` writes `models/min/` and `models/max/` (the min or max
column as typ, `ibisfix.corner_as_typ`); `routed_si.py` simulates its min/max corners from them at typ.
`run_si.py --validate-corners` (`results/validate_drivers_corners.md`) compares both ways, package removed, into
50/48/60/80 Ω and open against the DC high level from each model's own V-I tables (`ibisfix.dc_high`):
- Agilex `lvstl11_io_s3r40c_doff`: within 2 mV into every load, keywords and corner files alike (the loads it drives
  here are 48/60/80 Ω ODT).
- Winbond `PD40/PD48_ODT80_VOH25` at max with keywords: +3 / +9 mV into 60 / 80 Ω and +1.0 V open (2.05 V); with the
  corner file 0 mV into every resistive load. Into 50 Ω (the FPGA read termination, its only load here) both are
  exact, so the earlier min/max results were not affected.
- "open" for the Winbond drivers is still 110-200 mV under the V-I level at the end of the 3 ns pulse with every
  method (its pull-up has almost no current near the top, so it has not settled); the board never leaves it open.
- 50 Ω edges: 20-80 % times within a few ps of the tables except PD48 falling (typ 28 vs 39 ps, max 29 vs 20 ps).

**Routed copper after the delay tuning** (`extract_routes.py` on commit 002f700, 426 netlists, 312 s at `-j 24`;
one min-corner CS netlist alone 15 s, 0.29 GB): all 952 rows pass the masks and the over/undershoot limits
(`results/routed.md`). Worst at 1600 MT/s over all corners: DQ read 196 mV / 262 ps, DQ write 455 mV / 416 ps, CA
212 mV / 314 ps (CS into 60 Ω ODT, typ). Against the run before the retuning (2026-10-30): DQ within 3 mV / 3 ps,
CA 3-18 mV lower (worst: max corner 284 -> 266 mV; CS and CA now land on CK + 10 ps). `routed_si.py` appends rows as each netlist finishes
(`--resume` continues a stopped run, `--only REGEX` runs a subset) and keeps only the worst eye per kind in memory.
