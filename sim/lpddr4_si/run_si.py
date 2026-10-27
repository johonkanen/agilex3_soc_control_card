"""LPDDR4 SI sweep: gen_sch.py -> kicad-cli (KiCad's IBIS converter) -> ngspice (libngspice from the KiCad AppImage)
-> eyes, mask margins, over/undershoot -> results/.

  KICAD_APPRUN=.../squashfs-root/AppRun python3 run_si.py [--quick]

Writes results/results.csv, results/results.md and results/eye_*.png. Netlists and waveforms go to work/ (git-ignored).
"""
import argparse, ctypes, csv, glob, json, os, re, shutil, subprocess, sys
from concurrent.futures import ProcessPoolExecutor
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WORK, RES = os.path.join(HERE, 'work'), os.path.join(HERE, 'results')
APPRUN = os.environ.get('KICAD_APPRUN', '')
LIBNG = os.path.join(os.path.dirname(APPRUN), 'shared/lib/libngspice.so.0')
IBIS_CACHE = os.path.expanduser('~/.cache/kicad/10.0/ibis')
UI = 625e-12
SKIP = 12            # start-up bits not used in the eye
VDDQ = 1.1

# Rx masks. JEDEC JESD209-4 LPDDR4 rectangular masks for the DRAM inputs (as reproduced in TI SPRAD66B, 1600 column);
# for the FPGA read side TI's SoC-pad diamond (0.42 UI x 140 mV) is used as a proxy: Altera publishes no Rx mask.
MASK = {'dq_write': ('rect', 140e-3, 0.22), 'ca': ('rect', 175e-3, 0.30), 'dq_read': ('diamond', 140e-3, 0.42)}
# over/undershoot limits at the receiver: DRAM JEDEC DC abs max -0.4..1.5 V; Agilex 5 1.1 V HSIO (data sheet 813918
# Table 7): VCCIO+0.25 V for 100 % of the time ... nothing above VCCIO+0.40 V, undershoot -0.3 V
LIMIT = {'dq_write': (-0.4, 1.5), 'ca': (-0.4, 1.5), 'dq_read': (-0.3, VDDQ + 0.25)}


