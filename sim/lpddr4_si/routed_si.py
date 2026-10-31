"""SI of the routed LPDDR4 nets: each net's real copper (extract_routes.py -> work/routes.json) between the IBIS
buffers of the two ends, every net, both directions, three corners.

  $KICAD_APPRUN python3.11 extract_routes.py            # board -> work/routes.json
  python3 corner_models.py                              # models/min/, models/max/ (corner files)
  KICAD_APPRUN=.../AppRun python3 routed_si.py [-j 12]  # -> results/routed.csv, eye_routed_*.png
  python3 routed_report.py                              # -> results/routed.md
  ... routed_si.py --only 'r1600_min_ca_odt80__cs' -j 1  # one netlist (time it with /usr/bin/time -v first)
  ... routed_si.py --resume                             # skip the netlists already in results/routed.csv

Per net the graph from the board becomes the netlist: every track / arc piece a lossless line (Z0 and ps/mm by
layer, all LPDDR4 copper is 0.10 mm), every via an L/C (L by the span between the layers it joins, 0.4 pF incl.
the stub) with T-branches as routed. Uncoupled: no crosstalk and no meander self-coupling. Buffers, masks and
limits as run_si.py (README.md). min/max use the corner model files (corner_models.py) simulated at typ: KiCad's own
vcc=MIN/MAX keywords are right only into the 50 ohm V-t fixture (run_si.py --validate-corners).

Rows are appended to results/routed.csv as each netlist finishes, so a stopped run can be resumed (--resume); only the
worst eye per point kind is kept in memory for the PNGs.

Points: 1600 MT/s typ/min/max; DQ read with the DRAM's 40 ohm (all corners) and 48 ohm (typ) drive; CA/CS/CKE/CK
into CA_ODT_80 (typ/min/max) and CA_ODT_60 (typ); 2133 MT/s typ (headroom).
"""
import argparse, csv, json, os, re, sys, time
from concurrent.futures import ProcessPoolExecutor
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../../tools/kicad_ibis_simulation'))
from kicad_ibis import spice, eye
from kicad_ibis.fastnet import Netlist, KibisCache

WORK, RES = os.path.join(HERE, 'work'), os.path.join(HERE, 'results')
AGX = (os.path.join(HERE, 'models', 'agilex5_lpddr4.ibs'), 'Agilex5_A5EB013BB23BE6S')
MEM = (os.path.join(HERE, 'models', 'w66_lpddr4.ibs'), 'W66CL2NQUAFJ')
AGX_TX, AGX_RX = 'lvstl11_io_s3r40c_doff', 'lvstl11_in_e0g50c'
NBITS, TAIL = 150, 2e-9
VDDQ = 1.1
MASK = {'dq_write': ('rect', 140e-3, 0.22), 'ca': ('rect', 175e-3, 0.30), 'dq_read': ('diamond', 140e-3, 0.42)}
LIMIT = {'dq_write': (-0.4, 1.5), 'ca': (-0.4, 1.5), 'dq_read': (-0.3, VDDQ + 0.25)}
CORNERS = {'typ': 'models', 'min': 'models/min', 'max': 'models/max'}   # corner files, all simulated at typ
KEYS = ['point', 'net', 'kind', 'rx', 'where', 'eh_mV', 'ew_mask_ps', 'v_margin_mV', 't_margin_ps', 'vmax_mV',
        'vmin_mV', 'limits_ok', 'delay_ps', 'error']


def corner_lib(lib, corner):
    """(file, component) of a model in the corner's folder."""
    path = os.path.join(HERE, CORNERS[corner], os.path.basename(lib[0]))
    if not os.path.exists(path): sys.exit(f'{path} missing: run corner_models.py')
    return (path, lib[1])

