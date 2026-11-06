import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class BuildContract(unittest.TestCase):
    def test_complete_reference_catalog_is_preserved(self):
        script = ROOT / 'build.py'
        self.assertTrue(script.exists(), 'Isolated build entrypoint missing')
        subprocess.run([sys.executable, str(script)], check=True, capture_output=True)
        html = (ROOT / 'public/index.html').read_text()
        source = (ROOT / 'evidence/reference-current/index.html').read_text()
        source_match = re.search(r'id="productData"[^>]*>(.*?)</script>', source, re.S)
        assert source_match is not None
        raw = json.loads(source_match[1])
        expected = raw
        actual_match = re.search(r'id="productData"[^>]*>(.*?)</script>', html, re.S)
        assert actual_match is not None
        actual = json.loads(actual_match[1])
        # Vorlage bleibt vollstaendig und in Reihenfolge; dahinter nur die zwei vom Inhaber bestellten Einzeldosen (Semaglutide 15 mg, Tirzepatide 40 mg)
        self.assertEqual([p['id'] for p in actual], [p['id'] for p in expected] + ['semaglutide-15', 'tirzepatide-40'])
        self.assertEqual(len(actual), 27)
        priced = {x['id']: x for x in json.loads((ROOT / 'data/products.json').read_text())}
        for p, q in zip(actual, expected):
            self.assertEqual(p['price'], priced[p['id']]['price'])  # shop price list (competitor-anchored)
            self.assertEqual(p['image'], q['image'].replace('.png', '.webp'))
        self.assertIn('el-primary-light.svg', html)
        self.assertNotIn('checkoutDemo', (ROOT/'public/app.js').read_text())
        self.assertIn('telegram-web-app.js', html)
        self.assertEqual(list((ROOT/'public/assets').rglob('*.png')), [])
        self.assertLess(sum(f.stat().st_size for f in (ROOT/'public').rglob('*') if f.is_file()), 9_000_000)  # Budget 8 MB fuer 25 Produkte, 9 MB seit 27 (zwei Einzeldosen auf Inhaberwunsch)
        catalog = json.loads((ROOT/'data/catalog.json').read_text())
        for entry in catalog['dual_chamber']:
            self.assertTrue((ROOT/'public'/entry['image']).is_file(), entry['id'])
            self.assertFalse(entry['orderable'])
            self.assertIsNone(entry['price_cents'])
        for item in catalog['items']:
            self.assertTrue((ROOT/'public'/item['image']).is_file(), item['id'])
            self.assertIs(item['orderable'], False)
        self.assertTrue((ROOT/'public/sw.js').is_file())
        self.assertNotIn('__BUILD__', (ROOT/'public/sw.js').read_text())

if __name__ == '__main__':
    unittest.main()
