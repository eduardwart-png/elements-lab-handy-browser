#!/usr/bin/env python3
"""[team5-Kopie fuer Variante F (Haendlerdeckel): zusaetzlich KONFLIKTE_V3 (konflikte_F.csv); Verhandlungsliste = Zeilen < 2,5 x EK PLUS Zeilen mit Deckel < 2,5 x EK; neue Pruefklasse T13 (Haendlerspanne >= 40 % oder dokumentierter Konflikt). Grundlage: team4-Kopie fuer Stufen M1/M2/M3: Tabellenpfade ueber Umgebung (TABELLE_V3, ZEILEN_V3, AUSNAHMEN_V3, VERHANDLUNG_V3, BEFUND_SUFFIX); Reta 60 = Entscheidungsfall E2 und MOTS-C-Vial-Packs = E1 sind erlaubt (INFO), alles andere Rote bleibt Fehler; jede Zeile < 2,5 x EK muss in der Verhandlungsliste stehen]
Register-Test fuer die Preisfamilie v3 (Elements Labs). Controller-Rolle, unabhaengig vom Maker.

Prueft JEDE Regel aus EDDY_VORGABEN.yaml mit 'pruefbar: hart' einzeln und OHNE Toleranz (exakte Bruchrechnung).
Eingaben (alle read-only): tabelle_v3.csv, zeilen_v3.csv, ausnahmen_v3.csv, alte Verkaufsliste (cl.lines(adjusted=False) bzw. Snapshot),
references.json (EK, nur intern), anker_v2.csv (Markt).  Standard: Kopien in ./eingaben_v3 (Pruefsummen in PRUEFSUMMEN.txt).

Aufruf:   python test_vorgaben.py            (Standard: v3 aus ./eingaben_v3)
          TABELLE_V3=... ZEILEN_V3=... AUSNAHMEN_V3=... python test_vorgaben.py     (z. B. Variante B)
Ausgabe:  Testlauf auf stdout + test_vorgaben_befunde[_<suffix>].json/.md (jede Verletzung mit Zeile, alt, neu, Prozent).
Bedeutung der Schweregrade:  HART = Register 'pruefbar: hart' (Test schlaegt fehl); AUSLEGUNG = Register-Regel anders gelesen (Test schlaegt fehl,
wird im Bericht getrennt gefuehrt); INFO = weiche Regel, nur Befund (Test bleibt gruen).
"""
import sys
sys.dont_write_bytecode = True
import csv
import json
import os
import re
import unittest
from collections import defaultdict
from decimal import Decimal
from fractions import Fraction as F
from pathlib import Path

# KOPIE fuer das Release-Gate (preislisten/release.py, Pruefpunkt G3). Original: _DATA/ELEMENTS_STRATEGIE_20261024/team3/test_vorgaben.py
# Aenderungen gegen das Original (nur Pfade/Ausgabe, keine Regel geaendert):
#  - Tabelle und Ausnahmen kommen aus dem STAGING (RELEASE_STAGING, Standard ~/Projekte-Mac/elements-lab-telegram-staging/preislisten)
#  - alte Liste / FOCUS werden aus dem Staging-Code gelesen (miniapp/tools/catalog_lines.py, preislisten/empfehlung.py)
#  - interne Eingaben (zeilen_v3.csv mit EK, Snapshot, references, anker, ist_tabelle) bleiben read-only in eingaben_v3 (VORGABEN_EINGABEN)
#  - Befunde gehen nach VORGABEN_OUT (Standard <staging>/_out/gate/vorgaben), jeder Befund traegt den Testnamen ('test')
STG = Path(os.environ.get('RELEASE_STAGING', '/Users/eduardwart/Projekte-Mac/elements-lab-telegram-staging'))
IN = Path(os.environ.get('VORGABEN_EINGABEN', '/Users/eduardwart/Projekte-Mac/_DATA/ELEMENTS_STRATEGIE_20261024/team3/eingaben_v3'))
HERE = Path(os.environ.get('VORGABEN_OUT', str(STG / '_out' / 'gate' / 'vorgaben')))
REGISTER = Path('/Users/eduardwart/Projekte-Mac/_DATA/ELEMENTS_STRATEGIE_20261024/EDDY_VORGABEN.yaml')
LIVE_TOOLS = STG / 'miniapp' / 'tools'                       # Name beibehalten: hier der Staging-Code
LIVE_EMPFEHLUNG = STG / 'preislisten' / 'empfehlung.py'
CUR_TEST = ['']


def _p(env, name):
    return Path(os.environ[env]) if os.environ.get(env) else IN / name


TABELLE = Path(os.environ['TABELLE_V3']) if os.environ.get('TABELLE_V3') else STG / 'preislisten' / 'preisfamilie_v3.csv'
ZEILEN = _p('ZEILEN_V3', 'zeilen_v3.csv')
AUSNAHMEN = Path(os.environ['AUSNAHMEN_V3']) if os.environ.get('AUSNAHMEN_V3') else STG / 'preislisten' / 'ausnahmen_v3.csv'
SUFFIX = os.environ.get('BEFUND_SUFFIX', '')
VERHANDLUNG = os.environ.get('VERHANDLUNG_V3')
KONFLIKTE = os.environ.get('KONFLIKTE_V3')      # team5: konflikte_F.csv (Pack/10 ueber 60 % vom Marktmedian, mit Grund)
SHOP_ONLY_PACKS = {('bpc-157-tb-500', 'dual'): F(720)}   # 395. Zeile: Shop-Dual-Pack 20 mg ohne Katalogzeile: mind. 1,30 x Vial-Pack (550) = 720 EUR (E3)
FINDINGS = []                                             # alle Befunde, werden am Ende geschrieben


# ---------------------------------------------------------------- Hilfen
def money(s):
    s = (s or '').strip()
    return None if s == '' else F(Decimal(s))


def read(path):
    with open(path, encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh, delimiter=';'))


def eur(x):
    return '-' if x is None else f'{float(x):,.2f}'.replace(',', ' ').replace('.', ',')


def pct(new, old):
    return None if not old else float(100 * (F(new) - F(old)) / F(old))


def rowname(r):
    return f"{r['level']}/{r['form']} {r['substance']} {r['strength']}"


