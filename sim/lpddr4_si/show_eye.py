"""Open the worst eye (smallest mask timing margin, then voltage margin) in an interactive matplotlib window.

  python3 show_eye.py                  # worst over the realistic sweeps (results, zsweep; both data rates)
  python3 show_eye.py --all            # also the deliberately bad zlimit/zfail lines
  python3 show_eye.py POINT CASE RX WHERE   # a given row, e.g. r2133.33_zs70_l20_min dqr40 U4 die

Needs the work/*.dat waveforms from run_si.py. Each 1-UI trace is coloured by its bit (1 red, 0 blue). For any
other waveform file: python3 -m kicad_ibis.show_eye (tools/kicad_ibis_simulation).
"""
import argparse, csv, glob, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('row', nargs='*')
ap.add_argument('--all', action='store_true')
a = ap.parse_args()

rows = []
for f in glob.glob(os.path.join(HERE, 'results', 'results*.csv')):
    if not a.all and ('zlimit' in f or 'zfail' in f): continue
    rows += list(csv.DictReader(open(f)))
if a.row:
    rows = [r for r in rows if [r['point'], r['case'], r['rx'], r['where']] == a.row]
    if not rows: sys.exit('no such row')


def key(r):
    tm = float(r['t_margin_ps']); return (tm if tm == tm else -1e9, float(r['v_margin_mV']))


r = min(rows, key=key)
os.environ['SI_RATE'] = '2133.333' if r['point'].startswith('r2133') else '1600'   # before importing run_si (UI)
sys.path.insert(0, HERE)
import run_si as R
import matplotlib.pyplot as plt

tag = r['point']; meta = json.load(open(os.path.join(R.WORK, tag + '.json')))
vecs = []
for case, m in meta.items():
    vecs.append(f"x{m['drv'].lower()}.die0")
    for ref, pad in m['rx']: vecs += [pad, f"x{ref.lower()}.die0"]
t, w = R.spice.load(os.path.join(R.WORK, tag + '.dat'), vecs)
m = meta[r['case']]
pad = dict(m['rx'])[r['rx']]
v = w[pad if r['where'] == 'ball' else f"x{r['rx'].lower()}.die0"]
mask = R.MASK[m['kind']]; lo, hi = R.LIMIT[m['kind']]
ph, tr, lab, e = R.eye.analyse(t, w[f"x{m['drv'].lower()}.die0"], v, R.UI, mask, R.TAIL, R.SKIP)
fig, ax = plt.subplots(figsize=(10, 6))
R.eye.draw(ax, ph, tr, lab, e, mask, R.UI,
           f"{r['case']} {r['rx']} {r['where']}  |  {tag}  ({R.RATE:g} MT/s, DQ {r['zdq']} ohm {r['ldq']} mm, "
           f"{r['corner']}); limits {lo * 1e3:.0f}..{hi * 1e3:.0f} mV")
fig.tight_layout(); plt.show()
