import hashlib
import hmac
import importlib.util
import json
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import urlencode

ROOT=Path(__file__).resolve().parents[1]

class ServerContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=ROOT/'server.py'
        assert path.exists(), 'Real request handler missing'
        spec=importlib.util.spec_from_file_location('elements_server', path)
        assert spec is not None and spec.loader is not None
        cls.mod=importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=cls.mod
        spec.loader.exec_module(cls.mod)
        cls.mod.TERMS = cls.mod.relaxed()  # Altfaelle ohne Mindestwert/Versand; echte Konditionen: tests/test_terms.py

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path.home()/'.hermes/cache/scratch')
        self.db=Path(self.tmp.name)/'test.sqlite3'
        self.catalog=json.loads((ROOT/'data/products.json').read_text())
        self.body={'request_id':'test-request-001','items':[{'id':'bpc-157','quantity':2}],'research_confirmed':True}

    def tearDown(self):
        self.tmp.cleanup()

    def signed(self, **changes):
        pairs={'auth_date':str(int(time.time())),'user':json.dumps({'id':12345}),'query_id':'synthetic-test'}
        pairs.update(changes)
        key=hmac.new(b'WebAppData',b'synthetic-bot-key',hashlib.sha256).digest()
        check='\n'.join(f'{k}={v}' for k,v in sorted(pairs.items()))
        pairs['hash']=hmac.new(key,check.encode(),hashlib.sha256).hexdigest()
        return urlencode(pairs)

    def test_real_persistence_server_price_and_idempotency(self):
        response=self.mod.save_request(self.body,self.catalog,self.db,'preview')
        unit=next(p for p in self.catalog if p['id']=='bpc-157')['price_cents']
        self.assertEqual(response['total_cents'],2*unit)
        self.assertEqual(response['status'],'LOCAL_TEST_SAVED')
        self.assertEqual(self.mod.save_request(self.body,self.catalog,self.db,'preview')['id'],response['id'])
        with sqlite3.connect(self.db) as c:
            rows=c.execute('select payload from requests').fetchall()
        self.assertEqual(len(rows),1)
        self.assertEqual(json.loads(rows[0][0])['items'][0]['unit_price_cents'],unit)
        self.body['items'][0]['quantity']=3
        with self.assertRaises(ValueError):self.mod.save_request(self.body,self.catalog,self.db,'preview')

    def test_invalid_products_quantities_and_confirmation_never_write(self):
        invalid=[[],None,[{'id':'schott-dc','quantity':1}],[{'id':'missing','quantity':1}],[{'id':'bpc-157','quantity':True}],[{'id':'bpc-157','quantity':0}],[{'id':'bpc-157','quantity':100}],[{'id':'bpc-157','quantity':1.5}],[{'id':'bpc-157','quantity':1,'price_cents':1}]]
        for items in invalid:
            with self.subTest(items=items):
                self.body['items']=items
                with self.assertRaises(ValueError):self.mod.save_request(self.body,self.catalog,self.db,'preview')
        self.assertFalse(self.db.exists())
        self.body['items']=[{'id':'bpc-157','quantity':1}];self.body['research_confirmed']=False
        with self.assertRaises(ValueError):self.mod.save_request(self.body,self.catalog,self.db,'preview')
        self.assertFalse(self.db.exists())

    def test_retry_keeps_original_receipt_when_catalog_prices_change(self):
        first = self.mod.save_request(self.body, self.catalog, self.db, 'preview')
        product = next(p for p in self.catalog if p['id'] == 'bpc-157')
        product['price_cents'] += 100
        retry = self.mod.save_request(self.body, self.catalog, self.db, 'preview')
        self.assertEqual(retry['id'], first['id'])
        self.assertEqual(retry['total_cents'], 2 * (product['price_cents'] - 100))
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM requests').fetchone()[0], 1)

    def test_signed_rate_limit_keeps_idempotent_retries_and_private_db(self):
        import stat
        first = None
        for index in range(10):
            self.body['request_id'] = 'rate-request-' + str(index)
            result = self.mod.save_request(self.body, self.catalog, self.db, 'telegram', self.signed(), 'synthetic-bot-key')
            first = first or result['id']
        self.body['request_id'] = 'rate-request-10'
        with self.assertRaises(ValueError):
            self.mod.save_request(self.body, self.catalog, self.db, 'telegram', self.signed(), 'synthetic-bot-key')
        self.body['request_id'] = 'rate-request-0'
        self.assertEqual(self.mod.save_request(self.body, self.catalog, self.db, 'telegram', self.signed(), 'synthetic-bot-key')['id'], first)
        self.assertEqual(stat.S_IMODE(self.db.stat().st_mode), 0o600)

    def test_signed_telegram_identity_and_replay_expiry(self):
        self.assertEqual(self.mod.validate_init_data(self.signed(),'synthetic-bot-key')['id'],12345)
        for value in ['',self.signed()+'&user=bad',self.signed(auth_date='1'),self.signed(auth_date=str(int(time.time())+3600))]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):self.mod.validate_init_data(value,'synthetic-bot-key')
        with self.assertRaises(ValueError):self.mod.validate_init_data(self.signed(),'different-key')
        with self.assertRaises(ValueError):self.mod.save_request(self.body,self.catalog,self.db,'telegram',init_data='forged',bot_token='synthetic-bot-key')
        self.assertFalse(self.db.exists())
        result=self.mod.save_request(self.body,self.catalog,self.db,'telegram',init_data=self.signed(),bot_token='synthetic-bot-key')
        self.assertEqual(result['status'],'LOCAL_TEST_SAVED')

if __name__=='__main__':unittest.main()
