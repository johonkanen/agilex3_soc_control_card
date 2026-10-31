"""LPDDR4 SI sweep: gen_sch.py -> kicad-cli (KiCad's IBIS converter) -> ngspice (libngspice from the KiCad AppImage)
-> eyes, mask margins, over/undershoot -> results/. The generic parts live in tools/kicad_ibis_simulation (kicad_ibis).

  KICAD_APPRUN=.../squashfs-root/AppRun python3 run_si.py [--quick]

Writes results/results.csv, results/results.md and results/eye_*.png. Netlists and waveforms go to work/ (git-ignored).
"""
import argparse, csv, glob, json, os, subprocess, sys
from concurrent.futures import ProcessPoolExecutor
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../../tools/kicad_ibis_simulation'))
from kicad_ibis import spice, eye, ibisfix

WORK, RES = os.path.join(HERE, 'work'), os.path.join(HERE, 'results')
RATE = float(os.environ.get('SI_RATE', 1600))   # MT/s; the -6S EMIF IP allows 1600 and 2133
UI = 1e-6 / RATE
SKIP = 12            # start-up bits not used in the eye
TAIL = 2e-9          # .tran runs 2 ns past the last PRBS bit (gen_sch.py)
VDDQ = 1.1

# Rx masks. JEDEC JESD209-4 LPDDR4 rectangular masks for the DRAM inputs (as reproduced in TI SPRAD66B, 1600 column);
# for the FPGA read side TI's SoC-pad diamond (0.42 UI x 140 mV) is used as a proxy: Altera publishes no Rx mask.
MASK = {'dq_write': ('rect', 140e-3, 0.22), 'ca': ('rect', 175e-3, 0.30), 'dq_read': ('diamond', 140e-3, 0.42)}
# over/undershoot limits at the receiver: DRAM JEDEC DC abs max -0.4..1.5 V; Agilex 5 1.1 V HSIO (data sheet 813918
# Table 7): VCCIO+0.25 V for 100 % of the time ... nothing above VCCIO+0.40 V, undershoot -0.3 V
LIMIT = {'dq_write': (-0.4, 1.5), 'ca': (-0.4, 1.5), 'dq_read': (-0.3, VDDQ + 0.25)}


# ---------------------------------------------------------------------------------------------------------- netlists
def export(tag, gen_args):
    """gen_sch.py -> work/tag.kicad_sch -> kicad-cli spice netlist with the IBIS subcircuits copied next to it."""
    sch = os.path.join(WORK, tag + '.kicad_sch')
    subprocess.run([sys.executable, '-I', os.path.join(HERE, 'gen_sch.py'), sch, '--models', '../models'] + gen_args,
                   check=True, env=dict(os.environ))
    msgs = spice.export(sch, raw_kukd=bool(os.environ.get('SI_RAW_KUKD')))
    return msgs, json.load(open(os.path.join(WORK, tag + '.json')))


# -------------------------------------------------------------------------------------------------------------- sweep
def run_point(job):
    tag, gen_args, meta, plot = job
    cir = os.path.join(WORK, tag + '.cir')
    vecs = []
    for case, m in meta.items():
        vecs.append(f"x{m['drv'].lower()}.die0")
        for ref, pad in m['rx']: vecs += [pad, f"x{ref.lower()}.die0"]
    dat = os.path.join(WORK, tag + '.dat')
    if os.environ.get('SI_REUSE') and os.path.exists(dat) and os.path.getmtime(dat) > os.path.getmtime(cir):
        t, w = spice.load(dat, vecs)
    else:
        t, w = spice.ngspice(cir, vecs, dat)
    rows = []
    for case, m in meta.items():
        phi, bits = eye.stimulus_bits(t, w[f"x{m['drv'].lower()}.die0"], UI, TAIL)
        mask = MASK[m['kind']]; lo, hi = LIMIT[m['kind']]
        for ref, pad in m['rx']:
            for node, where in ((pad, 'ball'), (f"x{ref.lower()}.die0", 'die')):
                v = w[node]
                ph, tr, lab, lag = eye.fold(t, v, phi, bits, UI, SKIP)
                e = eye.metrics(ph, tr, lab, mask, UI)
                seg = v[t > SKIP * UI]
                row = dict(point=tag, case=case, rx=ref, where=where, delay_ps=lag * 1e12,
                           vmax_mV=seg.max() * 1e3, vmin_mV=seg.min() * 1e3, lim_lo_mV=lo * 1e3, lim_hi_mV=hi * 1e3,
                           limits_ok=bool(lo <= seg.min() and seg.max() <= hi),
                           **{k: v_ for k, v_ in e.items() if k not in ('top', 'bot')})
                row.update(dict(zip(('zdq', 'ldq', 'zca', 'via', 'corner'), gen_args_vals(gen_args))))
                rows.append(row)
                if plot and where == 'die':
                    e.update(vmax_mV=row['vmax_mV'], vmin_mV=row['vmin_mV'])
                    eye.save(os.path.join(RES, f'eye_{tag}_{case}_{ref}.png'), ph, tr, lab, e, mask, UI,
                             title=f'{case} {ref} die, {tag}')
    return rows


