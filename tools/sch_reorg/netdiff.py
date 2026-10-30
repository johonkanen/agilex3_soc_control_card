#!/usr/bin/env python3
"""netdiff.py before.xml after.xml - compare two KiCad XML netlists by connectivity (SCHEMATIC_REORG_PLAN.md 4.2).

A net is the set of its ref.pin; names are compared only for nets with the same pins. A reorganisation step is OK when
it prints 0 connectivity diffs (or exactly the intended ones) and only the renames that were meant.
"""
import sys, xml.etree.ElementTree as ET


def load(path):
    root = ET.parse(path).getroot()
    comps = {c.get('ref'): (c.findtext('value'), c.findtext('footprint')) for c in root.find('components')}
    nets = {}
    for n in root.find('nets'):
        nets[frozenset(f"{p.get('ref')}.{p.get('pin')}" for p in n)] = n.get('name')
    return comps, nets


(ca, na), (cb, nb) = load(sys.argv[1]), load(sys.argv[2])
for r in sorted(ca.keys() - cb.keys()): print('PART REMOVED ', r, ca[r])
for r in sorted(cb.keys() - ca.keys()): print('PART ADDED   ', r, cb[r])
for r in sorted(ca.keys() & cb.keys()):
    if ca[r] != cb[r]: print('PART CHANGED ', r, ca[r], '->', cb[r])
auto = lambda s: s.startswith(('Net-(', 'unconnected-('))
renamed = [(na[p], nb[p]) for p in na.keys() & nb.keys() if na[p] != nb[p]]
for a, b in sorted(renamed):
    print('RENAMED      ', a, '->', b, '(auto name)' if auto(a) or auto(b) else '')
for p in na.keys() - nb.keys(): print('NET CHANGED  ', na[p], sorted(p))
for p in nb.keys() - na.keys(): print('NET NEW      ', nb[p], sorted(p))
print(f'{len(ca)}->{len(cb)} parts, {len(na)}->{len(nb)} nets, '
      f'{len(renamed)} renamed, {len(na.keys() ^ nb.keys())} connectivity diffs')