# ---------------------------------------------------------------------------------------------------------- netlists
def simplify(t, v, tol):
    """Douglas-Peucker on a PWL (iterative)."""
    keep = np.zeros(len(t), bool); keep[[0, -1]] = True
    stack = [(0, len(t) - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2: continue
        tt, vv = t[a + 1:b], v[a + 1:b]
        lin = v[a] + (v[b] - v[a]) * (tt - t[a]) / (t[b] - t[a])
        i = int(np.argmax(np.abs(vv - lin)))
        if abs(vv[i] - lin[i]) > tol:
            m = a + 1 + i; keep[m] = True; stack += [(a, m), (m, b)]
    return t[keep], v[keep]


def clean_cache(text, dt=0.5e-12, tol=1e-3):
    """KIBIS writes the switching coefficients Ku/Kd as PWL sources with ~1e5 points per driver (0.8 ps steps, every
    IBIS waveform sample), which makes ngspice crawl, and with narrow solver spikes (to -0.9 / +1.3 for a few ps where
    the two-waveform system is ill-conditioned). Resample to 0.5 ps, median-filter over 2.5 ps, simplify to 1e-3."""
    def fix(m):
        a = np.array(m.group(2).split(), float).reshape(-1, 2)
        t, v = a[:, 0], a[:, 1]
        t, idx = np.unique(t[::-1], return_index=True); v = v[::-1][idx]       # last value wins at repeated times
        tu = np.arange(0, t[-1] + dt / 2, dt); vu = np.interp(tu, t, v)
        w = np.lib.stride_tricks.sliding_window_view(np.pad(vu, 2, mode='edge'), 5)
        ts, vs = simplify(tu, np.median(w, axis=1), tol)
        return m.group(1) + ' '.join(f'{x:.6e} {y:.6e}' for x, y in zip(ts, vs)) + ' )'
    return re.sub(r'^(Vk[ud] K[UD] GND pwl \()(.*?)\)', fix, text, flags=re.M)


def export(tag, gen_args):
    """gen_sch.py -> work/tag.kicad_sch -> kicad-cli spice netlist with the IBIS subcircuits copied next to it."""
    sch = os.path.join(WORK, tag + '.kicad_sch')
    subprocess.run([sys.executable, '-I', os.path.join(HERE, 'gen_sch.py'), sch, '--models', '../models'] + gen_args,
                   check=True, env=dict(os.environ))
    for f in glob.glob(os.path.join(IBIS_CACHE, '*.cache')): os.remove(f)
    r = subprocess.run([APPRUN, 'kicad-cli', 'sch', 'export', 'netlist', '--format', 'spice', '-o', tag + '.cir',
                        tag + '.kicad_sch'], cwd=WORK, capture_output=True, text=True)
    msgs = sorted(set(l for l in (r.stdout + r.stderr).splitlines() if l.strip()))
    if r.returncode or any('rror' in m or 'Invalid' in m for m in msgs): sys.exit(f'{tag}: kicad-cli failed:\n' + '\n'.join(msgs))
    idir = os.path.join(WORK, tag + '_ibis'); shutil.rmtree(idir, ignore_errors=True); os.makedirs(idir)
    cir = open(os.path.join(WORK, tag + '.cir')).read()
    for f in glob.glob(os.path.join(IBIS_CACHE, '*.cache')):
        dst = os.path.join(idir, os.path.basename(f))
        s = open(f).read()
        open(dst, 'w').write(s if os.environ.get('SI_RAW_KUKD') else clean_cache(s)); cir = cir.replace(f, dst)
    cir = re.sub(r'(?<=\s)/(\w+)', r'\1', cir)            # KiCad net names '/x' -> 'x' (ngspice reads '/' as divide)
    open(os.path.join(WORK, tag + '.cir'), 'w').write(cir)
    return [m for m in msgs if m], json.load(open(os.path.join(WORK, tag + '.json')))


def ngspice(cir, vecs, out):
    """Run one netlist in a fresh process through libngspice (ctypes); write the vectors to out (wrdata)."""
    code = f'''
import ctypes, glob, os
ng = ctypes.CDLL({LIBNG!r})
log = []
PF = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
EX = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_bool, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
pf = PF(lambda s, i, u: log.append(s.decode(errors='replace')) or 0); ex = EX(lambda *a: 0)
ng.ngSpice_Init(pf, pf, ex, None, None, None, None)
c = lambda s: ng.ngSpice_Command(s.encode())
for cm in glob.glob(os.path.join(os.path.dirname({LIBNG!r}), 'ngspice', '*.cm')): c('codemodel ' + cm)
c('set wr_singlescale'); c('set wr_vecnames'); c('source {cir}'); c('run')
c('wrdata {out} ' + {' '.join(f'v({v})' for v in vecs)!r})
open({out + '.log'!r}, 'w').write('\\n'.join(log))
'''
    r = subprocess.run([sys.executable, '-I', '-c', code], capture_output=True, text=True)
    if r.returncode or not os.path.exists(out): sys.exit(f'ngspice failed on {cir}: {r.stderr[-2000:]}')
    d = np.loadtxt(out, skiprows=1)
    return d[:, 0], {v: d[:, i + 1] for i, v in enumerate(vecs)}


# -------------------------------------------------------------------------------------------------------------- eyes
def driver_bits(t, vd):
    """Bit grid and bit values from the driver's own die waveform: edges sit on phi + k*UI (phi from the mid-level
    crossings), bit k is the level at phi + (k + 0.5)*UI. Avoids depending on KIBIS' PRBS seed and polarity."""
    lo, hi = np.percentile(vd, [2, 98]); mid = (lo + hi) / 2
    s = np.sign(vd - mid); i = np.nonzero(s[1:] != s[:-1])[0]
    tc = t[i] + (mid - vd[i]) * (t[i + 1] - t[i]) / (vd[i + 1] - vd[i])
    phi = np.angle(np.mean(np.exp(2j * np.pi * tc / UI))) / (2 * np.pi) * UI % UI
    n = int((t[-1] - phi) / UI)
    bits = (np.interp(phi + (np.arange(n) + 0.5) * UI, t, vd) > mid).astype(int)
    return phi, bits


def fold(t, v, phi, bits, dt=1e-12):
    """Align the receiver waveform to the driver bits (cross-correlation over 0-4 ns), return per-bit traces."""
    spb = int(round(UI / dt)); n = len(bits)
    tt = phi + np.arange(0, n * spb) * dt; vv = np.interp(tt, t, v)
    ideal = np.repeat(bits * 2 - 1.0, spb)
    s0 = SKIP * spb; L = int(4e-9 / dt)
    a = vv[s0:] - vv[s0:].mean(); b = ideal[s0:]
    nf = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    xc = np.fft.irfft(np.fft.rfft(a, nf) * np.conj(np.fft.rfft(b, nf)), nf)[:L]   # xc[lag] = sum a[i+lag] b[i]
    best = (0, int(np.argmax(xc)))
    lag = best[1] * dt
    ph = np.arange(spb) * dt
    traces, labels = [], []
    for k in range(SKIP, n):
        t0 = phi + lag + k * UI
        if t0 + UI > t[-1]: break
        traces.append(np.interp(t0 + ph, t, v)); labels.append(bits[k])
    return ph, np.array(traces), np.array(labels), lag


def eye_metrics(ph, tr, lab, mask):
    shape, V, W = mask; dt = ph[1] - ph[0]; w = int(round(W * UI / dt))
    top, bot = tr[lab == 1].min(0), tr[lab == 0].max(0)
    op = top - bot
    eh = op.max(); tc = int(op.argmax())
    vref = (top[tc] + bot[tc]) / 2
    # widest Vref: eye width at zero height, and at the mask height, scanning Vref
    def widths(vrs, h):   # longest run of 'open' phases for each Vref (vectorised)
        ok = (top[None, :] >= vrs[:, None] + h / 2) & (bot[None, :] <= vrs[:, None] - h / 2)
        d = np.diff(np.pad(ok.astype(np.int8), ((0, 0), (1, 1))), axis=1)
        out = np.zeros(len(vrs))
        for i in range(len(vrs)):
            s, e = np.nonzero(d[i] == 1)[0], np.nonzero(d[i] == -1)[0]
            if len(s): out[i] = (e - s).max()
        return out * dt
    vr_scan = np.linspace(bot.min(), top.max(), 400)
    ew0 = widths(vr_scan, 0).max()
    wm = widths(vr_scan, V); ewm, vr_m = wm.max(), vr_scan[int(wm.argmax())]
    # voltage margin of the mask at its best position (opening minus mask height, rect or diamond)
    vm = -1e9
    for s in range(0, len(ph) - w):
        if shape == 'rect':
            o = top[s:s + w].min() - bot[s:s + w].max() - V
        else:
            x = np.abs(np.arange(w) - (w - 1) / 2) / ((w - 1) / 2)
            h = V / 2 * (1 - x)
            o = (top[s:s + w] - h).min() - (bot[s:s + w] + h).max()
        vm = max(vm, o)
    return dict(eh_mV=eh * 1e3, ew0_ps=ew0 * 1e12, vref_mV=vr_m * 1e3, ew_mask_ps=ewm * 1e12,
                t_margin_ps=(ewm - W * UI) * 1e12 if ewm > 0 else float('nan'), v_margin_mV=vm * 1e3,
                top=top, bot=bot)


def plot_eye(png, title, ph, tr, lab, m, mask, extra=None):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.4, 4.2), dpi=110)
    x = np.concatenate([ph, ph + UI]) * 1e12
    for i in range(len(tr)):
        nxt = tr[i + 1] if i + 1 < len(tr) else tr[i]
        ax.plot(x, np.concatenate([tr[i], nxt]) * 1e3, color='#1f5fa8', lw=0.4, alpha=0.25)
    shape, V, W = mask
    # mask drawn at the best voltage-margin position for display: centre on the widest point at its Vref
    c = (ph[int(np.argmax(m['top'] - m['bot']))]) * 1e12; vr = m['vref_mV']; w = W * UI * 1e12; h = V * 1e3
    if shape == 'rect':
        ax.add_patch(plt.Rectangle((c - w / 2, vr - h / 2), w, h, fill=False, ec='#d62728', lw=1.4))
    else:
        ax.add_patch(plt.Polygon([(c - w / 2, vr), (c, vr + h / 2), (c + w / 2, vr), (c, vr - h / 2)], fill=False,
                                 ec='#d62728', lw=1.4))
    ax.set_xlim(0, 2 * UI * 1e12); ax.set_xlabel('time (ps), 2 UI'); ax.set_ylabel('mV')
    ax.set_title(title, fontsize=9)
    ax.text(0.01, 0.02, f"EH {m['eh_mV']:.0f} mV  EW {m['ew0_ps']:.0f} ps  mask margin {m['v_margin_mV']:+.0f} mV / "
            f"{m['t_margin_ps']:+.0f} ps" + (extra or ''), transform=ax.transAxes, fontsize=7.5)
    ax.grid(alpha=0.3); fig.tight_layout(); fig.savefig(png); plt.close(fig)


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
        d = np.loadtxt(dat, skiprows=1); t, w = d[:, 0], {v: d[:, i + 1] for i, v in enumerate(vecs)}
    else:
        t, w = ngspice(cir, vecs, dat)
    rows = []
    for case, m in meta.items():
        phi, bits = driver_bits(t, w[f"x{m['drv'].lower()}.die0"])
        mask = MASK[m['kind']]; lo, hi = LIMIT[m['kind']]
        for ref, pad in m['rx']:
            for node, where in ((pad, 'ball'), (f"x{ref.lower()}.die0", 'die')):
                v = w[node]
                ph, tr, lab, lag = fold(t, v, phi, bits)
                e = eye_metrics(ph, tr, lab, mask)
                seg = v[t > SKIP * UI]
                row = dict(point=tag, case=case, rx=ref, where=where, delay_ps=lag * 1e12,
                           vmax_mV=seg.max() * 1e3, vmin_mV=seg.min() * 1e3, lim_lo_mV=lo * 1e3, lim_hi_mV=hi * 1e3,
                           limits_ok=bool(lo <= seg.min() and seg.max() <= hi),
                           **{k: v_ for k, v_ in e.items() if k not in ('top', 'bot')})
                row.update(dict(zip(('zdq', 'ldq', 'zca', 'via', 'corner'), gen_args_vals(gen_args))))
                rows.append(row)
                if plot and where == 'die':
                    plot_eye(os.path.join(RES, f'eye_{tag}_{case}_{ref}.png'),
                             f'{case} {ref} die, {tag}', ph, tr, lab, e, mask,
                             f"  Vmax {row['vmax_mV']:.0f} Vmin {row['vmin_mV']:.0f} mV")
    return rows


