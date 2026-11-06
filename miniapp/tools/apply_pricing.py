"""Preislogik des Shops (Einzel-Vial, Einzel-Doppelkammer, 10er-Packs). Idempotent: liest nur eingefrorene Tabellen, rechnet nichts neu.

Regeln (Preisfamilie v3, Modell 3 "Packliste als Master", Stand 24.10.2026; BASIS = PREISFAMILIE_V3_2026_10_24):
  * Einzelpreise Vial und Doppelkammer aller 27 Shop-Produkte = preislisten/preisfamilie_v3.csv, level=einzel (54 Zeilen).
    Zuordnung Tabellenzeile -> products.json-id ueber preislisten/preisfamilie_v3_shopzuordnung.csv (Spalte shop_produkt, aus
    team/preismodell3/zeilen_v3.csv ohne Einkaufsspalten). Doppelkammer-Einzelpreis = inklusive Pen.
  * 10er-Packs = catalog_lines.lines() (adjusted=True: preisempfehlung.json aus preislisten/empfehlung.py = preisfamilie_v3.csv level=pack).
    Der ganze Katalog (340 Zeilen) steht als 10er-Packs im Shop (data/catalog-packs.json + die Packungen der Shop-Produkte).
  * Einzige Ausnahme ohne Katalogzeile: Doppelkammer-Pack BPC-157 + TB-500 20 mg (Shop-Dual-Pack) bleibt beim bisherigen Preis (SHOP_ONLY_PACK).
  * Einkaufspreise bleiben intern (preislisten/) und gelangen nie in data/ oder public/; apply() liest keine Einkaufswerte.
Ersetzt durch Preisfamilie v3 (nicht mehr verwendet): MARKET_FACTOR/PEN_CUT (Markt-Median x Faktor), Pen/Vial-Verhaeltnis der Konkurrenz,
DUAL_PREMIUM_CENTS (Vial + 10 EUR), PIECE_MARGIN (Einzel >= 1,2 x Stueckpreis, "bumped"), Dosisleiter +1 EUR, ANCHORS/COMPETITOR_PEN/UNDERCUT,
PACK_FACTOR (3 x Einkauf fuer Packs ohne Blattzeile), Dual-Pack >= Vial-Pack + 15 %. Diese Regeln stecken im Modell (Leiter, Korridor, Markt-Anker).
Die Markt-Hilfsfunktionen (vendor_at, market_reference, pen_ratio) bleiben fuer Analyse-Skripte (positionierung.py, ting_pdf.py).
"""
import csv
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog_lines as cl  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PRICES = ROOT.parent / 'preislisten'
TABLE = PRICES / 'preisfamilie_v3.csv'
SHOP_MAP = PRICES / 'preisfamilie_v3_shopzuordnung.csv'
MARKET = PRICES / 'markt_preise.json'
COSTS = PRICES / 'shop_costs.json'   # nur fuer den internen Bericht (evidence/pricing-report.csv), nie fuer Preise
PACK_SIZE = 10
BASIS = 'PREISFAMILIE_V3_2026_10_24'
SHOP_ONLY_PACK = {('bpc-157-tb-500', 'dual'): 72000}  # Shop-Dual-Pack ohne Katalogzeile (395. Element): mind. 1,30 x Vial-Pack (550) = 720 EUR (E3)
SHOP_ONLY_STATUS = 'SHOP_ONLY_FIXED_2026_10_24'


def dose(p):
    return float(p['concentration'].split()[0].replace(',', '.'))


def cents(euro_text):
    return round(float(euro_text) * 100)


def table_rows():
    with open(TABLE, newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh, delimiter=';'))


def single_prices(ids):
    """Einzelpreise je Shop-Produkt aus der Preisfamilie v3: ({id: vial_cents}, {id: dual_cents})."""
    with open(SHOP_MAP, newline='', encoding='utf-8') as fh:
        mapping = {(r['level'], r['form'], r['substance'], r['strength']): r['shop_produkt'] for r in csv.DictReader(fh, delimiter=';')}
    single, dual = {}, {}
    for r in table_rows():
        if r['level'] != 'einzel':
            continue
        pid = mapping[(r['level'], r['form'], r['substance'], r['strength'])]
        target = single if r['form'] == 'vial' else dual
        if pid in target:
            raise ValueError(f'Doppelte Einzelzeile {pid} {r["form"]}')
        target[pid] = cents(r['price_new_eur'])
    for name, got in (('Vial', single), ('Doppelkammer', dual)):
        if set(got) != set(ids):
            raise ValueError(f'Einzelpreise {name} decken die Shop-Produkte nicht ab: fehlt {sorted(set(ids) - set(got))}, zuviel {sorted(set(got) - set(ids))}')
    return single, dual


