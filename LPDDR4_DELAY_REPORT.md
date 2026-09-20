# LPDDR4 delay report – board state 2026-09-19 (after hand tuning to 178 ps)

Delays computed from the board file with the same numbers as the KiCad tuning profiles: F/B.Cu 6.1 ps/mm, In2/In5 7.08 ps/mm, In6 6.97 ps/mm, vias 7.2 ps/mm of traversed stack height (F→In2 0.25 mm = 1.8 ps, F→In5 1.31 mm = 9.4 ps, F→B 1.54 mm = 11.1 ps, each end). Disconnected copper pieces are ignored.

**Important:** the nets you tuned all show a *track* delay of exactly 178.0 ps, i.e. the number KiCad gave you did not include the via-in-pad transitions (the pad sits on F.Cu, the track on an inner layer). Physically an In2 route is 178 + 3.6 = 181.6 ps and an In5 route 178 + 18.9 = 196.9 ps, so "all at 178" is really a 15 ps spread. Tune with per-layer targets: F.Cu route target T, In2 route T − 3.6, In5 route T − 18.9, B.Cu route T − 22.2 (T = the lane's DQS delay including its own vias).

## Verdict per group (target = the lane's DQS_P, tolerance ±5 ps DQ/DM to DQS, ±5 ps CA to CK, pairs ≤ 2 ps)

| Group | Reference | Status |
|---|---|---|
| Lane 0 | dqs0_P 217.7 / dqs0_N 204.8 (pair skew 12.9 ps – fix first) | dq0–3, dq6 −36…−38; dq4, dq5, dq7 −13…−21; dm0 −69 (untuned, F.Cu) |
| Lane 1 | dqs1_P 168.2 / N 164.6 (3.6 ps) | dq8, 11, 12, 15 +13; dq10, dq13 +29; dq9 −52, dq14 −34, dm1 −28 (untuned F.Cu) |
| Lane 2 | dqs2_P 131.5 / N 127.5 (4.0 ps) | every DQ +48…+65 (DQS is 45 ps *shorter* than the tuned DQ); dq22 has a 0.14 mm gap on In2 at (155.7, 102.8) |
| Lane 3 | dqs3_P 108.2 / N 105.2 (3.0 ps) | dq26–29 +89…+96; dq24/25/30/31/dm3 −29…+18 (untuned F.Cu) |
| CA/CK | ck_P 166.7 / ck_N 157.9 (8.8 ps – fix first) | ca0 +59, ~{rst} +38, ~{cs} +18, ca1 −23, cke −39, ca3/ca4 −51/−55, ca2 −65, ca5 −69 |
| DQS↔CK | | dqs0 +51, dqs1 +2, dqs2 −35, dqs3 −59 ps vs ck_P |

So: not OK yet. Nothing is matched to its strobe; the 178 ps target only equalised the inner-layer DQ lines among themselves (and only their track part).

## Suggested order

1. Fix the pair skews: dqs0 (P is 1.8 mm longer than N) and ck (P 1.2 mm longer than N); dqs1/2/3 are 3–4 ps, bring to ≤ 2 ps.
2. Pick one target per lane = that lane's DQS delay (with vias). Lanes 2 and 3 have short strobes (131 / 108 ps); either lengthen dqs2/dqs3 to ~180 ps or shorten those DQ lines – shortening is the better signal-integrity choice where the escape allows it.
3. Tune DQ/DM to the target using the per-layer corrections above. DM lines and the F.Cu DQs (dq9, dq14, dq24, dq25, dq30, dq31, dm0–dm3) are still untuned.
4. CA/CKE/CS/RST to ck_P ±5 ps; then bring the four DQS groups to within the EMIF guideline of CK (check the Agilex 5 EMIF IP user guide length-matching table for the exact DQS-to-CK window; the controller calibrates tDQSCK, so this is the loosest constraint).
5. Close the dq22 gap and the open stubs on dq4 (In5, 164.4/100.7–101.9) and dq5 (In5, 171.2/95.4).

## Full table
    == lane 0: dqs0_P/N
      dqs0_P     217.7 ps  (track  198.8 + via  18.9;  28.1 mm, 2 vias; In5:28.1)
      dqs0_N     204.8 ps  (track  185.9 + via  18.9;  26.3 mm, 2 vias; In5:26.3)
      dq0        179.8 ps  (track  176.2 + via   3.6;  24.9 mm, 2 vias; F.C:0.1 In2:24.8)
      dq1        181.6 ps  (track  178.0 + via   3.6;  25.1 mm, 2 vias; In2:25.1)
      dq2        179.7 ps  (track  176.1 + via   3.6;  24.9 mm, 2 vias; F.C:0.0 In2:24.8)
      dq3        181.6 ps  (track  178.0 + via   3.6;  25.1 mm, 2 vias; In2:25.1)
      dq4        204.9 ps  (track  186.0 + via  18.9;  26.3 mm, 2 vias; In5:26.3)
      dq5        201.4 ps  (track  182.5 + via  18.9;  25.8 mm, 2 vias; In5:25.8)
      dq6        181.6 ps  (track  178.0 + via   3.6;  25.1 mm, 2 vias; In2:25.1)
      dq7        196.9 ps  (track  178.0 + via  18.9;  25.1 mm, 2 vias; In5:25.1)
      dm0        148.2 ps  (track  148.2 + via   0.0;  24.3 mm, 0 vias; F.C:24.3)
       DQ - DQS_P: dq0 -37.9, dq1 -36.0, dq2 -38.0, dq3 -36.1, dq4 -12.8, dq5 -16.3, dq6 -36.1, dq7 -20.8, dm0 -69.4
    == lane 1: dqs1_P/N
      dqs1_P     168.2 ps  (track  149.3 + via  18.9;  21.1 mm, 2 vias; In5:21.1)
      dqs1_N     164.6 ps  (track  145.7 + via  18.9;  20.6 mm, 2 vias; In5:20.6)
      dq8        181.6 ps  (track  178.0 + via   3.6;  25.1 mm, 2 vias; In2:25.1)  [1 disconnected pieces ignored]
      dq9        116.7 ps  (track  116.7 + via   0.0;  19.1 mm, 0 vias; F.C:19.1)
      dq10       196.9 ps  (track  178.0 + via  18.9;  25.1 mm, 2 vias; In5:25.1)
      dq11       181.6 ps  (track  178.0 + via   3.6;  25.1 mm, 2 vias; In2:25.1)
      dq12       181.6 ps  (track  178.0 + via   3.6;  25.1 mm, 2 vias; In2:25.1)
      dq13       196.9 ps  (track  178.0 + via  18.9;  25.1 mm, 2 vias; In5:25.1)
      dq14       134.3 ps  (track  134.3 + via   0.0;  22.0 mm, 0 vias; F.C:22.0)
      dq15       181.6 ps  (track  178.0 + via   3.6;  25.1 mm, 2 vias; In2:25.1)
      dm1        139.9 ps  (track  139.9 + via   0.0;  22.9 mm, 0 vias; F.C:22.9)
       DQ - DQS_P: dq8 +13.4, dq9 -51.5, dq10 +28.7, dq11 +13.4, dq12 +13.4, dq13 +28.7, dq14 -33.9, dq15 +13.4, dm1 -28.2
    == lane 2: dqs2_P/N
      dqs2_P     131.5 ps  (track  131.5 + via   0.0;  21.6 mm, 0 vias; F.C:21.6)
      dqs2_N     127.5 ps  (track  127.5 + via   0.0;  20.9 mm, 0 vias; F.C:20.9)
      dq16       181.6 ps  (track  178.0 + via   3.6;  25.1 mm, 2 vias; In2:25.1)
      dq17       179.7 ps  (track  176.1 + via   3.6;  24.9 mm, 2 vias; F.C:0.1 In2:24.8)
      dq18       181.6 ps  (track  178.0 + via   3.6;  25.1 mm, 2 vias; In2:25.1)
      dq19       185.7 ps  (track  182.1 + via   3.6;  25.7 mm, 2 vias; In2:25.7)
      dq20       196.9 ps  (track  178.0 + via  18.9;  25.1 mm, 2 vias; In5:25.1)
      dq21       187.4 ps  (track  168.5 + via  18.9;  23.8 mm, 2 vias; F.C:0.1 In5:23.7)
      dq22         7.2 ps  (track    5.4 + via   1.8;   0.8 mm, 1 vias; In2:0.8)  [69 disconnected pieces ignored]
      dq23       181.6 ps  (track  178.0 + via   3.6;  25.1 mm, 2 vias; In2:25.1)  [1 disconnected pieces ignored]
      dm2        181.6 ps  (track  178.0 + via   3.6;  25.1 mm, 2 vias; In2:25.1)
       DQ - DQS_P: dq16 +50.1, dq17 +48.2, dq18 +50.1, dq19 +54.2, dq20 +65.4, dq21 +55.9, dq22 -124.3, dq23 +50.1, dm2 +50.1
    == lane 3: dqs3_P/N
      dqs3_P     108.2 ps  (track   86.0 + via  22.2;  14.1 mm, 2 vias; B.C:14.1)
      dqs3_N     105.2 ps  (track   83.0 + via  22.2;  13.6 mm, 2 vias; B.C:13.6)
      dq24        93.7 ps  (track   93.7 + via   0.0;  15.4 mm, 0 vias; F.C:15.4)
      dq25        83.0 ps  (track   83.0 + via   0.0;  13.6 mm, 0 vias; F.C:13.6)
      dq26       196.9 ps  (track  178.0 + via  18.9;  25.1 mm, 2 vias; In5:25.1)
      dq27       196.9 ps  (track  178.0 + via  18.9;  25.1 mm, 2 vias; In5:25.1)
      dq28       204.0 ps  (track  185.1 + via  18.9;  26.2 mm, 2 vias; In5:26.2)
      dq29       196.9 ps  (track  178.0 + via  18.9;  25.1 mm, 2 vias; In5:25.1)
      dq30       126.2 ps  (track  126.2 + via   0.0;  20.7 mm, 0 vias; F.C:20.7)
      dq31       113.9 ps  (track  113.9 + via   0.0;  18.7 mm, 0 vias; F.C:18.7)
      dm3         78.9 ps  (track   78.9 + via   0.0;  12.9 mm, 0 vias; F.C:12.9)
       DQ - DQS_P: dq24 -14.5, dq25 -25.2, dq26 +88.7, dq27 +88.7, dq28 +95.8, dq29 +88.7, dq30 +18.0, dq31 +5.7, dm3 -29.3
    == CA / CK
      ck_P       166.7 ps  (track  146.0 + via  20.7;  20.6 mm, 4 vias; In2:18.9 In5:1.7)
      ck_N       157.9 ps  (track  137.2 + via  20.7;  19.4 mm, 4 vias; In2:17.7 In5:1.7)
      ca0        226.0 ps  (track  192.7 + via  33.3;  31.6 mm, 3 vias; B.C:31.6)
      ca1        143.6 ps  (track  143.6 + via   0.0;  23.5 mm, 0 vias; F.C:23.5)
      ca2        101.2 ps  (track  101.2 + via   0.0;  16.6 mm, 0 vias; F.C:16.6)
      ca3        115.5 ps  (track   93.3 + via  22.2;  15.3 mm, 2 vias; B.C:4.9 F.C:10.4)
      ca4        111.8 ps  (track   89.6 + via  22.2;  14.7 mm, 2 vias; B.C:4.9 F.C:9.8)
      ca5         97.9 ps  (track   75.8 + via  22.2;  12.4 mm, 2 vias; B.C:3.5 F.C:8.9)
      cke        127.8 ps  (track  127.8 + via   0.0;  21.0 mm, 0 vias; F.C:21.0)
      ~{cs}      184.6 ps  (track  151.3 + via  33.3;  24.8 mm, 3 vias; B.C:4.9 F.C:19.9)
      ~{rst}     204.4 ps  (track  182.2 + via  22.2;  29.9 mm, 2 vias; B.C:29.9)
       CA - CK_P: ca0 +59.3, ca1 -23.0, ca2 -65.4, ca3 -51.2, ca4 -54.9, ca5 -68.7, cke -38.8, ~{cs} +17.9, ~{rst} +37.7
       DQS_P - CK_P: dqs0 +51.0, dqs1 +1.5, dqs2 -35.2, dqs3 -58.5
