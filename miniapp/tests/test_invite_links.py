"""tools/invite_links.py (nur Hauptpaket): benannte Einladungslinks je Quelle und Zaehler. Telegram-API gestubbt, Token nie in der Ausgabe."""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools/invite_links.py'
sys.path.insert(0, str(ROOT))
GROUP = -1009876543210


@unittest.skipUnless(TOOL.is_file() and (ROOT / 'support.py').is_file(), 'Werkzeug nur im Hauptpaket')
class InviteLinks(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('invite_links', TOOL)
        self.tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.tool)
        self.tmp = tempfile.TemporaryDirectory(dir=Path.home() / '.hermes/cache/scratch')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'runtime').mkdir()
        self.calls = []

        def call(token, method, payload=None, timeout=40):
            self.calls.append((token, method, payload))
            return {'ok': True, 'result': {'invite_link': 'https://t.me/+AbC' + str(len(self.calls)), 'name': payload['name'],
                                           'creates_join_request': payload.get('creates_join_request', False), 'pending_join_request_count': 0}}
        for p in (patch.object(self.tool, 'ROOT', self.root), patch.object(self.tool.support, 'ROOT', self.root), patch.object(self.tool, 'call', call),
                  patch.dict(os.environ, {'ELEMENTS_TELEGRAM_BOT_TOKEN': 'SECRET-TOKEN-123', 'ELEMENTS_GROUP_CHAT_ID': str(GROUP)})):
            p.start()
            self.addCleanup(p.stop)

    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = self.tool.main(list(args))
        return code, out.getvalue()

    def test_create_named_links_and_list_counts_without_token(self):
        code, out = self.run_cli('create', 'kanal-pin', '--join-request')
        self.assertEqual(code, 0)
        code, out2 = self.run_cli('create', 'instagram')
        self.assertEqual([(m, p) for _, m, p in self.calls], [
            ('createChatInviteLink', {'chat_id': GROUP, 'name': 'kanal-pin', 'creates_join_request': True}),
            ('createChatInviteLink', {'chat_id': GROUP, 'name': 'instagram'})])
        self.assertIn('https://t.me/+AbC1', out)
        self.tool.support.count_invite('kanal-pin', 'requests')
        self.tool.support.count_invite('kanal-pin', 'requests')
        self.tool.support.count_invite('instagram', 'joins')
        code, listing = self.run_cli('list')
        self.assertEqual(code, 0)
        rows = {line.split()[0]: line for line in listing.splitlines() if line.startswith(('kanal-pin', 'instagram'))}
        self.assertRegex(rows['kanal-pin'], r'Anfragen 2 .*Beitritte 0')
        self.assertRegex(rows['instagram'], r'Anfragen 0 .*Beitritte 1')
        stored = json.loads((self.root / 'runtime/invite-links.json').read_text())
        self.assertEqual([s['name'] for s in stored], ['kanal-pin', 'instagram'])
        for text in (out, out2, listing, json.dumps(stored)):
            self.assertNotIn('SECRET-TOKEN-123', text)

    def test_bad_names_missing_group_and_api_errors_fail_cleanly(self):
        code, out = self.run_cli('create', 'x' * 33)
        self.assertNotEqual(code, 0)
        code, out = self.run_cli('create', 'bad name!')
        self.assertNotEqual(code, 0)
        self.assertEqual(self.calls, [])
        with patch.dict(os.environ, {'ELEMENTS_GROUP_CHAT_ID': ''}):
            code, out = self.run_cli('create', 'ok')
        self.assertNotEqual(code, 0)

        def boom(token, method, payload=None, timeout=40):
            raise self.tool.BotAPIError(400)
        with patch.object(self.tool, 'call', boom):
            code, out = self.run_cli('create', 'ok')
        self.assertNotEqual(code, 0)
        self.assertNotIn('SECRET-TOKEN-123', out)
        with patch.dict(os.environ, {'ELEMENTS_TELEGRAM_BOT_TOKEN': ''}):
            code, out = self.run_cli('create', 'ok')
        self.assertNotEqual(code, 0)


if __name__ == '__main__':
    unittest.main()
