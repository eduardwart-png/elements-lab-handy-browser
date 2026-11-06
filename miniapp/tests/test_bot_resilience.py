import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('resilient_bot', ROOT / 'bot.py')
assert spec is not None and spec.loader is not None
bot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot)

class BotResilienceContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path.home() / '.hermes/cache/scratch')
        self.root = Path(self.tmp.name)
        (self.root / 'runtime').mkdir()
        self.root_patch = patch.object(bot, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_blocked_recipient_does_not_stop_polling_or_poison_offset(self):
        polls = 0
        def call(_token, method, payload=None, timeout=40):
            nonlocal polls
            if method == 'getUpdates':
                polls += 1
                if polls > 1:
                    raise KeyboardInterrupt
                return {'ok': True, 'result': [{'update_id': 100, 'message': {'chat': {'id': 123, 'type': 'private'}, 'text': '/start'}}]}
            if method == 'sendMessage':
                raise bot.BotAPIError(403)
            return {'ok': True, 'result': True}
        with patch.object(bot, 'call', call), patch.dict(os.environ, {'ELEMENTS_TELEGRAM_BOT_TOKEN': 'SYNTHETIC'}):
            self.assertEqual(bot.main(), 0)
        self.assertEqual((self.root / 'runtime/bot-offset.txt').read_text(), '101')

    def test_corrupt_link_cache_is_deferred_not_a_crash(self):
        (self.root / 'runtime/bot-links.json').write_text('broken json')
        self.assertIs(bot.refresh_links('SYNTHETIC', 'https://x.trycloudflare.com'), False)

    def test_structurally_corrupt_link_cache_does_not_break_remember(self):
        for value in [[None], {'broken': True}, 'unexpected', [1, 'bad', {}]]:
            with self.subTest(value=value):
                path = self.root / 'runtime/bot-links.json'
                path.write_text(json.dumps(value))
                bot.remember_link(123, 42, '/')
                records = json.loads(path.read_text())
                self.assertIsInstance(records, list)
                self.assertEqual(records[-1]['message_id'], 42)

    def test_link_flood_control_is_deferred_without_restart(self):
        (self.root / 'runtime/bot-links.json').write_text(json.dumps([{'chat_id': 123, 'message_id': 1, 'path': '/'}]))
        def limited(*_args, **_kwargs): raise bot.BotAPIError(429)
        with patch.object(bot, 'call', limited):
            self.assertIs(bot.refresh_links('SYNTHETIC', 'https://x.trycloudflare.com'), False)

if __name__ == '__main__': unittest.main()
