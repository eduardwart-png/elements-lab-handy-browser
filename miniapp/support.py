"""Kontakt-/Support-Relay fuer den Elements-Labs-Bot.

Interessenten schreiben dem Bot privat (/kontakt oder t.me/<Bot>?start=kontakt); jede Nachricht wird per copyMessage in ein eigenes
Thema der internen Team-Gruppe (Forum-Supergruppe) kopiert, Antworten des Teams im Thema gehen per copyMessage zurueck.
Konfiguration nur ueber die Umgebung: ELEMENTS_TEAM_CHAT_ID (fehlt sie oder ist sie ungueltig, ist der Relay AUS) und optional
ELEMENTS_GROUP_CHAT_ID (Beitrittsanfragen). Gespeichert wird nur: Nutzer-ID, Thema-ID, Zeitstempel, Sprache, Status, Zaehler; nie
Nachrichteninhalte oder Namen. Konditionen in Auto-Antworten kommen zur Laufzeit aus data/terms.json.
Alle API-Aufrufe laufen ueber eine uebergebene Funktion api(method, payload); 400/403 werden hier abgefangen, damit die Poll-Schleife
nie anhaelt (401 geht weiter an die Schleife, 429/5xx nur beim ersten Kopieren, damit das Update spaeter erneut versucht wird).
"""
import contextlib
import hashlib
import os
import re
import sqlite3
import time
import unicodedata
import urllib.parse
from pathlib import Path

import terms as _terms

ROOT = Path(__file__).resolve().parent
HOUR = 3600
DAY = 24 * HOUR
MAX_PER_HOUR = 20
MAX_CHARS = 4000
MAX_BYTES = 20 * 1024 * 1024
ACK_EVERY = 12 * HOUR
LANGS = ('de', 'en', 'fr')
SERVICE_KEYS = ('forum_topic_created', 'forum_topic_edited', 'forum_topic_closed', 'forum_topic_reopened', 'general_forum_topic_hidden',
                'general_forum_topic_unhidden', 'pinned_message', 'new_chat_members', 'left_chat_member', 'new_chat_title', 'new_chat_photo',
                'delete_chat_photo', 'message_auto_delete_timer_changed', 'migrate_to_chat_id', 'migrate_from_chat_id', 'video_chat_started',
                'video_chat_ended', 'write_access_allowed')


class APIError(RuntimeError):
    """Basisklasse; bot.BotAPIError erbt davon (Attribut code = HTTP-/Telegram-Fehlercode)."""
    code = 0


def now():
    return time.time()


def load_terms():
    return _terms.load_terms()


