"""Dump the routed LPDDR4 copper (U7 <-> U12) as a graph per net, for routed_si.py. Runs in KiCad's Python:

  $KICAD_APPRUN python3.11 extract_routes.py [../../agilex_3_soc.kicad_pcb] [work/routes.json]

Per net: track and arc pieces (layer, length), vias (position, which layers have copper attached) and the U7 / U12
pads. Nodes are track end points snapped to 5 um, per layer; a via joins the end points within its pad radius on
every layer, a pad the F.Cu end points inside it and a via in the pad.
"""
import json, os, sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
board = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '../../agilex_3_soc.kicad_pcb')
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'work', 'routes.json')
PFX = '/IOBANK 3/'
SKIP = ('hb', 'rzq', '~{rst}')
SNAP = 5000   # nm

b = pcbnew.LoadBoard(board)
ln = b.GetLayerName
key = lambda x, y, layer: f'{round(x / SNAP)},{round(y / SNAP)},{layer}'
nets = {}
for t in b.GetTracks():
    n = t.GetNetname()
    if not n.startswith(PFX) or n[len(PFX):].startswith(SKIP): continue
    d = nets.setdefault(n[len(PFX):], dict(segs=[], vias=[], pads=[]))
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition()
        d['vias'].append(dict(x=p.x, y=p.y, r=t.GetWidth(pcbnew.F_Cu) // 2, top=ln(t.TopLayer()), bot=ln(t.BottomLayer())))
    else:
        s, e = t.GetStart(), t.GetEnd()
        d['segs'].append(dict(a=key(s.x, s.y, ln(t.GetLayer())), b=key(e.x, e.y, ln(t.GetLayer())),
                              layer=ln(t.GetLayer()), mm=t.GetLength() / 1e6, w=t.GetWidth() / 1e6,
                              pa=(s.x, s.y), pb=(e.x, e.y)))
for fp in b.GetFootprints():
    if fp.GetReference() not in ('U7', 'U12'): continue
    for p in fp.Pads():
        n = p.GetNetname()
        if n.startswith(PFX) and n[len(PFX):] in nets:
            nets[n[len(PFX):]]['pads'].append(dict(ref=fp.GetReference(), ball=p.GetNumber(), pad=p))

for name, d in nets.items():
    ends = {}
    for s in d['segs']:
        ends[s['a']] = (s['pa'], s['layer']); ends[s['b']] = (s['pb'], s['layer'])
    for i, v in enumerate(d['vias']):   # via: attached layer nodes
        v['id'] = f'via{i}'
        v['att'] = sorted({(lay, k) for k, ((x, y), lay) in ends.items()
                           if (x - v['x']) ** 2 + (y - v['y']) ** 2 <= v['r'] ** 2}, key=str)
    pads = []
    for p in d['pads']:
        pad = p.pop('pad'); att = []
        for k, ((x, y), lay) in ends.items():
            if lay == 'F.Cu' and pad.HitTest(pcbnew.VECTOR2I(int(x), int(y))): att.append(k)
        vias = [v['id'] for v in d['vias'] if pad.HitTest(pcbnew.VECTOR2I(int(v['x']), int(v['y'])))]
        pads.append(dict(ref=p['ref'], ball=p['ball'], att=att, vias=vias))
    d['pads'] = pads
    for s in d['segs']: s.pop('pa'); s.pop('pb')
    for v in d['vias']: v['att'] = [list(a) for a in v['att']]

os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump(nets, open(out, 'w'), indent=0)
print(f'{len(nets)} nets -> {out}')