VARIANTS = {   # name: (models folder, gen_sch --corner keywords, V-t / V-I column of the file in that folder)
    'typ': ('models', 'typ', 1),
    'min_kw': ('models', 'min', 2), 'max_kw': ('models', 'max', 3),            # KiCad's vcc=MIN/MAX keywords
    'min_files': ('models/min', 'typ', 1), 'max_files': ('models/max', 'typ', 1),   # corner_models.py, at typ
}


def validate(variants=('typ',)):
    """Converted drivers (package removed) into RECTDRIVER loads to GND, per variant: into the 50 ohm fixture the
    levels and 20-80 % edges against the IBIS V-t tables of that corner, and into every load (48/60/80 ohm ODT,
    open) the DC high level against ibisfix.dc_high from the model's own V-I tables."""
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    lines, dcl = [], []
    for var in variants:
        folder, kw, col = VARIANTS[var]
        tag = 'validate' if var == 'typ' else f'validate_{var}'
        msgs, meta = export(tag, ['--validate', '--corner', kw, '--models', '../' + folder])
        for f in glob.glob(os.path.join(WORK, tag + '_ibis', '*.cache')):   # the V-t tables are at the die
            spice.strip_package(f)
        t, w = spice.ngspice(os.path.join(WORK, tag + '.cir'), [f'{k}_o' for k in meta], os.path.join(WORK, tag + '.dat'))
        fix = {k: m for k, m in meta.items() if m['load'] == 50}
        if var == 'typ':
            fig, axs = plt.subplots(1, len(fix), figsize=(4.2 * len(fix), 3.4), dpi=110)
        for n_, (k, m) in enumerate(fix.items()):
            v = w[f'{k}_o']; lib = os.path.join(HERE, folder, m['lib'])
            for edge, sel in (('Rising', t < 4.0e-9), ('Falling', t >= 4.0e-9)):
                ti, vi = ibisfix.waveform(lib, m['model'], edge, col=col)
                tk, vk = t[sel], v[sel]
                # the simulated edge: window around the swing, starting where the table's first sample would sit
                mid = (vi[0] + vi[-1]) / 2
                ic = np.argmax(vk > mid) if edge == 'Rising' else np.argmax(vk < mid)
                _, d_ic = ibisfix.t2080(ti, vi)
                tsim = tk[ic] - (ti[np.argmax(vi > mid) if edge == 'Rising' else np.argmax(vi < mid)])
                ts = tsim + ti; vs = np.interp(ts, tk, vk)
                _, d_k = ibisfix.t2080(ts, vs)
                lines.append(f"| {var} | {m['model']} | {edge.lower()} | {vi[0]*1e3:.0f} / {vi[-1]*1e3:.0f} | "
                             f"{vs[0]*1e3:.0f} / {vk[-1]*1e3:.0f} | {d_ic*1e12:.1f} | {d_k*1e12:.1f} |")
                if var == 'typ':
                    ax = axs[n_]
                    ax.plot(ti * 1e12, vi * 1e3, 'k', lw=1.2, label=f'IBIS {edge.lower()}')
                    ax.plot(ti * 1e12, vs * 1e3, '--', lw=1.2, label=f'KiCad {edge.lower()}')
                    ax.set_title(f"{m['model']} into 50 ohm to GND", fontsize=8); ax.set_xlabel('ps')
                    ax.set_ylabel('mV'); ax.grid(alpha=.3); ax.legend(fontsize=7); ax.set_xlim(0, min(ti[-1], 1.5e-9) * 1e12)
        if var == 'typ':
            fig.tight_layout(); fig.savefig(os.path.join(RES, 'validate_drivers.png')); plt.close(fig)
        dc_col = col if folder == 'models' else 1
        for k, m in meta.items():
            vk = float(np.interp(3.9e-9, t, w[f'{k}_o']))           # end of the 3 ns high
            ref = ibisfix.dc_high(os.path.join(HERE, folder, m['lib']), m['model'], dc_col, m['load'])
            dcl.append(f"| {var} | {m['model']} | {'open' if m['load'] > 1e5 else '%g' % m['load']} | "
                       f"{ref*1e3:.0f} | {vk*1e3:.0f} | {(vk-ref)*1e3:+.0f} |")
    hdr = ['| variant | driver model | edge | V start / end, IBIS (mV) | V start / end, KiCad (mV) | t20-80, IBIS (ps) | t20-80, KiCad (ps) |',
           '|---|---|---|---|---|---|---|']
    dch = ['| variant | driver model | load (ohm) | DC high from V-I (mV) | KiCad (mV) | KiCad - V-I (mV) |',
           '|---|---|---|---|---|---|']
    name = 'validate_drivers.md' if tuple(variants) == ('typ',) else 'validate_drivers_corners.md'
    text = ('Into the 50 ohm V-t fixture (package removed):\n\n' + '\n'.join(hdr + lines) +
            '\n\nDC high level into each load (package removed), against the model\'s own V-I tables:\n\n' +
            '\n'.join(dch + dcl) + '\n')
    open(os.path.join(RES, name), 'w').write(text)
    print(text)


