"""Preispositionierung 10er-Packs (Vial + Doppelkammer): Einkauf, aktueller Shop-Preis, Markt, Empfehlung -> eine Excel-Datei.

Regeln (alle als Parameter oben, damit der Inhaber sie ohne Code ablesen kann):
  * Einkauf = reale beste Lieferantenpreise der Basisliste (vor allen Wunsch-Regeln), je 10er-Packung.
  * Markt = Median der oeffentlichen 10-Vial-Kits (peptidehaus.de, qsc-eu.com); bei einer Quelle diese Quelle.
  * Empfehlung Vial: aktueller Preis, gehalten im Band 5-15 % unter dem Markt-Median; nie unter Faktor 2 auf den Einkauf; auf 10 EUR aufgerundet.
  * Empfehlung Doppelkammer: aktueller Preis, mindestens 15 % ueber dem empfohlenen Vial, nie unter Faktor 2 auf den Einkauf, Staffel aufsteigend.
"""
import json
import statistics
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HERE = Path(__file__).resolve().parent
MINI = HERE.parent / 'miniapp'
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(MINI / 'tools'))
import apply_pricing as ap  # noqa: E402
import catalog_lines as cl  # noqa: E402
import markt_10er as m  # noqa: E402
import render_supplier as rs  # noqa: E402

BAND_LO, BAND_HI = 0.85, 0.95   # Verkaufspreis 5-15 % unter dem Markt-Median
MIN_FACTOR = 2.0                # Untergrenze: Verkaufspreis >= 2 x Einkauf (50 % Marge)
TARGET_FACTOR = 3.0             # bisheriger Katalogfaktor des Inhabers
DUAL_MIN = 1.15
RATIO = 1.5
OUT = Path.home() / 'Desktop' / 'Elements Labs Preispositionierung.xlsx'


