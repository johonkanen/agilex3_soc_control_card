#!/usr/bin/env python3
"""Corner model files: models/min/ and models/max/ (git-ignored, like models/): the IBIS files of models/ with the
min or max column copied into the typ column (kicad_ibis.ibisfix.corner_as_typ), so the min/max corners are
simulated at typ.

  python3 corner_models.py

Why: KiCad 10.0.7's corner keywords (vcc=MIN/MAX rpin=... on the IBIS element) are right only into the load the V-t
tables were made with (R_fixture, 50 ohm here); into other loads the high level is off (tools/kicad_ibis_simulation
CLAUDE.md, seen on the Efinix board: +46 mV into 60 ohm, +129 mV open). run_si.py --validate-corners compares both.
The per-pin package R/L/C in [Pin] (W66: written there by prep_models.py) has no corners and stays typ.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../../tools/kicad_ibis_simulation'))
from kicad_ibis import ibisfix

MODELS = os.path.join(HERE, 'models')
FILES = ('agilex5_lpddr4.ibs', 'w66_lpddr4.ibs')


def main():
    for corner in ('min', 'max'):
        os.makedirs(os.path.join(MODELS, corner), exist_ok=True)
        for f in FILES:
            out = os.path.join(MODELS, corner, f)
            open(out, 'w').write(ibisfix.corner_as_typ(open(os.path.join(MODELS, f), errors='replace').read(), corner))
            print(os.path.relpath(out, HERE))


if __name__ == '__main__':
    main()
