"""Schutz gegen veraltete feste Zahlen und Konditionsaussagen in Kundentexten (Bot, Frontend-Texte, PDF-Skript).
Neu in tests/. Zahlen gehoeren nach data/terms.json (Konditionen) bzw. werden zur Laufzeit aus den Katalogdaten gezaehlt (siehe team/marketing2/datenabhaengige_texte.md)."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import terms  # noqa: E402

FILES = ['extensions/terms.js', 'extensions/shop-formats.js', 'extensions/i18n-extra.js', 'extensions/telegram.js', 'extensions/zoom.js', 'bot.py', 'server.py', '../preislisten/make_pricelist.py']
STALE = [r'Gratisversand', r'Free shipping', r'Livraison gratuite', r'Versandpauschale', r'Versand \(pauschal\)', r'shipping_cents\s*:\s*[1-9]', r'free_shipping', r'to_free',
         r'\b230\b', r'25 Vial', r'25 Doppel', r'25 Stoffmengen', r'Referenzwebsite', r'reference website', r'Fortschrittsbalken', r'10er-Packung', r'Gleiche Preise', r'24/7']


class NoStaleClaims(unittest.TestCase):
    def test_no_stale_phrases_in_customer_text_sources(self):
        found = []
        for name in FILES:
            path = ROOT / name
            if not path.is_file():
                continue
            for number, line in enumerate(path.read_text().splitlines(), 1):
                for rx in STALE:
                    if re.search(rx, line):
                        found.append(f'{name}:{number}: {rx}')
        self.assertEqual(found, [])

    def test_bot_texts_follow_terms_json(self):
        import bot
        v = terms.text_vars(terms.load_terms())
        self.assertIn(f"Mindestbestellwert {v['min']}", bot.terms_line())
        self.assertIn(v['tiers'], bot.terms_line())
        self.assertIn(v['cmin'], bot.terms_line())
        self.assertNotIn('Gratis', bot.terms_line())
        self.assertLessEqual(len(bot.DESCRIPTION), 512)
        self.assertLessEqual(len(bot.SHORT_DESCRIPTION), 120)
        self.assertTrue(all(3 <= len(c['description']) <= 256 for c in bot.COMMANDS))
        for text in (bot.reply_for('/start')[0], bot.reply_for('/packs')[0], bot.reply_for('/hilfe')[0]):
            self.assertNotRegex(text, r'\b(230|25)\b')

    def test_terms_file_has_the_agreed_shape(self):
        t = terms.load_terms()
        self.assertEqual(sorted(t), ['collective_min_cents', 'currency', 'delivery_weeks', 'min_order_cents', 'tiers'])
        self.assertLess(t['collective_min_cents'], t['min_order_cents'])
        self.assertEqual(sorted(x['min_cents'] for x in t['tiers']), [x['min_cents'] for x in t['tiers']])
        self.assertTrue(all(x['min_cents'] >= t['min_order_cents'] for x in t['tiers']))


if __name__ == '__main__':
    unittest.main()
