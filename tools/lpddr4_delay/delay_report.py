#!/usr/bin/env python3
"""LPDDR4 delay report from KiCad's own delay calculation.

    export KICAD_APPRUN=<KiCad 10 AppImage>/AppRun        (or KICAD_CLI=kicad-cli)
    python3 tools/lpddr4_delay/delay_report.py [BOARD.kicad_pcb] [-o LPDDR4_DELAY_REPORT.md]

1. Copies the board, .kicad_pro and .kicad_dru to a temporary folder, appends a probe rule (a delay window of
   1-2 ps on every LPDDR4 net class) and runs `kicad-cli pcb drc`. Every net fails the rule, and the violation
   carries KiCad's actual delay: tracks per layer from the tuning profiles, vias by stack-up height, plus the
   U7 pad `die_delay` (the Agilex 5 package delay from the Quartus .pin file). U12 has no package data.
2. CA/CKE/CS/CK are T-shaped (U7 -> T-via under U12 -> one ball per channel). KiCad sums the whole net, so the
   two branches (T-via -> ball, computed here from the copper with the same per-layer delays) are taken off:
   die -> ball A = total - branch B, die -> ball B = total - branch A.
3. Grades every group against the Altera 821801 budgets (ps, FPGA package included) and prints / writes
   a markdown report.

Sign conventions: "DQ-DQS" = t(DQ) - t(DQS_P) of the same byte; "CA-CK" = t(CA) - t(CK_P) at the same
channel's ball; "CK-DQS" = t(CK_P) - t(DQS_P) at the byte's channel.
"""
import argparse, collections, heapq, json, math, os, re, shutil, subprocess, sys, tempfile

PFX = '/IOBANK 3/'
BYTES = {b: ['dq%d' % i for i in range(8 * b, 8 * b + 8)] + ['dm%d' % b] for b in range(4)}
BYTE_CH = {0: 'A', 1: 'A', 2: 'B', 3: 'B'}
CA = ['ca%d' % i for i in range(6)]
CSCKE = ['cke', '~{cs}']
LIM = {'dq': (-68, 43), 'ca': (-34, 34), 'cscke': (-85, 85), 'ckdqs': (-340, 170), 'pn': 1.0}
# design targets inside those limits (what the .kicad_dru group rules check, max - min of the group)
TGT = {'byte': 10, 'ca': 20, 'cscke': 60}


def kicad_cli():
    if os.environ.get('KICAD_CLI'):
        return [os.environ['KICAD_CLI']]
    if os.environ.get('KICAD_APPRUN'):
        return [os.environ['KICAD_APPRUN'], 'kicad-cli']
    return ['kicad-cli']


