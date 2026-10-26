import re, sys, json, collections
N, drc, probe, pj, base = sys.argv[1:6]
info = json.load(open(pj))['info']
def items(f):
    return [it for it in re.split(r'\n(?=\[)', open(f).read()) if it.startswith('[')]
def key(it):
    return re.sub(r'length [\d.]+ mm|\d+\.\d+ mm', '', it.split('\n')[0] + '|' + '|'.join(sorted(re.findall(r'\[([^\]]+)\]', it))))
cur, old = items(drc), items(base)
oldk = collections.Counter(key(i) for i in old)
new = collections.Counter()
opens = set()
for it in cur:
    k = it.split(']')[0][1:]
    nets = re.findall(r'\[(/IOBANK 3/[^\]]+)\]', it)
    if k == 'unconnected_items':
        opens.update(n for n in nets if any(n.endswith('/' + s) for s in list(info) + ['~{rst}']))
        continue
    if 'Zone' in it and k in ('clearance', 'hole_clearance'): continue
    if nets and any(n.split('/')[-1] in list(info) + ['~{rst}'] for n in nets): new[k] += 1
tot = re.findall(r'Found (\d+)', open(drc).read())
d = {}
for it in items(probe):
    if it.startswith('[length_out_of_range]') and 'probe_delay' in it:
        a = re.search(r'actual ([\d.]+) ps', it); n = re.search(r'\[(/IOBANK 3/[^\]]+)\]', it)
        if a and n: d[n.group(1).split('/')[-1]] = float(a.group(1))
# KiCad sums the whole net: die + trunk + both branches.  die -> ball = total - one branch.
ball = {s: d[s] - info[s]['branch_ps'] for s in info if s in d}
ck = (ball.get('ck_P', 0) + ball.get('ck_N', 0)) / 2
print(f'== {N}: DRC {tot[0]} viol / {tot[1]} unconn; open LPDDR CA/CK/rst nets: {sorted(o.split("/")[-1] for o in opens) or "none"}')
print(f'   non-zone DRC items on routed nets: {dict(new) or "none"}')
if ball:
    print('   die->ball ps: ' + ', '.join(f'{s} {v:.1f}' for s, v in ball.items()))
    ca = {s: v - ck for s, v in ball.items() if not s.startswith('ck_')}
    print(f'   CA/CKE/CS - CK: {min(ca.values()):+.1f} ... {max(ca.values()):+.1f} ps (limit +-34 CA, +-85 CS/CKE); CK P-N {ball["ck_P"] - ball["ck_N"]:+.1f} ps (limit 1)')
    if 'rst' in str(d): print(f'   rst total {d.get("~{rst}", float("nan")):.1f} ps')
