import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FormatCatalogContract(unittest.TestCase):
    def test_formats_are_current_reference_offers_with_market_based_prices(self):
        entries = json.loads((ROOT / 'data/shop-formats.json').read_text())
        vials = json.loads((ROOT / 'data/products.json').read_text())
        by_id = {p['id']: p for p in vials}
        duals = [p for p in entries if p['format'] == 'dual_chamber']
        pens = [p for p in entries if p['format'] == 'pen']
        self.assertEqual(len(duals), 27)
        self.assertEqual(len(pens), 1)
        self.assertEqual({p['base_product_id'] for p in duals}, set(by_id))
        packs = [p for p in entries if p['format'] in ('vial_pack', 'dual_pack')]
        self.assertEqual(len(packs), 54)
        self.assertEqual(len({p['id'] for p in entries + vials}), 109)
        for p in duals:
            self.assertGreaterEqual(p['price_cents'], by_id[p['base_product_id']]['price_cents'] + 1000)  # Doppelkammer teurer als das Vial
            self.assertEqual(p['image_type'], 'REFERENCE_ARTWORK')
            self.assertTrue((ROOT / 'asset-cache-current' / p['image']).is_file(), p['id'])
            self.assertNotIn('batch', p)
            self.assertNotIn('qr', p)
        self.assertEqual(pens[0]['price_cents'], 2000)
        self.assertEqual(pens[0]['image'], 'assets/products/reusable-pen.png')


if __name__ == '__main__':
    unittest.main()
