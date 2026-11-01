#!/usr/bin/env python3
"""Convert every sheet of an .xlsx file to CSV (standard library only, no openpyxl).

  python3 -I tools/datasheets/xlsx2csv.py agilex_pinout_files/a5eb013b.xlsx     # -> a5eb013b.<sheet>.csv beside it
"""
import csv, os, re, sys, zipfile
import xml.etree.ElementTree as ET

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def col_index(ref):
    n = 0
    for ch in re.match(r'[A-Z]+', ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n - 1


def convert(path):
    z = zipfile.ZipFile(path)
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', NS):
            shared.append(''.join(t.text or '' for t in si.iter('{%s}t' % NS['m'])))
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    out = []
    for sh in wb.find('m:sheets', NS):
        target = rels[sh.get('{%s}id' % NS['r'])].lstrip('/')
        target = target if target.startswith('xl/') else 'xl/' + target
        rows = []
        for row in ET.fromstring(z.read(target)).iter('{%s}row' % NS['m']):
            vals = {}
            for c in row.findall('m:c', NS):
                v = c.find('m:v', NS); t = c.get('t')
                if t == 'inlineStr':
                    txt = ''.join(x.text or '' for x in c.iter('{%s}t' % NS['m']))
                elif v is None:
                    continue
                elif t == 's':
                    txt = shared[int(v.text)]
                else:
                    txt = v.text
                vals[col_index(c.get('r'))] = txt
            if vals:
                rows.append([vals.get(i, '') for i in range(max(vals) + 1)])
        name = re.sub(r'[^A-Za-z0-9_-]+', '_', sh.get('name'))
        dst = f'{os.path.splitext(path)[0]}.{name}.csv'
        with open(dst, 'w', newline='') as f:
            csv.writer(f).writerows(rows)
        out.append((dst, len(rows)))
    return out


if __name__ == '__main__':
    for p in sys.argv[1:]:
        for dst, n in convert(p):
            print(f'{dst}: {n} rows')
