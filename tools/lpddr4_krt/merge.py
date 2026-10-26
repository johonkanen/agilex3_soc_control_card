"""Main board = v15 output minus its CK trunks: python3.11 merge.py IN(original) V15 OUT
Keeps the original ck copper (branches, ball vias, T vias, the two U7-side fan-out vias)."""
import sys, collections
import pcbnew
IN, V, OUT = sys.argv[1:4]
mm = pcbnew.ToMM
def key(t):
    if t.Type() == pcbnew.PCB_VIA_T: return ('v', round(mm(t.GetPosition().x), 3), round(mm(t.GetPosition().y), 3))
    a, c = sorted([(round(mm(t.GetStart().x), 3), round(mm(t.GetStart().y), 3)), (round(mm(t.GetEnd().x), 3), round(mm(t.GetEnd().y), 3))])
    return ('s', t.GetLayerName(), a, c)
CK = ('/IOBANK 3/ck_P', '/IOBANK 3/ck_N')
o = pcbnew.LoadBoard(IN); b = pcbnew.LoadBoard(V)
orig = {n: {key(t): t for t in o.GetTracks() if t.GetNetname() == n} for n in CK}
rm = [t for t in b.GetTracks() if t.GetNetname() in CK and key(t) not in orig[t.GetNetname()]]
have = {(t.GetNetname(), key(t)) for t in b.GetTracks() if t.GetNetname() in CK}
for t in rm: b.Remove(t)
add = 0
for n in CK:
    for k, t in orig[n].items():
        if (n, k) not in have:
            c = t.Duplicate(); b.Add(c); add += 1
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(OUT, b)
# summary: per-net track/via counts, original vs merged
def cnt(bd):
    c = collections.Counter()
    for t in bd.GetTracks(): c[t.GetNetname()] += 1
    return c
m = pcbnew.LoadBoard(OUT); a, z = cnt(o), cnt(m)
print(f'merge: removed {len(rm)} KRT ck items, restored {add} original ck items')
for n in sorted(set(a) | set(z)):
    if a[n] != z[n]: print(f'  {n}: {a[n]} -> {z[n]}')
u7 = m.FindFootprintByReference('U7'); print('U7 pads with pad-to-die:', sum(1 for p in u7.Pads() if p.GetPadToDieDelay()))
print('TMP/BR nets left:', [m.FindNet(i).GetNetname() for i in range(m.GetNetCount()) if m.FindNet(i) and m.FindNet(i).GetNetname().startswith(('TMP_', 'BR_'))])
print('TP footprints left:', [f.GetReference() for f in m.GetFootprints() if f.GetReference().startswith('TP_')])