def ladder_value(ref_by_dose, x):
    """Linear interpolation on the reference ladder; extrapolation along the nearest segment."""
    pts = sorted(ref_by_dose.items())
    if x <= pts[0][0]:
        (x0, y0), (x1, y1) = pts[0], pts[1]
    elif x >= pts[-1][0]:
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
    else:
        x0, y0, x1, y1 = next((a, ya, b, yb) for (a, ya), (b, yb) in zip(pts, pts[1:]) if a <= x <= b)
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def end_90_up(euro):
    """Smallest price of the form N,90 that is >= euro (float noise like 3*8.30 = 24.900000000000002 must not cost a euro)."""
    return end_90_up_cents(round(euro * 100, 6))


def end_90_up_cents(cents_value):
    value = math.ceil(round(cents_value, 6))
    return ((value + 10 + 99) // 100) * 100 - 10


def floor_90(cents_value):
    """Largest price of the form N,90 that is <= cents (never above the target)."""
    return max(990, ((int(math.floor(cents_value)) + 10) // 100) * 100 - 10)


def vendor_at(points, d):
    """Vendor price at dose d: exact, or log-log interpolation/extrapolation (at most factor 2 outside) from >= 2 points; else None."""
    pts = sorted((float(k), v) for k, v in points.items())
    for k, v in pts:
        if k == d:
            return v
    if len(pts) < 2:
        return None
    if d < pts[0][0]:
        (x0, y0), (x1, y1) = pts[0], pts[1]
    elif d > pts[-1][0]:
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
    else:
        (x0, y0), (x1, y1) = next(((a, ya), (b, yb)) for (a, ya), (b, yb) in zip(pts, pts[1:]) if a <= d <= b)
    if d < pts[0][0] / 2 or d > pts[-1][0] * 2:
        return None
    slope = math.log(y1 / y0) / math.log(x1 / x0)
    return y0 * (d / x0) ** slope


def market_reference(vendors, d):
    vals = sorted(v for v in (vendor_at(pts, d) for pts in vendors.values()) if v)
    if not vals:
        return None
    mid = len(vals) // 2
    return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2


def pen_ratio(market):
    r = sorted(pen / vial for _, pen, vial in market['pen_gegen_vial']['paare'])
    mid = len(r) // 2
    return r[mid] if len(r) % 2 else (r[mid - 1] + r[mid]) / 2


def market_key(p):
    return {'nad-plus': 'nad-plus'}.get(p['group'], p['group'])


def money(cents_value):
    return f'{cents_value // 100},{cents_value % 100:02d} €'


def pack_prices(vials):
    """10er-Preise je Shop-Produkt aus catalog_lines.lines() (Preisfamilie v3); ohne Katalogzeile nur SHOP_ONLY_PACK. Rueckgabe: packs, Liste ohne Zeile."""
    index = {(x['form'], x['name'], x['strength']): x for x in cl.lines()}
    packs, fallback = {}, []
    for p in vials:
        v, d = cl.MATCH[p['id']]
        entry = {}
        for form, ref, key in (('vial', v, 'vial'), ('dual', d, 'dual')):
            line = index.get((form, *ref)) if ref else None
            if line:
                entry[key] = line['price_cents']
                entry[key + '_line'] = line
            elif (p['id'], form) in SHOP_ONLY_PACK:
                entry[key] = SHOP_ONLY_PACK[(p['id'], form)]
                fallback.append((p['id'], form))
            else:
                raise ValueError(f'Kein 10er-Preis fuer {p["id"]} {form}: weder Katalogzeile noch SHOP_ONLY_PACK')
        packs[p['id']] = entry
    return packs, fallback


def compute(vials, ref=None, costs=None):
    """Einzel- und Packpreise; ref/costs werden nicht mehr gebraucht (Signatur bleibt fuer aeltere Aufrufer)."""
    packs, fallback = pack_prices(vials)
    single, dual = single_prices([p['id'] for p in vials])
    compute.dual, compute.fallback, compute.bumped = dual, fallback, []
    return single, packs


def apply():
    vials = json.loads((ROOT / 'data/products.json').read_text())
    formats = json.loads((ROOT / 'data/shop-formats.json').read_text())
    single, packs = compute(vials)
    for p in vials:
        p['price_cents'] = single[p['id']]
        p['price'] = money(single[p['id']])
        p['price_status'] = BASIS
    kept = [f for f in formats if f['format'] in ('dual_chamber', 'pen')]
    out = []
    for f in kept:
        if f['format'] == 'dual_chamber':
            c = compute.dual[f['base_product_id']]
            f['price_cents'], f['price'], f['price_status'] = c, money(c), BASIS
        out.append(f)
    num = 0
    for p in vials:  # catalogue of 10-packs: vial packs first, then dual packs, same order as the shop
        num += 1
        out.append(pack_item(p, p['id'] + '-x10', 'vial_pack', packs[p['id']]['vial'], p['id'], num, p['image'], p.get('detailImage', p['image']), packs[p['id']].get('vial_line')))
    dual_by_base = {f['base_product_id']: f for f in kept if f['format'] == 'dual_chamber'}
    for p in vials:
        d = dual_by_base[p['id']]
        num += 1
        out.append(pack_item(p, d['id'] + '-x10', 'dual_pack', packs[p['id']]['dual'], p['id'] + '-dual', num, d['image'], d.get('detailImage', d['image']), packs[p['id']].get('dual_line'), packs[p['id']].get('vial_line')))
    matched = {(l['form'], l['name'], l['strength']) for pk in packs.values() for l in (pk.get('vial_line'), pk.get('dual_line')) if l}
    extras = []
    for line in cl.lines():
        if (line['form'], line['name'], line['strength']) in matched:
            continue
        extras.append({'id': f"cat-{line['form']}-{cl.slug(line['name'])}-{cl.slug(line['strength'])}", 'name': line['name'], 'concentration': line['strength'],
                       'price': money(line['price_cents']), 'price_cents': line['price_cents'], 'format': 'vial_pack' if line['form'] == 'vial' else 'dual_pack',
                       'pack_size': PACK_SIZE, 'section': line['section'], 'code': line['code'], 'order': line['order'], 'line_name': line['name'], 'line_strength': line['strength'], 'catalog_only': True,
                       'price_status': BASIS, 'stock_status': 'UNCONFIRMED', 'discount_ok': bool(line.get('discount_ok'))})
    assert len({e['id'] for e in extras}) == len(extras), 'Katalog-IDs nicht eindeutig'
    (ROOT / 'data/catalog-packs.json').write_text(json.dumps(extras, ensure_ascii=False, indent=2) + '\n')
    (ROOT / 'data/products.json').write_text(json.dumps(vials, ensure_ascii=False, indent=2) + '\n')
    (ROOT / 'data/shop-formats.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
    return vials, out, single, packs, None


def pack_item(p, pid, fmt, cents_value, link, num, image, detail, line=None, sibling=None):
    ref = line or sibling or {}  # Produkt ohne eigene Katalogzeile: Abschnitt/Reihenfolge der Schwesterzeile
    return {'section': ref.get('section', ''), 'code': (line or {}).get('code', ''), 'order': ref.get('order', 9999), 'line_name': ref.get('name', ''), 'line_strength': ref.get('strength', ''),
            'id': pid, 'sourceId': p['id'], 'form': fmt, 'num': f'{num:02d}', 'name': p['name'], 'concentration': p['concentration'],
            'price': money(cents_value), 'price_cents': cents_value, 'category': p['category'], 'featured': False, 'group': p['group'], 'descKey': p['descKey'],
            'image': image, 'detailImage': detail, 'base_product_id': p['id'], 'link': link, 'format': fmt, 'pack_size': PACK_SIZE,
            'price_status': BASIS if line else SHOP_ONLY_STATUS, 'stock_status': 'UNCONFIRMED', 'discount_ok': bool((line or {}).get('discount_ok'))}


def report(vials, single, packs, costs, ref):
    """Interner Bericht (evidence/, nie public/): alte Vorlage, neue Einzel-/Packpreise, Einkauf je Vial."""
    lines = ['Produkt;Dosis;Vorlage alt;Vial neu;Doppelkammer neu;10er-Vial;10er-Doppelkammer;EK 10er-Vial;Marge Single-Vial (x EK je Vial)']
    for p in vials:
        c = costs.get(p['id'], {})
        ek = c.get('vial10_eur')
        lines.append(';'.join([p['name'], p['concentration'], money(ref['vial'][p['id']]), money(single[p['id']]), money(compute.dual[p['id']]),
                               money(packs[p['id']]['vial']), money(packs[p['id']]['dual']), f"{ek:.2f}".replace('.', ',') if ek else '',
                               f"{single[p['id']] / 100 / (ek / 10):.1f}".replace('.', ',') if ek else '']))
    return '\n'.join(lines)


if __name__ == '__main__':
    ref = json.loads((ROOT / 'data/reference-prices.json').read_text())
    vials, out, single, packs, _ = apply()
    costs = json.loads(COSTS.read_text()) if COSTS.is_file() else {}
    text = report(vials, single, packs, costs, ref)
    (ROOT / 'evidence/pricing-report.csv').write_text(text + '\n')
    print(text)
    print(len(out), 'format items')
