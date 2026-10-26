#!/usr/bin/env bash
# One KRT trunk variant:  run.sh WORK NAME [extra route.py args]   (WORK holds prep.kicad_pcb from prep.py)
#   env LC   layer costs F In1 In2 In3 In4 In5 In6 B (-1 = forbidden), default "6 -1 1 -1 -1 1 -1 -1" (v15)
#       MATCH=1  time-match the CA group (TOL ps); NOCK=1  leave CK out of the group
set -u; source "$(dirname "$0")/env.sh"
W=$(realpath "$1"); N=$2; shift 2; mkdir -p "$W/$N"; cd "$W/$N"; cp "$W/prep.kicad_pcb" .; proj prep; proj trunk
P='/IOBANK 3/'
if [ -n "${NOCK:-}" ]; then G=("${P}ca[0-5]" "${P}cke" "${P}~{cs}"); else G=("${P}ca[0-5]" "${P}cke" "${P}~{cs}" "${P}ck_[PN]"); fi
M=(); [ -n "${MATCH:-}" ] && M=(--length-match-group "${G[@]}" --time-matching --time-match-tolerance "${TOL:-1}")
export KICAD_RIP_PREEXISTING=0
"$KRT/.venv/bin/python" -X utf8 "$KRT/py_router/route.py" prep.kicad_pcb trunk.kicad_pcb --nets "${G[@]}" "${P}~{rst}" "${M[@]}" \
  --no-bga-zones U7 U12 --layers F.Cu In1.Cu In2.Cu In3.Cu In4.Cu In5.Cu In6.Cu B.Cu --layer-costs ${LC:-6 -1 1 -1 -1 1 -1 -1} \
  --impedance 40 --clearance 0.11 --routing-clearance-margin 0.01 --via-size 0.3 --via-drill 0.15 --grid-step 0.05 \
  --bga-proximity-radius 1 --proximity-heuristic-factor 0.02 --max-iterations 1000000 --no-fix-drc-settings \
  --json-out trunk.json "$@" > trunk.log 2>&1
echo "$N: $(grep -E 'Single-ended:' trunk.log | tail -1)"
