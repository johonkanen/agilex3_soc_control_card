"""eMMC (U11) write-direction SI: HPS SDMMC driver (Quartus IBIS) -> board -> eMMC input, solid reference vs In5 as
routed (In6 split 1V2 / 3V3 under the route, In6 gaps), with the return-path inductance at each reference change
swept.

  KICAD_APPRUN=.../squashfs-root/AppRun python3 run_si.py [--validate]

Results: results/summary.md, results/summary.csv, results/eye_*.png. See README.md for the model and assumptions.
"""
import argparse, csv, glob, os, sys
from concurrent.futures import ProcessPoolExecutor
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../../tools/kicad_ibis_simulation'))
from kicad_ibis import spice, eye, ibisfix
from kicad_ibis.fastnet import Netlist, KibisCache

WORK, RES = os.path.join(HERE, 'work'), os.path.join(HERE, 'results')
LIB = os.path.join(HERE, 'models', 'agilex5_hps_sdmmc.ibs')
COMP, MODEL, PIN = 'Agilex5_A5EB013BB23BE6S', '1p8_io_d8s1', 'AU74'      # HPS_SDMMC_CMD
RATE = 400e6                       # HS400 data rate (DDR on 200 MHz); CMD and CLK edges are covered by the same PRBS
UI = 1 / RATE
NBITS = 150
VCCQ = 1.8
MASK = ('rect', 0.65 * VCCQ - 0.35 * VCCQ, 0.8e-9 / UI)   # VIH-VIL (1.17 / 0.63 V), tISUddr + tIHddr = 0.4 + 0.4 ns
CORNERS = {'typ': '', 'min': ' vcc=MIN rpin=MIN lpin=MIN cpin=MIN', 'max': ' vcc=MAX rpin=MAX lpin=MAX cpin=MAX'}
CIN = {'6p': 6e-12, '2p': 2e-12}   # JEDEC eMMC 5.1 C_DEVICE max 6 pF; 2 pF = light load, most ringing

# lines (kicad_ibis.zsolve, JLC 8-layer stack-up, 0.10 mm): (ohm, ps/mm)
F_CU = (58.6, 6.14)                # F.Cu over In1 GND, 30 um mask
STRIP = (53.8, 7.00)               # In5 between In6 (0.1 mm) and In4 (0.357 mm), or In2 between In1 and In3 (mirror)
GAP = (88.5, 6.53)                 # In5 where In6 has no copper: In4 only, 0.357 mm below
VIA = (0.50e-9, 0.40e-12)          # F.Cu <-> In5 through via, estimate (as sim/lpddr4_si)
STUB_MM, BREAK_MM = 1.0, 1.0       # B.Cu stub to the 10k pull-up at U11; F.Cu breakout at U7

# sd_cmd as routed on In5 (emmc_ref.py on the board, 2026-10-29): 1V2 12.6 mm, In6 gap ~1.2 mm at the 1V2/3V3
# split, 3V3 8.1 mm, gaps / antipads ~2.5 mm under the U11 via field
IN5_SEGS = [('ref', 12.6), ('gap', 1.2), ('ref', 8.1), ('gap', 2.5)]
TOTAL_MM = sum(l for _, l in IN5_SEGS)


def case_list():
    cs = [('solid', dict(segs=[('ref', TOTAL_MM)], lret=0.0))]
    for L in (0.0, 0.5, 1.0, 2.0, 4.0):
        cs.append((f'in5_L{L:g}n', dict(segs=IN5_SEGS, lret=L * 1e-9)))
    cs.append(('bad_gap15_L10n', dict(segs=[('ref', 9.4), ('gap', 15.0)], lret=10e-9)))   # proves the check can fail
    for rs in (22, 33):             # series resistor at the HPS ball (0201 next to U7)
        cs.append((f'solid_rs{rs}', dict(segs=[('ref', TOTAL_MM)], lret=0.0, rs=rs)))
        cs.append((f'in5_L2n_rs{rs}', dict(segs=IN5_SEGS, lret=2e-9, rs=rs)))
    for d in (5.0, 10.0, 15.0, 20.0):  # 33 ohm at d mm along the route (In5, 2 nH per reference change)
        cs.append((f'in5_L2n_rs33_at{d:g}mm', dict(segs=split_at(IN5_SEGS, d, 33.0), lret=2e-9)))
    return cs


