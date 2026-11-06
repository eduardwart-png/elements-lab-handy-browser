"""Preisfamilie v3 (eingefrorene Tabelle preislisten/preisfamilie_v3.csv) == ausgelieferte Shop-Preise; Regeln der Familie ohne Toleranz.

Quelle: team/preismodell3/tabelle_v3.csv (24.10.2026), 394 Zeilen (340 level=pack, 54 level=einzel), ohne Einkaufswerte.
"""
import csv
import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PRICES = ROOT.parent / 'preislisten'
TABLE = PRICES / 'preisfamilie_v3.csv'
TABLE_SHA256 = 'b8f51beedd234cd2a117bbae07455d482bf14f27a3258a97281a34c445fe6720'  # tabelle_G.csv (Endstand G: F + Mindestmarge 60 % hart fuer alle Packs, Eddy 25.10.2026), eingefroren
sys.path.insert(0, str(ROOT / 'tools'))
import catalog_lines as cl  # noqa: E402

VIALS = json.loads((ROOT / 'data/products.json').read_text())
FORMATS = json.loads((ROOT / 'data/shop-formats.json').read_text())
EXTRA = json.loads((ROOT / 'data/catalog-packs.json').read_text())


def rows():
    with open(TABLE, newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh, delimiter=';'))


def cents(text):
    return round(float(text) * 100)


def shop_map():
    with open(PRICES / 'preisfamilie_v3_shopzuordnung.csv', newline='', encoding='utf-8') as fh:
        return {(r['level'], r['form'], r['substance'], r['strength']): r['shop_produkt'] for r in csv.DictReader(fh, delimiter=';')}


def delivered_singles():
    """(form, shop_produkt) -> Einzelpreis in Cent aus data/ (Vial = products.json, Doppelkammer = shop-formats.json)."""
    out = {('vial', p['id']): p['price_cents'] for p in VIALS}
    out.update({('dual', f['base_product_id']): f['price_cents'] for f in FORMATS if f['format'] == 'dual_chamber'})
    return out


class FrozenTable(unittest.TestCase):
    def test_table_is_the_frozen_v3_file_without_purchase_columns(self):
        self.assertEqual(hashlib.sha256(TABLE.read_bytes()).hexdigest(), TABLE_SHA256)
        rs = rows()
        self.assertEqual(list(rs[0].keys()), ['level', 'form', 'substance', 'strength', 'dose', 'unit', 'price_old_eur', 'price_new_eur'])
        self.assertEqual(len(rs), 394)
        self.assertEqual((sum(r['level'] == 'pack' for r in rs), sum(r['level'] == 'einzel' for r in rs)), (340, 54))
        keys = [(r['level'], r['form'], r['substance'], r['strength']) for r in rs]
        self.assertEqual(len(keys), len(set(keys)))

    def test_all_340_pack_rows_equal_the_catalogue_and_the_delivered_data(self):
        table = {(r['form'], r['substance'], r['strength']): cents(r['price_new_eur']) for r in rows() if r['level'] == 'pack'}
        ls = cl.lines()
        now = {(x['form'], x['name'], x['strength']): x['price_cents'] for x in ls}
        self.assertEqual(len(ls), 340)
        self.assertEqual(len(now), 340)  # keine Doppelzeilen
        self.assertEqual(now, table)
        delivered = {}
        for e in EXTRA:
            delivered[('vial' if e['format'] == 'vial_pack' else 'dual', e['name'], e['concentration'])] = e['price_cents']
        for pid, (v, d) in cl.MATCH.items():
            by = {f['id']: f for f in FORMATS}
            for ref, item_id, form in ((v, pid + '-x10', 'vial'), (d, 'dual-' + pid + '-x10', 'dual')):
                if ref:
                    delivered[(form, *ref)] = by[item_id]['price_cents']
        self.assertEqual(delivered, table)

    def test_old_sales_list_is_untouched_and_differs_from_v3(self):
        old = cl.lines(adjusted=False)
        self.assertEqual(len(old), 340)
        self.assertEqual(len({(x['form'], x['name'], x['strength']) for x in old}), 340)
        self.assertNotIn('owner_price_cents', old[0])
        oldp = {(x['form'], x['name'], x['strength']): x['price_cents'] for x in old}
        self.assertEqual(oldp[('vial', 'Retatrutide', '20 mg')], 47500)  # alte Verkaufsliste, Inhaberpreis v3 = 430
        self.assertNotEqual(oldp, {(x['form'], x['name'], x['strength']): x['price_cents'] for x in cl.lines()})

    def test_all_54_single_rows_equal_the_delivered_single_prices(self):
        mapping, got = shop_map(), delivered_singles()
        seen = set()
        for r in rows():
            if r['level'] != 'einzel':
                continue
            pid = mapping[(r['level'], r['form'], r['substance'], r['strength'])]
            seen.add((r['form'], pid))
            self.assertEqual(got[(r['form'], pid)], cents(r['price_new_eur']), (r['form'], pid))
        self.assertEqual(len(seen), 54)
        self.assertEqual(seen, set(got))
        for p in VIALS:
            self.assertEqual(p['price_status'], 'PREISFAMILIE_V3_2026_10_24')

    def test_recommendation_file_is_the_pack_table(self):
        recs = json.loads((PRICES / 'preisempfehlung.json').read_text())
        table = {(r['form'], r['substance'], r['strength']): float(r['price_new_eur']) for r in rows() if r['level'] == 'pack'}
        self.assertEqual({(r['form'], r['name'], r['strength']): float(r['price_eur']) for r in recs}, table)
        self.assertEqual(len(recs), 340)