# ---------------------------------------------------------------- Texte (keine Zahlen ausser Grenzen/Antwortzeit; Konditionen per Platzhalter)
TEXTS = {
    'de': {
        'welcome': 'Hallo! Hier erreichst du das Team von Elements Labs.\nSchreib uns deine Frage, wir melden uns, sobald wir können.\n'
                   'Zu Mindestbestellwert, Versand, Lieferzeit, Mengenrabatt, Sammelbestellung und Preisliste antwortet der Bot sofort.',
        'unavailable': 'Kontakt ist gerade nicht verfügbar, bitte schreibe später. Shop: /shop · Preisliste: /preisliste',
        'ack': 'Danke, das beantwortet das Team persönlich. Wir melden uns, sobald wir können.\n'
               'Bis dahin findest du in der Mini App die Chargen-Suche und die Qualitätsseite.',
        'footer': 'Deine Nachricht ist auch beim Team angekommen; wir melden uns, sobald wir können.',
        'too_long': 'Die Nachricht ist leider zu lang (höchstens 4000 Zeichen). Bitte kürzer oder in mehreren Teilen schicken.',
        'too_big': 'Die Datei ist leider zu groß (höchstens 20 MB). Bitte eine kleinere Datei oder einen Text schicken.',
        'rate': 'Du hast in der letzten Stunde schon viele Nachrichten geschickt. Bitte warte etwas; was du bisher geschickt hast, ist beim Team angekommen.',
        'join': 'Willkommen bei Elements Labs! Zum Shop: Knopf unten oder /shop.\nKurze Frage: Händler oder Endkunde?',
        'role_thanks': 'Danke! Für Fragen an das Team: /kontakt',
        'min_order': 'Mindestbestellwert: {min}. Von {cmin} bis unter {min} ist eine Sammelbestellung möglich.',
        'shipping': 'Versand: ab {min} inklusive.',
        'collective': 'Sammelbestellung von {cmin} bis unter {min}: versandkostenfrei, gebündelte Lieferung.',
        'delivery': 'Lieferzeit: {weeks}.',
        'weeks': '{a} bis {b} Wochen',
        'discount': 'Mengenrabatt auf rabattfähige 10er-Packs: {tiers}. Im Warenkorb siehst du Mengenrabatt und Versand.',
        'tier': '{p} % ab {eur}',
        'pricelist': 'Die Preisliste als PDF: Knopf unten oder /preisliste.',
        'b_shop': '🛒 Shop öffnen', 'b_pricelist': '📄 Preisliste (PDF)', 'b_batch': 'Chargen-Suche', 'b_quality': 'Qualität',
        'b_role_h': 'Händler', 'b_role_e': 'Endkunde',
    },
    'en': {
        'welcome': 'Hi! This is where you reach the Elements Labs team.\nWrite us your question; we will get back to you as soon as we can.\n'
                   'For minimum order, shipping, delivery time, volume discount, group orders and the price list the bot answers right away.',
        'unavailable': 'Contact is not available right now, please write again later. Shop: /shop · Price list: /preisliste',
        'ack': 'Thank you, the team will answer this personally. We will get back to you as soon as we can.\n'
               'Meanwhile you will find the batch lookup and the quality page in the Mini App.',
        'footer': 'Your message has also reached the team; we will get back to you as soon as we can.',
        'too_long': 'Sorry, this message is too long (at most 4000 characters). Please shorten it or send it in parts.',
        'too_big': 'Sorry, this file is too large (at most 20 MB). Please send a smaller file or a text.',
        'rate': 'You have sent many messages in the last hour. Please wait a little; everything you sent so far has reached the team.',
        'join': 'Welcome to Elements Labs! Shop: button below or /shop.\nQuick question: reseller or end customer?',
        'role_thanks': 'Thank you! Questions for the team: /kontakt',
        'min_order': 'Minimum order value: {min}. From {cmin} up to below {min} a group order is possible.',
        'shipping': 'Shipping: included from {min}.',
        'collective': 'Group order from {cmin} up to below {min}: no shipping costs, bundled delivery.',
        'delivery': 'Delivery time: {weeks}.',
        'weeks': '{a} to {b} weeks',
        'discount': 'Volume discount on eligible 10-packs: {tiers}. The cart shows discount and shipping.',
        'tier': '{p} % from {eur}',
        'pricelist': 'Price list as PDF: button below or /preisliste.',
        'b_shop': '🛒 Open shop', 'b_pricelist': '📄 Price list (PDF)', 'b_batch': 'Batch lookup', 'b_quality': 'Quality',
        'b_role_h': 'Reseller', 'b_role_e': 'End customer',
    },
    'fr': {
        'welcome': "Bonjour ! Ici, tu joins l'équipe d'Elements Labs.\nÉcris-nous ta question ; nous te répondons dès que possible.\n"
                   'Pour la commande minimum, la livraison, le délai, la remise sur quantité, la commande groupée et la liste de prix, le bot répond tout de suite.',
        'unavailable': "Le contact n'est pas disponible pour le moment, merci de réécrire plus tard. Boutique : /shop · Liste de prix : /preisliste",
        'ack': "Merci, l'équipe te répondra personnellement, dès que possible.\n"
               'En attendant, la recherche de lot et la page qualité sont dans la Mini App.',
        'footer': "Ton message est aussi arrivé à l'équipe ; nous te répondons dès que possible.",
        'too_long': 'Désolé, ce message est trop long (4000 caractères au maximum). Merci de le raccourcir ou de l’envoyer en plusieurs parties.',
        'too_big': 'Désolé, ce fichier est trop volumineux (20 MB au maximum). Merci d’envoyer un fichier plus petit ou un texte.',
        'rate': "Tu as envoyé beaucoup de messages dans la dernière heure. Merci de patienter ; tout ce que tu as envoyé est arrivé à l'équipe.",
        'join': 'Bienvenue chez Elements Labs ! Boutique : bouton ci-dessous ou /shop.\nPetite question : revendeur ou particulier ?',
        'role_thanks': "Merci ! Questions pour l'équipe : /kontakt",
        'min_order': 'Commande minimum : {min}. De {cmin} à moins de {min}, une commande groupée est possible.',
        'shipping': 'Livraison : incluse dès {min}.',
        'collective': 'Commande groupée de {cmin} à moins de {min} : sans frais de port, livraison regroupée.',
        'delivery': 'Délai de livraison : {weeks}.',
        'weeks': '{a} à {b} semaines',
        'discount': 'Remise sur quantité pour les packs de 10 éligibles : {tiers}. Le panier affiche la remise et la livraison.',
        'tier': '{p} % dès {eur}',
        'pricelist': 'Liste de prix en PDF : bouton ci-dessous ou /preisliste.',
        'b_shop': '🛒 Ouvrir la boutique', 'b_pricelist': '📄 Liste de prix (PDF)', 'b_batch': 'Recherche de lot', 'b_quality': 'Qualité',
        'b_role_h': 'Revendeur', 'b_role_e': 'Particulier',
    },
    # Interne Hinweise im Team-Chat (nur Deutsch)
    'team': {
        'blocked': 'Gesperrt. Nachrichten dieser Person werden still ignoriert. Aufheben: /entsperren',
        'unblocked': 'Entsperrt. Nachrichten dieser Person kommen wieder an.',
        'closed': 'Geschlossen. Schreibt die Person erneut, öffnet sich dieses Thema wieder.',
        'not_delivered': 'Antwort nicht zugestellt: Die Person hat den Bot blockiert oder den Chat gelöscht.',
        'auto_note': 'Bot hat automatisch geantwortet zu: {topics}. Bitte bei Bedarf ergänzen.',
        'role_note': 'Angabe nach Beitrittsanfrage: {role}.',
        'open_none': 'Keine offenen Anfragen.',
        'open_head': 'Offene Anfragen (älteste zuerst):',
        'digest_head': 'Erinnerung: {n} Anfrage(n) warten seit mehr als 24 Stunden auf Antwort (älteste zuerst):',
        'line': '• {link} · wartet seit {age}',
        'hours': '{n} Std.', 'days': '{n} Tg.',
        'min_order': 'Mindestbestellwert', 'shipping': 'Versand', 'collective': 'Sammelbestellung', 'delivery': 'Lieferzeit',
        'discount': 'Mengenrabatt', 'pricelist': 'Preisliste',
    },
}
FACT_ORDER = ('min_order', 'shipping', 'collective', 'delivery', 'discount', 'pricelist')

