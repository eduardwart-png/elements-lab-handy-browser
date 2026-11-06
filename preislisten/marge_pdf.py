"""PDF: Margenuebersicht (intern) - Einkaufspreis, Verkaufspreis, Marge je Produkt, Stand = aktueller Shop.

Marge = (VK - EK) / VK. EK = Listenpreis Ting (sichtbarer Wert, EUR; Kurs aus merged.json), wo Ting nicht liefert: andere Lieferantin. Ergebnis: 'Elements Labs Margenuebersicht.pdf'.

Kundensicht (10er-Packs): Haendlerspanne am Markt = 1 - (VK/10) / Markt-Median je Stueck, Delta gegen alte Liste = VK / alte Liste - 1.
Marktmedian und alte Liste kommen aus der Kennzahlen-Datei (Format zeilen_*.csv der Preis-Maker): Umgebungsvariable ZEILEN_CSV
oder Argument --zeilen <datei>; Standard team6/zeilen_G.csv, falls vorhanden, sonst team4/zeilen_M1_E2.csv. Gerechnet wird immer mit dem
Shop-VK dieser Liste (preisfamilie v3); weicht der Preis der Datei ab, wird das auf Seite 1 vermerkt.
"""
import csv
import json
import os
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import BaseDocTemplate, Frame, KeepTogether, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus import Image as RLImage
from reportlab.platypus.flowables import PageBreakIfNotEmpty

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'miniapp' / 'tools'))
import catalog_lines as cl  # noqa: E402
import ting_check as tc  # noqa: E402
from render_lists import logo_png  # noqa: E402

OUT = HERE / 'Elements Labs Margenübersicht.pdf'
APP = HERE.parent / 'miniapp'
INK, MUTED, PET, SOFT, LINE = colors.HexColor('#172027'), colors.HexColor('#66717B'), colors.HexColor('#0D5B6B'), colors.HexColor('#EEF4F5'), colors.HexColor('#D9DEE2')
GREEN, AMBER, RED = colors.HexColor('#067647'), colors.HexColor('#B54708'), colors.HexColor('#B42318')
STAND = '25.10.2026'
STRAT = Path.home() / 'Projekte-Mac/_DATA/ELEMENTS_STRATEGIE_20261024'
ZEILEN_DEFAULTS = [STRAT / 'team6/zeilen_G.csv', STRAT / 'team5/zeilen_F.csv', STRAT / 'team4/zeilen_M1_E2.csv']


def zeilen_csv(argv=None):
    """Kennzahlen-Datei: --zeilen <datei> > ZEILEN_CSV > team5/zeilen_F.csv > team4/zeilen_M1_E2.csv."""
    argv = sys.argv[1:] if argv is None else argv
    if '--zeilen' in argv:
        return Path(argv[argv.index('--zeilen') + 1])
    if os.environ.get('ZEILEN_CSV'):
        return Path(os.environ['ZEILEN_CSV'])
    return next((p for p in ZEILEN_DEFAULTS if p.is_file()), ZEILEN_DEFAULTS[-1])


def zkey(form, name, strength):
    return (form, re.sub(r'\s+', '', str(name)).lower().replace('–', '-'), re.sub(r'\s+', '', str(strength)).lower().replace('–', '-'))


def load_zeilen(path):
    """Pack-Zeilen der Kennzahlen-Datei -> {(form, name, strength): row}."""
    with open(path, newline='', encoding='utf-8') as fh:
        return {zkey(r['form'], r['substance'], r['strength']): r for r in csv.DictReader(fh, delimiter=';') if r['level'] == 'pack'}


def fnum(v):
    return float(v) if v not in (None, '') else None


def kundensicht(packs, zpath):
    """Haengt je Pack spanne, stk (Pack/10 in % vom Markt), mkt, alt, delta, z_vk an. Rueckgabe: Anzahl Packs mit abweichendem Datei-Preis."""
    Z = load_zeilen(zpath)
    abw = 0
    for r in packs:
        z = Z.get(zkey(r['form'], r['name'], r['strength']))
        mkt, alt = (fnum(z['markt_median_eur']), fnum(z['alte_liste_eur'])) if z else (None, None)
        r['z_vk'] = fnum(z['neu_eur']) if z else None
        if r['z_vk'] is not None and abs(r['z_vk'] - r['vk']) > 0.005:
            abw += 1
        r['mkt'], r['alt'] = mkt, alt
        r['stk'] = (r['vk'] / 10) / mkt if mkt else None
        r['spanne'] = 1 - r['stk'] if mkt else None
        r['delta'] = r['vk'] / alt - 1 if alt else None
        r['fx'] = r['vk'] / r['ek'] if r['ek'] else None
    return abw


