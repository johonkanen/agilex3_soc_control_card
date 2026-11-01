#!/usr/bin/env python3
"""Download the datasheet of every part on the board into docs/datasheets/ (git-ignored) and write docs/DATASHEETS.md.

  python3 -I tools/datasheets/fetch_datasheets.py            # all parts
  python3 -I tools/datasheets/fetch_datasheets.py --only C692886,C5219375

Sources, per part group (same LCSC number / MPN / value / footprint):
  1. JLCPCB's assembly-library copy of the datasheet, by LCSC number (the parts API returns a signed download URL;
     LCSC's own datasheet links answer with an HTML page from here);
  2. the footprint's Datasheet field when it is an http(s) link, saved as <name>_mfr.pdf;
  3. EXTRA below: manufacturer documents for parts whose JLC copy is missing or abridged.
Plain standard library; reads the .kicad_pcb as text, no pcbnew needed.
"""
import argparse, json, os, re, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
BOARD = os.path.join(ROOT, 'agilex_3_soc.kicad_pcb')
OUT = os.path.join(ROOT, 'docs', 'datasheets')
INDEX_MD = os.path.join(ROOT, 'docs', 'DATASHEETS.md')
JLC_API = 'https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList'
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'}
# manufacturer documents worth having next to the JLC copy (file name -> URL)
EXTRA = {
    'TPS548A28_ti.pdf': 'https://www.ti.com/lit/ds/symlink/tps548a28.pdf',
    'ADS7056_ti.pdf': 'https://www.ti.com/lit/ds/symlink/ads7056.pdf',
    'SN74AXC4T774_ti.pdf': 'https://www.ti.com/lit/ds/symlink/sn74axc4t774.pdf',
    'SN74LV4051A_ti.pdf': 'https://www.ti.com/lit/ds/symlink/sn74lv4051a.pdf',
    'OPA365_ti.pdf': 'https://www.ti.com/lit/ds/symlink/opa365.pdf',
    'AX3_abracon.pdf': 'https://abracon.com/datasheets/AX3.pdf',
}


def parts(board):
    s = open(board, encoding='utf-8').read()
    groups = {}
    for m in re.finditer(r'(?ms)^\t\(footprint "([^"]+)"\n(.*?)^\t\)\n', s):
        body = m.group(2)
        prop = dict(re.findall(r'\(property "([^"]+)" "((?:[^"\\]|\\.)*)"', body))
        ref = prop.get('Reference', '?')
        if ref.startswith(('FID', 'H', 'TP')) and not prop.get('LCSC'):
            continue
        key = (prop.get('LCSC', ''), prop.get('MPN', ''), prop.get('Value', ''), m.group(1).split(':')[-1])
        g = groups.setdefault(key, dict(lcsc=key[0], mpn=key[1], value=key[2], footprint=key[3],
                                        datasheet=prop.get('Datasheet', ''), refs=[],
                                        dnp='(dnp yes)' in body or prop.get('Value', '').upper() == 'DNP'))
        g['refs'].append(ref)
    for g in groups.values():
        g['refs'].sort(key=lambda r: (re.sub(r'\d', '', r), int(re.sub(r'\D', '', r) or 0)))
    return sorted(groups.values(), key=lambda g: g['refs'][0])


