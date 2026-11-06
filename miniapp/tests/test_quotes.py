import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERN = (ROOT.parent / 'preislisten/preisfamilie_v3.csv').is_file()     # Renés Paket enthaelt keine internen Preisdateien
spec = importlib.util.spec_from_file_location('quote_server', ROOT / 'server.py')
assert spec is not None and spec.loader is not None
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)
server.TERMS = server.relaxed()  # Altfaelle ohne Mindestwert/Versand; echte Konditionen: tests/test_terms.py


def catalog_price(form, name, strength):
    """10er-Preis aus der eingefrorenen Preisfamilie v3 (preislisten/preisfamilie_v3.csv, level=pack) in Cent."""
    import csv
    with open(ROOT.parent / 'preislisten/preisfamilie_v3.csv', newline='', encoding='utf-8') as fh:
        for r in csv.DictReader(fh, delimiter=';'):
            if (r['level'], r['form'], r['substance'], r['strength']) == ('pack', form, name, strength):
                return round(float(r['price_new_eur']) * 100)
    raise KeyError((form, name, strength))


class QuoteRequestContract(unittest.TestCase):
    def test_mixed_format_request_persists_without_inventing_a_total(self):
        products = json.loads((ROOT / 'data/products.json').read_text()) + json.loads((ROOT / 'data/shop-formats.json').read_text())
        with tempfile.TemporaryDirectory(dir=Path.home() / '.hermes/cache/scratch') as tmp:
            db_path = Path(tmp) / 'quotes.sqlite3'
            body = {'request_id': 'quote-contract-001', 'research_confirmed': True,
                    'items': [{'id': 'retatrutide-10', 'quantity': 1}, {'id': 'dual-retatrutide-10', 'quantity': 2}, {'id': 'mehrweg-pen', 'quantity': 1}]}
            result = server.save_request(body, products, db_path, 'preview')
            by = {p['id']: p['price_cents'] for p in products}
            expected = by['retatrutide-10'] + 2 * by['dual-retatrutide-10'] + by['mehrweg-pen']
            self.assertEqual(result['total_cents'], expected)
            self.assertEqual(result['known_total_cents'], expected)
            self.assertEqual(result['quote_items'], 0)
            self.assertEqual(server.save_request(body, products, db_path, 'preview')['id'], result['id'])
            with sqlite3.connect(db_path) as db:
                payload = json.loads(db.execute('SELECT payload FROM requests').fetchone()[0])
            self.assertEqual(payload['items'][1]['unit_price_cents'], by['dual-retatrutide-10'])
            self.assertEqual(payload['items'][1]['format'], 'dual_chamber')

    def test_unknown_price_still_stays_on_request_and_is_never_zero(self):
        products = [{'id': 'x', 'name': 'X', 'concentration': '1', 'price_cents': None, 'price_status': 'ON_REQUEST', 'format': 'dual_chamber'},
                    {'id': 'y', 'name': 'Y', 'concentration': '1', 'price_cents': 1000, 'format': 'vial'}]
        with tempfile.TemporaryDirectory(dir=Path.home() / '.hermes/cache/scratch') as tmp:
            result = server.save_request({'request_id': 'quote-contract-002', 'research_confirmed': True,
                                          'items': [{'id': 'x', 'quantity': 1}, {'id': 'y', 'quantity': 1}]}, products, Path(tmp) / 'q.sqlite3', 'preview')
            self.assertIsNone(result['total_cents'])
            self.assertEqual(result['known_total_cents'], 1000)
            self.assertEqual(result['quote_items'], 1)

    def test_pack_items_are_priced_and_labelled_as_ten_packs(self):
        products = json.loads((ROOT / 'data/products.json').read_text()) + json.loads((ROOT / 'data/shop-formats.json').read_text())
        by = {p['id']: p for p in products}
        with tempfile.TemporaryDirectory(dir=Path.home() / '.hermes/cache/scratch') as tmp:
            body = {'request_id': 'quote-contract-pack-01', 'research_confirmed': True,
                    'items': [{'id': 'retatrutide-10-x10', 'quantity': 1}, {'id': 'dual-retatrutide-10-x10', 'quantity': 2}]}
            result = server.save_request(body, products, Path(tmp) / 'q.sqlite3', 'preview')
            self.assertEqual(result['total_cents'], by['retatrutide-10-x10']['price_cents'] + 2 * by['dual-retatrutide-10-x10']['price_cents'])
            text = server.confirmation_text(result, [{'quantity': 1, 'name': 'Retatrutide', 'strength': '10 mg', 'format': 'vial_pack'},
                                                     {'quantity': 2, 'name': 'Retatrutide', 'strength': '10 mg', 'format': 'dual_pack'}])
            self.assertIn('10er-Pack', text)
            self.assertNotIn('Artikel', text)


    @unittest.skipUnless(INTERN, 'interne Preisdateien (preislisten/) nicht im Paket')
    def test_catalogue_only_pack_items_are_orderable_at_the_sales_sheet_price(self):
        products = server.load_products()
        by = {p['id']: p for p in products}
        self.assertIn('cat-vial-semaglutide-40-mg', by)
        with tempfile.TemporaryDirectory(dir=Path.home() / '.hermes/cache/scratch') as tmp:
            body = {'request_id': 'quote-contract-cat-01', 'research_confirmed': True,
                    'items': [{'id': 'cat-vial-semaglutide-40-mg', 'quantity': 2}, {'id': 'cat-dual-semaglutide-50-mg', 'quantity': 1}]}
            result = server.save_request(body, products, Path(tmp) / 'q.sqlite3', 'preview')
            self.assertEqual(result['total_cents'], 2 * by['cat-vial-semaglutide-40-mg']['price_cents'] + by['cat-dual-semaglutide-50-mg']['price_cents'])  # Preise aus data/ (Preisfamilie v3)
            self.assertEqual((by['cat-vial-semaglutide-40-mg']['price_cents'], by['cat-dual-semaglutide-50-mg']['price_cents']), (catalog_price('vial', 'Semaglutide', '40 mg'), catalog_price('dual', 'Semaglutide', '50 mg')))
            self.assertIn('10er-Pack', server.confirmation_text(result, [{'quantity': 2, 'name': 'Semaglutide', 'strength': '40 mg', 'format': 'vial_pack'}]))


if __name__ == '__main__':
    unittest.main()