class FamilyRules(unittest.TestCase):
    def test_dual_is_dearer_than_vial_for_single_and_pack(self):
        p = {(r['level'], r['form'], r['substance'], r['strength']): cents(r['price_new_eur']) for r in rows()}
        pairs = {'einzel': 0, 'pack': 0}
        for (lv, form, sub, st), price in p.items():
            if form == 'dual' and (lv, 'vial', sub, st) in p:
                pairs[lv] += 1
                self.assertGreater(price, p[(lv, 'vial', sub, st)], (lv, sub, st))
        self.assertEqual(pairs['einzel'], 27)
        self.assertGreater(pairs['pack'], 100)
        got = delivered_singles()  # zusaetzlich auf den ausgelieferten Daten
        for p_ in VIALS:
            self.assertGreater(got[('dual', p_['id'])], got[('vial', p_['id'])], p_['id'])
        by = {f['id']: f['price_cents'] for f in FORMATS}
        for p_ in VIALS:
            self.assertGreater(by['dual-' + p_['id'] + '-x10'], by[p_['id'] + '-x10'], p_['id'])

    def test_pack_piece_price_is_below_the_single_price(self):
        got = delivered_singles()
        by = {f['id']: f['price_cents'] for f in FORMATS}
        for p in VIALS:
            self.assertLess(by[p['id'] + '-x10'] / 10, got[('vial', p['id'])], p['id'])
            self.assertLess(by['dual-' + p['id'] + '-x10'] / 10, got[('dual', p['id'])], p['id'])

    def test_price_rises_with_the_dose_in_every_ladder(self):
        with open(PRICES / 'ausnahmen_v3.csv', newline='', encoding='utf-8') as fh:
            exc = {(r['level'], r['form'], r['substance'], r['zeile_klein_oder_einzel'], r['zeile_gross_oder_pack'])
                   for r in csv.DictReader(fh, delimiter=';') if r['regel'] in ('R1', 'R2')}  # nur Ausnahmen vom Steigen selbst
        groups = {}
        for r in rows():
            groups.setdefault((r['level'], r['form'], r['substance'], r['unit']), []).append((float(r['dose']), r['strength'], cents(r['price_new_eur'])))
        checked = 0
        for (lv, form, sub, _unit), lst in groups.items():
            lst.sort()
            for (d1, s1, p1), (d2, s2, p2) in zip(lst, lst[1:]):
                if (lv, form, sub, s1, s2) in exc:
                    continue
                checked += 1
                self.assertGreater(d2, d1, (lv, form, sub, s1, s2))
                self.assertGreater(p2, p1, (lv, form, sub, s1, s2))
        self.assertGreater(checked, 200)

    def test_documented_exceptions_reference_existing_rows(self):
        keys = {(r['level'], r['form'], r['substance'], r['strength']) for r in rows()}
        with open(PRICES / 'ausnahmen_v3.csv', newline='', encoding='utf-8') as fh:
            exc = list(csv.DictReader(fh, delimiter=';'))
        self.assertGreater(len(exc), 0)
        for r in exc:
            if r['level'] == 'pack':  # Leiter-Ausnahme: beide Zeilen der Pack-Leiter
                self.assertTrue((('pack', r['form'], r['substance'], r['zeile_klein_oder_einzel']) in keys), r['substance'])
                self.assertTrue((('pack', r['form'], r['substance'], r['zeile_gross_oder_pack']) in keys), r['substance'])
            else:  # R13 Einzel/Pack-Anteil: Einzelzeile (Substanzname der Einzelzeilen)
                self.assertEqual(r['level'], 'einzel/pack')
                self.assertTrue((('einzel', r['form'], r['substance'], r['zeile_klein_oder_einzel']) in keys), r['substance'])