def ceil10(v):
    return int(-(-round(v, 6) // 10)) * 10


def canon(n):
    n = m.norm(n.split(' (')[0])
    n = n.replace(' ', '').replace('-', '').replace('+', '').lower().replace('carnitine', 'carnitin').replace('322', '332')
    if n.startswith('hgh'):
        n = 'hgh'
    return {'bacteriostaticwater': 'bacteriostatischeswasser'}.get(n, n)


def main():
    rs.build()
    raw = rs.LAST_LOG['raw']
    cost = {}
    for r in raw:
        d = m.split_dose(r['dose'])
        if d:
            cost.setdefault((canon(r['name']), d), r)
    kits = {(r['name'], r['strength']): r for r in json.loads((HERE / 'markt_10er.json').read_text())}
    ratios = [r['sources']['peptidehaus'] / r['sources']['qsc'] for r in kits.values() if len(r['sources']) == 2]
    global RATIO
    RATIO = statistics.median(ratios)
    print('Verhaeltnis peptidehaus/qsc (Median aus', len(ratios), 'Zeilen):', round(RATIO, 2))
    lines = cl.lines(recommend=False)
    current = {(x['form'], x['name'], x['strength']): x for x in lines}
    out = []
    for x in lines:
        d = m.split_dose(x['strength'])
        c = cost.get((canon(x['name']), d))
        row = dict(section=x['section'], name=x['name'], strength=x['strength'], form=x['form'], code=x['code'], cur=x['price_cents'] / 100, order=x['order'],
                   owner=x.get('owner_price_cents', x['price_cents']) / 100)
        row['cost'] = (c['vial'] if x['form'] == 'vial' else c['dual']) if c else None
        row['cost_est'] = bool(c and x['form'] == 'dual' and c.get('dual_est'))
        row['src'] = {}
        row['market'] = None
        if x['form'] == 'vial':
            k = kits.get((x['name'], x['strength']))
            if k and k['sources']:
                row['src'] = k['sources']
                row['market'] = statistics.median(k['sources'].values())
                if len(k['sources']) == 1:  # fehlende Quelle ueber das typische Verhaeltnis beider Anbieter schaetzen
                    (only, val), = k['sources'].items()
                    row['market'] = val * ((1 + RATIO) / 2 if only == 'qsc' else (1 + 1 / RATIO) / 2)
                    row['market_est'] = True
        out.append(row)

    # Empfehlung Vial
    for r in out:
        if r['form'] != 'vial':
            continue
        rec = r['cur']
        note = 'ohne Marktpreis: unveraendert'
        if r['market']:
            lo, hi = BAND_LO * r['market'], BAND_HI * r['market']
            rec = min(max(rec, lo), hi)
            note = ('Markt (2 Quellen)' if len(r['src']) >= 2 else 'Markt (1 Quelle, zweite geschätzt)')
        if r['cost'] and rec < MIN_FACTOR * r['cost']:
            rec = MIN_FACTOR * r['cost']
            note += ' · Marge-Untergrenze'
        r['rec'] = ceil10(rec)
        r['note'] = note
    # Empfehlung Doppelkammer: mind. 15 % ueber dem empfohlenen Vial, Staffel aufsteigend
    vial_rec = {(r['name'], r['strength']): r['rec'] for r in out if r['form'] == 'vial'}
    for r in out:
        if r['form'] != 'dual':
            continue
        rec = r['cur']
        note = 'Doppelkammer: Verkaufsblatt'
        v = vial_rec.get((r['name'], r['strength']))
        if v and rec < DUAL_MIN * v:
            rec = DUAL_MIN * v
            note = 'Abstand zum Vial: mind. 15 %'
        if r['cost'] and rec < MIN_FACTOR * r['cost']:
            rec = MIN_FACTOR * r['cost']
            note += ' · Marge-Untergrenze'
        r['rec'] = ceil10(rec)
        r['note'] = note
    for form in ('vial', 'dual'):
        groups = {}
        for r in out:
            if r['form'] == form:
                groups.setdefault((r['name'].split(' (')[0], r['strength'].split()[-1] if r['strength'] else ''), []).append(r)
        for rs_ in groups.values():
            try:
                rs_.sort(key=lambda r: m.split_dose(r['strength'])[0])
            except TypeError:
                continue
            prev = None
            for r in rs_:
                if prev is not None and r['rec'] < prev['rec'] + 10 and m.split_dose(r['strength'])[0] > m.split_dose(prev['strength'])[0] and r['name'] == prev['name']:
                    r['rec'] = prev['rec'] + 10
                    r['note'] += ' · Staffel aufsteigend'
                prev = r
    # Abstand Doppelkammer nach Staffel-Anhebungen des Vials erneut sichern
    vial_rec = {(r['name'], r['strength']): r['rec'] for r in out if r['form'] == 'vial'}
    for r in out:
        v = vial_rec.get((r['name'], r['strength']))
        if r['form'] == 'dual' and v and r['rec'] < ceil10(DUAL_MIN * v):
            r['rec'] = ceil10(DUAL_MIN * v)

    # ---- Einzelpreise der 25 Shop-Produkte
    market = json.loads((ap.MARKET).read_text())
    vials = json.loads((MINI / 'data/products.json').read_text())
    formats = {f['id']: f for f in json.loads((MINI / 'data/shop-formats.json').read_text())}
    by_line = {(r['form'], r['name'], r['strength']): r for r in out}
    singles = []
    for p in vials:
        mk = ap.market_reference(market['vial'][ap.market_key(p)], ap.dose(p)) if ap.market_key(p) in market['vial'] else None
        v, d = cl.MATCH[p['id']]
        rv = by_line.get(('vial', *v)) if v else None
        rd = by_line.get(('dual', *d)) if d else None
        dual_id = 'dual-' + p['id']
        singles.append(dict(name=p['name'], dose=p['concentration'], market=mk, single=p['price_cents'] / 100, dual=formats[dual_id]['price_cents'] / 100,
                            pack=rv['cur'] if rv else None, pack_rec=rv['rec'] if rv else None, dpack=rd['cur'] if rd else None, dpack_rec=rd['rec'] if rd else None))

    # ---- Excel
    wb = Workbook()
    head_fill = PatternFill('solid', fgColor='0D5B6B')
    sec_fill = PatternFill('solid', fgColor='E6EFF1')
    thin = Side(style='thin', color='D9DEE2')
    border = Border(bottom=thin)
    hfont = Font(bold=True, color='FFFFFF')
    EUR = '#,##0" €"'
    PCT = '0%'

    def header(ws, cols, row=1):
        for i, c in enumerate(cols, 1):
            cell = ws.cell(row=row, column=i, value=c)
            cell.fill, cell.font = head_fill, hfont
            cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center' if i > 3 else 'left')
        ws.row_dimensions[row].height = 44

    # Sheet 1: Empfehlung Vial + Doppelkammer je Zeile
    ws = wb.active
    ws.title = 'Empfehlung 10er-Packs'
    cols = ['Bereich', 'Produkt', 'Dosierung', 'Typ', 'Einkauf\n(reale beste\nLieferantenpreise)', 'Aktuell im Shop', 'Markt\npeptidehaus', 'Markt\nqsc-eu', 'Markt\nMedian', 'Empfehlung', 'Änderung\nin €', 'Marge\naktuell', 'Marge\nEmpfehlung', 'Faktor\nauf Einkauf', 'Begründung / Belegqualität']
    header(ws, cols)
    r0 = 2
    section_order = {s: i for i, s in enumerate(cl.SECTIONS)}
    out.sort(key=lambda r: (section_order.get(r['section'], 99), r['order']))
    for i, r in enumerate(out):
        row = r0 + i
        ws.cell(row, 1, r['section'])
        ws.cell(row, 2, r['name'])
        ws.cell(row, 3, r['strength'])
        ws.cell(row, 4, 'Vial 10er' if r['form'] == 'vial' else 'Doppelkammer 10er')
        ws.cell(row, 5, r['cost'] if r['cost'] is not None else None)
        ws.cell(row, 6, r['cur'])
        ws.cell(row, 7, r['src'].get('peptidehaus'))
        ws.cell(row, 8, r['src'].get('qsc'))
        ws.cell(row, 9, r['market'])
        ws.cell(row, 10, r['rec'])
        ws.cell(row, 11, f'=J{row}-F{row}')
        ws.cell(row, 12, f'=IF(E{row}="","",(F{row}-E{row})/F{row})')
        ws.cell(row, 13, f'=IF(E{row}="","",(J{row}-E{row})/J{row})')
        ws.cell(row, 14, f'=IF(E{row}="","",J{row}/E{row})')
        ws.cell(row, 15, r['note'] + (' · Einkauf berechnet' if r['cost_est'] else '') + ('' if r['cost'] is not None else ' · Einkauf unbekannt'))
        for c in (5, 6, 7, 8, 9, 10, 11):
            ws.cell(row, c).number_format = EUR
        for c in (12, 13):
            ws.cell(row, c).number_format = PCT
        ws.cell(row, 14).number_format = '0.0"×"'
        ws.cell(row, 10).font = Font(bold=True)
        for c in range(1, 16):
            ws.cell(row, c).border = border
            if c > 4 and c < 15:
                ws.cell(row, c).alignment = Alignment(horizontal='right')
    last = r0 + len(out) - 1
    for col, w in zip('ABCDEFGHIJKLMNO', (26, 34, 20, 18, 15, 13, 12, 10, 11, 13, 11, 10, 11, 10, 52)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = 'D2'
    ws.auto_filter.ref = f'A1:O{last}'
    ws.conditional_formatting.add(f'K{r0}:K{last}', CellIsRule(operator='lessThan', formula=['0'], font=Font(color='B42318', bold=True)))
    ws.conditional_formatting.add(f'K{r0}:K{last}', CellIsRule(operator='greaterThan', formula=['0'], font=Font(color='067647', bold=True)))

    # Sheet 2: Einzelpreise der 25 Shop-Produkte
    w2 = wb.create_sheet('Einzelpreise (Shop-Produkte)')
    cols2 = ['Produkt', 'Dosierung', 'Markt Einzelvial\n(Median freie Shops)', 'Unser Einzelvial\naktuell', 'Abstand zum\nMarkt', 'Doppelkammer\neinzeln aktuell', '10er-Vial\naktuell', 'je Stück', 'Rabatt\nPack vs. Einzel', '10er-Vial\nEmpfehlung', 'je Stück', '10er-Doppelk.\naktuell', '10er-Doppelk.\nEmpfehlung']
    header(w2, cols2)
    for i, s in enumerate(singles):
        row = 2 + i
        w2.cell(row, 1, s['name']); w2.cell(row, 2, s['dose'])
        w2.cell(row, 3, s['market']); w2.cell(row, 4, s['single'])
        w2.cell(row, 5, f'=IF(C{row}="","",D{row}/C{row}-1)')
        w2.cell(row, 6, s['dual']); w2.cell(row, 7, s['pack'])
        w2.cell(row, 8, f'=IF(G{row}="","",G{row}/10)')
        w2.cell(row, 9, f'=IF(G{row}="","",1-H{row}/D{row})')
        w2.cell(row, 10, s['pack_rec']); w2.cell(row, 11, f'=IF(J{row}="","",J{row}/10)')
        w2.cell(row, 12, s['dpack']); w2.cell(row, 13, s['dpack_rec'])
        for c in (3, 4, 6, 7, 10, 12, 13):
            w2.cell(row, c).number_format = EUR
        for c in (8, 11):
            w2.cell(row, c).number_format = '#,##0.0" €"'
        for c in (5, 9):
            w2.cell(row, c).number_format = PCT
        for c in range(1, 14):
            w2.cell(row, c).border = border
            if c > 2:
                w2.cell(row, c).alignment = Alignment(horizontal='right')
    for col, w in zip('ABCDEFGHIJKLM', (20, 16, 18, 15, 12, 15, 12, 10, 12, 13, 10, 14, 14)):
        w2.column_dimensions[col].width = w
    w2.freeze_panes = 'C2'

    # Sheet 3: Methode / Lesehilfe
    w3 = wb.create_sheet('Methode')
    text = [
        ('Preisleiter', 'Frei verkäufliche Einzelvials (Markt) > unser Einzelvial (gleich Markt) > 10er-Pack je Stück (deutlich darunter) > Markt-Kits (Wettbewerber).'),
        ('Einkauf', 'Reale beste Lieferantenpreise der Basisliste je 10er-Packung (vor Wunschpreis-Regeln). Doppelkammer: Kartuschenpreis x 10 (ggf. berechnet).'),
        ('Markt 10er', 'Öffentliche 10-Vial-Kits von peptidehaus.de (Händler-Stil) und qsc-eu.com (Großhandel-Stil), Stand 24.10.2026. Die beiden liegen oft um den Faktor 2-3 auseinander; der Median liegt dazwischen.'),
        ('Empfehlung Vial', 'Aktueller Preis, gehalten im Band 5-15 % unter dem Markt-Median (billig genug für Kunden, ohne Marge zu verschenken). Nie unter Faktor 2 auf den Einkauf (mind. 50 % Marge). Aufgerundet auf volle 10 €. Ohne Marktpreis: unverändert.'),
        ('Empfehlung Doppelkammer', 'Mindestens 15 % über dem empfohlenen Vial, nie unter Faktor 2 auf den Einkauf; Staffel aufsteigend (größere Dosierung kostet mehr). Für 10er-Doppelkammern gibt es keinen öffentlichen Marktpreis.'),
        ('Marge', '(Verkaufspreis - Einkauf) / Verkaufspreis, ohne Versand, Zahlungsgebühren und Steuern.'),
        ('Grenzen', 'Zeilen mit nur einer Marktquelle oder ohne Marktpreis sind unsicherer; der Einkauf fehlt bei wenigen Zeilen (Wasser, HGH, Blends).'),
        ('Nichts umgesetzt', 'Diese Datei ist nur eine Empfehlung. Im Shop ist nichts geändert.'),
    ]
    w3.column_dimensions['A'].width = 26
    w3.column_dimensions['B'].width = 120
    for i, (a, b) in enumerate(text, 1):
        w3.cell(i, 1, a).font = Font(bold=True)
        w3.cell(i, 2, b).alignment = Alignment(wrap_text=True, vertical='top')
        w3.row_dimensions[i].height = 34
    wb.save(OUT)

    # Kennzahlen fuer den Bericht
    vi = [r for r in out if r['form'] == 'vial' and r['cost']]
    di = [r for r in out if r['form'] == 'dual' and r['cost']]
    def agg(rows, key):
        return sum(r[key] for r in rows), sum(r['cost'] for r in rows)
    for label, rows_ in (('Vial', vi), ('Doppelkammer', di)):
        cur, c = agg(rows_, 'cur'); rec, _ = agg(rows_, 'rec')
        print(f'{label}: {len(rows_)} Zeilen mit Einkauf; Summe aktuell {cur:,.0f} / Empfehlung {rec:,.0f} / Einkauf {c:,.0f}; Marge aktuell {1 - c / cur:.0%} -> Empfehlung {1 - c / rec:.0%}')
    chg = [r for r in out if r['rec'] != r['cur']]
    print('Zeilen gesamt', len(out), 'mit Aenderung', len(chg), '; Vial gesenkt', sum(1 for r in chg if r['form'] == 'vial' and r['rec'] < r['cur']), 'angehoben', sum(1 for r in chg if r['form'] == 'vial' and r['rec'] > r['cur']),
          '; Dual gesenkt', sum(1 for r in chg if r['form'] == 'dual' and r['rec'] < r['cur']), 'angehoben', sum(1 for r in chg if r['form'] == 'dual' and r['rec'] > r['cur']))
    below = [r for r in out if r['cost'] and r['rec'] < TARGET_FACTOR * r['cost']]
    print('Zeilen unter Faktor 3:', len(below), '; unter Faktor 2:', sum(1 for r in out if r['cost'] and r['rec'] < 2 * r['cost'] - 0.01))
    json.dump(out, open(HERE / 'positionierung.json', 'w'), ensure_ascii=False, indent=1, default=str)
    print('geschrieben:', OUT)


if __name__ == '__main__':
    main()
