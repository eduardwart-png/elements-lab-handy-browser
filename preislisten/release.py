#!/usr/bin/env python3
"""release.py - Freigabeweg fuer den Elements-Shop: Gate -> Promote mit Rollback -> Live-Gegenprobe.

Nur Python-Standardbibliothek (QR-Dekodierung optional ueber cv2 im Team-Python).

  release.py status                         ein Bildschirm: Datenhash, Gate-Alter je Schritt, offene Entscheidungen, Live-Gesundheit
  release.py gate [--nur G1,G5]             nur lesend; Exit 0 nur wenn ALLES gruen und keine Entscheidung offen (1 = rot, 2 = gelb)
                                            schreibt <staging>/_out/gate/GATE.json + GATE.md
  release.py probe staging|live             Datenpruefung + HTTP-Probe (live: /health, Preise, Menueknopf -> Tunnel)
  release.py promote --freigabe-eddy [--trockenlauf]
                                            verlangt frisches gruenes Gate (<= 2 h, gleicher Datenhash, gleiche Entscheidungen),
                                            sichert Live, kopiert, startet neu, probe live; bei Fehler automatischer Rollback
                                            (Trockenlauf: nur Plan; mit RELEASE_SIMULATE_FAIL=1 Rollback-Beweis im Wegwerf-Ordner)
  release.py qa-stamp --blocker N --hoch N  setzt <staging>/_out/qa_stamp.json (vom Browser-QA-Lauf)
  release.py list-stamp                     setzt <staging>/_out/listen_stamp.json (nach dem Listenlauf)

Umgebung (fuer Tests): RELEASE_STAGING, RELEASE_LIVE, RELEASE_STAGING_URL, RELEASE_LIVE_URL, RELEASE_ENTSCHEIDUNGEN,
RELEASE_BACKUP_ROOT, RELEASE_SIMULATE_FAIL. Der Telegram-Token wird nur im Prozess gelesen und nie ausgegeben.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

HOME = Path.home()
TOOLDIR = Path(__file__).resolve().parent
SCRATCH = HOME / '.hermes/cache/scratch'
RESTART_PROBE = HOME / '.hermes/tools/elements-preis/live_restart_probe.py'   # dauerhaft, neu erstellt 28.10.2026
AUDIT_DIR = HOME / '.hermes/tools/elements-preis/controller2'   # dauerhaft (Scratch wird nach 24 h geleert, 28.10.2026)
TEAM_PY = HOME / '.hermes/tools/elements-preis/v/bin/python'
GATE_MAX_AGE = 2 * 3600
EXPECTED_PRODUCTS = 396
QR_BASE = 'https://eduardwart-png.github.io/elements-lab-handy-browser/#batch='
QR_PRODUCTS = ('semaglutide-15', 'tirzepatide-40')
SHOP_ONLY_PACKS = {'dual-bpc-157-tb-500-x10': 72000}   # Shop-Dual-Pack ohne Tabellenzeile: mind. 1,30 x Vial-Pack (550) = 720 EUR (E3)
PATH_REWRITE = ('preislisten/pipeline_alles.sh', 'preislisten/make_design_package.py', 'preislisten/bild_composite.py',
                'miniapp/tests/browser_acceptance.py')   # wie staging.sh paths/to_live
EXCLUDE_DIRS = {'.git', '__pycache__', '.venv-build', 'node_modules', '_out', 'public.next', 'public.prev', 'runtime'}
EXCLUDE_FILES = {'.DS_Store', '.tests_ok'}
ALLOWED_PREFIX = ('miniapp/data/', 'miniapp/public/', 'miniapp/evidence/', 'miniapp/tools/', 'miniapp/tests/', 'miniapp/extensions/',
                  'miniapp/asset-cache-current/', 'miniapp/katalog-bilder/', 'preislisten/')
FORBIDDEN = re.compile(r'(^|/)\.env|(^|/)runtime/|\.(db|sqlite3?)$|(^|/)\.git/|public\.next|\.tests_ok$|(^|/)token', re.I)
DECISION_KEYS = ('e1_motsc_alte_liste', 'e2_reta60_ausnahme', 'e3_dual_mind_30')


class Ctx:
    def __init__(self, stg=None, live=None, stg_url=None, live_url=None, entscheidungen=None, backup_root=None):
        self.stg = Path(stg or os.environ.get('RELEASE_STAGING', HOME / 'Projekte-Mac/elements-lab-telegram-staging'))
        self.live = Path(live or os.environ.get('RELEASE_LIVE', HOME / 'Projekte-Mac/elements-lab-telegram'))
        self.stg_url = stg_url or os.environ.get('RELEASE_STAGING_URL', 'http://127.0.0.1:8899')
        self.live_url = live_url or os.environ.get('RELEASE_LIVE_URL', 'http://127.0.0.1:8766')
        self.entscheidungen = Path(entscheidungen or os.environ.get('RELEASE_ENTSCHEIDUNGEN', TOOLDIR / 'entscheidungen_eddy.json'))
        self.backup_root = Path(backup_root or os.environ.get('RELEASE_BACKUP_ROOT', HOME / 'Projekte-Mac/_DATA/ELEMENTS_STRATEGIE_20261024'))

    @property
    def gate_dir(self):
        return self.stg / '_out' / 'gate'


def now_iso(t=None):
    return datetime.fromtimestamp(t or time.time()).strftime('%Y-%m-%d %H:%M:%S')


def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def res(cid, name, status, meldung, belege=None, t0=None):
    return dict(id=cid, name=name, status=status, meldung=meldung, belege=list(belege or [])[:60],
                zeit=now_iso(), zeit_epoch=time.time(), dauer_s=round(time.time() - (t0 or time.time()), 2))


# ------------------------------------------------------------------ Datenhash
def data_files(root):
    root = Path(root)
    out = [root / 'preislisten' / n for n in ('preisfamilie_v3.csv', 'preisfamilie_v3_shopzuordnung.csv', 'ausnahmen_v3.csv', 'preisempfehlung.json')]
    out += sorted((root / 'miniapp/data').glob('*.json'))
    return [p for p in out if p.is_file()]


def datenhash(root):
    """SHA-256 ueber Tabelle, Zuordnung, Ausnahmen, data/*.json und den ganzen public/-Baum (Pfad + Inhalt; mtime egal)."""
    root = Path(root)
    files = data_files(root)
    pub = root / 'miniapp/public'
    if pub.is_dir():
        files += sorted(p for p in pub.rglob('*') if p.is_file() and p.name not in EXCLUDE_FILES)
    h = hashlib.sha256()
    for p in files:
        h.update(str(p.relative_to(root)).encode() + b'\0' + sha_file(p).encode() + b'\n')
    dz = max([p.stat().st_mtime for p in data_files(root)] or [0])
    return dict(hash=h.hexdigest(), dateien=len(files), datenzeit=dz, datenzeit_iso=now_iso(dz) if dz else None)


# ------------------------------------------------------------------ Entscheidungen
def load_decisions(ctx):
    d = json.loads(ctx.entscheidungen.read_text())
    for k in DECISION_KEYS:
        if k not in d or d[k] not in (True, False, None):
            raise ValueError(f'{ctx.entscheidungen.name}: Schluessel {k} fehlt oder ist nicht true/false/null')
    return d


def open_decisions(dec):
    return [k for k in DECISION_KEYS if dec.get(k) is None]


# ------------------------------------------------------------------ Preisvergleich (G1 und probe)
def read_csv(p):
    with open(p, newline='', encoding='utf-8-sig') as fh:
        return list(csv.DictReader(fh, delimiter=';'))


def cents(s):
    return int(round(float(s) * 100))


def price_text_ok(item):
    """'70,90 €' muss zu price_cents passen (Anzeige == Rechenwert)."""
    t = (item.get('price') or '').replace('\u00a0', ' ')
    m = re.match(r'^([\d.]+),(\d\d) €$', t)
    return bool(m) and int(m.group(1).replace('.', '')) * 100 + int(m.group(2)) == item.get('price_cents')


def compare_prices(table, mapping, vials, formats, extra):
    """Gibt (fehler, zaehler) zurueck. table: Zeilen der preisfamilie_v3.csv; mapping: (level,form,substance,strength) -> shop_produkt."""
    err, cnt = [], dict(einzel=0, pack=0, shop_only=0)
    single = {('vial', p['id']): p for p in vials}
    single.update({('dual', f['base_product_id']): f for f in formats if f.get('format') == 'dual_chamber'})
    by_id = {f['id']: f for f in formats}
    cat = {}
    for e in extra:
        k = ('vial' if e['format'] == 'vial_pack' else 'dual', e['name'], e['concentration'])
        if k in cat:
            err.append(f'catalog-packs doppelt: {k}')
        cat[k] = e
    used = set()
    for r in table:
        k4 = (r['level'], r['form'], r['substance'], r['strength'])
        soll = cents(r['price_new_eur'])
        if r['level'] == 'einzel':
            pid = mapping.get(k4)
            item = single.get((r['form'], pid)) if pid else None
            if item is None:
                err.append(f'Einzel ohne Shop-Artikel: {k4} -> {pid}')
                continue
            used.add(id(item))
            cnt['einzel'] += 1
        else:
            pid = mapping.get(k4)
            item = by_id.get((pid + '-x10') if r['form'] == 'vial' else ('dual-' + pid + '-x10')) if pid else cat.get((r['form'], r['substance'], r['strength']))
            if item is None:
                err.append(f'Pack ohne Shop-Artikel: {k4}')
                continue
            if id(item) in used:
                err.append(f'Shop-Artikel doppelt belegt: {item["id"]}')
            used.add(id(item))
            cnt['pack'] += 1
        if item.get('price_cents') != soll:
            err.append(f"Preis falsch {item['id']}: Shop {item.get('price_cents')} ct, Tabelle {soll} ct ({'/'.join(k4)})")
        if not price_text_ok(item):
            err.append(f"Preistext passt nicht zu price_cents: {item['id']} '{item.get('price')}' / {item.get('price_cents')}")
    for fid, soll in SHOP_ONLY_PACKS.items():
        it = by_id.get(fid)
        if it is None or it.get('price_cents') != soll:
            err.append(f'Shop-Dual-Pack {fid}: {None if it is None else it.get("price_cents")} ct statt {soll} ct')
        else:
            used.add(id(it))
            cnt['shop_only'] += 1
    rest = [x['id'] for x in list(vials) + list(formats) + list(extra) if id(x) not in used and x.get('format') != 'pen']
    if rest:
        err.append(f'{len(rest)} Shop-Artikel ohne Tabellenzeile: {rest[:8]}')
    if cnt['einzel'] != 54 or cnt['pack'] != 340:
        err.append(f"Zaehlung: {cnt['einzel']} Einzel (soll 54), {cnt['pack']} Packs (soll 340)")
    return err, cnt


def load_table(root):
    root = Path(root)
    table = read_csv(root / 'preislisten/preisfamilie_v3.csv')
    mapping = {(r['level'], r['form'], r['substance'], r['strength']): r['shop_produkt']
               for r in read_csv(root / 'preislisten/preisfamilie_v3_shopzuordnung.csv')}
    return table, mapping


def compare_files(root):
    root = Path(root)
    table, mapping = load_table(root)
    d = root / 'miniapp/data'
    v, f, e = (json.loads((d / n).read_text()) for n in ('products.json', 'shop-formats.json', 'catalog-packs.json'))
    err, cnt = compare_prices(table, mapping, v, f, e)
    cnt['artikel'] = len(v) + len(f) + len(e)
    if cnt['artikel'] != EXPECTED_PRODUCTS:
        err.append(f"{cnt['artikel']} Artikel in data/ (soll {EXPECTED_PRODUCTS})")
    return err, cnt


def http(url, method='GET', timeout=15, headers=None):
    req = urllib.request.Request(url, method=method, headers=dict({'User-Agent': 'release-gate'}, **(headers or {})))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, (r.read() if method == 'GET' else b''), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, b'', {}
    except Exception as e:  # noqa: BLE001
        return None, repr(e).encode()[:200], {}


def embedded(html):
    out = {}
    for m in re.finditer(r'<script id="(\w+)" type="application/json">(.*?)</script>', html, re.S):
        out[m.group(1)] = json.loads(m.group(2))
    return out


def compare_http(root, base):
    st, body, _ = http(base.rstrip('/') + '/', timeout=25)
    if st != 200:
        return [f'GET {base}/ -> {st}'], {}
    emb = embedded(body.decode('utf-8', 'replace'))
    if not all(k in emb for k in ('productData', 'formatData', 'packData')):
        return ['Startseite ohne productData/formatData/packData'], {}
    table, mapping = load_table(root)
    err, cnt = compare_prices(table, mapping, emb['productData'], emb['formatData'], emb['packData'])
    cnt['artikel'] = len(emb['productData']) + len(emb['formatData']) + len(emb['packData'])
    return err, cnt


def health(base, timeout=10):
    st, body, _ = http(base.rstrip('/') + '/health', timeout=timeout)
    try:
        return st, json.loads(body)
    except Exception:  # noqa: BLE001
        return st, {}


# ------------------------------------------------------------------ Gate-Pruefpunkte
def g1_daten(ctx):
    t0 = time.time()
    try:
        err, cnt = compare_files(ctx.stg)
    except Exception as e:  # noqa: BLE001
        return res('G1', 'Daten-Konsistenz', 'rot', f'Daten nicht lesbar: {e!r}', t0=t0)
    beleg = [f"{cnt['einzel']} Einzel, {cnt['pack']} Packs, Shop-Dual-Pack {cnt['shop_only']}, {cnt.get('artikel')} Artikel"]
    if err:
        return res('G1', 'Daten-Konsistenz', 'rot', f'{len(err)} Abweichung(en) zwischen Tabelle und data/', beleg + err, t0)
    return res('G1', 'Daten-Konsistenz', 'gruen', 'alle Preise in data/ == preisfamilie_v3.csv', beleg, t0)


def g2_tests(ctx):
    t0 = time.time()
    script = ctx.live / 'preislisten/staging.sh'
    before = datenhash(ctx.stg)['hash']
    try:
        p = subprocess.run(['zsh', str(script), 'test'], capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired:
        return res('G2', 'Tests', 'rot', 'staging.sh test nach 900 s abgebrochen', t0=t0)
    out = [l for l in (p.stdout + p.stderr).splitlines() if l.strip()][-12:]
    after = datenhash(ctx.stg)['hash']
    if after != before:
        return res('G2', 'Tests', 'rot', 'Tests haben Staging-Daten/public veraendert (Datenhash vorher != nachher)', out, t0)
    if p.returncode == 0 and any('TESTS GRUEN' in l for l in out):
        return res('G2', 'Tests', 'gruen', 'staging.sh test: Python + Node gruen', out, t0)
    return res('G2', 'Tests', 'rot', f'staging.sh test rot (Exit {p.returncode})', out, t0)


VORGABEN_RUNNER = r'''
import sys, json, unittest
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import test_vorgaben as t
suite = unittest.defaultTestLoader.loadTestsFromModule(t)
r = unittest.TestResult()
suite.run(r)
st = {}
for c in t.__dict__.values():
    if isinstance(c, type) and issubclass(c, unittest.TestCase):
        for n in dir(c):
            if n.startswith('test_'):
                st[n] = 'ok'
for tc, _ in r.failures: st[tc._testMethodName] = 'fail'
for tc, tb in r.errors: st[getattr(tc, '_testMethodName', str(tc))] = 'error: ' + tb.strip().splitlines()[-1][:200]
for tc, _ in r.skipped: st[tc._testMethodName] = 'skip'
print('@@JSON@@' + json.dumps(dict(ran=r.testsRun, status=st)))
'''


def vorgaben_expectation(dec):
    """Erwartete Rot-Zeilen je Test aus den Entscheidungen. Rueckgabe (erwartet: test -> set(zeilen)), offen: [schluessel]."""
    exp, offen = {}, []
    for k, spec in (dec.get('_erwartung') or {}).items():
        if 'test' not in spec:
            continue
        v = dec.get(k)
        if v is None:
            offen.append(k)
            continue
        exp.setdefault(spec['test'], set()).update(spec['true' if v else 'false'])
    return exp, offen


def g3_regeltests(ctx, dec):
    t0 = time.time()
    out_dir = ctx.gate_dir / 'vorgaben'
    env = dict(os.environ, RELEASE_STAGING=str(ctx.stg), VORGABEN_OUT=str(out_dir))
    # Endstand G (25.10.2026, Mindestmarge 60 % hart): Eingaben (zeilen_v3.csv = zeilen_F.csv mit EK, intern), Verhandlungsliste und Konflikte aus dem Staging
    env.setdefault('VORGABEN_EINGABEN', str(HOME / 'Projekte-Mac/_DATA/ELEMENTS_STRATEGIE_20261024/team6/eingaben_G'))
    env.setdefault('VERHANDLUNG_V3', str(ctx.stg / 'preislisten' / 'verhandlungsliste_v3.csv'))
    env.setdefault('KONFLIKTE_V3', str(ctx.stg / 'preislisten' / 'konflikte_G.csv'))
    py = ctx.live / 'miniapp/.venv-build/bin/python'
    py = str(py) if py.exists() else sys.executable
    p = subprocess.run([py, '-c', VORGABEN_RUNNER, str(TOOLDIR / 'vorgaben_tests')], capture_output=True, text=True, env=env, timeout=300)
    m = re.search(r'@@JSON@@(.*)', p.stdout)
    if not m:
        return res('G3', 'Regeltests', 'rot', 'Regeltests nicht lauffaehig', (p.stdout + p.stderr).splitlines()[-8:], t0)
    run = json.loads(m.group(1))
    befunde = json.loads((out_dir / 'test_vorgaben_befunde.json').read_text())
    rot_zeilen = {}
    for b in befunde:
        if b['schwere'] in ('HART', 'AUSLEGUNG'):
            rot_zeilen.setdefault(b['test'], set()).add(b['zeile'])
    exp, offen = vorgaben_expectation(dec)
    offen_tests = {dec['_erwartung'][k]['test'] for k in offen}
    skip_ok = set(dec.get('_erwartet_uebersprungen', []))
    bad, gedeckt, blockiert = [], [], []
    for name, st in sorted(run['status'].items()):
        ist = rot_zeilen.get(name, set()) if st == 'fail' else set()
        if st.startswith('error'):
            bad.append(f'{name}: {st}')
        elif st == 'skip':
            if name not in skip_ok:
                bad.append(f'{name}: unerwartet uebersprungen')
        elif name in offen_tests:
            blockiert.append(f'{name}: Entscheidung offen, aktuell {"rot " + str(sorted(ist)) if ist else "gruen"}')
        elif name in exp:
            if ist != exp[name]:
                bad.append(f'{name}: rot erwartet fuer {sorted(exp[name])}, ist {sorted(ist)}')
            elif ist:
                gedeckt.append(f'{name}: rot wie entschieden {sorted(ist)}')
        elif st == 'fail':
            bad.append(f'{name}: unerwartet rot {sorted(ist)}')
    # E3 (kein Test im Register-Test): Abstand Doppelkammer-Pack zu Vial-Pack in der Tabelle
    e3 = (dec.get('_erwartung') or {}).get('e3_dual_mind_30', {})
    table, _ = load_table(ctx.stg)
    p_ = {(r['form'], r['substance'], r['strength']): float(r['price_new_eur']) for r in table if r['level'] == 'pack'}
    ratios = sorted((p_[k] / p_[('vial',) + k[1:]] - 1, k) for k in p_ if k[0] == 'dual' and ('vial',) + k[1:] in p_)
    med = ratios[len(ratios) // 2][0] if ratios else 0
    info = f'Dual-Pack gegen Vial-Pack: {len(ratios)} Paare, Min {ratios[0][0]:+.0%}, Median {med:+.0%}' if ratios else 'keine Paare'
    v3 = dec.get('e3_dual_mind_30')
    if v3 is None:
        blockiert.append(f'E3 offen ({info})')
    else:
        regel = e3.get('true' if v3 else 'false', {})
        lo, hi = regel.get('min_aufschlag'), regel.get('max_median')
        unter = [f'{k[1]} {k[2]} {r:+.0%}' for r, k in ratios if lo is not None and r < lo - 1e-9]
        if unter or (hi is not None and med > hi + 1e-9):
            bad.append(f'E3={v3}: Tabelle passt nicht zur Entscheidung ({info}; unter Min: {unter[:6]}; max Median {hi})')
        else:
            gedeckt.append(f'E3={v3}: {info} passt')
    beleg = [f"{run['ran']} Tests; Befunde: {out_dir}/test_vorgaben_befunde.md"] + bad + blockiert + gedeckt
    if bad:
        return res('G3', 'Regeltests', 'rot', f'{len(bad)} unerwartete(s) Ergebnis(se)', beleg, t0)
    if blockiert:
        return res('G3', 'Regeltests', 'gelb', f'keine unerwarteten Rot-Tests, aber {len(blockiert)} Pruefung(en) haengen an offenen Entscheidungen', beleg, t0)
    return res('G3', 'Regeltests', 'gruen', 'nur entschiedene Rot-Tests', beleg, t0)


def g4_audit(ctx, dec):
    t0 = time.time()
    py = str(TEAM_PY) if TEAM_PY.exists() else sys.executable
    p = subprocess.run([py, str(AUDIT_DIR / 'audit.py'), str(ctx.stg / 'preislisten/preisfamilie_v3.csv'), '--config', 'config_final.json',
                        '--eddy-reta40-expected', 'null'], cwd=str(AUDIT_DIR), capture_output=True, text=True, timeout=300)
    try:
        a = json.loads(p.stdout)
    except Exception:  # noqa: BLE001
        return res('G4', 'Preispruefer', 'rot', 'audit.py lieferte kein JSON', (p.stderr or p.stdout).splitlines()[-6:], t0)
    if a.get('input_error_count'):
        return res('G4', 'Preispruefer', 'rot', f"{a['input_error_count']} Eingabefehler im Audit", [str(x)[:200] for x in a.get('input_errors', [])][:10], t0)
    exc = {(x['regel'], x['level'], x['form'], x['substance'], x['zeile_gross_oder_pack']) for x in read_csv(ctx.stg / 'preislisten/ausnahmen_v3.csv')}
    hard = [v for v in a['violations'] if v.get('severity') == 'hard']
    e3 = dec.get('e3_dual_mind_30')
    neu, gedeckt = [], []
    for v in hard:
        r = v['row']
        k = (v['rule'], r['level'], r['form'], r['substance'], r['strength'])
        if k in exc:
            gedeckt.append('/'.join(k))
        elif v['rule'] == 'R4' and e3 is False:
            gedeckt.append('/'.join(k) + ' (durch E3=Nein gedeckt)')
        else:
            neu.append('/'.join(k) + f" ist {v.get('actual')} soll {v.get('expected')}")
    hard_exc = {k for k in exc if k[0] not in ('R13',)}   # R13 ist weich (Anteil); harte Ausnahmen muessen auch auftreten
    nicht_getroffen = sorted('/'.join(k) for k in hard_exc if not any((v['rule'], v['row']['level'], v['row']['form'], v['row']['substance'], v['row']['strength']) == k for v in hard))
    beleg = [f"hard_count {a['hard_count']}, by_rule {{{', '.join(f'{k}: {n}' for k, n in sorted(a['hard_by_rule'].items()) if n)}}}"] + \
            [f'neu: {x}' for x in neu] + [f'Ausnahme ohne Treffer: {x}' for x in nicht_getroffen] + [f'dokumentiert: {x}' for x in gedeckt]
    if neu or nicht_getroffen:
        return res('G4', 'Preispruefer', 'rot', f'{len(neu)} neue harte Treffer, {len(nicht_getroffen)} Ausnahmen ohne Treffer', beleg, t0)
    return res('G4', 'Preispruefer', 'gruen', f'{len(hard)} harte Treffer == dokumentierte Ausnahmenliste', beleg, t0)


LEAK = [
    ('Herstellername', re.compile(r'\bTing\b')),
    ('chinesische Zeichen', re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')),
    ('Einkauf/Lieferant', re.compile(r'einkauf|lieferant|supplier|wholesale|purchase[_ ]?price|cost_eur|shop_costs|vial10_eur|dual10_eur', re.I)),
    ('EK-Feld', re.compile(r'(?<![A-Za-z])ek_|_ek(?![A-Za-z])|ziel_ek', re.I)),
    ('Telefon/Messenger', re.compile(r'whatsapp|wechat|\btelefon|\bphone:|\btel\.?:|\+86|\+\d{2,3}[ -]?\d{3,4}[ -]?\d{4,}', re.I)),
    ('Firma', re.compile(r'co\.,? ?ltd|\bltd\b|limited company|\bgmbh\b|\bfirma\b|biotech', re.I)),
    ('fremde Website', re.compile(r'https?://(?!(?:' + '|'.join(re.escape(d) for d in (
        'telegram.org', 't.me', 'www.w3.org', 'eduardwart-png.github.io',
        # Studienquellen der Produktseiten (Literaturangaben, keine Firmen-/Bezugsquelle)
        'pubmed.ncbi.nlm.nih.gov', 'pmc.ncbi.nlm.nih.gov', 'doi.org', 'www.nature.com', 'www.sciencedirect.com', 'www.mdpi.com',
        'www.gutnliver.org')) + r')[/"\'\s)])[a-z0-9.-]+\.[a-z]{2,}', re.I)),
]
# Ausdruecklich erlaubte Kundentexte der Vorlage (kein Bezug zu Einkauf oder Hersteller); jeder Treffer wird im Beleg als 'erlaubt' gefuehrt.
LEAK_ERLAUBT = ('Weiter einkaufen', 'Supplier Verified', 'Not sent to a supplier')
# Vorlagen-Datendateien aus der Original-App (Recherche-Bibliothek: Quellenlinks zu Verpackungsherstellern, Spaltenname supplier_sku). /data/ wird NICHT ausgeliefert (HTTP 404, 24.10.2026 geprueft).
LEAK_DATA_VORLAGE = ('catalog.json', 'catalog-template.csv')
TEXT_EXT = {'.js', '.html', '.css', '.json', '.csv', '.txt', '.svg', '.md', '.webmanifest', '.xml'}


def g5_leaks(ctx):
    t0 = time.time()
    hits, erlaubt = [], []
    n = 0
    for base in ('miniapp/public', 'miniapp/data'):
        for f in sorted((ctx.stg / base).rglob('*')):
            if not f.is_file() or f.suffix.lower() not in TEXT_EXT:
                continue
            n += 1
            txt = f.read_text(errors='ignore')
            for label, rx in LEAK:
                for m in rx.finditer(txt):
                    if base == 'miniapp/data' and f.name in LEAK_DATA_VORLAGE and label in ('Einkauf/Lieferant', 'fremde Website'):
                        erlaubt.append(f'{f.name}: {m.group(0)!r} (Vorlagen-Datei, nicht ausgeliefert)')
                        continue
                    s = max(0, m.start() - 30)
                    umfeld = txt[max(0, m.start() - 25):m.end() + 25]
                    if base == 'miniapp/public' and any(e in umfeld and txt.find(e, max(0, m.start() - 25)) <= m.start() < txt.find(e, max(0, m.start() - 25)) + len(e) for e in LEAK_ERLAUBT):
                        erlaubt.append(f'{f.name}: {m.group(0)!r}')
                        continue
                    hits.append(f"{label}: {f.relative_to(ctx.stg)}: ...{txt[s:m.end() + 30]!r}...")
    beleg = [f'{n} Textdateien in public/ und data/ durchsucht; {len(erlaubt)} erlaubte Vorlagentexte ({", ".join(LEAK_ERLAUBT)})'] + hits[:50]
    if hits:
        return res('G5', 'Leak-Suche', 'rot', f'{len(hits)} Treffer', beleg, t0)
    return res('G5', 'Leak-Suche', 'gruen', '0 Treffer', beleg, t0)


QR_DECODE = r'''
import sys, json, cv2
out = {}
for p in sys.argv[1:]:
    im = cv2.imread(p)
    out[p] = None if im is None else cv2.QRCodeDetector().detectAndDecode(im)[0]
print(json.dumps(out))
'''


def g6_etiketten(ctx):
    t0 = time.time()
    m = ctx.stg / 'miniapp'
    ac = m / 'asset-cache-current'
    bad, ok = [], []
    prods = {p['id']: p for p in json.loads((m / 'data/products.json').read_text())}
    for pid in QR_PRODUCTS:
        files = [ac / f'assets/products/{pid}-vial.png', ac / f'assets/products/{pid}-detail.png', ac / f'assets/products/dual-chamber/{pid}.png']
        miss = [str(f.relative_to(ac)) for f in files if not f.is_file()]
        if miss:
            bad.append(f'fehlt in asset-cache-current: {miss}')
            continue
        if sha_file(files[0]) != sha_file(files[1]):
            bad.append(f'{pid}: detail.png != vial.png')
        else:
            ok.append(f'{pid}: detail == vial ({files[0].stat().st_size} B), dual {files[2].stat().st_size} B')
    qr = {}
    for pid in QR_PRODUCTS:
        batch = prods.get(pid, {}).get('batch')
        if not batch:
            bad.append(f'{pid}: keine Charge in products.json')
            continue
        for d in (ac / 'img', m / 'public/img'):
            f = d / f'qr-{batch}.png'
            if not f.is_file():
                bad.append(f'QR fehlt: {f.relative_to(m)}')
            else:
                qr[str(f)] = QR_BASE + batch
    if qr:
        py = str(TEAM_PY) if TEAM_PY.exists() else None
        p = subprocess.run([py, '-c', QR_DECODE] + list(qr), capture_output=True, text=True, timeout=120) if py else None
        if not p or p.returncode:
            bad.append('QR-Dekodierung nicht moeglich (cv2 im Team-Python fehlt)')
        else:
            got = json.loads(p.stdout)
            for f, want in qr.items():
                if got.get(f) != want:
                    bad.append(f'QR {Path(f).name}: {got.get(f)!r} statt {want}')
                else:
                    ok.append(f'QR {Path(f).parent.name}/{Path(f).name} -> {want}')
    for pid in QR_PRODUCTS:
        for rel in (f'assets/products/{pid}-vial.webp', f'assets/products/{pid}-detail.webp', f'assets/products/dual-chamber/{pid}.webp'):
            st, body, _ = http(ctx.stg_url.rstrip('/') + '/' + rel)
            disk = m / 'public' / rel
            if st != 200 or len(body) < 10000 or body[:4] != b'RIFF' or body[8:12] != b'WEBP' or (disk.is_file() and len(body) != disk.stat().st_size):
                bad.append(f'{rel}: HTTP {st}, {len(body)} B (Platte {disk.stat().st_size if disk.is_file() else "-"} B)')
            else:
                ok.append(f'{rel}: HTTP 200, {len(body)} B WebP')
    if bad:
        return res('G6', 'Etiketten', 'rot', f'{len(bad)} Fehler', bad + ok, t0)
    return res('G6', 'Etiketten', 'gruen', 'Etikettdateien, QR und WebP-Auslieferung in Ordnung', ok, t0)


REF_RX = re.compile(r'''(?<![\w$/.-])((?:\./)?(?:assets|img)/[A-Za-z0-9_./%-]+\.(?:png|webp|jpe?g|svg|gif|woff2?|ttf|css|js|json|mp4|ico))''')
SRC_RX = re.compile(r'''(?:src|href)=["']([^"'#?]+\.(?:js|css|webmanifest|json|png|webp|svg))''')


def g7_auslieferung(ctx):
    t0 = time.time()
    pub = ctx.stg / 'miniapp/public'
    st, h = health(ctx.stg_url)
    bad, beleg = [], [f'/health -> {st} {h}']
    if st != 200 or h.get('status') != 'ok' or h.get('products') != EXPECTED_PRODUCTS:
        bad.append(f'Staging /health: {st} {h} (soll status ok, {EXPECTED_PRODUCTS} Produkte)')
    refs = set()
    srcs = [pub / 'index.html'] + sorted(pub.glob('*.js')) + sorted(pub.glob('*.css')) + sorted((pub / 'extensions').glob('*.js'))
    for f in srcs:
        if not f.is_file():
            continue
        txt = f.read_text(errors='ignore')
        refs.update(r.lstrip('./') for r in REF_RX.findall(txt))
        if f.suffix == '.html':
            refs.update(r.lstrip('./') for r in SRC_RX.findall(txt) if '://' not in r and not r.startswith('data:'))
    refs.add('index.html')
    missing = []
    for r in sorted(refs):
        s, _, _ = http(ctx.stg_url.rstrip('/') + '/' + r, method='HEAD', timeout=10)
        if s != 200:
            missing.append(f'{r} -> {s}')
    beleg.append(f'{len(refs)} referenzierte Dateien aus {len([s for s in srcs if s.is_file()])} Quellen per HEAD geprueft')
    if missing:
        bad.append(f'{len(missing)} Dateien nicht ausgeliefert')
    if (ctx.stg / 'miniapp/public.next').exists():
        bad.append('miniapp/public.next existiert: im Staging laeuft gerade ein Bau (oder ein abgebrochener)')
    if bad:
        return res('G7', 'Auslieferung', 'rot', '; '.join(bad), beleg + missing, t0)
    return res('G7', 'Auslieferung', 'gruen', f'396 Produkte, {len(refs)} Assets HTTP 200, keine 404', beleg, t0)


def read_stamp(p):
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return None


def g8_qa(ctx, dh):
    t0 = time.time()
    p = ctx.stg / '_out/qa_stamp.json'
    s = read_stamp(p)
    if s is None:
        return res('G8', 'Browser-QA-Stempel', 'rot', f'{p.relative_to(ctx.stg)} fehlt (QA-Lauf setzt ihn mit release.py qa-stamp)', t0=t0)
    beleg = [f"Stempel {s.get('zeit')}: Blocker {s.get('blocker')}, Hoch {s.get('hoch')}, Hash {str(s.get('datenhash'))[:12]}"]
    if s.get('datenhash') != dh['hash']:
        return res('G8', 'Browser-QA-Stempel', 'rot', 'QA-Stempel gehoert zu einem anderen Datenstand (Datenhash verschieden)', beleg, t0)
    if s.get('blocker') != 0 or s.get('hoch') != 0:
        return res('G8', 'Browser-QA-Stempel', 'rot', 'QA meldet Blocker/Hoch', beleg, t0)
    return res('G8', 'Browser-QA-Stempel', 'gruen', '0 Blocker, 0 Hoch, passender Datenhash', beleg, t0)


def desktop_files(ctx):
    d = ctx.stg / '_out/desktop'
    return sorted(f for f in d.rglob('*') if f.is_file() and f.name not in EXCLUDE_FILES) if d.is_dir() else []


def g9_listen(ctx, dh):
    t0 = time.time()
    files = desktop_files(ctx)
    if not files:
        return res('G9', 'Listen', 'rot', '_out/desktop/ leer oder fehlt', t0=t0)
    s = read_stamp(ctx.stg / '_out/listen_stamp.json')
    alt = [f"{f.relative_to(ctx.stg)} ({now_iso(f.stat().st_mtime)})" for f in files if f.stat().st_mtime <= dh['datenzeit']]
    beleg = [f"{len(files)} Dateien in _out/desktop, Datenzeit {dh['datenzeit_iso']}"] + [f'aelter als Daten: {a}' for a in alt[:30]]
    if s is None:
        return res('G9', 'Listen', 'rot', '_out/listen_stamp.json fehlt (Listenlauf setzt ihn mit release.py list-stamp)', beleg, t0)
    bad = []
    if s.get('datenhash') != dh['hash']:
        bad.append('Listen-Stempel gehoert zu anderem Datenhash')
    if alt:
        bad.append(f'{len(alt)} Listen aelter als die Daten')
    cur = {str(f.relative_to(ctx.stg)): sha_file(f) for f in files}
    if cur != s.get('dateien'):
        bad.append('Listen seit dem Stempel veraendert/hinzugefuegt/entfernt')
    if bad:
        return res('G9', 'Listen', 'rot', '; '.join(bad), beleg, t0)
    return res('G9', 'Listen', 'gruen', f'{len(files)} Listen jünger als die Daten, Stempel passt', beleg, t0)


def walk(root):
    root = Path(root)
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in EXCLUDE_DIRS]
        for fn in fns:
            if fn not in EXCLUDE_FILES:
                yield str((Path(dp) / fn).relative_to(root))


def norm_paths(data):
    return data.replace(b'Projekte-Mac/elements-lab-telegram-staging', b'Projekte-Mac/elements-lab-telegram')


def diff_plan(stg, live):
    """Dateien, die ein Promote kopieren wuerde (Inhalt verschieden oder neu). PATH_REWRITE-Dateien mit Pfadnormalisierung."""
    stg, live = Path(stg), Path(live)
    plan = []
    for rel in walk(stg):
        s, l = stg / rel, live / rel
        if not l.exists():
            plan.append(dict(datei=rel, art='neu'))
            continue
        if rel in PATH_REWRITE:
            if norm_paths(s.read_bytes()) != l.read_bytes():
                plan.append(dict(datei=rel, art='geaendert', pfade_umschreiben=True))
            continue
        if s.stat().st_size != l.stat().st_size or sha_file(s) != sha_file(l):
            plan.append(dict(datei=rel, art='geaendert', live_neuer=l.stat().st_mtime > s.stat().st_mtime + 1))
    return plan


def rsync_count(stg, live):
    ex = []
    for d in EXCLUDE_DIRS:
        ex += ['--exclude', d + '/']
    for f in EXCLUDE_FILES:
        ex += ['--exclude', f]
    try:
        p = subprocess.run(['rsync', '-rcn', '--out-format=%n'] + ex + [f'{stg}/', f'{live}/'], capture_output=True, timeout=300)
        return len([l for l in p.stdout.splitlines() if l and not l.endswith(b'/')])
    except Exception:  # noqa: BLE001
        return None


LISTEN_TOOL = Path(__file__).resolve().parent / 'listen_aufraeumen.py'
LISTEN_PY = Path.home() / '.hermes/tools/elements-preis/v/bin/python'   # Team-Python mit pymupdf (Text-Vergleich der PDFs)


def listen_sweep(mode):
    """Ruft listen_aufraeumen.py auf; mode '--pruefen' oder '--aufraeumen'. Gibt (returncode, json) zurueck."""
    py = str(LISTEN_PY) if LISTEN_PY.exists() else sys.executable
    r = subprocess.run([py, str(LISTEN_TOOL), mode, '--json'], capture_output=True, text=True, timeout=300)
    try:
        j = json.loads(r.stdout[r.stdout.index('{'):])
    except Exception:  # noqa: BLE001
        j = {'fehler': (r.stdout + r.stderr)[-400:]}
    return r.returncode, j


def g11_listen_sauber(ctx):
    """Eddy 25.10.2026: keine veralteten Listen ausserhalb des massgeblichen Desktop-Ordners. Raeumt selbst auf (Papierkorb) und prueft danach."""
    t0 = time.time()
    if not LISTEN_TOOL.exists():
        return res('G11', 'Listen-Sauberkeit', 'rot', 'listen_aufraeumen.py fehlt', t0=t0)
    rc, j = listen_sweep('--aufraeumen')
    beleg = [f'in Papierkorb gelegt: {a}' for a, _ in j.get('in_papierkorb', [])]
    beleg += [f'Desktop weicht ab (wird nach dem Promote per Cutover angeglichen): {a}' for a in j.get('desktop_weicht_ab', [])]
    if 'fehler' in j:
        return res('G11', 'Listen-Sauberkeit', 'rot', f"Aufraeumen nicht lesbar: {j['fehler']}", beleg, t0)
    bad = j.get('veraltete_kopien', []) + j.get('unbekannte_listen_im_massgeblichen_ordner', [])
    if bad:
        return res('G11', 'Listen-Sauberkeit', 'rot', f'{len(bad)} veraltete Listen ausserhalb des Listenordners nicht entfernbar', beleg + bad[:10], t0)
    return res('G11', 'Listen-Sauberkeit', 'gruen', 'keine veralteten Listen ausserhalb von Desktop/Elements_Lab' + (f'; {len(j["in_papierkorb"])} entfernt' if j.get('in_papierkorb') else ''), beleg, t0)


def listen_nach_promote():
    """Nach erfolgreichem Promote: Desktop-Listen an den Live-Stand angleichen (Cutover) und Reste wegraeumen."""
    stg = Path.home() / 'Projekte-Mac/elements-lab-telegram-staging/preislisten/pipeline_v3.sh'
    rc, j = listen_sweep('--pruefen')
    if j.get('desktop_weicht_ab') and stg.exists():
        r = subprocess.run(['/bin/zsh', str(stg), 'cutover', '--freigabe-eddy'], capture_output=True, text=True, timeout=300)
        print('  Listen-Cutover:', 'ok' if r.returncode == 0 else f'FEHLER {r.returncode}: {(r.stdout + r.stderr)[-300:]}')
    rc, j = listen_sweep('--aufraeumen')
    print('  Listen-Stand:', 'SAUBER' if j.get('sauber') else f"NICHT SAUBER {j}")
    return bool(j.get('sauber'))


def g10_live(ctx):
    t0 = time.time()
    st, h = health(ctx.live_url)
    bad, beleg = [], [f'Live /health -> {st} {h}']
    if st != 200 or h.get('status') != 'ok' or h.get('products') != EXPECTED_PRODUCTS or h.get('mode') != 'telegram':
        bad.append('Live /health nicht ok (status ok, 396, mode telegram erwartet)')
    plan = diff_plan(ctx.stg, ctx.live)
    rc = rsync_count(ctx.stg, ctx.live)
    beleg.append(f'Differenz Staging -> Live: {len(plan)} Dateien (rsync -n zaehlt {rc}, ohne Pfadumschreibung der {len(PATH_REWRITE)} Hilfsskripte)')
    verboten = [p['datei'] for p in plan if FORBIDDEN.search(p['datei'])]
    fremd = [p['datei'] for p in plan if not p['datei'].startswith(ALLOWED_PREFIX) and not re.match(r'^miniapp/[^/]+\.(py|md|command)$', p['datei'])]
    neuer = [p['datei'] for p in plan if p.get('live_neuer')]
    if verboten:
        bad.append(f'verbotene Dateien in der Differenz: {verboten[:10]}')
    if fremd:
        bad.append(f'unerwartete Dateien in der Differenz: {fremd[:10]}')
    if neuer:
        bad.append(f'{len(neuer)} Live-Dateien sind neuer als ihr Staging-Gegenstueck (Live wurde nachtraeglich geaendert): {neuer[:8]}')
    beleg += [f"{p['art']}: {p['datei']}" for p in plan[:40]]
    if bad:
        return res('G10', 'Live-Unversehrtheit', 'rot', '; '.join(bad), beleg, t0)
    return res('G10', 'Live-Unversehrtheit', 'gruen', f'Live gesund, {len(plan)} erwartete Dateien in der Differenz', beleg, t0)


# ------------------------------------------------------------------ Gate
def run_gate(ctx, only=None, write=True):
    dh = datenhash(ctx.stg)
    try:
        dec = load_decisions(ctx)
        dec_err = None
    except Exception as e:  # noqa: BLE001
        dec, dec_err = {}, repr(e)
    checks = []
    plan = [('G1', lambda: g1_daten(ctx)), ('G2', lambda: g2_tests(ctx)), ('G3', lambda: g3_regeltests(ctx, dec)),
            ('G4', lambda: g4_audit(ctx, dec)), ('G5', lambda: g5_leaks(ctx)), ('G6', lambda: g6_etiketten(ctx)),
            ('G7', lambda: g7_auslieferung(ctx)), ('G8', lambda: g8_qa(ctx, dh)), ('G9', lambda: g9_listen(ctx, dh)),
            ('G10', lambda: g10_live(ctx)), ('G11', lambda: g11_listen_sauber(ctx))]
    for cid, fn in plan:
        if only and cid not in only:
            continue
        if dec_err and cid in ('G3', 'G4'):
            checks.append(res(cid, 'Entscheidungen', 'rot', f'entscheidungen_eddy.json ungueltig: {dec_err}'))
            continue
        try:
            checks.append(fn())
        except Exception as e:  # noqa: BLE001  ein abgestuerzter Pruefpunkt ist rot, nie gruen
            checks.append(res(cid, cid, 'rot', f'Pruefpunkt abgestuerzt: {e!r}'))
    offen = open_decisions(dec) if dec else list(DECISION_KEYS)
    if dh['hash'] != datenhash(ctx.stg)['hash']:
        checks.append(res('G0', 'Stabilitaet', 'rot', 'Staging hat sich waehrend des Gate-Laufs geaendert'))
    status = 'rot' if any(c['status'] == 'rot' for c in checks) else ('gelb' if offen or any(c['status'] == 'gelb' for c in checks) else 'gruen')
    if only and status == 'gruen':
        status = 'gelb'   # Teil-Gate gibt nie frei
    g = dict(version=1, zeit=now_iso(), zeit_epoch=time.time(), staging=str(ctx.stg), datenhash=dh['hash'], datenzeit=dh['datenzeit_iso'],
             entscheidungen={k: dec.get(k) for k in DECISION_KEYS}, entscheidungen_sha=sha_file(ctx.entscheidungen) if ctx.entscheidungen.exists() else None,
             offene_entscheidungen=offen, teil_gate=sorted(only) if only else None, status=status,
             exit={'gruen': 0, 'rot': 1, 'gelb': 2}[status], checks=checks)
    if write:
        ctx.gate_dir.mkdir(parents=True, exist_ok=True)
        (ctx.gate_dir / 'GATE.json').write_text(json.dumps(g, ensure_ascii=False, indent=1))
        (ctx.gate_dir / 'GATE.md').write_text(gate_md(g))
    return g


ICON = {'gruen': 'GRUEN', 'gelb': 'GELB ', 'rot': 'ROT  '}


def gate_md(g):
    L = [f"# Release-Gate {g['zeit']}: {g['status'].upper()}", '',
         f"Datenhash `{g['datenhash']}` (Datenzeit {g['datenzeit']}), Staging `{g['staging']}`",
         f"Entscheidungen: {g['entscheidungen']} - offen: {', '.join(g['offene_entscheidungen']) or 'keine'}", '',
         '| Punkt | Ergebnis | Meldung |', '|---|---|---|']
    L += [f"| {c['id']} {c['name']} | {c['status']} | {c['meldung']} |" for c in g['checks']]
    for c in g['checks']:
        L += ['', f"## {c['id']} {c['name']}: {c['status']} ({c['zeit']}, {c['dauer_s']} s)", '', c['meldung']] + [f'- {b}' for b in c['belege']]
    return '\n'.join(L) + '\n'


# ------------------------------------------------------------------ Probe
def menu_button_check(live_root, origin):
    """Liest den Menueknopf ueber die Bot-API. Token nur im Speicher; Fehlermeldungen ohne Token."""
    env = (Path(live_root) / 'miniapp/runtime/.env.elements').read_text()
    m = re.search(r'TOKEN=(\S+)', env)
    if not m:
        return False, 'kein Token in der Laufzeit-Konfiguration'
    tok = m.group(1)
    try:
        st, body, _ = http(f'https://api.telegram.org/bot{tok}/getChatMenuButton', timeout=20)
        if st != 200:
            return False, f'getChatMenuButton HTTP {st}'
        url = ((json.loads(body).get('result') or {}).get('web_app') or {}).get('url', '')
    finally:
        del tok
    if not origin or not url.startswith(origin):
        return False, f'Menueknopf zeigt auf {url[:80]!r}, Tunnel ist {origin!r}'
    s, _, _ = http(url, timeout=25)
    return s == 200, f'Menueknopf {url[:80]} -> HTTP {s}'


def probe(ctx, which):
    root, url = (ctx.live, ctx.live_url) if which == 'live' else (ctx.stg, ctx.stg_url)
    bad, ok = [], []
    st, h = None, {}
    for _ in range(3 if which == 'live' else 1):
        st, h = health(url)
        if st == 200:
            break
        time.sleep(5)
    want_mode = 'telegram' if which == 'live' else 'preview'
    (ok if st == 200 and h.get('products') == EXPECTED_PRODUCTS and h.get('mode') == want_mode and h.get('status') == 'ok' else bad).append(f'/health {st} {h}')
    if not (root / 'preislisten/preisfamilie_v3.csv').is_file():
        bad.append(f'{root.name}: preislisten/preisfamilie_v3.csv fehlt - dort laeuft noch nicht die Preisfamilie v3 (vor dem ersten Promote erwartet)')
    try:
        err, cnt = compare_files(root)
        (bad.extend(f'Dateien: {e}' for e in err) if err else ok.append(f'Dateien: {cnt}'))
    except Exception as e:  # noqa: BLE001
        bad.append(f'Dateien nicht vergleichbar: {type(e).__name__}: {getattr(e, "filename", "") or e}')
    base = url
    origin = None
    if which == 'live':
        try:
            origin = json.loads((root / 'miniapp/runtime/status.json').read_text()).get('origin')
        except Exception:  # noqa: BLE001
            origin = None
        s0, _, _ = http(url.rstrip('/') + '/', method='HEAD')
        if s0 != 200 and origin:
            base = origin
    try:
        err, cnt = compare_http(root, base)
        (bad.extend(f'HTTP: {e}' for e in err) if err else ok.append(f'HTTP-Startseite ({base.split("//")[0]}): {cnt}'))
    except Exception as e:  # noqa: BLE001
        bad.append(f'HTTP-Vergleich nicht moeglich: {type(e).__name__}: {getattr(e, "filename", "") or e}')
    if which == 'live':
        s, _, _ = http((origin or '').rstrip('/') + '/health', timeout=25) if origin else (None, b'', {})
        (ok if s == 200 else bad).append(f'Tunnel {origin} /health von aussen -> {s}')
        try:
            good, msg = menu_button_check(root, origin)
        except Exception as e:  # noqa: BLE001
            good, msg = False, f'Menueknopf nicht pruefbar: {type(e).__name__}'
        (ok if good else bad).append(msg)
    return dict(ziel=which, zeit=now_iso(), ok=not bad, fehler=bad, belege=ok)


# ------------------------------------------------------------------ Promote
def promote_blockers(ctx, max_age=GATE_MAX_AGE, now=None):
    now = now or time.time()
    g = read_stamp(ctx.gate_dir / 'GATE.json')
    if g is None:
        return ['kein GATE.json - erst release.py gate']
    b = []
    if g.get('status') != 'gruen' or g.get('exit') != 0 or g.get('teil_gate'):
        b.append(f"Gate ist {g.get('status')} (nur ein volles gruenes Gate gibt frei)")
    if now - float(g.get('zeit_epoch', 0)) > max_age:
        b.append(f"Gate ist {int((now - float(g.get('zeit_epoch', 0))) // 60)} min alt (max {max_age // 60} min)")
    if g.get('datenhash') != datenhash(ctx.stg)['hash']:
        b.append('Datenhash des Staging hat sich seit dem Gate geaendert')
    try:
        dec = load_decisions(ctx)
        off = open_decisions(dec)
        if off:
            b.append(f'offene Entscheidungen: {off}')
        if ctx.entscheidungen.exists() and sha_file(ctx.entscheidungen) != g.get('entscheidungen_sha'):
            b.append('entscheidungen_eddy.json seit dem Gate geaendert')
    except Exception as e:  # noqa: BLE001
        b.append(f'Entscheidungen ungueltig: {e!r}')
    return b


def promote_core(stg, live, plan, backup_dir, restart_fn, probe_fn, log=print, rewrite=True, fail_copy_after=None):
    """Sichert die betroffenen Live-Dateien, kopiert, startet neu, prueft. Bei Fehler: Rollback + Neustart + Probe.
    Rueckgabe dict(ergebnis='live'|'rollback'|'rollback_fehlgeschlagen', ...)."""
    stg, live, backup_dir = Path(stg), Path(live), Path(backup_dir)
    files = [p['datei'] for p in plan]
    neu = [f for f in files if not (live / f).exists()]
    vorher = {f: sha_file(live / f) for f in files if (live / f).exists()}
    for f in vorher:
        dst = backup_dir / 'files' / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live / f, dst)
        if sha_file(dst) != vorher[f]:
            raise RuntimeError(f'Sicherung fehlerhaft: {f}')
    (backup_dir / 'manifest.json').write_text(json.dumps(dict(zeit=now_iso(), live=str(live), staging=str(stg), vorher=vorher, neu=neu), indent=1))
    log(f'Sicherung: {len(vorher)} Dateien + {len(neu)} neue nach {backup_dir}')
    rep = dict(sicherung=str(backup_dir), dateien=len(files), neu=len(neu))
    try:
        for i, f in enumerate(files):
            if fail_copy_after is not None and i >= fail_copy_after:
                raise RuntimeError('simulierter Kopierfehler')
            (live / f).parent.mkdir(parents=True, exist_ok=True)
            tmp = (live / f).with_name((live / f).name + '.release-tmp')
            shutil.copy2(stg / f, tmp)
            if rewrite and f in PATH_REWRITE:
                tmp.write_bytes(norm_paths(tmp.read_bytes()))
            os.replace(tmp, live / f)
        log(f'kopiert: {len(files)} Dateien')
        restart_fn()
        pr = probe_fn()
        rep['probe'] = pr
        if pr.get('ok'):
            rep['ergebnis'] = 'live'
            return rep
        log('PROBE LIVE ROT -> Rollback')
    except Exception as e:  # noqa: BLE001
        rep['fehler'] = repr(e)
        log(f'Fehler beim Promote: {e!r} -> Rollback')
    rollback(live, backup_dir, log)
    restart_fn()
    pr2 = probe_fn()
    rep['probe_nach_rollback'] = pr2
    rest = {f: sha_file(live / f) for f in vorher}
    gleich = rest == vorher and not any((live / f).exists() for f in neu)
    rep['ergebnis'] = 'rollback' if gleich and pr2.get('ok') else 'rollback_fehlgeschlagen'
    rep['rollback_bytegleich'] = gleich
    return rep


def rollback(live, backup_dir, log=print):
    live, backup_dir = Path(live), Path(backup_dir)
    man = json.loads((backup_dir / 'manifest.json').read_text())
    for f in man['vorher']:
        (live / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_dir / 'files' / f, live / f)
    for f in man['neu']:
        if (live / f).exists():
            (live / f).unlink()
    for f in list(Path(live).rglob('*.release-tmp')):
        f.unlink()
    log(f"Rollback: {len(man['vorher'])} Dateien zurueck, {len(man['neu'])} neue entfernt")


def real_restart(log=print):
    p = subprocess.run([sys.executable, str(RESTART_PROBE)], capture_output=True, text=True, timeout=900)
    for l in (p.stdout + p.stderr).splitlines()[-12:]:
        log('  restart: ' + l)


def simulate_rollback(ctx, plan, log=print):
    """Rollback-Beweis ohne Live-Eingriff: echte Dateiliste, Live-/Staging-Fassungen in einen Wegwerf-Ordner, Probe schlaegt fehl."""
    sand = Path(tempfile.mkdtemp(prefix='release-sim-', dir=str(SCRATCH)))
    for side, src in (('live', ctx.live), ('stg', ctx.stg)):
        for p in plan:
            if (src / p['datei']).exists():
                (sand / side / p['datei']).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src / p['datei'], sand / side / p['datei'])
    before = {f: sha_file(sand / 'live' / f) for f in walk(sand / 'live')}
    calls = []
    rep = promote_core(sand / 'stg', sand / 'live', plan, sand / 'sicherung', lambda: calls.append('restart'),
                       lambda: dict(ok=len(calls) > 1, fehler=[] if len(calls) > 1 else ['simuliert: probe live rot']), log=log)
    after = {f: sha_file(sand / 'live' / f) for f in walk(sand / 'live')}
    rep.update(sandbox=str(sand), neustarts=len(calls), live_bytegleich_wie_vorher=(before == after))
    return rep


def cmd_promote(ctx, args):
    if not args.freigabe_eddy:
        print('ABBRUCH: ohne --freigabe-eddy kein Live-Gang')
        return 2
    blockers = promote_blockers(ctx)
    plan = diff_plan(ctx.stg, ctx.live)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup = ctx.backup_root / f'live-sicherung-{stamp}'
    print(f"{'TROCKENLAUF' if args.trockenlauf else 'PROMOTE'}: {len(plan)} Dateien Staging -> Live ({sum(p['art'] == 'neu' for p in plan)} neu)")
    for p in plan[:80]:
        print(f"  {p['art']:9} {p['datei']}{'  (Pfade umschreiben)' if p.get('pfade_umschreiben') else ''}")
    print(f'  Sicherung nach: {backup}\n  Neustart: {RESTART_PROBE}\n  danach: release.py probe live; bei Rot automatischer Rollback')
    verb = [p['datei'] for p in plan if FORBIDDEN.search(p['datei'])]
    if verb:
        blockers.append(f'verbotene Dateien im Plan: {verb[:5]}')
    if blockers:
        print('BLOCKIERT:\n  - ' + '\n  - '.join(blockers))
    if args.trockenlauf:
        if os.environ.get('RELEASE_SIMULATE_FAIL') == '1':
            rep = simulate_rollback(ctx, plan)
            print('SIMULATION (Wegwerf-Ordner, Live unberuehrt): ' + json.dumps({k: rep[k] for k in ('ergebnis', 'rollback_bytegleich', 'live_bytegleich_wie_vorher', 'neustarts', 'dateien', 'sandbox')}))
            ctx.gate_dir.mkdir(parents=True, exist_ok=True)
            (ctx.gate_dir / 'ROLLBACK_SIMULATION.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str))
            if rep['ergebnis'] != 'rollback' or not rep['live_bytegleich_wie_vorher']:
                return 4
        print('TROCKENLAUF: Abbruch vor dem Kopieren. Live unveraendert.')
        return 3 if blockers else 0
    if blockers:
        return 3
    if not plan:
        print('nichts zu kopieren')
        return 0
    rep = promote_core(ctx.stg, ctx.live, plan, backup, real_restart, lambda: probe(ctx, 'live'))
    (backup / 'PROMOTE_BERICHT.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str))
    ctx.gate_dir.mkdir(parents=True, exist_ok=True)
    (ctx.gate_dir / f'PROMOTE_{stamp}.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str))
    print(f"ERGEBNIS: {rep['ergebnis']} (Bericht {backup / 'PROMOTE_BERICHT.json'})")
    if rep['ergebnis'] == 'live':
        try:
            listen_nach_promote()
        except Exception as e:  # noqa: BLE001 - Listenpflege darf einen erfolgreichen Promote nie kippen
            print(f'  Listen-Nachpflege fehlgeschlagen: {e!r}')
    return 0 if rep['ergebnis'] == 'live' else 5


# ------------------------------------------------------------------ Stempel, Status
def cmd_qa_stamp(ctx, args):
    dh = datenhash(ctx.stg)
    s = dict(datenhash=dh['hash'], zeit=now_iso(), zeit_epoch=time.time(), blocker=args.blocker, hoch=args.hoch, notiz=args.notiz or '')
    (ctx.stg / '_out').mkdir(parents=True, exist_ok=True)
    (ctx.stg / '_out/qa_stamp.json').write_text(json.dumps(s, ensure_ascii=False, indent=1))
    print(f"qa_stamp.json gesetzt: Blocker {args.blocker}, Hoch {args.hoch}, Hash {dh['hash'][:12]}")
    return 0


def cmd_list_stamp(ctx, args):
    dh = datenhash(ctx.stg)
    files = desktop_files(ctx)
    if not files:
        print('ABBRUCH: _out/desktop ist leer')
        return 1
    s = dict(datenhash=dh['hash'], zeit=now_iso(), zeit_epoch=time.time(), datenzeit=dh['datenzeit_iso'],
             dateien={str(f.relative_to(ctx.stg)): sha_file(f) for f in files})
    (ctx.stg / '_out/listen_stamp.json').write_text(json.dumps(s, ensure_ascii=False, indent=1))
    alt = [f for f in files if f.stat().st_mtime <= dh['datenzeit']]
    print(f"listen_stamp.json gesetzt: {len(files)} Dateien, Hash {dh['hash'][:12]}" + (f'; WARNUNG {len(alt)} Dateien aelter als die Daten' if alt else ''))
    return 0


def age(t):
    if not t:
        return '-'
    m = int((time.time() - float(t)) // 60)
    return f'{m} min' if m < 120 else f'{m // 60} h {m % 60} min'


def cmd_status(ctx, args):
    dh = datenhash(ctx.stg)
    print(f"STAGING  {ctx.stg}\n  Datenhash {dh['hash'][:16]}  ({dh['dateien']} Dateien, Datenzeit {dh['datenzeit_iso']})")
    g = read_stamp(ctx.gate_dir / 'GATE.json')
    if g:
        frisch = 'passt' if g['datenhash'] == dh['hash'] else 'VERALTET (anderer Datenhash)'
        print(f"GATE     {g['status'].upper()} vor {age(g['zeit_epoch'])}, Hash {frisch}")
        for c in g['checks']:
            print(f"  {c['id']:4} {ICON.get(c['status'], c['status'])} vor {age(c['zeit_epoch']):>10}  {c['name']}: {c['meldung'][:90]}")
    else:
        print('GATE     noch nie gelaufen')
    for n in ('qa_stamp.json', 'listen_stamp.json'):
        s = read_stamp(ctx.stg / '_out' / n)
        print(f"  {n:18} " + ('fehlt' if s is None else f"vor {age(s.get('zeit_epoch'))}, Hash {'passt' if s.get('datenhash') == dh['hash'] else 'anders'}"))
    try:
        dec = load_decisions(ctx)
        print(f"ENTSCHEIDUNGEN  " + ', '.join(f"{k}={dec[k]}" for k in DECISION_KEYS) + f"  -> offen: {open_decisions(dec) or 'keine'}")
    except Exception as e:  # noqa: BLE001
        print(f'ENTSCHEIDUNGEN  ungueltig: {e!r}')
    pr = probe(ctx, 'live')
    print(f"LIVE     {'GESUND' if pr['ok'] else 'ROT'}")
    for b in pr['belege']:
        print('  ok   ' + b[:150])
    for b in pr['fehler']:
        print('  ROT  ' + b[:150])
    bl = promote_blockers(ctx)
    print('PROMOTE  ' + ('moeglich (mit --freigabe-eddy)' if not bl else 'gesperrt: ' + '; '.join(bl)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('status')
    gp = sub.add_parser('gate')
    gp.add_argument('--nur', help='nur diese Pruefpunkte, z. B. G1,G5 (Teil-Gate gibt nie frei)')
    pp = sub.add_parser('probe')
    pp.add_argument('ziel', choices=['staging', 'live'])
    pr = sub.add_parser('promote')
    pr.add_argument('--freigabe-eddy', action='store_true')
    pr.add_argument('--trockenlauf', action='store_true')
    qa = sub.add_parser('qa-stamp')
    qa.add_argument('--blocker', type=int, required=True)
    qa.add_argument('--hoch', type=int, required=True)
    qa.add_argument('--notiz')
    sub.add_parser('list-stamp')
    a = ap.parse_args(argv)
    ctx = Ctx()
    if a.cmd == 'gate':
        only = set(x.strip().upper() for x in a.nur.split(',')) if a.nur else None
        g = run_gate(ctx, only)
        print(f"GATE {g['status'].upper()}  Datenhash {g['datenhash'][:16]}  offen: {g['offene_entscheidungen'] or 'keine'}")
        for c in g['checks']:
            print(f"  {c['id']:4} {ICON[c['status']]} {c['name']}: {c['meldung'][:110]}")
        print(f"Bericht: {ctx.gate_dir / 'GATE.md'}")
        return g['exit']
    if a.cmd == 'probe':
        r = probe(ctx, a.ziel)
        print(f"PROBE {a.ziel.upper()} {'OK' if r['ok'] else 'ROT'}")
        for b in r['belege']:
            print('  ok   ' + b[:160])
        for b in r['fehler']:
            print('  ROT  ' + b[:160])
        return 0 if r['ok'] else 1
    if a.cmd == 'promote':
        return cmd_promote(ctx, a)
    if a.cmd == 'qa-stamp':
        return cmd_qa_stamp(ctx, a)
    if a.cmd == 'list-stamp':
        return cmd_list_stamp(ctx, a)
    return cmd_status(ctx, a)


if __name__ == '__main__':
    sys.exit(main())