def split_at(segs, d, rs):
    out, acc = [], 0.0
    for kind, mm in segs:
        if acc <= d < acc + mm:
            out += [(kind, d - acc)] if d > acc else []
            out += [('rs', rs), (kind, acc + mm - d)]
        else:
            out.append((kind, mm))
        acc += mm
    return out


RD = 200.0                         # damping R across every lumped L (via, return path): kills the 10+ GHz L/C tanks
                                   # that stop ngspice; >> |jwL| (< 10 ohm) in the signal band


def lpar(n, a, b, L):
    n.l(a, b, L); n.r(a, b, RD)


def via(n, a, b):
    n.c(a, '0', VIA[1] / 2); lpar(n, a, b, VIA[0]); n.c(b, '0', VIA[1] / 2)


def netlist(tag, segs, lret, corner, cin, method='gear', rs=0):
    n = Netlist(tag)
    n.ibis('U7', 'drv', LIB, COMP, PIN, MODEL, ['u7_pad'], f'f0=400M n={NBITS}{CORNERS[corner]}')
    if rs:
        n.r('u7_pad', 'u7_rs', rs); n.tl('u7_rs', 'b1', F_CU[0], BREAK_MM * F_CU[1] * 1e-12)
    else:
        n.tl('u7_pad', 'b1', F_CU[0], BREAK_MM * F_CU[1] * 1e-12)
    via(n, 'b1', 'v1')
    node, k = 'v1', 0
    # return-path inductance where the reference plane changes: at the U7 via (In1 GND -> In6 1V2), at the
    # 1V2 / 3V3 split and at the U11 via (In6 3V3 -> GND); series L in the signal path (loop inductance)
    if lret and segs[0][0] == 'ref' and len(segs) > 1:
        lpar(n, node, 'lr0', lret); node = 'lr0'
    for i, (kind, mm) in enumerate(segs):
        if kind == 'rs':            # mid-route resistor on F.Cu: via up, 0.5 mm, R, 0.5 mm, via down
            k += 1; via(n, node, f'm{k}a'); n.tl(f'm{k}a', f'm{k}b', F_CU[0], 0.5 * F_CU[1] * 1e-12)
            n.r(f'm{k}b', f'm{k}c', mm); n.tl(f'm{k}c', f'm{k}d', F_CU[0], 0.5 * F_CU[1] * 1e-12)
            via(n, f'm{k}d', f'm{k}e'); node = f'm{k}e'; continue
        z, ps = STRIP if kind == 'ref' else GAP
        if lret and kind == 'gap' and i < len(segs) - 1:
            k += 1; lpar(n, node, f'lr{k}', lret); node = f'lr{k}'
        k += 1; n.tl(node, f's{k}', z, mm * ps * 1e-12); node = f's{k}'
    if lret and len(segs) > 1:
        lpar(n, node, 'lrz', lret); node = 'lrz'
    via(n, node, 'emmc')
    n.c('emmc', '0', cin)
    n.tl('emmc', 'pu', F_CU[0], STUB_MM * F_CU[1] * 1e-12)
    n.r('pu', 'vccq', 10e3)
    n.lines.append(f'Vq vccq 0 {VCCQ}')
    n.directive('.options method=gear maxord=2 reltol=1e-4' if method == 'gear' else '.options method=trap reltol=1e-4')
    n.directive(f'.tran 1p {NBITS * UI + 2e-9:.6g}')
    return n


def run_point(args):
    tag, cir, cir_trap = args
    t, w = spice.ngspice(cir, ['xu7.die0', 'emmc'], os.path.join(WORK, tag + '.dat'))
    if t[-1] < NBITS * UI:          # 'timestep too small': retry with the trapezoidal method
        t, w = spice.ngspice(cir_trap, ['xu7.die0', 'emmc'], os.path.join(WORK, tag + '.dat'))
    if t[-1] < NBITS * UI:          # last resort: 2 ps print step (changes ngspice's step control)
        loose = cir[:-4] + '_2p.cir'
        open(loose, 'w').write(open(cir).read().replace('.tran 1p', '.tran 2p'))
        t, w = spice.ngspice(loose, ['xu7.die0', 'emmc'], os.path.join(WORK, tag + '.dat'))
    if t[-1] < NBITS * UI: sys.exit(f'{tag}: ngspice stopped at {t[-1]*1e9:.1f} ns')
    ph, tr, lab, m = eye.analyse(t, w['xu7.die0'], w['emmc'], UI, MASK)
    return tag, ph, tr, lab, m