# ---------------------------------------------------------------- Erkennung (Kleinschreibung, Akzente entfernt, feste Muster)
SENSITIVE = re.compile(
    r'qualit|\brein|purit|puret|\bpure\b|herkunft|woher|\borigin|herstell|manufactur|fabricant|zuverlass|serios|vertrau|trust|reliab|fiable|'
    r'fake|scam|betrug|arnaque|zahlung|bezahl|payment|\bpay|crypto|krypto|bitcoin|\bbtc\b|usdt|uberweis|iban|rechnung|invoice|facture|paiement|'
    r'legal|recht|gesetz|erlaubt|verbot|zoll|customs|douane|steuer|\btax|\btva\b|\bloi\b|juridi|\bcoa\b|zertifi|certifi|analys|labor|\blab\b|hplc|'
    r'test|charge|batch|\blot\b|sicher|\bsafe|secur|nebenwirk|side effect|dosier|dosage|posolog')
FACTS = {
    'min_order': re.compile(r'mindestbestell|mindestwert|mindestmenge|mindestabnahme|minimum|\bmoq\b|min\.? order|commande min'),
    'shipping': re.compile(r'versand|verschick|porto|shipping|\bship|livraison|expedi|frais de port'),
    'collective': re.compile(r'sammel|group order|collective|groupee|commande group'),
    'delivery': re.compile(r'lieferzeit|lieferdauer|wie lange|wann kommt|how long|delivery time|\bdeliver|\bdelai|combien de temps'),
    'discount': re.compile(r'rabatt|discount|staffel|remise|reduction|nachlass|mengenpreis'),
    'pricelist': re.compile(r'preisliste|price ?list|\bpreise\b|\bprices\b|\bprix\b|tarif|katalog'),
}


