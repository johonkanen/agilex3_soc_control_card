# LPDDR4 delay report and tuner targets

`delay_report.py` grades the LPDDR4 routing against the Altera 821801 skew budgets, using KiCad's own delay
numbers. These include the per-layer tuning profiles, the via heights and the U7 pad `die_delay`, which holds the
Agilex 5 package delay.

```
export KICAD_APPRUN=<KiCad 10 AppImage>/AppRun      # or KICAD_CLI=kicad-cli
python3 tools/lpddr4_delay/delay_report.py -o LPDDR4_DELAY_REPORT.md          # report only (exit 1 if a check fails)
python3 tools/lpddr4_delay/delay_report.py --dru -o LPDDR4_DELAY_REPORT.md    # also rewrite the tuner targets
```

- **Delays:** the script runs `kicad-cli pcb drc` on a temporary copy, with an impossible delay window on every
  LPDDR4 net, and reads the actual delays from the violations.
- **T-nets:** CA/CKE/CS/CK split into one branch per channel. The two branches come from the copper (tree path
  delays: branch A = (d(U7,A) + d(A,B) − d(U7,B)) / 2), so die → ball = KiCad total − the other branch. The script's
  own copper total must reproduce KiCad's within 2 ps, or it reports an error.
- **Tuner offsets:** the report lists every tuning pattern whose last reading (`last_tuning_length`) differs from
  the delay above. On a T the tuner's path can take in part of the other branch; with `--dru`, a T-net offset of
  2 ps or more shifts that net's min/opt, so "Update all tuning patterns" lands the real die -> ball on target.
  Readings are as fresh as the last update: rerun the script after each update.
- **`--dru`:** replaces the `delay_report targets` block at the end of `agilex_3_soc.kicad_dru`. It writes one
  `length` window in ps per net, which is what KiCad's length tuner aims at. The targets are lengthen-only: the
  slowest net of each byte, and the slowest CA/CK die → ball delay.

Method and rules: `LPDDR4_DELAY_MATCHING.md`, section 4.
