import gzip
import hashlib
import hmac
import http.client
import importlib.util
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, 'relaxed'):
        mod.TERMS = mod.relaxed()  # Altfaelle ohne Mindestwert/Versand; echte Konditionen: tests/test_terms.py
    return mod


def signed_init_data(token, user_id=4242):
    data = {'auth_date': str(int(time.time())), 'query_id': 'AAtest', 'user': json.dumps({'id': user_id, 'first_name': 'T'})}
    check = '\n'.join(f'{k}={v}' for k, v in sorted(data.items()))
    secret = hmac.new(b'WebAppData', token.encode(), hashlib.sha256).digest()
    data['hash'] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


class HttpContract(unittest.TestCase):
    TOKEN = '123456:SYNTHETIC-TEST-TOKEN-NOT-REAL-0000000000'

    @classmethod
    def setUpClass(cls):
        cls.srv = load('server')
        cls.tmp = tempfile.TemporaryDirectory(dir=Path.home() / '.hermes/cache/scratch')
        cls.server = cls.srv.ShopServer(('127.0.0.1', 0), cls.srv.Handler)
        port = cls.server.server_address[1]
        cls.port = port
        s = cls.server
        s.mode, s.bot_token, s.db_path = 'telegram', cls.TOKEN, Path(cls.tmp.name) / 't.sqlite3'
        s.products = json.loads((ROOT / 'data/products.json').read_text())
        s.allowed_hosts, s.allowed_origins = {f'127.0.0.1:{port}'}, {f'http://127.0.0.1:{port}'}
        s.bot_name, s.notified = 'ElementsLabsShop_bot', set()
        cls.sent = []
        s.notify = lambda token, uid, text: cls.sent.append((uid, text)) or True
        threading.Thread(target=s.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def req(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        c.request(method, path, body=body, headers={'Host': f'127.0.0.1:{self.port}', **(headers or {})})
        r = c.getresponse()
        data = r.read()
        c.close()
        return r, data

    def test_client_error_report_is_logged_sanitised_and_limited(self):
        import contextlib, io
        buf = io.StringIO()
        body = json.dumps({'m': 'TypeError: x\nINJECT', 'r': '#cart', 's': 'telegram.js', 'l': 12, 'p': 'ios', 'v': '9.1', 'extra': 'ignored'}).encode()
        with contextlib.redirect_stdout(buf):
            r, _ = self.req('POST', '/api/client-error', body, {'Content-Type': 'application/json'})
        self.assertEqual(r.status, 204)
        line = [l for l in buf.getvalue().splitlines() if l.startswith('CLIENT-ERROR')]
        self.assertEqual(len(line), 1)
        self.assertNotIn('INJECT\nCLIENT', buf.getvalue())
        self.assertNotIn('extra', line[0])
        r, _ = self.req('POST', '/api/client-error', b'x' * 5000, {'Content-Type': 'application/json'})
        self.assertEqual(r.status, 413)
        r, _ = self.req('POST', '/api/client-error', b'{bad', {'Content-Type': 'application/json'})
        self.assertEqual(r.status, 400)
        # invalid reports must not consume the quota of valid ones; deep JSON is a 400, not a crash
        for _ in range(40):
            self.req('POST', '/api/client-error', b'', {'Content-Type': 'application/json'})
        r, _ = self.req('POST', '/api/client-error', b'[' * 1000 + b']' * 1000, {'Content-Type': 'application/json'})
        self.assertEqual(r.status, 400)
        r, _ = self.req('POST', '/api/client-error', b'{"m":"a"}', {'Content-Type': 'application/json', 'Origin': 'https://evil.example'})
        self.assertEqual(r.status, 403)
        from concurrent.futures import ThreadPoolExecutor
        self.srv._client_error_window.clear()
        with ThreadPoolExecutor(4) as pool:
            codes = list(pool.map(lambda _: self.req('POST', '/api/client-error', b'{"m":"a"}', {'Content-Type': 'application/json'})[0].status, range(60)))
        self.assertEqual(codes.count(204), 30)
        self.assertEqual(codes.count(429), 30)
        self.srv._client_error_window.clear()

    def test_notification_claim_survives_memory_reset_and_parallel_retries(self):
        from concurrent.futures import ThreadPoolExecutor
        headers = {'Content-Type': 'application/json', 'X-Telegram-Init-Data': signed_init_data(self.TOKEN)}
        request = {'request_id': 'durable-notification-001', 'items': [{'id': 'bpc-157', 'quantity': 1}], 'research_confirmed': True}
        encoded = json.dumps(request).encode()
        before = len(self.sent)
        self.assertEqual(self.req('POST', '/api/orders', encoded, headers)[0].status, 200)
        self.server.notified = set()
        self.assertEqual(self.req('POST', '/api/orders', encoded, headers)[0].status, 200)
        self.assertEqual(len(self.sent), before + 1, 'Notification must not repeat after process-local state is lost')
        request['request_id'] = 'parallel-notification-001'
        encoded = json.dumps(request).encode()
        previous = self.server.notify
        def delayed(token, uid, text):
            time.sleep(.05)
            return previous(token, uid, text)
        self.server.notify = delayed
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                responses = list(pool.map(lambda _: self.req('POST', '/api/orders', encoded, headers)[0].status, range(2)))
            self.assertEqual(responses, [200, 200])
            self.assertEqual(len(self.sent), before + 2)
        finally:
            self.server.notify = previous

    def test_inline_scripts_are_hash_bound_not_unrestricted(self):
        response, _ = self.req('GET', '/')
        policy = response.getheader('Content-Security-Policy')
        script = policy.split('script-src ', 1)[1].split(';', 1)[0]
        self.assertNotIn("'unsafe-inline'", script)
        self.assertIn("'sha256-", script)

    def test_mixed_formats_keep_identity_and_price_controls(self):
        previous = self.server.products
        self.server.products = self.srv.load_products()
        try:
            body = {'request_id': 'http-mixed-quote-001', 'items': [{'id': 'retatrutide-10', 'quantity': 1}, {'id': 'dual-tirzepatide-10', 'quantity': 1}, {'id': 'mehrweg-pen', 'quantity': 1}], 'research_confirmed': True}
            headers = {'Content-Type': 'application/json', 'X-Telegram-Init-Data': signed_init_data(self.TOKEN)}
            response, data = self.req('POST', '/api/orders', json.dumps(body).encode(), headers)
            result = json.loads(data)
            self.assertEqual(response.status, 200)
            by = {p['id']: p['price_cents'] for p in self.server.products}
            expected = by['retatrutide-10'] + by['dual-tirzepatide-10'] + by['mehrweg-pen']
            self.assertEqual(result['total_cents'], expected)
            self.assertEqual(result['known_total_cents'], expected)
            foreign = {**headers, 'X-Telegram-Init-Data': signed_init_data(self.TOKEN, user_id=99999)}
            self.assertEqual(self.req('POST', '/api/orders', json.dumps(body).encode(), foreign)[0].status, 400)
            body['request_id'] = 'http-price-override-001'
            body['items'][1]['price_cents'] = 1
            self.assertEqual(self.req('POST', '/api/orders', json.dumps(body).encode(), headers)[0].status, 400)
        finally:
            self.server.products = previous

    def test_slow_body_connection_times_out_without_hanging_server(self):
        import socket
        previous = self.srv.Handler.timeout
        self.srv.Handler.timeout = .1
        try:
            with socket.create_connection(('127.0.0.1', self.port), timeout=2) as connection:
                headers = f'POST /api/orders HTTP/1.0\r\nHost: 127.0.0.1:{self.port}\r\nContent-Type: application/json\r\nContent-Length: 100\r\n\r\n'
                connection.sendall(headers.encode() + b'{')
                response = connection.recv(4096)
                self.assertIn(b'503', response.split(b'\r\n', 1)[0])
            self.assertEqual(self.req('GET', '/health')[0].status, 200)
        finally:
            self.srv.Handler.timeout = previous

    def test_static_gzip_etag_head_and_cache_policy(self):
        r, data = self.req('GET', '/app.js', headers={'Accept-Encoding': 'gzip'})
        self.assertEqual(r.getheader('Content-Encoding'), 'gzip')
        self.assertIn(b'function', gzip.decompress(data))
        etag = r.getheader('ETag')
        self.assertEqual(self.req('GET', '/app.js', headers={'If-None-Match': etag})[0].status, 304)
        h, body = self.req('HEAD', '/app.js')
        self.assertEqual((h.status, body), (200, b''))
        self.assertEqual(self.req('GET', '/app.js')[0].getheader('Cache-Control'), 'no-cache')
        asset = next((ROOT / 'public/assets/products').glob('*.webp')).name
        self.assertIn('max-age', self.req('GET', '/assets/products/' + asset)[0].getheader('Cache-Control'))

    def test_private_paths_and_malformed_input_never_crash(self):
        for path in ['/data/products.json', '/evidence/build.json', '/runtime/test-requests.sqlite3', '/../server.py', '/%00', '/index.html%00.png']:
            self.assertEqual(self.req('GET', path)[0].status, 404, path)
        hdr = {'Content-Type': 'application/json'}
        self.assertEqual(self.req('POST', '/api/orders', b'[' * 10000, hdr)[0].status, 400)
        self.assertEqual(self.req('POST', '/api/orders', b'{}', {'Content-Type': 'text/plain'})[0].status, 415)
        self.assertEqual(self.req('GET', '/health')[0].status, 200)

    def test_config_exposes_bot_name_and_signed_order_notifies_once(self):
        _, data = self.req('GET', '/api/config')
        self.assertEqual(json.loads(data)['bot'], 'ElementsLabsShop_bot')
        body = json.dumps({'request_id': 'notify-test-0001', 'items': [{'id': 'bpc-157', 'quantity': 2}], 'research_confirmed': True}).encode()
        hdr = {'Content-Type': 'application/json', 'X-Telegram-Init-Data': signed_init_data(self.TOKEN)}
        r, data = self.req('POST', '/api/orders', body, hdr)
        result = json.loads(data)
        self.assertEqual((r.status, result['status'], result['notified']), (200, 'LOCAL_TEST_SAVED', True))
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0][0], 4242)
        self.assertIn('nicht an einen Händler gesendet', self.sent[0][1])
        self.assertIn(result['id'], self.sent[0][1])
        again = json.loads(self.req('POST', '/api/orders', body, hdr)[1])
        self.assertEqual((again['id'], again.get('notified')), (result['id'], None))
        self.assertEqual(len(self.sent), 1)
        # unsigned request in telegram mode is rejected and sends nothing
        self.assertEqual(self.req('POST', '/api/orders', body, {'Content-Type': 'application/json'})[0].status, 400)
        self.assertEqual(len(self.sent), 1)


class BotContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bot = load('bot')

    def test_replies_and_deep_links(self):
        r = self.bot.reply_for
        self.assertEqual(r('/start')[1], '/')
        self.assertEqual(r('/start p_bpc-157')[1], '/#product=bpc-157')
        self.assertEqual(r('/start p_retatrutide-10')[1], '/#product=retatrutide-10')
        self.assertEqual(r('/start katalog')[1], '/#info')
        self.assertEqual(r('/shop@ElementsLabsShop_bot')[1], '/')
        self.assertEqual(r('/vials')[1], '/#products/vial')
        self.assertEqual(r('/packs')[1], '/#packs')
        self.assertEqual(r('/preisliste')[0], self.bot.PRICELIST_MARK)
        self.assertIsNone(r('/hilfe')[1])
        self.assertIn('Testversion', r('/start')[0])
        self.assertIsNone(r('hallo')[1])

    def test_format_entry_points_and_menu(self):
        reply = self.bot.reply_for
        self.assertEqual(reply('/doppelkammer')[1], '/#dual-chamber')
        self.assertEqual(reply('/pen')[1], '/#accessories')
        self.assertEqual(reply('/warenkorb')[1], '/#cart')
        self.assertEqual(reply('/start p_dual-retatrutide-10')[1], '/#product=dual-retatrutide-10')
        calls = []
        self.bot.call = lambda token, method, payload=None, timeout=40: calls.append((method, payload))
        self.bot.handle('t', {'chat': {'id': 1, 'type': 'private'}, 'text': '/start'}, 'https://x.trycloudflare.com')
        links = calls[0][1]['reply_markup']['inline_keyboard']
        self.assertEqual(sum(len(row) for row in links), 6)
        self.assertEqual(links[0][0]['text'], '🛒  SHOP ÖFFNEN')  # Shop steht allein und zuerst
        self.assertEqual(links[0][0]['web_app']['url'], 'https://x.trycloudflare.com/')
        self.assertIn('/?r=dual-chamber', str(links))
        self.assertIn('/?r=packs', str(links))
        self.assertIn('pricelist', str(links))

    def test_only_private_chats_get_replies(self):
        calls = []
        self.bot.call = lambda token, method, payload=None, timeout=40: calls.append((method, payload))
        self.bot.handle('t', {'chat': {'id': 1, 'type': 'group'}, 'text': '/start'}, 'https://x.trycloudflare.com')
        self.assertEqual(calls, [])
        self.bot.handle('t', {'chat': {'id': 1, 'type': 'private'}, 'text': '/shop'}, 'https://x.trycloudflare.com')
        self.assertEqual(calls[0][1]['reply_markup']['inline_keyboard'][0][0]['web_app']['url'], 'https://x.trycloudflare.com/')

    def test_pricelist_command_and_button_send_the_pdf_only_in_private_chats(self):
        sent = []
        self.bot.send_pricelist = lambda token, chat_id: sent.append(chat_id)
        self.bot.call = lambda *a, **k: {'ok': True, 'result': {}}
        self.bot.handle('t', {'chat': {'id': 7, 'type': 'private'}, 'text': '/preisliste'}, 'https://x.trycloudflare.com')
        self.bot.handle('t', {'chat': {'id': 8, 'type': 'group'}, 'text': '/preisliste'}, 'https://x.trycloudflare.com')
        self.bot.handle_callback('t', {'id': 'q1', 'data': 'pricelist', 'message': {'chat': {'id': 9, 'type': 'private'}}})
        self.bot.handle_callback('t', {'id': 'q2', 'data': 'pricelist', 'message': {'chat': {'id': 10, 'type': 'supergroup'}}})
        self.bot.handle_callback('t', {'id': 'q3', 'data': 'other', 'message': {'chat': {'id': 11, 'type': 'private'}}})
        self.assertEqual(sent, [7, 9])

    def test_failed_pricelist_upload_does_not_block_polling(self):
        def blocked(token, chat_id):
            raise self.bot.BotAPIError(403)
        self.bot.send_pricelist = blocked
        self.bot.handle('t', {'chat': {'id': 7, 'type': 'private'}, 'text': '/preisliste'}, 'https://x.trycloudflare.com')  # 403: Update gilt als erledigt
        self.bot.handle_callback('t', {'id': 'q', 'data': 'pricelist', 'message': {'chat': {'id': 7, 'type': 'private'}}})
        def broken(token, chat_id):
            raise self.bot.BotAPIError(500)
        self.bot.send_pricelist = broken
        with self.assertRaises(self.bot.BotAPIError):
            self.bot.handle('t', {'chat': {'id': 7, 'type': 'private'}, 'text': '/preisliste'}, 'https://x.trycloudflare.com')

    def test_pricelist_pdf_exists_and_has_no_internal_data(self):
        data = self.bot.PRICELIST.read_bytes()
        self.assertTrue(data.startswith(b'%PDF'))
        body, ctype = self.bot.multipart({'chat_id': 1}, 'document', 'x.pdf', b'DATA')
        self.assertIn(b'filename="x.pdf"', body)
        self.assertIn('boundary=', ctype)
        from terms import load_terms, text_vars
        line = self.bot.terms_line()
        v = text_vars(load_terms())
        self.assertTrue(line.startswith(f"Mindestbestellwert {v['min']} · Versand inklusive"))  # Zahlen aus data/terms.json, nicht fest
        self.assertIn(v['tiers'], line)
        self.assertNotIn('Gratisversand', line)


if __name__ == '__main__':
    unittest.main()
