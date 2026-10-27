"""results/results.csv -> results/results.md (tables for NEXT_STEPS.md).  python3 report.py

Per row: the worst of the receiver ball and die (and of both U12 dies for CA). Margins are against the Rx mask
(run_si.py MASK): v_margin = eye opening inside the mask window minus the mask height, t_margin = eye width at the
mask height minus the mask width.
"""
import csv, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, 'results', 'results.csv'))))
for r in rows:
    for k, v in r.items():
        try: r[k] = float(v)
        except ValueError: pass

CASES = [('dqw', 'DQ write: U7 40 Ω → U12 ODT 48 Ω', 'rect 140 mV × 0.22 UI'),
         ('dqr40', 'DQ read: U12 40 Ω (PDDS 6) → U7 ODT 50 Ω', 'diamond 140 mV × 0.42 UI'),
         ('dqr48', 'DQ read: U12 48 Ω (PDDS 5) → U7 ODT 50 Ω', 'diamond 140 mV × 0.42 UI'),
         ('ca0_80', 'CA0 T (trunk 28 mm), CA ODT 80 Ω', 'rect 175 mV × 0.30 UI'),
         ('ca0_60', 'CA0 T (trunk 28 mm), CA ODT 60 Ω', 'rect 175 mV × 0.30 UI'),
         ('ca5_80', 'CA5 T (trunk 10.8 mm), CA ODT 80 Ω', 'rect 175 mV × 0.30 UI')]
POINTS = collections.OrderedDict()
for r in rows: POINTS.setdefault(r['point'], r)


def worst(point, case):
    rs = [r for r in rows if r['point'] == point and r['case'] == case]
    return dict(eh=min(r['eh_mV'] for r in rs), ew=min(r['ew0_ps'] for r in rs),
                vm=min(r['v_margin_mV'] for r in rs), tm=min(r['t_margin_ps'] for r in rs),
                vmax=max(r['vmax_mV'] for r in rs), vmin=min(r['vmin_mV'] for r in rs),
                ok=all(r['limits_ok'] in (True, 'True') for r in rs))


def label(p):
    r = POINTS[p]
    extra = {'long': '', 'short': ', short via (In2)'}[r['via']] + ('' if r['corner'] == 'typ' else f", {r['corner']} corner")
    return f"{r['zdq']:.0f} Ω", f"{r['ldq']:.0f} mm{extra}"


out = ['| case | line | DQ length / setting | eye height (mV) | eye width (ps) | mask margin V (mV) | mask margin t (ps) '
       '| Vmax / Vmin (mV) | abs max |', '|---|---|---|---|---|---|---|---|---|']
for case, title, mask in CASES:
    for p in POINTS:
        if case.startswith('ca') and POINTS[p]['ldq'] != 20: continue   # CA does not depend on the DQ length
        w = worst(p, case); z, s = label(p)
        if case.startswith('ca'): s = s.replace('20 mm', 'as routed').replace(', short via (In2)', ' (DQ via only)')
        if case.startswith('ca') and 'DQ via only' in s: continue
        out.append(f"| {title} | {z} | {s} | {w['eh']:.0f} | {w['ew']:.0f} | {w['vm']:+.0f} | {w['tm']:+.0f} | "
                   f"{w['vmax']:.0f} / {w['vmin']:.0f} | {'ok' if w['ok'] else '**over**'} |")
open(os.path.join(HERE, 'results', 'results.md'), 'w').write('\n'.join(out) + '\n')
print('\n'.join(out))