def kicad_delays(board):
    """{net short name: delay ps} for every LPDDR4 net, from a KiCad DRC probe run."""
    base = os.path.splitext(board)[0]
    with tempfile.TemporaryDirectory() as d:
        b = os.path.join(d, 'probe.kicad_pcb')
        shutil.copy(board, b)
        shutil.copy(base + '.kicad_pro', os.path.join(d, 'probe.kicad_pro'))
        dru = open(base + '.kicad_dru').read() if os.path.exists(base + '.kicad_dru') else '(version 1)\n'
        dru += ('\n(rule "probe_delay"\n\t(condition "A.hasNetclass(\'lpddr_dq\') || A.hasNetclass(\'lpddr_ca\') || '
                'A.hasNetclass(\'lpddr_diff\')")\n\t(constraint length (min 1ps) (max 2ps)))\n')
        open(os.path.join(d, 'probe.kicad_dru'), 'w').write(dru)
        out = os.path.join(d, 'probe.json')
        subprocess.run(kicad_cli() + ['pcb', 'drc', '--severity-all', '--format', 'json', '-o', out, b],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        rep = json.load(open(out))
    delay = {}
    for v in rep['violations']:
        if v['type'] != 'length_out_of_range' or 'probe_delay' not in v['description']:
            continue
        a = re.search(r'actual ([\d.]+) ps', v['description'])
        nets = {re.search(r'\[([^\]]+)\]', i['description']).group(1) for i in v['items']
                if re.search(r'\[([^\]]+)\]', i['description'])}
        for n in nets:
            if n.startswith(PFX) and a:
                delay[n[len(PFX):]] = float(a.group(1))
    return delay


# ---------------------------------------------------------------- board geometry (T-branches)
def blocks(txt, tag):
    for m in re.finditer(r'\n\t\(%s[ \n]' % tag, txt):
        s = m.start() + 1; depth = 0; i = s
        while True:
            c = txt[i]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    break
            i += 1
        yield txt[s:i + 1]


def stack_depth(txt):
    st = txt[txt.find('(stackup'):]
    z, depth = 0.0, {}
    for name, th in re.findall(r'\(layer "([^"]+)"[^()]*?(?:\([^()]*\)[^()]*?)*?\(thickness ([\d.]+)\)', st[:st.find('\n\t\t)\n')]):
        if name.endswith('.Cu'):
            depth[name] = z + float(th) / 2
        if not name.endswith(('Mask', 'Paste', 'SilkS')):
            z += float(th)
    return depth


def profiles(pro):
    p = json.load(open(pro))
    out = {}
    for t in p['tuning_profiles']['tuning_profiles_impedance_geometric']:
        out[t['type']] = ({e['signal_layer']: e['delay'] / 1e6 for e in t['layer_entries']}, t['via_prop_delay'] / 1e6)
    return out  # type 0 single-ended, 1 differential


def arc_len(x1, y1, xm, ym, x2, y2):
    """Length of the circular arc start -> mid -> end."""
    ax, ay, bx, by, cx, cy = x1, y1, xm, ym, x2, y2
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        return math.hypot(x2 - x1, y2 - y1)
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    r = math.hypot(ax - ux, ay - uy)
    ang = lambda x, y: math.atan2(y - uy, x - ux)
    a1, am, a2 = ang(ax, ay), ang(bx, by), ang(cx, cy)
    sweep = (a2 - a1) % (2 * math.pi)
    if (am - a1) % (2 * math.pi) > sweep:   # mid not on the ccw path: the arc runs the other way
        sweep = 2 * math.pi - sweep
    return r * sweep


def branches(board, nets):
    """{net: {u12 ball: branch delay ps}} for the T-shaped CA/CK nets. A branch is the part of the copper that only
    leads to that ball. With path delays d(U7, A), d(U7, B) and d(A, B) through the copper of a tree-shaped net, the
    branch to A is (d(U7, A) + d(A, B) - d(U7, B)) / 2, wherever the trunk splits (separate T-via or a ball via)."""
    txt = open(board).read()
    depth = stack_depth(txt)
    prof = profiles(os.path.splitext(board)[0] + '.kicad_pro')
    pads = collections.defaultdict(list)   # net -> [(ref, ball, x, y, radius)]
    die = {}   # U7 ball -> die_delay ps
    for b in blocks(txt, 'footprint'):
        ref = re.search(r'\(property "Reference" "([^"]+)"', b).group(1)
        if ref not in ('U7', 'U12'):
            continue
        fx, fy, *r = map(float, re.search(r'\(at ([\d.\- ]+)\)', b).group(1).split())
        th = math.radians(r[0] if r else 0)
        for p in re.finditer(r'\(pad "([^"]+)" \w+ \w+\s+\(at ([\d.\- ]+)\)\s+\(size ([\d.]+)[^)]*\).*?'
                             r'\(net (?:\d+ )?"([^"]*)"', b, re.S):
            px, py = map(float, p.group(2).split()[:2])
            end = b.find('\n\t\t(pad ', p.end())
            m = re.search(r'\(die_delay ([\d.]+)\)', b[p.end():end if end > 0 else len(b)])
            if ref == 'U7' and m:
                die[p.group(1)] = float(m.group(1))
            pads[p.group(4)].append((ref, p.group(1), fx + px * math.cos(th) + py * math.sin(th),
                                     fy - px * math.sin(th) + py * math.cos(th), float(p.group(3)) / 2))
    segs = collections.defaultdict(list); vias = collections.defaultdict(list)
    for m in re.finditer(r'\(segment\s+\(start ([\d.-]+) ([\d.-]+)\)\s+\(end ([\d.-]+) ([\d.-]+)\)\s+\(width [\d.]+\)\s+'
                         r'\(layer "([^"]+)"\)\s+\(net (?:\d+ )?"([^"]*)"', txt):
        segs[m.group(6)].append((float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)), m.group(5)))
    for b in blocks(txt, 'arc'):   # tuning meanders and rounded corners
        m = re.search(r'\(start ([\d.-]+) ([\d.-]+)\)\s+\(mid ([\d.-]+) ([\d.-]+)\)\s+\(end ([\d.-]+) ([\d.-]+)\).*?'
                      r'\(layer "([^"]+)"\).*?\(net (?:\d+ )?"([^"]*)"', b, re.S)
        if m:
            x1, y1, xm, ym, x2, y2 = map(float, m.groups()[:6])
            segs[m.group(8)].append((x1, y1, x2, y2, m.group(7), arc_len(x1, y1, xm, ym, x2, y2)))
    for b in blocks(txt, 'via'):
        a = re.search(r'\(at ([\d.-]+) ([\d.-]+)\)', b); n = re.search(r'\(net (?:\d+ )?"([^"]*)"', b)
        if n:
            vias[n.group(1)].append((float(a.group(1)), float(a.group(2))))
    key = lambda x, y: (round(x, 3), round(y, 3))
    out = {}
    for s in nets:
        net = PFX + s
        lay_ps, via_ps = prof[1 if s.startswith('ck_') else 0]
        g = collections.defaultdict(list)   # nodes: ((x, y), layer) and ('pad', ref, ball)
        def edge(a, b, w):
            g[a].append((b, w)); g[b].append((a, w))
        for x1, y1, x2, y2, L, *arc in segs[net]:
            edge((key(x1, y1), L), (key(x2, y2), L), (arc[0] if arc else math.hypot(x2 - x1, y2 - y1)) * lay_ps[L])
        pts = collections.defaultdict(set)
        for n in list(g):
            pts[n[0]].add(n[1])
        for vx, vy in vias[net]:
            ls = sorted(pts.get(key(vx, vy), ()))
            for i in ls:
                for j in ls:
                    if i < j:
                        edge((key(vx, vy), i), (key(vx, vy), j), abs(depth[i] - depth[j]) * via_ps)
        for ref, ball, x, y, rad in pads[net]:   # SMD pads on F.Cu; via-in-pad reaches the inner layers
            for pt, ls in pts.items():
                if math.hypot(pt[0] - x, pt[1] - y) <= rad:
                    for L in ls:
                        edge(('pad', ref, ball), (pt, L), abs(depth[L] - depth['F.Cu']) * via_ps)
        def dist_from(src):
            dist = {}; h = [(0.0, 0, src)]; k = 1
            while h:
                d, _, n = heapq.heappop(h)
                if n in dist:
                    continue
                dist[n] = d
                for m, w in g[n]:
                    if m not in dist:
                        heapq.heappush(h, (d + w, k, m)); k += 1
            return dist
        u7 = [('pad', r_, b_) for r_, b_, *_ in pads[net] if r_ == 'U7']
        u12 = [('pad', r_, b_) for r_, b_, *_ in pads[net] if r_ == 'U12']
        if u7:
            out.setdefault('_die', {})[s] = die.get(u7[0][2], 0.0)
        if len(u7) != 1 or len(u12) != 2:
            out[s] = None; continue
        d7 = dist_from(u7[0]); da = dist_from(u12[0])
        A, B = u12
        if A not in d7 or B not in d7 or B not in da:
            out[s] = None; continue
        ba = (d7[A] + da[B] - d7[B]) / 2
        out[s] = {A[2]: ba, B[2]: da[B] - ba, '_copper': d7[A] + da[B] - ba}   # _copper: whole tree, for a check
    return out