def http(url, data=None, headers=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get('Content-Type', '')


def jlc_info(lcsc):
    body = json.dumps({'keyword': lcsc, 'currentPage': 1, 'pageSize': 5}).encode()
    raw, _ = http(JLC_API, body, {'Content-Type': 'application/json'})
    for c in (json.loads(raw).get('data') or {}).get('componentPageInfo', {}).get('list') or []:
        if c.get('componentCode') == lcsc:
            return c
    return None


def save_pdf(url, path):
    data, ctype = http(url, timeout=120)
    if not data.startswith(b'%PDF'):
        raise ValueError(f'not a PDF ({ctype}, {len(data)} bytes)')
    open(path, 'wb').write(data)
    return len(data)


def safe(name):
    return re.sub(r'[^A-Za-z0-9._+-]+', '_', name).strip('_')[:60]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', help='comma-separated LCSC numbers')
    ap.add_argument('--force', action='store_true', help='download again even if the file exists')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    only = set(a.only.split(',')) if a.only else None
    rows = []
    for g in parts(BOARD):
        if only and g['lcsc'] not in only:
            continue
        r = dict(g, files=[], status=[], mfr_part='', manufacturer='', jlc_page='')
        if g['lcsc']:
            try:
                c = jlc_info(g['lcsc'])
                if not c:
                    r['status'].append('JLC: part not found')
                else:
                    r['mfr_part'] = c.get('componentModelEn') or ''
                    r['manufacturer'] = c.get('componentBrandEn') or ''
                    r['jlc_page'] = c.get('lcscGoodsUrl') or ''
                    url = c.get('dataManualFileAccessIdUrl') or c.get('dataManualUrl')
                    fn = safe(f"{g['lcsc']}_{r['mfr_part'] or g['value']}") + '.pdf'
                    p = os.path.join(OUT, fn)
                    if os.path.exists(p) and not a.force:
                        r['files'].append(fn); r['status'].append('JLC: cached')
                    elif url:
                        n = save_pdf(url, p); r['files'].append(fn); r['status'].append(f'JLC: ok {n // 1024} kB')
                    else:
                        r['status'].append('JLC: no datasheet on file')
            except Exception as e:
                r['status'].append(f'JLC: {type(e).__name__}: {e}'[:120])
            time.sleep(0.5)
        else:
            r['status'].append('no LCSC number')
        ds = g['datasheet']
        if ds.startswith('http') and 'lcsc.com' not in ds:
            fn = safe(f"{g['lcsc'] or g['value']}_mfr") + '.pdf'
            p = os.path.join(OUT, fn)
            try:
                if os.path.exists(p) and not a.force:
                    r['files'].append(fn); r['status'].append('Datasheet field: cached')
                else:
                    n = save_pdf(ds, p); r['files'].append(fn); r['status'].append(f'Datasheet field: ok {n // 1024} kB')
            except Exception as e:
                r['status'].append(f'Datasheet field: {type(e).__name__}: {e}'[:120])
        rows.append(r)
        print(f"{','.join(r['refs'][:3]):18} {g['lcsc']:10} {(r['mfr_part'] or g['value'])[:28]:28} {'; '.join(r['status'])}", flush=True)
    extra = []
    if not only:
        for fn, url in EXTRA.items():
            p = os.path.join(OUT, fn)
            try:
                st = 'cached' if os.path.exists(p) and not a.force else f'ok {save_pdf(url, p) // 1024} kB'
            except Exception as e:
                st = f'{type(e).__name__}: {e}'[:120]
            extra.append((fn, url, st)); print(f'extra {fn}: {st}', flush=True)
        write_index(rows, extra)
    json.dump(rows, open(os.path.join(OUT, 'index.json'), 'w'), indent=1)


def write_index(rows, extra):
    L = ['# Datasheets', '',
         'Every part on `agilex_3_soc.kicad_pcb`, grouped by LCSC number / MPN / value / footprint, with where its',
         'datasheet comes from. The PDFs are copyrighted and git-ignored; `python3 -I tools/datasheets/fetch_datasheets.py`',
         'downloads them into `docs/datasheets/` (JLCPCB\'s library copy by LCSC number, plus manufacturer links). Generated',
         'by that script; the Altera documents are listed in `docs/README.md`.', '',
         '| Refs | Value | MPN (JLC) | Manufacturer | LCSC | Local file(s) | Status |', '|---|---|---|---|---|---|---|']
    for r in rows:
        refs = ', '.join(r['refs']) if len(r['refs']) <= 6 else ', '.join(r['refs'][:6]) + f" (+{len(r['refs']) - 6})"
        lcsc = f"[{r['lcsc']}]({r['jlc_page']})" if r['jlc_page'] else r['lcsc']
        files = '<br>'.join(f'`{f}`' for f in r['files']) or '–'
        st = '; '.join(r['status']).replace('|', '/')
        if r['dnp']:
            st = 'DNP; ' + st
        L.append(f"| {refs} | {r['value'].replace('|', '/')} | {r['mfr_part']} | {r['manufacturer']} | {lcsc} | {files} | {st} |")
    L += ['', '## Manufacturer documents', '', '| Local file | Source | Status |', '|---|---|---|']
    L += [f'| `{fn}` | <{url}> | {st} |' for fn, url, st in extra]
    open(INDEX_MD, 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    sys.exit(main())
