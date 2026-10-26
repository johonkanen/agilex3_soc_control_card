#!/usr/bin/env bash
# grade.sh WORK NAME : finish WORK/NAME/trunk -> out, KiCad DRC, KiCad delay probe, timing summary, path trace
set -u; source "$(dirname "$0")/env.sh"
W=$(realpath "$1"); N=$2; cd "$W/$N"; proj out; proj probe
$KPY "$TOOLS/finish.py" trunk.kicad_pcb out.kicad_pcb "$W/prep.json" 2>&1 | grep finish
$KCLI pcb drc -o drc.rpt out.kicad_pcb > /dev/null 2>&1
cp out.kicad_pcb probe.kicad_pcb
printf '\n(rule "probe_delay"\n\t(condition "A.hasNetclass(%s) || A.hasNetclass(%s)")\n\t(constraint length (min 1ps) (max 2ps)))\n' "'lpddr_ca'" "'lpddr_diff'" >> probe.kicad_dru
$KCLI pcb drc --severity-all -o probe.rpt probe.kicad_pcb > /dev/null 2>&1
python3 "$TOOLS/report.py" "$N" drc.rpt probe.rpt "$W/prep.json" drc.rpt
$KPY "$TOOLS/paths.py" out.kicad_pcb "$W/prep.json" 2>&1 | grep -v -i 'debug\|memory leak'