def ibis_wf(path, model, edge, vfix=0.0):
    """[Rising|Falling Waveform] typ column of a model, for the table with V_fixture == vfix."""
    t = open(path).read()
    i = re.search(rf'^\[Model\]\s+{re.escape(model)}\s*$', t, re.M).start()
    j = t.find('[Model]', i + 8); blk = t[i:j if j > 0 else len(t)]
    unit = {'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'm': 1e-3, 'f': 1e-15}
    num = lambda s: float(re.match(r'[-+.\deE]+', s).group()) * unit.get(re.sub(r'[-+.\deE]+', '', s)[:1].lower(), 1)
    for w in re.finditer(rf'\[{edge} Waveform\](.*?)(?=\n\[)', blk, re.S):
        body = w.group(1)
        vf = re.search(r'^V_fixture\s*=\s*(\S+)', body, re.M)
        if not vf or abs(num(vf.group(1).rstrip('Vv')) - vfix) > 1e-6: continue
        rows = [l.split() for l in body.splitlines() if l.strip() and not l.strip().startswith('|') and '=' not in l]
        return np.array([num(r[0].rstrip('sS')) for r in rows]), np.array([num(r[1].rstrip('Vv')) for r in rows])
    raise KeyError(f'{model} {edge} V_fixture={vfix}')


def validate():
    """Converted driver (package removed) into 50 ohm to GND vs the IBIS V-t table: levels and 20-80 % edge times."""
    msgs, meta = export('validate', ['--validate'])
    idir = os.path.join(WORK, 'validate_ibis')
    for f in glob.glob(os.path.join(idir, '*.cache')):     # the V-t tables are at the die, without package
        s = open(f).read()
        s = re.sub(r'^(RPIN \S+ \S+) \S+', r'\1 1e-6', s, flags=re.M)
        s = re.sub(r'^(LPIN \S+ \S+) \S+', r'\1 1e-15', s, flags=re.M)
        s = re.sub(r'^(CPIN \S+ \S+) \S+', r'\1 1e-18', s, flags=re.M)
        open(f, 'w').write(s)
    t, w = ngspice(os.path.join(WORK, 'validate.cir'), [f'{k}_o' for k in meta], os.path.join(WORK, 'validate.dat'))
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, len(meta), figsize=(4.2 * len(meta), 3.4), dpi=110)
    lines = ['| driver model | edge | V start / end, IBIS (mV) | V start / end, KiCad (mV) | t20-80, IBIS (ps) | t20-80, KiCad (ps) |',
             '|---|---|---|---|---|---|']

    def t2080(tt, vv):
        a, b = vv[0], vv[-1]; lo, hi = a + 0.2 * (b - a), a + 0.8 * (b - a)
        x = (vv - lo) / (hi - lo) if b > a else (lo - vv) / (lo - hi)
        i1 = np.argmax(x >= 0); i2 = np.argmax(x >= 1)
        return tt[i1], tt[i2] - tt[i1]
    for ax, (k, m) in zip(axs, meta.items()):
        v = w[f'{k}_o']; lib = os.path.join(HERE, 'models', m['lib'])
        for edge, sel in (('Rising', t < 4.0e-9), ('Falling', t >= 4.0e-9)):
            ti, vi = ibis_wf(lib, m['model'], edge)
            tk, vk = t[sel], v[sel]
            # the simulated edge: window around the swing, starting where the table's first sample would sit
            mid = (vi[0] + vi[-1]) / 2
            ic = np.argmax(vk > mid) if edge == 'Rising' else np.argmax(vk < mid)
            t_ic, d_ic = t2080(ti, vi)
            tsim = tk[ic] - (ti[np.argmax(vi > mid) if edge == 'Rising' else np.argmax(vi < mid)])
            ts = tsim + ti; vs = np.interp(ts, tk, vk)
            _, d_k = t2080(ts, vs)
            lines.append(f"| {m['model']} | {edge.lower()} | {vi[0]*1e3:.0f} / {vi[-1]*1e3:.0f} | {vs[0]*1e3:.0f} / "
                         f"{vk[-1]*1e3:.0f} | {d_ic*1e12:.1f} | {d_k*1e12:.1f} |")
            ax.plot(ti * 1e12, vi * 1e3, 'k', lw=1.2, label=f'IBIS {edge.lower()}' )
            ax.plot(ti * 1e12, vs * 1e3, '--', lw=1.2, label=f'KiCad {edge.lower()}')
        ax.set_title(f"{m['model']} into 50 ohm to GND", fontsize=8); ax.set_xlabel('ps'); ax.set_ylabel('mV')
        ax.grid(alpha=.3); ax.legend(fontsize=7); ax.set_xlim(0, min(ti[-1], 1.5e-9) * 1e12)
    fig.tight_layout(); fig.savefig(os.path.join(RES, 'validate_drivers.png')); plt.close(fig)
    open(os.path.join(RES, 'validate_drivers.md'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))


