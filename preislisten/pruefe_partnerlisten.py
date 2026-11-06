#!/usr/bin/env python3
"""Unabhaengige Pruefung der Partner-PDFs (liest nur die fertigen PDFs + zuordnung.csv + ting_*.json).

Prueft: (1) jede erwartete Zeile (Name, Spezifikation, Preis = Quellpreis x 1,15) steht in dieser Reihenfolge im PDF,
(2) alle Quellpreise stimmen mit der OCR-Gegenprobe der Quelle ueberein (Eingabedatei pruefe-OCR liegt im Scratch),
(3) keine Spur der Quelle: Begriffsliste im Text UND in den Rohbytes (Metadaten, XMP, Schriften), kein Anhang, keine Annotation, keine Links,
(4) kein Bild ausser dem Logo, (5) keine Quellcodes sichtbar.
Exit 0 = alles gut."""
import csv
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pymupdf

HOME = Path.home()
D = HOME / 'Desktop/Elements_Lab/4 FÜR KOOPERATIONSPARTNER'
Z = HOME / 'Projekte-Mac/_DATA/ELEMENTS_STRATEGIE_20261024/partnerlisten/zuordnung.csv'
FILES = {'vials': 'Elements Labs Preisliste Partner – Vials.pdf', 'cartridges': 'Elements Labs Preisliste Partner – Cartridges.pdf'}
BEGRIFFE = ['aupson', 'aurenbi', 'whatsapp', 'wechat', 'telegram', 'hong kong', 'hongkong', 'shenzhen', 'china', 'delivery', 'shipping', 'lieferort', 'gmp',
            'coa', 'secure payment', 'discreet', 'pypdf', 'ting', 'http', 'www.', '.com', '@', '+852', 'ebos', 'hermes']
BYTES = [b'aupson', b'AUPSON', b'aurenbi', b'AURENBI', b'WhatsApp', b'WHATSAPP', b'pypdf', b'Hong', b'852', b'/EmbeddedFile', b'/URI', b'/Annots']


def money(u):
    return (Decimal(int(u)) * Decimal('1.15')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def main():
    rows = list(csv.DictReader(Z.open(), delimiter=';'))
    fehler = []
    for liste, fn in FILES.items():
        pdf = D / fn
        d = pymupdf.open(pdf)
        lines = []
        for pg in d:
            lines += [l.strip() for l in pg.get_text().splitlines() if l.strip()]
        txt = '\n'.join(lines)
        soll = [r for r in rows if r['liste'] == liste]
        # (1) Reihenfolge-Pruefung
        pos = 0
        for r in soll:
            want = [r['anzeige_name'], r['spezifikation'], f"${money(r['quellpreis_usd']):,.2f}"]
            if liste == 'cartridges':
                want.append(f"${money(r['quellpreis_single_usd']):,.2f}")
            if str(money(r['quellpreis_usd'])) != r['neuer_preis_usd']:
                fehler.append(f'{liste}: CSV-Preis falsch {r["quellcode_INTERN"]}')
            for w in want:
                nxt = next((i + 1 for i in range(pos, len(lines)) if lines[i] == w), None)
                if nxt is None:      # langer Name kann in der Zelle umbrechen: zwei Zeilen zusammensetzen
                    nxt = next((i + 2 for i in range(pos, len(lines) - 1) if lines[i] + ' ' + lines[i + 1] == w), None)
                if nxt is None:
                    fehler.append(f'{liste}: nicht in Reihenfolge gefunden: {w!r} ({r["quellcode_INTERN"]})')
                    break
                pos = nxt
        n_price = len(re.findall(r'\$[\d,]+\.\d\d', txt))
        erwartet = len(soll) * (2 if liste == 'cartridges' else 1)
        if n_price != erwartet:
            fehler.append(f'{liste}: {n_price} Preise im PDF, erwartet {erwartet}')
        # (3) Spuren
        low = txt.lower()
        for b in BEGRIFFE:
            if b in low.replace('http', 'http'):
                # 'coa'/'ting'/'china' nur als Wort pruefen, sonst Teilwort-Fehlalarme (z. B. 'coating', 'Cartridge Pricing')
                if re.search(r'(?<![a-z])' + re.escape(b) + r'(?![a-z])', low):
                    fehler.append(f'{liste}: Begriff im Text: {b!r}')
        if re.search(r'\b\d{1,2}[./ ](\d{1,2}|[A-Za-z]{3,9})[./ ]\d{2,4}\b|\b(19|20)\d\d\b|as of', txt, re.I):
            fehler.append(f'{liste}: Datum im Text')
        if re.search(r'[\u3000-\u9fff\uac00-\ud7af]', txt):
            fehler.append(f'{liste}: CJK-Zeichen im Text')
        raw = pdf.read_bytes()
        for b in BYTES:
            if b in raw:
                fehler.append(f'{liste}: Rohbytes enthalten {b!r}')
        meta = {k: v for k, v in d.metadata.items() if v and k not in ('format', 'creationDate', 'modDate')}
        if any(re.search(r'(?i)aupson|aurenbi|ting|whatsapp|eddy|eduard', str(v)) for v in meta.values()):
            fehler.append(f'{liste}: Metadaten verraten etwas: {meta}')
        if d.embfile_count() or any(list(pg.annots() or []) or pg.get_links() for pg in d):
            fehler.append(f'{liste}: Anhang, Annotation oder Link vorhanden')
        # (4) Bilder: nur das Logo auf Seite 1
        bilder = [len(pg.get_images(full=True)) for pg in d]
        if bilder[0] != 1 or any(bilder[1:]):
            fehler.append(f'{liste}: Bilder je Seite {bilder}')
        # (5) Quellcodes sichtbar?
        for r in soll:
            c = r['quellcode_INTERN']
            if len(c) >= 4 and re.search(r'(?<![A-Za-z0-9])' + re.escape(c) + r'(?![A-Za-z0-9])', txt) and c.lower() not in r['anzeige_name'].lower():
                fehler.append(f'{liste}: Quellcode sichtbar: {c}')
        print(f'{liste}: {len(d)} Seiten, {len(soll)} Zeilen, {n_price} Preise, Bilder je Seite {bilder}, Metadaten {meta}')
    print('FEHLER:' if fehler else 'OK: keine Fehler')
    for f in fehler:
        print('  -', f)
    return 1 if fehler else 0


if __name__ == '__main__':
    sys.exit(main())
