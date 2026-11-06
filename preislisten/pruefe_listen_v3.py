"""Maschinelle Pruefung aller Listen/PDFs aus pipeline_v3.sh gegen preisfamilie_v3.csv / preisempfehlung.json.

Je Datei: Seitenzahl, Render-Test (jede Seite als Bild, nicht leer -> _out/render/), Preisabgleich (Kundenliste vollstaendig X/340,
interne Dateien alle erkannten Zeilen, Pflicht-Stichproben), Leak-Suche, Vergleich mit dem Desktop-Stand (hoeher/niedriger/gleich).
Margenliste zusaetzlich: Kundensicht-Spalten (Haendlerspanne am Markt, Delta gegen alte Liste) aller 10er-Packs gegen die Kennzahlen-Datei
(ZEILEN_CSV, Standard wie marge_pdf.zeilen_csv), Tafel Seite 1, Seite 'Zeilen mit Aufmerksamkeit', Layout (Raender, Ueberlappung, Schrift >= 7 pt).
Liest nur; schreibt nur _out/pruefung_v3.json und _out/render/. Exit 1 bei Abweichung.
"""
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

import openpyxl
import pymupdf

HERE = Path(__file__).resolve().parent
S = HERE.parent
OUT = S / '_out'
D = OUT / 'desktop'
DESK = Path.home() / 'Desktop' / 'Elements_Lab'
TING, RENE, EDDY = '1 FÜR TING', '2 FÜR RENÉ', '3 FÜR EDDY (intern)'
MM = 72 / 25.4
SHOP_ONLY = {('dual', 'bpc-157+tb-500', '20mg(10mg+10mg)')}  # Shop-Dual-Pack ohne Tabellenzeile (apply_pricing.SHOP_ONLY_PACK)
MUST = [('vial', 'Retatrutide', '30 mg'), ('vial', 'Retatrutide', '40 mg'), ('vial', 'Retatrutide', '60 mg'), ('dual', 'Retatrutide', '30 mg'),
        ('dual', 'Retatrutide', '40 mg'), ('dual', 'Retatrutide', '60 mg'), ('vial', 'MOTS-c', '40 mg'), ('dual', 'MOTS-c', '40 mg'),
        ('dual', 'GHK-Cu', '100 mg'), ('dual', 'BPC-157 + TB-500', '20 mg (10 mg + 10 mg)'), ('vial', 'L-Carnitine', '600 mg'), ('vial', 'L-Carnitine', '1200 mg')]


def n(s):
    return re.sub(r'\s+', '', str(s)).lower().replace('–', '-')


def key(form, name, strength):
    return (form, n(name), n(strength))


def money(t):
    """'1.280 €' / '15,50 €' / '580,00' -> float; '–' -> None."""
    t = t.replace('€', '').replace('*', '').strip()
    if not t or t in ('–', '-'):
        return None
    return float(t.replace('.', '').replace(',', '.'))


# ---------------------------------------------------------------- Wahrheit
with open(HERE / 'preisfamilie_v3.csv', newline='', encoding='utf-8') as fh:
    TABLE = list(csv.DictReader(fh, delimiter=';'))
PACK = {key(r['form'], r['substance'], r['strength']): float(r['price_new_eur']) for r in TABLE if r['level'] == 'pack'}
OLD = {key(r['form'], r['substance'], r['strength']): float(r['price_old_eur']) for r in TABLE if r['level'] == 'pack'}
EMP = {key(x['form'], x['name'], x['strength']): x for x in json.loads((HERE / 'preisempfehlung.json').read_text())}
FORMATS = json.loads((S / 'miniapp/data/shop-formats.json').read_text())
for it in FORMATS:
    if it.get('format') == 'dual_pack' and not it.get('code') and it.get('line_name'):
        k = key('dual', it['line_name'], it['line_strength'])
        if k in SHOP_ONLY:
            PACK[k] = it['price_cents'] / 100
# Einzelpreise: Tabellenzeile -> Shop-Produkt (Zuordnung) -> Katalogzeile des Packs gleicher Basis
with open(HERE / 'preisfamilie_v3_shopzuordnung.csv', newline='', encoding='utf-8') as fh:
    SHOPMAP = {(r['level'], r['form'], r['substance'], r['strength']): r['shop_produkt'] for r in csv.DictReader(fh, delimiter=';')}