def gen_args_vals(a):
    d = dict(zip(a[::2], a[1::2]))
    return (float(d.get('--zdq', 40)), float(d.get('--ldq', 20)), float(d.get('--zca', 40)), d.get('--via-dq', 'long'),
            d.get('--corner', 'typ'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quick', action='store_true', help='baseline 40/50 ohm, 20 mm only')
    ap.add_argument('--validate', action='store_true', help='only check the converted drivers against IBIS V-t tables')
    ap.add_argument('-j', type=int, default=6)
    a = ap.parse_args()
    if not os.path.exists(LIBNG): sys.exit('set KICAD_APPRUN to the extracted KiCad 10 AppImage AppRun')
    os.makedirs(WORK, exist_ok=True); os.makedirs(RES, exist_ok=True)
    if a.validate: return validate()
    pts = []
    for z in (40, 50):
        for l in ((20,) if a.quick else (16, 20, 22)):
            pts.append((f'z{z}_l{l}', ['--zdq', str(z), '--ldq', str(l), '--zca', str(z)], l == 20))
        if not a.quick:
            pts.append((f'z{z}_l20_shortvia', ['--zdq', str(z), '--ldq', '20', '--zca', str(z), '--via-dq', 'short'], False))
            for c in ('min', 'max'):
                pts.append((f'z{z}_l20_{c}', ['--zdq', str(z), '--ldq', '20', '--zca', str(z), '--corner', c], False))
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
    with open(os.path.join(RES, 'results.csv'), 'w', newline='') as f:
        wr = csv.DictWriter(f, keys); wr.writeheader(); wr.writerows(rows)
    print(f'{len(rows)} rows -> results/results.csv')


if __name__ == '__main__':
    main()
