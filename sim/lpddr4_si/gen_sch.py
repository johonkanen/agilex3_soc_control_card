"""Write the LPDDR4 SI simulation schematic (KiCad 10, IBIS + TLINE + L/C), one channel per case.

  python3 gen_sch.py OUT.kicad_sch [--zdq 40] [--ldq 20] [--zca 40] [--via-dq long|short] [--corner typ|min|max]

The committed lpddr4_si.kicad_sch is the baseline (40 ohm, 20 mm). run_si.py writes one schematic per sweep point
into work/, exports it with kicad-cli (which runs KiCad's IBIS-to-SPICE converter) and runs ngspice on it.
Every element is a normal KiCad simulation symbol, so the file also opens and simulates in Eeschema.

Channels (all uncoupled, all in one netlist):
  dqw    DQ write   U7 driver lvstl11_io_s3r40c_doff (pin T62)  -> via -> neck -> line -> neck -> via -> U12 ODT_48
  dqr40  DQ read    U12 PD40_ODT80_VOH25 (40 ohm, PU-CAL VDDQ/2.5) -> same channel reversed -> U7 lvstl11_in_e0g50c
  dqr48  DQ read    U12 PD48_ODT80_VOH25 (48 ohm)
  ca0_80 / ca0_60   CA0 (longest trunk) U7 B66 -> via -> In2 trunk -> T-via -> 2 B.Cu branches -> via -> CA_ODT_80/60
  ca5_80            CA5 (shortest trunk)
"""
import argparse, json, os, re, uuid

KSYM = os.path.join(os.path.dirname(os.environ.get('KICAD_APPRUN', '')), 'usr/share/kicad/symbols')
AGX = ('agilex5_lpddr4.ibs', 'Agilex5_A5EB013BB23BE6S')   # (file in models/, IBIS [Component])
MEM = ('w66_lpddr4.ibs', 'W66CL2NQUAFJ')

# stack-up (field solved, see LPDDR4_SWIZZLE_PLAN.md); ps/mm
PS_IN, PS_OUT = 7.02, 6.16
Z_NECK_IN, Z_NECK_OUT = 55.0, 60.0          # 0.10 mm neck-downs (extrapolated from the 0.12/0.18 and 0.15/0.20 solves)
NECK_MM = 1.5                               # neck-down length at each BGA
VIA = {'short': (0.15e-9, 0.40e-12),        # F.Cu <-> In2 (0.24 mm span), 0.3/0.15 mm via, C incl. the stub
       'long': (0.50e-9, 0.40e-12)}         # F.Cu <-> In5 / In2 <-> B.Cu / B.Cu <-> F.Cu (1.3-1.5 mm span)
# CA, from the board (tools/lpddr4_krt/paths.py, 2026-10-27): In2 trunk / B.Cu branch (0.10 mm) lengths in mm
CA = {'ca0': dict(pin='B66', trunk=27.99, br=2.43, mem=('H2', 'R2')),
      'ca5': dict(pin='A66', trunk=10.77, br=1.76, mem=('J11', 'P11'))}
DQ_PIN, DQ_MEM = 'T62', 'C11'               # U7 DQ[9] (largest package L*C of the DQ pins); U12 DQ9_A
UI = 625e-12


def uid(): return str(uuid.uuid4())


def eng(v):
    for e, s in ((1e9, 'G'), (1e6, 'Meg'), (1, ''), (1e-3, 'm'), (1e-6, 'u'), (1e-9, 'n'), (1e-12, 'p'), (1e-15, 'f')):
        if abs(v) >= e * 0.999: return f'{v / e:.4g}{s}'
    return f'{v:.4g}'


def lib_symbol(lib, name):
    t = open(os.path.join(KSYM, f'{lib}.kicad_symdir', f'{name}.kicad_sym')).read()
    i = t.find(f'(symbol "{name}"')
    body = t[i:t.rstrip().rfind(')')].rstrip()
    return body.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)