SINGLE, SINGLE_BY_NAME = {}, {}
for r in TABLE:
    if r['level'] != 'einzel':
        continue
    pid = SHOPMAP[('einzel', r['form'], r['substance'], r['strength'])]
    SINGLE_BY_NAME[key(r['form'], r['substance'], r['strength'])] = float(r['price_new_eur'])
    for it in FORMATS:
        if it.get('format') == ('vial_pack' if r['form'] == 'vial' else 'dual_pack') and it.get('base_product_id') == pid and it.get('line_name'):
            SINGLE[key(r['form'], it['line_name'], it['line_strength'])] = float(r['price_new_eur'])
problems = []
if len([k for k in PACK if k not in SHOP_ONLY]) != 340 or len(EMP) != 340:
    problems.append(f'Wahrheit: {len(PACK)} Packs in Tabelle, {len(EMP)} in preisempfehlung.json (erwartet 340)')
for k, v in EMP.items():
    if PACK.get(k) != float(v['price_eur']):
        problems.append(f'preisempfehlung.json weicht von Tabelle ab: {k} {v["price_eur"]} != {PACK.get(k)}')

# ---------------------------------------------------------------- Allgemeine Pruefungen
CUSTOMER_LEAKS = [r'\bting\b', r'aurenbi', r'einkauf', r'\bEK\b', r'marge', r'lieferant', r'hersteller', r'produzent', r'wholesale', r'supplier',
                  r'\bUSD\b', r'\$', r'peptidehaus', r'qsc', r'[\u3000-\u303f\u3400-\u9fff\uff00-\uffef]', r'whats\s*app', r'\bWA\b', r'telefon',
                  r'\+\d', r'\b0\d{3,}[ /-]?\d{4,}', r'https?:', r'www\.', r'\.(com|de|eu|net|org|cn)\b', r'@', r'gmbh', r'\bUG\b', r'\bltd\b',
                  r'firma', r'\bGMP\b', r'\bCOA\b', r'zertifi', r'rechtlich', r'zugelassen', r'compliance', r'einzelkammer', r'gratisversand', r'pauschal', r'packung\b']
TING_LEAKS = [r'\bverkauf', r'marge', r'\bVK\b', r'andere lieferant', r'peptidehaus', r'qsc', r'[\u3400-\u9fff]', r'whats\s*app', r'https?:', r'www\.']


def leaks(text, patterns):
    return sorted({m.group(0) for p in patterns for m in re.finditer(p, text, re.I)})


def render(path, tag):
    """Jede Seite als PNG (40 dpi) nach _out/render/<tag>/; Anteil nicht-weisser Pixel je Seite."""
    d = pymupdf.open(path)
    rd = OUT / 'render' / tag
    rd.mkdir(parents=True, exist_ok=True)
    for old in rd.glob('*.png'):
        old.unlink()
    ink = []
    for i, p in enumerate(d):
        pix = p.get_pixmap(dpi=40, colorspace=pymupdf.csGRAY)
        pix.save(rd / f'seite_{i + 1:02d}.png')
        ink.append(round(sum(1 for b in pix.samples if b < 235) / len(pix.samples), 4))
    return len(d), ink


def pdf_text(path):
    d = pymupdf.open(path)
    meta = ' '.join(str(v) for k, v in (d.metadata or {}).items() if v and 'date' not in k.lower())
    return '\n'.join(p.get_text() for p in d), meta, any(d[0].get_images())


def rows_by_y(page, tol=3.0):
    rows = []
    for w in sorted(page.get_text('words'), key=lambda w: ((w[1] + w[3]) / 2, w[0])):
        yc = (w[1] + w[3]) / 2
        if rows and abs(rows[-1][0] - yc) < tol:
            rows[-1][1].append(w)
        else:
            rows.append([yc, [w]])
    return [sorted(ws, key=lambda w: w[0]) for _, ws in rows]


