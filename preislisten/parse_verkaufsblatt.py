"""Verkaufsblatt (Inhaber, 10er-Katalogpreise) -> verkaufsblatt_parsed.json. Zeilen exakt wie im PDF; nur Zeichenbereinigung."""
import json, re, sys
from pathlib import Path
import pymupdf
SRC = Path(sys.argv[1] if len(sys.argv) > 1 else '/Users/eduardwart/Desktop/ELEMENTS_LABS_VERKAUFSBLATT.pdf')
d = pymupdf.open(SRC)
lines = []
for p in d:
    for l in p.get_text().split('\n'):
        l = re.sub(r'\s+', ' ', l.replace('\xad', '-')).strip()
        if l:
            lines.append(l)
SECTIONS = {'WEIGHT LOSS & FAT REDUCTION', 'REPAIR & RECOVERY', 'BEAUTY & ANTI-AGING', 'SLEEP & NEUROLOGICAL SUPPORT', 'HORMONE & GROWTH', 'ORGAN SUPPORT',
            'PEPTIDE BLENDS', 'SUPPLIES', 'WEIGHT MANAGEMENT', 'PEPTIDE & NEURO SUPPORT', 'HORMONE & GROWTH SUPPORT', 'METABOLIC, BEAUTY & BLENDS'}
form, section, rows, i = 'vial', None, [], 0
PRICE = re.compile(r'^([\d.]+,\d{2}) €$')
while i < len(lines):
    l = lines[i]
    if l.startswith('BEREICH 2'):
        form, section = 'dual', None
    if l in SECTIONS:
        section = l
    m = PRICE.match(l)
    if m and lines[i - 1].endswith(('10 Vials', '10 Doppelkammern')):
        unit = lines[i - 1]
        if unit in ('10 Vials', '10 Doppelkammern'):
            code, name, strength = lines[i - 4], lines[i - 3], lines[i - 2]
        else:  # CP10: strength and unit share a line
            code, name, strength = lines[i - 3], lines[i - 2], unit
        rows.append(dict(form=form, section=section, code=code, name=name, strength=strength, price_cents=int(m[1].replace('.', '').replace(',', ''))))
    i += 1
json.dump(rows, open(Path(__file__).parent / 'verkaufsblatt_parsed.json', 'w'), ensure_ascii=False, indent=1)
print(len(rows), sum(r['form'] == 'vial' for r in rows), sum(r['form'] == 'dual' for r in rows))
print(sorted({(r['form'], r['section']) for r in rows}, key=str))
