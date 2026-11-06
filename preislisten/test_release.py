#!/usr/bin/env python3
"""Tests fuer release.py (unittest). Arbeitet nur in Wegwerfkopien unter ~/.hermes/cache/scratch, nie in Live oder Staging.

Aufruf:  python3 preislisten/test_release.py -v
"""
import sys
sys.dont_write_bytecode = True
import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import release as R  # noqa: E402

STG = Path(os.environ.get('RELEASE_STAGING', Path.home() / 'Projekte-Mac/elements-lab-telegram-staging'))
SCRATCH = Path.home() / '.hermes/cache/scratch'
DATA_FILES = ['preislisten/preisfamilie_v3.csv', 'preislisten/preisfamilie_v3_shopzuordnung.csv', 'preislisten/ausnahmen_v3.csv',
              'miniapp/data/products.json', 'miniapp/data/shop-formats.json', 'miniapp/data/catalog-packs.json']


def tree_sha(root):
    return {f: R.sha_file(Path(root) / f) for f in R.walk(root)}


class Sandbox(unittest.TestCase):
    """Wegwerfkopie des Staging-Datenbaums (nur Preisdaten + Mini-public)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='test-release-', dir=str(SCRATCH)))
        self.stg = self.tmp / 'stg'
        for rel in DATA_FILES:
            (self.stg / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(STG / rel, self.stg / rel)
        (self.stg / 'miniapp/public').mkdir(parents=True)
        (self.stg / 'miniapp/public/index.html').write_text('<html>Elements</html>')
        self.dec = self.tmp / 'entscheidungen.json'
        d = json.loads((HERE / 'entscheidungen_eddy.json').read_text())
        for k in R.DECISION_KEYS:
            d[k] = True
        self.dec.write_text(json.dumps(d))
        self.ctx = R.Ctx(stg=self.stg, live=self.tmp / 'live', entscheidungen=self.dec, backup_root=self.tmp / 'backup',
                         stg_url='http://127.0.0.1:9', live_url='http://127.0.0.1:9')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fake_gate(self, **over):
        g = dict(status='gruen', exit=0, teil_gate=None, zeit_epoch=time.time(), datenhash=R.datenhash(self.stg)['hash'],
                 entscheidungen_sha=R.sha_file(self.dec))
        g.update(over)
        self.ctx.gate_dir.mkdir(parents=True, exist_ok=True)
        (self.ctx.gate_dir / 'GATE.json').write_text(json.dumps(g))


class TestDatenhash(Sandbox):
    def test_hash_stabil_und_unabhaengig_von_mtime(self):
        a = R.datenhash(self.stg)['hash']
        self.assertEqual(a, R.datenhash(self.stg)['hash'])
        os.utime(self.stg / 'miniapp/data/products.json', (1, 1))
        self.assertEqual(a, R.datenhash(self.stg)['hash'])

    def test_hash_aendert_sich_bei_inhalt_und_public(self):
        a = R.datenhash(self.stg)['hash']
        (self.stg / 'miniapp/public/index.html').write_text('<html>anders</html>')
        b = R.datenhash(self.stg)['hash']
        self.assertNotEqual(a, b)
        p = self.stg / 'preislisten/preisfamilie_v3.csv'
        p.write_text(p.read_text().replace('70.90', '71.90', 1))
        self.assertNotEqual(b, R.datenhash(self.stg)['hash'])


class TestGateG1(Sandbox):
    def test_kopie_ist_gruen(self):
        err, cnt = R.compare_files(self.stg)
        self.assertEqual(err, [])
        self.assertEqual((cnt['einzel'], cnt['pack'], cnt['shop_only'], cnt['artikel']), (54, 340, 1, 396))

    def test_manipulierter_preis_macht_gate_rot(self):
        p = self.stg / 'miniapp/data/catalog-packs.json'
        d = json.loads(p.read_text())
        d[5]['price_cents'] += 1000
        p.write_text(json.dumps(d))
        g = R.run_gate(self.ctx, only={'G1'}, write=False)
        self.assertEqual(g['status'], 'rot')
        self.assertEqual(g['exit'], 1)
        self.assertTrue(any('Preis falsch' in b for b in g['checks'][0]['belege']), g['checks'][0]['belege'][:5])

    def test_manipulierter_einzelpreis_und_dualpack(self):
        p = self.stg / 'miniapp/data/shop-formats.json'
        d = json.loads(p.read_text())
        for x in d:
            if x['id'] == 'dual-bpc-157-tb-500-x10':
                x['price_cents'] = 54000
        p.write_text(json.dumps(d))
        err, _ = R.compare_files(self.stg)
        self.assertTrue(any('dual-bpc-157-tb-500-x10' in e for e in err), err)

    def test_teil_gate_gibt_nie_frei(self):
        g = R.run_gate(self.ctx, only={'G1'}, write=False)
        self.assertEqual(g['status'], 'gelb')
        self.assertNotEqual(g['exit'], 0)


class TestLeak(Sandbox):
    def test_herstellername_und_ek_feld_werden_gefunden(self):
        (self.stg / 'miniapp/public/app.js').write_text('var a = "Ting"; var ek_je = 1; var t = "\u4e2d\u6587";')
        c = R.g5_leaks(self.ctx)
        self.assertEqual(c['status'], 'rot')
        labels = ' '.join(c['belege'])
        for w in ('Herstellername', 'EK-Feld', 'chinesische Zeichen'):
            self.assertIn(w, labels)


class TestPromoteSperren(Sandbox):
    def test_gruenes_frisches_gate_gibt_frei(self):
        self.fake_gate()
        self.assertEqual(R.promote_blockers(self.ctx), [])

    def test_offene_entscheidung_blockiert(self):
        d = json.loads(self.dec.read_text())
        d['e2_reta60_ausnahme'] = None
        self.dec.write_text(json.dumps(d))
        self.fake_gate()
        b = R.promote_blockers(self.ctx)
        self.assertTrue(any('offene Entscheidungen' in x for x in b), b)

    def test_abgelaufenes_gate_blockiert(self):
        self.fake_gate(zeit_epoch=time.time() - 2 * 3600 - 60)
        b = R.promote_blockers(self.ctx)
        self.assertTrue(any('min alt' in x for x in b), b)

    def test_anderer_datenhash_blockiert(self):
        self.fake_gate()
        (self.stg / 'miniapp/public/index.html').write_text('<html>neu gebaut</html>')
        self.assertTrue(any('Datenhash' in x for x in R.promote_blockers(self.ctx)))

    def test_rotes_gate_und_geaenderte_entscheidung_blockieren(self):
        self.fake_gate(status='gelb', exit=2)
        self.assertTrue(any('Gate ist gelb' in x for x in R.promote_blockers(self.ctx)))
        self.fake_gate()
        self.dec.write_text(self.dec.read_text() + ' ')
        self.assertTrue(any('seit dem Gate geaendert' in x for x in R.promote_blockers(self.ctx)))

    def test_kein_gate_blockiert(self):
        self.assertTrue(R.promote_blockers(self.ctx))

    def test_cli_promote_ohne_freigabe_und_trockenlauf_kopiert_nichts(self):
        live = self.tmp / 'live'
        (live / 'miniapp/data').mkdir(parents=True)
        (live / 'miniapp/data/products.json').write_text('[]')
        before = tree_sha(live)

        class A:
            freigabe_eddy = False
            trockenlauf = True
        self.assertEqual(R.cmd_promote(self.ctx, A), 2)
        A.freigabe_eddy = True
        self.assertEqual(R.cmd_promote(self.ctx, A), 3)   # kein Gate -> blockiert, aber Plan gelistet
        self.assertEqual(before, tree_sha(live))


class TestRollback(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='test-rollback-', dir=str(SCRATCH)))
        self.live, self.stg = self.tmp / 'live', self.tmp / 'stg'
        for root, txt in ((self.live, 'alt'), (self.stg, 'neu')):
            (root / 'miniapp/data').mkdir(parents=True)
            (root / 'miniapp/data/products.json').write_text(f'[{txt}]')
            (root / 'miniapp/public').mkdir(parents=True)
            (root / 'miniapp/public/app.js').write_text(f'// {txt}')
        (self.stg / 'miniapp/public/neu.js').write_text('// nur im Staging')
        (self.stg / 'preislisten').mkdir()
        (self.stg / 'preislisten/pipeline_alles.sh').write_text('cd ~/Projekte-Mac/elements-lab-telegram-staging/miniapp')
        (self.live / 'miniapp/runtime').mkdir()
        (self.live / 'miniapp/runtime/.env.elements').write_text('X=1')
        self.before = tree_sha(self.live)
        self.restarts = []

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def plan(self):
        p = R.diff_plan(self.stg, self.live)
        self.assertEqual(sorted(x['datei'] for x in p), ['miniapp/data/products.json', 'miniapp/public/app.js', 'miniapp/public/neu.js',
                                                         'preislisten/pipeline_alles.sh'])
        return p

    def test_erfolg_kopiert_und_schreibt_pfade_um(self):
        rep = R.promote_core(self.stg, self.live, self.plan(), self.tmp / 'bak', lambda: self.restarts.append(1), lambda: dict(ok=True), log=lambda *_: None)
        self.assertEqual(rep['ergebnis'], 'live')
        self.assertEqual((self.live / 'miniapp/data/products.json').read_text(), '[neu]')
        self.assertIn('elements-lab-telegram/miniapp', (self.live / 'preislisten/pipeline_alles.sh').read_text())
        self.assertNotIn('staging', (self.live / 'preislisten/pipeline_alles.sh').read_text())
        self.assertEqual((self.live / 'miniapp/runtime/.env.elements').read_text(), 'X=1')
        self.assertEqual(self.restarts, [1])
        self.assertEqual(R.diff_plan(self.stg, self.live), [])

    def test_probe_rot_fuehrt_zu_rollback_bytegleich(self):
        calls = []

        def probe():
            calls.append(1)
            return dict(ok=len(calls) > 1, fehler=['simuliert'])
        rep = R.promote_core(self.stg, self.live, self.plan(), self.tmp / 'bak', lambda: self.restarts.append(1), probe, log=lambda *_: None)
        self.assertEqual(rep['ergebnis'], 'rollback')
        self.assertTrue(rep['rollback_bytegleich'])
        self.assertEqual(self.before, tree_sha(self.live))
        self.assertFalse((self.live / 'miniapp/public/neu.js').exists())
        self.assertEqual(len(self.restarts), 2)   # Neustart nach Kopie und nach Rollback

    def test_kopierfehler_fuehrt_zu_rollback(self):
        rep = R.promote_core(self.stg, self.live, self.plan(), self.tmp / 'bak', lambda: self.restarts.append(1), lambda: dict(ok=True),
                             log=lambda *_: None, fail_copy_after=2)
        self.assertEqual(rep['ergebnis'], 'rollback')
        self.assertIn('simulierter Kopierfehler', rep['fehler'])
        self.assertEqual(self.before, tree_sha(self.live))
        self.assertEqual(list(self.live.rglob('*.release-tmp')), [])

    def test_rollback_scheitert_wird_gemeldet(self):
        rep = R.promote_core(self.stg, self.live, self.plan(), self.tmp / 'bak', lambda: None, lambda: dict(ok=False), log=lambda *_: None)
        self.assertEqual(rep['ergebnis'], 'rollback_fehlgeschlagen')   # Probe auch nach Rollback rot -> laut melden
        self.assertTrue(rep['rollback_bytegleich'])

    def test_runtime_und_env_nie_im_plan(self):
        (self.stg / 'miniapp/runtime').mkdir()
        (self.stg / 'miniapp/runtime/.env.elements').write_text('Y=2')
        (self.stg / 'miniapp/.tests_ok').write_text('1')
        self.assertFalse(any('runtime' in p['datei'] or '.env' in p['datei'] or 'tests_ok' in p['datei'] for p in R.diff_plan(self.stg, self.live)))

    def test_simulation_cli_beruehrt_live_nicht(self):
        ctx = R.Ctx(stg=self.stg, live=self.live, entscheidungen=HERE / 'entscheidungen_eddy.json', backup_root=self.tmp / 'bak')
        rep = R.simulate_rollback(ctx, R.diff_plan(self.stg, self.live), log=lambda *_: None)
        self.assertEqual(rep['ergebnis'], 'rollback')
        self.assertTrue(rep['live_bytegleich_wie_vorher'])
        self.assertEqual(self.before, tree_sha(self.live))
        shutil.rmtree(rep['sandbox'], ignore_errors=True)


class TestEntscheidungen(unittest.TestCase):
    def test_erwartungen_aus_entscheidungen(self):
        d = json.loads((HERE / 'entscheidungen_eddy.json').read_text())
        exp, offen = R.vorgaben_expectation(d)
        self.assertEqual(sorted(offen), ['e1_motsc_alte_liste', 'e2_reta60_ausnahme'])   # e3 hat keinen Test, wird separat geprueft
        d.update(e1_motsc_alte_liste=False, e2_reta60_ausnahme=True)
        exp, offen = R.vorgaben_expectation(d)
        self.assertEqual(offen, [])
        self.assertEqual(exp['test_P7_fokus_vial_packs_nicht_unter_alter_liste'], {'pack/vial Retatrutide 60 mg'})
        self.assertEqual(len(exp['test_P7x_mots_c_vial_packs_auslegung']), 3)


if __name__ == '__main__':
    unittest.main()