def key(r):
    return (r['level'], r['form'], r['substance'], r['strength'])


def note(regel, schwere, zeile, text, alt=None, neu=None, **extra):
    d = dict(regel=regel, schwere=schwere, zeile=zeile, text=text, alt=None if alt is None else float(alt), neu=None if neu is None else float(neu),
             prozent=None if (alt is None or neu is None) else round(pct(neu, alt), 1), test=CUR_TEST[0])
    d.update(extra)
    FINDINGS.append(d)
    return d


def fmt(d):
    s = f"[{d['regel']}/{d['schwere']}] {d['zeile']}: {d['text']}"
    if d.get('alt') is not None and d.get('neu') is not None:
        s += f" | alt {eur(d['alt'])} -> neu {eur(d['neu'])} ({d['prozent']:+.1f} %)"
    return s


class Daten:
    """Lazy geladene Eingaben, einmal je Lauf."""
    _done = False

    @classmethod
    def load(cls):
        if cls._done:
            return
        cls.tab = read(TABELLE)
        cls.zei = read(ZEILEN)
        for r in cls.tab:
            r['p'] = money(r['price_new_eur'])
            r['p_ist'] = money(r['price_old_eur'])
            r['d'] = F(Decimal(r['dose']))
        cls.z = {key(r): r for r in cls.zei}
        for r in cls.zei:
            r['p'] = money(r['neu_eur'])
            r['alt'] = money(r['alte_liste_eur'])
            r['ek'] = money(r['ek_je_zeile_eur_INTERN'])
            r['d'] = F(Decimal(r['dose']))
        cls.exc = read(AUSNAHMEN)
        snap = json.loads((IN / 'alte_liste_snapshot.json').read_text())
        lines, cls.focus = snap['lines'], snap['focus']
        cls.alt_quelle = 'Snapshot'
        try:    # Live-Gegenprobe (nur lesen); weicht sie vom Snapshot ab, schlaegt test_eingaben fehl
            sys.path.insert(0, str(LIVE_TOOLS))
            import catalog_lines as cl
            live = [dict(form=x['form'], name=x['name'], strength=x['strength'], price_cents=x['price_cents']) for x in cl.lines(adjusted=False)]
            cls.alt_live_gleich = (live == lines)
            lines, cls.alt_quelle = live, 'cl.lines(adjusted=False) live'
            m = re.search(r'^FOCUS\s*=\s*\(([^)]*)\)', LIVE_EMPFEHLUNG.read_text(), re.M)
            cls.focus = re.findall(r"'([^']+)'", m.group(1))
        except Exception as exc:   # kein Live-Zugriff: Snapshot gilt
            cls.alt_live_gleich = None
            cls.alt_live_fehler = repr(exc)
        cls.alt = {(x['form'], x['name'], x['strength']): F(x['price_cents'], 100) for x in lines}
        cls.refs = json.loads((IN / 'references.json').read_text())
        cls.ref_by = {(r['level'], r['form'], r['substance'], r['strength']): r for r in cls.refs['rows']}
        with open(IN / 'anker_v2.csv', encoding='utf-8-sig', newline='') as fh:
            cls.anker = {r['product_id']: r for r in csv.DictReader(fh, delimiter=';')}
        cls._done = True

    @classmethod
    def ladders(cls, rows=None):
        out = defaultdict(list)
        for r in (rows or cls.zei):
            if r['unit'].lower() in ('mg', 'iu'):
                out[(r['level'], r['form'], r['gruppe'], r['unit'].lower())].append(r)
        for v in out.values():
            v.sort(key=lambda r: r['d'])
        return out

    @classmethod
    def shop_pairs(cls):
        """54 Einzel-Shopzeilen -> zugehoeriger 10er-Pack (Preis, Quelle). Pack-Preis None, wenn keine Zeile existiert."""
        packs = {(r['shop_produkt'], r['form']): r for r in cls.zei if r['level'] == 'pack' and r['shop_produkt']}
        out = []
        for e in cls.zei:
            if e['level'] == 'einzel' and e['shop_produkt']:
                pk = packs.get((e['shop_produkt'], e['form']))
                if pk is not None:
                    out.append((e, pk, pk['p'], 'Tabelle'))
                else:
                    out.append((e, None, SHOP_ONLY_PACKS.get((e['shop_produkt'], e['form'])), 'Shop-Wert ohne Katalogzeile'))
        return out


def setUpModule():
    Daten.load()


def tearDownModule():
    HERE.mkdir(parents=True, exist_ok=True)
    base = HERE / f'test_vorgaben_befunde{SUFFIX}'
    base.with_suffix('.json').write_text(json.dumps(FINDINGS, ensure_ascii=False, indent=1))
    lines = [f'# Befunde Register-Test ({TABELLE.name})', '', f'Anzahl: {len(FINDINGS)}', '']
    for sev in ('HART', 'AUSLEGUNG', 'INFO', 'LUECKE'):
        sub = [d for d in FINDINGS if d['schwere'] == sev]
        if sub:
            lines += [f'## {sev} ({len(sub)})', '']
            lines += ['- ' + fmt(d) for d in sub]
            lines.append('')
    base.with_suffix('.md').write_text('\n'.join(lines))


class Basis(unittest.TestCase):
    def setUp(self):
        CUR_TEST[0] = self._testMethodName

    def meld(self, regel, schwere, items, header):
        """Befunde registrieren; Test faellt bei HART/AUSLEGUNG."""
        if schwere in ('HART', 'AUSLEGUNG') and items:
            self.fail(f'{header}: {len(items)} Verletzung(en)\n  ' + '\n  '.join(fmt(d) for d in items))


