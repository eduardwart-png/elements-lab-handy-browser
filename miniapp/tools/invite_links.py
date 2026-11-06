"""Benannte Einladungslinks je Quelle fuer die Elements-Labs-Gruppe (nur Hauptpaket; Renes Paket enthaelt tools/ nicht).

  python tools/invite_links.py create <quelle> [--join-request]   Link mit Namen <quelle> anlegen (createChatInviteLink)
  python tools/invite_links.py list                              angelegte Links mit Zaehlern (Beitrittsanfragen / Beitritte)

Token (ELEMENTS_TELEGRAM_BOT_TOKEN) und Gruppe (ELEMENTS_GROUP_CHAT_ID) nur aus der Umgebung; der Token wird nie ausgegeben.
Die Bot-API liefert zu einem Link keine Nutzungszahl; der Bot zaehlt deshalb selbst (Beitrittsanfragen ueber den Link-Namen in
chat_join_request, Beitritte in chat_member) in runtime/support.sqlite3. Das zaehlt ab dem Zeitpunkt, ab dem der Bot laeuft.
Nur echte Beitritte ueber geteilte Links; keine Funktion zum Erzeugen oder Hinzufuegen von Mitgliedern.
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
import support  # noqa: E402
from bot import BotAPIError, call  # noqa: E402

NAME = re.compile(r'[A-Za-z0-9_-]{1,32}')


def _links_file():
    return ROOT / 'runtime/invite-links.json'


def _load():
    try:
        data = json.loads(_links_file().read_text())
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def create(token, chat_id, name, join_request=False):
    payload = {'chat_id': chat_id, 'name': name}
    if join_request:
        payload['creates_join_request'] = True
    link = call(token, 'createChatInviteLink', payload)['result']
    records = [r for r in _load() if r.get('name') != name]
    records.append({'name': name, 'invite_link': link.get('invite_link', ''), 'creates_join_request': bool(link.get('creates_join_request')),
                    'created_at': int(time.time())})
    _links_file().parent.mkdir(exist_ok=True)
    _links_file().write_text(json.dumps(records, indent=1))
    return link


def main(argv=None):
    parser = argparse.ArgumentParser(description='Einladungslinks je Quelle')
    sub = parser.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('create')
    c.add_argument('name')
    c.add_argument('--join-request', action='store_true', help='Beitritt nur per Anfrage (Bot begruesst und nimmt an)')
    sub.add_parser('list')
    args = parser.parse_args(argv)
    if args.cmd == 'list':
        counts = support.invite_counts()
        names = [r['name'] for r in _load()] + sorted(set(counts) - {r['name'] for r in _load()})
        print(f"{'Quelle':<20} Zaehler")
        for record_name in names:
            n = counts.get(record_name, {'requests': 0, 'joins': 0})
            link = next((r['invite_link'] for r in _load() if r['name'] == record_name), '')
            print(f"{record_name:<20} Anfragen {n['requests']}  Beitritte {n['joins']}  {link}")
        return 0
    if not NAME.fullmatch(args.name):
        print('Name: 1-32 Zeichen, nur Buchstaben, Ziffern, - und _', file=sys.stderr)
        return 2
    token = os.environ.get('ELEMENTS_TELEGRAM_BOT_TOKEN', '')
    chat_id = support.group_chat_id()
    if not token or chat_id is None:
        print('ELEMENTS_TELEGRAM_BOT_TOKEN und ELEMENTS_GROUP_CHAT_ID muessen in der Umgebung gesetzt sein', file=sys.stderr)
        return 2
    try:
        link = create(token, chat_id, args.name, args.join_request)
    except BotAPIError as error:
        print(f'Telegram lehnte ab (HTTP {error.code}); ist der Bot Admin mit dem Recht "Nutzer hinzufuegen"?', file=sys.stderr)
        return 1
    except OSError as error:
        print('Netzwerkfehler:', type(error).__name__, file=sys.stderr)
        return 1
    print(f"{args.name}: {link.get('invite_link', '')}" + ('  (mit Beitrittsanfrage)' if args.join_request else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