# 0.10 mm lines (kicad_ibis.zsolve): Z0; ps/mm from the board's tuning profile (the delays the routing is matched to)
Z = {'F.Cu': 58.6, 'B.Cu': 58.6, 'In2.Cu': 53.8, 'In5.Cu': 53.8}
PS = {'F.Cu': 6.1, 'B.Cu': 6.1, 'In2.Cu': 7.08, 'In5.Cu': 7.08}
DEPTH = {'F.Cu': 0.0, 'In1.Cu': 0.1, 'In2.Cu': 0.24, 'In3.Cu': 0.6, 'In4.Cu': 0.95, 'In5.Cu': 1.31, 'In6.Cu': 1.45,
         'B.Cu': 1.55}   # mm, approximate (JLC08161H-3313)
VIA_C = 0.40e-12


def via_l(a, b):   # as sim/lpddr4_si: F.Cu <-> In2 (and its mirror In5 <-> B.Cu) 0.15 nH, longer spans 0.50 nH
    span = abs(DEPTH[a] - DEPTH[b])
    return 0.0 if span < 1e-6 else 0.15e-9 if span < 0.35 else 0.50e-9


def channel(n, net, R, p, end_nets):
    """Copper of one net into netlist n; node names prefixed p. end_nets: {(ref, ball): netlist node of the pin}."""
    node = lambda k: f'{p}_{k.replace(",", "_").replace(".", "")}'
    for s in R['segs']:
        n.tl(node(s['a']), node(s['b']), Z[s['layer']], max(s['mm'], 1e-4) * PS[s['layer']] * 1e-12)
    pad_of_via = {v: pd for pd in R['pads'] for v in pd['vias']}
    for v in R['vias']:
        att = [(lay, node(k)) for lay, k in v['att']]
        if v['id'] in pad_of_via:            # via in pad: the pad (F.Cu) is one more attachment
            pd = pad_of_via[v['id']]; att.append(('F.Cu', end_nets[(pd['ref'], pd['ball'])]))
        cnt = {}
        for lay, _ in att: cnt[lay] = cnt.get(lay, 0) + 1
        hub_layer = max(cnt, key=lambda l: (cnt[l], DEPTH[l]))
        hub = f'{p}_{v["id"]}'
        n.c(hub, '0', VIA_C)
        for lay, nd in att:
            L = via_l(lay, hub_layer)
            if L: n.l(nd, hub, L); n.r(nd, hub, 200.0)   # 200 ohm across L: damps the 10+ GHz tanks
            else: n.r(nd, hub, 1e-3)
    for pd in R['pads']:                     # F.Cu track ends inside the pad
        for k in pd['att']: n.r(end_nets[(pd['ref'], pd['ball'])], node(k), 1e-3)


def build(group, direction, corner, rate, nets, R, odt=80, pd=40):
    """One netlist: every net of the group, uncoupled. Returns (Netlist, [(net, kind, drv ref, [(rx ref, pin node)])])."""
    ui = 1e-6 / rate
    n = Netlist(f'{group} {direction} {corner} {rate:g}')
    prbs = f'f0={rate:g}M n={NBITS}'
    agx, mem = corner_lib(AGX, corner), corner_lib(MEM, corner)
    meta = []
    for i, net in enumerate(nets):
        r = R[net]; p = f'c{i}'
        ends = {(d['ref'], d['ball']): f'{p}_{d["ref"].lower()}_{d["ball"].lower()}' for d in r['pads']}
        u7 = [k for k in ends if k[0] == 'U7'][0]; u12 = [k for k in ends if k[0] == 'U12']
        channel(n, net, r, p, ends)
        if direction == 'write':             # DQ write, CA: FPGA drives
            n.ibis(f'd{i}', 'drv', *agx, u7[1], AGX_TX, [ends[u7]], prbs)
            rxs = []
            for j, k in enumerate(u12):
                model = 'ODT_48' if group.startswith('byte') else f'CA_ODT_{odt}'
                n.ibis(f'r{i}_{j}', 'rx', *mem, k[1], model, [ends[k]]); rxs.append((f'r{i}_{j}', ends[k]))
            meta.append((net, 'dq_write' if group.startswith('byte') else 'ca', f'd{i}', rxs))
        else:                                # DQ read: DRAM drives, FPGA 50 ohm ODT
            n.ibis(f'd{i}', 'drv', *mem, u12[0][1], f'PD{pd}_ODT80_VOH25', [ends[u12[0]]], prbs)
            n.ibis(f'r{i}_0', 'rx', *agx, u7[1], AGX_RX, [ends[u7]])
            meta.append((net, 'dq_read', f'd{i}', [(f'r{i}_0', ends[u7])]))
    # keep only the analysed vectors: ngspice otherwise stores every node of the route graphs (GBs per run)
    n.directive('.save ' + ' '.join(f'v({v})' for _, _, d, rxs in meta
                                    for v in [f'x{d}.die0'] + [x for r, pin in rxs for x in (pin, f'x{r}.die0')]))
    n.directive('.options method=gear maxord=2 reltol=1e-4')
    n.directive(f'.tran 1p {NBITS * ui + TAIL:.6g}')
    return n, meta


