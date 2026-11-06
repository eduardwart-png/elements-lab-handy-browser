"""Importiert die vom Betreiber gepflegte Tabelle katalog.csv in data/catalog.json.
Spalten (Semikolon, UTF-8, Excel-tauglich): Name;Kategorie;Beschreibung;Preis_EUR;Verfuegbarkeit;Bild
Preise: 12,90 oder 12.90 (leer = Preis auf Anfrage). Bild: Dateiname in katalog-bilder/ (leer = Platzhalter).
Der Katalog ist reine Anzeige + Merkliste; Artikel sind nie automatisch bestellbar.
"""
import csv
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / 'katalog.csv'
IMAGES = ROOT / 'katalog-bilder'


def slug(text):
    t = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')[:48] or 'artikel'


def parse_price(raw):
    raw = (raw or '').strip().replace('€', '').replace(' ', '')
    if not raw:
        return None
    if ',' in raw:
        raw = raw.replace('.', '').replace(',', '.')
    if not re.fullmatch(r'\d{1,6}(\.\d{1,2})?', raw):
        raise ValueError('Ungültiger Preis: ' + raw)
    cents = round(float(raw) * 100)
    if cents < 1:
        raise ValueError('Preis muss größer 0 sein')
    return cents


def load(path=CSV, images=IMAGES):
    items, seen = [], set()
    with open(path, newline='', encoding='utf-8-sig') as fh:
        rows = list(csv.DictReader(fh, delimiter=';'))
    for n, row in enumerate(rows, start=2):
        name = (row.get('Name') or '').strip()
        if not name:
            continue
        base = slug(name)
        item_id, i = base, 2
        while item_id in seen:
            item_id, i = f'{base}-{i}', i + 1
        seen.add(item_id)
        image = (row.get('Bild') or '').strip()
        if image:
            if not re.fullmatch(r'[\w.\- ]+\.(png|jpe?g|webp|svg)', image, re.I) or not (images / image).is_file():
                raise ValueError(f'Zeile {n}: Bilddatei {image!r} fehlt in katalog-bilder/')
        items.append({'id': item_id, 'name': name, 'category': (row.get('Kategorie') or 'Sonstiges').strip(), 'description': (row.get('Beschreibung') or '').strip(),
                      'price_cents': parse_price(row.get('Preis_EUR')), 'availability': (row.get('Verfuegbarkeit') or 'Auf Anfrage').strip(),
                      'image': ('assets/catalog-user/' + image) if image else 'assets/catalog/label.svg', 'sample': False, 'published': True, 'orderable': False})
    return items


def main():
    items = load()
    path = ROOT / 'data/catalog.json'
    catalog = json.loads(path.read_text())
    catalog['items'] = items
    catalog['note'] = 'Zusatzkatalog aus katalog.csv. Anzeige- und Merkliste, keine Bestellung.'
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    print(f'{len(items)} Katalogartikel übernommen.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as exc:
        print('FEHLER:', exc)
        sys.exit(1)