CH_OF_BALL = lambda ball: 'A' if re.match(r'[A-K]\d', ball) else 'B'   # U12 rows A-K channel A, L-AB channel B


BEGIN = '# ---- BEGIN delay_report targets (generated by tools/lpddr4_delay/delay_report.py --dru; do not edit) ----'
END = '# ---- END delay_report targets ----'


def write_dru(path, targets):
    """Replace the generated block in the .kicad_dru: one delay window per net, which KiCad's length tuner uses
    as its target (time-domain profiles)."""
    old = open(path).read()
    if BEGIN in old:
        old = old[:old.index(BEGIN)].rstrip('\n') + '\n' + old[old.index(END) + len(END):].lstrip('\n')
    order = lambda n: (0 if n.startswith(('dq', 'dm')) else 1, n)
    blk = [BEGIN,
           '# Lengthen-only targets: each byte tuned to its slowest net, CA/CKE/CS/CK to the slowest die->ball delay',
           '# (KiCad totals: die_delay + copper; T-nets include both branches). Rerun the script after re-routing.']
    for n in sorted(targets, key=order):
        tg, tol = targets[n]
        blk.append('(rule "dly_%s"\n\t(condition "A.NetName == \'%s%s\'")\n\t(constraint length (min %.1fps) (max %.1fps)))'
                   % (re.sub(r'[^\w]', '', n), PFX, n, tg - tol, tg + tol))
    blk.append(END)
    open(path, 'w').write(old.rstrip('\n') + '\n\n' + '\n'.join(blk) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('board', nargs='?', default='agilex_3_soc.kicad_pcb')
    ap.add_argument('-o', '--out')
    ap.add_argument('--dru', action='store_true',
                    help='write the per-net KiCad tuner targets as delay windows into the board .kicad_dru '
                         '(between the BEGIN/END delay_report markers)')
    a = ap.parse_args()
    targets = {}   # net -> (target ps, tolerance ps)
    D = kicad_delays(a.board)
    T = branches(a.board, CA + CSCKE + ['ck_P', 'ck_N'])
    L = []; bad = []
    p = L.append
    def chk(ok, what):
        if not ok:
            bad.append(what)
        return 'OK' if ok else '**FAIL**'

    p('## Strobe and clock pairs (P/N skew, limit < 1 ps)\n')
    p('| Pair | P (ps) | N (ps) | P-N | |')
    p('|---|---|---|---|---|')
    for pair in ['dqs%d' % b for b in range(4)] + ['ck']:
        P, N = D.get(pair + '_P'), D.get(pair + '_N')
        if P is None or N is None:
            p('| %s | missing | | | **FAIL** |' % pair); bad.append(pair + ' missing'); continue
        p('| %s | %.1f | %.1f | %+.1f | %s |' % (pair, P, N, P - N, chk(abs(P - N) < LIM['pn'], pair + ' P/N')))

    p('\n## Data bytes (DQ/DM - DQS_P, limit %+d ... %+d ps; design target: group spread <= %d ps)\n'
      % (LIM['dq'] + (TGT['byte'],)))
    p('Lengthen-only tuning: every net of a byte (DQS_P/N included) is tuned to the slowest one, the **KiCad tuner '
      'target** column; "add" is what each net needs. KiCad\'s delays already include the U7 package delay.\n')
    p('| Byte | DQS_P (ps) | DQ/DM - DQS_P (ps) | Range | Spread | Limit | Target | KiCad tuner target | add (ps) |')
    p('|---|---|---|---|---|---|---|---|---|')
    for b, nets in BYTES.items():
        ref = D.get('dqs%d_P' % b)
        rel = {n: D[n] - ref for n in nets if n in D and ref is not None}
        miss = [n for n in nets if n not in D]
        if not rel:
            p('| %d | missing | | | | **FAIL** | | | |' % b); bad.append('byte %d' % b); continue
        lo, hi = min(rel.values()), max(rel.values())
        allv = list(rel.values()) + [0.0]
        grp = {n: D[n] for n in nets + ['dqs%d_P' % b, 'dqs%d_N' % b] if n in D}
        top = max(grp.values())
        for n in grp:
            targets[n] = (top, TGT['byte'] / 2)
        p('| %d | %.1f | %s | %+.1f ... %+.1f | %.1f | %s | %s | %.1f | %s |' % (
            b, ref, ', '.join('%s %+.1f' % (n, v) for n, v in rel.items()), lo, hi, max(allv) - min(allv),
            chk(LIM['dq'][0] <= lo and hi <= LIM['dq'][1] and not miss, 'byte %d limit' % b),
            'OK' if max(allv) - min(allv) <= TGT['byte'] else 'over', top,
            ', '.join('%s +%.0f' % (n, top - v) for n, v in grp.items() if top - v >= 1) or 'none'))

    p('\n## Address/command (die -> U12 ball, T-branch removed)\n')
    ball = {}
    for s in CA + CSCKE + ['ck_P', 'ck_N']:   # own copper + die must reproduce KiCad's total
        br = T.get(s)
        if br and s in D and abs(br['_copper'] + T['_die'][s] - D[s]) > 2.0:
            bad.append('%s: own copper delay %.1f + die %.1f != KiCad %.1f' % (s, br['_copper'], T['_die'][s], D[s]))
    for s in CA + CSCKE + ['ck_P', 'ck_N']:
        br = T.get(s)
        br = br and {k: v for k, v in br.items() if not k.startswith('_')}
        if s not in D or not br or None in br.values() or len(br) != 2:
            ball[s] = None; continue
        (b1, d1), (b2, d2) = sorted(br.items(), key=lambda kv: CH_OF_BALL(kv[0]))
        ball[s] = {'A': (b1, D[s] - d2, d1), 'B': (b2, D[s] - d1, d2)}
    ok = {s: v for s, v in ball.items() if v}
    mean = lambda v: (v['A'][1] + v['B'][1]) / 2
    ref = max(mean(v) for v in ok.values()) if ok else None   # lengthen-only: the slowest die->ball
    p('KiCad shows the whole T (die + trunk + both branches). Lengthen-only tuning: every CA/CKE/CS/CK net is brought '
      'to the slowest die->ball delay (%s ps); its **KiCad tuner target** is that plus its own branch (mean of A '
      'and B). T-branches must match within 1 ps (A vs B).\n' % ('%.1f' % ref if ref else '?'))
    p('| Net | KiCad total (ps) | branch A / B (ps) | die->ball A | die->ball B | - CK_P (A / B) | Limit | KiCad tuner target | add (ps) |')
    p('|---|---|---|---|---|---|---|---|---|')
    ckb = ball.get('ck_P')
    for s in ['ck_P', 'ck_N'] + CA + CSCKE:
        v = ball.get(s)
        if v is None:
            p('| %s | %s | branches not found (open?) | | | | **FAIL** | | |' % (s, D.get(s, 'missing'))); bad.append(s); continue
        lim = LIM['ca'] if s in CA else LIM['cscke']
        if s.startswith('ck_') or ckb is None:
            rel, verdict = '', ''
        else:
            ra, rb = v['A'][1] - ckb['A'][1], v['B'][1] - ckb['B'][1]
            rel = '%+.1f / %+.1f' % (ra, rb)
            verdict = chk(all(lim[0] <= r <= lim[1] for r in (ra, rb)), s + ' vs CK')
        tbad = abs(v['A'][2] - v['B'][2]) >= 1.0
        if tbad:
            bad.append('%s T-branches %.1f/%.1f' % (s, v['A'][2], v['B'][2]))
        tgt = ref + (v['A'][2] + v['B'][2]) / 2
        targets[s] = (tgt, TGT['ca'] / 2 if s in CA or s.startswith('ck_') else TGT['cscke'] / 2)
        p('| %s | %.1f | %.1f / %.1f%s | %.1f (%s) | %.1f (%s) | %s | %s | %.1f | %+.0f |' % (
            s, D[s], v['A'][2], v['B'][2], ' **FAIL**' if tbad else '', v['A'][1], v['A'][0], v['B'][1], v['B'][0],
            rel, verdict + (' (%+d ... %+d)' % lim if verdict else ''), tgt, tgt - D[s]))
    if ckb:
        p('\n## CK - DQS (limit %+d ... %+d ps)\n' % LIM['ckdqs'])
        p('| Byte | channel | CK_P at ball (ps) | DQS_P (ps) | CK - DQS | |')
        p('|---|---|---|---|---|---|')
        for b in range(4):
            c = BYTE_CH[b]; q = D.get('dqs%d_P' % b)
            if q is None:
                continue
            r = ckb[c][1] - q
            p('| %d | %s | %.1f | %.1f | %+.1f | %s |' % (b, c, ckb[c][1], q, r,
                                                         chk(LIM['ckdqs'][0] <= r <= LIM['ckdqs'][1], 'CK-DQS %d' % b)))
    rst = D.get('~{rst}')
    if rst is not None:
        p('\n~{rst}: %.1f ps total (no matching requirement).' % rst)

    head = ['# LPDDR4 delay report', '',
            'Generated by `tools/lpddr4_delay/delay_report.py` from `%s`. Delays are KiCad\'s own (DRC probe rule): '
            'tracks per layer from the tuning profiles, vias by stack-up height, plus the U7 pad `die_delay` '
            '(Agilex 5 package delay, Quartus .pin). U12 package delay is not included (no data). '
            'CA/CK: the T-branch to the other channel\'s ball is subtracted (branches computed from the copper with '
            'the same per-layer delays).' % os.path.basename(a.board), '',
            '**Result: %s**' % ('all limits met' if not bad else '%d check(s) fail: %s' % (len(bad), ', '.join(bad))), '']
    if a.dru:
        write_dru(os.path.splitext(a.board)[0] + '.kicad_dru', targets)
        head += ['Per-net delay windows written to the .kicad_dru (block `delay_report targets`): DQ/DM/DQS '
                 '+-%g ps, CA/CK +-%g ps, CS/CKE +-%g ps around the tuner targets.' %
                 (TGT['byte'] / 2, TGT['ca'] / 2, TGT['cscke'] / 2), '']
    text = '\n'.join(head + L) + '\n'
    print(text)
    if a.out:
        open(a.out, 'w').write(text)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
