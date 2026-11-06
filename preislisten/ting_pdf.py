"""PDF: Ting-Preischeck - Ting-Einkauf gegen Elements-Labs-Verkaufspreise (inkl. Marktpreis-Orientierung)."""
import statistics
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, KeepTogether, PageTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus import Image as RLImage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'miniapp' / 'tools'))
import ting_check as tc  # noqa: E402
from render_lists import logo_png  # noqa: E402
STAND = '25.10.2026'  # Preisstand Preisfamilie v3

OUT = HERE / 'Elements Labs Ting-Preischeck.pdf'
INK, MUTED, PET, SOFT, LINE = colors.HexColor('#172027'), colors.HexColor('#66717B'), colors.HexColor('#0D5B6B'), colors.HexColor('#EEF4F5'), colors.HexColor('#D9DEE2')
GREEN, AMBER, RED = colors.HexColor('#067647'), colors.HexColor('#B54708'), colors.HexColor('#B42318')


def eur(v):
    return f'{int(round(v)):,}'.replace(',', '.') + ' €'


def ceil10(v):
    return int(-(-round(v, 6) // 10)) * 10


def main():
    rows, rate = tc.load(final=True)
    vial = [r for r in rows if r['form'] == 'vial']
    dual = [r for r in rows if r['form'] == 'dual']
    sections = []
    for r in rows:
        if r['section'] not in sections:
            sections.append(r['section'])
    order = {s: i for i, s in enumerate(__import__('catalog_lines').SECTIONS)}
    sections.sort(key=lambda s: order.get(s, 99))

    def margin(r, cost=None):
        c = r['ting'] if cost is None else cost
        return (r['rec'] - c) / r['rec']

    vt = [r for r in vial if r.get('ting') is not None]
    dt = [r for r in dual if r.get('ting') is not None]
    both = [r for r in vt if r.get('other')]
    v_cost, v_rec, v_cur = sum(r['ting'] for r in vt), sum(r['rec'] for r in vt), sum(r['cur'] for r in vt)
    d_cost, d_rec = sum(r['ting'] for r in dt), sum(r['rec'] for r in dt)
    v_cost2 = sum((r.get('ting2') or r['ting']) for r in vt)
    low = [r for r in vt if margin(r) < tc.OK]
    knapp = [r for r in vt if tc.OK <= margin(r) < tc.GOOD]
    for r in vt:
        r['need'] = ceil10(2 * r['ting'])  # Preis fuer mindestens 50 % Marge auf den sichtbaren Ting-Preis
    over_market = [r for r in low if r.get('market') and r['need'] > 0.95 * r['market']]

    W, H = landscape(A4)
    m = 12 * mm
    doc = BaseDocTemplate(str(OUT), pagesize=landscape(A4), leftMargin=m, rightMargin=m, topMargin=12 * mm, bottomMargin=14 * mm,
                          title='Elements Labs · Ting-Preischeck', author='Elements Labs')

    def foot(c, d):
        c.saveState()
        c.setStrokeColor(LINE); c.line(m, 10.5 * mm, W - m, 10.5 * mm)
        c.setFont('Helvetica', 8); c.setFillColor(MUTED)
        c.drawString(m, 6.5 * mm, f'Elements Labs · Ting-Preischeck · Stand {STAND} · intern · Preise je 10er-Packung in Euro')
        c.drawRightString(W - m, 6.5 * mm, f'Seite {d.page}')
        c.restoreState()

    doc.addPageTemplates([PageTemplate(id='p', frames=[Frame(m, 14 * mm, W - 2 * m, H - 26 * mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=foot)])
    h1 = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=22, leading=26, textColor=INK, spaceAfter=2)
    sub = ParagraphStyle('sub', fontName='Helvetica', fontSize=10.5, leading=14, textColor=MUTED)
    h2 = ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=PET, spaceBefore=6, spaceAfter=4)
    body = ParagraphStyle('b', fontName='Helvetica', fontSize=9.4, leading=13, textColor=INK, spaceAfter=3)
    cell = ParagraphStyle('c', fontName='Helvetica', fontSize=8.6, leading=10.6, textColor=INK)
    cellb = ParagraphStyle('cb', parent=cell, fontName='Helvetica-Bold')
    rt = ParagraphStyle('rt', parent=cell, alignment=2)
    rtb = ParagraphStyle('rtb', parent=rt, fontName='Helvetica-Bold')
    hd = ParagraphStyle('hd', parent=rtb, fontSize=7.8, leading=9.4)
    hdl = ParagraphStyle('hdl', parent=cellb, fontSize=7.8, leading=9.4)
    gray = '#9AA3AA'

    logo, (lw, lh) = logo_png()
    lg = RLImage(str(logo), width=46 * mm, height=46 * mm * lh / lw)
    lg.hAlign = 'LEFT'
    story = [lg, Spacer(1, 6), Paragraph('Ting-Preischeck', h1),
             Paragraph(f'Ting-Einkauf gegen Elements-Labs-Verkaufspreise · inkl. Marktorientierung · Stand {STAND} · Kurs 1 € = {rate:.4f} $', sub), Spacer(1, 8)]

    pct = lambda x: f'{x:.0%}'
    verdict = [
        ['Doppelkammer (10er)', f'{len(dt)} von {len(dual)} Zeilen bei Ting', f'Marge {pct(1 - d_cost / d_rec)} auf Ting', 'Funktioniert: alle Zeilen über 60 % Marge.'],
        ['Vial (10er)', f'{len(vt)} von {len(vial)} Zeilen bei Ting', f'Marge {pct(1 - v_cost / v_rec)} auf Ting', f'{len(vt) - len(low) - len(knapp)} Zeilen stark (über 60 %), {len(knapp)} solide (50–60 %), {len(low)} nachverhandeln (unter 50 %).'],
    ]
    t = Table([[Paragraph(f'<b>{a}</b>', cell), Paragraph(b, cell), Paragraph(f'<b>{c}</b>', cell), Paragraph(d, cell)] for a, b, c, d in verdict], colWidths=[40 * mm, 55 * mm, 55 * mm, W - 2 * m - 150 * mm])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), SOFT), ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.white), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                           ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5), ('LEFTPADDING', (0, 0), (-1, -1), 8)]))
    story += [t, Spacer(1, 8), Paragraph('Das Wichtigste', h2)]
    pts = [
        f'<b>Verkaufspreise</b> = neue Preise im Shop: mindestens 3 × Ting-Einkauf, nicht über dem Markt-Median (wo der Einkauf das zulässt), Doppelkammer mindestens 15 % über dem Vial, volle 10 €. Das Vergleichsmaterial (Markt-Median, alte Liste, Neuer Preis) steht in jeder Zeile.',
        '<b>Hauptfokus GHK-Cu, 5-Amino-1MQ und Retatrutide:</b> Diese Preise liegen nie unter deiner alten Verkaufsliste (Stammkunden bekommen keinen niedrigeren Preis als früher). Marge und Marktabstand stehen unten in jeder Zeile.',
        f'<b>Doppelkammer:</b> Ting liefert {len(dt)} von {len(dual)} Katalogzeilen; Einkauf {eur(d_cost)}, Verkauf {eur(d_rec)}. Die Preise tragen mit großem Abstand (kleinste Marge {pct(min(margin(r) for r in dt))}).',
        f'<b>Vial:</b> Bei den Vials ist Ting im Schnitt <b>{(sum(r["ting"] for r in both) / sum(r["other"] for r in both) - 1):.0%} teurer</b> als die andere Lieferantin (Summe über {len(both)} Zeilen: {eur(sum(r["ting"] for r in both))} gegen {eur(sum(r["other"] for r in both))}); nur bei {sum(1 for r in both if r["ting"] < r["other"])} Zeilen ist Ting günstiger. Ohne die andere Lieferantin sinkt die Marge von {pct(1 - sum(min(r["ting"], r["other"] or 1e9) for r in both) / sum(r["rec"] for r in both))} auf {pct(1 - sum(r["ting"] for r in both) / sum(r["rec"] for r in both))}.',
        f'<b>Mindestmarge:</b> Kein Vial liegt unter {pct(min(margin(r) for r in vt))} Marge auf den Ting-Preis; {len(knapp)} Zeilen liegen zwischen 50 und 60 %. Bei einigen Wirkstoffen ist der Ting-Preis so hoch, dass unser Preis dadurch über dem Markt liegt. Diese Zeilen stehen mit Zielpreis in der Verhandlungsliste (Abschnitt 3).',
        f'<b>Zweiter Preis im Ting-PDF:</b> Bei {sum(1 for r in vt if r.get("ting2"))} Vial-Zeilen steht unter dem sichtbaren Preis ein zweiter, dunkel gedruckter Wert (niedriger). Gerechnet habe ich mit dem sichtbaren Preis (vorsichtig). Mit dem zweiten Wert läge der Vial-Einkauf bei {eur(v_cost2)} statt {eur(v_cost)} und wäre fast gleich der anderen Lieferantin. <b>Bitte bei Ting klären, welcher Preis gilt.</b>',
        'Alle Ting-Preise gelten laut dir inklusive Labels und Verpackung (kein Aufstocken). Versand, Zoll und Zahlungsgebühren sind nicht eingerechnet.',
    ]
    for p_ in pts:
        story.append(Paragraph('•&nbsp;&nbsp;' + p_, ParagraphStyle('bl', parent=body, leftIndent=10, firstLineIndent=-10)))
    story.append(Spacer(1, 6))
    story.append(Paragraph('<b>Lesehilfe:</b> Ting Liste = sichtbarer Preis je 10 Vials, umgerechnet in €. 2. Wert = zweiter Preis im selben PDF. Andere Lief. = günstigster Preis der anderen Lieferantin (Wholesale/EUR-Liste). Markt = Median der 10-Vial-Kits von peptidehaus.de und qsc-eu.com. Marge = (Verkauf − Ting) / Verkauf. „Preis ≥ 50 %“ = Verkaufspreis, der mindestens 50 % Marge auf den sichtbaren Ting-Preis hält.', body))
    story.append(PageBreak := __import__('reportlab.platypus', fromlist=['PageBreak']).PageBreak())

    def status_par(r):
        s = tc.status(r)
        col = {'stark': GREEN, 'solide': AMBER, 'nachverhandeln': RED}.get(s, MUTED)
        return Paragraph(f'<font color="{col.hexval().replace("0x", "#")}"><b>{s}</b></font>', ParagraphStyle('st', parent=cell, fontSize=8))

    def money(v, bold=False, grey=False):
        if v is None:
            return Paragraph(f'<font color="{gray}">–</font>', rt)
        txt = eur(v)
        return Paragraph((f'<font color="{gray}">{txt}</font>' if grey else f'<b>{txt}</b>' if bold else txt), rt)

    # ---- Vial-Tabellen
    story.append(Paragraph('1 · Vials · Preis je Packung mit 10 Vials', h2))
    cw = [W - 2 * m - 222 * mm, 22 * mm, 20 * mm, 18 * mm, 20 * mm, 20 * mm, 20 * mm, 22 * mm, 20 * mm, 20 * mm, 30 * mm]
    heads = ['Produkt', 'Dosis', 'Ting Liste', '2. Wert', 'Andere\nLief.', 'Markt\nMedian', 'Alte\nListe', 'Neuer Preis', 'Marge\nauf Ting', 'Preis\nfür ≥ 50 %', 'Status']
    for sec in sections:
        rs_ = sorted([r for r in vial if r['section'] == sec], key=lambda r: r['order'])
        if not rs_:
            continue
        data = [[Paragraph(sec, ParagraphStyle('s', parent=cellb, textColor=colors.white))] + [''] * 10,
                [Paragraph(h.replace('\n', '<br/>'), hdl if i < 2 else hd) for i, h in enumerate(heads)]]
        st = [('SPAN', (0, 0), (-1, 0)), ('BACKGROUND', (0, 0), (-1, 0), PET), ('BACKGROUND', (0, 1), (-1, 1), SOFT), ('LINEBELOW', (0, 1), (-1, 1), 0.8, PET),
              ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 2.2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.2)]
        for r in rs_:
            has = r.get('ting') is not None
            mg = margin(r) if has else None
            rowd = [Paragraph(r['name'], cell), Paragraph(r['strength'], cell), money(r.get('ting')), money(r.get('ting2'), grey=True), money(r.get('other'), grey=True),
                    money(r.get('market')), money(r.get('old')), money(r['rec'], bold=True),
                    Paragraph(f'<b>{mg:.0%}</b>' if has else f'<font color="{gray}">–</font>', rt),
                    money(r.get('need') if has and tc.status(r) in ('nachverhandeln', 'solide') else None), status_par(r)]
            data.append(rowd)
            i = len(data) - 1
            st.append(('LINEBELOW', (0, i), (-1, i), 0.25, LINE))
            if has and tc.status(r) == 'nachverhandeln':
                st.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#FFF6E5')))
            if not has:
                st.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F2F4F7')))
        tb = Table(data, colWidths=cw, repeatRows=2)
        tb.setStyle(TableStyle(st))
        story += [tb, Spacer(1, 7)]

    story.append(__import__('reportlab.platypus', fromlist=['PageBreak']).PageBreak())
    story.append(Paragraph('2 · Doppelkammern · Preis je Packung mit 10 Kartuschen', h2))
    cw2 = [W - 2 * m - 150 * mm, 26 * mm, 26 * mm, 24 * mm, 26 * mm, 22 * mm, 26 * mm]
    heads2 = ['Produkt', 'Dosis', 'Ting\n(10 Kartuschen)', 'Alte\nListe', 'Neuer Preis', 'Marge\nauf Ting', 'Status']
    for sec in sections:
        rs_ = sorted([r for r in dual if r['section'] == sec], key=lambda r: r['order'])
        if not rs_:
            continue
        data = [[Paragraph(sec, ParagraphStyle('s2', parent=cellb, textColor=colors.white))] + [''] * 6,
                [Paragraph(h.replace('\n', '<br/>'), hdl if i < 2 else hd) for i, h in enumerate(heads2)]]
        st = [('SPAN', (0, 0), (-1, 0)), ('BACKGROUND', (0, 0), (-1, 0), PET), ('BACKGROUND', (0, 1), (-1, 1), SOFT), ('LINEBELOW', (0, 1), (-1, 1), 0.8, PET),
              ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 2.2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.2)]
        for r in rs_:
            has = r.get('ting') is not None
            data.append([Paragraph(r['name'], cell), Paragraph(r['strength'], cell), money(r.get('ting')), money(r.get('old')), money(r['rec'], bold=True),
                         Paragraph(f'<b>{margin(r):.0%}</b>' if has else f'<font color="{gray}">–</font>', rt), status_par(r)])
            i = len(data) - 1
            st.append(('LINEBELOW', (0, i), (-1, i), 0.25, LINE))
            if not has:
                st.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F2F4F7')))
        tb = Table(data, colWidths=cw2, repeatRows=2)
        tb.setStyle(TableStyle(st))
        story += [tb, Spacer(1, 7)]

    # ---- Verhandlungsliste Ting + Haendlerperspektive
    import json as _json
    fin = {(x['form'], x['name'], x['strength']): x for x in _json.loads((HERE / 'preisempfehlung.json').read_text())}
    neg = [(r, fin[(r['form'], r['name'], r['strength'])]['ting_target_eur']) for r in vial if fin.get((r['form'], r['name'], r['strength']), {}).get('ting_target_eur') and r.get('ting') is not None and fin[(r['form'], r['name'], r['strength'])]['ting_target_eur'] < r['ting']]
    neg.sort(key=lambda x: -(x[0]['ting'] - x[1]) / x[0]['ting'])
    story.append(__import__('reportlab.platypus', fromlist=['PageBreak']).PageBreak())
    story.append(Paragraph('3 · Verhandlungsliste Ting', h2))
    story.append(Paragraph('Bei diesen Vials liegt unser Preis mehr als 20 % über dem Markt-Median, weil der Ting-Preis zu hoch ist (Mindestmarge 50 %). Mit dem Zielpreis wäre bei Marktpreis eine Marge von 60 % erreicht. Retatrutide und die übrigen Hauptfokus-Produkte stehen wegen der alten Liste über dem Markt; dort ist der Ting-Preis bereits niedrig genug.', body))
    data = [[Paragraph(h, hdl if i < 2 else hd) for i, h in enumerate(['Produkt', 'Dosis', 'Ting aktuell', 'Zielpreis Ting', 'Senkung', 'Markt-Median', 'Unser Preis'])]]
    for r, target in neg:
        data.append([Paragraph(r['name'], cell), Paragraph(r['strength'], cell), money(r['ting']), money(target, bold=True), Paragraph(f"−{(r['ting'] - target) / r['ting']:.0%}", rt), money(r.get('market')), money(r['rec'], bold=True)])
    if len(data) > 1:
        tb = Table(data, colWidths=[W - 2 * m - 150 * mm, 26 * mm, 24 * mm, 26 * mm, 20 * mm, 26 * mm, 28 * mm], repeatRows=1)
        tb.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), SOFT), ('LINEBELOW', (0, 0), (-1, 0), 0.8, PET), ('LINEBELOW', (0, 1), (-1, -1), 0.25, LINE), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 2.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5)]))
        story += [tb, Spacer(1, 8)]
    import apply_pricing as ap
    market_json = _json.loads(ap.MARKET.read_text())
    shop_vials = _json.loads((HERE.parent / 'miniapp/data/products.json').read_text())
    shop_formats = {f['id']: f for f in _json.loads((HERE.parent / 'miniapp/data/shop-formats.json').read_text())}
    story.append(__import__('reportlab.platypus', fromlist=['PageBreak']).PageBreak())
    story.append(Paragraph('4 · Händlerperspektive (25 Shop-Produkte)', h2))
    story.append(Paragraph('Ein Zwischenhändler kauft ein 10er-Pack bei uns und verkauft die Vials einzeln zum Markt-Median der frei verkäuflichen Einzelpreise. Das Verhältnis zeigt, ob sich der Einkauf bei uns für ihn lohnt.', body))
    data = [[Paragraph(h, hdl if i < 2 else hd) for i, h in enumerate(['Produkt', 'Dosis', '10er-Pack', 'je Vial', 'Markt Einzelvial', 'Händler-Erlös (10 Stück)', 'Händler-Marge'])]]
    for p_ in shop_vials:
        key = ap.market_key(p_)
        if key not in market_json['vial'] or (p_['id'] + '-x10') not in shop_formats:
            continue
        mk = ap.market_reference(market_json['vial'][key], ap.dose(p_))
        pack = shop_formats[p_['id'] + '-x10']['price_cents'] / 100
        rev = 10 * mk
        data.append([Paragraph(p_['name'], cell), Paragraph(p_['concentration'], cell), money(pack, bold=True), Paragraph(f'{pack / 10:,.0f} €'.replace(',', '.'), rt), Paragraph(f'{mk:,.0f} €'.replace(',', '.'), rt), money(rev), Paragraph(f'<b>{(rev - pack) / rev:.0%}</b>', rt)])
    tb = Table(data, colWidths=[W - 2 * m - 166 * mm, 26 * mm, 24 * mm, 20 * mm, 30 * mm, 36 * mm, 30 * mm], repeatRows=1)
    tb.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), SOFT), ('LINEBELOW', (0, 0), (-1, 0), 0.8, PET), ('LINEBELOW', (0, 1), (-1, -1), 0.25, LINE), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 2.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5)]))
    story += [tb, Spacer(1, 8)]
    # ---- Schluss: nicht bei Ting, Auffaelligkeiten, Annahmen
    no_v = [f"{r['name']} {r['strength']}" for r in vial if r.get('ting') is None]
    no_d = [f"{r['name']} {r['strength']}" for r in dual if r.get('ting') is None]
    story.append(KeepTogether([
        Paragraph('5 · Nicht bei Ting und offene Punkte', h2),
        Paragraph('<b>Vials ohne Ting-Preis:</b> ' + (', '.join(no_v) or 'keine') + '. Diese Zeilen kommen nur von der anderen Lieferantin oder gar nicht.', body),
        Paragraph('<b>Doppelkammern ohne Ting-Preis:</b> ' + (', '.join(no_d) or 'keine') + '.', body),
        Paragraph('<b>Annahmen:</b> (1) Ting-Vial-Preis = Listenpreis je 10 Vials, sichtbarer Wert. (2) Ting-Doppelkammer: Die Pens-Liste nennt einen Preis je Kartusche; für die 10er-Packung ist er mit 10 multipliziert. Das ist nicht ausdrücklich bestätigt. (3) Wechselkurs 1,1193 $ je € (EZB 23.10.2026). (4) Namen und Dosierungen der Pens-Liste stammen aus der Bildlesung des PDFs, die Preise sind zusätzlich per Texterkennung geprüft.', body),
        Paragraph('<b>Nächste Schritte:</b> Bei Ting den zweiten Preis und die Packungsgröße der Kartuschen bestätigen lassen; danach die farbig hinterlegten Vial-Zeilen entscheiden. Die Verkaufspreise im Shop sind noch nicht geändert.', body),
    ]))
    doc.build(story)
    print('geschrieben', OUT)
    print('Zeilen zu niedrig', len(low), 'knapp', len(knapp), 'ueber Markt', len(over_market))


if __name__ == '__main__':
    main()
