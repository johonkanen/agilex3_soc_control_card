"""SI of the routed LPDDR4 nets: each net's real copper (extract_routes.py -> work/routes.json) between the IBIS
buffers of the two ends, every net, both directions, three corners.

  $KICAD_APPRUN python3.11 extract_routes.py            # board -> work/routes.json
  KICAD_APPRUN=.../AppRun python3 routed_si.py [-j 12]  # -> results/routed.csv, results/routed.md, eye_routed_*.png

Per net the graph from the board becomes the netlist: every track / arc piece a lossless line (Z0 and ps/mm by
layer, all LPDDR4 copper is 0.10 mm), every via an L/C (L by the span between the layers it joins, 0.4 pF incl.
the stub) with T-branches as routed. Uncoupled: no crosstalk and no meander self-coupling. Buffers, masks and
limits as run_si.py (README.md).

Points: 1600 MT/s typ/min/max; DQ read with the DRAM's 40 ohm (all corners) and 48 ohm (typ) drive; CA/CS/CKE/CK
into CA_ODT_80 (typ/min/max) and CA_ODT_60 (typ); 2133 MT/s typ (headroom).
"""
import argparse, csv, json, os, re, sys
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
CORNERS = {'typ': '', 'min': ' vcc=MIN rpin=MIN lpin=MIN cpin=MIN', 'max': ' vcc=MAX rpin=MAX lpin=MAX cpin=MAX'}

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
    cs = CORNERS[corner]; prbs = f'f0={rate:g}M n={NBITS}{cs}'
    meta = []
    for i, net in enumerate(nets):
        r = R[net]; p = f'c{i}'
        ends = {(d['ref'], d['ball']): f'{p}_{d["ref"].lower()}_{d["ball"].lower()}' for d in r['pads']}
        u7 = [k for k in ends if k[0] == 'U7'][0]; u12 = [k for k in ends if k[0] == 'U12']
        channel(n, net, r, p, ends)
        if direction == 'write':             # DQ write, CA: FPGA drives
            n.ibis(f'd{i}', 'drv', *AGX, u7[1], AGX_TX, [ends[u7]], prbs)
            rxs = []
            for j, k in enumerate(u12):
                model = 'ODT_48' if group.startswith('byte') else f'CA_ODT_{odt}'
                n.ibis(f'r{i}_{j}', 'rx', *MEM, k[1], model, [ends[k]], cs.strip()); rxs.append((f'r{i}_{j}', ends[k]))
            meta.append((net, 'dq_write' if group.startswith('byte') else 'ca', f'd{i}', rxs))
        else:                                # DQ read: DRAM drives, FPGA 50 ohm ODT
            n.ibis(f'd{i}', 'drv', *MEM, u12[0][1], f'PD{pd}_ODT80_VOH25', [ends[u12[0]]], prbs)
            n.ibis(f'r{i}_0', 'rx', *AGX, u7[1], AGX_RX, [ends[u7]], cs.strip())
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
    ap = argparse.ArgumentParser(); ap.add_argument('-j', type=int, default=12); a = ap.parse_args()
    spice.check()
    os.makedirs(WORK, exist_ok=True); os.makedirs(RES, exist_ok=True)
    R = json.load(open(os.path.join(WORK, 'routes.json')))
    cache = KibisCache(os.path.join(WORK, 'kibis'))
    # one netlist per net: the nets are uncoupled, and in one netlist every net runs at the timestep of the busiest
    # edge of all of them (a whole byte: > 1 h; each net alone: ~15 s)
    built = []
    for tag, group, direction, corner, rate, nets, kw in points(R):
        for net in nets:
            n, meta = build(group, direction, corner, rate, [net], R, **kw)
            built.append((tag, re.sub(r'\W', '', net), n, meta, rate))
    print('KIBIS conversions:', cache.resolve([e for *_, n, _, _ in built for e in n.ib], jobs=6), flush=True)
    jobs = [(tag, n.write(os.path.join(WORK, f'{tag}__{nm}.cir'), cache), meta, rate, True)
            for tag, nm, n, meta, rate in built]
    print(len(jobs), 'netlists', flush=True)
    import matplotlib; matplotlib.use('Agg')
    rows = []
    with ProcessPoolExecutor(a.j) as ex:
        for r in ex.map(run_point, jobs, chunksize=4): rows += r; print('.', end='', flush=True)
    print()
    errs = [r for r in rows if 'error' in r]
    if errs: print('ERRORS:', errs)
    rows = [r for r in rows if 'error' not in r]
    # worst eye per point kind (die) -> png
    worst = {}
    for r in rows:
        if '_eye' not in r: continue
        k = (r['point'].split('_')[0], r['kind'])
        if k not in worst or r['v_margin_mV'] < worst[k]['v_margin_mV']: worst[k] = r
    for (rate, kind), r in worst.items():
        ph, tr, lab, m = r['_eye']
        ui = 1e-6 / (1600 if rate == 'r1600' else 2133.333)
        eye.save(os.path.join(RES, f'eye_routed_{rate}_{kind}.png'), ph, tr, lab, m, MASK[kind], ui,
                 title=f'worst {kind}: {r["net"]} {r["point"]} (die)')
    keys = [k for k in rows[0] if k != '_eye']
    with open(os.path.join(RES, 'routed.csv'), 'w', newline='') as f:
        wr = csv.DictWriter(f, keys, extrasaction='ignore'); wr.writeheader(); wr.writerows(rows)
    print(f'{len(rows)} rows -> results/routed.csv')


if __name__ == '__main__':
    main()