def _norm(text):
    text = unicodedata.normalize('NFKD', (text or '').lower())
    return ''.join(c for c in text if not unicodedata.combining(c))


def detect(text):
    """-> (set der Fakten-Themen, heikel?). Heikel geht vor: dann keine inhaltliche Antwort."""
    s = _norm(text)
    return {k for k, rx in FACTS.items() if rx.search(s)}, bool(SENSITIVE.search(s))


def eur(cents, lang='de'):
    whole, rest = divmod(int(cents), 100)
    if lang == 'en':
        return '€' + f'{whole:,}' + (f'.{rest:02d}' if rest else '')
    if lang == 'fr':
        return f'{whole:,}'.replace(',', '\u00a0') + (f',{rest:02d}' if rest else '') + '\u00a0€'
    return _terms.short_eur(int(cents))


def fact_answer(intents, lang):
    t, terms = TEXTS[lang], load_terms()
    w = terms['delivery_weeks']
    values = {'min': eur(terms['min_order_cents'], lang), 'cmin': eur(terms['collective_min_cents'], lang),
              'weeks': t['weeks'].format(a=w['min'], b=w['max']),
              'tiers': ' · '.join(t['tier'].format(p=x['percent'], eur=eur(x['min_cents'], lang)) for x in terms['tiers'])}
    lines = [t[k].format(**values) for k in FACT_ORDER if k in intents]
    return '\n'.join(lines + ['', t['footer']])


# ---------------------------------------------------------------- Konfiguration
def _env_chat(name):
    value = os.environ.get(name, '').strip()
    return int(value) if re.fullmatch(r'-100\d{6,15}', value) else None


def team_chat_id():
    return _env_chat('ELEMENTS_TEAM_CHAT_ID')


def group_chat_id():
    return _env_chat('ELEMENTS_GROUP_CHAT_ID')


def lang_of(user):
    code = str((user or {}).get('language_code') or '')[:2].lower()
    return code if code in LANGS else 'de'


def command_of(text):
    if not isinstance(text, str) or not text.startswith('/'):
        return '', ''
    command, _, argument = text.strip().partition(' ')
    return command.split('@')[0].lower(), argument.strip().lower()


def is_entry(message):
    return command_of(message.get('text')) in (('/kontakt', ''), ('/start', 'kontakt'))


def wants_relay(message):
    """Privat: Einstieg /kontakt bzw. ?start=kontakt oder jede Nachricht, die kein Befehl ist."""
    text = message.get('text')
    return is_entry(message) or not (isinstance(text, str) and text.startswith('/'))


def is_team_chat(chat):
    team = team_chat_id()
    return team is not None and (chat or {}).get('id') == team


