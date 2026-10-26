# Common settings for the KRT trunk scripts (source it).  Override any of these in the environment.
REPO=${REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}
KRT=${KRT:-$HOME/dev/KiCadRoutingTools}             # KiCadRoutingTools checkout with its .venv
KICAD_APPRUN=${KICAD_APPRUN:?set KICAD_APPRUN to the KiCad AppImage AppRun (gives python3.11 with pcbnew and kicad-cli)}
KPY="$KICAD_APPRUN python3.11"; KCLI="$KICAD_APPRUN kicad-cli"
TOOLS="$REPO/tools/lpddr4_krt"
proj(){ for e in kicad_pro kicad_dru; do cp "$REPO/agilex_3_soc.$e" "$1.$e"; done; }   # project files next to a board copy
