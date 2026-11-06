"""Kontakt-/Support-Relay (support.py): Einstieg, Team-Themen, Auto-Antworten aus data/terms.json, Missbrauchsschutz, Digest,
Beitrittsanfragen. Telegram-API ist durchgehend gestubbt (keine Netzaufrufe, kein Token).
Laeuft nur, wenn support.py im Paket liegt (Renes Code-Paket fuehrt es nicht zwingend)."""
import importlib.util
import json
import os
import re
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HAS_SUPPORT = (ROOT / 'support.py').is_file()
sys.path.insert(0, str(ROOT))
TEAM = -1001234567890
GROUP = -1009876543210
BASE = 'https://x.trycloudflare.com'


def load_bot():
    spec = importlib.util.spec_from_file_location('support_bot', ROOT / 'bot.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeAPI:
    """Nimmt Aufrufe auf; fail[method] = Code oder Funktion(payload) -> Code/None."""
    def __init__(self, bot):
        self.bot, self.calls, self.fail, self.thread, self.mid = bot, [], {}, 500, 1000

    def __call__(self, _token, method, payload=None, timeout=40):
        payload = payload or {}
        self.calls.append((method, payload))
        rule = self.fail.get(method)
        code = rule(payload) if callable(rule) else rule
        if code:
            raise self.bot.BotAPIError(code)
        if method == 'createForumTopic':
            self.thread += 1
            return {'ok': True, 'result': {'message_thread_id': self.thread, 'name': payload['name']}}
        if method in ('sendMessage', 'copyMessage'):
            self.mid += 1
            return {'ok': True, 'result': {'message_id': self.mid}}
        if method == 'createChatInviteLink':
            return {'ok': True, 'result': {'invite_link': 'https://t.me/+abc' + payload['name'][:3], 'name': payload['name'],
                                           'creates_join_request': payload.get('creates_join_request', False)}}
        return {'ok': True, 'result': True}

    def of(self, method):
        return [p for m, p in self.calls if m == method]

    def clear(self):
        self.calls.clear()


def user_msg(text=None, uid=77, lang='de', first='Anna', username='anna_h', mid=5, **extra):
    m = {'message_id': mid, 'chat': {'id': uid, 'type': 'private'}, 'from': {'id': uid, 'is_bot': False, 'first_name': first, 'language_code': lang}}
    if username:
        m['from']['username'] = username
    if text is not None:
        m['text'] = text
    m.update(extra)
    return m


def team_msg(text, thread, chat=TEAM, sender=None, mid=900, **extra):
    m = {'message_id': mid, 'chat': {'id': chat, 'type': 'supergroup', 'is_forum': True}, 'from': sender or {'id': 5, 'is_bot': False, 'first_name': 'Team'},
         'message_thread_id': thread, 'is_topic_message': True, 'text': text}
    m.update(extra)
    return m


WHEN = ('sobald wir können', 'as soon as we can', 'dès que possible')      # Eddy 25.10.2026: keine feste Antwortzeit versprechen


@unittest.skipUnless(HAS_SUPPORT, 'support.py nicht im Paket')
class RelayBase(unittest.TestCase):
    def setUp(self):
        self.bot = load_bot()
        self.support = self.bot.support
        self.tmp = tempfile.TemporaryDirectory(dir=Path.home() / '.hermes/cache/scratch')
        self.root = Path(self.tmp.name)
        (self.root / 'runtime').mkdir()
        self.clock = [1_800_000_000.0]
        self.api = FakeAPI(self.bot)
        for p in (patch.object(self.bot, 'ROOT', self.root), patch.object(self.support, 'ROOT', self.root),
                  patch.object(self.support, 'now', lambda: self.clock[0]), patch.object(self.bot, 'call', self.api)):
            p.start()
            self.addCleanup(p.stop)
        self.env = patch.dict(os.environ, {'ELEMENTS_TEAM_CHAT_ID': str(TEAM)})
        self.env.start()
        self.addCleanup(self.env.stop)
        os.environ.pop('ELEMENTS_GROUP_CHAT_ID', None)
        self.addCleanup(self.tmp.cleanup)

    def send(self, message, base=BASE):
        self.bot.handle('t', message, base)

    def texts(self, chat_id):
        return [p['text'] for p in self.api.of('sendMessage') if p['chat_id'] == chat_id]

    def advance(self, seconds):
        self.clock[0] += seconds


class EntryAndFailClosed(RelayBase):
    def test_kontakt_command_and_deep_link_greet_in_user_language(self):
        for text, lang, needle in (('/kontakt', 'de', 'Schreib uns deine Frage'), ('/start kontakt', 'de', 'Schreib uns deine Frage'),
                                   ('/kontakt@ElementsLabsShop_bot', 'en', 'Write us your question'), ('/start kontakt', 'fr', 'Écris-nous ta question'),
                                   ('/kontakt', 'it', 'Schreib uns deine Frage')):
            with self.subTest(text=text, lang=lang):
                self.api.clear()
                self.send(user_msg(text, lang=lang))
                body = self.texts(77)
                self.assertEqual(len(body), 1)
                self.assertIn(needle, body[0])
                self.assertTrue(any(w in body[0] for w in WHEN), body[0])
                self.assertNotIn('24-48', body[0])
                self.assertEqual(self.api.of('createForumTopic'), [])   # Thema erst mit der ersten echten Nachricht
        self.assertIn('kontakt', [c['command'] for c in self.bot.COMMANDS])
        self.assertIn('/kontakt', self.bot.reply_for('/hilfe')[0])

    def test_without_team_chat_the_relay_is_off_and_says_so(self):
        for value in (None, '', 'abc', '12; DROP'):
            with self.subTest(value=value):
                self.api.clear()
                if value is None:
                    os.environ.pop('ELEMENTS_TEAM_CHAT_ID', None)
                else:
                    os.environ['ELEMENTS_TEAM_CHAT_ID'] = value
                self.send(user_msg('/kontakt'))
                self.send(user_msg('Hallo, ich habe eine Frage'))
                self.assertEqual([m for m, _ in self.api.calls], ['sendMessage', 'sendMessage'])
                for text in self.texts(77):
                    self.assertIn('Kontakt ist gerade nicht verfügbar, bitte schreibe später', text)

    def test_existing_commands_still_work_and_group_chatter_is_ignored(self):
        self.send(user_msg('/shop'))
        self.assertEqual(self.api.of('createForumTopic'), [])
        self.api.clear()
        self.send({'message_id': 1, 'chat': {'id': -100555, 'type': 'supergroup'}, 'from': {'id': 3, 'is_bot': False}, 'text': 'hallo'})
        self.assertEqual(self.api.calls, [])


class TopicsAndTeamReplies(RelayBase):
    def test_one_topic_per_user_and_messages_are_copied_not_stored(self):
        secret = 'Meine geheime Nachricht 4711'
        self.send(user_msg(secret))
        self.send(user_msg(None, mid=6, photo=[{'file_id': 'x', 'file_size': 1000}], caption='Noch etwas'))
        topics = self.api.of('createForumTopic')
        self.assertEqual(len(topics), 1)
        self.assertEqual(topics[0]['chat_id'], TEAM)
        self.assertIn('Anna', topics[0]['name'])
        self.assertIn('@anna_h', topics[0]['name'])
        self.assertNotIn('77', topics[0]['name'])
        copies = self.api.of('copyMessage')
        self.assertEqual([(c['chat_id'], c['from_chat_id'], c['message_id'], c['message_thread_id']) for c in copies],
                         [(TEAM, 77, 5, self.api.thread), (TEAM, 77, 6, self.api.thread)])
        raw = b''.join(p.read_bytes() for p in (self.root / 'runtime').glob('support.sqlite3*'))
        self.assertNotIn(secret.encode(), raw)
        self.assertNotIn(b'Anna', raw)
        db = sqlite3.connect(self.root / 'runtime/support.sqlite3')
        cols = {r[1] for r in db.execute('PRAGMA table_info(topics)')}
        db.close()
        self.assertLessEqual(cols, {'user_id', 'thread_id', 'lang', 'status', 'blocked', 'created_at', 'last_user_at', 'last_team_at',
                                    'waiting_since', 'last_ack_at', 'limit_notice_at'})

    def test_topic_title_never_carries_a_phone_number(self):
        self.send(user_msg('Hallo', first='+49 170 1234567', username=None))
        name = self.api.of('createForumTopic')[0]['name']
        self.assertNotRegex(name, r'\d{5}')
        self.assertLessEqual(len(name), 128)

    def test_team_reply_in_topic_goes_back_to_the_user(self):
        self.send(user_msg('Hallo'))
        thread = self.api.thread
        self.api.clear()
        self.send(team_msg('Hallo Anna, gerne.', thread))
        self.assertEqual([(c['chat_id'], c['from_chat_id'], c['message_id']) for c in self.api.of('copyMessage')], [(77, TEAM, 900)])
        self.assertEqual(self.support.Store(self.root).get(77)['status'], 'answered')

    def test_replies_from_other_chats_bots_or_foreign_senders_are_not_relayed(self):
        self.send(user_msg('Hallo'))
        thread = self.api.thread
        self.api.clear()
        self.send(team_msg('fremd', thread, chat=-1001111111111))
        self.send(team_msg('bot', thread, sender={'id': 9, 'is_bot': True, 'first_name': 'X'}))
        self.send(team_msg('kanal', thread, sender_chat={'id': -1002222222222, 'type': 'channel'}))
        self.send(team_msg('/irgendwas', thread))
        self.send(team_msg('kein thema', None, is_topic_message=False))
        self.send(team_msg('', thread, forum_topic_created={'name': 'x'}))
        self.assertEqual(self.api.of('copyMessage'), [])
        self.send(team_msg('anonymer admin', thread, sender={'id': 1087968824, 'is_bot': True, 'first_name': 'Group'}, sender_chat={'id': TEAM, 'type': 'supergroup'}))
        self.assertEqual(len(self.api.of('copyMessage')), 1)

    def test_block_unblock_and_close(self):
        self.send(user_msg('Hallo'))
        thread = self.api.thread
        self.send(team_msg('/sperren', thread))
        self.api.clear()
        self.send(user_msg('Spam', mid=7))
        self.send(user_msg('/kontakt', mid=8))
        self.assertEqual(self.api.calls, [])          # gesperrt: still ignoriert
        self.send(team_msg('/entsperren', thread))
        self.api.clear()
        self.send(user_msg('Wieder da', mid=9))
        self.assertEqual(len(self.api.of('copyMessage')), 1)
        self.send(team_msg('/schliessen@ElementsLabsShop_bot', thread))
        self.assertEqual(self.api.of('closeForumTopic'), [{'chat_id': TEAM, 'message_thread_id': thread}])
        self.assertEqual(self.support.Store(self.root).get(77)['status'], 'closed')
        self.api.clear()
        self.send(user_msg('Neue Frage', mid=10))
        self.assertEqual(self.api.of('reopenForumTopic'), [{'chat_id': TEAM, 'message_thread_id': thread}])
        self.assertEqual(self.api.of('createForumTopic'), [])
        self.assertEqual(self.api.of('copyMessage')[0]['message_thread_id'], thread)

    def test_deleted_topic_is_recreated_once(self):
        self.send(user_msg('Hallo'))
        old = self.api.thread
        self.api.fail['copyMessage'] = lambda p: 400 if p.get('message_thread_id') == old else None
        self.send(user_msg('Noch da?', mid=6))
        self.assertEqual(len(self.api.of('createForumTopic')), 2)
        self.assertEqual(self.support.Store(self.root).get(77)['thread_id'], self.api.thread)

    def test_open_list_oldest_first(self):
        self.send(user_msg('Erste', uid=101, first='A'))
        t1 = self.api.thread
        self.advance(3600)
        self.send(user_msg('Zweite', uid=102, first='B'))
        t2 = self.api.thread
        self.advance(3600)
        self.send(user_msg('Dritte', uid=103, first='C'))
        t3 = self.api.thread
        self.send(team_msg('Antwort', t3))
        self.api.clear()
        self.send(team_msg('/offen', None, is_topic_message=False))
        text = self.texts(TEAM)[0]
        links = re.findall(r't\.me/c/(\d+)/(\d+)', text)
        self.assertEqual(links, [('1234567890', str(t1)), ('1234567890', str(t2))])
        self.api.clear()
        self.send(team_msg('/offen', None, chat=-1001111111111, is_topic_message=False))
        self.assertEqual(self.api.calls, [])


class Abuse(RelayBase):
    def test_rate_limit_twenty_per_hour_with_one_friendly_notice(self):
        for i in range(20):
            self.send(user_msg(f'Nachricht {i}', mid=100 + i))
        self.assertEqual(len(self.api.of('copyMessage')), 20)
        self.api.clear()
        self.send(user_msg('21', mid=200))
        self.send(user_msg('22', mid=201))
        self.assertEqual(self.api.of('copyMessage'), [])
        notices = self.texts(77)
        self.assertEqual(len(notices), 1)
        self.assertIn('Bitte warte', notices[0])
        self.advance(3601)
        self.api.clear()
        self.send(user_msg('neue Stunde', mid=202))
        self.assertEqual(len(self.api.of('copyMessage')), 1)

    def test_too_long_texts_and_big_files_are_refused_kindly(self):
        self.send(user_msg('x' * 4001))
        self.send(user_msg(None, mid=6, document={'file_id': 'd', 'file_size': 21 * 1024 * 1024}))
        self.send(user_msg(None, mid=7, forward_origin={'type': 'user'}, video={'file_id': 'v', 'file_size': 25 * 1024 * 1024}))
        self.send(user_msg(None, mid=8, caption='y' * 4001, photo=[{'file_id': 'p', 'file_size': 10}]))
        self.assertEqual(self.api.of('copyMessage'), [])
        self.assertEqual(self.api.of('createForumTopic'), [])
        refusals = self.texts(77)
        self.assertEqual(len(refusals), 4)
        self.assertTrue(all('4000' in t or '20 MB' in t for t in refusals))
        self.send(user_msg('x' * 4000, mid=9))
        self.assertEqual(len(self.api.of('copyMessage')), 1)

    def test_acknowledgement_at_most_once_per_twelve_hours(self):
        self.send(user_msg('Hallo zusammen'))
        self.send(user_msg('Noch eine Sache', mid=6))
        acks = self.texts(77)
        self.assertEqual(len(acks), 1)
        self.assertTrue(any(w in acks[0] for w in WHEN), acks[0])
        self.assertNotIn('24-48', acks[0])
        self.advance(12 * 3600 + 1)
        self.send(user_msg('Später', mid=7))
        self.assertEqual(len(self.texts(77)), 2)

    def test_user_who_blocked_the_bot_does_not_break_anything(self):
        self.send(user_msg('Hallo'))
        thread = self.api.thread
        self.api.fail['copyMessage'] = lambda p: 403 if p['chat_id'] == 77 else None
        self.api.clear()
        self.send(team_msg('Antwort', thread))
        notes = [p for p in self.api.of('sendMessage') if p['chat_id'] == TEAM]
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]['message_thread_id'], thread)
        self.assertIn('nicht zugestellt', notes[0]['text'])

    def test_poll_loop_survives_403_for_team_reply(self):
        self.send(user_msg('Hallo'))
        thread = self.api.thread
        polls = 0
        inner = self.api

        def call(token, method, payload=None, timeout=40):
            nonlocal polls
            if method == 'getUpdates':
                polls += 1
                if polls > 1:
                    raise KeyboardInterrupt
                return {'ok': True, 'result': [{'update_id': 300, 'message': team_msg('Antwort', thread)}]}
            if method == 'copyMessage':
                raise self.bot.BotAPIError(403)
            return inner(token, method, payload)
        with patch.object(self.bot, 'call', call), patch.dict(os.environ, {'ELEMENTS_TELEGRAM_BOT_TOKEN': 'SYNTHETIC'}):
            self.assertEqual(self.bot.main(), 0)
        self.assertEqual((self.root / 'runtime/bot-offset.txt').read_text(), '301')


