Into the 50 ohm V-t fixture (package removed):

| variant | driver model | edge | V start / end, IBIS (mV) | V start / end, KiCad (mV) | t20-80, IBIS (ps) | t20-80, KiCad (ps) |
|---|---|---|---|---|---|---|
| typ | lvstl11_io_s3r40c_doff | rising | 0 / 617 | 0 / 617 | 38.0 | 37.0 |
| typ | lvstl11_io_s3r40c_doff | falling | 617 / 0 | 617 / 0 | 36.0 | 37.0 |
| typ | PD40_ODT80_VOH25 | rising | 0 / 365 | -0 / 365 | 37.0 | 41.0 |
| typ | PD40_ODT80_VOH25 | falling | 365 / 0 | 365 / -0 | 32.0 | 32.0 |
| typ | PD48_ODT80_VOH25 | rising | 0 / 365 | 0 / 365 | 37.0 | 35.0 |
| typ | PD48_ODT80_VOH25 | falling | 365 / 0 | 365 / -0 | 28.0 | 39.0 |
| min_kw | lvstl11_io_s3r40c_doff | rising | 0 / 601 | 0 / 601 | 36.0 | 38.0 |
| min_kw | lvstl11_io_s3r40c_doff | falling | 601 / 0 | 601 / 0 | 36.0 | 36.0 |
| min_kw | PD40_ODT80_VOH25 | rising | 0 / 355 | 0 / 355 | 44.0 | 35.0 |
| min_kw | PD40_ODT80_VOH25 | falling | 356 / 1 | 355 / 0 | 26.0 | 26.0 |
| min_kw | PD48_ODT80_VOH25 | rising | 0 / 355 | 0 / 355 | 50.0 | 46.0 |
| min_kw | PD48_ODT80_VOH25 | falling | 356 / 1 | 355 / -0 | 32.0 | 32.0 |
| max_kw | lvstl11_io_s3r40c_doff | rising | 0 / 636 | 0 / 635 | 43.0 | 43.0 |
| max_kw | lvstl11_io_s3r40c_doff | falling | 636 / 0 | 635 / 0 | 39.0 | 40.0 |
| max_kw | PD40_ODT80_VOH25 | rising | 0 / 394 | -0 / 394 | 29.0 | 29.0 |
| max_kw | PD40_ODT80_VOH25 | falling | 394 / -0 | 394 / 0 | 25.0 | 25.0 |
| max_kw | PD48_ODT80_VOH25 | rising | 0 / 394 | -0 / 394 | 32.0 | 32.0 |
| max_kw | PD48_ODT80_VOH25 | falling | 394 / -0 | 394 / 0 | 29.0 | 20.0 |
| min_files | lvstl11_io_s3r40c_doff | rising | 0 / 601 | 0 / 601 | 36.0 | 37.0 |
| min_files | lvstl11_io_s3r40c_doff | falling | 601 / 0 | 601 / 0 | 36.0 | 36.0 |
| min_files | PD40_ODT80_VOH25 | rising | 0 / 355 | 0 / 355 | 44.0 | 35.0 |
| min_files | PD40_ODT80_VOH25 | falling | 356 / 1 | 355 / 0 | 26.0 | 26.0 |
| min_files | PD48_ODT80_VOH25 | rising | 0 / 355 | 0 / 355 | 50.0 | 46.0 |
| min_files | PD48_ODT80_VOH25 | falling | 356 / 1 | 355 / -0 | 32.0 | 32.0 |
| max_files | lvstl11_io_s3r40c_doff | rising | 0 / 636 | 0 / 635 | 43.0 | 43.0 |
| max_files | lvstl11_io_s3r40c_doff | falling | 636 / 0 | 635 / 0 | 39.0 | 40.0 |
| max_files | PD40_ODT80_VOH25 | rising | 0 / 394 | -0 / 394 | 29.0 | 29.0 |
| max_files | PD40_ODT80_VOH25 | falling | 394 / -0 | 394 / 0 | 25.0 | 25.0 |
| max_files | PD48_ODT80_VOH25 | rising | 0 / 394 | -0 / 394 | 32.0 | 32.0 |
| max_files | PD48_ODT80_VOH25 | falling | 394 / -0 | 394 / 0 | 29.0 | 20.0 |

