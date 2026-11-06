"""Preislogik: Einzel- und Packpreise = Preisfamilie v3 (preislisten/preisfamilie_v3.csv, Gleichheitstests in test_preisfamilie.py). Einkaufspreise bleiben intern."""
import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import importlib.util
spec = importlib.util.spec_from_file_location('apply_pricing', ROOT / 'tools/apply_pricing.py')
ap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ap)

VIALS = json.loads((ROOT / 'data/products.json').read_text())
FORMATS = json.loads((ROOT / 'data/shop-formats.json').read_text())
REF = json.loads((ROOT / 'data/reference-prices.json').read_text())
sys_path_tools = str(ROOT / 'tools')
import sys
sys.path.insert(0, sys_path_tools)
import catalog_lines as cl
PACKS_EXTRA = json.loads((ROOT / 'data/catalog-packs.json').read_text())
import csv
with open(ROOT.parent / 'preislisten/preisfamilie_v3_shopzuordnung.csv', newline='', encoding='utf-8') as _fh:
    _MAP = {(r['level'], r['form'], r['substance'], r['strength']): r['shop_produkt'] for r in csv.DictReader(_fh, delimiter=';')}
with open(ROOT.parent / 'preislisten/preisfamilie_v3.csv', newline='', encoding='utf-8') as _fh:
    TABLE_SINGLE = [dict(r, shop_produkt=_MAP[(r['level'], r['form'], r['substance'], r['strength'])]) for r in csv.DictReader(_fh, delimiter=';') if r['level'] == 'einzel']


