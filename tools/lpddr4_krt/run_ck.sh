#!/usr/bin/env bash
# CK as a coupled pair with route_diff.py:  run_ck.sh WORK NAME [extra route_diff args]
# (WORK/prep.kicad_pcb made with PREP_NETS='ck_P ck_N' prep.py, so the CA trunks stay as obstacles)
#   env GAP (pair gap, 0.12), WIDTH (0.14), LC (layer costs, as run.sh)
set -u; source "$(dirname "$0")/env.sh"
W=$(realpath "$1"); N=$2; shift 2; mkdir -p "$W/$N"; cd "$W/$N"; cp "$W/prep.kicad_pcb" .; proj prep; proj trunk
export KICAD_RIP_PREEXISTING=0
"$KRT/.venv/bin/python" -X utf8 "$KRT/py_router/route_diff.py" prep.kicad_pcb trunk.kicad_pcb --nets '/IOBANK 3/ck_*' \
  --diff-pair-intra-match --diff-pair-gap ${GAP:-0.12} --track-width ${WIDTH:-0.14} --no-gnd-vias \
  --no-bga-zones U7 U12 --layers F.Cu In1.Cu In2.Cu In3.Cu In4.Cu In5.Cu In6.Cu B.Cu --layer-costs ${LC:-6 -1 1 -1 -1 1 -1 -1} \
  --clearance 0.11 --routing-clearance-margin 0.01 --via-size 0.3 --via-drill 0.15 --grid-step 0.05 \
  --bga-proximity-radius 1 --proximity-heuristic-factor 0.02 --heuristic-weight 1.5 --no-fix-drc-settings "$@" > trunk.log 2>&1
echo "$N: $(grep -E 'Diff pairs:|coupled|single.ended' trunk.log | tail -2 | tr '\n' ' ')"