# ---------------------------------------------------------------- Speicher (nur IDs, Zeiten, Sprache, Status, Zaehler)
class Store:
    def __init__(self, root=None):
        self.path = Path(root or ROOT) / 'runtime/support.sqlite3'
        with self._db() as db:
            db.executescript(
                'CREATE TABLE IF NOT EXISTS topics (user_id INTEGER PRIMARY KEY, thread_id INTEGER, lang TEXT, status TEXT, blocked INTEGER DEFAULT 0,'
                ' created_at REAL, last_user_at REAL, last_team_at REAL, waiting_since REAL, last_ack_at REAL, limit_notice_at REAL);'
                'CREATE INDEX IF NOT EXISTS topics_thread ON topics(thread_id);'
                'CREATE TABLE IF NOT EXISTS events (user_id INTEGER, at REAL);'
                'CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value REAL);'
                'CREATE TABLE IF NOT EXISTS invites (name TEXT PRIMARY KEY, requests INTEGER DEFAULT 0, joins INTEGER DEFAULT 0);')

    @contextlib.contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, user_id):
        with self._db() as db:
            row = db.execute('SELECT * FROM topics WHERE user_id=?', (user_id,)).fetchone()
        return dict(row) if row else None

    def by_thread(self, thread_id):
        with self._db() as db:
            row = db.execute('SELECT * FROM topics WHERE thread_id=?', (thread_id,)).fetchone()
        return dict(row) if row else None

    def update(self, user_id, **fields):
        cols = ', '.join(f'{k}=?' for k in fields)
        with self._db() as db:
            db.execute('INSERT OR IGNORE INTO topics (user_id, status, blocked, created_at) VALUES (?, ?, 0, ?)', (user_id, 'open', now()))
            db.execute(f'UPDATE topics SET {cols} WHERE user_id=?', (*fields.values(), user_id))

    def recent(self, user_id, since):
        with self._db() as db:
            db.execute('DELETE FROM events WHERE at < ?', (now() - HOUR,))
            return db.execute('SELECT COUNT(*) FROM events WHERE user_id=? AND at >= ?', (user_id, since)).fetchone()[0]

    def add_event(self, user_id, at):
        with self._db() as db:
            db.execute('INSERT INTO events VALUES (?, ?)', (user_id, at))

    def waiting(self, older_than=None):
        sql = "SELECT * FROM topics WHERE status='open' AND blocked=0 AND thread_id IS NOT NULL AND waiting_since IS NOT NULL"
        args = ()
        if older_than is not None:
            sql, args = sql + ' AND waiting_since <= ?', (older_than,)
        with self._db() as db:
            return [dict(r) for r in db.execute(sql + ' ORDER BY waiting_since, user_id', args)]

    def meta(self, key, value=None):
        with self._db() as db:
            if value is not None:
                db.execute('INSERT OR REPLACE INTO meta VALUES (?, ?)', (key, value))
                return value
            row = db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
        return row[0] if row else None

    def count_invite(self, name, field):
        with self._db() as db:
            db.execute('INSERT OR IGNORE INTO invites (name) VALUES (?)', (name,))
            db.execute(f'UPDATE invites SET {field} = {field} + 1 WHERE name=?', (name,))

    def invites(self):
        with self._db() as db:
            return {r['name']: {'requests': r['requests'], 'joins': r['joins']} for r in db.execute('SELECT * FROM invites ORDER BY name')}


def count_invite(name, field):
    if field in ('requests', 'joins') and isinstance(name, str) and name:
        Store().count_invite(name[:32], field)


def invite_counts():
    return Store().invites()


# ---------------------------------------------------------------- Hilfen
def safe(api, method, payload):
    """Nebenaufrufe: Fehler ausser 401 werden nur protokolliert (Poll-Schleife laeuft weiter)."""
    try:
        return api(method, payload)
    except APIError as error:
        if error.code == 401:
            raise
        print(f'Support: {method} skipped ({error.code})', flush=True)
        return None


def web_url(base, path):
    if path.startswith('/#'):
        return base + '/?r=' + urllib.parse.quote(path[2:], safe='=/-_')
    return base + path


def info_markup(base, lang):
    t = TEXTS[lang]
    rows = []
    if base:
        rows.append([{'text': t['b_shop'], 'web_app': {'url': web_url(base, '/')}}])
    rows.append([{'text': t['b_pricelist'], 'callback_data': 'pricelist'}])
    if base:
        rows.append([{'text': t['b_batch'], 'web_app': {'url': web_url(base, '/#batch-lookup')}},
                     {'text': t['b_quality'], 'web_app': {'url': web_url(base, '/#quality')}}])
    return {'inline_keyboard': rows}