def run_point(job):
    tag, cir, meta, rate, plot = job
    ui = 1e-6 / rate
    vecs = []
    for net, kind, drv, rxs in meta:
        vecs.append(f'x{drv}.die0')
        for ref, pin in rxs: vecs += [pin, f'x{ref}.die0']
    dat = cir[:-4] + '.dat'
    t, w = spice.ngspice(cir, vecs, dat)
    os.remove(dat)   # tens of MB each; the rows below are what is kept
    if t[-1] < NBITS * ui: return [dict(point=tag, net='*', error=f'ngspice stopped at {t[-1]*1e9:.1f} ns')]
    rows = []
    for net, kind, drv, rxs in meta:
        phi, bits = eye.stimulus_bits(t, w[f'x{drv}.die0'], ui, TAIL)
        lo, hi = LIMIT[kind]
        for ref, pin in rxs:
            for node, where in ((pin, 'ball'), (f'x{ref}.die0', 'die')):
                v = w[node]
                ph, tr, lab, lag = eye.fold(t, v, phi, bits, ui, 12)
                m = eye.metrics(ph, tr, lab, MASK[kind], ui)
                seg = v[t > 12 * ui]
                rows.append(dict(point=tag, net=net, kind=kind, rx=ref, where=where, eh_mV=m['eh_mV'],
                                 ew_mask_ps=m['ew_mask_ps'], v_margin_mV=m['v_margin_mV'], t_margin_ps=m['t_margin_ps'],
                                 vmax_mV=seg.max() * 1e3, vmin_mV=seg.min() * 1e3,
                                 limits_ok=bool(lo <= seg.min() and seg.max() <= hi), delay_ps=lag * 1e12))
                if plot and where == 'die':
                    m.update(vmax_mV=seg.max() * 1e3, vmin_mV=seg.min() * 1e3)
                    rows[-1]['_eye'] = (ph, tr, lab, m)
    return rows


