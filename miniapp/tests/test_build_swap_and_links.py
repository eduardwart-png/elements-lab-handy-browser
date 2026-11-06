import json, sys, tempfile, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build, bot


class SwapRollback(unittest.TestCase):
    def test_failed_swap_restores_public(self):
        with tempfile.TemporaryDirectory() as tmp:
            pub = Path(tmp) / 'public'; pub.mkdir(); (pub / 'index.html').write_text('old')
            original_rename = Path.rename
            calls = {'n': 0}
            def flaky(self, target):
                calls['n'] += 1
                if self.name == 'public.next':
                    raise PermissionError('injected')
                return original_rename(self, target)
            def fake_build():
                (build.PUBLIC / 'index.html').parent.mkdir(parents=True, exist_ok=True)
                (build.PUBLIC / 'index.html').write_text('new')
            with mock.patch.object(build, 'PUBLIC', pub), mock.patch.object(build, '_build', fake_build), mock.patch.object(Path, 'rename', flaky):
                with self.assertRaises(PermissionError):
                    build.build()
            self.assertEqual((pub / 'index.html').read_text(), 'old')
            self.assertFalse((Path(tmp) / 'public.next').exists())


class LegacyLinks(unittest.TestCase):
    def test_fragment_buttons_migrate_on_same_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'runtime').mkdir()
            (root / 'runtime/bot-links.json').write_text(json.dumps([{'chat_id': 1, 'message_id': 2, 'path': '/#dual-chamber', 'last_origin': 'https://x.test'}]))
            sent = []
            with mock.patch.object(bot, 'ROOT', root), mock.patch.object(bot, 'call', lambda t, m, p: sent.append((m, p))):
                self.assertTrue(bot.refresh_links('t', 'https://x.test'))
            self.assertEqual(len(sent), 1)
            self.assertIn('/?r=dual-chamber', json.dumps(sent[0][1]))


if __name__ == '__main__':
    unittest.main()
