"""Build the two IBIS files the simulation uses, in models/ (git-ignored), from the vendor originals.

  python3 prep_models.py QUARTUS_IBS [WINBOND_IBS]

1. models/agilex5_lpddr4.ibs: the IBIS file Quartus writes for the varA_ron48 build (quartus_eda
   --board_signal_integrity=on --format=ibis), plus the 50 ohm calibrated-OCT receiver models lvstl11_in_e0g50c and
   dlvstl11_in_e0g50c copied from Quartus' Agilex 5 EMIF IBIS library. Their [Algorithmic Model] (AMI DLL) blocks are
   dropped: this is an analog-only simulation. The Quartus file itself only has the output buffers of the build
   (lvstl11_io_s3r40c_doff: 40 ohm calibrated, fastest slew, de-emphasis off), not the read termination.
2. models/w66_lpddr4.ibs: Winbond W66CL2NQUAFJ (public stand-in for the SK hynix part). Its [Package] is all zero and
   the package lives in a sparse [Define Package Model] matrix that KiCad's IBIS converter does not read; the self
   R/L/C of each pin (matrix diagonal) is written into the [Pin] R_pin/L_pin/C_pin columns instead (no coupling).
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, 'models')
QLIB = os.environ.get('QUARTUS_ROOTDIR', '/home/jari/altera_pro/26.1.1/quartus') + \
    '/common/misc/ibis_writer/input_files/agilex_5_device_emif_ami.ibs'
RX_MODELS = ['lvstl11_in_e0g50c', 'dlvstl11_in_e0g50c']


def extract_models(path, names):
    """[Model] blocks by name from a (large) IBIS file, read line by line."""
    out, cur = {}, None
    with open(path, errors='replace') as f:
        for line in f:
            if line.startswith('[Model]'):
                n = line.split()[1]
                cur = n if n in names else None
                if cur: out[cur] = []
            elif line.startswith(('[End]', '[Define Package Model]', '[Model Selector]')):
                cur = None
            if cur: out[cur].append(line)
    missing = set(names) - set(out)
    if missing: sys.exit(f'models not found in {path}: {missing}')
    return {n: re.sub(r'\[Algorithmic Model\].*?\[End Algorithmic Model\]\n', '', ''.join(v), flags=re.S)
            for n, v in out.items()}


def agilex(qibs):
    src = open(qibs).read()
    # KiCad's parser rejects [R Series] (the REFCLK series-termination model): drop it and its pin mapping
    src = re.sub(r'\[Series Pin Mapping\].*?\n(?=\|)', '', src, flags=re.S)
    src = re.sub(r'\[Model\] R_ser_out_tds_11V_100\n.*?(?=\n\[Model\]|\n\[End\])', '', src, flags=re.S)
    blks = extract_models(QLIB, RX_MODELS)
    i = src.rfind('[End]')
    open(os.path.join(MODELS, 'agilex5_lpddr4.ibs'), 'w').write(src[:i] + ''.join(blks[n] for n in RX_MODELS) + src[i:])


def sparse_diag(text, name):
    j = text.find(f'[{name} Matrix]')
    body = text[j:]
    m = re.search(r'\n\[(?!Row\])', body[5:])
    body = body[:m.start() + 5] if m else body
    d = {}
    for r in re.split(r'\[Row\]\s+', body)[1:]:
        lines = [l.split('|')[0].split() for l in r.strip().splitlines()]
        pin = lines[0][0]
        for l in lines[1:]:
            if len(l) >= 2 and l[0] == pin: d[pin] = float(l[1])
    return d


def winbond(wibs):
    t = open(wibs).read()
    pkg = t[t.find('[Define Package Model]'):]
    L, C, R = (sparse_diag(pkg, n) for n in ('Inductance', 'Capacitance', 'Resistance'))
    out, in_pin = [], False
    for line in t.splitlines(keepends=True):
        if line.startswith('[Pin]'):
            in_pin = True   # KiCad's parser matches R_pin/L_pin/C_pin case-sensitively; Winbond writes R_Pin
            line = '[Pin] Signal_Name   Model_Name  R_pin  L_pin C_pin\n'
        elif line.startswith('['):
            in_pin = False
        elif in_pin and line.strip() and not line.startswith('|'):
            f = line.split()
            if len(f) == 3:   # pin, signal, model: add the package self R/L/C where the matrix has the pin
                p = f[0]
                rlc = (f'{R[p]:.4f}  {L[p] * 1e9:.4f}nH  {C[p] * 1e12:.4f}pF' if p in L and p in C and p in R
                       else 'NA  NA  NA')
                line = f'{f[0]:8s}{f[1]:10s}{f[2]:12s}{rlc}\n'
        out.append(line)
    open(os.path.join(MODELS, 'w66_lpddr4.ibs'), 'w').write(''.join(out))


if __name__ == '__main__':
    os.makedirs(MODELS, exist_ok=True)
    agilex(sys.argv[1])
    winbond(sys.argv[2] if len(sys.argv) > 2 else os.path.join(MODELS, 'w66cl2nquafj_a001.ibs'))
    print('wrote', os.path.join(MODELS, 'agilex5_lpddr4.ibs'), os.path.join(MODELS, 'w66_lpddr4.ibs'))