def points(R):
    byte = {b: [f'dq{i}' for i in range(8 * b, 8 * b + 8)] + [f'dm{b}', f'dqs{b}_P', f'dqs{b}_N'] for b in range(4)}
    ca = [f'ca{i}' for i in range(6)] + ['cke', '~{cs}', 'ck_P', 'ck_N']
    pts = []
    for rate, corners in ((1600, ('typ', 'min', 'max')), (2133.333, ('typ',))):
        for c in corners:
            for b, nets in byte.items():
                pts.append((f'r{rate:.0f}_{c}_byte{b}_w', f'byte{b}', 'write', c, rate, nets, {}))
                pts.append((f'r{rate:.0f}_{c}_byte{b}_r40', f'byte{b}', 'read', c, rate,
                            [x for x in nets if not x.startswith('dm')], dict(pd=40)))
                if c == 'typ' and rate == 1600:
                    pts.append((f'r{rate:.0f}_{c}_byte{b}_r48', f'byte{b}', 'read', c, rate,
                                [x for x in nets if not x.startswith('dm')], dict(pd=48)))
            pts.append((f'r{rate:.0f}_{c}_ca_odt80', 'ca', 'write', c, rate, ca, dict(odt=80)))
            if c == 'typ' and rate == 1600:
                pts.append((f'r{rate:.0f}_{c}_ca_odt60', 'ca', 'write', c, rate, ca, dict(odt=60)))
    missing = sorted({n for *_, nets, _ in pts for n in nets} - set(R))
    if missing: sys.exit(f'not in routes.json: {missing}')
    return pts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-j', type=int, default=12)
    ap.add_argument('--only', help='regex on "<point>__<net>": run only those netlists (e.g. to time one alone)')
    ap.add_argument('--resume', action='store_true', help='keep results/routed.csv and skip the netlists in it')
    a = ap.parse_args()
    spice.check()
    os.makedirs(WORK, exist_ok=True); os.makedirs(RES, exist_ok=True)
    R = json.load(open(os.path.join(WORK, 'routes.json')))
    cache = KibisCache(os.path.join(WORK, 'kibis'))
    out = os.path.join(RES, 'routed.csv')
    done = set()
    if a.resume and os.path.exists(out):
        done = {(r['point'], r['net']) for r in csv.DictReader(open(out)) if not r.get('error')}
    # one netlist per net: the nets are uncoupled, and in one netlist every net runs at the timestep of the busiest
    # edge of all of them (a whole byte: > 1 h; each net alone: ~15 s)
    built = []
    for tag, group, direction, corner, rate, nets, kw in points(R):
        for net in nets:
            if (tag, net) in done or (a.only and not re.search(a.only, f'{tag}__{net}')): continue
            n, meta = build(group, direction, corner, rate, [net], R, **kw)
            built.append((tag, re.sub(r'\W', '', net), n, meta, rate))
    if not built: return print('nothing to run')
    print('KIBIS conversions:', cache.resolve([e for *_, n, _, _ in built for e in n.ib], jobs=6), flush=True)
    jobs = [(tag, n.write(os.path.join(WORK, f'{tag}__{nm}.cir'), cache), meta, rate, True)
            for tag, nm, n, meta, rate in built]
    print(len(jobs), 'netlists', f'({len(done)} done before)' if done else '', flush=True)
    import matplotlib; matplotlib.use('Agg')
    if not (a.resume and os.path.exists(out)):
        with open(out, 'w', newline='') as f: csv.DictWriter(f, KEYS).writeheader()
    worst, nrow, nerr, t0 = {}, 0, 0, time.time()
    with ProcessPoolExecutor(a.j) as ex:
        for k, rows in enumerate(ex.map(run_point, jobs, chunksize=1)):
            for r in rows:                    # only the worst eye per (rate, kind) stays in memory
                e = r.pop('_eye', None)
                if e is None or 'error' in r: continue
                key = (r['point'].split('_')[0], r['kind'])
                if key not in worst or r['v_margin_mV'] < worst[key][0]['v_margin_mV']: worst[key] = (r, e)
            with open(out, 'a', newline='') as f:     # appended as each netlist finishes: a stopped run resumes
                csv.DictWriter(f, KEYS, extrasaction='ignore').writerows(rows)
            nrow += len(rows); nerr += sum('error' in r for r in rows)
            if (k + 1) % 20 == 0 or k + 1 == len(jobs):
                print(f'{k + 1}/{len(jobs)} netlists, {time.time() - t0:.0f} s', flush=True)
    if nerr: print('ERRORS:', nerr, 'rows (see the error column of results/routed.csv)')
    for (rate, kind), (r, (ph, tr, lab, m)) in worst.items():
        ui = 1e-6 / (1600 if rate == 'r1600' else 2133.333)
        eye.save(os.path.join(RES, f'eye_routed_{rate}_{kind}.png'), ph, tr, lab, m, MASK[kind], ui,
                 title=f'worst {kind}: {r["net"]} {r["point"]} (die)')
    print(f'{nrow} rows -> results/routed.csv')


if __name__ == '__main__':
    main()