# ---------------------------------------------------------------- Eingangspruefung
class T00_Eingaben(Basis):
    def test_eingaben_konsistent(self):
        D = Daten
        self.assertEqual(len(D.tab), len(D.zei), 'tabelle und zeilen unterschiedlich lang')
        self.assertEqual(len({key(r) for r in D.tab}), len(D.tab), 'doppelte Zeilen-Identitaeten in tabelle')
        bad = [rowname(r) for r in D.tab if key(r) not in D.z or D.z[key(r)]['p'] != r['p']]
        self.assertEqual(bad, [], 'tabelle und zeilen nennen unterschiedliche Preise')
        self.assertEqual(sum(1 for r in D.tab if r['level'] == 'pack'), 340)
        self.assertEqual(sum(1 for r in D.tab if r['level'] == 'einzel'), 54)
        if D.alt_live_gleich is not None:
            self.assertTrue(D.alt_live_gleich, 'Live-Altliste weicht vom Snapshot ab')
        falsch = []
        for r in D.zei:
            if r['level'] == 'pack':
                a = D.alt.get((r['form'], r['substance'], r['strength']))
                if (a is None) != (r['alt'] is None) or (a is not None and a != r['alt']):
                    falsch.append(rowname(r))
        self.assertEqual(falsch, [], 'alte_liste_eur in zeilen_v3 weicht von cl.lines(adjusted=False) ab')

    def test_S1_identitaeten_komplett(self):
        """S1: kein Produkt faellt weg: gleiche 394 Identitaeten wie die Ist-Tabelle; Reta/Tirz/Sema vorhanden."""
        ist = {(r['level'], r['form'], r['substance'], r['strength']) for r in read(IN / 'ist_tabelle.csv')}
        neu = {key(r) for r in Daten.tab}
        self.assertEqual(sorted(ist - neu), [], 'Zeilen fehlen')
        self.assertEqual(sorted(neu - ist), [], 'Zeilen ohne Ist-Gegenstueck')
        self.assertTrue({'Retatrutide', 'Tirzepatide', 'Semaglutide'} <= {r['substance'] for r in Daten.tab})

    def test_K5_R1_tabelle_ohne_intern(self):
        """R1/K5: die teilbare Tabelle hat nur die 8 Schema-Spalten (kein EK) und nennt keinen Lieferanten."""
        with open(TABELLE, encoding='utf-8-sig') as fh:
            head = fh.readline().strip().split(';')
        self.assertEqual(head, ['level', 'form', 'substance', 'strength', 'dose', 'unit', 'price_old_eur', 'price_new_eur'])
        text = TABELLE.read_text()
        self.assertIsNone(re.search(r'\b(Ting|Sing|Singt|Sink)\b', text), 'Lieferantenname in Tabelle')

    def test_S3_tabelle_ohne_rechtstexte(self):
        """S3 (stichprobenhaft): keine Rechts-/Compliance-Woerter in der teilbaren Tabelle."""
        text = TABELLE.read_text().lower()
        treffer = [w for w in ('compliance', 'rechtlich', 'zulassung', 'arzneimittel', 'haftung', 'gesetz') if w in text]
        self.assertEqual(treffer, [])


