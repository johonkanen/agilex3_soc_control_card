"""Per net: die -> each U12 ball along the copper (Dijkstra), and total copper vs path copper.  python3.11 paths.py BOARD PREP_JSON"""
import sys, json, heapq, collections
import pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); P = json.load(open(sys.argv[2])); depth = P['depth']
PS = {'F.Cu': 6.1, 'B.Cu': 6.1, 'In2.Cu': 7.08, 'In5.Cu': 7.08}
mm = pcbnew.ToMM; IU = pcbnew.pcbIUScale.IU_PER_PS
R = lambda v: (round(mm(v.x) * 50), round(mm(v.y) * 50))
nets = list(P['info']) + ['~{rst}']
for s in nets:
    n = '/IOBANK 3/' + s
    segs = [t for t in b.GetTracks() if t.GetNetname() == n and t.Type() != pcbnew.PCB_VIA_T]
    vias = [t for t in b.GetTracks() if t.GetNetname() == n and t.Type() == pcbnew.PCB_VIA_T]
    pads = [p for p in b.GetPads() if p.GetNetname() == n]
    g = collections.defaultdict(list)
    def edge(a, c, w, L=0, lay=None):
        g[a].append((c, w, L, lay)); g[c].append((a, w, L, lay))
    for t in segs:
        L = mm(t.GetLength()); lay = t.GetLayerName()
        edge((R(t.GetStart()), lay), (R(t.GetEnd()), lay), L * PS.get(lay, 7.0), L, lay)
    def join(pos, layers):
        layers = sorted(layers, key=lambda l: depth[l])
        for a, c in zip(layers, layers[1:]): edge((pos, a), (pos, c), abs(depth[a] - depth[c]) * 7.2)
    cu = list(depth)
    for v in vias: join(R(v.GetPosition()), cu)
    # attach segment ends that land inside a pad / via (not exactly on centre)
    nodes = list(g)
    for v in vias:
        for (q, lay) in nodes:
            if (q[0] - R(v.GetPosition())[0]) ** 2 + (q[1] - R(v.GetPosition())[1]) ** 2 <= (0.15 * 50) ** 2:
                edge((q, lay), (R(v.GetPosition()), lay), 0)
    for p in pads:
        pl = [l for l in cu if p.IsOnLayer(b.GetLayerID(l))]
        for (q, lay) in nodes:
            if lay in pl and p.HitTest(pcbnew.VECTOR2I(int(q[0] / 50 * 1e6), int(q[1] / 50 * 1e6))):
                edge((q, lay), (R(p.GetPosition()), lay), 0)
        if len(pl) > 1: join(R(p.GetPosition()), pl)
    src = [p for p in pads if p.GetParentFootprint().GetReference() == 'U7'][0]
    dst = [p for p in pads if p.GetParentFootprint().GetReference() == 'U12']
    start = (R(src.GetPosition()), 'F.Cu'); dist = {start: 0}; prev = {}; h = [(0, start)]
    while h:
        d, u = heapq.heappop(h)
        if d > dist.get(u, 1e9): continue
        for v, w, L, lay in g[u]:
            if d + w < dist.get(v, 1e9): dist[v] = d + w; prev[v] = (u, L, lay); heapq.heappush(h, (d + w, v))
    die = src.GetPadToDieDelay() / IU
    tot = sum(mm(t.GetLength()) for t in segs)
    out = []
    for p in dst:
        k = (R(p.GetPosition()), 'F.Cu')
        if k not in dist: out.append(f'{p.GetNumber()} OPEN'); continue
        L = collections.Counter(); u = k
        while u in prev: u2, l, lay = prev[u]; L[lay or "via"] += l; u = u2
        out.append(f'{p.GetNumber()} {dist[k] + die:.1f}ps (' + ' '.join(f'{a[:3]} {v:.1f}' for a, v in sorted(L.items()) if v) + ')')
    pathL = sum(float(x.split()[-1]) for x in []) 
    print(f'{s:6s} die {die:5.1f}  copper {tot:6.2f} mm  ' + ' | '.join(out))
