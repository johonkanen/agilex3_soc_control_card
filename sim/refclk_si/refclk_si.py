"""LPDDR4 EMIF refclk (100 MHz LVDS oscillator U9 -> AC coupling -> bias/termination -> U7 B55/A58) with KiCad +
ngspice, using the Agilex 5 IBIS receiver model and a data-sheet LVDS source (no IBIS model of the Abracon AX3).

  KICAD_APPRUN=.../squashfs-root/AppRun python3 refclk_si.py [--show CASE]

Circuit (clock sheet, 2026-10-28):
  U9 OUT/nOUT -> R25/R26 33R -> C8/C9 100n -> B.Cu 9.6 mm -> via -> U7 B55/A58 (tds11_in_e0t100, 1.1 V TDS)
  R27/R28 50R from each leg to VICM_REFCLK = 1V1 x R245 3k9 / (R244 1k + R245 3k9), C249 1u + C250 100n
Source (AX3 data sheet, LVDS @ 3.3 V): VOD 0.25/0.35/0.45 V into 100 ohm, Tr/Tf 20-80 % 0.15-0.4 ns, VOS ~1.25 V.
  'I': ideal current-mode output (+-VOD/100 A, 10 k common-mode resistance per leg) - the worst case for a low load
  'V': 100 ohm differential Thevenin source (VOS +- VOD per leg behind 50 ohm), open-circuit swing 2 x VOD
Termination cases (RD OCT = the Agilex on-chip 100 ohm differential termination, +-40 %: 60/100/140 ohm, placed at
the pins; KiCad's IBIS parser drops the [R Series] model that carries it):
  built_rd60/100/140  R27/R28 50R + RD OCT on (the Quartus EMIF default, PHY_TERM_X_R_T_REFCLK_INPUT_OHM = RT_DIFF)
  rtoff               R27/R28 50R only (RT_OFF)
  rdonly_rd60/100/140 RD OCT only, R27/R28 changed to 1k (bias only)
Limits (Agilex 5 data sheet 813918, Table 42, True Differential Signaling 1.1 V receiver): VID 100-454 mV,
VICM(DC) 0.80-0.95 V; no over/undershoot beyond 1.177 / 0.573 V.
"""
import argparse, csv, json, os, sys
from concurrent.futures import ProcessPoolExecutor
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../../tools/kicad_ibis_simulation'))
from kicad_ibis import sch, spice

WORK, RES = os.path.join(HERE, 'work'), os.path.join(HERE, 'results')
AGX = ('agilex5_lpddr4.ibs', 'Agilex5_A5EB013BB23BE6S')          # sim/lpddr4_si/models (prep_models.py)
PERIOD = 10e-9
TRAN = 80e-9
LINE_MM, PS_MM, ZLINE = 9.6, 6.1, 50.0                             # B.Cu 0.1 mm, loosely coupled legs
VIA = (0.5e-9, 0.4e-12)
VOS = 1.25
VID_MIN, VID_MAX, VICM_MIN, VICM_MAX, VABS_MIN, VABS_MAX = 0.100, 0.454, 0.80, 0.95, 0.573, 1.177
TERMS = [('built_rd60', 50, 60), ('built_rd100', 50, 100), ('built_rd140', 50, 140), ('rtoff', 50, None),
         ('rdonly_rd60', 1000, 60), ('rdonly_rd100', 1000, 100), ('rdonly_rd140', 1000, 140)]
VODS = (0.25, 0.35, 0.45)