# ---------------------------------------------------------------- P1
class T01_P1(Basis):
    def pairs(self, level):
        by = defaultdict(dict)
        for r in Daten.zei:
            if r['level'] == level:
                by[(r['substance'], r['d'], r['unit'].lower())][r['form']] = r
        return {k: v for k, v in by.items() if 'vial' in v and 'dual' in v}

    def _check(self, level):
        bad = []
        pairs = self.pairs(level)
        for k, v in sorted(pairs.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            vi, du = v['vial'], v['dual']
            if not du['p'] > vi['p']:
                bad.append(note('P1', 'HART', rowname(du), f"Doppelkammer {eur(du['p'])} nicht teurer als Vial {eur(vi['p'])}", alt=vi['p'], neu=du['p']))
        return bad, pairs

    def test_P1_einzel_dual_teurer_als_vial(self):
        bad, pairs = self._check('einzel')
        self.assertGreaterEqual(len(pairs), 27)
        self.meld('P1', 'HART', bad, 'P1 Einzel')

    def test_P1_pack_dual_teurer_als_vial(self):
        bad, pairs = self._check('pack')
        self.assertGreaterEqual(len(pairs), 100)
        self.meld('P1', 'HART', bad, 'P1 Pack')

    def test_P1_abstand_info(self):
        """Register: Abstand 'ca. +15 %'. Modell erzwingt >= +30 % (R4). Nur Befund: Verteilung."""
        info = []
        for level in ('einzel', 'pack'):
            gaps = sorted(float(100 * (v['dual']['p'] / v['vial']['p'] - 1)) for v in self.pairs(level).values())
            med = gaps[len(gaps) // 2]
            info.append(note('P1', 'INFO', level, f"Dual-Aufschlag gegen Vial: Median {med:.0f} %, Min {gaps[0]:.0f} %, Max {gaps[-1]:.0f} %, "
                             f"{sum(1 for g in gaps if g > 50)} von {len(gaps)} ueber +50 % (Register: ca. +15 %)"))
        self.meld('P1', 'INFO', info, 'P1 Abstand')


# ---------------------------------------------------------------- P2
def exc_pairs(rules):
    out = set()
    for x in Daten.exc:
        if x['regel'] in rules and x['level'] in ('pack', 'einzel'):
            out.add((x['level'], x['form'], x['substance'], x['zeile_klein_oder_einzel'], x['zeile_gross_oder_pack']))
    return out


class T02_P2(Basis):
    def test_P2_preis_steigt_und_je_mg_faellt(self):
        ex = exc_pairs({'R1', 'R2'})
        bad, n = [], 0
        for (level, form, grp, unit), lst in sorted(Daten.ladders().items()):
            for a, b in zip(lst, lst[1:]):
                if b['d'] == a['d']:
                    bad.append(note('P2', 'HART', rowname(b), f"zwei Zeilen mit gleicher Dosis {b['d']} in einer Leiter"))
                    continue
                n += 1
                pair = (level, form, a['substance'], a['strength'], b['strength'])
                steigt = b['p'] > a['p']
                faellt = b['p'] / b['d'] < a['p'] / a['d']
                if (not steigt or not faellt) and pair not in ex:
                    bad.append(note('P2', 'HART', rowname(b), f"{'Preis steigt nicht' if not steigt else ''}{' und ' if not steigt and not faellt else ''}"
                                    f"{'Preis je Einheit faellt nicht' if not faellt else ''} gegen {a['strength']} ({eur(a['p'])} -> {eur(b['p'])}; "
                                    f"je Einheit {float(a['p'] / a['d']):.3f} -> {float(b['p'] / b['d']):.3f})", alt=a['p'], neu=b['p']))
        self.assertGreater(n, 150)
        self.meld('P2', 'HART', bad, 'P2 Leiter')

    def test_P2_stufenabstand_proportional(self):
        """Eddys Negativbeispiele (Reta 40->50 nur +30, 60->100 +40): Aufschlag mind. 40 % des proportionalen Zuwachses (Audit-R3-Formel, Modellannahme).
        Ausnahmen nur aus ausnahmen_v3.csv (Regel R3)."""
        ex = exc_pairs({'R3'})
        bad = []
        for (level, form, grp, unit), lst in sorted(Daten.ladders().items()):
            for a, b in zip(lst, lst[1:]):
                if b['d'] <= a['d']:
                    continue
                if b['p'] * a['d'] < a['p'] * (F(3, 5) * a['d'] + F(2, 5) * b['d']):
                    pair = (level, form, a['substance'], a['strength'], b['strength'])
                    if pair not in ex:
                        soll = a['p'] * (F(3, 5) * a['d'] + F(2, 5) * b['d']) / a['d']
                        bad.append(note('P2', 'HART', rowname(b), f"Stufenabstand zu klein gegen {a['strength']} {eur(a['p'])}; Mindestpreis {eur(soll)}", alt=soll, neu=b['p']))
        self.meld('P2', 'HART', bad, 'P2 Stufenabstand')


# ---------------------------------------------------------------- P3
class T03_P3(Basis):
    def test_P3_packs_volle_zehner(self):
        bad = []
        for r in Daten.zei:
            if r['level'] == 'pack' and r['p'] % 10 != 0:
                bad.append(note('P3', 'HART', rowname(r), f"Pack {eur(r['p'])} ist kein volles Zehner", neu=r['p']))
        for k, v in SHOP_ONLY_PACKS.items():
            if v % 10:
                bad.append(note('P3', 'HART', str(k), 'Shop-Pack ohne Katalogzeile nicht auf Zehner', neu=v))
        self.meld('P3', 'HART', bad, 'P3 Zehnerrundung')

    def test_P3_einzel_komma90_info(self):
        n = [r for r in Daten.zei if r['level'] == 'einzel' and r['p'] % 1 != F(9, 10)]
        self.meld('P3', 'INFO', [note('P3', 'INFO', 'einzel', f'{len(n)} von 54 Einzelpreisen enden nicht auf ,90 (Register: KEIN hartes ,90-Gate)')], 'P3 Info')


# ---------------------------------------------------------------- P4 (weich) / P10 (weich)
class T04_P4_P10(Basis):
    def test_P4_einzel_gegen_markt_info(self):
        """Einzel-Vial <= belegter Marktmedian (anker_v2.csv: vial_market_median_eur). Nur Befund (Register: Vergleich mit belegtem Angebot)."""
        info = []
        for e in Daten.zei:
            if e['level'] == 'einzel' and e['form'] == 'vial' and e['shop_produkt']:
                a = Daten.anker.get(e['shop_produkt'])
                if a and a['vial_market_median_eur']:
                    med = F(Decimal(a['vial_market_median_eur']))
                    if e['p'] > med:
                        info.append(note('P4', 'INFO', rowname(e), f"Einzel ueber Marktmedian {eur(med)}", alt=med, neu=e['p']))
        self.meld('P4', 'INFO', info, 'P4')

    def test_P10_bac_water_info(self):
        info = [note('P10', 'INFO', rowname(r), f"Bac. Water {eur(r['p'])} (Register: 3 ml 20 / 10 ml 40 = zu hoch)", neu=r['p'])
                for r in Daten.zei if r['gruppe'].startswith('bacteriostatic')]
        self.meld('P10', 'INFO', info, 'P10')


# ---------------------------------------------------------------- P5
def zeile(level, form, gruppe, dose):
    for r in Daten.zei:
        if r['level'] == level and r['form'] == form and r['gruppe'] == gruppe and r['d'] == F(dose):
            return r
    return None


class T05_P5_Anker(Basis):
    """Plausibilitaetsfaelle mit Kontext; keine pauschalen Festpreise (Register P5)."""

    def test_P5_reta30_einzel_nicht_20390(self):
        r = zeile('einzel', 'vial', 'retatrutide', 30)
        self.assertIsNotNone(r)
        bad = []
        if r['p'] >= F('203'):
            bad.append(note('P5', 'HART', rowname(r), 'Reta 30 mg Einzel wieder auf Abgelehnt-Niveau (203,90)', alt=F('203.90'), neu=r['p']))
        if r['p'] > F('129.90'):
            bad.append(note('P5', 'AUSLEGUNG', rowname(r), 'ueber Eddys eigenem Reta-40-Verkauf 129,90 (30 mg darf nicht mehr kosten als 40 mg)', alt=F('129.90'), neu=r['p']))
        note('P5', 'INFO', rowname(r), f"Kontext: abgelehnt 203, Markt-Beispiel Reta 40 = 180, eigener Verkauf Reta 40 = 130; v3 = {eur(r['p'])}", neu=r['p'])
        self.meld('P5', 'HART', bad, 'P5 Reta 30')

    def test_P5_mots40_einzel_nahe_80(self):
        r = zeile('einzel', 'vial', 'mots-c', 40)
        dev = float(100 * (r['p'] - 80) / 80)
        note('P5', 'INFO', rowname(r), f"Kaufpreisbeispiel 80; v3 = {eur(r['p'])} ({dev:+.1f} % gegen 80)", alt=F(80), neu=r['p'])
        bad = []
        if abs(dev) > 15:
            bad.append(note('P5', 'HART', rowname(r), f'MOTS-C 40 mg Einzel {dev:+.1f} % neben Kaufpreisbeispiel 80 (Rahmen +-15 %)', alt=F(80), neu=r['p']))
        if r['p'] >= F('123'):
            bad.append(note('P5', 'HART', rowname(r), 'MOTS-C 40 mg Einzel wieder auf abgelehntem Niveau 123,90', alt=F('123.90'), neu=r['p']))
        self.meld('P5', 'HART', bad, 'P5 MOTS-C 40')

    def test_P5_ghk_dual_ca_100(self):
        r = zeile('einzel', 'dual', 'ghk-cu', 100)
        dev = float(100 * (r['p'] - 100) / 100)
        note('P5', 'INFO', rowname(r), f"ca. 100 glatt inkl. Pen; v3 = {eur(r['p'])} ({dev:+.1f} %)", alt=F(100), neu=r['p'])
        bad = [] if abs(dev) <= 5 else [note('P5', 'HART', rowname(r), f'GHK-Cu Doppelkammer {dev:+.1f} % neben 100 (Rahmen +-5 %)', alt=F(100), neu=r['p'])]
        self.meld('P5', 'HART', bad, 'P5 GHK-Cu Dual')

    def test_P5_mots40_dual_nicht_17590(self):
        r = zeile('einzel', 'dual', 'mots-c', 40)
        bad = [] if r['p'] < F('175') else [note('P5', 'HART', rowname(r), 'MOTS-C 40 mg Doppelkammer wieder auf kritisiertem Niveau 175', alt=F('175'), neu=r['p'])]
        self.meld('P5', 'HART', bad, 'P5 MOTS-C Dual')

    def test_P5_reta40_einzel_luecke(self):
        """Reta 40 Einzel (130 eigener Verkauf, 180 Markt): Zeile fehlt in v3 (Szenario B). Nicht pruefbar -> LUECKE mit Kontext."""
        r = zeile('einzel', 'vial', 'retatrutide', 40)
        pk = zeile('pack', 'vial', 'retatrutide', 40)
        r30 = zeile('einzel', 'vial', 'retatrutide', 30)
        if r is None:
            lo, hi = pk['p'] / 10 / F(58, 100), pk['p'] / 10 / F(42, 100)
            note('P5', 'LUECKE', 'einzel/vial Retatrutide 40 mg', f"Einzelzeile fehlt; Pack 40 mg = {eur(pk['p'])} -> Einzel im 42-58-%-Korridor {eur(lo)}..{eur(hi)}; "
                 f"130 waere {float(100 * pk['p'] / 10 / 130):.1f} % Packanteil; Reta 30 Einzel = {eur(r30['p'])} -> 130 waere nur {float(100 * (130 / r30['p'] - 1)):+.1f} % fuer +33 % Dosis")
            self.skipTest('Reta-40-Einzelzeile fehlt (Szenario B) - nicht pruefbar, siehe Befund LUECKE')
        self.assertLessEqual(r['p'], F('180'))


# ---------------------------------------------------------------- P6
class T06_P6(Basis):
    def test_P13_alle_packs_mind_60_prozent_marge(self):
        bad, ohne, n = [], [], 0
        for r in Daten.zei:
            if r['level'] != 'pack':
                continue
            if r['ek'] is None:
                ohne.append(rowname(r))
                continue
            n += 1
            if r['p'] < F(5, 2) * r['ek']:     # Register P13 (Eddy 25.10.2026): Mindestmarge 60 % fuer ALLE Packs = 2,5 x EK, hart
                bad.append(note('P6', 'HART', rowname(r), f"Pack {eur(r['p'])} < 2,5 x EK (Mindestmarge 60 %) {eur(r['ek'])} (Faktor {float(r['p'] / r['ek']):.3f})", neu=r['p'], ek=float(r['ek'])))
        self.assertGreater(n, 330)
        for z in ohne:
            note('P6', 'LUECKE', z, 'EK fehlt: 2,5-x-Grenze (60 % Marge) nicht pruefbar')
        self.meld('P6', 'HART', bad, 'P6 Mindestmarge')

    def test_P6_ziel_2_5_info(self):
        low = [r for r in Daten.zei if r['level'] == 'pack' and r['ek'] is not None and r['p'] < F(5, 2) * r['ek']]
        info = [note('P6', 'INFO', rowname(r), f"Faktor {float(r['p'] / r['ek']):.2f} < 2,5 (Ziel 2,5-3,0)", neu=r['p'], ek=float(r['ek'])) for r in low]
        if VERHANDLUNG:     # team4: jede Zeile unter 2,5 x EK muss mit Ziel-EK in der Verhandlungsliste stehen
            vl = {(x['form'], x['substance'], x['strength']) for x in read(VERHANDLUNG)}
            fehlt = [note('P6', 'HART', rowname(r), 'Faktor < 2,5 und nicht in der Verhandlungsliste', neu=r['p'], ek=float(r['ek'])) for r in low if (r['form'], r['substance'], r['strength']) not in vl]
            self.meld('P6', 'HART', fehlt, 'P6 Verhandlungsliste unvollstaendig')
            erwartet = {(r['form'], r['substance'], r['strength']) for r in low}
            if KONFLIKTE:     # team5: Zeilen, deren Haendlerdeckel unter 2,5 x EK faellt, gehen ebenfalls an den Lieferanten
                for x in read(KONFLIKTE):
                    if x['Lieferant verhandeln'] == 'ja':
                        erwartet.add((x['Form'], x['Produkt'], x['Dosis']))
            self.assertEqual(vl, erwartet, 'Verhandlungsliste und (Zeilen < 2,5 x EK + Deckel-Konflikte mit EK-Ursache) stimmen nicht ueberein')


# ---------------------------------------------------------------- P7
class T07_P7(Basis):
    def vial_focus_rows(self, substances):
        return [r for r in Daten.zei if r['level'] == 'pack' and r['form'] == 'vial' and r['substance'] in substances and r['alt'] is not None]

    def test_P7_fokus_vial_packs_nicht_unter_alter_liste(self):
        """Fokus laut Register/Code (empfehlung.FOCUS): GHK-Cu, 5-Amino-1MQ, Retatrutide. Reta 15/20 sind durch P9 (neuere Inhaberentscheidung) gedeckt, werden aber gelistet."""
        rows = self.vial_focus_rows(set(Daten.focus))
        self.assertGreaterEqual(len(rows), 15)
        p9 = {('Retatrutide', '15 mg'), ('Retatrutide', '20 mg')}
        bad = []
        for r in rows:
            if r['p'] < r['alt']:
                e2 = (r['substance'], r['strength']) == ('Retatrutide', '60 mg')   # team4: dokumentierter Entscheidungsfall E2 (Altlistenfehler, Empfehlung 860)
                gedeckt = (r['substance'], r['strength']) in p9   # Gate-Kopie: E2 (Reta 60) bleibt HART rot; release.py erwartet es nur bei Eddys Ja (entscheidungen_eddy.json)
                d = note('P7', 'INFO' if gedeckt else 'HART', rowname(r),
                         ('gedeckt durch P9 (Inhaberentscheidung 400/430); ' if (r['substance'], r['strength']) in p9 else 'Entscheidungsfall E2 (Reta 60); ' if e2 else '') + f"Ursache: {r['angewendete_regel']}", alt=r['alt'], neu=r['p'], gedeckt_durch_P9=gedeckt)
                if not gedeckt:
                    bad.append(d)
        self.meld('P7', 'HART', bad, 'P7 Fokus unter alter Liste')

    def test_P7x_mots_c_vial_packs_auslegung(self):
        """AUSLEGUNG: MOTS-C ist Fokus der Lieferantenliste (R2) und wird im Shop wie ein Fokusprodukt behandelt; P7 nennt es nicht. Befund trotzdem hart gelistet."""
        rows = self.vial_focus_rows({'MOTS-c'})
        bad = [note('P7', 'HART', rowname(r), f"Entscheidungsfall E1 (MOTS-C-Packs bleiben gesenkt, Empfehlung Nein zur alten Liste); Ursache: {r['angewendete_regel']}", alt=r['alt'], neu=r['p']) for r in rows if r['p'] < r['alt']]
        self.meld('P7', 'HART', bad, 'P7x MOTS-C (E1)')   # Gate-Kopie: HART, release.py erwartet es gemaess entscheidungen_eddy.json

    def test_P7y_alle_vial_packs_info(self):
        """Info: Original MSG 82562 'Die alte Preisliste ist die Untergrenze? Ja' ist weiter als das Register (nur Fokus). Zaehlung ueber alle Vial-Packs."""
        rows = [r for r in Daten.zei if r['level'] == 'pack' and r['form'] == 'vial' and r['alt'] is not None]
        low = [r for r in rows if r['p'] < r['alt']]
        low10 = [r for r in low if r['p'] < F(9, 10) * r['alt']]
        note('P7', 'INFO', 'alle Vial-Packs', f"{len(low)} von {len(rows)} Vial-Packs unter alter Liste, davon {len(low10)} um mehr als 10 %")


# ---------------------------------------------------------------- P8
class T08_P8(Basis):
    def test_P8_pack_je_stueck_unter_einzel(self):
        pairs = Daten.shop_pairs()
        self.assertEqual(len(pairs), 54)
        bad, ohne = [], []
        for e, pk, price, quelle in pairs:
            if price is None:
                ohne.append(rowname(e))
                continue
            if not price / 10 < e['p']:
                bad.append(note('P8', 'HART', rowname(e), f"Pack/10 = {eur(price / 10)} nicht unter Einzel {eur(e['p'])}", alt=e['p'], neu=price / 10))
        self.assertEqual(ohne, [], 'Einzelzeile ohne Packpreis')
        self.meld('P8', 'HART', bad, 'P8 Pack je Stueck')

    def test_P8_korridor_info(self):
        """Korridor offen (Inhaberentscheidung): Befund ueber 60 % (obere Kante Eddy-Regressionstest 48-60 %) und unter 42 %; Vial/Dual-Abstand je Produkt."""
        info, share = [], {}
        for e, pk, price, quelle in Daten.shop_pairs():
            s = float(100 * price / 10 / e['p'])
            share[(e['shop_produkt'], e['form'])] = s
            if s > 58 or s < 42:
                info.append(note('P8', 'INFO', rowname(e), f"Packanteil {s:.1f} % ausserhalb 42-58 %", neu=e['p'], anteil=round(s, 1)))
        spread = sorted(((abs(share[(p, 'vial')] - share[(p, 'dual')]), p) for (p, f) in share if f == 'vial'), reverse=True)
        info.append(note('P8', 'INFO', 'Vial/Dual-Paare', 'groesste Anteilsabstaende Vial gegen Dual (Prozentpunkte): ' + ', '.join(f'{p} {d:.1f}' for d, p in spread[:6])))
        self.meld('P8', 'INFO', info, 'P8 Korridor')


# ---------------------------------------------------------------- P9
class T09_P9(Basis):
    def test_P9_reta_packs_15_400_20_430(self):
        bad = []
        for dose, soll in ((15, 400), (20, 430)):
            r = zeile('pack', 'vial', 'retatrutide', dose)
            self.assertIsNotNone(r, f'Reta {dose} Pack fehlt')
            if r['p'] != soll:
                bad.append(note('P9', 'HART', rowname(r), f'Reta {dose} mg Pack muss {soll} sein', alt=F(soll), neu=r['p']))
        self.meld('P9', 'HART', bad, 'P9')


# ---------------------------------------------------------------- P11
class T11_P11(Basis):
    def test_P11_ek_ohne_zuschlag(self):
        """EK je Zeile in zeilen_v3 == cost10_eur der unabhaengigen Quelle references.json (Ting-Preis, Labels/Verpackung inklusive) -> kein Zuschlag."""
        bad, n = [], 0
        for r in Daten.zei:
            ref = Daten.ref_by.get(key(r))
            self.assertIsNotNone(ref, rowname(r))
            c = ref.get('cost10_eur')
            if r['level'] == 'pack':
                n += 1
                if (c is None) != (r['ek'] is None) or (c is not None and r['ek'] != F(Decimal(str(c))).limit_denominator(100)):
                    bad.append(note('P11', 'HART', rowname(r), f"EK in zeilen {r['ek']} != Quelle {c} (moeglicher Zuschlag/Doppelzaehlung)"))
        self.assertGreater(n, 330)
        self.meld('P11', 'HART', bad, 'P11 EK-Gleichheit')

    def test_P11_kein_zuschlag_im_modellcode(self):
        """Keine Zuschlagsspalte/-konstante fuer Labels/Verpackung in den Ergebnisdateien; Faktor-Spalte == Preis/EK."""
        head = ' '.join(Daten.zei[0].keys()).lower()
        self.assertIsNone(re.search(r'etikett|label|verpack|zuschlag|packaging|versand', head), 'Zuschlagsspalte in zeilen')
        bad = []
        for r in Daten.zei:
            if r['level'] == 'pack' and r['ek'] is not None and r['faktor_x_ek_neu']:
                f = F(Decimal(r['faktor_x_ek_neu']))
                if abs(f - r['p'] / r['ek']) > F(1, 100):
                    bad.append(note('P11', 'HART', rowname(r), f"Faktor in Datei {f} != Preis/EK {float(r['p'] / r['ek']):.3f}"))
        self.meld('P11', 'HART', bad, 'P11 Faktor')


# ---------------------------------------------------------------- Abdeckung Register -> Test
# 'test' = Name der Testmethode in diesem Modul; 'grund' = begruendete Nicht-Pruefbarkeit (mit Ersatzkontrolle)
ABDECKUNG = {
    'P1': dict(test=['test_P1_einzel_dual_teurer_als_vial', 'test_P1_pack_dual_teurer_als_vial']),
    'P2': dict(test=['test_P2_preis_steigt_und_je_mg_faellt', 'test_P2_stufenabstand_proportional']),
    'P3': dict(test=['test_P3_packs_volle_zehner']),
    'P4': dict(test=['test_P4_einzel_gegen_markt_info'], grund='weich (Vergleich mit belegtem Angebot): nur Befund, kein Gate'),
    'P5': dict(test=['test_P5_reta30_einzel_nicht_20390', 'test_P5_mots40_einzel_nahe_80', 'test_P5_ghk_dual_ca_100', 'test_P5_mots40_dual_nicht_17590',
                     'test_P5_reta40_einzel_luecke']),
    'P6': dict(test=['test_P13_alle_packs_mind_60_prozent_marge']),
    'P7': dict(test=['test_P7_fokus_vial_packs_nicht_unter_alter_liste', 'test_P7x_mots_c_vial_packs_auslegung']),
    'P8': dict(test=['test_P8_pack_je_stueck_unter_einzel']),
    'P9': dict(test=['test_P9_reta_packs_15_400_20_430']),
    'P10': dict(test=['test_P10_bac_water_info'], grund='weich: nur Befund'),
    'P11': dict(test=['test_P11_ek_ohne_zuschlag', 'test_P11_kein_zuschlag_im_modellcode']),
    'P12': dict(test=['test_P12_keine_leere_preiszelle']),   # team4: Register-Regel P12 (nachgetragen 25.10.)
    'P13': dict(test=['test_P13_alle_packs_mind_60_prozent_marge']),   # Register P13 (Eddy 25.10.2026): Mindestmarge 60 % (= 2,5 x EK) fuer ALLE Packs, hart
    'K1': dict(grund='Shop-Kondition (Mindestbestellwert), steht nicht in der Preistabelle; Kontrolle: Haendler-Browser-QA (team/qa), Staging-Test'),
    'K2': dict(grund='Versandregel im Shop-Code (terms.js), nicht Teil der Preistabelle; Kontrolle: Konditionsrechnung der QA'),
    'K3': dict(grund='Mengenrabatt/Gratisversand-Balken/Bot-Liste sind Funktionen; Rabattfaehigkeit haengt an Marge >= 60 % (nicht in der Tabelle)'),
    'K4': dict(grund='Textinhalt im Shop (Export/Fokus 10er/Lieferzeit); keine Preisaussage'),
    'K5': dict(test=['test_K5_R1_tabelle_ohne_intern'], grund='Teilpruefung: Lieferantenname in teilbarer Tabelle; Shop-Texte separat (Marketing-QA)'),
    'S1': dict(test=['test_S1_identitaeten_komplett'], grund='Teilpruefung: 394 Identitaeten + Reta/Tirz/Sema; Katalogvollstaendigkeit im Shop separat'),
    'S2': dict(grund='Bildregel (Pixelmessung + Sichtpruefung), keine Tabellenregel'),
    'S3': dict(test=['test_S3_tabelle_ohne_rechtstexte'], grund='Stichprobe auf Woerter in der Tabelle; Shop-Texte separat'),
    'R1': dict(test=['test_K5_R1_tabelle_ohne_intern'], grund='Teilpruefung: teilbare Tabelle ohne EK-Spalten'),
    'R2': dict(grund='Prozess-/Lieferantenregel (eine Gesamtpreisliste an Ting nach Eddys Go); kein Tabellenmerkmal'),
    'R3': dict(grund='Ablage/Ordnerregel auf dem Desktop; kein Tabellenmerkmal'),
    'A1': dict(grund='Arbeitsablauf (ein Ja, dann Umsetzung); Gate ist dieser Test + Audit'),
    'A2': dict(grund='Arbeitsablauf: nur Antwort, nichts aendern; Kontrolle: git status / Pruefsummen im Bericht'),
    'A3': dict(grund='Qualitaetsregel fuer Lieferungen; durch diesen Testlauf operationalisiert (alle harten Tests muessen gruen sein)'),
}


class T12_P12(Basis):
    def test_P12_keine_leere_preiszelle(self):
        """P12 (hart): keine Zeile ohne Preis in der ausgelieferten Tabelle (Preise sind 394 Zeilen, alle gefuellt und > 0)."""
        bad = [note('P12', 'HART', rowname(r), 'leerer oder nicht positiver Preis', neu=r['p']) for r in Daten.tab if r['p'] is None or r['p'] <= 0]
        self.meld('P12', 'HART', bad, 'P12 leere Preise')
        self.assertEqual(len(Daten.tab), 394)


# ---------------------------------------------------------------- T13 (team5): Haendlerdeckel / Kundenvernunft
class T13_Haendlerdeckel(Basis):
    """Eddys zweites Ziel (Kundenpreise vernuenftig): Pack je Stueck <= 60 % vom Marktmedian (Haendlerspanne >= 40 %) bei jeder 10er-Pack-Zeile mit Marktdaten,
    ausser ein dokumentierter Konflikt in konflikte_F.csv. Exakte Bruchrechnung aus zeilen (neu_eur, markt_median_eur), unabhaengig vom Modell."""
    def setUp(self):
        if not KONFLIKTE:
            self.skipTest('KONFLIKTE_V3 nicht gesetzt (nur fuer Variante F)')

    def konflikte(self):
        return {(x['Form'], x['Produkt'], x['Dosis']): x for x in read(KONFLIKTE)}

    def test_T13_spanne_mind_40_oder_konflikt_mit_grund(self):
        kon = self.konflikte()
        mit_markt = [r for r in Daten.zei if r['level'] == 'pack' and money(r['markt_median_eur']) is not None]
        self.assertGreater(len(mit_markt), 90)
        unter = {(r['form'], r['substance'], r['strength']) for r in mit_markt if r['p'] > 6 * money(r['markt_median_eur'])}      # Pack/10 > 0,60 x Markt  <=>  Spanne < 40 %
        fehlt = [note('T13', 'HART', f'{k[0]} {k[1]} {k[2]}', 'Haendlerspanne < 40 % und nicht in konflikte_F.csv') for k in sorted(unter - set(kon))]
        zuviel = [note('T13', 'HART', f'{k[0]} {k[1]} {k[2]}', 'in konflikte_F.csv, aber Haendlerspanne >= 40 %') for k in sorted(set(kon) - unter)]
        leer = [note('T13', 'HART', f'{k[0]} {k[1]} {k[2]}', 'Konflikt ohne Grund') for k, x in kon.items() if not x['Grund'].strip()]
        self.meld('T13', 'HART', fehlt + zuviel + leer, 'T13 Haendlerspanne')
        for k in sorted(kon):
            x = kon[k]
            note('T13', 'INFO', f'{k[0]} {k[1]} {k[2]}', f"Spanne {x['Händlerspanne']} %, Preis {x['Preis neu']} (Deckel {x['Preis für 40 % Spanne']}), duenne Marktbasis: {x['dünne Marktbasis']}; {x['Grund']}")

    def test_T13_duenne_basis_nur_mit_deckel_ab_2_5x(self):
        """Duenne Marktbasis (n < 3): Deckel nur, wenn Deckel >= 2,5 x EK. Also: ist der Deckel < 2,5 x EK, bleibt der Preis wie in M1_E2 (Spalte 'Preis M1_E2')."""
        bad = []
        for k, x in self.konflikte().items():
            if x['dünne Marktbasis'] == 'ja' and F(Decimal(x['Faktor dabei'])) < F(5, 2) and x['Preis neu'] != x['Preis M1_E2']:
                bad.append(note('T13', 'HART', f'{k[0]} {k[1]} {k[2]}', 'duenne Marktbasis, Deckel < 2,5 x EK, aber Preis gegen M1_E2 veraendert'))
        self.meld('T13', 'HART', bad, 'T13 duenne Marktbasis')
        n_duenn = sum(1 for r in Daten.zei if r['level'] == 'pack' and r.get('duenne_marktbasis') == 'ja')
        note('T13', 'INFO', 'alle Packs', f'{n_duenn} Pack-Zeilen mit duenner Marktbasis (n < 3)')

    def test_T13_deckel_senkt_nie_unter_2_5x_ek_wo_gruen_moeglich(self):
        """Konfliktzeilen mit EK-Ursache bleiben bei Preis >= max(Deckel, 2,5 x EK) bzw. bisherigem Preis; keine Konfliktzeile liegt unter 2,5 x EK, nur weil der Deckel es verlangte."""
        bad = []
        for k, x in self.konflikte().items():
            neu, cap, ek = F(Decimal(x['Preis neu'])), F(Decimal(x['Preis für 40 % Spanne'])), F(Decimal(x['EK']))
            if x['Lieferant verhandeln'] == 'ja' and x['dünne Marktbasis'] == 'nein' and neu < F(5, 2) * ek and neu != F(Decimal(x['Preis M1_E2'])):
                bad.append(note('T13', 'HART', f'{k[0]} {k[1]} {k[2]}', f'Preis {neu} unter 2,5 x EK {ek} durch den Deckel {cap}'))
        self.meld('T13', 'HART', bad, 'T13 Deckel unter Gruen')


class T99_Abdeckung(Basis):
    def parse_register(self):
        ids, cur = {}, None
        for line in REGISTER.read_text().splitlines():
            m = re.match(r'^- id: (\w+)', line)
            if m:
                cur = m.group(1)
                ids[cur] = ''
            m2 = re.match(r'^  pruefbar: (.*)', line)
            if m2 and cur:
                ids[cur] = m2.group(1).strip("'\" ")
        return ids

    def test_jede_regel_hat_test_oder_begruendung(self):
        ids = self.parse_register()
        self.assertGreaterEqual(len(ids), 24, 'Register nicht vollstaendig gelesen')
        methoden = {n for c in (T00_Eingaben, T01_P1, T02_P2, T03_P3, T04_P4_P10, T05_P5_Anker, T06_P6, T07_P7, T08_P8, T09_P9, T11_P11, T12_P12) for n in dir(c) if n.startswith('test_')}
        fehl = []
        for rid, pruefbar in ids.items():
            a = ABDECKUNG.get(rid)
            if a is None:
                fehl.append(f'{rid}: kein Eintrag')
                continue
            for t in a.get('test', []):
                if t not in methoden:
                    fehl.append(f'{rid}: Test {t} existiert nicht')
            if pruefbar.lower().startswith('hart') and not a.get('test'):
                fehl.append(f'{rid}: Register sagt hart, aber kein Test')
            if not a.get('test') and not a.get('grund'):
                fehl.append(f'{rid}: weder Test noch Begruendung')
        extra = sorted(set(ABDECKUNG) - set(ids))
        self.assertEqual(fehl, [], 'Abdeckungsluecken')
        self.assertEqual(extra, [], 'Abdeckung nennt Regeln, die im Register fehlen')

    def test_abdeckungstabelle_ausgeben(self):
        ids = self.parse_register()
        out = ['| Regel | Register-Pruefbarkeit | Test / Begruendung |', '|---|---|---|']
        for rid in ids:
            a = ABDECKUNG[rid]
            tt = ', '.join(a.get('test', []))
            out.append(f"| {rid} | {ids[rid][:70] or '-'} | {tt}{' ; ' if tt and a.get('grund') else ''}{a.get('grund', '')} |")
        HERE.mkdir(parents=True, exist_ok=True)
        (HERE / f'regel_zu_test{SUFFIX}.md').write_text('# Regel -> Test (aus test_vorgaben.py, automatisch)\n\n' + '\n'.join(out) + '\n')


if __name__ == '__main__':
    unittest.main(verbosity=2)