class OwnerCases(unittest.TestCase):
    def test_owner_data_points(self):
        got = delivered_singles()
        self.assertLessEqual(got[('vial', 'retatrutide-30')], 12990)
        self.assertLessEqual(got[('vial', 'mots-c-40')], 8990)
        self.assertEqual(got[('dual', 'ghk-cu-100')], 9990)
        now = {(x['form'], x['name'], x['strength']): x['price_cents'] for x in cl.lines()}
        self.assertEqual((now[('vial', 'Retatrutide', '15 mg')], now[('vial', 'Retatrutide', '20 mg')]), (40000, 43000))
        by = {e['id']: e['price_cents'] for e in EXTRA}
        by.update({f['id']: f['price_cents'] for f in FORMATS})
        self.assertEqual(by['dual-ghk-cu-100-x10'], 47000)

    def test_shop_only_dual_pack_is_at_least_130_percent_of_the_vial_pack(self):
        f = next(x for x in FORMATS if x['id'] == 'dual-bpc-157-tb-500-x10')
        self.assertEqual(f['price_cents'], 72000)  # Vial-Pack BPC-157+TB-500 20 mg = 550 EUR (Tabelle), Dual mind. 1,30 x = 715 -> 720 EUR (E3)
        self.assertNotIn(('dual', 'BPC-157 + TB-500', '20 mg (10 mg + 10 mg)'), {(x['form'], x['name'], x['strength']) for x in cl.lines()})


class NoPurchaseData(unittest.TestCase):
    KEY = re.compile(r'(cost|einkauf|ek_|_ek|ziel_ek|target|intern|ting)', re.I)
    TEXT = re.compile(r'(ek_je_zeile|ziel_ek|einkaufspreis|cost_eur|ting_target|vial10_eur|dual10_eur|\bting\b)', re.I)

    def _keys(self, obj, path=''):
        if isinstance(obj, dict):
            for k, v in obj.items():
                self.assertIsNone(self.KEY.search(k), path + '/' + k)
                self._keys(v, path + '/' + k)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                self._keys(v, f'{path}[{i}]')

    def test_no_purchase_fields_or_producer_name_in_data_or_public(self):
        for f in (ROOT / 'data').glob('*.json'):
            self._keys(json.loads(f.read_text()), f.name)
            self.assertIsNone(self.TEXT.search(f.read_text()), f.name)
        public = ROOT / 'public'
        self.assertTrue(public.is_dir())
        for f in public.rglob('*'):
            if f.suffix in {'.js', '.html', '.json', '.css', '.csv', '.txt'}:
                self.assertIsNone(self.TEXT.search(f.read_text(errors='ignore')), str(f))
            self.assertNotIn(f.name, ('preisfamilie_v3.csv', 'ausnahmen_v3.csv', 'verhandlungsliste_v3.csv', 'preisempfehlung.json'))


if __name__ == '__main__':
    unittest.main()