def gen_args_vals(a):
    d = dict(zip(a[::2], a[1::2]))
    return (float(d.get('--zdq', 40)), float(d.get('--ldq', 20)), float(d.get('--zca', 40)), d.get('--via-dq', 'long'),
            d.get('--corner', 'typ'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quick', action='store_true', help='baseline 40/50 ohm, 20 mm only')
    ap.add_argument('--validate', action='store_true', help='only check the converted drivers against IBIS V-t tables')
    ap.add_argument('--validate-corners', action='store_true',
                    help='--validate at typ, min and max, with KiCad\'s corner keywords and with the corner files')
    ap.add_argument('--zsweep', action='store_true', help='DQ line 55-70 ohm (how narrow can the traces be)')
    ap.add_argument('--zlimit', action='store_true', help='DQ line 80-150 ohm (push past manufacturable widths until it fails)')
    ap.add_argument('--zfail', action='store_true', help='long, badly mismatched DQ lines: check that the eye analysis can fail')
    ap.add_argument('--casweep', action='store_true', help='everything at 0.10 mm: DQ 55 ohm, CA trunk 55/60 ohm')
    ap.add_argument('-j', type=int, default=6)
    a = ap.parse_args()
    spice.check()
    os.makedirs(WORK, exist_ok=True); os.makedirs(RES, exist_ok=True)
    if a.validate: return validate()
    if a.validate_corners: return validate(tuple(VARIANTS))
    pts = []
    for z in (40, 50):
        for l in ((20,) if a.quick else (16, 20, 22)):
            pts.append((f'z{z}_l{l}', ['--zdq', str(z), '--ldq', str(l), '--zca', str(z)], l == 20))
        if not a.quick:
            pts.append((f'z{z}_l20_shortvia', ['--zdq', str(z), '--ldq', '20', '--zca', str(z), '--via-dq', 'short'], False))
            for c in ('min', 'max'):
                pts.append((f'z{z}_l20_{c}', ['--zdq', str(z), '--ldq', '20', '--zca', str(z), '--corner', c], False))
    if a.zsweep:   # narrow DQ lines (CA as routed, 40 ohm)
        pts = [(f'zs{z}_l20' + ('' if c == 'typ' else f'_{c}'),
                ['--zdq', str(z), '--ldq', '20', '--zca', '40', '--corner', c], c == 'typ' and z in (60, 70))
               for z in (55, 60, 65, 70) for c in ('typ', 'min')]
    if a.zlimit:
        pts = [(f'zl{z}_l20' + ('' if c == 'typ' else f'_{c}'),
                ['--zdq', str(z), '--ldq', '20', '--zca', '40', '--corner', c], c == 'typ')
               for z in (80, 100, 120, 150) for c in ('typ', 'min')]
    if a.zfail:
        pts = [(f'zf{z}_l{l}', ['--zdq', str(z), '--ldq', str(l), '--zca', '40'], True)
               for z, l in ((55, 80), (100, 40), (100, 80), (150, 40), (150, 80))]
    if a.casweep:
        pts = [(f'zc{z}_l20' + ('' if c == 'typ' else f'_{c}'),
                ['--zdq', '55', '--ldq', '20', '--zca', str(z), '--corner', c], c == 'typ')
               for z in (55, 60) for c in ('typ', 'min', 'max')]
    if RATE != 1600: pts = [(f'r{RATE:g}_' + t, g, p) for t, g, p in pts]
    out = ('results_casweep' if a.casweep else 'results_zfail' if a.zfail else 'results_zlimit' if a.zlimit else 'results_zsweep' if a.zsweep else 'results') + ('' if RATE == 1600 else f'_{RATE:g}')
    jobs = []
    for tag, args, plot in pts:          # kicad-cli export is sequential (shared IBIS cache dir); ngspice in parallel
        if os.environ.get('SI_REUSE') and os.path.exists(os.path.join(WORK, tag + '.dat')):
            jobs.append((tag, args, json.load(open(os.path.join(WORK, tag + '.json'))), plot)); continue
        msgs, meta = export(tag, args)
        if msgs: print(tag, 'kicad-cli:', '; '.join(msgs))
        jobs.append((tag, args, meta, plot))
    rows = []
    with ProcessPoolExecutor(a.j) as ex:
        for r in ex.map(run_point, jobs): rows += r
    keys = list(rows[0])
    with open(os.path.join(RES, out + '.csv'), 'w', newline='') as f:
        wr = csv.DictWriter(f, keys); wr.writeheader(); wr.writerows(rows)
    print(f"{len(rows)} rows -> results/{out}.csv")


if __name__ == '__main__':
    main()
