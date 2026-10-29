"""Ring-back / glitch check on the simulated eMMC-pin waveforms (work/*.dat): edges seen by a receiver with the JEDEC
1.8 V thresholds (VIH 1.17 V, VIL 0.63 V, hysteresis between them) vs the driver die, and the worst ring-back:
after a rising edge passes VIH, how close the waveform comes back to VIH within 1.5 UI (edges followed by >= 2 UI
without a transition only; falling: to VIL);
negative = it rings back into the VIL..VIH band (a glitch when it reaches the other threshold).

  python3 ringback.py   -> results/ringback.md
"""
import glob, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../../tools/kicad_ibis_simulation'))
from kicad_ibis import spice
VIH, VIL, UI, SKIP = 1.17, 0.63, 2.5e-9, 12


def edges(t, v):
    """Schmitt receiver: list of (time, +1/-1) state changes."""
    st, out = (1 if v[0] > VIH else 0), []
    for i in np.nonzero((v > VIH) | (v < VIL))[0]:
        s = 1 if v[i] > VIH else 0
        if s != st: out.append((t[i], 1 if s else -1)); st = s
    return out


rows = []
for f in sorted(glob.glob(os.path.join(HERE, 'work', '*.dat'))):
    t, w = spice.load(f); keep = t > SKIP * UI
    t, rx, dr = t[keep], w['emmc'][keep], w['xu7.die0'][keep]
    e_rx, e_dr = edges(t, rx), edges(t, dr)
    rb = []
    if len(e_rx) == len(e_dr):        # edges followed by >= 2 UI without a driver transition: window 1.5 UI
        for i, (tc, s) in enumerate(e_rx):
            if i + 1 < len(e_dr) and e_dr[i + 1][0] - e_dr[i][0] < 2 * UI: continue
            pk = (t > tc) & (t < tc + 0.5 * UI)            # start at the first overshoot peak after the crossing
            t0 = t[pk][np.argmax(s * rx[pk])]
            sel = (t > t0) & (t < tc + 1.5 * UI)
            if sel.any(): rb.append((rx[sel].min() - VIH) if s > 0 else (VIL - rx[sel].max()))
    rows.append((os.path.basename(f)[:-4], len(e_dr), len(e_rx), min(rb) * 1e3, rx.max() * 1e3, rx.min() * 1e3))
lines = ['| point | driver edges | eMMC-pin edges | worst ring-back margin (mV) | Vmax (mV) | Vmin (mV) |', '|---|---|---|---|---|---|']
lines += [f'| {p} | {a} | {b}{" GLITCH" if b != a else ""} | {m:.0f} | {x:.0f} | {n:.0f} |' for p, a, b, m, x, n in rows]
open(os.path.join(HERE, 'results', 'ringback.md'), 'w').write('\n'.join(lines) + '\n'); print('\n'.join(lines))
