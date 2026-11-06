"""Abgabe-Fixes (QA-Befunde 25.10.2026) am gebauten Stand public/: Texte, Vertrauenszeile, Suche, Bildvergroesserung.
Laeuft nach `staging.sh build` (wie test_build.py liest der Test die Build-Ausgabe)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / 'public'


def read(name):
    return (PUB / name).read_text()


class DeadAndStaleTexts(unittest.TestCase):
    def test_no_dead_texts_in_shipped_i18n(self):
        # Die Recherche-Hub-Absaetze (hub.c4b) enthalten eine eigene Altformulierung; sie liegen ausserhalb dieses Auftrags.
        i18n = re.sub(r"^\s*'hub\.c4b':.*$", '', read('i18n.js'), flags=re.M)
        for phrase in ('Gleiche Preise wie im Vial-Sortiment', 'Same prices as the vial range', 'Mêmes prix que la gamme en flacons',
                       'Pen nicht im Lieferumfang', 'Nicht im Lieferumfang', '24/7 Kundendienst', '24/7 customer service', 'Service client 24/7', 'Qualitätskontrolle', 'PRE-LAUNCH STATUS', 'STATUT PRÉ-LANCEMENT', "'legal.preLaunch"):
            self.assertFalse(phrase in i18n, phrase)

    def test_dual_range_key_is_the_short_true_text(self):
        i18n = read('i18n.js')
        values = re.findall(r'"focus\.dualRange": "([^"]*)"', i18n) + re.findall(r"'focus\.dualRange': '([^']*)'", i18n)
        self.assertEqual(set(values), {'Dual chamber, pen included', 'Doppelkammer inklusive Pen', 'Double chambre, stylo inclus'})
        self.assertIn('Doppelkammer inklusive Pen', values)

    def test_legal_pages_have_no_prelaunch_banner(self):
        app, i18n = read('app.js'), read('i18n.js')
        self.assertNotIn('legal.preLaunch', app + i18n)
        legal = app[app.index('function legal(kind)'):]
        legal = legal[:legal.index('\n')]
        self.assertNotIn('FFF3CD', legal)
        self.assertIn("t('legal.operator')", legal)  # Rest der Seite bleibt
        self.assertIn("t('legal.rou')", legal)
        for text in re.findall(r"'legal\.imprintText':'([^']*)'", i18n):
            self.assertIsNone(re.search(r'PRE_LAUNCH|Interim|intermédiaire', text), text)

    def test_french_quantity_label_and_pen_nav(self):
        i18n, shop = read('i18n.js'), read('shop-formats.js')
        self.assertIn("'detail.chooseSize':'Choisir la quantité'", i18n)
        self.assertNotIn("'detail.chooseSize':'Choisir le format'", i18n)
        self.assertIn("'shop.navPen': lang==='fr'?'Stylo':'Pen'", shop)

    def test_age_dialog_uses_du(self):
        html, i18n = read('index.html'), read('i18n.js')
        self.assertIn('Bevor du fortfährst', html)
        self.assertIn('Bist du 18 Jahre oder älter?', html)
        self.assertNotIn('Bevor Sie fortfahren', html + i18n)
        self.assertNotIn('Sind Sie 18', html + i18n)
        self.assertIn("'age.title':'Bevor du fortfährst'", i18n)
        self.assertIn("'Before you continue'", i18n)  # EN/FR unveraendert
        self.assertIn("'Avant de continuer'", i18n)


class ProductPage(unittest.TestCase):
    def test_dual_pages_render_the_same_trust_row_as_vials(self):
        app = read('app.js')
        self.assertIn("${window.ELShop.penIncluded()}${trustBadges}`:trustBadges}", app)
        self.assertEqual(app.count('${trustBadges}'), 1)

    def test_search_with_dose_links_the_matching_variant(self):
        app = read('app.js')
        self.assertIn('pick:q?window.ELShop.pickVariant(g.variants,q):\'\'', app)
        self.assertEqual(app.count('href="#product=${target}"'), 2)
        self.assertIn('target=g.pick||lead.id', app)

    def test_zoom_is_shipped_and_labelled_in_three_languages(self):
        html, i18n = read('index.html'), read('i18n.js')
        self.assertIn('<script src="zoom.js"></script>', html)
        self.assertLess(html.index('telegram.js'), html.index('zoom.js'))
        self.assertTrue((PUB / 'zoom.js').is_file())
        for lang in ('de', 'en', 'fr'):
            m = re.search(r"Object\.assign\(window\.__EL_I18N__\.%s, \{'zoom\.open': '([^']+)', 'zoom\.dialog': '([^']+)', 'zoom\.close': '([^']+)', 'zoom\.hintIn': '([^']+)', 'zoom\.hintOut': '([^']+)'\}\)" % lang, i18n)
            self.assertTrue(m, lang)
            self.assertEqual(len(set(m.groups())), 5, lang)

    def test_price_stays_right_aligned_next_to_badge(self):
        css = read('miniapp.css')
        self.assertRegex(css, r'\.variant-opt \.vo-price\{order:3;margin-left:auto;text-align:right\}')
        self.assertRegex(css, r'\.variant-opt \.vo-badge\{order:2;')


if __name__ == '__main__':
    unittest.main()
