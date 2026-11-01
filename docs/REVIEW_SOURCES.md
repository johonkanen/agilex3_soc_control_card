# Sources for the pre-order review

What the review agents need, where it lives, and whether it can be fetched without a person. Checked 2026-11-01 on
the build machine. Vendor documents are copyrighted and git-ignored; this file and `DATASHEETS.md` only hold links.

## Retrieval status

| Source | Location | How to get it | Status |
|---|---|---|---|
| Altera documents for U7 (pin connection guidelines, power management, configuration, device data sheet, HPS booting) | `docs/*.pdf` | manual download, links in `docs/README.md` | present, all open (46-269 pages) |
| A5EB013B pinout | `agilex_pinout_files/a5eb013b.xlsx`, `.pdf`; CSV per sheet `a5eb013b.<sheet>.csv` | manual download (`docs/README.md`); CSV with `tools/datasheets/xlsx2csv.py` | present; `Pin_List_B23B.csv` has 795 balls |
| B23B ball coordinates and land pattern | `docs/agilex5_b23b_ball_coordinates_land_pattern.xlsx` + `.csv` per sheet | manual download; CSV with `xlsx2csv.py` | present |
| Agilex 5 PCB design guidelines (821801), cited by `agilex_3_soc.kicad_dru` | `docs/821801_agilex5_pcb_design_guidelines.pdf` | manual download from <https://docs.altera.com/r/docs/821801/current>; the site serves a JavaScript page to scripts | **missing** |
| Datasheets of every other part | `docs/datasheets/` (index `DATASHEETS.md`) | `python3 -I tools/datasheets/fetch_datasheets.py` (JLCPCB library copy by LCSC number, plus manufacturer links) | 73 of 78 part groups fetched; the rest are U7 (Altera documents above), the DNP resistors and the gaps below |
| JLCPCB PCB capabilities | <https://jlcpcb.com/capabilities/pcb-capabilities> | plain HTTP, readable text | ok |
| JLCPCB stack-up JLC08161H-3313 | board setup (`agilex_3_soc.kicad_pcb`), notes in `agilex_3_soc.kicad_dru`, `sim/lpddr4_si/README.md` | – (<https://jlcpcb.com/impedance> needs JavaScript) | in the repo |
| Vendor IBIS models (Agilex, SK hynix, Winbond) | `sim/lpddr4_si/models/` (+ `min/`, `max/`) | manual, see `sim/lpddr4_si/README.md` | present |
| JLCPCB parts API (stock, LCSC data) | `tools/jlc/jlc_search.py`, `stock_check.py` | plain HTTP POST | ok |

## Gaps

| Item | Problem | What to do |
|---|---|---|
| 821801 PCB design guidelines | not downloaded; needed for the PDN, LPDDR4 layout and return-path checks | download the PDF to `docs/821801_agilex5_pcb_design_guidelines.pdf` |
| D1, D2 Würth 150060RS75000 LED | JLC has no PDF on file; we-online.com answers 403 to scripts | download from <https://www.we-online.com/catalog/datasheet/150060RS75000.pdf> to `docs/datasheets/C3030991_150060RS75000.pdf` (only pinout/polarity is needed) |
| Y3 25 MHz crystal | **no LCSC number or MPN on the footprint**, so no datasheet and no JLC placement | pick the part (load capacitance must match C251/C252 = 27 pF) and add LCSC/MPN; a BOM finding in itself |
| J3 2x19 1.27 mm socket | no LCSC number or MPN (bottom-side socket) | add the part, or mark it as hand-soldered / not assembled by JLC |
| J9 HR911130A, Y4 oscillator, L2-L5 inductors | JLC copies are scanned images (no text layer) | readable as images; J9's is 2 pages: check the PHY-side pinout and LED polarity against it |
| TI parts (TPS548A28, SN74AXC4T774, ADS7056) | JLC copies are the Chinese editions | the English TI originals are fetched as `*_ti.pdf` |

## Tools on the build machine

| Tool | Where | Notes |
|---|---|---|
| KiCad 10 CLI and Python (`pcbnew`) | unpacked AppImage `squashfs-root/AppRun` (`$K kicad-cli`, `$K python3.11`) | headless ERC/DRC parity needs `KICAD10_SYMBOL_DIR="/mnt/c/Program Files/KiCad/10.0/share/kicad/symbols"`; run on a scratch copy of the project, never save the real board |
| ngspice | inside the KiCad AppImage (`KICAD_APPRUN=$K` for the `sim/` scripts) | |
| Quartus Prime Pro 26.3 | `~/altera_pro/26.3` | EMIF test project `~/dev/agilex5_emif_test` (copy it before changing anything) |
| PDF text | `pdftotext`, `pdfinfo` (poppler) | |
| xlsx | `tools/datasheets/xlsx2csv.py` | no `openpyxl` installed |