def sband(sp):
    """Farbband der Haendlerspanne nach dem angezeigten Wert (eine Nachkommastelle)."""
    if sp is None:
        return 'ohne'
    v = round(sp * 100, 1)
    return 'gruen' if v >= 40 else 'orange' if v >= 30 else 'rot'


def eur(v, dec=0):
    if v is None:
        return '–'
    s = f'{v:,.{dec}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return s + ' €'


def pct(v):
    return '–' if v is None else f'{v * 100:.0f} %'


def pct1(v, sign=False):
    """0.805 -> '80,5 %'; sign=True: '+8,3 %' / '−20,0 %' / '±0,0 %'."""
    if v is None:
        return '–'
    x = round(v * 100, 1)
    pre = ('+' if x > 0 else '−' if x < 0 else '±') if sign else ('−' if x < 0 else '')
    return pre + f'{abs(x):.1f}'.replace('.', ',') + ' %'


def scol(sp):
    return {'gruen': '#067647', 'orange': '#B54708', 'rot': '#B42318'}.get(sband(sp), '#66717B')


def kennzahlen(packs):
    """Kennzahlen der Kundensicht-Tafel (Seite 1) ueber alle 10er-Packs."""
    from statistics import median
    K = {}
    for b in ('gruen', 'orange', 'rot', 'ohne'):
        K['s_' + b] = sum(1 for r in packs if sband(r.get('spanne')) == b)
    mit = [r for r in packs if r.get('spanne') is not None]
    K['s_mit'] = len(mit)
    K['s_median'] = median(r['spanne'] for r in mit) if mit else None
    K['stk_median'] = median(r['stk'] for r in mit) if mit else None
    d = [r for r in packs if r.get('delta') is not None]
    K['d_hoeher'] = sum(1 for r in d if r['vk'] > r['alt'] + 0.005)
    K['d_hoeher10'] = sum(1 for r in d if round(r['delta'] * 100, 1) > 10)
    K['d_gleich'] = sum(1 for r in d if abs(r['vk'] - r['alt']) <= 0.005)
    K['d_niedriger'] = sum(1 for r in d if r['vk'] < r['alt'] - 0.005)
    K['d_niedriger10'] = sum(1 for r in d if round(r['delta'] * 100, 1) < -10)
    K['d_ohne'] = len(packs) - len(d)
    tot = sum(r['vk'] for r in packs)
    mb = lambda r: 'ohne' if r['m'] is None else 'gruen' if r['m'] >= 0.60 else 'orange' if r['m'] >= 0.50 else 'rot'  # noqa: E731
    for b in ('gruen', 'orange', 'rot', 'ohne'):
        K['m_' + b] = sum(1 for r in packs if mb(r) == b)
        K['u_' + b] = sum(r['vk'] for r in packs if mb(r) == b) / tot if tot else None
    known = [r for r in packs if r['m'] is not None]
    K['m_gew'] = 1 - sum(r['ek'] for r in known) / sum(r['vk'] for r in known) if known else None
    return K


def band(m):
    return 'ohne EK' if m is None else '≥ 70 %' if m >= 0.70 else '60–69 %' if m >= 0.60 else '50–59 %' if m >= 0.50 else 'unter 50 %'


def collect():
    rows, rate = tc.load()
    ek = {(r['form'], r['name'], r['strength']): r for r in rows}
    lines = cl.lines()
    out = []
    for x in lines:
        r = ek[(x['form'], x['name'], x['strength'])]
        cost = r['ting'] if r.get('ting') is not None else r.get('other')
        src = 'Ting' if r.get('ting') is not None else ('andere Lieferantin' if r.get('other') is not None else None)
        vk = x['price_cents'] / 100
        note = []
        if x.get('supplement'):
            note.append('neu im Sortiment')
        if src == 'andere Lieferantin':
            note.append('EK andere Lieferantin')
        if x['name'].startswith('Melanotan') and x['form'] == 'vial':
            note.append('Ting führt MT-1/MT-2 gemeinsam')
        if x.get('discount_ok'):
            note.append('Mengenrabatt möglich')
        out.append(dict(kind='pack', form=x['form'], section=x['section'], name=x['name'], strength=x['strength'], order=x['order'], ek=cost, vk=vk, ek2=r.get('ting2'), src=src, note=note))
    # Einzelverkauf der 25 Shop-Produkte (Vial, Doppelkammer) + Pen
    products = json.loads((APP / 'data/products.json').read_text())
    formats = {f['id']: f for f in json.loads((APP / 'data/shop-formats.json').read_text())}
    costs = json.loads((HERE / 'shop_costs.json').read_text())
    single = []
    for p in products:
        v, d = cl.MATCH[p['id']]
        for form, ref, vk in (('vial', v, p['price_cents'] / 100), ('dual', d, formats.get('dual-' + p['id'], {}).get('price_cents', 0) / 100 or None)):
            if vk is None:
                continue
            ek10, src = None, None
            if ref and (form, ref[0], ref[1]) in ek:
                rr = ek[(form, ref[0], ref[1])]
                ek10 = rr['ting'] if rr.get('ting') is not None else rr.get('other')
                src = 'Ting' if rr.get('ting') is not None else 'andere Lieferantin'
            if ek10 is None and p['id'] in costs:
                ek10 = costs[p['id']].get('vial10_eur' if form == 'vial' else 'dual10_eur')
                src = 'Ting' if ek10 else None
            single.append(dict(kind='single', form=form, section=p['category'], name=p['name'], strength=p['concentration'], order=int(p['num']), ek=ek10 / 10 if ek10 else None, vk=vk,
                               src=src, note=[], ek2=None))
    pen = formats.get('mehrweg-pen')
    if pen:
        single.append(dict(kind='single', form='pen', section='Zubehör', name='Mehrweg-Pen', strength='1 Stück', order=99, ek=None, vk=pen['price_cents'] / 100, src=None, note=['EK nicht in den Lieferantenlisten']))
    for r in out + single:
        r['m_eur'] = (r['vk'] - r['ek']) if r['ek'] is not None else None
        r['m'] = (r['m_eur'] / r['vk']) if r['ek'] is not None and r['vk'] else None
    return out, single, rate


