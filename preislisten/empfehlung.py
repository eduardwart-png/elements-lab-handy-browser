"""Preise der 10er-Packs = Preisfamilie v3 (Modell 3 "Packliste als Master", Stand 24.10.2026).

Quelle der Wahrheit ist die eingefrorene Tabelle preislisten/preisfamilie_v3.csv (Schema level;form;substance;strength;dose;unit;
price_old_eur;price_new_eur, 394 Zeilen, keine Einkaufswerte). Hier werden nur die 340 Zeilen level=pack gelesen; zur Laufzeit wird
nichts neu gerechnet (Reproduktion: team/preismodell3/modell3.py). Ausgabe unveraendert preisempfehlung.json (intern) mit Schluessel
(form, name, strength), von catalog_lines.lines(adjusted=True) als Preisebene gelesen.

  * discount_ok: weiter Marge-Regel 1 - Einkauf/Preis >= DISCOUNT_MARGIN (Einkauf aus ting_check.load(), bleibt intern).
  * ting_target_eur: Ziel-Einkauf fuer 2,5 x aus preislisten/verhandlungsliste_v3.csv (intern), sonst None.
  * OWNER_PRICE (Reta 15 mg = 400, 20 mg = 430 EUR) bleibt Inhaberentscheidung; die Tabelle enthaelt sie bereits, hier nur Gegenprobe.
Ersetzt durch Preisfamilie v3 (frueher compute() mit eigenen Regeln): FACTOR (3 x Einkauf), DUAL_MIN (+15 %), STEP_MIN (3-%-Staffel),
FOCUS, MARKET_CAP, RESELLER_COST_SHARE, MIN_FACTOR (2 x Einkauf). Diese Regeln stecken jetzt im Modell (Leiter je Substanz,
Dual-Pack >= 1,30 x Vial-Pack, EK-Schranke 2,0 x, alte Liste als Master).
"""
import csv
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'miniapp' / 'tools'))
import ting_check as tc  # noqa: E402

OUT = HERE / 'preisempfehlung.json'
TABLE = HERE / 'preisfamilie_v3.csv'
NEGOTIATION = HERE / 'verhandlungsliste_v3.csv'
OWNER_PRICE = {('vial', 'Retatrutide', '15 mg'): 400, ('vial', 'Retatrutide', '20 mg'): 430}  # Inhaberentscheidung 24.10.2026 (in der Tabelle enthalten)
DISCOUNT_MARGIN = 0.60  # Mengenrabatt nur auf Zeilen, die auch nach Abzug mindestens ca. 50 % Marge halten (Marge >= 60 % vor Rabatt)


def ceil10(v):
    return int(-(-round(v, 6) // 10)) * 10


def read_table(level='pack'):
    """Zeilen der eingefrorenen Preisfamilie; level=pack: Schluessel (form, substance, strength) = catalog_lines-Schluessel (form, name, strength)."""
    with open(TABLE, newline='', encoding='utf-8') as fh:
        return [r for r in csv.DictReader(fh, delimiter=';') if r['level'] == level]


def targets():
    """Ziel-Einkauf je 10er-Pack fuer Faktor 2,5 (Verhandlungsliste v3, intern)."""
    with open(NEGOTIATION, newline='', encoding='utf-8') as fh:
        return {(r['form'], r['substance'], r['strength']): float(r['ziel_ek_fuer_2_5x_eur'])
                for r in csv.DictReader(fh, delimiter=';') if r.get('level', 'pack') == 'pack' and r['ziel_ek_fuer_2_5x_eur']}


def compute():
    table = {(r['form'], r['substance'], r['strength']): float(r['price_new_eur']) for r in read_table('pack')}
    rows, _ = tc.load()
    keys = {(r['form'], r['name'], r['strength']) for r in rows}
    if keys != set(table) or len(rows) != len(table):
        raise SystemExit(f'Preisfamilie v3 passt nicht zum Katalog: fehlt {sorted(keys - set(table))[:5]}, zuviel {sorted(set(table) - keys)[:5]}')
    for key, fixed in OWNER_PRICE.items():
        if table[key] != fixed:
            raise SystemExit(f'Inhaberpreis {key} = {fixed} fehlt in der Tabelle (dort {table[key]})')
    for r in rows:
        key = (r['form'], r['name'], r['strength'])
        r['cost'] = r.get('ting') if r.get('ting') is not None else r.get('other')
        r['price'] = int(table[key]) if table[key] == int(table[key]) else table[key]
        r['why'] = ['Preisfamilie v3'] + (['Inhaberpreis'] if key in OWNER_PRICE else [])
    return rows


if __name__ == '__main__':
    rows = compute()
    tgt = targets()
    out = [dict(form=r['form'], name=r['name'], strength=r['strength'], price_eur=r['price'], discount_ok=bool(r['cost'] and 1 - r['cost'] / r['price'] >= DISCOUNT_MARGIN),
                current_eur=r['cur'], cost_eur=r['cost'], market_eur=r.get('market'), why=sorted(set(r['why'])),
                ting_target_eur=tgt.get((r['form'], r['name'], r['strength']))) for r in rows]
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    v = [r for r in rows if r['form'] == 'vial' and r['cost']]
    d = [r for r in rows if r['form'] == 'dual' and r['cost']]
    for label, rs_ in (('Vial', v), ('Doppelkammer', d)):
        print(label, len(rs_), 'Zeilen; Summe alt', sum(r['cur'] for r in rs_), 'neu', sum(r['price'] for r in rs_), 'Einkauf', round(sum(r['cost'] for r in rs_)),
              'Marge neu', f"{1 - sum(r['cost'] for r in rs_) / sum(r['price'] for r in rs_):.0%}", '| angehoben', sum(1 for r in rs_ if r['price'] > r['cur']), 'gesenkt', sum(1 for r in rs_ if r['price'] < r['cur']))
    print('Zeilen', len(out), '| discount_ok', sum(1 for x in out if x['discount_ok']), '| mit Ziel-Einkauf', sum(1 for x in out if x['ting_target_eur']), '| ohne Einkauf', sum(1 for r in rows if not r['cost']))
    with open(HERE.parent / 'miniapp' / 'evidence' / 'preisempfehlung-bericht.csv', 'w', newline='') as fh:
        w = csv.writer(fh, delimiter=';')
        w.writerow(['Form', 'Produkt', 'Dosis', 'Einkauf (Ting)', 'Markt', 'Shop vorher', 'Empfehlung', 'Marge', 'Hinweise'])
        for r in rows:
            w.writerow([r['form'], r['name'], r['strength'], r['cost'] and round(r['cost']), r.get('market') and round(r['market']), r['cur'], r['price'], r['cost'] and f"{1 - r['cost'] / r['price']:.0%}", ', '.join(sorted(set(r['why'])))])