DC high level into each load (package removed), against the model's own V-I tables:

| variant | driver model | load (ohm) | DC high from V-I (mV) | KiCad (mV) | KiCad - V-I (mV) |
|---|---|---|---|---|---|
| typ | lvstl11_io_s3r40c_doff | 50 | 617 | 617 | -0 |
| typ | lvstl11_io_s3r40c_doff | 48 | 606 | 605 | -0 |
| typ | lvstl11_io_s3r40c_doff | 60 | 666 | 665 | -0 |
| typ | lvstl11_io_s3r40c_doff | 80 | 739 | 738 | -1 |
| typ | lvstl11_io_s3r40c_doff | open | 1100 | 1099 | -1 |
| typ | PD40_ODT80_VOH25 | 50 | 365 | 365 | -0 |
| typ | PD40_ODT80_VOH25 | 48 | 359 | 358 | -0 |
| typ | PD40_ODT80_VOH25 | 60 | 393 | 392 | -1 |
| typ | PD40_ODT80_VOH25 | 80 | 435 | 435 | -0 |
| typ | PD40_ODT80_VOH25 | open | 1041 | 883 | -158 |
| typ | PD48_ODT80_VOH25 | 50 | 365 | 365 | -1 |
| typ | PD48_ODT80_VOH25 | 48 | 359 | 358 | -1 |
| typ | PD48_ODT80_VOH25 | 60 | 393 | 392 | -1 |
| typ | PD48_ODT80_VOH25 | 80 | 435 | 435 | -1 |
| typ | PD48_ODT80_VOH25 | open | 1040 | 877 | -163 |
| min_kw | lvstl11_io_s3r40c_doff | 50 | 601 | 601 | -0 |
| min_kw | lvstl11_io_s3r40c_doff | 48 | 591 | 590 | -0 |
| min_kw | lvstl11_io_s3r40c_doff | 60 | 649 | 648 | -0 |
| min_kw | lvstl11_io_s3r40c_doff | 80 | 720 | 719 | -0 |
| min_kw | lvstl11_io_s3r40c_doff | open | 1067 | 1066 | -1 |
| min_kw | PD40_ODT80_VOH25 | 50 | 356 | 355 | -1 |
| min_kw | PD40_ODT80_VOH25 | 48 | 350 | 349 | -1 |
| min_kw | PD40_ODT80_VOH25 | 60 | 382 | 379 | -3 |
| min_kw | PD40_ODT80_VOH25 | 80 | 422 | 416 | -6 |
| min_kw | PD40_ODT80_VOH25 | open | 1024 | 666 | -358 |
| min_kw | PD48_ODT80_VOH25 | 50 | 356 | 355 | -2 |
| min_kw | PD48_ODT80_VOH25 | 48 | 350 | 349 | -1 |
| min_kw | PD48_ODT80_VOH25 | 60 | 382 | 379 | -3 |
| min_kw | PD48_ODT80_VOH25 | 80 | 422 | 416 | -6 |
| min_kw | PD48_ODT80_VOH25 | open | 1024 | 667 | -356 |
| max_kw | lvstl11_io_s3r40c_doff | 50 | 636 | 635 | -1 |
| max_kw | lvstl11_io_s3r40c_doff | 48 | 624 | 624 | -1 |
| max_kw | lvstl11_io_s3r40c_doff | 60 | 686 | 685 | -1 |
| max_kw | lvstl11_io_s3r40c_doff | 80 | 761 | 760 | -1 |
| max_kw | lvstl11_io_s3r40c_doff | open | 1133 | 1131 | -2 |
| max_kw | PD40_ODT80_VOH25 | 50 | 394 | 394 | -0 |
| max_kw | PD40_ODT80_VOH25 | 48 | 387 | 387 | -1 |
| max_kw | PD40_ODT80_VOH25 | 60 | 426 | 429 | +3 |
| max_kw | PD40_ODT80_VOH25 | 80 | 473 | 483 | +9 |
| max_kw | PD40_ODT80_VOH25 | open | 1056 | 2055 | +1000 |
| max_kw | PD48_ODT80_VOH25 | 50 | 394 | 394 | -0 |
| max_kw | PD48_ODT80_VOH25 | 48 | 387 | 387 | -1 |
| max_kw | PD48_ODT80_VOH25 | 60 | 426 | 429 | +3 |
| max_kw | PD48_ODT80_VOH25 | 80 | 473 | 482 | +9 |
| max_kw | PD48_ODT80_VOH25 | open | 1057 | 2054 | +997 |
| min_files | lvstl11_io_s3r40c_doff | 50 | 601 | 601 | -0 |
| min_files | lvstl11_io_s3r40c_doff | 48 | 591 | 590 | -0 |
| min_files | lvstl11_io_s3r40c_doff | 60 | 649 | 648 | -0 |
| min_files | lvstl11_io_s3r40c_doff | 80 | 720 | 719 | -1 |
| min_files | lvstl11_io_s3r40c_doff | open | 1067 | 1066 | -1 |
| min_files | PD40_ODT80_VOH25 | 50 | 356 | 355 | -1 |
| min_files | PD40_ODT80_VOH25 | 48 | 350 | 349 | -1 |
| min_files | PD40_ODT80_VOH25 | 60 | 382 | 380 | -2 |
| min_files | PD40_ODT80_VOH25 | 80 | 422 | 420 | -2 |
| min_files | PD40_ODT80_VOH25 | open | 1024 | 822 | -201 |
| min_files | PD48_ODT80_VOH25 | 50 | 356 | 355 | -2 |
| min_files | PD48_ODT80_VOH25 | 48 | 350 | 349 | -1 |
| min_files | PD48_ODT80_VOH25 | 60 | 382 | 380 | -2 |
| min_files | PD48_ODT80_VOH25 | 80 | 422 | 420 | -2 |
| min_files | PD48_ODT80_VOH25 | open | 1024 | 818 | -205 |
| max_files | lvstl11_io_s3r40c_doff | 50 | 636 | 635 | -1 |
| max_files | lvstl11_io_s3r40c_doff | 48 | 624 | 624 | -1 |
| max_files | lvstl11_io_s3r40c_doff | 60 | 686 | 685 | -1 |
| max_files | lvstl11_io_s3r40c_doff | 80 | 761 | 760 | -1 |
| max_files | lvstl11_io_s3r40c_doff | open | 1133 | 1131 | -2 |
| max_files | PD40_ODT80_VOH25 | 50 | 394 | 394 | -0 |
| max_files | PD40_ODT80_VOH25 | 48 | 387 | 387 | -0 |
| max_files | PD40_ODT80_VOH25 | 60 | 426 | 426 | -0 |
| max_files | PD40_ODT80_VOH25 | 80 | 473 | 473 | -0 |
| max_files | PD40_ODT80_VOH25 | open | 1056 | 945 | -111 |
| max_files | PD48_ODT80_VOH25 | 50 | 394 | 394 | -0 |
| max_files | PD48_ODT80_VOH25 | 48 | 387 | 387 | -0 |
| max_files | PD48_ODT80_VOH25 | 60 | 426 | 426 | -0 |
| max_files | PD48_ODT80_VOH25 | 80 | 473 | 473 | -0 |
| max_files | PD48_ODT80_VOH25 | open | 1057 | 937 | -120 |
