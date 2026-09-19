# LPDDR4 delay report (board as of 2026-09-19, after DQS skew fix)

Delays from the JLC08161H-3313 profile (F/B 6.1, In2/In5 7.08 ps/mm, via 7.2 ps/mm of traversed height). Package delays NOT included. Negative = shorter than the reference.

## Byte lane 0 — DQS0: P 28.08 mm / 208.2 ps, N 28.08 mm / 208.2 ps (intra-pair 0.0 ps, 2 vias)

| Net | Length | Delay | vs DQS |
|---|---|---|---|
| dq0 | 24.13 mm | 174.4 ps (2 vias) | -33.8 ps |
| dq1 | 25.06 mm | 179.2 ps (2 vias) | -29.0 ps |
| dq2 | 22.46 mm | 162.6 ps (2 vias) | -45.7 ps |
| dq3 | 21.18 mm | 151.7 ps (2 vias) | -56.5 ps |
| dq4 | 22.82 mm | 171.0 ps (2 vias) | -37.2 ps |
| dq5 | 22.78 mm | 170.7 ps (2 vias) | -37.5 ps |
| dq6 | 21.63 mm | 155.0 ps (2 vias) | -53.2 ps |
| dq7 | 22.88 mm | 171.4 ps (2 vias) | -36.8 ps |
| dm0 | 26.00 mm | 158.6 ps (0 vias) | -49.6 ps |

## Byte lane 1 — DQS1: P 21.09 mm / 158.7 ps, N 21.06 mm / 158.5 ps (intra-pair 0.2 ps, 2 vias)

| Net | Length | Delay | vs DQS |
|---|---|---|---|
| dq8 | 23.99 mm | 171.7 ps (2 vias) | +13.0 ps |
| dq9 | 26.00 mm | 158.6 ps (0 vias) | -0.0 ps |
| dq10 | 16.91 mm | 129.2 ps (2 vias) | -29.5 ps |
| dq11 | 16.94 mm | 121.7 ps (2 vias) | -36.9 ps |
| dq12 | 22.80 mm | 163.2 ps (2 vias) | +4.6 ps |
| dq13 | 21.75 mm | 163.4 ps (2 vias) | +4.8 ps |
| dq14 | 26.01 mm | 158.7 ps (0 vias) | +0.0 ps |
| dq15 | 22.20 mm | 159.0 ps (2 vias) | +0.3 ps |
| dm1 | 26.00 mm | 158.6 ps (0 vias) | -0.0 ps |

## Byte lane 2 — DQS2: P 21.66 mm / 132.1 ps, N 21.66 mm / 132.1 ps (intra-pair 0.0 ps, 0 vias)

| Net | Length | Delay | vs DQS |
|---|---|---|---|
| dq16 | 24.00 mm | 171.7 ps (2 vias) | +39.6 ps |
| dq17 | 23.25 mm | 166.3 ps (2 vias) | +34.2 ps |
| dq18 | 24.01 mm | 171.8 ps (2 vias) | +39.7 ps |
| dq19 | 24.25 mm | 173.5 ps (2 vias) | +41.4 ps |
| dq20 | 23.18 mm | 173.5 ps (2 vias) | +41.4 ps |
| dq21 | 23.40 mm | 175.0 ps (2 vias) | +42.9 ps |
| dq22 | 23.95 mm | 171.4 ps (2 vias) | +39.3 ps |
| dq23 | 25.11 mm | 179.6 ps (2 vias) | +47.5 ps |
| dm2 | 24.00 mm | 171.7 ps (2 vias) | +39.6 ps |

## Byte lane 3 — DQS3: P 14.10 mm / 97.1 ps, N 14.10 mm / 97.1 ps (intra-pair 0.0 ps, 2 vias)

| Net | Length | Delay | vs DQS |
|---|---|---|---|
| dq24 | 15.25 mm | 93.0 ps (0 vias) | -4.1 ps |
| dq25 | 13.61 mm | 83.0 ps (0 vias) | -14.1 ps |
| dq26 | 19.24 mm | 145.7 ps (2 vias) | +48.6 ps |
| dq27 | 12.26 mm | 96.2 ps (2 vias) | -0.9 ps |
| dq28 | 22.78 mm | 170.7 ps (2 vias) | +73.6 ps |
| dq29 | 14.48 mm | 111.9 ps (2 vias) | +14.8 ps |
| dq30 | 20.69 mm | 126.2 ps (0 vias) | +29.1 ps |
| dq31 | 18.67 mm | 113.9 ps (0 vias) | +16.8 ps |
| dm3 | 12.73 mm | 77.7 ps (0 vias) | -19.4 ps |

## CA / CK — CK: P 21.12 mm / 159.0 ps, N 21.09 mm / 158.7 ps (fan-out to both channels included)

| Net | Length | Delay | vs CK |
|---|---|---|---|
| ca0 | 23.96 mm | 157.3 ps (3 vias) | -1.6 ps |
| ca1 | 27.77 mm | 169.4 ps (0 vias) | +10.5 ps |
| ca2 | 28.71 mm | 175.1 ps (0 vias) | +16.3 ps |
| ca3 | 23.01 mm | 151.4 ps (2 vias) | -7.4 ps |
| ca4 | 22.75 mm | 149.9 ps (2 vias) | -9.0 ps |
| ca5 | 21.84 mm | 144.3 ps (2 vias) | -14.5 ps |
| cke | 27.78 mm | 169.5 ps (0 vias) | +10.6 ps |
| ~{cs} | 23.50 mm | 154.4 ps (3 vias) | -4.4 ps |
| ~{rst} | 17.64 mm | 118.7 ps (2 vias) | -40.2 ps |

| DQS vs CK | |
|---|---|
| dqs0 | +49.4 ps |
| dqs1 | -0.1 ps |
| dqs2 | -26.8 ps |
| dqs3 | -61.7 ps |
