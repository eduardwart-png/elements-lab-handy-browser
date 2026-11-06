"""Regeltest: veraltete Listen werden erkannt und in den Papierkorb gelegt, aktuelle/Quell-/fremde Dateien bleiben (Eddy 25.10.2026)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import listen_aufraeumen as la  # noqa: E402


class ListenAufraeumen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        h = Path(self.tmp.name)
        (h / 'Desktop/Elements_Lab/3 FÜR EDDY (intern)').mkdir(parents=True)
        (h / 'Desktop/Elements_Lab/1 FÜR TING').mkdir(parents=True)
        (h / 'Downloads').mkdir()
        (h / 'staging_out/3 FÜR EDDY (intern)').mkdir(parents=True)
        self.h = h
        self.saved = {k: getattr(la, k) for k in ('HOME', 'DESK', 'ROOTS', 'STAGING_OUT', 'LOG', 'SKIP_PARTS')}
        la.HOME, la.DESK = h, h / 'Desktop/Elements_Lab'
        la.ROOTS, la.STAGING_OUT = [h / 'Desktop', h / 'Downloads'], h / 'staging_out'
        la.LOG, la.SKIP_PARTS = h / 'log.jsonl', ('Obsidian', '.git')
        (h / 'Desktop/Elements_Lab/3 FÜR EDDY (intern)/Preisliste für Kunden (Tabelle).csv').write_text('neu')
        (h / 'staging_out/3 FÜR EDDY (intern)/Preisliste für Kunden (Tabelle).csv').write_text('neu')

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(la, k, v)
        self.tmp.cleanup()

    def test_stale_copy_goes_to_trash_and_everything_else_stays(self):
        d = self.h / 'Downloads'
        (d / 'Elements-Labs-Preisliste.pdf').write_text('alt')                       # veraltete Liste (anderer Inhalt)
        (d / 'Elements Labs Preisliste (Kunden) (1).pdf').write_text('alt2')          # Telegram-Duplikat
        (d / 'Preisliste für Kunden (Tabelle).csv').write_text('neu')                # identisch mit aktuellem Stand -> bleibt
        (d / 'ELEMENTS_LABS_VERKAUFSBLATT.pdf').write_text('quelle')                 # Lieferanten-Quelle -> nie anfassen
        (d / 'VERBUNDWERK_DATENGRUNDLAGE.xlsx').write_text('anderes Projekt')        # fremd -> nie anfassen
        stale, fremd, abw = la.analyse()
        self.assertEqual(sorted(p.name for p in stale), ['Elements Labs Preisliste (Kunden) (1).pdf', 'Elements-Labs-Preisliste.pdf'])
        self.assertEqual(abw, [])
        self.assertEqual(la.main(['--pruefen', '--json']), 1)
        self.assertEqual(la.main(['--aufraeumen', '--json']), 0)
        self.assertEqual(sorted(p.name for p in d.iterdir()), ['ELEMENTS_LABS_VERKAUFSBLATT.pdf', 'Preisliste für Kunden (Tabelle).csv', 'VERBUNDWERK_DATENGRUNDLAGE.xlsx'])
        self.assertTrue((self.h / '.Trash/Elements-Labs-Preisliste.pdf').exists())     # wiederherstellbar
        self.assertEqual(len(la.LOG.read_text().splitlines()), 2)

    def test_desktop_deviation_and_unknown_list_in_canonical_folder_are_reported(self):
        (self.h / 'Desktop/Elements_Lab/3 FÜR EDDY (intern)/Preisliste für Kunden (Tabelle).csv').write_text('veraltet')
        (self.h / 'Desktop/Elements_Lab/3 FÜR EDDY (intern)/Top-20 Bestseller alt.pdf').write_text('x')
        stale, fremd, abw = la.analyse()
        self.assertEqual([p.name for p in fremd], ['Top-20 Bestseller alt.pdf'])
        self.assertTrue(any('weicht vom frischen Listenlauf ab' in a for a in abw))
        self.assertEqual(la.main(['--pruefen']), 1)

    def test_partner_lists_and_their_copies_are_never_stale(self):
        part = self.h / 'Desktop/Elements_Lab/4 FÜR KOOPERATIONSPARTNER'
        part.mkdir()
        (part / 'Elements Labs Preisliste Partner – Vials.pdf').write_text('partner')
        d = self.h / 'Downloads'
        (d / 'Elements Labs Preisliste Partner – Vials.pdf').write_text('partner')        # Kopie (z. B. vom Versand) -> bleibt
        (d / 'Elements Labs Preisliste Partner – Alt.pdf').write_text('alter Stand')      # veraltete Partner-Liste -> weg
        stale, fremd, abw = la.analyse()
        self.assertEqual([p.name for p in stale], ['Elements Labs Preisliste Partner – Alt.pdf'])
        self.assertEqual(fremd, [])
        self.assertTrue((part / 'Elements Labs Preisliste Partner – Vials.pdf').exists())


if __name__ == '__main__':
    unittest.main()