# ---------------------------------------------------------------- Kundenpreisliste (neues Layout)
def parse_customer(path):
    """Spaltenraster aus make_pricelist.py: Produkt | Dosierung | Vial Einzel/10er/je Stueck | Doppelkammer Einzel/10er/je Stueck."""
    W = pymupdf.paper_size('a4')[0]
    m = 14 * MM
    cw = [24, 15, 18, 15, 15, 18, 15]
    edges = [m, W - m - sum(cw) * MM]
    for c in cw:
        edges.append(edges[-1] + c * MM)
    out = []
    for page in pymupdf.open(path):
        H = page.rect.height
        words = [w for w in page.get_text('words') if (w[1] + w[3]) / 2 < H - 12 * MM]
        heads = [(w[1] + w[3]) / 2 for w in words if w[4] == 'Produkt' and w[0] < m + 5]
        if not heads:
            continue
        words = [w for w in words if (w[1] + w[3]) / 2 > min(heads) - 34 and not any(h - 34 < (w[1] + w[3]) / 2 < h + 17 for h in heads)]
        col = lambda w: next((i for i in range(8) if edges[i] - 1 <= (w[0] + w[2]) / 2 < edges[i + 1] + 1), None)  # noqa: E731
        anchors = sorted({round((w[1] + w[3]) / 2, 1) for w in words if col(w) == 3 and re.match(r'^([\d.]+|–)$', w[4])})
        rows = {a: [[] for _ in range(8)] for a in anchors}
        for w in words:
            c, yc = col(w), (w[1] + w[3]) / 2
            if c is None or not anchors:
                continue
            a = min(anchors, key=lambda a: abs(a - yc))
            if abs(a - yc) <= 14:
                rows[a][c].append(w)
        for a in anchors:
            cells = [' '.join(x[4] for x in sorted(ws, key=lambda w: (round(w[1]), w[0]))) for ws in rows[a]]
            out.append(cells)
    return out


def check_customer_rows(cells_rows, label):
    res = dict(zeilen=len(cells_rows), packs_ok=0, packs_erwartet=len(PACK), einzel_ok=0, einzel_erwartet=len(SINGLE), stueck_ok=0, sterne_ok=0, fehler=[])
    seen = {}
    for c in cells_rows:
        name, dose = c[0], c[1]
        for form, off in (('vial', 2), ('dual', 5)):
            k = key(form, name, dose)
            single, pack, each = money(c[off]), money(c[off + 1]), money(c[off + 2])
            if pack is None:
                if k in PACK:
                    res['fehler'].append(f'{label}: fehlt Pack {k}')
                continue
            seen[k] = seen.get(k, 0) + 1
            if PACK.get(k) == pack:
                res['packs_ok'] += 1
            else:
                res['fehler'].append(f'{label}: Pack {k} = {pack} != Tabelle {PACK.get(k)}')
            if each is not None and abs(each - pack / 10) < 0.006:
                res['stueck_ok'] += 1
            else:
                res['fehler'].append(f'{label}: je Stück {k} = {each} != {pack / 10}')
            if pack % 10:
                res['fehler'].append(f'{label}: Pack {k} nicht auf volle 10 €')
            star = '*' in c[off + 1]
            want = (k in EMP and not EMP[k]['discount_ok'])
            if star == want:
                res['sterne_ok'] += 1
            else:
                res['fehler'].append(f'{label}: Stern {k} = {star}, erwartet {want}')
            if k in SINGLE:
                if single == SINGLE[k]:
                    res['einzel_ok'] += 1
                else:
                    res['fehler'].append(f'{label}: Einzel {k} = {single} != Tabelle {SINGLE[k]}')
            elif single is not None:
                res['fehler'].append(f'{label}: Einzelpreis ohne Tabellenzeile {k} = {single}')
    for k in PACK:
        if seen.get(k, 0) != 1:
            res['fehler'].append(f'{label}: Pack {k} {seen.get(k, 0)}x statt 1x')
    res['pflicht'] = {' '.join(k): ('ok' if key(*k) in seen else 'FEHLT') for k in MUST}
    return res, seen