def main():
    packs, single, rate = collect()
    W, H = landscape(A4)
    m = 12 * mm
    doc = BaseDocTemplate(str(OUT), pagesize=landscape(A4), leftMargin=m, rightMargin=m, topMargin=12 * mm, bottomMargin=14 * mm, title='Elements Labs · Margenübersicht', author='Elements Labs')

    def foot(c, d):
        c.saveState()
        c.setStrokeColor(LINE); c.line(m, 10.5 * mm, W - m, 10.5 * mm)
        c.setFont('Helvetica', 8); c.setFillColor(MUTED)
        c.drawString(m, 6.5 * mm, f'Elements Labs · Margenübersicht · Stand {STAND} · intern · Preise in Euro, Marge = (VK − EK) / VK')
        c.drawRightString(W - m, 6.5 * mm, f'Seite {d.page}')
        c.restoreState()

    doc.addPageTemplates([PageTemplate(id='p', frames=[Frame(m, 14 * mm, W - 2 * m, H - 26 * mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=foot)])
    h1 = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=22, leading=26, textColor=INK)
    sub = ParagraphStyle('sub', fontName='Helvetica', fontSize=10.5, leading=14, textColor=MUTED)
    h2 = ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=PET, spaceBefore=6, spaceAfter=4)
    body = ParagraphStyle('b', fontName='Helvetica', fontSize=8.8, leading=11.6, textColor=INK, spaceAfter=2)
    cell = ParagraphStyle('c', fontName='Helvetica', fontSize=8.4, leading=10.2, textColor=INK)
    cellb = ParagraphStyle('cb', parent=cell, fontName='Helvetica-Bold')
    rt = ParagraphStyle('rt', parent=cell, alignment=2)
    rtb = ParagraphStyle('rtb', parent=rt, fontName='Helvetica-Bold')
    hd = ParagraphStyle('hd', parent=rtb, fontSize=7.8, leading=9.4)
    hdl = ParagraphStyle('hdl', parent=cellb, fontSize=7.8, leading=9.4)
    small = ParagraphStyle('sm', parent=cell, fontSize=7.6, leading=9, textColor=colors.HexColor('#3C464F'))

    def tbl(data, widths, extra=None, pad=2.2):
        t = Table(data, colWidths=widths, repeatRows=1)
        style = [('BACKGROUND', (0, 0), (-1, 0), SOFT), ('LINEBELOW', (0, 0), (-1, 0), 0.8, PET), ('LINEBELOW', (0, 1), (-1, -1), 0.25, LINE), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                 ('TOPPADDING', (0, 0), (-1, -1), pad), ('BOTTOMPADDING', (0, 0), (-1, -1), pad)]
        t.setStyle(TableStyle(style + (extra or [])))
        return t

    def mcol(mv):
        return RED if mv is not None and mv < 0.50 else AMBER if mv is not None and mv < 0.60 else GREEN if mv is not None else MUTED

    def mp(mv, bold=True):
        return Paragraph(f'<font color="{mcol(mv).hexval().replace("0x", "#")}"><b>{pct(mv)}</b></font>', rt)

    def spz(r):
        sp_ = r.get('spanne')
        return Paragraph(f'<font color="{scol(sp_)}"><b>{pct1(sp_)}</b></font>' if sp_ is not None else '–', rt)

    def agg(rs):
        known = [r for r in rs if r['m'] is not None]
        if not known:
            return None, None, None
        return sum(r['m'] for r in known) / len(known), 1 - sum(r['ek'] for r in known) / sum(r['vk'] for r in known), min(r['m'] for r in known)

    lg_img, (lw, lh) = logo_png()
    img = RLImage(str(lg_img), width=34 * mm, height=34 * mm * lh / lw)
    img.hAlign = 'LEFT'
    sv = [r for r in single if r['form'] == 'vial']
    sd = [r for r in single if r['form'] == 'dual']
    pv = [r for r in packs if r['form'] == 'vial']
    pd = [r for r in packs if r['form'] == 'dual']
    sp = [r for r in single if r['form'] == 'pen']
    allr = single + packs
    noek = [r for r in allr if r['m'] is None]
    low = sorted([r for r in allr if r['m'] is not None], key=lambda r: r['m'])[:15]

    zpath = zeilen_csv()
    abw = kundensicht(packs, zpath)
    story = [img, Spacer(1, 2), Paragraph('Margenübersicht', h1),
             Paragraph(f'Einkaufspreis, Verkaufspreis und Marge für jedes Produkt im Shop – und wie viel Luft die 10er-Packs Ihren Händlern lassen · Stand {STAND}', sub), Spacer(1, 5)]
    bl = ParagraphStyle('bl', parent=body, fontSize=8.4, leading=10.6, leftIndent=9, firstLineIndent=-9)
    G, O_, R_ = '#067647', '#B54708', '#B42318'
    left = [
        '<b>Marge</b> = (Verkaufspreis − Einkaufspreis) / Verkaufspreis. Einkauf = sichtbarer Listenpreis von Ting (Dollar in Euro); wo Ting nicht liefert, die andere Lieferantin. Ohne Versand, Zoll, Zahlungsgebühren.',
        '<b>Einzelverkauf</b> (Endkunde): Einkauf = ein Zehntel des 10er-Preises. <b>10er-Packs</b> (Händler): Einkauf und Verkauf je 10 Stück.',
        f'<b>Farben Marge:</b> <font color="{G}"><b>grün</b></font> ab 60 %, <font color="{O_}"><b>orange</b></font> 50–59 %, <font color="{R_}"><b>rot</b></font> unter 50 %. „Faktor × EK“ = Verkauf geteilt durch Einkauf (2,5 × EK = 60 % Marge).',
        '<b>Mengenrabatt</b> ab 2.500 € (5 %) und 5.000 € (10 %): Packs mit Wert in der Spalte „Marge bei 10&nbsp;% Rabatt“ (dort „–“ = kein Mengenrabatt). <b>Ting-Zweitwert:</b> gerechnet mit dem sichtbaren, höheren Wert (vorsichtig).',
    ]
    right = [
        '<b>Händlerspanne am Markt</b> (nur 10er-Packs): Was Ihr Händler behält, wenn er jedes Stück zum üblichen Marktpreis weiterverkauft. Rechnung: 1 − (Packpreis ÷ 10) ÷ Markt-Median je Stück.',
        f'<b>Farben Händlerspanne:</b> <font color="{G}"><b>grün</b></font> ab 40 % (Händler verdient gut), <font color="{O_}"><b>orange</b></font> 30–39 %, <font color="{R_}"><b>rot</b></font> unter 30 % (wenig Luft für den Händler). „–“ = keine Marktdaten.',
        '<b>Pack je Stück vom Markt:</b> Preis eines Stücks im 10er-Pack in Prozent des Markt-Einzelpreises (niedrig = gut für den Händler).',
        '<b>Δ gegen alte Liste:</b> Änderung des Packpreises gegenüber der alten Verkaufsliste in Prozent (+ teurer, − günstiger, ± gleich).',
    ]
    story.append(Table([[[Paragraph('•&nbsp;&nbsp;' + x, bl) for x in left], [Paragraph('•&nbsp;&nbsp;' + x, bl) for x in right]]], colWidths=[(W - 2 * m) / 2 - 3 * mm, (W - 2 * m) / 2 + 3 * mm],
                       style=[('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (0, 0), 8), ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
    story.append(Spacer(1, 2))
    story.append(Paragraph('Überblick', h2))
    heads = ['Bereich', 'Zeilen', 'Ø Marge', 'Marge gewichtet', 'niedrigste', 'unter 50 %', 'ohne EK']
    data = [[Paragraph(h, hdl if i == 0 else hd) for i, h in enumerate(heads)]]
    for label, rs in (('Einzelverkauf Vial', sv), ('Einzelverkauf Doppelkammer', sd), ('Einzelverkauf Mehrweg-Pen', sp), ('10er-Packs Vial', pv), ('10er-Packs Doppelkammer', pd)):
        a, wgt, mn = agg(rs)
        data.append([Paragraph(f'<b>{label}</b>', cell), Paragraph(str(len(rs)), rt), mp(a), mp(wgt), mp(mn), Paragraph(str(sum(1 for r in rs if r['m'] is not None and r['m'] < 0.5)), rt),
                     Paragraph(str(sum(1 for r in rs if r['m'] is None)), rt)])
    a, wgt, mn = agg(allr)
    data.append([Paragraph('<b>Alles zusammen</b>', cell), Paragraph(str(len(allr)), rtb), mp(a), mp(wgt), mp(mn), Paragraph(str(sum(1 for r in allr if r['m'] is not None and r['m'] < 0.5)), rtb),
                 Paragraph(str(len(noek)), rtb)])
    story.append(tbl(data, [70 * mm, 24 * mm, 28 * mm, 34 * mm, 28 * mm, 26 * mm, 26 * mm], extra=[('LINEABOVE', (0, -1), (-1, -1), 0.8, PET)], pad=1.6))
    story.append(Paragraph('„Ø Marge“ ist der Durchschnitt über die Zeilen, „gewichtet“ der Durchschnitt nach Umsatz (eine Packung oder ein Stück je Zeile).', small))
    # Kundensicht (10er-Packs)
    K = kennzahlen(packs)
    story.append(Paragraph(f'Kundensicht – sind die 10er-Packs für Ihre Händler vernünftig? ({len(packs)} Packs)', h2))
    lab = ParagraphStyle('lab', parent=cell, fontSize=8.2, leading=9.8)
    sub_ = ParagraphStyle('sub_', parent=lab, leftIndent=8, textColor=MUTED)

    def c(txt, colr=None, bold=False):
        t_ = f'<b>{txt}</b>' if bold else str(txt)
        return Paragraph(f'<font color="{colr}">{t_}</font>' if colr else t_, rt)
    A = [(Paragraph(f'<font color="{G}"><b>ab 40 %</b></font> (grün)', lab), c(K['s_gruen'], G, True)),
         (Paragraph(f'<font color="{O_}"><b>30–39 %</b></font> (orange)', lab), c(K['s_orange'], O_, True)),
         (Paragraph(f'<font color="{R_}"><b>unter 30 %</b></font> (rot)', lab), c(K['s_rot'], R_, True)),
         (Paragraph('ohne Marktdaten', lab), c(K['s_ohne'])),
         (Paragraph('<b>Median Händlerspanne</b>', lab), c(pct1(K['s_median']), scol(K['s_median']), True)),
         (Paragraph('<b>Pack je Stück vom Markt</b> (Median)', lab), c(pct1(K['stk_median']), None, True))]
    B = [(Paragraph('höher', lab), c(K['d_hoeher'])), (Paragraph('davon mehr als +10 %', sub_), c(K['d_hoeher10'])), (Paragraph('gleich', lab), c(K['d_gleich'])),
         (Paragraph('niedriger', lab), c(K['d_niedriger'])), (Paragraph('davon mehr als −10 %', sub_), c(K['d_niedriger10'])), (Paragraph('ohne alten Preis', lab), c(K['d_ohne']))]
    C = [(Paragraph(f'<font color="{G}"><b>grün</b></font> ab 60 %', lab), c(K['m_gruen'], G, True), c(pct1(K['u_gruen']))),
         (Paragraph(f'<font color="{O_}"><b>orange</b></font> 50–59 %', lab), c(K['m_orange'], O_, True), c(pct1(K['u_orange']))),
         (Paragraph(f'<font color="{R_}"><b>rot</b></font> unter 50 %', lab), c(K['m_rot'], R_, True), c(pct1(K['u_rot']))),
         (Paragraph('ohne EK', lab), c(K['m_ohne']), c(pct1(K['u_ohne']))),
         (Paragraph('<b>Marge gewichtet</b>', lab), c(''), mp(K['m_gew'])), (Paragraph('', lab), c(''), c(''))]
    data = [[Paragraph(h, hdl if i in (0, 3, 6) else hd) for i, h in enumerate(['Händlerspanne am Markt', 'Packs', '', 'Gegen alte Verkaufsliste', 'Packs', '', 'Marge 10er-Packs', 'Packs', 'Umsatzanteil'])]]
    for a_, b_, c_ in zip(A, B, C):
        data.append([a_[0], a_[1], '', b_[0], b_[1], '', c_[0], c_[1], c_[2]])
    story.append(tbl(data, [58 * mm, 18 * mm, 8 * mm, 50 * mm, 18 * mm, 8 * mm, 44 * mm, 18 * mm, 26 * mm], pad=1.5,
                     extra=[('BACKGROUND', (2, 0), (2, -1), colors.white), ('BACKGROUND', (5, 0), (5, -1), colors.white), ('LINEBELOW', (2, 0), (2, -1), 0, colors.white),
                            ('LINEBELOW', (5, 0), (5, -1), 0, colors.white), ('LINEABOVE', (0, 5), (1, 5), 0.6, PET), ('LINEABOVE', (6, 5), (8, 5), 0.6, PET)]))
    story.append(Spacer(1, 2))
    story.append(Paragraph(f'<b>Auf einen Blick:</b> {K["s_gruen"]} von {K["s_mit"]} Packs mit Marktdaten lassen dem Händler mindestens 40 % Spanne, wenn er zum üblichen Marktpreis weiterverkauft; '
                           f'im Median sind es {pct1(K["s_median"])}. Ein Stück im 10er-Pack kostet ihn im Median {pct1(K["stk_median"])} des Markt-Einzelpreises. Packs mit wenig Spanne stehen ab Seite 3 („Zeilen mit Aufmerksamkeit“).', body))
    note = f'Marktpreise und alte Liste aus „{zpath.name}“ ({K["s_mit"]} Packs mit Marktdaten). Gerechnet ist mit dem Shop-Preis dieser Liste.'
    if abw:
        note += f' In {abw} Packs weicht der Preis in dieser Datei vom Shop-Preis ab (Datei = Vorschlag, Shop = gültig).'
    story.append(Paragraph(note, small))
    story.append(PageBreak())
    # Verteilung (Seite 2 oben)
    bands = ['≥ 70 %', '60–69 %', '50–59 %', 'unter 50 %', 'ohne EK']
    data = [[Paragraph(h, hdl if i == 0 else hd) for i, h in enumerate(['Marge'] + ['Einzel Vial', 'Einzel Doppelk.', 'Pen', '10er Vial', '10er Doppelk.'])]]
    for b in bands:
        data.append([Paragraph(f'<b>{b}</b>', cell)] + [Paragraph(str(sum(1 for r in rs if band(r['m']) == b)), rt) for rs in (sv, sd, sp, pv, pd)])
    story.append(Paragraph('Verteilung der Margen (Anzahl Zeilen)', h2))
    story.append(tbl(data, [70 * mm, 32 * mm, 32 * mm, 20 * mm, 32 * mm, 32 * mm], pad=1.6))
    story.append(Spacer(1, 4))

    # niedrigste + ohne EK
    story.append(Paragraph('Die 15 niedrigsten Margen', h2))
    cw = [W - 2 * m - 190 * mm, 38 * mm, 26 * mm, 24 * mm, 24 * mm, 24 * mm, 24 * mm, 30 * mm]
    ht = ['Produkt', 'Bereich', 'Dosis', 'EK', 'VK', 'Marge €', 'Marge', 'EK-Quelle']
    data = [[Paragraph(h, hdl if i < 3 or i == len(ht) - 1 else hd) for i, h in enumerate(ht)]]

    def area(r):
        return ('Einzel ' if r['kind'] == 'single' else '10er ') + ('Vial' if r['form'] == 'vial' else 'Doppelkammer' if r['form'] == 'dual' else 'Pen')

    for r in low:
        data.append([Paragraph(r['name'], cell), Paragraph(area(r), cell), Paragraph(r['strength'], cell), Paragraph(eur(r['ek'], 2), rt), Paragraph(eur(r['vk'], 2), rt),
                     Paragraph(eur(r['m_eur'], 2), rt), mp(r['m']), Paragraph(r['src'] or '–', cell)])
    story.append(tbl(data, cw))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f'Zeilen ohne Einkaufspreis ({len(noek)})', h2))
    if noek:
        story.append(Paragraph('Für diese Zeilen liegt in keiner Lieferantenliste ein Preis vor. Die Marge lässt sich nicht berechnen. Der Verkaufspreis steht trotzdem im Shop (Verkaufsblatt bzw. 3 × geschätzter Einkauf) und sollte nach Rückmeldung von Ting geprüft werden.', body))
        data = [[Paragraph(h, hdl if i < 3 or i == 4 else hd) for i, h in enumerate(['Produkt', 'Bereich', 'Dosis', 'VK', 'Hinweis'])]]
        for r in noek:
            data.append([Paragraph(r['name'], cell), Paragraph(area(r), cell), Paragraph(r['strength'], cell), Paragraph(eur(r['vk'], 2), rt), Paragraph('; '.join(r['note']) or 'bei Ting anfragen', cell)])
        story.append(tbl(data, [W - 2 * m - 200 * mm, 40 * mm, 40 * mm, 30 * mm, 90 * mm]))
    story.append(PageBreak())

    # Zeilen mit Aufmerksamkeit (Seite 3)
    story.append(Paragraph('Zeilen mit Aufmerksamkeit (10er-Packs)', h2))
    lowm = sorted([r for r in packs if r['m'] is not None and r['m'] < 0.60], key=lambda r: r['m'])
    story.append(Paragraph(f'<b>1 · Marge unter 60 % ({len(lowm)} Packs, orange/rot).</b> Ziel-EK = Einkaufspreis, bei dem dieses Pack 60 % Marge bringt (= Verkaufspreis ÷ 2,5, also 2,5 × EK). '
                           '„Senkung“ = so viel müsste der Einkauf sinken.', body))
    if lowm:
        ht = ['Produkt', 'Bereich', 'Dosis', 'EK', 'VK', 'Marge', 'Faktor × EK', 'Ziel-EK<br/>(60 %)', 'Senkung<br/>in €', 'Senkung<br/>in %', 'Händler-<br/>spanne']
        data = [[Paragraph(h, hdl if i < 3 else hd) for i, h in enumerate(ht)]]
        for r in lowm:
            ziel = r['vk'] / 2.5
            data.append([Paragraph(r['name'], cell), Paragraph(area(r), cell), Paragraph(r['strength'], cell), Paragraph(eur(r['ek'], 2), rt), Paragraph(eur(r['vk'], 2), rt), mp(r['m']),
                         Paragraph(f"{r['fx']:.2f} ×".replace('.', ','), rt), Paragraph(f'<b>{eur(ziel, 2)}</b>', rt), Paragraph(eur(r['ek'] - ziel, 2), rt), Paragraph(pct1((r['ek'] - ziel) / r['ek']), rt), spz(r)])
        story.append(tbl(data, [W - 2 * m - 212 * mm, 33 * mm, 34 * mm, 18 * mm, 20 * mm, 15 * mm, 18 * mm, 20 * mm, 18 * mm, 16 * mm, 20 * mm], pad=1.0))
    else:
        story.append(Paragraph('Keine – alle Packs mit Einkaufspreis haben mindestens 60 % Marge.', body))
    story.append(Spacer(1, 3))
    lows = sorted([r for r in packs if r.get('spanne') is not None and sband(r['spanne']) != 'gruen'], key=lambda r: r['spanne'])
    story.append(Paragraph(f'<b>2 · Händlerspanne am Markt unter 40 % ({len(lows)} Packs).</b> Hier bleibt dem Händler beim Weiterverkauf zum Marktpreis wenig. '
                           'Pack je Stück = Packpreis ÷ 10.', body))
    if lows:
        ht = ['Produkt', 'Bereich', 'Dosis', 'VK', 'Pack je Stück', 'Markt je Stück', 'Pack je Stück vom Markt', 'Händler-<br/>spanne', 'Faktor × EK', 'Marge']
        data = [[Paragraph(h, hdl if i < 3 else hd) for i, h in enumerate(ht)]]
        for r in lows:
            data.append([Paragraph(r['name'], cell), Paragraph(area(r), cell), Paragraph(r['strength'], cell), Paragraph(eur(r['vk'], 2), rt), Paragraph(eur(r['vk'] / 10, 2), rt),
                         Paragraph(eur(r['mkt'], 2), rt), Paragraph(pct1(r['stk']), rt), spz(r),
                         Paragraph('–' if r['fx'] is None else f"{r['fx']:.2f} ×".replace('.', ','), rt), mp(r['m'])])
        story.append(tbl(data, [W - 2 * m - 207 * mm, 33 * mm, 34 * mm, 20 * mm, 20 * mm, 20 * mm, 24 * mm, 22 * mm, 18 * mm, 16 * mm], pad=1.0))
    else:
        story.append(Paragraph('Keine – alle Packs mit Marktdaten lassen dem Händler mindestens 40 %.', body))
    story.append(Spacer(1, 3))
    story.append(Paragraph('<b>Was das für die Verhandlung mit Ting bedeutet:</b> Bei Tabelle 1 liegt der Hebel im Einkauf – der Verkaufspreis bleibt, Ting müsste auf den Ziel-EK kommen. '
                           'Bei Tabelle 2 ist der Packpreis für Händler schon eng am Markt: Preis nicht erhöhen; bei hohem Faktor × EK (ab 3) wäre Luft für einen niedrigeren Packpreis, '
                           'unter 2,5 hilft nur ein günstigerer Einkauf. Packs in beiden Tabellen zuerst mit Ting besprechen.', body))
    story.append(PageBreakIfNotEmpty())

    def disc(r):
        if 'Mengenrabatt möglich' in r['note'] and r['ek'] is not None:
            return mp(1 - r['ek'] / (0.9 * r['vk']))
        return Paragraph('–', rt)

    def block(title, rs, per_euro=2, secs=True):
        story.append(Paragraph(title, h2))
        simple = rs and rs[0]['kind'] == 'single'
        if simple:
            heads_ = ['Produkt', 'Dosis', 'EK', 'VK', 'Marge €', 'Marge %', 'Hinweis']
            cw_ = [W - 2 * m - 160 * mm, 38 * mm, 24 * mm, 24 * mm, 26 * mm, 20 * mm, 28 * mm]
        else:  # 10er-Packs: + Haendlerspanne am Markt, Delta gegen alte Liste
            heads_ = ['Produkt', 'Dosis', 'EK', 'VK', 'Marge €', 'Marge %', 'Marge bei\n10 % Rabatt', 'Händler-\nspanne\nam Markt', 'Δ gegen\nalte Liste', 'Hinweis']
            # Produkt und Dosis ohne Zeilenumbruch (die Pruefung liest Name/Dosis zeilenweise): Breite nach dem laengsten Eintrag, Rest an „Hinweis“
            wn = max(stringWidth(r['name'], 'Helvetica', 8.4) for r in packs) + 13
            wd = max(stringWidth(r['strength'], 'Helvetica', 8.4) for r in packs) + 13
            fixed = [21 * mm, 22 * mm, 20 * mm, 17 * mm, 20 * mm, 20 * mm, 19 * mm]
            cw_ = [wn, wd] + fixed + [W - 2 * m - wn - wd - sum(fixed)]
            assert cw_[-1] >= 28 * mm, f'Hinweis-Spalte zu schmal: {cw_[-1] / mm:.1f} mm'
        nc = len(heads_)
        data = [[Paragraph(h.replace('\n', '<br/>'), hdl if i in (0, 1, nc - 1) else hd) for i, h in enumerate(heads_)]]
        extra = []
        last = None
        for r in sorted(rs, key=lambda r: (cl.SECTIONS.index(r['section']) if r['section'] in cl.SECTIONS else 99, r['order'])):
            if secs and r['section'] != last:
                last = r['section']
                data.append([Paragraph(f'<b>{last}</b>', ParagraphStyle('s', parent=cell, textColor=PET))] + [''] * (nc - 1))
                extra += [('SPAN', (0, len(data) - 1), (-1, len(data) - 1)), ('BACKGROUND', (0, len(data) - 1), (-1, len(data) - 1), SOFT)]
            data.append([Paragraph(r['name'], cell), Paragraph(r['strength'], cell), Paragraph(eur(r['ek'], per_euro), rt), Paragraph(f"<b>{eur(r['vk'], per_euro)}</b>", rt),
                         Paragraph(eur(r['m_eur'], per_euro), rt), mp(r['m'])] + ([] if simple else [disc(r), spz(r), Paragraph(pct1(r.get('delta'), sign=True), rt)])
                        + [Paragraph(', '.join(x for x in r['note'] if simple or x != 'Mengenrabatt möglich'), small)])  # Rabatt steht in eigener Spalte
        story.append(tbl(data, cw_, extra=extra, pad=1.7))

    block('Einzelverkauf · Vial (Endkundenpreis)', [dict(r, note=[]) for r in sv], 2, secs=False)
    story.append(PageBreak())
    block('Einzelverkauf · Doppelkammer und Pen (Endkundenpreis)', sd + sp, 2, secs=False)
    story.append(PageBreak())
    block('10er-Packs · Vial (Händlerpreis je 10 Stück)', pv)
    story.append(PageBreak())
    block('10er-Packs · Doppelkammer (Händlerpreis je 10 Stück)', pd)
    doc.build(story)
    disc_rows = [r for r in packs if 'Mengenrabatt möglich' in r['note'] and r['ek'] is not None]
    print('geschrieben', OUT)
    print('min Marge Packs exakt', round(min(r['m'] for r in packs if r['m'] is not None), 4), '| min nach 10 % Rabatt', round(min(1 - r['ek'] / (0.9 * r['vk']) for r in disc_rows), 4), '| Rabattzeilen', len(disc_rows))
    print('Kennzahlen-Datei', zpath, '| Packs mit abweichendem Datei-Preis', abw, '|', {k: (round(v, 4) if isinstance(v, float) else v) for k, v in kennzahlen(packs).items()})
    print('ohne EK:', [(r['form'], r['name'], r['strength']) for r in noek])
    for label, rs in (('Einzel Vial', sv), ('Einzel Dual', sd), ('Pen', sp), ('Pack Vial', pv), ('Pack Dual', pd), ('alles', allr)):
        a, wgt, mn = agg(rs)
        print(label, len(rs), 'Ø', pct(a), 'gewichtet', pct(wgt), 'min', pct(mn), 'unter50', sum(1 for r in rs if r['m'] is not None and r['m'] < 0.5), 'ohneEK', sum(1 for r in rs if r['m'] is None))


if __name__ == '__main__':
    main()
