"""Ting-Preischeck: Ting-Einkauf (Ting_Vials.pdf, Ting_Pens.pdf) gegen Elements-Labs-Verkaufspreise (Empfehlung der Preispositionierung).

Ting-Vial-Preis = Listenpreis je 10 Vials (USD, sichtbar im PDF). Das PDF enthaelt unter dem Preis einen zweiten, dunkel gedruckten Wert ("2. Wert");
welcher gilt, ist unbestaetigt - Marge wird mit dem sichtbaren Preis gerechnet, der 2. Wert zusaetzlich gezeigt.
Ting-Doppelkammer = Preis je Kartusche x 10 (Annahme: Pens-Liste nennt Preis je Kartusche).
"""
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'miniapp' / 'tools'))
import catalog_lines as cl  # noqa: E402
import markt_10er as m  # noqa: E402
from positionierung import canon  # noqa: E402

GOOD, OK = 0.60, 0.50


# Katalogname -> Name in merged.json (Ting-/Lieferantenliste), wo die Schreibweise abweicht oder canon() Varianten zusammenwerfen wuerde
ALIAS = {
    ('vial', 'CagriSema (2,5 mg + 2,5 mg)'): 'Cagrilintide + Semaglutide',
    ('vial', 'Melanotan I (MT-1)'): 'Melanotan I/II',  # Ting fuehrt MT-1/MT-2 bei Vials gemeinsam (Zuordnung unbestaetigt)
    ('vial', 'Melanotan II (MT-2)'): 'Melanotan I/II',
    ('vial', 'CJC-1295 (ohne DAC) + Ipamorelin'): 'CJC-1295 + Ipamorelin',
    ('dual', 'CJC-1295 (ohne DAC) + Ipamorelin'): 'CJC-1295 (ohne DAC) + Ipamorelin (5 mg + 5 mg)',
    ('vial', 'Lipo-C (216)'): 'Lipo-C (Variante 216)',
    ('vial', 'Lipo-C (526)'): 'Lipo-C (Variante 526)',
    ('vial', 'Oxytocin Acetate'): 'Oxytocin',
    ('dual', 'Oxytocin Acetate (Pharmaceutical Grade)'): 'Oxytocin (Pharma-Qualit\u00e4t)',
    ('dual', 'Oxytocin Acetate (Industrial Grade)'): 'Oxytocin (Industriequalit\u00e4t)',
    ('vial', 'TB-500 Fragment'): 'TB Frag',
}


def dose_of(s):
    d = m.split_dose(s)
    if d is None:
        x = re.match(r'\s*([\d.,]+)\s*mcg', s)
        if x:
            d = (round(float(x.group(1).replace(',', '.')) / 1000, 6), 'mg')
    return d


def _find(ex, cn, form, name, d):
    """Zuordnung Katalogzeile -> Lieferantenzeile: erst exakter (Alias-)Name, sonst canon-Name nur wenn eindeutig (nie CJC mit/ohne DAC, Lipo-C 216/526 u. a. vermischen)."""
    target = ALIAS.get((form, name), name)
    hit = ex.get((target, d))
    if hit:
        return hit
    hit = cn.get((canon(target), d))
    if hit and len({e[0] for e in hit}) == 1:
        return hit
    return None


def load(final=False):
    """final=True: Verkaufspreis = endgueltige Preisempfehlung (preisempfehlung.json), sonst Empfehlung der Preispositionierung."""
    mg = json.loads((HERE / 'merged.json').read_text())
    rate = mg['rate']
    ting_v, ting_d, oth_v = ({}, {}), ({}, {}), ({}, {})
    for v in mg['vials']:
        d = dose_of(v['dose'])
        if not d:
            continue
        if v.get('ting_usd') is not None:
            for idx, k in ((ting_v[0], (v['name'], d)), (ting_v[1], (canon(v['name']), d))):
                idx.setdefault(k, []).append((v['name'], v))
        cands = [x for x in (v.get('wholesale_eur'), v.get('list_eur')) if x is not None]
        if cands:
            for idx, k in ((oth_v[0], (v['name'], d)), (oth_v[1], (canon(v['name']), d))):
                idx.setdefault(k, []).append((v['name'], min(cands)))
    for p_ in mg['dual']:
        d = dose_of(p_['dose'])
        if d:
            for idx, k in ((ting_d[0], (p_['name'], d)), (ting_d[1], (canon(p_['name']), d))):
                idx.setdefault(k, []).append((p_['name'], p_))
    pos = {(r['form'], r['name'], r['strength']): r for r in json.loads((HERE / 'positionierung.json').read_text())}
    old_sheet = {(x['form'], x['name'], x['strength']): x['price_cents'] / 100 for x in cl.lines(adjusted=False) if not x.get('supplement')}  # Verkaufsblatt des Inhabers, unveraendert
    rows = []
    for x in cl.lines(recommend=False):
        d = dose_of(x['strength'])
        p = pos[(x['form'], x['name'], x['strength'])]
        row = dict(form=x['form'], section=x['section'], name=x['name'], strength=x['strength'], order=x['order'], cur=p['cur'], old=old_sheet.get((x['form'], x['name'], x['strength'])), rec=p['rec'],
                   market=p['market'], src=p['src'], supplement=bool(x.get('supplement')))
        if x['form'] == 'vial':
            t = _find(*ting_v, 'vial', x['name'], d)
            o = _find(*oth_v, 'vial', x['name'], d)
            other = min(e[1] for e in o) if o else None
            if t:
                vis = min(e[1]['ting_vis'] for e in t)
                hid = min(e[1]['ting_usd'] for e in t)
                row.update(ting=round(vis / rate, 2), ting2=round(hid / rate, 2) if hid != vis else None, other=other)
            elif other is not None:
                row.update(other=other)
        else:
            t = _find(*ting_d, 'dual', x['name'], d)
            if t:
                row.update(ting=round(min(e[1]['dual_usd'] for e in t) * 10 / rate, 2), ting2=None, other=None)
        rows.append(row)
    if final and (HERE / 'preisempfehlung.json').is_file():
        fin = {(r['form'], r['name'], r['strength']): r['price_eur'] for r in json.loads((HERE / 'preisempfehlung.json').read_text())}
        for r in rows:
            r['rec'] = fin.get((r['form'], r['name'], r['strength']), r['rec'])
    return rows, rate


def status(r):
    if r.get('ting') is None:
        return 'nicht bei Ting'
    mg = (r['rec'] - r['ting']) / r['rec']
    return 'stark' if mg >= GOOD else 'solide' if mg >= OK else 'nachverhandeln'


if __name__ == '__main__':
    rows, rate = load()
    for form in ('vial', 'dual'):
        rs_ = [r for r in rows if r['form'] == form]
        hit = [r for r in rs_ if r.get('ting') is not None]
        print(form, len(rs_), 'Zeilen;', len(hit), 'bei Ting')
        miss = [(r['name'], r['strength']) for r in rs_ if r.get('ting') is None]
        print('  ohne Ting:', miss)
        if hit:
            cost = sum(r['ting'] for r in hit); rec = sum(r['rec'] for r in hit); cur = sum(r['cur'] for r in hit)
            print(f'  Summe Ting {cost:,.0f} | Shop aktuell {cur:,.0f} | Empfehlung {rec:,.0f} | Marge Empfehlung {1 - cost / rec:.0%} | aktuell {1 - cost / cur:.0%}')
            from collections import Counter
            print('  Status:', Counter(status(r) for r in hit))