def parse_customer_xlsx(path):
    ws = openpyxl.load_workbook(path).active
    rows, text = [], []
    for r in ws.iter_rows(values_only=True):
        text.append(' '.join('' if v is None else str(v) for v in r))
        if r and isinstance(r[4] if len(r) > 4 else None, (int, float)) or (r and len(r) > 7 and isinstance(r[7], (int, float))):
            fmt = lambda v: '–' if v is None else f'{v:.2f}'.replace('.', ',')  # noqa: E731
            stars = r[9] or ''
            rows.append([r[1], r[2], fmt(r[3]), fmt(r[4]) + (' *' if 'Vial' in stars else ''), fmt(r[5]),
                         fmt(r[6]), fmt(r[7]) + (' *' if 'Doppelkammer' in stars else ''), fmt(r[8])])
    wb = openpyxl.load_workbook(path)
    meta = f'{wb.properties.title} {wb.properties.creator}'
    return rows, '\n'.join(text) + '\n' + meta


def parse_old_customer(path):
    """Desktop-Stand: Produkt | Dosierung | Vial 10 Stueck | Doppelkammer 10 Stueck (Zeilen ohne Umbruch genuegen fuer den Vergleich)."""
    out = {}
    for page in pymupdf.open(path):
        hd = [w for w in page.get_text('words') if w[4] == 'Dosierung']
        if not hd:
            continue
        xd = hd[0][0]
        for ws in rows_by_y(page):
            name = ' '.join(w[4] for w in ws if w[0] < xd - 2)
            rest = [w for w in ws if w[0] >= xd - 2]
            toks = re.findall(r'(–|[\d.]+(?:,\d+)? €)', ' '.join(w[4] for w in rest))
            dose = re.split(r' (?:–|[\d.]+(?:,\d+)? €)', ' '.join(w[4] for w in rest))[0]
            if name and len(toks) >= 2:
                for form, t in zip(('vial', 'dual'), toks[-2:]):
                    if money(t) is not None:
                        out[key(form, name, dose)] = money(t)
    return out


# ---------------------------------------------------------------- interne PDFs (Spalten aus der jeweils letzten Kopfzeile)
VK_HEAD = {'VK': -20, 'Neuer': 22, 'Unser': 0}  # Kopfwort der Verkaufspreis-Spalte -> Versatz der rechtsbuendigen Zahl
CFG = {'marge', 'ting', 'top20'}


def parse_internal(path, kind):
    out = []
    form, level = 'vial', 'pack'
    hdr, prev = None, {}
    for page in pymupdf.open(path):
        for ws in rows_by_y(page):
            line = ' '.join(w[4] for w in ws)
            if kind == 'ting':
                if re.match(r'^1 · Vials', line):
                    form = 'vial'
                elif re.match(r'^2 · Doppelkammer', line):
                    form = 'dual'
                elif re.match(r'^[345] · ', line):
                    form = None
            if kind == 'marge' and re.match(r'^(Einzelverkauf|10er-Packs) · ', line):
                level = 'einzel' if line.startswith('Einzel') else 'pack'
                form = 'dual' if '· Doppelkammer' in line else 'vial'
            words = {w[4]: w for w in ws}
            first = 'Produkt' if 'Produkt' in words else 'Wirkstoff' if 'Wirkstoff' in words else None
            if first and 'Dosis' in words:
                hdr = dict(name=words[first][0] - 5, bereich=words['Bereich'][0] if 'Bereich' in words else None, dose=words['Dosis'][0] - 3)
                if kind == 'marge' and 'spanne' in words and 'gegen' in prev:  # Kundensicht-Spalten (rechtsbuendig: rechter Rand = x1 des Kopfworts)
                    hdr['sp'], hdr['dl'] = words['spanne'][2], prev['gegen'][2]
                for h, dx in VK_HEAD.items():
                    for src in (words, prev):
                        if h in src:
                            hdr['vk'] = src[h][0] + dx
                prev = words
                continue
            prev = words
            if not hdr or 'vk' not in hdr:
                continue
            prices = [(w[0], w[4]) for i, w in enumerate(ws) if re.match(r'^[\d.]+(,\d+)?$', w[4]) and i + 1 < len(ws) and ws[i + 1][4] == '€']
            near = [t for x, t in prices if abs(x - hdr['vk']) < 25]
            if not near:
                continue
            name_end = hdr['bereich'] if hdr['bereich'] else hdr['dose']
            name = ' '.join(w[4] for w in ws if hdr['name'] <= w[0] < name_end - 2 and not re.match(r'^#\d+$', w[4]))
            dose = []
            after = [w for w in ws if w[0] >= hdr['dose']]
            for i, w in enumerate(after):
                if w[4] == '–' or (re.match(r'^[\d.]+(,\d+)?$', w[4]) and i + 1 < len(after) and after[i + 1][4] == '€'):
                    break
                dose.append(w[4])
            f, lv = form, level
            if kind == 'marge' and hdr['bereich']:
                b = ' '.join(w[4] for w in ws if hdr['bereich'] - 2 <= w[0] < hdr['dose'])
                f = 'vial' if b.endswith('Vial') else 'dual' if b.endswith('Doppelkammer') else None
                lv = 'pack' if b.startswith('10er') else 'einzel'
            if f:
                row = dict(level=lv, key=key(f, name, ' '.join(dose)), vk=money(near[0]), page=page.number + 1)
                if 'sp' in hdr:
                    row['spanne'], row['delta'] = (pct_cell([w for w in ws if hdr[c] - 48 <= w[2] <= hdr[c] + 2]) for c in ('sp', 'dl'))
                out.append(row)
    return out