class PricingRules(unittest.TestCase):
    def test_end_90_up_never_rounds_below_the_input(self):
        for euro in (174.21, 174.95, 175.0, 270.69, 0.5, 99.9, 99.91):
            cents = ap.end_90_up(euro)
            self.assertGreaterEqual(cents, round(euro * 100), euro)
            self.assertEqual(cents % 100, 90)
            self.assertLess(cents - round(euro * 100), 100)

    def test_end_90_up_survives_float_noise_on_the_90_boundary(self):
        self.assertEqual(ap.end_90_up(3 * 8.30), 2490)   # 24.900000000000002 in floating point
        self.assertEqual(ap.end_90_up(24.90), 2490)
        self.assertEqual(ap.end_90_up(24.91), 2590)
        self.assertEqual(ap.end_90_up(0.0), -10 + 100)

    def test_vial_prices_equal_the_preisfamilie_v3(self):
        """Ersetzt test_vial_prices_equal_the_market_median (Preisfamilie v3, 24.10.2026): Einzel-Vial = Tabelle level=einzel, Endung ,90, mehr mg kostet mehr."""
        table = {r['shop_produkt']: r for r in TABLE_SINGLE if r['form'] == 'vial'}
        self.assertEqual(set(table), {p['id'] for p in VIALS})
        for p in VIALS:
            self.assertEqual(p['price_cents'], round(float(table[p['id']]['price_new_eur']) * 100), p['id'])
            self.assertEqual(p['price_cents'] % 100, 90, p['id'])
            self.assertEqual(p['price_status'], ap.BASIS)
        for group in {p['group'] for p in VIALS}:
            ladder = sorted((ap.dose(p), p['price_cents']) for p in VIALS if p['group'] == group)
            for (d1, c1), (d2, c2) in zip(ladder, ladder[1:]):
                self.assertGreater(c2, c1, group)  # more mg always costs more

    def test_market_interpolation_is_exact_on_quotes_and_log_linear_between(self):
        self.assertEqual(ap.vendor_at({'10': 50, '40': 200}, 10), 50)
        self.assertAlmostEqual(ap.vendor_at({'10': 50, '40': 200}, 20), 100, places=6)   # price per mg constant
        self.assertIsNone(ap.vendor_at({'10': 50}, 20))                                   # one quote: no guess
        self.assertIsNone(ap.vendor_at({'10': 50, '20': 90}, 100))                        # far extrapolation refused
        self.assertEqual(ap.market_reference({'a': {'10': 40}, 'b': {'10': 60}, 'c': {'10': 50}}, 10), 50)

    def test_floor_90_never_exceeds_the_target(self):
        for cents in (5000, 5090, 5089, 12345, 1000, 100):
            v = ap.floor_90(cents)
            self.assertEqual(v % 100, 90)
            self.assertTrue(v <= cents or v == 990)

    def test_dual_chamber_is_dearer_than_the_vial_and_equal_to_the_preisfamilie_v3(self):
        """Ersetzt ..._equal_to_the_market_pen: Doppelkammer-Einzel (inklusive Pen) = Tabelle, teurer als das Vial, Endung ,90; GHK-Cu 100 mg = 99,90."""
        table = {r['shop_produkt']: r for r in TABLE_SINGLE if r['form'] == 'dual'}
        by = {p['id']: p for p in VIALS}
        duals = [f for f in FORMATS if f['format'] == 'dual_chamber']
        self.assertEqual({f['base_product_id'] for f in duals}, set(table))
        for f in duals:
            v = by[f['base_product_id']]
            self.assertEqual(f['price_cents'], round(float(table[v['id']]['price_new_eur']) * 100), f['id'])
            self.assertGreater(f['price_cents'], v['price_cents'], f['id'])
            self.assertEqual(f['price_cents'] % 100, 90, f['id'])
        self.assertEqual(next(f for f in duals if f['base_product_id'] == 'ghk-cu-100')['price_cents'], 9990)

    def test_dual_chamber_single_prices_rise_with_the_dose(self):
        by = {p['id']: p for p in VIALS}
        groups = {}
        for f in FORMATS:
            if f['format'] == 'dual_chamber':
                v = by[f['base_product_id']]
                groups.setdefault(v['group'], []).append((ap.dose(v), f['price_cents'], f['id']))
        for group, lst in groups.items():
            lst.sort()
            for (d1, p1, i1), (d2, p2, i2) in zip(lst, lst[1:]):
                self.assertGreaterEqual(p2, p1 + 100, (i1, i2))

    def test_pack_catalogue_has_one_vial_and_one_dual_pack_per_product(self):
        packs = [f for f in FORMATS if f['format'] in ('vial_pack', 'dual_pack')]
        self.assertEqual(sorted(f['id'] for f in packs if f['format'] == 'vial_pack'), sorted(p['id'] + '-x10' for p in VIALS))
        self.assertEqual(sorted(f['id'] for f in packs if f['format'] == 'dual_pack'), sorted('dual-' + p['id'] + '-x10' for p in VIALS))
        single = {p['id']: p['price_cents'] for p in VIALS}
        single.update({f['id']: f['price_cents'] for f in FORMATS if f['format'] == 'dual_chamber'})
        for f in packs:
            self.assertEqual(f['pack_size'], 10)
            base_single = single[f['id'][:-4]]
            self.assertLess(f['price_cents'] / 10, base_single, f['id'])  # a pack is always cheaper per piece than single buying
            self.assertTrue(f['link'] and not f['link'].endswith('-x10'))

    def test_pack_prices_are_the_preisfamilie_v3_prices(self):
        """Ersetzt ..._owners_sales_sheet_prices: Shop-Packs = cl.lines() = Tabelle level=pack (alle 340 Zeilen in test_preisfamilie.py)."""
        index = {(x['form'], x['name'], x['strength']): x['price_cents'] for x in cl.lines()}
        by = {f['id']: f for f in FORMATS}
        checked = 0
        for pid, (v, d) in cl.MATCH.items():
            for ref, item_id, form in ((v, pid + '-x10', 'vial'), (d, 'dual-' + pid + '-x10', 'dual')):
                if ref:
                    checked += 1
                    self.assertEqual(by[item_id]['price_cents'], index[(form, *ref)], item_id)
                    self.assertEqual(by[item_id]['price_status'], ap.BASIS, item_id)
        self.assertEqual(checked, 53)
        # Produkt ohne Katalogzeile (Doppelkammer-Pack BPC-157+TB-500 20 mg): mind. 1,30 x Vial-Pack (550) = 720 EUR
        dual = by['dual-bpc-157-tb-500-x10']['price_cents']
        self.assertEqual(dual, 72000)
        self.assertGreater(dual, by['bpc-157-tb-500-x10']['price_cents'])

    def test_full_catalogue_contains_every_sales_sheet_line_exactly_once(self):
        lines = cl.lines()
        sheet = [x for x in lines if not x.get('supplement')]
        self.assertEqual((len(sheet), sum(x['form'] == 'vial' for x in sheet), sum(x['form'] == 'dual' for x in sheet)), (238, 124, 114))  # Verkaufsblatt des Inhabers
        extra = [x for x in lines if x.get('supplement')]  # Sortimentsergaenzung aus den Lieferantenlisten (102 Zeilen, Zubehoer ausgenommen)
        self.assertEqual((len(extra), sum(x['form'] == 'vial' for x in extra), sum(x['form'] == 'dual' for x in extra)), (102, 101, 1))
        shop = {f['id'] for f in FORMATS if f['format'] in ('vial_pack', 'dual_pack')}
        matched = sum(1 for pid, (v, d) in cl.MATCH.items() for ref in (v, d) if ref)
        self.assertEqual(len(PACKS_EXTRA) + matched, len(lines))
        self.assertEqual(len({e['id'] for e in PACKS_EXTRA}), len(PACKS_EXTRA))
        self.assertFalse(shop & {e['id'] for e in PACKS_EXTRA})
        index = {(x['form'], x['name'], x['strength']): x['price_cents'] for x in lines}
        for e in PACKS_EXTRA:
            form = 'vial' if e['format'] == 'vial_pack' else 'dual'
            self.assertEqual(e['price_cents'], index[(form, e['name'], e['concentration'])], e['id'])
            self.assertEqual(e['pack_size'], 10)
            self.assertIn(e['section'], cl.SECTIONS)

    def test_single_price_is_never_below_the_piece_price_of_the_pack(self):
        by = {f['id']: f for f in FORMATS}
        for p in VIALS:
            self.assertGreaterEqual(p['price_cents'], by[p['id'] + '-x10']['price_cents'] / 10 * 1.2 - 100, p['id'])
        for f in FORMATS:
            if f['format'] == 'dual_chamber':
                self.assertGreaterEqual(f['price_cents'], by[f['id'] + '-x10']['price_cents'] / 10 * 1.2 - 100, f['id'])

    def test_purchase_prices_never_reach_public_data_or_the_build(self):
        needles = ('vial10_eur', 'dual10_eur', 'shop_costs', 'einkaufspreis')
        for rel in ('data/products.json', 'data/shop-formats.json', 'data/catalog.json'):
            text = (ROOT / rel).read_text().lower()
            for n in needles:
                self.assertNotIn(n, text, (rel, n))
        public = ROOT / 'public'
        if public.is_dir():
            for f in public.rglob('*'):
                if f.suffix in {'.js', '.html', '.json', '.css'}:
                    text = f.read_text(errors='ignore').lower()
                    for n in needles:
                        self.assertNotIn(n, text, (str(f), n))

    def test_applying_twice_gives_the_same_result(self):
        before = (ROOT / 'data/shop-formats.json').read_text(), (ROOT / 'data/products.json').read_text()
        vials, out, *_ = ap.apply()
        self.assertEqual((ROOT / 'data/shop-formats.json').read_text(), before[0])
        self.assertEqual((ROOT / 'data/products.json').read_text(), before[1])


if __name__ == '__main__':
    unittest.main()