def short_id(user_id):
    digest = hashlib.sha256(f'elements-support:{user_id}'.encode()).digest()
    return ''.join(chr(65 + b % 26) for b in digest[:5])


def topic_title(user, lang):
    first = re.sub(r'[\x00-\x1f\x7f]', '', str(user.get('first_name') or ''))
    first = re.sub(r'\+?\d[\d\s\-/().]{3,}\d|\d{3,}', '', first).strip(' ·-')
    username = user.get('username') or ''
    parts = [first[:60]] if re.search(r'[^\W\d_]', first) else []
    if re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{2,31}', username):
        parts.append('@' + username)
    return f"{' '.join(parts) or 'Interessent'} · {short_id(user['id'])} · {lang.upper()}"[:128]


def topic_link(team, thread):
    return f'https://t.me/c/{str(team)[4:]}/{thread}'


def size_problem(message):
    text = message.get('text') or message.get('caption') or ''
    if len(text) > MAX_CHARS:
        return 'too_long'
    sizes = [v.get('file_size') or 0 for k in ('document', 'video', 'audio', 'voice', 'animation', 'video_note', 'sticker')
             for v in [message.get(k)] if isinstance(v, dict)]
    sizes += [p.get('file_size') or 0 for p in message.get('photo') or [] if isinstance(p, dict)]
    return 'too_big' if any(isinstance(s, int) and s > MAX_BYTES for s in sizes) else None


def _create_topic(api, store, team, user, lang):
    result = api('createForumTopic', {'chat_id': team, 'name': topic_title(user, lang)})
    thread = result['result']['message_thread_id']
    store.update(user['id'], thread_id=thread, lang=lang, status='open')
    return thread


def ensure_topic(api, store, team, user, lang):
    row = store.get(user['id'])
    if row and row.get('thread_id'):
        if row['status'] == 'closed':
            try:
                api('reopenForumTopic', {'chat_id': team, 'message_thread_id': row['thread_id']})
            except APIError as error:
                if error.code == 401:
                    raise
                if error.code == 400:
                    return _create_topic(api, store, team, user, lang)
            store.update(user['id'], status='open')
        return row['thread_id']
    return _create_topic(api, store, team, user, lang)


