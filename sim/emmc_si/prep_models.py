"""Build models/agilex5_hps_sdmmc.ibs (git-ignored) from the IBIS file Quartus writes for a build with the HPS SD/eMMC
pins (~/dev/agilex5_emif_test/varA_hpsmux):

  quartus_eda emif_test -c emif_test --board_signal_integrity=on --format=ibis --output_directory=ibis
  python3 prep_models.py ibis/emif_test_emif_test_a5eb013bb23be6s.ibs

The SDMMC pins (AU74 CMD, AY67 CCLK, BC64.. DATA0-7) use 1p8_io_d8s1 (1.8 V LVCMOS I/O, 8 mA, slew 1). KiCad 10.0.7's
parser throws (vector range check) on the full file, so only that model and its pins are kept (plus the POWER/GND
pins); [Define Package Model], [Diff Pin] and [Pin Mapping] are dropped. The per-pin R/L/C stay in [Pin].
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../../tools/kicad_ibis_simulation'))
from kicad_ibis import ibisfix

KEEP = '1p8_io_d8s1'
t = ibisfix.fix(open(sys.argv[1], errors='replace').read())
t = re.sub(r'\n\[Define Package Model\].*?\[End Package Model\][^\n]*\n', '\n', t, flags=re.S)
t = re.sub(r'\n\[(Diff Pin|Pin Mapping)\].*?(?=\n\[)', '\n', t, flags=re.S)
blocks = re.split(r'(?=\n\[Model\] )', t)
model = [re.sub(r'\n\[End\].*', '', b, flags=re.S) for b in blocks[1:] if b.split()[1] == KEEP]


def pins(m):
    keep = lambda l: l.startswith(('|', '[')) or len(l.split()) < 3 or l.split()[2] in (KEEP, 'POWER', 'GND', 'NC')
    return '\n'.join(l for l in m.group(0).split('\n') if keep(l))


head = re.sub(r'\[Pin\].*?(?=\n\[|\Z)', pins, blocks[0], flags=re.S)
os.makedirs(os.path.join(HERE, 'models'), exist_ok=True)
open(os.path.join(HERE, 'models', 'agilex5_hps_sdmmc.ibs'), 'w').write(head + ''.join(model) + '\n[End]\n')
print(f'models/agilex5_hps_sdmmc.ibs written ({KEEP} only)')