def build(src, t2080, path):
    s = sch.Sch(models='../../lpddr4_si/models', project='refclk_si')
    s.text(f'.tran 1p {TRAN * 1e9:g}n\n.options method=gear maxord=2 reltol=1e-4', 25.4, 15.24)
    s.row('supplies'); s.sym('Simulation_SPICE', 'VDC', 'V', {'1': 'v1v1', '2': 'GND'}, '1.1',
                             {'Sim.Device': 'V', 'Sim.Type': 'DC', 'Sim.Pins': '1=+ 2=-', 'Sim.Params': 'dc=1.1'})
    s.sym('Simulation_SPICE', 'VDC', 'V', {'1': 'vos', '2': 'GND'}, f'{VOS}',
          {'Sim.Device': 'V', 'Sim.Type': 'DC', 'Sim.Pins': '1=+ 2=-', 'Sim.Params': f'dc={VOS}'})
    tr = t2080 / 0.6                                                   # 0-100 % ramp of the PULSE source
    pw = PERIOD / 2 - tr
    meta = {}
    for vod in VODS:
        for term, rt, rd in TERMS:
            k = f'v{int(vod * 1000)}_{term}'
            s.row(f'{k}: {src} source VOD {vod} V, {t2080 * 1e12:.0f} ps, R27/R28 {rt} ohm, RD OCT {rd or "off"}')
            p, n = f'{k}_op', f'{k}_on'
            # each square wave = PULSE(0 -> +A at 1 ns) + PULSE(0 -> -A half a period later): 0 at the operating
            # point, so the AC-coupling caps start at the steady-state (zero-mean) charge
            def pulse(kind, nets, amp, td):
                return s.sym('Simulation_SPICE', f'{kind}PULSE', kind, nets, f'{amp:g}',
                             {'Sim.Device': kind, 'Sim.Type': 'PULSE', 'Sim.Pins': '1=+ 2=-',
                              'Sim.Params': f'y1=0 y2={amp:g} td={sch.eng(td)} tr={sch.eng(tr)} tf={sch.eng(tr)} '
                                            f'tw={sch.eng(pw)} per={sch.eng(PERIOD)}'})
            if src == 'I':      # current steering between the legs (+-VOD/100), 10 k to VOS per leg
                i = vod / 100
                pulse('I', {'1': p, '2': n}, i, 1e-9); pulse('I', {'1': p, '2': n}, -i, 1e-9 + PERIOD / 2)
                s.r(p, 'vos', 10e3); s.r(n, 'vos', 10e3)
            else:               # per leg VOS +- VOD behind 50 ohm (VOD across 100 ohm)
                for leg, sgn in ((p, -1), (n, 1)):
                    pulse('V', {'1': leg + 'a', '2': 'vos'}, sgn * vod, 1e-9)
                    pulse('V', {'1': leg + 'i', '2': leg + 'a'}, -sgn * vod, 1e-9 + PERIOD / 2)
                    s.r(leg + 'i', leg, 50)
            rx = {}
            for leg, pin in ((p, 'A58'), (n, 'B55')):    # U9 OUT -> refclk_N (A58), nOUT -> refclk_P (B55)
                s.r(leg, leg + '_r', 33); s.c(leg + '_r', leg + '_c', 100e-9)
                s.tl(leg + '_c', leg + '_l', ZLINE, LINE_MM * PS_MM * 1e-12)
                s.via(leg + '_l', leg + '_pin', *VIA)
                s.r(leg + '_pin', k + '_vicm', rt)
                rx[pin] = s.ibis('rx', AGX, pin, 'tds11_in_e0t100', leg + '_pin')
            s.r('v1v1', k + '_vicm', 1e3); s.r(k + '_vicm', 'GND', 3.9e3)
            s.c(k + '_vicm', 'GND', 1e-6); s.c(k + '_vicm', 'GND', 100e-9)
            if rd: s.r(p + '_pin', n + '_pin', rd)
            meta[k] = dict(vod=vod, term=term, rt=rt, rd=rd, P=rx['B55'], N=rx['A58'],
                           Ppin=n + '_pin', Npin=p + '_pin', vicm=k + '_vicm')
    s.write(path)
    return meta


def measure(t, vp, vn):
    """Settled clock after 30 ns. vid = settled |Vp - Vn| (last 20 % of each half period; the DC VID of the data
    sheet), vid_min = lowest |Vp - Vn| from 40 % of the half period on (dips from ringing), VICM, abs min/max per leg,
    differential edge time between -60 % and +60 % of the settled level (= 20-80 % of the swing)."""
    sel = t > 30e-9
    t, vp, vn = t[sel], vp[sel], vn[sel]
    vd = vp - vn; vc = (vp + vn) / 2
    ph = ((t - 1e-9) % (PERIOD / 2)) / (PERIOD / 2)
    vs = np.median(np.abs(vd[ph > 0.8]))
    vid_min = np.abs(vd[ph > 0.4]).min()
    a, b = -0.6 * vs, 0.6 * vs
    up = np.nonzero((vd[:-1] < a) & (vd[1:] >= a))[0]
    rise = [t[i + np.argmax(vd[i:] >= b)] - t[i] for i in up if (vd[i:] >= b).any()]
    return dict(vid_mV=vs * 1e3, vid_min_mV=vid_min * 1e3, vicm_mV=vc.mean() * 1e3,
                vmin_mV=min(vp.min(), vn.min()) * 1e3, vmax_mV=max(vp.max(), vn.max()) * 1e3,
                t2080_ps=np.median(rise) * 1e12 if rise else float('nan'))


