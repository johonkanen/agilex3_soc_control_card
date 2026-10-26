"""KRT trunk trial, finish:  python3.11 finish.py IN OUT PREP_JSON
T pads -> through vias, BR_/TMP_ copper and U12 pads back on their nets (branch ends snapped back onto T),
routed LPDDR4 tracks on F/B clamped to 0.20 mm, zones refilled."""
import sys, json
import pcbnew
IN, OUT, PJ = sys.argv[1:4]
FM, mm = pcbnew.FromMM, pcbnew.ToMM
info = json.load(open(PJ))['info']
b = pcbnew.LoadBoard(IN)
names = {b.FindNet(i).GetNetname(): b.FindNet(i) for i in range(b.GetNetCount()) if b.FindNet(i) is not None}
real = lambda s: names['/IOBANK 3/' + s]
tps = [f for f in b.GetFootprints() if f.GetReference().startswith('TP_')]
for f in tps:
    v = pcbnew.PCB_VIA(b); v.SetPosition(f.GetPosition()); v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetWidth(FM(0.3)); v.SetDrill(FM(0.15)); v.SetNet(list(f.Pads())[0].GetNet()); b.Add(v)
snapped = 0
for t in list(b.GetTracks()):
    n = t.GetNetname()
    if n.startswith(('BR_', 'TMP_')):
        s = n.split('_', 1)[1]; t.SetNet(real(s))
        if t.Type() != pcbnew.PCB_VIA_T:
            T = pcbnew.VECTOR2I(FM(info[s]['T'][0]), FM(info[s]['T'][1]))
            for end, setter in ((t.GetStart(), t.SetStart), (t.GetEnd(), t.SetEnd)):
                if (end - T).EuclideanNorm() < FM(0.26): setter(T); snapped += 1
for p in b.FindFootprintByReference('U12').Pads():
    if p.GetNetname().startswith('TMP_'): p.SetNet(real(p.GetNetname()[4:]))
clamped = 0
routed = {'/IOBANK 3/' + s for s in info} | {'/IOBANK 3/~{rst}'}
for t in b.GetTracks():
    if t.Type() != pcbnew.PCB_VIA_T and t.GetNetname() in routed and t.GetLayerName() in ('F.Cu', 'B.Cu') and t.GetWidth() > FM(0.2001):
        t.SetWidth(FM(0.2)); clamped += 1
for f in tps: b.Remove(f)
for n in list(names):
    if n.startswith(('BR_', 'TMP_')): b.Remove(names[n])
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(OUT, b)
print(f'finish: {len(tps)} T vias back, {snapped} branch ends snapped, {clamped} F/B tracks clamped to 0.20 mm')
