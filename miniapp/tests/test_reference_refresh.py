"""Current-source visual assets and prices, not the old placeholder catalogue."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CurrentReferenceTests(unittest.TestCase):
    def test_pen_uses_current_reference_artwork_and_price(self):
        formats = json.loads((ROOT / 'data/shop-formats.json').read_text())
        pen = next(p for p in formats if p['format'] == 'pen')
        self.assertEqual(pen['image'], 'assets/products/reusable-pen.png')
        self.assertEqual(pen['price_cents'], 2000)
        self.assertEqual(pen['image_type'], 'REFERENCE_ARTWORK')
        self.assertTrue((ROOT / 'public/assets/products/reusable-pen.webp').is_file())

    def test_dual_variants_use_their_own_reference_images_and_prices(self):
        vials = {p['id']: p for p in json.loads((ROOT / 'data/products.json').read_text())}
        duals = [p for p in json.loads((ROOT / 'data/shop-formats.json').read_text()) if p['format'] == 'dual_chamber']
        self.assertEqual(len(duals), 27)
        for p in duals:
            base = vials[p['base_product_id']]
            self.assertEqual(p['image'], 'assets/products/dual-chamber/' + base['id'] + '.png')
            self.assertGreaterEqual(p['price_cents'], base['price_cents'] + 1000)
            self.assertNotIn('batch', p)
            self.assertNotIn('qr', p)

    def test_home_uses_the_current_pen_and_dual_reference_scene(self):
        html = (ROOT / 'public/index.html').read_text()
        scripts = html + (ROOT / 'public/app.js').read_text() + (ROOT / 'public/i18n.js').read_text()
        self.assertIn('hero-focus/home-mobile.webp', scripts)
        self.assertIn('variants.js', html)
        self.assertNotIn('assets/shop/mehrweg-pen.svg', scripts)
        self.assertTrue((ROOT / 'public/assets/products/dual-chamber/retatrutide-10.webp').is_file())
        self.assertNotIn('Demo-Checkout', scripts.replace('Verpackungsvorschau. Nicht freigegeben. Demo-Checkout.', ''))


if __name__ == '__main__':
    unittest.main()
