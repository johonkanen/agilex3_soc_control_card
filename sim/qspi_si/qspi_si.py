"""QSPI (SDM AS x4 -> IS25WP128, U7 -> U2) write-direction SI, to choose the series resistors R293-R298.

  python3 ../lpddr4_si/corner_models.py        # once: the corner model files (models/ are git-ignored)
  KICAD_APPRUN=.../AppRun python3 qspi_si.py   # -> results.json, results.md

Write direction only: Agilex SDM driver 1p8_io_d8s1 (Quartus IBIS) -> optional
series R at the driver -> via -> 0.10 mm In2 stripline -> via -> receiver.
Receiver: STAND-IN (no public IS25WP128 IBIS): Agilex 1p8_in_20wpu (1.8 V CMOS input with clamps, C_comp 4.4 pF)
on a BGA pin, plus 1.6 pF so the input totals the flash's 6 pF CIN (data sheet max)."""
import os, sys, json
from concurrent.futures import ProcessPoolExecutor
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(HERE, '../..')
sys.path.insert(0, B + '/tools/kicad_ibis_simulation')
from kicad_ibis import spice
from kicad_ibis.fastnet import Netlist, KibisCache
WORK = HERE + '/work'; os.makedirs(WORK, exist_ok=True)
MOD = {'typ': B + '/sim/lpddr4_si/models', 'min': B + '/sim/lpddr4_si/models/min', 'max': B + '/sim/lpddr4_si/models/max'}
COMP = 'Agilex5_A5EB013BB23BE6S'
NETS = {'CLK': ('CY69', 26.7, 2), 'D0': ('CN64', 35.4, 2), 'CS': ('BY71', 38.7, 3)}   # pin, mm on In2, vias
Z0, PS = 53.8, 7.08            # 0.10 mm on In2 (field solve), ps/mm from the tuning profile
RATE = 200.0                   # Mb/s: AS_CLK 100 MHz, the -6S maximum (config user guide note 15)
NB = 120

def build(net, corner, rs):
    pin, mm, nv = NETS[net]; lib = MOD[corner] + '/agilex5_lpddr4.ibs'
    n = Netlist(f'{net} {corner} Rs={rs}')
    n.ibis('d', 'drv', lib, COMP, pin, '1p8_io_d8s1', ['p'], f'f0={RATE:g}M n={NB}')
    if rs: n.r('p', 'a', rs)
    else: n.r('p', 'a', 1e-3)
    n.l('a', 'v1', 0.15e-9); n.r('a', 'v1', 200); n.c('v1', '0', 0.4e-12)          # F.Cu -> In2 via
    segs = nv - 1; L = mm / segs; prev = 'v1'
    for k in range(segs):
        nxt = f't{k}'
        n.tl(prev, nxt, Z0, L * PS * 1e-12)
        if k < segs - 1: n.l(nxt, f'm{k}', 0.15e-9); n.r(nxt, f'm{k}', 200); n.c(f'm{k}', '0', 0.4e-12); nxt = f'm{k}'
        prev = nxt
    n.l(prev, 'rx', 0.15e-9); n.r(prev, 'rx', 200); n.c('rx', '0', 0.4e-12)       # In2 -> F.Cu via
    n.ibis('r', 'rx', lib, COMP, 'AN67', '1p8_in_20wpu', ['rx'])
    n.c('rx', '0', 1.6e-12)
    n.directive('.save v(rx) v(xr.die0) v(xd.die0)')
    n.directive('.options method=gear maxord=2 reltol=1e-4')
    n.directive(f'.tran 1p {NB / RATE * 1e-6 + 2e-9:.6g}')
    return n

def crossings(v, th):
    s = v > th
    return int(np.count_nonzero(s[1:] != s[:-1]))

def run(job):
    net, corner, rs, cir = job
    dat = cir[:-4] + '.dat'
    t, w = spice.ngspice(cir, ['rx', 'xr.die0', 'xd.die0'], dat); os.remove(dat)
    ui = 1e-6 / RATE; sel = t > 8 * ui
    vdd = {'typ': 1.8, 'min': 1.62, 'max': 1.89}[corner]
    edges = crossings(w['xd.die0'][sel], vdd / 2)            # transitions sent
    out = dict(net=net, corner=corner, rs=rs, edges=edges)
    for node, nm in (('rx', 'pin'), ('xr.die0', 'die')):
        v = w[node][sel]
        out[f'vmax_{nm}'] = float(v.max()); out[f'vmin_{nm}'] = float(v.min())
        # a clean edge crosses VIH (0.7 VDD) and VIL (0.3 VDD) once each; extra crossings = ringback into the band
        out[f'extra_{nm}'] = (crossings(v, 0.7 * vdd) - edges) + (crossings(v, 0.3 * vdd) - edges)
    return out

if __name__ == '__main__':
    cache = KibisCache(WORK + '/kibis'); jobs = []; nl = []
    for net in NETS:
        for corner in ('typ', 'min', 'max'):
            for rs in (0, 22, 33, 47, 68):
                n = build(net, corner, rs); nl.append((net, corner, rs, n))
    print('KIBIS:', cache.resolve([e for *_, n in nl for e in n.ib], jobs=6), flush=True)
    for net, corner, rs, n in nl:
        jobs.append((net, corner, rs, n.write(f'{WORK}/{net}_{corner}_r{rs}.cir', cache)))
    with ProcessPoolExecutor(12) as ex: rows = list(ex.map(run, jobs))
    json.dump(rows, open(HERE + '/results.json', 'w'), indent=1)
    out = ['| net | corner | Rs (ohm) | edges | Vmax pin / die (V) | Vmin pin / die (V) | extra VIH/VIL crossings pin / die |',
           '|---|---|---|---|---|---|---|']
    for r in rows:
        out.append(f"| {r['net']} | {r['corner']} | {r['rs']} | {r['edges']} | {r['vmax_pin']:.2f} / {r['vmax_die']:.2f} | {r['vmin_pin']:.2f} / {r['vmin_die']:.2f} | {r['extra_pin']} / {r['extra_die']} |")
    open(HERE + '/results.md', 'w').write('\n'.join(out) + '\n'); print('\n'.join(out))