def _allowed_numbers(terms):
    nums = {terms['min_order_cents'] // 100, terms['collective_min_cents'] // 100, terms['delivery_weeks']['min'], terms['delivery_weeks']['max'], 24, 48, 10}
    for t in terms['tiers']:
        nums |= {t['min_cents'] // 100, t['percent']}
    return nums


def _numbers(text):
    return {int(re.sub(r'[.,\s\u202f\u00a0]', '', n)) for n in re.findall(r'\d{1,3}(?:[.,\u202f\u00a0 ]\d{3})+|\d+', text)}


class AutoAnswers(RelayBase):
    QUESTIONS = {'min_order': 'Wie hoch ist der Mindestbestellwert?', 'shipping': 'Was kostet der Versand?', 'delivery': 'Wie ist die Lieferzeit?',
                 'discount': 'Gibt es Rabatt?', 'pricelist': 'Habt ihr eine Preisliste?', 'collective': 'Geht eine Sammelbestellung?'}

    def answer_for(self, text, lang='de', uid=77):
        self.api.clear()
        self.send(user_msg(text, lang=lang, uid=uid))
        return self.texts(uid), [p for p in self.api.of('sendMessage') if p['chat_id'] == uid]

    def test_intents_are_deterministic(self):
        d = self.support.detect
        for intent, q in self.QUESTIONS.items():
            self.assertEqual(d(q), ({intent}, False), q)
        self.assertEqual(d('minimum order and shipping?'), ({'min_order', 'shipping'}, False))
        self.assertEqual(d('Quel est le délai de livraison ?')[0] & {'delivery'}, {'delivery'})
        for q in ('Wie rein ist das?', 'Woher kommt die Ware, Herkunft?', 'Do you accept PayPal?', 'Ist das legal?', 'Seid ihr zuverlässig?',
                  'Welche Zahlung geht? Und Versand?', 'Quelle est la pureté ?', 'Habt ihr Analysen zur Charge?'):
            self.assertTrue(d(q)[1], q)
        self.assertEqual(d('Hallo, wie geht es?'), (set(), False))

    def test_fact_answers_use_terms_json_values_only(self):
        terms = self.support.load_terms()
        allowed = _allowed_numbers(terms)
        for lang in ('de', 'en', 'fr'):
            for n, (intent, q) in enumerate(self.QUESTIONS.items()):
                with self.subTest(lang=lang, intent=intent):
                    texts, payloads = self.answer_for(q, lang=lang, uid=1000 + n + (100 if lang == 'en' else 200 if lang == 'fr' else 0))
                    self.assertEqual(len(texts), 1)
                    self.assertLessEqual(_numbers(texts[0]), allowed, texts[0])
                    self.assertEqual(len(self.api.of('copyMessage')), 1)          # Frage geht zusaetzlich ans Team
        texts, _ = self.answer_for(self.QUESTIONS['min_order'], uid=2001)
        self.assertIn(self.support.eur(terms['min_order_cents'], 'de'), texts[0])
        texts, payloads = self.answer_for(self.QUESTIONS['discount'], uid=2002)
        for t in terms['tiers']:
            self.assertIn(f"{t['percent']} %", texts[0])
            self.assertIn(self.support.eur(t['min_cents'], 'de'), texts[0])
        self.assertIn('10er-Packs', texts[0])
        texts, payloads = self.answer_for(self.QUESTIONS['delivery'], uid=2003)
        self.assertIn(f"{terms['delivery_weeks']['min']} bis {terms['delivery_weeks']['max']} Wochen", texts[0])
        buttons = json.dumps(payloads[0]['reply_markup'])
        self.assertIn('pricelist', buttons)
        self.assertIn(BASE + '/', buttons)
        self.assertIn('?r=batch-lookup', buttons)
        self.assertIn('?r=quality', buttons)

    def test_answers_follow_a_changed_terms_file(self):
        changed = {'currency': 'EUR', 'min_order_cents': 70000, 'collective_min_cents': 30000, 'delivery_weeks': {'min': 4, 'max': 6},
                   'tiers': [{'min_cents': 300000, 'percent': 7}]}
        with patch.object(self.support, 'load_terms', lambda: changed):
            texts, _ = self.answer_for('Mindestbestellwert, Lieferzeit und Rabatt?', uid=3001)
        self.assertIn('700 €', texts[0])
        self.assertIn('300 €', texts[0])
        self.assertIn('4 bis 6 Wochen', texts[0])
        self.assertIn('7 % ab 3.000 €', texts[0])
        self.assertNotIn('500', texts[0])

    def test_sensitive_or_unclear_questions_get_no_claims(self):
        for n, q in enumerate(('Wie hoch ist die Reinheit?', 'Do you accept PayPal or crypto?', 'Ist das legal in Deutschland?', 'Woher kommt die Ware?',
                               'Welche Zahlungsarten und was kostet der Versand?')):
            with self.subTest(q=q):
                texts, payloads = self.answer_for(q, uid=4000 + n)
                self.assertEqual(len(texts), 1)
                self.assertIn('das beantwortet das Team persönlich', texts[0])
                self.assertEqual(_numbers(texts[0]) - {24, 48}, set(), texts[0])
                self.assertIn('?r=batch-lookup', json.dumps(payloads[0]['reply_markup']))
                self.assertEqual(len(self.api.of('copyMessage')), 1)
        texts, payloads = self.answer_for('Quelle est la pureté ?', lang='fr', uid=4100)
        self.assertIn('équipe', texts[0])

    def test_no_invented_claims_in_any_user_text(self):
        forbidden = re.compile(r'paypal|bitcoin|krypto|crypto|überweisung|virement|bank transfer|iban|zertifi|certifi|gmp|iso ?\d|garant|guarantee|'
                               r'\bkunden\b|customers|clients|referenz|reference|testimonial|99|100 ?%|legal|rechtlich|compliance|\b24/7\b', re.I)
        flat = json.dumps(self.support.TEXTS, ensure_ascii=False)
        self.assertEqual(forbidden.findall(flat), [])
        self.assertEqual(_numbers(flat) - {4000, 20, 24, 48, 10, 12}, set())       # keine Zahlen ausser Grenzen und Antwortzeit, Rest kommt aus terms.json


class Digest(RelayBase):
    def setUp(self):
        super().setUp()
        env = patch.dict(os.environ, {'ELEMENTS_SUPPORT_DIGEST': '1'})
        env.start()
        self.addCleanup(env.stop)

    def test_digest_is_off_by_default_and_no_fixed_reply_time_is_promised(self):
        with patch.dict(os.environ, {'ELEMENTS_SUPPORT_DIGEST': ''}):
            self.send(user_msg('Hallo'))
            self.advance(72 * 3600)
            self.api.clear()
            self.assertIsNone(self.support.maybe_digest(lambda m, p=None: self.api('t', m, p)))
            self.assertEqual(self.api.calls, [])
        self.assertNotIn('24-48', json.dumps(self.support.TEXTS, ensure_ascii=False))

    def test_digest_only_for_topics_older_than_a_day_and_at_most_daily(self):
        self.assertIsNone(self.support.digest_text())
        self.send(user_msg('Hallo'))
        self.advance(23 * 3600)
        self.api.clear()
        self.assertIsNone(self.support.maybe_digest(lambda m, p=None: self.api('t', m, p)))
        self.assertEqual(self.api.calls, [])
        self.advance(2 * 3600)
        text = self.support.maybe_digest(lambda m, p=None: self.api('t', m, p))
        self.assertIn('t.me/c/1234567890/', text)
        self.assertEqual([p['chat_id'] for p in self.api.of('sendMessage')], [TEAM])
        self.advance(3600)
        self.assertIsNone(self.support.maybe_digest(lambda m, p=None: self.api('t', m, p)))
        self.advance(24 * 3600)
        self.assertIsNotNone(self.support.maybe_digest(lambda m, p=None: self.api('t', m, p)))
        self.send(team_msg('Antwort', self.api.thread))
        self.advance(25 * 3600)
        self.assertIsNone(self.support.maybe_digest(lambda m, p=None: self.api('t', m, p)))

    def test_digest_runs_from_the_poll_loop_and_errors_never_stop_it(self):
        self.send(user_msg('Hallo'))
        self.advance(25 * 3600)
        polls, seen = 0, []
        inner = self.api

        def call(token, method, payload=None, timeout=40):
            nonlocal polls
            if method == 'getUpdates':
                seen.append(payload['allowed_updates'])
                polls += 1
                if polls > 2:
                    raise KeyboardInterrupt
                return {'ok': True, 'result': []}
            if method == 'sendMessage' and payload.get('chat_id') == TEAM and polls == 0:
                raise self.bot.BotAPIError(500)
            return inner(token, method, payload)
        with patch.object(self.bot, 'call', call), patch.dict(os.environ, {'ELEMENTS_TELEGRAM_BOT_TOKEN': 'SYNTHETIC'}):
            self.assertEqual(self.bot.main(), 0)
        self.assertIn('chat_join_request', seen[0])
        self.assertIn('message', seen[0])
        self.assertIn('callback_query', seen[0])


class JoinRequests(RelayBase):
    def request(self, chat=GROUP, link=None):
        r = {'chat': {'id': chat, 'type': 'supergroup'}, 'from': {'id': 555, 'is_bot': False, 'first_name': 'Neu', 'language_code': 'de'},
             'user_chat_id': 555, 'date': 1}
        if link:
            r['invite_link'] = {'invite_link': 'https://t.me/+x', 'name': link, 'creates_join_request': True}
        return r

    def run_update(self, update):
        polls = 0
        inner = self.api

        def call(token, method, payload=None, timeout=40):
            nonlocal polls
            if method == 'getUpdates':
                polls += 1
                if polls > 1:
                    raise KeyboardInterrupt
                return {'ok': True, 'result': [dict(update, update_id=700)]}
            return inner(token, method, payload)
        with patch.object(self.bot, 'call', call), patch.dict(os.environ, {'ELEMENTS_TELEGRAM_BOT_TOKEN': 'SYNTHETIC'}):
            self.assertEqual(self.bot.main(), 0)
        self.assertEqual((self.root / 'runtime/bot-offset.txt').read_text(), '701')

    def test_join_request_off_without_group_setting(self):
        self.run_update({'chat_join_request': self.request()})
        self.assertEqual(self.api.of('approveChatJoinRequest'), [])
        self.assertEqual(self.api.of('sendMessage'), [])

    def test_join_request_welcome_question_and_approval(self):
        os.environ['ELEMENTS_GROUP_CHAT_ID'] = str(GROUP)
        self.run_update({'chat_join_request': self.request(link='kanal-pin')})
        msg = self.api.of('sendMessage')[0]
        self.assertEqual(msg['chat_id'], 555)
        self.assertIn('Händler oder Endkunde?', msg['text'])
        markup = json.dumps(msg['reply_markup'])
        self.assertIn('role_h', markup)
        self.assertIn('role_e', markup)
        self.assertEqual(self.api.of('approveChatJoinRequest'), [{'chat_id': GROUP, 'user_id': 555}])
        self.assertEqual(self.support.invite_counts().get('kanal-pin', {}).get('requests'), 1)

    def test_join_request_errors_never_stop_polling(self):
        os.environ['ELEMENTS_GROUP_CHAT_ID'] = str(GROUP)
        self.api.fail['sendMessage'] = 403
        self.api.fail['approveChatJoinRequest'] = 400
        self.run_update({'chat_join_request': self.request()})
        self.assertEqual(len(self.api.of('approveChatJoinRequest')), 1)
        self.api.clear()
        self.api.fail.clear()
        self.run_update({'chat_join_request': self.request(chat=-1003333333333)})
        self.assertEqual(self.api.of('approveChatJoinRequest') + self.api.of('sendMessage'), [])

    def test_role_answer_is_only_noted_in_the_relay_topic(self):
        query = {'id': 'q', 'data': 'role_h', 'from': {'id': 555, 'first_name': 'Neu', 'language_code': 'de'}, 'message': {'chat': {'id': 555, 'type': 'private'}}}
        self.bot.handle_callback('t', query)
        notes = [p for p in self.api.of('sendMessage') if p['chat_id'] == TEAM]
        self.assertEqual(len(notes), 1)
        self.assertIn('Händler', notes[0]['text'])
        self.assertEqual(notes[0]['message_thread_id'], self.api.thread)
        self.assertTrue(any(p['chat_id'] == 555 for p in self.api.of('sendMessage')))
        raw = (self.root / 'runtime/support.sqlite3').read_bytes()
        self.assertNotIn('Händler'.encode(), raw)

    def test_members_joining_by_named_link_are_counted(self):
        os.environ['ELEMENTS_GROUP_CHAT_ID'] = str(GROUP)
        update = {'chat_member': {'chat': {'id': GROUP, 'type': 'supergroup'}, 'from': {'id': 1}, 'date': 1,
                                  'old_chat_member': {'status': 'left', 'user': {'id': 9}}, 'new_chat_member': {'status': 'member', 'user': {'id': 9}},
                                  'invite_link': {'invite_link': 'https://t.me/+y', 'name': 'insta'}}}
        self.run_update(update)
        self.assertEqual(self.support.invite_counts()['insta']['joins'], 1)


@unittest.skipUnless(HAS_SUPPORT, 'support.py nicht im Paket')
class WithoutSupportModule(unittest.TestCase):
    def test_bot_keeps_working_when_support_module_is_missing(self):
        bot = load_bot()
        calls = []
        with patch.object(bot, 'support', None), patch.object(bot, 'call', lambda t, m, p=None, timeout=40: calls.append((m, p)) or {'ok': True, 'result': {}}):
            bot.handle('t', {'chat': {'id': 1, 'type': 'private'}, 'text': 'hallo'}, BASE)
            self.assertEqual(calls, [])
            bot.handle('t', {'chat': {'id': 1, 'type': 'private'}, 'text': '/shop'}, BASE)
            self.assertEqual(calls[0][0], 'sendMessage')


RELEASE = next((p for p in (ROOT.parent / 'preislisten/release.py', Path.home() / 'Projekte-Mac/elements-lab-telegram/preislisten/release.py') if p.is_file()), None)


@unittest.skipUnless(HAS_SUPPORT and RELEASE, 'Release-Gate nicht im Paket')
class NoPurchaseTermsInBotCode(unittest.TestCase):
    """Gleiche Leak-Muster wie Release-Gate G5 (release.LEAK), angewandt auf den Bot-Code; bot.py-Alttexte ('Einkauf fuer Zwischenhaendler'
    = Kundenseite) stehen als ausdrueckliche Ausnahme."""
    ALT = ('Einkauf für Zwischenhändler', 'Händler-Einkauf', 'Hilfe zum Einkauf')

    def test_g5_patterns_on_bot_code(self):
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location('release_gate', RELEASE)   # nur lesen (Muster LEAK), nichts ausfuehren
        release = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(release)
        hits = []
        for name in ('support.py', 'bot.py', 'tools/invite_links.py', 'BOT_SUPPORT.md'):
            text = (ROOT / name).read_text()
            for alt in self.ALT if name == 'bot.py' else ():
                text = text.replace(alt, '')
            for label, rx in release.LEAK:
                if label == 'fremde Website':
                    continue          # api.telegram.org ist erlaubt, ist im Muster unter telegram.org nicht abgedeckt
                hits += [f'{name}: {label}: {m.group(0)}' for m in rx.finditer(text)]
        self.assertEqual(hits, [])