def run(job):
    tag, meta = job
    vecs = []
    for k, m in meta.items(): vecs += [f"x{m['P'].lower()}.die0", f"x{m['N'].lower()}.die0"]
    dat = os.path.join(WORK, tag + '.dat')
    if os.environ.get('SI_REUSE') and os.path.exists(dat): t, w = spice.load(dat, vecs)
    else: t, w = spice.ngspice(os.path.join(WORK, tag + '.cir'), vecs, dat)
    rows = []
    for k, m in meta.items():
        r = measure(t, w[f"x{m['P'].lower()}.die0"], w[f"x{m['N'].lower()}.die0"])
        ok = (VID_MIN * 1e3 <= r['vid_min_mV'] and r['vid_mV'] <= VID_MAX * 1e3 and
              VICM_MIN * 1e3 <= r['vicm_mV'] <= VICM_MAX * 1e3 and
              r['vmin_mV'] >= VABS_MIN * 1e3 and r['vmax_mV'] <= VABS_MAX * 1e3)
        rows.append(dict(point=tag, case=k, src=tag.split('_')[0], edge_ps=tag.split('_')[1], vod_mV=m['vod'] * 1e3,
                         term=m['term'], **{x: round(y, 1) for x, y in r.items()}, ok=ok))
    return rows


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--show', help='open one case, e.g. I_400:v250_built_rd60')
    a = ap.parse_args()
    spice.check(); os.makedirs(WORK, exist_ok=True); os.makedirs(RES, exist_ok=True)
    if a.show: return show(a.show)
    jobs = []
    for src in ('I', 'V'):
        for t2080 in (400e-12, 150e-12):
            tag = f'{src}_{int(t2080 * 1e12)}'
            if os.environ.get('SI_REUSE') and os.path.exists(os.path.join(WORK, tag + '.dat')):
                jobs.append((tag, json.load(open(os.path.join(WORK, tag + '.json'))))); continue
            meta = build(src, t2080, os.path.join(WORK, tag + '.kicad_sch'))
            json.dump(meta, open(os.path.join(WORK, tag + '.json'), 'w'))
            msgs = spice.export(os.path.join(WORK, tag + '.kicad_sch'))
            if msgs: print(tag, 'kicad-cli:', '; '.join(msgs))
            jobs.append((tag, meta))
    rows = []
    with ProcessPoolExecutor(4) as ex:
        for r in ex.map(run, jobs): rows += r
    with open(os.path.join(RES, 'results.csv'), 'w', newline='') as f:
        wr = csv.DictWriter(f, list(rows[0])); wr.writeheader(); wr.writerows(rows)
    report(rows)


def report(rows):
    out = ['| termination | source | VOD (mV) | VID settled (mV) | VID min after edge (mV) | VICM (mV) | Vmin / Vmax per leg (mV) | edge 20-80 (ps) | ok |',
           '|---|---|---|---|---|---|---|---|---|']
    for term, _, _ in TERMS:
        for src in ('I', 'V'):
            for vod in VODS:
                rs = [r for r in rows if r['term'] == term and r['src'] == src and r['vod_mV'] == vod * 1e3]
                out.append(f"| {term} | {src} | {vod * 1e3:.0f} | {np.mean([r['vid_mV'] for r in rs]):.0f} | "
                           f"{min(r['vid_min_mV'] for r in rs):.0f} | {np.mean([r['vicm_mV'] for r in rs]):.0f} | "
                           f"{min(r['vmin_mV'] for r in rs):.0f} / {max(r['vmax_mV'] for r in rs):.0f} | "
                           f"{min(r['t2080_ps'] for r in rs):.0f}-{max(r['t2080_ps'] for r in rs):.0f} | "
                           f"{'ok' if all(r['ok'] for r in rs) else '**FAIL**'} |")
    open(os.path.join(RES, 'results.md'), 'w').write('\n'.join(out) + '\n')
    print('\n'.join(out))


def show(spec):
    tag, k = spec.split(':')
    meta = json.load(open(os.path.join(WORK, tag + '.json')))
    vecs = []
    for kk, m in meta.items(): vecs += [f"x{m['P'].lower()}.die0", f"x{m['N'].lower()}.die0"]
    t, w = spice.load(os.path.join(WORK, tag + '.dat'), vecs)
    m = meta[k]; vp, vn = w[f"x{m['P'].lower()}.die0"], w[f"x{m['N'].lower()}.die0"]
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    s = t > 30e-9
    a1.plot(t[s] * 1e9, vp[s] * 1e3, label='B55 (P) die'); a1.plot(t[s] * 1e9, vn[s] * 1e3, label='A58 (N) die')
    for y in (VABS_MIN, VABS_MAX): a1.axhline(y * 1e3, color='r', ls=':')
    a1.set_ylabel('mV'); a1.legend(); a1.grid(alpha=.3); a1.set_title(f'{tag} {k}')
    a2.plot(t[s] * 1e9, (vp - vn)[s] * 1e3, 'k')
    for y in (VID_MIN, -VID_MIN, VID_MAX, -VID_MAX): a2.axhline(y * 1e3, color='r', ls=':')
    a2.set_ylabel('Vp - Vn (mV)'); a2.set_xlabel('ns'); a2.grid(alpha=.3)
    fig.tight_layout(); plt.show()


if __name__ == '__main__':
    main()
