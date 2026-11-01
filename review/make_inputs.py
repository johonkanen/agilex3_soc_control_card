#!/usr/bin/env python3
"""Regenerate the frozen review inputs in review/inputs/ from the current commit.

  K=<unpacked KiCad AppImage>/squashfs-root/AppRun python3 -I review/make_inputs.py

Writes netlist.xml / netlist.net (kicad-cli), u7_balls.csv (every U7 ball in the netlist joined with Altera's pin
list), u7_balls_not_in_netlist.csv (Altera balls the U7 symbol lacks) and COMMIT. Needs the Altera pin list as CSV
(agilex_pinout_files/a5eb013b.Pin_List_B23B.csv, from tools/datasheets/xlsx2csv.py). Commit or stash first: the
inputs describe the committed state.
"""
import collections, csv, os, subprocess, sys
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
OUT = os.path.join(ROOT, 'review', 'inputs')
PINLIST = os.path.join(ROOT, 'agilex_pinout_files', 'a5eb013b.Pin_List_B23B.csv')


def main():
    k = os.environ.get('K')
    if not k:
        sys.exit('set K to the KiCad AppImage AppRun (see review/README.md)')
    if subprocess.run(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT, capture_output=True,
                      text=True).stdout.strip():
        print('warning: uncommitted changes; the inputs will not match COMMIT', file=sys.stderr)
    os.makedirs(OUT, exist_ok=True)
    env = dict(os.environ, KICAD10_SYMBOL_DIR=os.environ.get(
        'KICAD10_SYMBOL_DIR', '/mnt/c/Program Files/KiCad/10.0/share/kicad/symbols'))
    for fmt, fn in (('kicadxml', 'netlist.xml'), ('kicadsexpr', 'netlist.net')):
        subprocess.run([k, 'kicad-cli', 'sch', 'export', 'netlist', '--format', fmt, '-o', os.path.join(OUT, fn),
                        os.path.join(ROOT, 'agilex_3_soc.kicad_sch')], check=True, env=env, capture_output=True)
    root = ET.parse(os.path.join(OUT, 'netlist.xml')).getroot()
    pins, members = collections.defaultdict(list), {}
    for n in root.iter('net'):
        nodes = [(x.get('ref'), x.get('pin'), x.get('pinfunction') or '', x.get('pintype') or '') for x in n.iter('node')]
        members[n.get('name')] = nodes
        for ref, pin, fn, tp in nodes:
            pins[(ref, pin)].append((n.get('name'), fn, tp))
    alt = {r[8]: r for r in csv.reader(open(PINLIST)) if len(r) > 8 and r[8] and r[0] != 'Bank Number'}
    rows = []
    for (ref, pin), v in pins.items():
        if ref != 'U7':
            continue
        net, fn, tp = v[0]
        others = [f'{a}.{b}' for a, b, _, _ in members[net] if a != 'U7'][:8]
        a = alt.get(pin, [''] * 12)
        rows.append([pin, net, fn, tp, sum(1 for x in members[net] if x[0] == 'U7'), ';'.join(others),
                     a[0], a[2], a[3], a[4], a[5]])
    with open(os.path.join(OUT, 'u7_balls.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['ball', 'net', 'symbol_pin_function', 'pintype', 'u7_pins_on_net', 'other_members(first 8)',
                    'alt_bank', 'alt_pin_name', 'alt_optional', 'alt_config', 'alt_hps'])
        w.writerows(sorted(rows))
    missing = sorted(set(alt) - {r[0] for r in rows})
    with open(os.path.join(OUT, 'u7_balls_not_in_netlist.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['ball', 'alt_bank', 'alt_pin_name', 'alt_optional', 'alt_config', 'alt_hps'])
        w.writerows([b, alt[b][0], alt[b][2], alt[b][3], alt[b][4], alt[b][5]] for b in missing)
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout
    open(os.path.join(OUT, 'COMMIT'), 'w').write(head)
    print(f'{len(rows)} U7 balls in the netlist, {len(missing)} Altera balls not in it; commit {head.strip()}')


if __name__ == '__main__':
    main()
