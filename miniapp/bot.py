"""Elements Labs bot: catalogue entry points and private request confirmations.
Token from the local environment only. No orders or messages to merchants.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from server import load_products
from terms import text_vars
try:
    import support  # Kontakt-/Support-Relay (optional: fehlt die Datei, laeuft der Bot wie bisher)
except ImportError:
    support = None

ROOT = Path(__file__).resolve().parent
API = 'https://api.telegram.org/bot{}/{}'
PRODUCTS = {p['id'] for p in load_products()}
COMMANDS = [
    {'command': 'shop', 'description': '🛒 Shop öffnen'},
    {'command': 'packs', 'description': '10er-Packs · Preis je Stück'},
    {'command': 'preisliste', 'description': 'Preisliste als PDF'},
    {'command': 'vials', 'description': 'Vials einzeln'},
    {'command': 'doppelkammer', 'description': 'Doppelkammer inkl. Pen'},
    {'command': 'pen', 'description': 'Mehrweg-Pen (auch einzeln)'},
    {'command': 'warenkorb', 'description': 'Warenkorb'},
    {'command': 'katalog', 'description': 'Research Library'},
    {'command': 'kontakt', 'description': 'Frage an das Team'},
    {'command': 'hilfe', 'description': 'Hilfe'}]
ALLOWED_UPDATES = ['message', 'callback_query', 'chat_join_request', 'chat_member']
PRICELIST = ROOT / 'data/preisliste.pdf'
PRICELIST_MARK = '__PRICELIST__'
# Alle Texte mit Zahlen: Platzhalter {min} {cmin} {wk} {tiers} werden aus data/terms.json gefuellt (terms.text_vars), nie von Hand getippt.
DESCRIPTION_T = 'Elements Labs · Einkauf für Zwischenhändler in der EU: Vials und Doppelkammern (inklusive Pen), einzeln oder im 10er-Pack. Direktbezug, Lieferzeit {wk} Wochen, Versand ab {min} inklusive. Tippe auf START und dann auf »Shop öffnen«. Testversion: Anfragen werden lokal gespeichert.'
SHORT_DESCRIPTION_T = 'Elements Labs · Händler-Einkauf · Mindestbestellwert {min} · Versand inklusive'
TERMS_LINE_T = 'Mindestbestellwert {min} · Versand inklusive · Lieferzeit {wk} Wochen\nMengenrabatt auf rabattfähige 10er-Packs: {tiers}\nSammelbestellung von {cmin} bis unter {min}: versandkostenfrei, gebündelte Lieferung'
START_T = '🛒 ELEMENTS LABS · Einkauf für Zwischenhändler\n\nVials und Doppelkammern (inklusive Pen), einzeln oder im 10er-Pack. Direktbezug für den Export.\n\n{terms_line}\n\nTippe auf »Shop öffnen« und stelle deine Auswahl zusammen. Mit /preisliste erhältst du die Preise als PDF.\n\nTestversion: Wir speichern deine Anfrage lokal und bestätigen sie hier im Chat. Keine Zahlung und kein Außenversand.'
PACKS_T = 'Elements Labs · 10er-Packs\nJeder Preis gilt für 10 Stück, der Preis je Stück steht daneben. Mindestbestellwert {min}, Versand inklusive; Sammelbestellung ab {cmin}. Öffne den Katalog und wähle Substanz, Stoffmenge und Ausführung.'
HELP_T = 'Hilfe zum Einkauf\n• /shop – Shop öffnen\n• /packs – 10er-Packs mit Preis je Stück\n• /preisliste – Preise als PDF\n• /vials – Vials einzeln\n• /doppelkammer – Doppelkammer inklusive Pen\n• /pen – Mehrweg-Pen (auch einzeln)\n• /warenkorb – Auswahl, Mengen und Konditionen prüfen\n• /katalog – Research Library\n• /kontakt – Frage an das Team\n\nWähle Substanz, Stoffmenge und Ausführung. Ein 10er-Pack enthält 10 Stück; Menge 2 bedeutet zwei Packs. Im Warenkorb siehst du Mengenrabatt und Versand.\n\nTestversion: Speichere deine Auswahl als lokale Testanfrage. Die Bestätigung enthält deine Referenz. Keine Zahlung und kein Außenversand. Falls ein alter Chatbutton nicht lädt, öffne den Shop über den aktuellen Menüknopf.'
CAPTION_T = 'Elements Labs · Preisliste: 10er-Packs (Vial und Doppelkammer inkl. Pen) mit Preis je Stück. Mindestbestellwert {min}, Versand inklusive.'


def terms_line():
    return TERMS_LINE_T.format(**text_vars())


def _fill(template):
    return template.format(terms_line=terms_line(), **text_vars())


DESCRIPTION = _fill(DESCRIPTION_T)
SHORT_DESCRIPTION = _fill(SHORT_DESCRIPTION_T)
assert len(DESCRIPTION) <= 512 and len(SHORT_DESCRIPTION) <= 120, 'Telegram-Grenzen: Beschreibung 512, Kurzbeschreibung 120 Zeichen'


class BotAPIError(support.APIError if support else RuntimeError):
    def __init__(self, code, retry_after=5):
        self.code = code
        self.retry_after = max(1, min(60, int(retry_after)))
        super().__init__('Telegram API HTTP ' + str(code))


def call(token, method, payload=None, timeout=40):
    request = urllib.request.Request(API.format(token, method), data=json.dumps(payload or {}).encode(), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        try:
            retry_after = json.load(error).get('parameters', {}).get('retry_after', 5)
        except (ValueError, OSError):
            retry_after = 5
        raise BotAPIError(error.code, retry_after) from None
    if not result.get('ok'):
        raise BotAPIError(result.get('error_code', 500))
    return result


def origin():
    file = ROOT / 'runtime/origin.txt'
    value = file.read_text().strip() if file.exists() else ''
    return value if re.fullmatch(r'https://[a-z0-9.-]+', value) else ''


def reply_for(text):
    command, _, argument = text.strip().partition(' ')
    command = command.split('@')[0].lower()
    argument = argument.strip()
    if command == '/start':
        if argument.startswith('p_') and argument[2:] in PRODUCTS:
            return 'Elements Labs · Ausführung öffnen', '/#product=' + argument[2:]
        paths = {'katalog': '/#info', 'dual': '/#dual-chamber', 'pen': '/#accessories', 'cart': '/#cart', 'packs': '/#packs'}
        if argument == 'preisliste':
            return PRICELIST_MARK, None
        if argument == 'packs':
            return _fill(PACKS_T), paths['packs']
        if argument in paths:
            return 'Elements Labs · Katalog', paths[argument]
        return _fill(START_T), '/'
    if command == '/preisliste':
        return PRICELIST_MARK, None
    paths = {'/shop': '/', '/packs': '/#packs', '/vials': '/#products/vial', '/doppelkammer': '/#dual-chamber', '/pen': '/#accessories', '/warenkorb': '/#cart', '/katalog': '/#info'}
    if command == '/packs':
        return _fill(PACKS_T), paths[command]
    if command in paths:
        return 'Elements Labs · Katalog öffnen', paths[command]
    if command == '/hilfe':
        return _fill(HELP_T), None
    return 'Bitte einen Bereich wählen oder /hilfe nutzen.', None


def web_url(base, path):
    """Target route as ?r=... : Telegram may rewrite the URL fragment with its launch parameters."""
    if path.startswith('/#'):
        return base + '/?r=' + urllib.parse.quote(path[2:], safe='=/-_')
    return base + path


def menu(base):
    return {'inline_keyboard': [
        [{'text': '🛒  SHOP ÖFFNEN', 'web_app': {'url': web_url(base, '/')}}],
        [{'text': '10er-Packs · Komplettkatalog', 'web_app': {'url': web_url(base, '/#packs')}}],
        [{'text': 'Vials', 'web_app': {'url': web_url(base, '/#products/vial')}}, {'text': 'Doppelkammer inkl. Pen', 'web_app': {'url': web_url(base, '/#dual-chamber')}}],
        [{'text': 'Warenkorb', 'web_app': {'url': web_url(base, '/#cart')}}, {'text': '📄 Preisliste (PDF)', 'callback_data': 'pricelist'}]]}


def remember_link(chat_id, message_id, path):
    file = ROOT / 'runtime/bot-links.json'
    try:
        records = json.loads(file.read_text()) if file.exists() else []
    except (OSError, ValueError):
        records = []
    if not isinstance(records, list):
        records = []
    records = [r for r in records if isinstance(r, dict) and isinstance(r.get('chat_id'), int) and isinstance(r.get('message_id'), int) and (r['chat_id'], r['message_id']) != (chat_id, message_id)]
    records.append({'chat_id': chat_id, 'message_id': message_id, 'path': path})
    temporary = file.with_suffix('.next')
    temporary.write_text(json.dumps(records[-100:]))
    os.replace(temporary, file)


def refresh_links(token, base):
    file = ROOT / 'runtime/bot-links.json'
    if not file.exists():
        return True
    try:
        records = json.loads(file.read_text())
    except (OSError, ValueError):
        return False
    if not isinstance(records, list):
        return False
    complete = True
    for record in records[-100:]:
        if not isinstance(record, dict) or not isinstance(record.get('chat_id'), int) or not isinstance(record.get('message_id'), int):
            continue
        path = record.get('path', '/')
        if not isinstance(path, str) or not (path == '/' or path.startswith('/#')) or (record.get('last_origin') == base and not path.startswith('/#')):
            continue
        markup = menu(base) if path == '/' else {'inline_keyboard': [[{'text': 'Elements Labs öffnen', 'web_app': {'url': web_url(base, path)}}]]}
        try:
            call(token, 'editMessageReplyMarkup', {'chat_id': record['chat_id'], 'message_id': record['message_id'], 'reply_markup': markup})
        except BotAPIError as error:
            if error.code == 401:
                raise
            if error.code not in (400, 403):
                complete = False
                break
        except (urllib.error.URLError, TimeoutError, ValueError):
            complete = False
            break
        record['last_origin'] = base
    temporary = file.with_suffix('.next')
    temporary.write_text(json.dumps(records))
    os.replace(temporary, file)
    return complete


def multipart(fields, file_field, file_name, file_bytes):
    boundary = '----el' + os.urandom(8).hex()
    parts = []
    for key, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; filename="{file_name}"\r\nContent-Type: application/pdf\r\n\r\n'.encode() + file_bytes + b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    return b''.join(parts), 'multipart/form-data; boundary=' + boundary


def send_pricelist(token, chat_id):
    """Preisliste als PDF: beim ersten Mal hochladen, danach per file_id (neu hochladen, sobald die Datei sich aendert)."""
    if not PRICELIST.is_file():
        call(token, 'sendMessage', {'chat_id': chat_id, 'text': 'Die Preisliste ist gerade nicht verfügbar. Bitte im Shop unter »10er-Packs« nachsehen.'})
        return
    stamp = f'{int(PRICELIST.stat().st_mtime)}:{PRICELIST.stat().st_size}'
    cache = ROOT / 'runtime/pricelist-file.json'
    try:
        known = json.loads(cache.read_text()) if cache.exists() else {}
    except (OSError, ValueError):
        known = {}
    caption = _fill(CAPTION_T)
    if known.get('stamp') == stamp and known.get('file_id'):
        try:
            call(token, 'sendDocument', {'chat_id': chat_id, 'document': known['file_id'], 'caption': caption})
            return
        except BotAPIError as error:
            if error.code not in (400,):
                raise
    data, ctype = multipart({'chat_id': chat_id, 'caption': caption}, 'document', 'Elements-Labs-Preisliste.pdf', PRICELIST.read_bytes())
    request = urllib.request.Request(API.format(token, 'sendDocument'), data=data, headers={'Content-Type': ctype})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        raise BotAPIError(error.code) from None
    file_id = (result.get('result', {}).get('document') or {}).get('file_id')
    if file_id:
        try:
            cache.write_text(json.dumps({'stamp': stamp, 'file_id': file_id}))
        except OSError:
            pass


def handle_callback(token, query):
    message = query.get('message') or {}
    chat = message.get('chat', {})
    try:
        call(token, 'answerCallbackQuery', {'callback_query_id': query['id']})
    except BotAPIError:
        pass
    if support and query.get('data') in ('role_h', 'role_e'):
        support.handle_role(lambda method, payload=None: call(token, method, payload), query)
        return
    if query.get('data') == 'pricelist' and chat.get('type') == 'private' and isinstance(chat.get('id'), int):
        try:
            send_pricelist(token, chat['id'])
        except BotAPIError as error:
            if error.code not in (400, 403):
                raise
            print('Bot recipient unavailable; skipped pricelist:', error.code, flush=True)


def api_for(token):
    return lambda method, payload=None: call(token, method, payload)


def handle(token, message, base):
    chat = message.get('chat', {})
    text = message.get('text')
    if support and support.is_team_chat(chat):
        support.handle_team(api_for(token), message)
        return
    if support and chat.get('type') == 'private' and support.wants_relay(message):
        support.handle_private(api_for(token), message, base)
        return
    if chat.get('type') != 'private' or not isinstance(text, str) or not text.startswith('/'):
        return
    body, path = reply_for(text)
    if body == PRICELIST_MARK:
        try:
            send_pricelist(token, chat['id'])
        except BotAPIError as error:
            if error.code not in (400, 403):
                raise
            print('Bot recipient unavailable; skipped pricelist:', error.code, flush=True)
        return
    payload = {'chat_id': chat['id'], 'text': body}
    if path and base:
        payload['reply_markup'] = menu(base) if path == '/' else {'inline_keyboard': [[{'text': 'Elements Labs öffnen', 'web_app': {'url': web_url(base, path)}}]]}
    try:
        result = call(token, 'sendMessage', payload)
    except BotAPIError as error:
        if error.code in (400, 403):
            print('Bot recipient unavailable; skipped update:', error.code, flush=True)
            return
        raise
    if path and isinstance(result, dict) and result.get('result', {}).get('message_id'):
        try:
            remember_link(chat['id'], result['result']['message_id'], path)
        except OSError:
            print('Bot link cache unavailable; message delivered, polling continues', flush=True)


def main():
    os.umask(0o077)
    token = os.environ.get('ELEMENTS_TELEGRAM_BOT_TOKEN', '')
    if not token:
        sys.exit('ELEMENTS_TELEGRAM_BOT_TOKEN fehlt')
    offset_file = ROOT / 'runtime/bot-offset.txt'
    offset = int(offset_file.read_text()) if offset_file.exists() else 0
    while True:
        try:
            call(token, 'setMyCommands', {'commands': COMMANDS})
            call(token, 'setMyDescription', {'description': DESCRIPTION})
            call(token, 'setMyShortDescription', {'short_description': SHORT_DESCRIPTION})
            refresh_links(token, origin())
            break
        except BotAPIError as error:
            if error.code in (401, 403):
                print('Bot setup authentication refused', flush=True)
                return 2
            time.sleep(error.retry_after)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            time.sleep(5)
    next_refresh = time.monotonic() + 60
    print('ELEMENTS LABS bot polling', flush=True)
    while True:
        try:
            if time.monotonic() >= next_refresh:
                refresh_links(token, origin())
                next_refresh = time.monotonic() + 60
            if support:
                support.poll_tick(api_for(token))   # Erinnerungs-Digest fuer das Team, hoechstens 1 x je 24 h
            result = call(token, 'getUpdates', {'offset': offset, 'timeout': 25, 'allowed_updates': ALLOWED_UPDATES}, timeout=40)
            for update in result.get('result', []):
                if 'message' in update:
                    handle(token, update['message'], origin())
                elif 'callback_query' in update:
                    handle_callback(token, update['callback_query'])
                elif 'chat_join_request' in update and support:
                    support.handle_join_request(api_for(token), update['chat_join_request'], origin())
                elif 'chat_member' in update and support:
                    support.handle_chat_member(update['chat_member'])
                offset = update['update_id'] + 1
                offset_file.write_text(str(offset))
        except BotAPIError as error:
            if error.code in (401, 403):
                print('Bot authentication refused; stopped without retries', flush=True)
                return 2
            time.sleep(error.retry_after)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, OSError):
            time.sleep(3)
        except KeyboardInterrupt:
            return 0


if __name__ == '__main__':
    sys.exit(main())