def validate():
    """Driver (package removed) into 50 ohm to GND vs the model's V-t table (V_fixture = 0): levels and t20-80."""
    from kicad_ibis.sch import Sch
    os.makedirs(WORK, exist_ok=True)
    s = Sch('../models'); s.row('validate')
    s.ibis('drv', ('agilex5_hps_sdmmc.ibs', COMP), PIN, MODEL, 'o', 'ton=3n toff=3n td=1n n=1', 'RECTDRIVER')
    s.r('o', 'GND', 50); s.text('.tran 1p 8n', 25.4, 15.24)
    sch = os.path.join(WORK, 'validate.kicad_sch'); s.write(sch)
    print('\n'.join(spice.export(sch)))
    for f in glob.glob(os.path.join(WORK, 'validate_ibis', '*.cache')): spice.strip_package(f)
    t, w = spice.ngspice(os.path.join(WORK, 'validate.cir'), ['o'], os.path.join(WORK, 'validate.dat'))
    v = w['o']; out = ['| edge | V start / end, IBIS (mV) | V end, KiCad (mV) | t20-80 IBIS (ps) | t20-80 KiCad (ps) |',
                       '|---|---|---|---|---|']
    for edge, sel in (('Rising', t < 4e-9), ('Falling', t >= 4e-9)):
        ti, vi = ibisfix.waveform(LIB, MODEL, edge)
        tk, vk = t[sel], v[sel]
        _, d_i = ibisfix.t2080(ti, vi); _, d_k = ibisfix.t2080(tk, vk)
        out.append(f'| {edge.lower()} | {vi[0]*1e3:.0f} / {vi[-1]*1e3:.0f} | {vk[-1]*1e3:.0f} | {d_i*1e12:.1f} | {d_k*1e12:.1f} |')
    os.makedirs(RES, exist_ok=True)
    open(os.path.join(RES, 'validate_driver.md'), 'w').write('\n'.join(out) + '\n'); print('\n'.join(out))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--validate', action='store_true'); a = ap.parse_args()
    if a.validate: return validate()
    os.makedirs(WORK, exist_ok=True); os.makedirs(RES, exist_ok=True)
    cache = KibisCache(os.path.join(WORK, 'kibis'))
    pts = {}
    for case, c in case_list():
        for corner in CORNERS:
            for cname, cin in CIN.items():
                pts[f'{case}_{corner}_{cname}'] = (case, corner, cname, netlist(case, c['segs'], c['lret'], corner, cin, rs=c.get('rs', 0)),
                                                    netlist(case, c['segs'], c['lret'], corner, cin, 'trap', c.get('rs', 0)))
    cache.resolve([e for p in pts.values() for e in p[3].ib])
    jobs = [(tag, p[3].write(os.path.join(WORK, tag + '.cir'), cache), p[4].write(os.path.join(WORK, tag + '_trap.cir'), cache))
            for tag, p in pts.items()]
    import matplotlib; matplotlib.use('Agg')
    rows = []
    with ProcessPoolExecutor(8) as ex:
        for tag, ph, tr, lab, m in ex.map(run_point, jobs):
            case, corner, cname = pts[tag][:3]
            rows.append(dict(case=case, corner=corner, cin=cname,
                             **{k: round(float(v), 1) for k, v in m.items() if k not in ('top', 'bot')}))
            if corner == 'max' and cname == '2p' or case.startswith('bad'):
                eye.save(os.path.join(RES, f'eye_{tag}.png'), ph, tr, lab, m, MASK, UI, title=f'{tag} (eMMC pin)')
    rows.sort(key=lambda r: ([c for c, _ in case_list()].index(r['case']), r['corner'], r['cin']))
    keys = list(rows[0])
    with open(os.path.join(RES, 'summary.csv'), 'w', newline='') as f:
        wr = csv.DictWriter(f, keys); wr.writeheader(); wr.writerows(rows)
    cols = ['case', 'corner', 'cin', 'eh_mV', 'ew_mask_ps', 't_margin_ps', 'v_margin_mV', 'vmax_mV', 'vmin_mV', 'delay_ps']
    md = ['| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)] + \
         ['| ' + ' | '.join(str(r[c]) for c in cols) + ' |' for r in rows]
    open(os.path.join(RES, 'summary.md'), 'w').write('\n'.join(md) + '\n'); print('\n'.join(md))


if __name__ == '__main__':
    main()
