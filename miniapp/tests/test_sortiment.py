"""Sortiment und Einkaufszuordnung (Owner 24.10.2026: es darf nichts fehlen, was lieferbar ist; Marge nur mit dem richtigen Einkaufspreis).
Braucht die Preis-Umgebung (openpyxl, reportlab); ohne sie werden die Tests uebersprungen:  ~/.hermes/tools/elements-preis/v/bin/python -m unittest tests.test_sortiment"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRE = ROOT.parent / 'preislisten'
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(PRE))
try:
    import ting_check as tc
    import sortiment_ergaenzung as se
    import catalog_lines as cl
except ImportError:  # pragma: no cover
    tc = None


@unittest.skipIf(tc is None, 'Preis-Umgebung (openpyxl) fehlt')
class Sortiment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, _ = tc.load()
        cls.by = {(r['form'], r['name'], r['strength']): r for r in cls.rows}

    def cost(self, form, name, strength):
        r = self.by[(form, name, strength)]
        return r['ting'] if r.get('ting') is not None else r.get('other')

    def test_variants_do_not_share_a_cost(self):
        self.assertGreater(self.cost('vial', 'CJC-1295 (mit DAC)', '5 mg'), self.cost('vial', 'CJC-1295 (ohne DAC)', '5 mg') * 1.5)
        self.assertGreater(self.cost('dual', 'CJC-1295 (mit DAC)', '10 mg'), self.cost('dual', 'CJC-1295 (ohne DAC)', '10 mg'))
        self.assertGreater(self.cost('vial', 'Lipo-C (526)', '10 ml'), self.cost('vial', 'Lipo-C (216)', '10 ml'))
        self.assertNotEqual(self.cost('dual', 'CJC-1295 (ohne DAC) + Ipamorelin', '10 mg (5 mg + 5 mg)'), self.cost('dual', 'CJC-1295 (ohne DAC)', '10 mg'))

    def test_ting_spellings_are_matched(self):
        for key in (('vial', 'CagriSema (2,5 mg + 2,5 mg)', '5 mg'), ('vial', 'IGF-1 LR3', '0,1 mg'), ('vial', 'Melanotan I (MT-1)', '10 mg'), ('vial', 'CJC-1295 (ohne DAC) + Ipamorelin', '10 mg (5 mg + 5 mg)')):
            self.assertIsNotNone(self.cost(*key), key)

    def test_every_supplier_line_is_in_the_catalogue(self):
        """Jede Ting-Zeile (Vial und Doppelkammer) hat eine Katalogzeile (Zubehoer ausgenommen)."""
        mg = json.loads((PRE / 'merged.json').read_text())
        cat = [(x['form'], x['name'], tc.dose_of(x['strength'])) for x in cl.lines()]
        missing = []
        for form, key in (('vial', 'vials'), ('dual', 'dual')):
            for v in mg[key]:
                if v.get('section') == 'Zubehör':
                    continue
                if form == 'vial' and v.get('ting_usd') is None and v.get('wholesale_eur') is None and v.get('list_eur') is None:
                    continue
                d = tc.dose_of(v['dose'])
                names = {v['name'], se.NAME_FIX.get(v['name'], v['name'])}
                hit = any(f == form and dd == d and (n in names or se.canon(n) in {se.canon(x) for x in names}) for f, n, dd in cat)
                if not hit:
                    hit = any(f == form and dd == d and tc.ALIAS.get((form, n)) in names for f, n, dd in cat)
                if not hit:
                    missing.append((form, v['name'], v['dose']))
        self.assertEqual(missing, [])

    def test_supplement_prices_follow_the_same_rules(self):
        lines = cl.lines()
        sup = [x for x in lines if x.get('supplement')]
        self.assertGreater(len(sup), 90)
        for x in sup:
            self.assertEqual(x['price_cents'] % 1000, 0, x)
            r = self.by[(x['form'], x['name'], x['strength'])]
            c = r['ting'] if r.get('ting') is not None else r.get('other')
            if c:
                self.assertGreaterEqual(x['price_cents'] / 100, 2 * c * 0.999, x)  # mindestens 50 % Marge


if __name__ == '__main__':
    unittest.main()