def _age(seconds):
    t = TEXTS['team']
    hours = int(seconds // HOUR)
    return t['days'].format(n=hours // 24) if hours >= 48 else t['hours'].format(n=max(hours, 1))


def _lines(team, rows, at):
    return [TEXTS['team']['line'].format(link=topic_link(team, r['thread_id']), age=_age(at - r['waiting_since'])) for r in rows]


# ---------------------------------------------------------------- Nutzerseite
def handle_private(api, message, base):
    user = message.get('from') or {}
    chat_id = (message.get('chat') or {}).get('id')
    if not isinstance(user.get('id'), int) or not isinstance(chat_id, int):
        return
    uid, lang = user['id'], lang_of(user)
    t = TEXTS[lang]
    team = team_chat_id()
    try:
        store = Store() if team is not None else None    # Relay aus: nichts speichern, nur Hinweis
        row = store.get(uid) if store else None
    except (sqlite3.Error, OSError):
        store, row = None, None
    if row and row['blocked']:
        return
    if team is None or store is None:
        safe(api, 'sendMessage', {'chat_id': chat_id, 'text': t['unavailable']})
        return
    row = row or {}
    if is_entry(message):
        safe(api, 'sendMessage', {'chat_id': chat_id, 'text': t['welcome'], 'reply_markup': info_markup(base, lang)})
        return
    at = now()
    if store.recent(uid, at - HOUR) >= MAX_PER_HOUR:
        if (row.get('limit_notice_at') or 0) < at - HOUR:
            safe(api, 'sendMessage', {'chat_id': chat_id, 'text': t['rate']})
            store.update(uid, limit_notice_at=at)
        return
    problem = size_problem(message)
    if problem:
        safe(api, 'sendMessage', {'chat_id': chat_id, 'text': t[problem]})
        return
    try:
        thread = ensure_topic(api, store, team, user, lang)
        payload = {'chat_id': team, 'from_chat_id': chat_id, 'message_id': message['message_id'], 'message_thread_id': thread}
        try:
            api('copyMessage', payload)
        except APIError as error:
            if error.code != 400:
                raise
            payload['message_thread_id'] = thread = _create_topic(api, store, team, user, lang)   # Thema geloescht: einmal neu anlegen
            api('copyMessage', payload)
    except APIError as error:
        if error.code not in (400, 403):
            raise
        print('Support: team chat unavailable', error.code, flush=True)
        safe(api, 'sendMessage', {'chat_id': chat_id, 'text': t['unavailable']})
        return
    store.add_event(uid, at)
    row = store.get(uid) or {}
    store.update(uid, last_user_at=at, lang=lang, status='open',
                 waiting_since=row.get('waiting_since') if row.get('status') == 'open' and row.get('waiting_since') else at)
    facts, sensitive = detect(message.get('text') or message.get('caption') or '')
    if facts and not sensitive:
        safe(api, 'sendMessage', {'chat_id': chat_id, 'text': fact_answer(facts, lang), 'reply_markup': info_markup(base, lang)})
        topics = ', '.join(TEXTS['team'][k] for k in FACT_ORDER if k in facts)
        safe(api, 'sendMessage', {'chat_id': team, 'message_thread_id': thread, 'text': TEXTS['team']['auto_note'].format(topics=topics)})
    elif (row.get('last_ack_at') or 0) < at - ACK_EVERY:
        safe(api, 'sendMessage', {'chat_id': chat_id, 'text': t['ack'], 'reply_markup': info_markup(base, lang)})
        store.update(uid, last_ack_at=at)


# ---------------------------------------------------------------- Teamseite
def handle_team(api, message):
    team = team_chat_id()
    if team is None or (message.get('chat') or {}).get('id') != team:
        return
    sender, sender_chat = message.get('from') or {}, message.get('sender_chat')
    if sender_chat is not None:
        if (sender_chat or {}).get('id') != team:       # nur anonyme Admins dieser Gruppe, kein verknuepfter Kanal
            return
    elif sender.get('is_bot') or not isinstance(sender.get('id'), int):
        return
    if any(k in message for k in SERVICE_KEYS):
        return
    command, _ = command_of(message.get('text'))
    thread = message.get('message_thread_id') if message.get('is_topic_message') else None
    tt = TEXTS['team']
    store = Store()
    if command == '/offen':
        rows = store.waiting()
        text = '\n'.join([tt['open_head']] + _lines(team, rows, now())) if rows else tt['open_none']
        payload = {'chat_id': team, 'text': text}
        if thread:
            payload['message_thread_id'] = thread
        safe(api, 'sendMessage', payload)
        return
    if not thread:
        return
    row = store.by_thread(thread)
    if not row:
        return
    note = {'chat_id': team, 'message_thread_id': thread}
    if command == '/sperren':
        store.update(row['user_id'], blocked=1)
        safe(api, 'sendMessage', dict(note, text=tt['blocked']))
        return
    if command == '/entsperren':
        store.update(row['user_id'], blocked=0)
        safe(api, 'sendMessage', dict(note, text=tt['unblocked']))
        return
    if command == '/schliessen':
        store.update(row['user_id'], status='closed', waiting_since=None)
        safe(api, 'sendMessage', dict(note, text=tt['closed']))
        safe(api, 'closeForumTopic', {'chat_id': team, 'message_thread_id': thread})
        return
    if command:
        return                                           # andere Befehle bleiben intern
    try:
        api('copyMessage', {'chat_id': row['user_id'], 'from_chat_id': team, 'message_id': message['message_id']})
    except APIError as error:
        if error.code not in (400, 403):
            raise
        safe(api, 'sendMessage', dict(note, text=tt['not_delivered']))
        return
    fields = {'last_team_at': now(), 'waiting_since': None}
    if row['status'] != 'closed':
        fields['status'] = 'answered'
    store.update(row['user_id'], **fields)


# ---------------------------------------------------------------- Digest (aus der Poll-Schleife, hoechstens 1 x je 24 h)
def digest_text(at=None):
    team = team_chat_id()
    at = now() if at is None else at
    if team is None:
        return None
    rows = Store().waiting(older_than=at - DAY)
    if not rows:
        return None
    return '\n'.join([TEXTS['team']['digest_head'].format(n=len(rows))] + _lines(team, rows, at))


def maybe_digest(api):
    if os.environ.get('ELEMENTS_SUPPORT_DIGEST', '').strip() != '1':
        return None        # Erinnerung standardmaessig AUS (Eddy 25.10.2026); nur mit ELEMENTS_SUPPORT_DIGEST=1
    team = team_chat_id()
    if team is None:
        return None
    store, at = Store(), now()
    if at - (store.meta('digest_at') or 0) < DAY:
        return None
    text = digest_text(at)
    if not text:
        return None
    try:
        api('sendMessage', {'chat_id': team, 'text': text})
    except APIError as error:
        print('Support: digest deferred', error.code, flush=True)
        store.meta('digest_at', at - DAY + HOUR)          # naechster Versuch in einer Stunde
        return None
    store.meta('digest_at', at)
    return text


def poll_tick(api):
    try:
        return maybe_digest(api)
    except Exception as error:  # noqa: BLE001 - Hintergrundaufgabe darf die Poll-Schleife nie anhalten
        print('Support: digest skipped', type(error).__name__, flush=True)
        return None


# ---------------------------------------------------------------- Beitrittsanfragen und Rollenfrage
def handle_join_request(api, request, base):
    group = group_chat_id()
    if group is None or (request.get('chat') or {}).get('id') != group:
        return
    user = request.get('from') or {}
    if not isinstance(user.get('id'), int):
        return
    target = request.get('user_chat_id') if isinstance(request.get('user_chat_id'), int) else user['id']
    try:
        count_invite((request.get('invite_link') or {}).get('name'), 'requests')
    except (sqlite3.Error, OSError):
        pass
    lang = lang_of(user)
    t = TEXTS[lang]
    rows = [[{'text': t['b_shop'], 'web_app': {'url': web_url(base, '/')}}]] if base else []
    rows.append([{'text': t['b_role_h'], 'callback_data': 'role_h'}, {'text': t['b_role_e'], 'callback_data': 'role_e'}])
    safe(api, 'sendMessage', {'chat_id': target, 'text': t['join'], 'reply_markup': {'inline_keyboard': rows}})
    safe(api, 'approveChatJoinRequest', {'chat_id': group, 'user_id': user['id']})


def handle_chat_member(update):
    group = group_chat_id()
    if group is None or (update.get('chat') or {}).get('id') != group:
        return
    old, new = (update.get('old_chat_member') or {}).get('status'), (update.get('new_chat_member') or {}).get('status')
    if old in ('left', 'kicked') and new in ('member', 'restricted'):
        try:
            count_invite((update.get('invite_link') or {}).get('name'), 'joins')
        except (sqlite3.Error, OSError):
            pass


def handle_role(api, query):
    user = query.get('from') or {}
    chat = (query.get('message') or {}).get('chat') or {}
    if query.get('data') not in ('role_h', 'role_e') or chat.get('type') != 'private' or not isinstance(user.get('id'), int):
        return
    lang = lang_of(user)
    team = team_chat_id()
    if team is not None:
        try:
            store = Store()
            row = store.get(user['id'])
            if row and row['blocked']:
                return
            thread = ensure_topic(api, store, team, user, lang)
            role = TEXTS['de']['b_role_h' if query['data'] == 'role_h' else 'b_role_e']
            safe(api, 'sendMessage', {'chat_id': team, 'message_thread_id': thread, 'text': TEXTS['team']['role_note'].format(role=role)})
        except APIError as error:
            if error.code == 401:
                raise
            print('Support: role note skipped', error.code, flush=True)
        except (sqlite3.Error, OSError):
            print('Support: role note skipped (storage)', flush=True)
    safe(api, 'sendMessage', {'chat_id': chat['id'], 'text': TEXTS[lang]['role_thanks']})
