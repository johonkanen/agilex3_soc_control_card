"""KRT trunk trial, prep:  python3.11 prep.py IN OUT
- U7 pad-to-die delays from the Quartus .pin file (all LPDDR4 balls).
- For each shared CA/CK net: a temporary 1-pad THT footprint TP_<net> on the existing T-via (pad-to-die = branch delay
  T -> U12 ball), the T-via removed, the branches and ball vias parked on BR_<net> (ends next to T pulled back 0.25 mm),
  the U12 pads parked on TMP_<net>. Other copper of these nets (U7-side fan-out vias) is removed.
Original branch coordinates go to prep.json for finish.py."""
import sys, json, math, os, re
import pcbnew
IN, OUT = sys.argv[1:3]
FM, mm = pcbnew.FromMM, pcbnew.ToMM
IU_PER_PS = pcbnew.pcbIUScale.IU_PER_PS
SHARED = ['ca0', 'ca1', 'ca2', 'ca3', 'ca4', 'ca5', 'cke', '~{cs}', 'ck_P', 'ck_N']
PFX = '/IOBANK 3/'
PS = {'F.Cu': 6.1, 'B.Cu': 6.1, 'In2.Cu': 7.08, 'In5.Cu': 7.08}
VIA_PS_MM = 7.2
PULL = 0.25
b = pcbnew.LoadBoard(IN)

# layer depths from the stack-up (copper centre), for via-span delays
txt = open(IN).read()
st = txt[txt.find('(stackup'):]; st = st[:st.find('\n\t\t)\n')]
z, depth = 0.0, {}
for name, th in re.findall(r'\(layer "([^"]+)"[^()]*?(?:\([^()]*\)[^()]*?)*?\(thickness ([\d.]+)\)', st):
    if name.endswith('.Cu'): depth[name] = z + float(th) / 2
    if not name.endswith(('Mask', 'Paste', 'SilkS')): z += float(th)
def via_ps(l1, l2): return abs(depth[l1] - depth[l2]) * VIA_PS_MM

# 1) U7 pad-to-die
pin = os.environ.get('PINFILE', os.path.expanduser('~/dev/agilex5_emif_test/varA_bswap/output_files/emif_test.pin'))
delay = {}
for l in open(pin):
    f = [x.strip() for x in l.split(':')]
    if len(f) > 6 and f[0].startswith('LPDDR4_') and f[-1].endswith('ps'): delay[f[1]] = float(f[-1][:-2])
u7 = b.FindFootprintByReference('U7'); n7 = 0
for p in u7.Pads():
    if p.GetNumber() in delay:
        p.SetPadToDieDelay(int(round(delay[p.GetNumber()] * IU_PER_PS))); n7 += 1
print(f'prep: U7 pad-to-die set on {n7} pads')

def new_net(name):
    code = max(b.FindNet(i).GetNetCode() for i in range(b.GetNetCount()) if b.FindNet(i) is not None) + 1
    ni = pcbnew.NETINFO_ITEM(b, name, code); b.Add(ni); return ni

u12 = b.FindFootprintByReference('U12'); bb = u12.GetCourtyard(pcbnew.F_CrtYd).BBox()
saved, doomed, info = {}, [], {}
for s in SHARED:
    net = b.FindNet(PFX + s)
    pads = [p for p in u12.Pads() if p.GetNetname() == PFX + s]
    tr = [t for t in b.GetTracks() if t.GetNetname() == PFX + s]
    vias = [t for t in tr if t.Type() == pcbnew.PCB_VIA_T]
    segs = [t for t in tr if t.Type() != pcbnew.PCB_VIA_T]
    ball = lambda v: any((v.GetPosition() - p.GetPosition()).EuclideanNorm() < 20000 for p in pads)
    tv = [v for v in vias if not ball(v) and bb.Contains(v.GetPosition())]
    assert len(tv) == 1, (s, len(tv))
    T = tv[0].GetPosition(); tx, ty = mm(T.x), mm(T.y)
    lay = {t.GetLayerName() for t in segs if bb.Contains(t.GetStart())}; assert len(lay) == 1, (s, lay); lay = lay.pop()
    Lbr = sum(mm(t.GetLength()) for t in segs if bb.Contains(t.GetStart()) and bb.Contains(t.GetEnd())) / 2
    d_br = Lbr * PS[lay] + via_ps('F.Cu', lay)          # branch + ball via (pad on F.Cu)
    info[s] = dict(T=(tx, ty), layer=lay, branch_mm=round(Lbr, 4), branch_ps=round(d_br, 2))
    # temporary T pad
    fp = pcbnew.FOOTPRINT(b); fp.SetReference('TP_' + s); fp.SetPosition(T)
    pad = pcbnew.PAD(fp); pad.SetNumber('1'); pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
    pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE); pad.SetSize(pcbnew.VECTOR2I(FM(0.3), FM(0.3)))
    pad.SetDrillSize(pcbnew.VECTOR2I(FM(0.15), FM(0.15))); pad.SetLayerSet(pcbnew.PAD.PTHMask())
    pad.SetPosition(T); pad.SetNet(net); pad.SetPadToDieDelay(int(round(d_br * IU_PER_PS))); fp.Add(pad); b.Add(fp)
    br, tmp = new_net('BR_' + s), new_net('TMP_' + s)
    for t in segs:
        if not bb.Contains(t.GetStart()):
            doomed.append(t); continue
        a, c = t.GetStart(), t.GetEnd()
        saved[t.m_Uuid.AsString()] = [s, mm(a.x), mm(a.y), mm(c.x), mm(c.y)]
        for end, other, setter in ((a, c, t.SetStart), (c, a, t.SetEnd)):
            if (end - T).EuclideanNorm() < 2000:
                L = (other - end).EuclideanNorm(); k = min(FM(PULL) / L, 0.9)
                setter(pcbnew.VECTOR2I(int(end.x + (other.x - end.x) * k), int(end.y + (other.y - end.y) * k)))
        t.SetNet(br)
    for v in vias:
        if v is tv[0] or not ball(v): doomed.append(v)
        else: v.SetNet(br)
    for p in pads: p.SetNet(tmp)
for t in doomed: b.Remove(t)
json.dump(dict(saved=saved, info=info, depth=depth), open(os.path.join(os.path.dirname(OUT) or '.', 'prep.json'), 'w'), indent=1)
pcbnew.SaveBoard(OUT, b)
for s, v in info.items(): print('prep:', s, v)
print(f'prep: removed {len(doomed)} T-vias/other copper; depths', {k: round(v, 3) for k, v in depth.items()})
