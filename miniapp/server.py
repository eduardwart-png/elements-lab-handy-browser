"""Isolated research-shop TEST server: local inbox only, never sends orders.
Python standard library; no payments, no third-party order processing.
"""
import argparse
import base64
import gzip
import threading
import urllib.request
import hashlib
import hmac
import json
import mimetypes
import os
import re
import sqlite3
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast
from urllib.parse import parse_qsl, unquote, urlsplit

ROOT = Path(__file__).resolve().parent
import sys  # noqa: E402

sys.path.insert(0, str(ROOT))
from terms import MinOrderError, calc as calc_terms, load_terms, relaxed  # noqa: E402

TERMS = load_terms()


class RateLimitError(ValueError):
    pass


def validate_init_data(raw, bot_token, max_age=3600):
    if not raw or not bot_token or len(raw) > 16384:
        raise ValueError('Telegram authentication required')
    try:
        pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True)
        if len({k for k, _ in pairs}) != len(pairs):
            raise ValueError('Duplicate authentication field')
        data = dict(pairs)
        received_hash = data.pop('hash', '')
        if not re.fullmatch(r'[a-fA-F0-9]{64}', received_hash):
            raise ValueError('Invalid authentication hash')
        # Official bot-token verification: include every field except hash.
        check = '\n'.join(f'{k}={v}' for k, v in sorted(data.items()))
        secret = hmac.new(b'WebAppData', bot_token.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, received_hash.lower()):
            raise ValueError('Invalid Telegram signature')
        age = time.time() - int(data['auth_date'])
        if age < -30 or age > max_age:
            raise ValueError('Expired Telegram authentication')
        user = json.loads(data['user'])
        if not isinstance(user, dict) or type(user.get('id')) is not int or user['id'] <= 0:
            raise ValueError('Invalid Telegram identity')
        return {'id': user['id']}
    except (KeyError, TypeError, json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError('Invalid Telegram authentication data') from exc


def save_request(body, products, db_path, mode, init_data='', bot_token='', terms=None):
    if mode not in {'preview', 'telegram'}:
        raise ValueError('Invalid server mode')
    identity = validate_init_data(init_data, bot_token) if mode == 'telegram' else None
    base_keys = {'request_id', 'items', 'research_confirmed'}
    if not isinstance(body, dict) or set(body) not in (base_keys, base_keys | {'collective'}):
        raise ValueError('Invalid request structure')
    if 'collective' in body and type(body['collective']) is not bool:
        raise ValueError('Invalid collective flag')
    terms = terms or TERMS
    key = body['request_id']
    if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,80}', key):
        raise ValueError('Invalid request id')
    if body['research_confirmed'] is not True:
        raise ValueError('Research confirmation required')
    raw_items = body['items']
    if not isinstance(raw_items, list) or not 1 <= len(raw_items) <= min(100, len(products)):
        raise ValueError('Invalid cart')
    by_id = {p['id']: p for p in products}
    items, seen = [], set()
    for item in raw_items:
        if not isinstance(item, dict) or set(item) != {'id', 'quantity'}:
            raise ValueError('Invalid cart item')
        pid, qty = item['id'], item['quantity']
        if not isinstance(pid, str) or pid not in by_id or pid in seen:
            raise ValueError('Unknown or duplicate product')
        if type(qty) is not int or not 1 <= qty <= 99:
            raise ValueError('Invalid quantity')
        p = by_id[pid]
        cents = p['price_cents']
        if not (type(cents) is int and cents > 0) and not (cents is None and p.get('price_status') == 'ON_REQUEST'):
            raise ValueError('Invalid configured price')
        seen.add(pid)
        items.append({'id': pid, 'name': p['name'], 'strength': p['concentration'], 'format': p.get('format', 'vial'), 'quantity': qty, 'unit_price_cents': cents, 'discount_ok': bool(p.get('discount_ok'))})
    quote_items = sum(x['unit_price_cents'] is None for x in items)
    known_total = sum(x['quantity'] * x['unit_price_cents'] for x in items if x['unit_price_cents'] is not None)
    quote = calc_terms([(i['quantity'], i['unit_price_cents'], i['discount_ok']) for i in items], terms, body.get('collective', False))
    if not quote['min_ok']:
        raise MinOrderError(quote['min_order_cents'], quote['subtotal_cents'])
    payload = {'items': items, 'total_cents': quote['payable_cents'], 'known_total_cents': known_total, 'quote_items': quote_items, 'currency': 'EUR', 'telegram_user_id': identity['id'] if identity else None, 'mode': mode, 'external_delivery': False,
               'subtotal_cents': quote['subtotal_cents'], 'discount_percent': quote['discount_percent'], 'discount_cents': quote['discount_cents'], 'shipping_cents': quote['shipping_cents'], 'collective': quote['collective']}
    intent = {'items': sorted((i['id'], i['quantity']) for i in items), 'telegram_user_id': payload['telegram_user_id'], 'mode': mode, 'collective': quote['collective']}
    fingerprint = hashlib.sha256(json.dumps(intent, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    fd = os.open(db_path, os.O_CREAT | os.O_RDWR, 0o600)
    os.close(fd)
    os.chmod(db_path, 0o600)
    # Fresh connection + write lock makes concurrent retries idempotent.
    with sqlite3.connect(db_path, timeout=10) as db:
        db.execute('CREATE TABLE IF NOT EXISTS requests (request_key TEXT PRIMARY KEY, id TEXT UNIQUE NOT NULL, fingerprint TEXT NOT NULL, payload TEXT NOT NULL, created_at INTEGER NOT NULL)')
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT id, fingerprint, payload FROM requests WHERE request_key=?', (key,)).fetchone()
        if row:
            stored = json.loads(row[2])
            stored_intent = {'items': sorted((i['id'], i['quantity']) for i in stored['items']), 'telegram_user_id': stored.get('telegram_user_id'), 'mode': stored.get('mode'), 'collective': bool(stored.get('collective', False))}
            if stored_intent != intent:
                raise ValueError('Request id already used with different contents')
            request_id = row[0]
            payload = stored
            quote_items = stored.get('quote_items', sum(i['unit_price_cents'] is None for i in stored['items']))
            known_total = stored.get('known_total_cents', sum(i['quantity'] * i['unit_price_cents'] for i in stored['items'] if i['unit_price_cents'] is not None))
        else:
            if identity:
                recent = db.execute("SELECT count(*) FROM requests WHERE created_at>=? AND json_extract(payload, '$.telegram_user_id')=?", (int(time.time()) - 60, identity['id'])).fetchone()[0]
                daily = db.execute('SELECT count(*) FROM requests WHERE created_at>=?', (int(time.time()) - 86400,)).fetchone()[0]
                if recent >= 10 or daily >= 5000:
                    raise RateLimitError('Too many requests; retry later')
            request_id = 'EL-TEST-' + uuid.uuid4().hex[:16].upper()
            db.execute('INSERT INTO requests VALUES (?,?,?,?,?)', (key, request_id, fingerprint, json.dumps(payload, ensure_ascii=False), int(time.time())))
    os.chmod(db_path, 0o600)
    return {'id': request_id, 'status': 'LOCAL_TEST_SAVED', 'total_cents': payload['total_cents'], 'known_total_cents': known_total, 'quote_items': quote_items, 'currency': 'EUR', 'external_delivery': False,
            'subtotal_cents': payload.get('subtotal_cents', known_total), 'discount_percent': payload.get('discount_percent', 0), 'discount_cents': payload.get('discount_cents', 0), 'shipping_cents': payload.get('shipping_cents', 0), 'collective': bool(payload.get('collective', False)), '_telegram_user_id': identity['id'] if identity else None}


def claim_notification(db_path, request_id):
    with sqlite3.connect(db_path, timeout=10) as db:
        db.execute('CREATE TABLE IF NOT EXISTS notification_attempts (id TEXT PRIMARY KEY, state TEXT NOT NULL, attempted_at INTEGER NOT NULL)')
        cursor = db.execute('INSERT OR IGNORE INTO notification_attempts VALUES (?, ?, ?)', (request_id, 'pending', int(time.time())))
        return cursor.rowcount == 1


def finish_notification(db_path, request_id, delivered):
    with sqlite3.connect(db_path, timeout=10) as db:
        db.execute('UPDATE notification_attempts SET state=? WHERE id=?', ('sent' if delivered else 'failed', request_id))


def send_telegram_message(token, user_id, text):
    """Confirmation to the submitting user's own chat. Never to a merchant. Best effort."""
    try:
        req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage', data=json.dumps({'chat_id': user_id, 'text': text, 'disable_web_page_preview': True}).encode(), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=6) as r:
            return json.load(r).get('ok') is True
    except Exception:
        return False


def confirmation_text(result, items):
    labels = {'vial': 'Vial', 'dual_chamber': 'Doppelkammer inkl. Pen', 'pen': 'Zubehör', 'vial_pack': '10er-Pack Vial', 'dual_pack': '10er-Pack Doppelkammer inkl. Pen'}
    lines = [f"{i['quantity']}× {i['name']} {i['strength']} · {labels.get(i.get('format', 'vial'), 'Artikel')}" for i in items]
    money = lambda c: f"{c // 100:,}".replace(',', '.') + f",{c % 100:02d} €"  # 2.840,50 € wie im Shop
    cents = result['total_cents']
    total = 'Preis teilweise auf Anfrage' if cents is None else money(cents)
    extra = ''
    if result.get('discount_cents'):
        extra += f"\nZwischensumme: {money(result['subtotal_cents'])}\nMengenrabatt {result['discount_percent']} %: −{money(result['discount_cents'])}"
    if result.get('collective'):
        extra += '\nSammelbestellung: versandkostenfrei, gebündelte Lieferung'
    elif result.get('subtotal_cents'):
        extra += '\nVersand: inklusive'
    return ('Elements Labs · Testanfrage gespeichert\n' + result['id'] + '\n\n' + '\n'.join(lines) + f'{extra}\n\nSumme: {total}\n'
            'Nur lokal gespeichert – nicht an einen Händler gesendet, keine Zahlung, kein Versand.')


TEXT_TYPES = ('text/', 'application/javascript', 'application/json', 'image/svg+xml')


class ShopServer(ThreadingHTTPServer):
    mode: str
    bot_token: str
    db_path: Path
    products: list[dict]
    allowed_hosts: set[str]
    allowed_origins: set[str]
    bot_name: str = ''
    notify = staticmethod(send_telegram_message)


_client_error_window = []
_client_error_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    timeout = 15
    server_version = 'ElementsTest/1.0'

    @property
    def shop(self) -> ShopServer:
        return cast(ShopServer, self.server)

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Cache-Control', getattr(self, 'cache_policy', 'no-store'))
        inline_policy = getattr(self, 'inline_policy', '')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' https://telegram.org " + inline_policy + "; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'self' https://web.telegram.org https://*.telegram.org; object-src 'none'; base-uri 'self'")
        super().end_headers()

    def response_json(self, code, body):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def valid_host(self):
        host = self.headers.get('Host', '')
        return host in self.shop.allowed_hosts

    def do_HEAD(self):
        self.head_only = True
        self.do_GET()

    def do_GET(self):
        if not self.valid_host():
            return self.response_json(403, {'error': 'Host not allowed'})
        path = unquote(urlsplit(self.path).path)
        if '\x00' in path:
            return self.response_json(404, {'error': 'Not found'})
        if path == '/api/config':
            return self.response_json(200, {'mode': self.shop.mode, 'external_delivery': False, 'payments': False, 'bot': self.shop.bot_name})
        if path == '/health':
            return self.response_json(200, {'status': 'ok', 'mode': self.shop.mode, 'products': len(self.shop.products), 'node': os.environ.get('ELEMENTS_NODE', 'primary')})
        target = (ROOT/'public'/path.lstrip('/')).resolve()
        public = (ROOT/'public').resolve()
        if not target.is_relative_to(public) or any(part.startswith('.') for part in target.relative_to(public).parts):
            return self.response_json(404, {'error': 'Not found'})
        if path == '/':
            target = public/'index.html'
        if not target.is_file():
            return self.response_json(404, {'error': 'Not found'})
        data = target.read_bytes()
        mime = mimetypes.guess_type(str(target))[0] or 'application/octet-stream'
        if mime == 'text/html':
            scripts = re.findall(r'<script\b[^>]*>(.*?)</script\s*>', data.decode('utf-8'), re.S | re.I)
            self.inline_policy = ' '.join("'sha256-" + base64.b64encode(hashlib.sha256(code.encode()).digest()).decode() + "'" for code in scripts)
        etag = '"' + hashlib.sha256(data).hexdigest()[:20] + '"'
        self.cache_policy = 'public, max-age=86400' if target.relative_to(public).parts[0] == 'assets' else 'no-cache'
        if self.headers.get('If-None-Match') == etag:
            self.send_response(304)
            self.send_header('ETag', etag)
            return self.end_headers()
        encoded = False
        if mime.startswith(TEXT_TYPES) and len(data) > 1024 and 'gzip' in self.headers.get('Accept-Encoding', ''):
            data, encoded = gzip.compress(data, 6, mtime=0), True
        self.send_response(200)
        self.send_header('Content-Type', mime + ('; charset=utf-8' if mime.startswith('text/') or mime in {'application/javascript','application/json'} else ''))
        self.send_header('ETag', etag)
        self.send_header('Vary', 'Accept-Encoding')
        if encoded:
            self.send_header('Content-Encoding', 'gzip')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        if not getattr(self, 'head_only', False):
            self.wfile.write(data)

    def client_error(self):
        """Browser-side crash reports from the mini app: validated first, then rate limited; written to the service log only."""
        origin = self.headers.get('Origin')
        if origin and origin not in self.shop.allowed_origins:
            return self.response_json(403, {'error': 'Origin not allowed'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            length = -1
        if length < 1 or length > 2048:
            return self.response_json(413, {'error': 'Invalid body size'})
        try:
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError
        except (ValueError, UnicodeError, RecursionError):
            return self.response_json(400, {'error': 'Invalid report'})
        now = time.time()
        with _client_error_lock:
            _client_error_window[:] = [t for t in _client_error_window if now - t < 60]
            if len(_client_error_window) >= 30:
                return self.response_json(429, {'error': 'Too many reports'})
            _client_error_window.append(now)
        clean = {key: re.sub(r'[^\x20-\x7e]', ' ', str(body.get(key, '')))[:160] for key in ('m', 's', 'r', 'p', 'v')}
        clean['l'] = body.get('l') if isinstance(body.get('l'), int) else 0
        print('CLIENT-ERROR ' + json.dumps(clean, ensure_ascii=True), flush=True)
        self.send_response(204)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_POST(self):
        if not self.valid_host():
            return self.response_json(403, {'error': 'Host not allowed'})
        if self.path == '/api/client-error':
            return self.client_error()
        if self.path != '/api/orders':
            return self.response_json(404, {'error': 'Not found'})
        origin = self.headers.get('Origin')
        if origin and origin not in self.shop.allowed_origins:
            return self.response_json(403, {'error': 'Origin not allowed'})
        if self.headers.get_content_type() != 'application/json':
            return self.response_json(415, {'error': 'JSON required'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 1 or length > 16384:
                return self.response_json(413, {'error': 'Invalid body size'})
            body = json.loads(self.rfile.read(length))
            result = save_request(body, self.shop.products, self.shop.db_path, self.shop.mode, self.headers.get('X-Telegram-Init-Data', ''), self.shop.bot_token)
        except MinOrderError as exc:
            return self.response_json(422, {'error': str(exc), 'code': 'MIN_ORDER', 'min_order_cents': exc.minimum_cents, 'subtotal_cents': exc.subtotal_cents})
        except RateLimitError:
            return self.response_json(429, {'error': 'Too many requests; retry later', 'code': 'RATE_LIMITED'})
        except RecursionError:
            return self.response_json(400, {'error': 'Invalid request'})
        except (ValueError, UnicodeError) as exc:
            return self.response_json(400, {'error': str(exc), 'code': 'AUTH_EXPIRED' if str(exc) == 'Expired Telegram authentication' else 'INVALID_REQUEST'})
        except (sqlite3.Error, OSError):
            return self.response_json(503, {'error': 'Local inbox unavailable; request not confirmed'})
        uid = result.pop('_telegram_user_id', None)
        if self.shop.mode == 'telegram':
            try:
                claimed = claim_notification(self.shop.db_path, result['id'])
            except sqlite3.Error:
                claimed = False
                result['notification_status'] = 'unavailable'
            if claimed:
                by_id = {p['id']: p for p in self.shop.products}
                lines = [{'quantity': i['quantity'], 'name': by_id[i['id']]['name'], 'strength': by_id[i['id']]['concentration'], 'format': by_id[i['id']].get('format', 'vial')} for i in body['items']]
                delivered = self.shop.notify(self.shop.bot_token, uid, confirmation_text(result, lines))
                result['notification_status'] = 'sent' if delivered else 'failed'
                if delivered:
                    result['notified'] = True
                try:
                    finish_notification(self.shop.db_path, result['id'], delivered)
                except sqlite3.Error:
                    result['notification_record'] = 'pending'
        return self.response_json(200, result)

    def log_message(self, format, *args):
        # Do not log URL querystrings, Telegram headers or request bodies.
        print(f'{self.command} {self.path.split("?")[0]} {str(args[1]) if len(args)>1 else ""}', flush=True)


def load_products():
    products = json.loads((ROOT / 'data/products.json').read_text())
    formats = ROOT / 'data/shop-formats.json'
    if formats.is_file():
        products += json.loads(formats.read_text())
    packs = ROOT / 'data/catalog-packs.json'
    if packs.is_file():
        products += json.loads(packs.read_text())
    if len({p['id'] for p in products}) != len(products):
        raise ValueError('Duplicate product id across formats')
    return products


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--mode', choices=['preview','telegram'], default='preview')
    parser.add_argument('--public-origin', help='Explicit isolated HTTPS preview origin; never the original website')
    parser.add_argument('--db', type=Path, default=ROOT/'runtime/test-requests.sqlite3')
    parser.add_argument('--relaxed-terms', action='store_true', help='NUR fuer die Browser-Abnahme: Mindestwert, Versand und Rabatt aus')
    args = parser.parse_args()
    if args.relaxed_terms:
        global TERMS
        TERMS = relaxed()
    token = os.environ.get('ELEMENTS_TELEGRAM_BOT_TOKEN', '')
    if args.public_origin and args.mode != 'telegram':
        parser.error('--public-origin requires --mode telegram (signed Telegram identity)')
    if args.mode == 'telegram' and not token:
        parser.error('ELEMENTS_TELEGRAM_BOT_TOKEN must be configured securely for this shop bot')
    server = ShopServer(('127.0.0.1', args.port), Handler)
    server.mode = args.mode
    server.bot_token = token
    server.db_path = args.db
    server.bot_name = os.environ.get('ELEMENTS_BOT_USERNAME', '') if re.fullmatch(r'[A-Za-z0-9_]{5,32}', os.environ.get('ELEMENTS_BOT_USERNAME', '')) else ''
    server.notified = set()
    server.products = load_products()
    server.allowed_hosts = {f'127.0.0.1:{args.port}',f'localhost:{args.port}'}
    server.allowed_origins = {f'http://127.0.0.1:{args.port}',f'http://localhost:{args.port}'}
    if args.public_origin:
        u = urlsplit(args.public_origin)
        if u.scheme != 'https' or not u.netloc or u.path not in {'','/'} or u.query or u.fragment or u.username or u.password:
            parser.error('A clean HTTPS origin is required')
        server.allowed_hosts.add(u.netloc)
        server.allowed_origins.add(f'https://{u.netloc}')
    print(f'ELEMENTS LABS isolated TEST server on http://127.0.0.1:{args.port} ({args.mode}, no external delivery)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

if __name__ == '__main__':
    main()