def pins_of(lib, name):
    t = open(os.path.join(KSYM, f'{lib}.kicad_symdir', f'{name}.kicad_sym')).read()
    return {m[2]: (float(m[0]), float(m[1])) for m in
            re.findall(r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) [-\d.]+\).*?\(number "(\w+)"', t, re.S)}


class Sch:
    def __init__(self, models):
        self.models = models; self.root = uid(); self.items = []; self.libs = {}; self.n = {}; self.x = 25.4; self.y = 25.4

    def prop(self, k, v, x, y, hide=True):
        return (f'\t\t(property "{k}" "{v}"\n\t\t\t(at {x:.2f} {y:.2f} 0)\n\t\t\t(effects\n\t\t\t\t(font\n'
                f'\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n{"				(hide yes)" + chr(10) if hide else ""}\t\t\t)\n\t\t)\n')

    def sym(self, lib, name, pfx, nets, value='', props=None):
        key = f'{lib}:{name}'
        if key not in self.libs: self.libs[key] = (lib_symbol(lib, name), pins_of(lib, name))
        pins = self.libs[key][1]
        self.n[pfx] = self.n.get(pfx, 0) + 1; ref = f'{pfx}{self.n[pfx]}'
        x, y = self.x, self.y
        s = (f'\t(symbol\n\t\t(lib_id "{key}")\n\t\t(at {x:.2f} {y:.2f} 0)\n\t\t(unit 1)\n\t\t(exclude_from_sim no)\n'
             f'\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n\t\t(uuid "{uid()}")\n')
        s += self.prop('Reference', ref, x, y - 6.35, False) + self.prop('Value', value or name, x, y + 7.62, False)
        s += self.prop('Footprint', '', x, y) + self.prop('Datasheet', '', x, y)
        for k, v in (props or {}).items(): s += self.prop(k, v, x, y)
        for p in pins: s += f'\t\t(pin "{p}"\n\t\t\t(uuid "{uid()}")\n\t\t)\n'
        s += (f'\t\t(instances\n\t\t\t(project "lpddr4_si"\n\t\t\t\t(path "/{self.root}"\n\t\t\t\t\t(reference "{ref}")\n'
              f'\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n')
        self.items.append(s)
        for p, net in nets.items():   # a local label on each pin end (no wires needed)
            px, py = pins[p]
            self.items.append(f'\t(label "{net}"\n\t\t(at {x + px:.2f} {y - py:.2f} 0)\n\t\t(effects\n\t\t\t(font\n'
                              f'\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "{uid()}")\n\t)\n')
        self.x += 30.48
        return ref

    def text(self, s, x, y):
        s = s.replace('"', '\\"').replace('\n', '\\n')
        self.items.append(f'\t(text "{s}"\n\t\t(exclude_from_sim no)\n\t\t(at {x:.2f} {y:.2f} 0)\n\t\t(effects\n'
                          f'\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n'
                          f'\t\t(uuid "{uid()}")\n\t)\n')

    def row(self, title):
        self.y += 30.48; self.x = 25.4
        self.text(title, 25.4, self.y - 12.7)

    # elements
    def ibis(self, kind, lib, pin, model, net, params='', stype=None):
        name = 'IBIS_DRIVER' if kind == 'drv' else 'IBIS_DEVICE'
        st = stype or ('PRBSDRIVER' if kind == 'drv' else 'IBISDEVICE')
        props = {'Sim.Device': 'IBIS', 'Sim.Type': st, 'Sim.Pins': '1=GND 2=IN/OUT',
                 'Sim.Library': f'{self.models}/{lib[0]}', 'Sim.Name': lib[1], 'Sim.Ibis.Pin': pin,
                 'Sim.Ibis.Model': model}
        if params: props['Sim.Params'] = params
        return self.sym('Simulation_SPICE', name, 'U', {'1': 'GND', '2': net}, f'{model}', props)

    def tl(self, a, b, z0, td):
        return self.sym('Simulation_SPICE', 'TLINE', 'TL', {'1': a, '2': 'GND', '3': b, '4': 'GND'},
                        f'TLINE {z0:g}R {td * 1e12:.1f}ps',
                        {'Sim.Device': 'TLINE', 'Sim.Pins': '1=1+ 2=1- 3=2+ 4=2-',
                         'Sim.Params': f'z0={z0:g} td={eng(td)}'})

    def via(self, a, b, kind):
        L, C = VIA[kind]
        self.sym('Device', 'C', 'C', {'1': a, '2': 'GND'}, eng(C / 2))
        self.sym('Device', 'L', 'L', {'1': a, '2': b}, eng(L))
        self.sym('Device', 'C', 'C', {'1': b, '2': 'GND'}, eng(C / 2))


def build_validate(a):
    """Each driver model as a RECTDRIVER into the IBIS waveform fixture (50 ohm to GND), to compare the converted
    model with the [Rising/Falling Waveform] tables (run_si.py --validate strips the package from the subcircuit)."""
    s = Sch(a.models); meta = {}
    s.text('.tran 1p 8n', 25.4, 15.24)
    for tag, lib, pin, model in (('agx_dq', AGX, DQ_PIN, 'lvstl11_io_s3r40c_doff'), ('mem_pd40', MEM, DQ_MEM, 'PD40_ODT80_VOH25'),
                                 ('mem_pd48', MEM, DQ_MEM, 'PD48_ODT80_VOH25')):
        s.row(f'{tag}: {model} into 50 ohm to GND')
        meta[tag] = dict(kind='validate', model=model, lib=lib[0],
                         drv=s.ibis('drv', lib, pin, model, f'{tag}_o', 'ton=3n toff=3n td=1n n=1', 'RECTDRIVER'))
        s.sym('Device', 'R', 'R', {'1': f'{tag}_o', '2': 'GND'}, '50')
    return finish(s, meta)


def finish(s, meta):
    libs = ''.join('\t\t' + v[0].replace('\n', '\n\t') + '\n' for v in s.libs.values())
    return meta, (f'(kicad_sch\n\t(version 20250114)\n\t(generator "eeschema")\n\t(generator_version "10.0")\n'
                  f'\t(uuid "{s.root}")\n\t(paper "A2")\n\t(lib_symbols\n{libs}\t)\n' + ''.join(s.items) +
                  '\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)\n\t(embedded_fonts no)\n)\n')


def build(a):
    s = Sch(a.models); meta = {}
    prbs = f'f0={eng(1 / UI)} n={a.bits}'   # KIBIS PRBS7 (x^7+x^6+1, seed 0x12): f0 = bit rate
    # KiCad 10 compares the corner with "MIN"/"MAX" (upper case); the lower-case enum values silently give typ.
    # C_comp is typ in every corner (KiCad 10).
    c = a.corner.upper()
    corner = '' if a.corner == 'typ' else f' vcc={c} rpin={c} lpin={c} cpin={c}'
    s.text(f'LPDDR4 SI, generated by gen_sch.py: DQ line {a.zdq:g} ohm {a.ldq:g} mm (via {a.via_dq}), '
           f'CA trunk {a.zca:g} ohm, corner {a.corner}. 1600 MT/s, PRBS.', 25.4, 10.16)
    s.text(f'.tran 1p {a.bits * UI * 1e9 + 2:.1f}n\n.options method=gear maxord=2 reltol=1e-4', 25.4, 15.24)
    tdq = (a.ldq - 2 * NECK_MM) * PS_IN * 1e-12
    tneck = NECK_MM * PS_IN * 1e-12

    def dq_channel(tag, near, far):   # near = U7 side net, far = U12 side net
        s.via(near, f'{tag}_n1', a.via_dq)
        zn = max(Z_NECK_IN, a.zdq)   # a line narrower than the 0.10 mm neck-down needs no neck-down
        s.tl(f'{tag}_n1', f'{tag}_l1', zn, tneck)
        s.tl(f'{tag}_l1', f'{tag}_l2', a.zdq, tdq)
        s.tl(f'{tag}_l2', f'{tag}_n2', zn, tneck)
        s.via(f'{tag}_n2', far, a.via_dq)

    s.row('dqw: DQ write, U7 40 ohm -> U12 ODT 48 ohm')
    d = s.ibis('drv', AGX, DQ_PIN, 'lvstl11_io_s3r40c_doff', 'dqw_u7', prbs + corner)
    dq_channel('dqw', 'dqw_u7', 'dqw_u12')
    meta['dqw'] = dict(kind='dq_write', drv=d, rx=[(s.ibis('rx', MEM, DQ_MEM, 'ODT_48', 'dqw_u12', corner.strip()),
                                                    'dqw_u12')])
    for tag, model in (('dqr40', 'PD40_ODT80_VOH25'), ('dqr48', 'PD48_ODT80_VOH25')):
        s.row(f'{tag}: DQ read, U12 {model} -> U7 50 ohm ODT')
        d = s.ibis('drv', MEM, DQ_MEM, model, f'{tag}_u12', prbs + corner)
        dq_channel(tag, f'{tag}_u7', f'{tag}_u12')
        meta[tag] = dict(kind='dq_read', drv=d, rx=[(s.ibis('rx', AGX, DQ_PIN, 'lvstl11_in_e0g50c', f'{tag}_u7',
                                                              corner.strip()), f'{tag}_u7')])
    for tag, ca, odt in (('ca0_80', 'ca0', 80), ('ca0_60', 'ca0', 60), ('ca5_80', 'ca5', 80)):
        c = CA[ca]
        s.row(f'{tag}: {ca} T, U7 40 ohm -> In2 trunk {c["trunk"]} mm -> T-via -> 2 x B.Cu {c["br"]} mm -> CA ODT {odt}')
        meta[tag] = dict(kind='ca', drv=s.ibis('drv', AGX, c['pin'], 'lvstl11_io_s3r40c_doff', f'{tag}_u7',
                                               prbs + corner), rx=[])
        s.via(f'{tag}_u7', f'{tag}_t0', 'short')
        s.tl(f'{tag}_t0', f'{tag}_t1', a.zca, c['trunk'] * PS_IN * 1e-12)
        s.via(f'{tag}_t1', f'{tag}_tb', 'long')
        for i, mp in enumerate(c['mem']):
            s.tl(f'{tag}_tb', f'{tag}_b{i}', Z_NECK_OUT, c['br'] * PS_OUT * 1e-12)
            s.via(f'{tag}_b{i}', f'{tag}_u12{"ab"[i]}', 'long')
            meta[tag]['rx'].append((s.ibis('rx', MEM, mp, f'CA_ODT_{odt}', f'{tag}_u12{"ab"[i]}', corner.strip()),
                                    f'{tag}_u12{"ab"[i]}'))

    return finish(s, meta)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('out')
    p.add_argument('--zdq', type=float, default=40.0)
    p.add_argument('--ldq', type=float, default=20.0)
    p.add_argument('--zca', type=float, default=40.0)
    p.add_argument('--via-dq', default='long', choices=list(VIA))
    p.add_argument('--corner', default='typ', choices=['typ', 'min', 'max'])
    p.add_argument('--bits', type=int, default=150)
    p.add_argument('--validate', action='store_true', help='driver-into-fixture schematic instead')
    p.add_argument('--models', default='models', help='models/ folder, relative to the schematic')
    a = p.parse_args()
    meta, text = (build_validate if a.validate else build)(a)
    open(a.out, 'w').write(text)
    json.dump(meta, open(os.path.splitext(a.out)[0] + '.json', 'w'), indent=1)   # case -> driver / receivers
