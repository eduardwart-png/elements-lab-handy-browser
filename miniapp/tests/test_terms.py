"""Konditionen: Mindestbestellwert, Versand inklusive, Mengenrabatt, Sammelbestellung (Server) + Paritaet zu extensions/terms.js."""
import importlib.util
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERN = (ROOT.parent / 'preislisten/preisfamilie_v3.csv').is_file()     # Renés Paket enthaelt keine internen Preisdateien: diese Pruefungen laufen nur im Hauptprojekt
SKIP_INTERN = unittest.skipUnless(INTERN, 'interne Preisdateien (preislisten/) nicht im Paket')
sys.path.insert(0, str(ROOT))
import terms  # noqa: E402

spec = importlib.util.spec_from_file_location('terms_server', ROOT / 'server.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)
T = terms.load_terms()

# Schwellen aus der Abnahme (Cent): Zwischensumme -> (Rabatt%, Rabatt bei voller Berechtigung, Zahlbetrag, min_ok direkt)
THRESHOLDS = [
    (49990, 0, 0, 49990, False),
    (50000, 0, 0, 50000, True),
    (99990, 0, 0, 99990, True),
    (100000, 0, 0, 100000, True),
    (249990, 0, 0, 249990, True),
    (250000, 5, 12500, 237500, True),
    (499990, 5, 24999, 474991, True),
    (500000, 10, 50000, 450000, True),
]


class Calc(unittest.TestCase):
    def test_terms_file_has_no_shipping_fields(self):
        self.assertEqual(T['min_order_cents'], 50000)
        self.assertEqual(T['collective_min_cents'], 20000)
        self.assertEqual(T['delivery_weeks'], {'min': 2, 'max': 3})
        self.assertNotIn('shipping_cents', T)
        self.assertNotIn('free_shipping_cents', T)

    def test_threshold_table(self):
        for subtotal, percent, discount, payable, min_ok in THRESHOLDS:
            r = terms.calc([(1, subtotal, True)], T)
            self.assertEqual((r['discount_percent'], r['discount_cents'], r['payable_cents'], r['min_ok'], r['shipping_cents']), (percent, discount, payable, min_ok, 0), subtotal)

    def test_shipping_is_always_included(self):
        for cents in (20000, 49990, 50000, 99990, 100000, 250000, 500000):
            r = terms.calc([(1, cents, True)], T, collective=cents < 50000)
            self.assertEqual(r['shipping_cents'], 0)
            self.assertEqual(r['payable_cents'], cents - r['discount_cents'])

    def test_discount_only_on_eligible_lines_and_tiers(self):
        t1, t2 = T['tiers'][0], T['tiers'][1]
        a = terms.calc([(1, t1['min_cents'], True)], T)
        self.assertEqual((a['discount_percent'], a['discount_cents']), (t1['percent'], t1['min_cents'] * t1['percent'] // 100))
        b = terms.calc([(1, t2['min_cents'] - 10000, False), (1, 10000, True)], T)
        self.assertEqual(b['discount_percent'], t2['percent'])
        self.assertEqual(b['discount_cents'], 10000 * t2['percent'] // 100)  # nur der berechtigte Teil
        self.assertEqual(b['eligible_cents'], 10000)
        c = terms.calc([(1, t1['min_cents'], False)], T)
        self.assertEqual((c['discount_percent'], c['discount_cents']), (t1['percent'], 0))  # Stufe erreicht, aber nichts rabattfaehig

    def test_collective_only_below_minimum_order(self):
        lo, hi = T['collective_min_cents'], T['min_order_cents']
        ok = terms.calc([(1, lo, True)], T, collective=True)
        self.assertTrue(ok['min_ok'] and ok['collective'] and not ok['direct'])
        self.assertEqual((ok['shipping_cents'], ok['payable_cents']), (0, lo))
        self.assertFalse(terms.calc([(1, lo - 1, True)], T, collective=True)['min_ok'])
        top = terms.calc([(1, hi - 10, True)], T, collective=True)
        self.assertTrue(top['min_ok'] and top['collective'])
        direct = terms.calc([(1, hi, True)], T, collective=True)
        self.assertTrue(direct['direct'] and direct['min_ok'] and not direct['collective'])  # Wunsch wird ab dem Mindestbestellwert verworfen
        self.assertFalse(terms.calc([(1, lo, True)], T, collective=False)['min_ok'])  # ohne Haken gilt 500

    def test_python_and_javascript_agree(self):
        rnd = random.Random(7)
        cases = []
        prices = [None, 1990, 2000, 9900, 15000, 19999, 20000, 24990, 25000, 37000, 49000, 49990, 50000, 99990, 100000, 120000, 249990, 250000, 499990, 500000]
        for _ in range(400):
            lines = [[rnd.randint(1, 5), rnd.choice(prices), rnd.random() < 0.7] for _ in range(rnd.randint(1, 5))]
            cases.append({'lines': lines, 'collective': rnd.random() < 0.5})
        out = subprocess.run(['node', str(ROOT / 'tests/terms_calc.cjs')], input=json.dumps({'cases': cases}), capture_output=True, text=True, check=True).stdout
        js = json.loads(out)
        for case, got in zip(cases, js):
            want = terms.calc([tuple(x) for x in case['lines']], T, case['collective'])
            for key in want:
                self.assertEqual(got[key], want[key], (case, key))


class ServerRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.products = server.load_products()
        cls.pack = next(p for p in cls.products if p.get('format') == 'vial_pack' and 35000 <= p['price_cents'] <= 49000 and p.get('discount_ok'))
        cls.single = next(p for p in cls.products if p.get('format', 'vial') == 'vial' and 5000 <= p['price_cents'] < 20000)

    def save(self, items, collective=None, key='terms-test-0001'):
        body = {'request_id': key, 'items': [{'id': i, 'quantity': q} for i, q in items], 'research_confirmed': True}
        if collective is not None:
            body['collective'] = collective
        with tempfile.TemporaryDirectory() as d:
            return server.save_request(body, self.products, Path(d) / 'r.sqlite3', 'preview', terms=T)

    def test_below_minimum_is_rejected_with_amounts(self):
        with self.assertRaises(terms.MinOrderError) as ctx:
            self.save([(self.single['id'], 1)])
        self.assertEqual((ctx.exception.minimum_cents, ctx.exception.subtotal_cents), (T['min_order_cents'], self.single['price_cents']))

    def test_minimum_reached_has_no_shipping(self):
        r = self.save([(self.pack['id'], 2)])
        sub = 2 * self.pack['price_cents']
        self.assertEqual((r['subtotal_cents'], r['shipping_cents'], r['total_cents'], r['collective']), (sub, 0, sub, False))

    def test_collective_accepts_cart_between_200_and_499(self):
        qty = -(-T['collective_min_cents'] // self.single['price_cents'])
        sub = qty * self.single['price_cents']
        self.assertTrue(T['collective_min_cents'] <= sub < T['min_order_cents'], sub)
        r = self.save([(self.single['id'], qty)], collective=True)
        self.assertTrue(r['collective'])
        self.assertEqual((r['shipping_cents'], r['total_cents']), (0, sub))

    def test_collective_flag_is_dropped_at_minimum_order(self):
        qty = -(-T['min_order_cents'] // self.pack['price_cents'])
        r = self.save([(self.pack['id'], qty)], collective=True)
        self.assertFalse(r['collective'])

    def test_volume_discount_without_shipping(self):
        n = -(-T['tiers'][0]['min_cents'] // self.pack['price_cents'])
        r = self.save([(self.pack['id'], n)])
        self.assertEqual(r['shipping_cents'], 0)
        self.assertEqual(r['discount_percent'], T['tiers'][0]['percent'])
        self.assertEqual(r['total_cents'], r['subtotal_cents'] - r['discount_cents'])

    def test_invalid_collective_flag(self):
        with self.assertRaises(ValueError):
            self.save([(self.pack['id'], 2)], collective='yes')



class PackPrices(unittest.TestCase):
    def test_dual_pack_is_at_least_15_percent_above_vial_pack_and_tens(self):
        products = server.load_products()
        packs = [p for p in products if p.get('format') in ('vial_pack', 'dual_pack') and p.get('line_name')]
        by = {(p['format'], p['line_name'], p['line_strength']): p for p in packs}
        pairs = 0
        for (fmt, name, strength), p in by.items():
            if fmt != 'vial_pack':
                continue
            d = by.get(('dual_pack', name, strength))
            if d:
                pairs += 1
                if d.get('price_status') == 'SHOP_ONLY_FIXED_2026_10_24':  # Shop-Dual-Pack ohne Katalogzeile (BPC-157+TB-500 20 mg) = 720 EUR (mind. 1,30 x Vial-Pack 550)
                    self.assertEqual(d['price_cents'], 72000, (name, strength))
                    self.assertGreater(d['price_cents'], p['price_cents'], (name, strength))
                    continue
                self.assertGreaterEqual(d['price_cents'] * 100, p['price_cents'] * 115, (name, strength))
        self.assertGreater(pairs, 70)
        # Zehner-Preise im Katalog (Owner 24.10.2026), Ausnahme: Zeilen ohne Empfehlung bleiben bei Blattpreis
        tens = sum(1 for p in packs if p['price_cents'] % 1000 == 0)
        self.assertGreater(tens, len(packs) * 0.9)


class OwnerPriceRules(unittest.TestCase):
    @SKIP_INTERN
    def test_focus_substances_follow_the_preisfamilie_v3(self):
        """Ersetzt test_focus_substances_never_below_the_old_sales_sheet: die eingefrorene Preisfamilie v3 ist die Preisquelle und senkt
        einzelne Fokus-Zeilen unter die alte Liste (z. B. Reta 60 mg Vial-Pack). Geprueft: Fokus-Zeilen == Tabelle, Inhaberpreise fest."""
        import csv
        sys.path.insert(0, str(ROOT / 'tools'))
        import catalog_lines as cl
        with open(ROOT.parent / 'preislisten/preisfamilie_v3.csv', newline='', encoding='utf-8') as fh:
            table = {(r['form'], r['substance'], r['strength']): round(float(r['price_new_eur']) * 100) for r in csv.DictReader(fh, delimiter=';') if r['level'] == 'pack'}
        now = {(x['form'], x['name'], x['strength']): x['price_cents'] for x in cl.lines()}
        checked = 0
        for key, price in now.items():
            if key[1] in ('GHK-Cu', '5-Amino-1MQ', 'Retatrutide'):
                checked += 1
                self.assertEqual(price, table[key], key)
        self.assertGreater(checked, 20)
        self.assertEqual((now[('vial', 'Retatrutide', '15 mg')], now[('vial', 'Retatrutide', '20 mg')]), (40000, 43000))  # Inhaberentscheidung 24.10.2026
        self.assertEqual(now[('vial', 'GHK-Cu', '100 mg')], 19000)  # Stammkundenpreis aus der alten Liste

    @SKIP_INTERN
    def test_every_catalogue_price_is_a_multiple_of_ten_euros(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        import catalog_lines as cl
        bad = [(x['form'], x['name'], x['strength'], x['price_cents']) for x in cl.lines() if x['price_cents'] % 1000]
        self.assertEqual(bad, [])

    @SKIP_INTERN
    def test_smaller_dose_is_at_least_three_percent_cheaper(self):
        """Owner-Regel: kleinere Dosis immer mindestens 3 % guenstiger als die naechstgroessere (Vial-Packs und Doppelkammer-Packs)."""
        sys.path.insert(0, str(ROOT / 'tools'))
        import catalog_lines as cl
        import re
        groups = {}
        for x in cl.lines():
            m = re.match(r'([\d.,]+)\s*(\S+)', x['strength'])
            if m:
                groups.setdefault((x['form'], x['name'], m.group(2)), []).append((float(m.group(1).replace(',', '.')), x['price_cents']))
        bad = []
        for key, lst in groups.items():
            lst.sort()
            for (d1, p1), (d2, p2) in zip(lst, lst[1:]):
                if d2 > d1 and p1 > p2 * 0.97 + 1:
                    bad.append((key, d1, p1, d2, p2))
        self.assertEqual(bad, [])


if __name__ == '__main__':
    unittest.main()
