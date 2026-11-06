"""Marktanalyse 10er-Vial-Katalogpreise: Verkaufsblatt (Inhaber) gegen oeffentliche 10-Vial-Kits (peptidehaus.de, qsc-eu.com).

Schreibt preislisten/markt_10er.json (je Zeile Quellen, Median, Entscheidung) und preislisten/markt_10er_analyse.csv.
Regel: nur Vials; Median aus mindestens 2 Quellen; liegt der Blattpreis darueber, wird auf den Median (auf 5 EUR gerundet) gesenkt, sonst bleibt er.
"""
import csv
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'miniapp' / 'tools'))
import catalog_lines as cl  # noqa: E402

MKT = Path.home() / '.hermes/cache/scratch/mkt'
ALIAS = [('antibacterial water', 'bacteriostatic water'), ('nad+ support', 'nad+'), ('epitalon (epithalon)', 'epithalon'), ('kisspeptin', 'kisspeptin'),
         ('mots-c', 'mots-c'), ('mt-1 (melanotan 1 acetate)', 'melanotan i'), ('mt-2 (melanotan 2 acetate)', 'melanotan ii'), ('igf-1lr3', 'igf-1 lr3'),
         ('hexarelin acetate', 'hexarelin'), ('ghrp-2 acetate', 'ghrp-2'), ('ghrp-6 acetate', 'ghrp-6'), ('gonadorelin acetate', 'gonadorelin'),
         ('oxytocin acetate', 'oxytocin'), ('sermorelin acetate', 'sermorelin'), ('cjc-1295 without dac', 'cjc-1295 (ohne dac)'), ('cjc-1295 with dac', 'cjc-1295 (mit dac)'),
         ('thymosin alpha-1', 'thymosin alpha-1'), ('glow blend', 'glow'), ('klow blend', 'klow'), ('vitamin b12', 'b12'), ('foxo4-dri', 'foxo4'), ('foxo4', 'foxo4'),
         ('adipotide (fttp)', 'adipotide'), ('l-carnitine', 'l-carnitine'), ('aod-9604', 'aod9604'), ('lipo-c', 'lipo-c'), ('survodutide', 'survodutide'),
         ('tb-500 (full-length)', 'tb-500'), ('retatrutide', 'retatrutide')]


def norm(name):
    n = name.lower().replace('\\|', '').strip()
    n = re.sub(r'\s+', ' ', n)
    for a, b in ALIAS:
        if n.startswith(a) or n == a:
            return b
    return n


def split_dose(text, last=False):
    ms = list(re.finditer(r'(\d+(?:[.,]\d+)?)\s*(mg|ml|iu)\b', text.lower()))
    if not ms:
        return None
    m = ms[-1] if last else ms[0]
    return (float(m.group(1).replace(',', '.')), m.group(2))


def load_quotes():
    quotes = {}  # (name, dose, unit) -> {source: eur}
    for text, eur in json.loads((MKT / 'peptidehaus_kits.json').read_text()).items():
        base = text.split('×')[0].strip()
        d = split_dose(base, last=True)
        if not d:
            continue
        name = re.sub(r'\s*\d+(?:[.,]\d+)?\s*(mg|ml|iu)\s*$', '', base, flags=re.I).strip()
        if '+' in name and 'glow' not in name.lower() and 'klow' not in name.lower():
            continue
        quotes.setdefault((norm(name), d[0], d[1]), {})['peptidehaus'] = eur
    for line in (MKT / 'https_qsc_eu_com_compounds_html.txt').read_text().split('\n'):
        m = re.match(r'\|\s*(.+?)\s*\\\|\s*10-Vial Kit\s*\\\|.*?\|\s*[A-Z0-9-]+\s*\|\s*€([\d,.]+)\s*\|', line)
        if not m or '+' in m.group(1) or 'Blend' in m.group(1):
            continue
        d = split_dose(m.group(1))
        if not d:
            continue
        name = re.sub(r'\s*\d+(?:[.,]\d+)?\s*(mg|ml|iu)\b.*$', '', m.group(1), flags=re.I).strip()
        quotes.setdefault((norm(name), d[0], d[1]), {})['qsc'] = float(m.group(2).replace(',', ''))
    return quotes


def line_key(line):
    d = split_dose(line['strength'])
    name = line['name']
    if name.startswith('Lipo-C'):
        name = 'Lipo-C'
    return (norm(name), d[0], d[1]) if d else None


def main():
    quotes = load_quotes()
    rows = []
    for ln in cl.lines(adjusted=False):
        if ln['form'] != 'vial':
            continue
        key = line_key(ln)
        src = quotes.get(key, {}) if key else {}
        owner = ln['price_cents'] / 100
        med, basis = None, ''
        if len(src) >= 2:
            med, basis = round(statistics.median(src.values()), 2), 'Median aus 2 Quellen'
        elif len(src) == 1 and owner > 1.5 * next(iter(src.values())):
            med, basis = round(1.15 * next(iter(src.values())), 2), 'eine Quelle, Blattpreis > 1,5-fach: Quelle +15 %'
        new = owner
        reason = 'keine belastbare Quelle: unveraendert' if med is None else 'Blattpreis <= Markt: unveraendert'
        if med is not None and owner > med:
            cand = max(5 * round(med / 5), 5)
            if cand < owner:
                new, reason = cand, 'gesenkt: ' + basis
        rows.append(dict(code=ln['code'], name=ln['name'], strength=ln['strength'], section=ln['section'], owner_eur=owner, sources=src, median_eur=med, new_eur=new, reason=reason))
    # mehr mg kostet nie weniger: von oben nach unten glaetten (nur senken)
    by = {}
    for r in rows:
        by.setdefault(re.sub(r'\s*\(.*$', '', r['name']), []).append(r)
    for group in by.values():
        group.sort(key=lambda r: (split_dose(r['strength']) or (0, ''))[0])
        for a, b in zip(group, group[1:]):
            if split_dose(a['strength']) and split_dose(b['strength']) and split_dose(a['strength'])[1] == split_dose(b['strength'])[1] and a['new_eur'] >= b['new_eur'] and a['new_eur'] > 5:
                a['new_eur'] = max(5, b['new_eur'] - 5)
                a['reason'] += ' + Staffel geglaettet'
    (HERE / 'markt_10er.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    with open(HERE / 'markt_10er_analyse.csv', 'w', newline='') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['Code', 'Produkt', 'Staerke', 'Blattpreis 10er-Vial', 'peptidehaus 10er', 'qsc-eu 10er', 'Median', 'Neu', 'Entscheidung'])
        for r in rows:
            w.writerow([r['code'], r['name'], r['strength'], r['owner_eur'], r['sources'].get('peptidehaus', ''), r['sources'].get('qsc', ''), r['median_eur'] or '', r['new_eur'], r['reason']])
    lowered = [r for r in rows if r['new_eur'] < r['owner_eur']]
    print(len(rows), 'Vial-Zeilen;', sum(1 for r in rows if r['median_eur']), 'mit >=2 Quellen;', sum(1 for r in rows if r['sources']), 'mit >=1 Quelle;', len(lowered), 'gesenkt')
    for r in lowered:
        print(f"{r['name']} {r['strength']}: {r['owner_eur']:.0f} -> {r['new_eur']:.0f} (Median {r['median_eur']}, {r['sources']})")


if __name__ == '__main__':
    main()