def pct_cell(ws):
    """Woerter einer Prozentzelle ('80,5 %', '+8,3 %', '−20,0 %', '±0,0 %', '–') -> float in Prozentpunkten oder None."""
    t = ''.join(w[4] for w in ws).replace('%', '').replace('±', '').replace('+', '').replace('−', '-').replace(',', '.')
    if t in ('', '–', '-'):
        return None
    try:
        return float(t)
    except ValueError:
        return f'unlesbar:{t}'


def check_kundensicht(rows, path, label='marge'):
    """Neue Spalten der 10er-Pack-Tabellen gegen die Kennzahlen-Datei (ZEILEN_CSV): Haendlerspanne am Markt und Delta gegen alte Liste.
    Datei-Preis = Shop-VK -> Prozentwerte der Datei direkt; sonst aus Markt-Median/alter Liste der Datei mit dem Shop-VK nachgerechnet. Toleranz 0,1 Prozentpunkt."""
    import marge_pdf as mpdf
    zp = mpdf.zeilen_csv([])
    Z = {key(*k): v for k, v in mpdf.load_zeilen(zp).items()}
    fl = lambda v: float(v) if v not in (None, '') else None  # noqa: E731
    res = dict(datei=str(zp), zeilen=0, ok=0, direkt_aus_datei=0, nachgerechnet=0, ohne_marktdaten=0, max_abweichung_pp=0.0, fehler=[], hinweise=[])
    seen = {}
    for r in rows:
        if r['level'] != 'pack' or 'spanne' not in r:
            continue
        z = Z.get(r['key'])
        if z is None:
            res['fehler'].append(f'{label}: Pack {r["key"]} nicht in {zp.name}')
            continue
        if r['key'] in seen:
            continue
        seen[r['key']] = r
        res['zeilen'] += 1
        vk = r['vk']
        if fl(z['neu_eur']) is not None and abs(fl(z['neu_eur']) - vk) < 0.005:
            res['direkt_aus_datei'] += 1
            exp_sp, exp_dl = fl(z['haendlerspanne_markt_pct']), fl(z['delta_pct_gegen_alte_liste'])
        else:
            res['nachgerechnet'] += 1
            mk, alt = fl(z['markt_median_eur']), fl(z['alte_liste_eur'])
            exp_sp = 100 * (1 - (vk / 10) / mk) if mk else None
            exp_dl = 100 * (vk / alt - 1) if alt else None
        if exp_sp is None:
            res['ohne_marktdaten'] += 1
        good = True
        for nm, got, exp in (('Händlerspanne', r['spanne'], exp_sp), ('Δ alte Liste', r['delta'], exp_dl)):
            if got is None and exp is None:
                continue
            if not isinstance(got, float) or exp is None or abs(got - exp) > 0.1 + 1e-9:
                good = False
                res['fehler'].append(f'{label}: {nm} {r["key"]} PDF {got} != Datei {None if exp is None else round(exp, 2)} (Seite {r["page"]})')
            else:
                res['max_abweichung_pp'] = max(res['max_abweichung_pp'], round(abs(got - exp), 3))
        res['ok'] += good
    res['stichprobe_25'] = sorted(' '.join(k[1:]) + f' ({k[0]})' for k in list(seen)[::max(1, len(seen) // 25)][:25])
    if res['zeilen'] < 340:
        res['fehler'].append(f'{label}: nur {res["zeilen"]} von 340 Packs mit Kundensicht-Spalten erkannt')
    if res['direkt_aus_datei'] < 25:
        res['hinweise'].append(f'nur {res["direkt_aus_datei"]} Packs mit gleichem Preis in Datei und Shop - Rest nachgerechnet')
    # Seite 1: 'X von Y Packs mit Marktdaten' muss zu den Tabellenspalten passen
    p1 = pymupdf.open(path)[0].get_text().replace('\n', ' ')
    mm_ = re.search(r'(\d+) von (\d+) Packs mit Marktdaten', p1)
    want = (sum(1 for r in seen.values() if isinstance(r['spanne'], float) and r['spanne'] >= 40), sum(1 for r in seen.values() if r['spanne'] is not None))
    res['seite1_gruen_von_mit'] = [int(mm_.group(1)), int(mm_.group(2))] if mm_ else None
    if not mm_ or (int(mm_.group(1)), int(mm_.group(2))) != want or 'Kundensicht' not in p1:
        res['fehler'].append(f'{label}: Kundensicht-Tafel Seite 1 {res["seite1_gruen_von_mit"]} passt nicht zu den Tabellen {list(want)}')
    pages = [pg.get_text() for pg in pymupdf.open(path)]
    att = next((i + 1 for i, t in enumerate(pages) if 'Zeilen mit Aufmerksamkeit (10er-Packs)' in t), None)
    low = next((i + 1 for i, t in enumerate(pages) if 'Die 15 niedrigsten Margen' in t), None)
    res['seite_aufmerksamkeit'], res['seite_15_niedrigste'] = att, low
    if not att or not low or att != low + 1:
        res['fehler'].append(f'{label}: Seite „Zeilen mit Aufmerksamkeit“ ({att}) nicht direkt nach den 15 niedrigsten Margen ({low})')
    return res


def check_layout(path, margin_mm=12, min_pt=7.0):
    """Alle Woerter innerhalb der Seitenraender, keine ueberlappenden Woerter, keine Schrift unter min_pt."""
    res = dict(seiten=0, ausserhalb=[], ueberlappung=[], min_schrift_pt=99.0)
    for pg in pymupdf.open(path):
        res['seiten'] += 1
        W, H = pg.rect.width, pg.rect.height
        m = margin_mm * MM
        ws = pg.get_text('words')
        for w in ws:
            if w[0] < m - 1.5 or w[2] > W - m + 1.5 or w[1] < 10 * MM or w[3] > H - 4 * MM:
                res['ausserhalb'].append(f'S.{pg.number + 1} {w[4]!r} {tuple(round(v) for v in w[:4])}')
        ws = sorted(ws, key=lambda w: w[0])
        for i, a in enumerate(ws):
            for b in ws[i + 1:]:
                if b[0] >= a[2]:
                    break
                ix = min(a[2], b[2]) - max(a[0], b[0])
                iy = min(a[3], b[3]) - max(a[1], b[1])
                if ix > 0.8 and iy > 0.25 * min(a[3] - a[1], b[3] - b[1]):
                    res['ueberlappung'].append(f'S.{pg.number + 1} {a[4]!r}/{b[4]!r}')
        for blk in pg.get_text('dict')['blocks']:
            for ln in blk.get('lines', []):
                for sp in ln['spans']:
                    if sp['text'].strip():
                        res['min_schrift_pt'] = min(res['min_schrift_pt'], round(sp['size'], 2))
    res['ok'] = not res['ausserhalb'] and not res['ueberlappung'] and res['min_schrift_pt'] >= min_pt
    return res


def render_hd(path, tag, dpi=110):
    """Seitenbilder in hoeherer Aufloesung fuer die Sichtpruefung (_out/render/<tag>/)."""
    rd = OUT / 'render' / tag
    rd.mkdir(parents=True, exist_ok=True)
    for old in rd.glob('*.png'):
        old.unlink()
    for i, pg in enumerate(pymupdf.open(path)):
        pg.get_pixmap(dpi=dpi).save(rd / f'seite_{i + 1:02d}.png')


def check_internal(rows, label):
    res = dict(zeilen_erkannt=len(rows), geprueft=0, ok=0, fehler=[])
    seen = {}
    for r in rows:
        truth = (PACK if r['level'] == 'pack' else SINGLE_BY_NAME).get(r['key'])
        if truth is None:
            continue
        res['geprueft'] += 1
        seen[r['key']] = r['vk']
        if truth == r['vk']:
            res['ok'] += 1
        else:
            res['fehler'].append(f'{label}: {r["level"]} {r["key"]} VK {r["vk"]} != Tabelle {truth}')
    res['pflicht'] = {' '.join(k): ('ok' if key(*k) in seen else 'nicht in Datei') for k in MUST}
    return res, seen


def compare(old, new):
    common = [k for k in new if k in old]
    return dict(gemeinsam=len(common), hoeher=sum(1 for k in common if new[k] > old[k]), niedriger=sum(1 for k in common if new[k] < old[k]),
                gleich=sum(1 for k in common if new[k] == old[k]), nur_neu=len([k for k in new if k not in old]), nur_alt=len([k for k in old if k not in new]))


# ---------------------------------------------------------------- Lauf
report = {}
cust = D / EDDY / 'Preisliste für Kunden (auch im Bot).pdf'
files = {
    'kunden_pdf': cust, 'kunden_xlsx': D / EDDY / 'Preisliste für Kunden (Tabelle).xlsx',
    'marge': D / EDDY / 'MARGEN – Einkauf, Verkauf, Marge je Produkt.pdf', 'ting': D / EDDY / 'Ting-Preischeck, Verhandlung, Händlermarge.pdf',
    'top20': D / EDDY / 'Top-20 Bestseller mit Preisen.pdf', 'ting_liste': D / TING / 'Elements Labs Preisliste (Bestpreis, Top-Produkte markiert).pdf',
    'rene': D / RENE / 'ZUERST LESEN - Übergabe für René.pdf',
}
for tag, path in files.items():
    r = report[tag] = dict(datei=str(path.relative_to(OUT)))
    if not path.is_file():
        problems.append(f'{tag}: Datei fehlt'); continue
    if path.suffix == '.pdf':
        r['seiten'], ink = render(path, tag)
        r['render_min_tinte'] = min(ink)
        if min(ink) < 0.002:
            problems.append(f'{tag}: leere Seite(n) {[i + 1 for i, v in enumerate(ink) if v < 0.002]}')
        text, meta, has_img = pdf_text(path)
        r['logo'] = has_img
    old_path = DESK / path.relative_to(D)
    if tag in ('kunden_pdf',):
        res, seen = check_customer_rows(parse_customer(path), tag)
        r.update(res)
        r['leaks'] = leaks(text + '\n' + meta, CUSTOMER_LEAKS)
        r['bot_kopie_identisch'] = hashlib.sha256(path.read_bytes()).hexdigest() == hashlib.sha256((S / 'miniapp/data/preisliste.pdf').read_bytes()).hexdigest()
        r['spaltenkoepfe'] = all(s in text for s in ('Einzel', '10er-Pack', 'je Stück', 'Doppelkammer · inklusive Pen'))
        if not r['bot_kopie_identisch'] or not r['spaltenkoepfe'] or not has_img:
            problems.append(f'{tag}: Bot-Kopie/Spaltenköpfe/Logo nicht ok')
        if old_path.is_file():
            oldp = parse_old_customer(old_path)
            r['vs_desktop'] = compare(oldp, {k: PACK[k] for k in seen})
            r['vs_desktop']['desktop_gleich_price_old'] = f"{sum(1 for k in oldp if OLD.get(k) == oldp[k])}/{len(oldp)}"
            r['vs_price_old_alle_340'] = compare(OLD, {k: PACK[k] for k in OLD})
            r['vs_desktop']['seiten_alt'] = len(pymupdf.open(old_path))
    elif tag == 'kunden_xlsx':
        rows, text = parse_customer_xlsx(path)
        res, _ = check_customer_rows(rows, tag)
        r.update(res)
        r['leaks'] = leaks(text, CUSTOMER_LEAKS)
    elif tag in CFG:
        prows = parse_internal(path, tag)
        res, seen = check_internal(prows, tag)
        r.update(res)
        if tag == 'marge':  # Kundensicht: neue Spalten gegen ZEILEN_CSV, Tafel Seite 1, Seitenfolge, Layout, Seitenbilder 110 dpi
            ks = r['kundensicht'] = check_kundensicht(prows, path)
            lay = r['layout'] = check_layout(path)
            render_hd(path, 'marge_kundensicht')
            problems.extend(ks['fehler'][:20])
            if not lay['ok']:
                problems.append(f"marge: Layout {lay['ausserhalb'][:5]} {lay['ueberlappung'][:5]} min Schrift {lay['min_schrift_pt']}")
        r['leaks'] = leaks(text, [r'[\u3400-\u9fff]'])
        r['intern_markiert'] = 'intern' in text.lower()
        if r['geprueft'] < 25:
            problems.append(f'{tag}: nur {r["geprueft"]} Zeilen geprüft (< 25)')
        if old_path.is_file():
            oldseen = {x['key']: x['vk'] for x in parse_internal(old_path, tag) if x['level'] == 'pack'}
            r['vs_desktop'] = compare(oldseen, {k: v for k, v in seen.items() if k in PACK})
            r['vs_desktop']['seiten_alt'] = len(pymupdf.open(old_path))
    elif tag == 'ting_liste':
        r['leaks'] = leaks(text + '\n' + meta, TING_LEAKS)
        vk_hits = 0
        if old_path.is_file():
            old_text = '\n'.join(p.get_text() for p in pymupdf.open(old_path))
            strip = lambda t: re.sub(r'Stand \d\d\.\d\d\.\d{4}', '', t)  # noqa: E731
            new_rows = [ln for ln in strip(text).split('\n') if ln.strip()]
            old_rows = [ln for ln in strip(old_text).split('\n') if ln.strip()]
            r['vs_desktop'] = dict(text_identisch=new_rows == old_rows, zeilen_neu=len(new_rows), zeilen_alt=len(old_rows), seiten_alt=len(pymupdf.open(old_path)))
            r['stichprobe_zeilen_gleich'] = sum(1 for a, b in zip(new_rows[::max(1, len(new_rows) // 40)], old_rows[::max(1, len(old_rows) // 40)]) if a == b)
        r['enthaelt_keine_v3_verkaufspreise'] = vk_hits == 0
    elif tag == 'rene':
        r['leaks'] = leaks(text, [r'[\u3400-\u9fff]', r'\d €'])
        if old_path.is_file():
            r['identisch_mit_desktop'] = path.read_bytes() == old_path.read_bytes()
    if r.get('fehler'):
        problems += r['fehler'][:20]
    if r.get('leaks'):
        problems.append(f'{tag}: Leak-Treffer {r["leaks"]}')
    for k, v in (r.get('pflicht') or {}).items():
        if tag.startswith('kunden') and v != 'ok':
            problems.append(f'{tag}: Pflichtzeile {k} {v}')

report['alles_ok'] = not problems
report['probleme'] = problems
(OUT / 'pruefung_v3.json').write_text(json.dumps(report, ensure_ascii=False, indent=1))
for tag, r in report.items():
    if isinstance(r, dict):
        short = {k: ({kk: vv for kk, vv in v.items() if kk not in ('fehler', 'stichprobe_25', 'ausserhalb', 'ueberlappung')} if isinstance(v, dict) else v)
                 for k, v in r.items() if k not in ('fehler', 'datei', 'pflicht')}
        print(tag, json.dumps(short, ensure_ascii=False))
        if r.get('pflicht'):
            print('   Pflicht:', ', '.join(f'{k}={v}' for k, v in r['pflicht'].items()))
print('PROBLEME', len(problems))
for p in problems[:40]:
    print('  ', p)
sys.exit(0 if not problems else 1)
