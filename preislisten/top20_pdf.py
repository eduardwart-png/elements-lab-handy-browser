"""PDF: Top-20 Bestseller (EU-Shops, Bestseller-Sortierung) mit Marktpreisen, Einkauf heute und Wunsch-Einkaufspreisen fuer die Ting-Verhandlung."""
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, KeepTogether, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus import Image as RLImage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'miniapp' / 'tools'))
import ting_check as tc  # noqa: E402
import top_seller as ts  # noqa: E402
from render_lists import logo_png  # noqa: E402

OUT = HERE / 'Elements Labs Top-20 Bestseller.pdf'
INK, MUTED, PET, SOFT, LINE = colors.HexColor('#172027'), colors.HexColor('#66717B'), colors.HexColor('#0D5B6B'), colors.HexColor('#EEF4F5'), colors.HexColor('#D9DEE2')
GREEN, AMBER = colors.HexColor('#067647'), colors.HexColor('#B54708')
TARGET_MARGIN = 0.60


def eur(v):
    return '–' if v is None else f'{int(round(v)):,}'.replace(',', '.') + ' €'


def floor5(v):
    return int(v // 5) * 5


def main():
    rows, rate = tc.load(final=True)
    vial = [r for r in rows if r['form'] == 'vial']
    top = [t for t in ts.ranking() if ts.catalog_rows(t[0])][:20]
    names_by_sub = {}
    for sub, score, shops, pos in top:
        keys = {(x['name'], x['strength']) for x in ts.catalog_rows(sub) if x['form'] == 'vial'}
        names_by_sub[sub] = sorted([r for r in vial if (r['name'], r['strength']) in keys], key=lambda r: r['order'])
    # Kennzahlen
    summary = []
    for rank, (sub, score, shops, pos) in enumerate(top, 1):
        rs = [r for r in names_by_sub[sub] if r.get('ting') is not None]
        for r in rs:
            known = [v for v in (r.get('ting'), r.get('other')) if v is not None]
            r['best'] = min(known)
            r['wish'] = min(r['best'], floor5((1 - TARGET_MARGIN) * r['market'])) if r.get('market') else r['best']
        save_best = sum(r['ting'] - r['best'] for r in rs)
        save_wish = sum(r['ting'] - r['wish'] for r in rs)
        cost = sum(r['ting'] for r in rs)
        rev = sum(r['rec'] for r in rs)
        summary.append(dict(rank=rank, sub=sub, shops=len(shops), best_pos=min(pos.values()), rows=len(rs), margin=(1 - cost / rev) if rev else None, save_best=save_best, save_wish=save_wish, cost=cost))

    W, H = landscape(A4)
    m = 12 * mm
    doc = BaseDocTemplate(str(OUT), pagesize=landscape(A4), leftMargin=m, rightMargin=m, topMargin=12 * mm, bottomMargin=14 * mm, title='Elements Labs · Top-20 Bestseller', author='Elements Labs')

    def foot(c, d):
        c.saveState()
        c.setStrokeColor(LINE); c.line(m, 10.5 * mm, W - m, 10.5 * mm)
        c.setFont('Helvetica', 8); c.setFillColor(MUTED)
        c.drawString(m, 6.5 * mm, 'Elements Labs · Top-20 Bestseller · Stand 25.10.2026 · intern · Preise je 10er-Packung in Euro')
        c.drawRightString(W - m, 6.5 * mm, f'Seite {d.page}')
        c.restoreState()

    doc.addPageTemplates([PageTemplate(id='p', frames=[Frame(m, 14 * mm, W - 2 * m, H - 26 * mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=foot)])
    h1 = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=22, leading=26, textColor=INK)
    sub = ParagraphStyle('sub', fontName='Helvetica', fontSize=10.5, leading=14, textColor=MUTED)
    h2 = ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=PET, spaceBefore=6, spaceAfter=4)
    body = ParagraphStyle('b', fontName='Helvetica', fontSize=8.8, leading=11.6, textColor=INK, spaceAfter=2)
    cell = ParagraphStyle('c', fontName='Helvetica', fontSize=8.8, leading=10.8, textColor=INK)
    cellb = ParagraphStyle('cb', parent=cell, fontName='Helvetica-Bold')
    rt = ParagraphStyle('rt', parent=cell, alignment=2)
    rtb = ParagraphStyle('rtb', parent=rt, fontName='Helvetica-Bold')
    hd = ParagraphStyle('hd', parent=rtb, fontSize=7.8, leading=9.4)
    hdl = ParagraphStyle('hdl', parent=cellb, fontSize=7.8, leading=9.4)

    def tbl(data, widths, repeat=1, extra=None, pad=2.6):
        t = Table(data, colWidths=widths, repeatRows=repeat)
        style = [('BACKGROUND', (0, 0), (-1, 0), SOFT), ('LINEBELOW', (0, 0), (-1, 0), 0.8, PET), ('LINEBELOW', (0, 1), (-1, -1), 0.25, LINE), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                 ('TOPPADDING', (0, 0), (-1, -1), pad), ('BOTTOMPADDING', (0, 0), (-1, -1), pad)]
        t.setStyle(TableStyle(style + (extra or [])))
        return t

    lg_img, (lw, lh) = logo_png()
    img = RLImage(str(lg_img), width=34 * mm, height=34 * mm * lh / lw)
    img.hAlign = 'LEFT'
    total_save_best = sum(s['save_best'] for s in summary)
    total_save_wish = sum(s['save_wish'] for s in summary)
    story = [img, Spacer(1, 3), Paragraph('Top-20 Bestseller', h1),
             Paragraph('Was in Deutschland und Europa aktuell am meisten verkauft wird · Marktpreise · Einkauf heute · Wunschpreise für die Verhandlung', sub), Spacer(1, 8)]
    pts = [
        '<b>Wie die Rangfolge entsteht:</b> Ich habe bei 5 deutschen und europäischen Online-Shops (alphasynth, smartpeptides, lumopeptides, cellpept, aestheticlabs) die Sortierung „Beliebtheit“ (meistverkauft) abgefragt und die ersten 25 Plätze je Shop mit Rangpunkten gewertet. Das ist ein Näherungswert für „Top Seller“, keine Umsatzzahl. Zubehör ist getrennt aufgeführt.',
        '<b>Die Spitze:</b> Retatrutide ist in allen 5 Shops unter den ersten 6, GHK-Cu und MOTS-c stehen ebenfalls in allen 5 Shops unter den ersten 25. Danach BPC-157, Semax, Tirzepatide, Tesamorelin. Semaglutide steht nur in 2 Shops weit vorn; „Semax“ liegt deutlich höher, falls du damit gemeint hast.',
        '<b>Bac. Water ist überall Platz 1 oder 2</b> (neben Spritzen und Tupfern) und wird von fast jedem Kunden mitgekauft. Bei uns kostet das Wasser 30 € (3 ml) und 40 € (10 ml) je 10 Stück, der Markt verlangt 79 bis 110 €. Hier lohnt ein günstiger Ting-Einkauf besonders, weil es jede Bestellung begleitet.',
        f'<b>Spielraum beim Einkauf:</b> Würde Ting bei diesen 20 Wirkstoffen auf den besten bekannten Preis (der günstigere von Ting und der anderen Lieferantin) gehen, spart das {eur(total_save_best)} je kompletter Bestellung aller Dosen. Mit dem Wunschpreis (60 % Marge bei Marktpreis) wären es {eur(total_save_wish)}.',
    ]
    for p_ in pts:
        story.append(Paragraph('•&nbsp;&nbsp;' + p_, ParagraphStyle('bl', parent=body, leftIndent=10, firstLineIndent=-10)))
    story.append(Spacer(1, 4))
    heads = ['#', 'Wirkstoff', 'Shops in\nTop 25', 'Beste\nPlatzierung', 'Dosen\nbei Ting', 'Einkauf Ting\n(alle Dosen)', 'Marge\nheute', 'Ersparnis bei\nBestpreis', 'Ersparnis bei\nWunschpreis']
    data = [[Paragraph(h.replace('\n', '<br/>'), hdl if i < 2 else hd) for i, h in enumerate(heads)]]
    for s in summary:
        data.append([Paragraph(str(s['rank']), cell), Paragraph(f"<b>{s['sub']}</b>", cell), Paragraph(f"{s['shops']} von 5", rt), Paragraph(f"Platz {s['best_pos']}", rt), Paragraph(str(s['rows']), rt), Paragraph(eur(s['cost']), rt),
                     Paragraph(f"{s['margin']:.0%}" if s['margin'] is not None else '–', rt), Paragraph(eur(s['save_best']) if s['save_best'] > 0 else '–', rt), Paragraph(f"<b>{eur(s['save_wish'])}</b>" if s['save_wish'] > 0 else '–', rt)])
    story.append(tbl(data, [10 * mm, W - 2 * m - 190 * mm, 22 * mm, 24 * mm, 20 * mm, 30 * mm, 20 * mm, 30 * mm, 34 * mm], pad=1.5))
    story.append(PageBreak())
    story.append(Paragraph('Preise je Wirkstoff (10er-Packung Vial)', h2))
    story.append(Paragraph('<b>Ting heute</b> = sichtbarer Listenpreis. <b>Andere Lief.</b> = günstigster Preis der anderen Lieferantin. <b>Markt</b> = 10-Vial-Kits bei peptidehaus (hoch) und qsc-eu (niedrig). <b>Wunsch</b> = Einkaufspreis, bei dem wir beim Marktpreis 60 % Marge hätten, nie höher als der beste bekannte Preis. Bei Zeilen ohne Marktpreis ist der Wunsch der beste bekannte Preis.', body))
    cw = [W - 2 * m - 210 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm, 24 * mm, 24 * mm, 30 * mm]
    heads2 = ['Wirkstoff', 'Dosis', 'Ting\nheute', 'Andere\nLief.', 'Markt\nniedrig', 'Markt\nhoch', 'Unser\nVerkauf', 'Marge\nheute', 'Wunsch\nEinkauf', 'Senkung\nggü. Ting']
    for s in summary:
        rs = [r for r in names_by_sub[s['sub']] if r.get('ting') is not None]
        if not rs:
            continue
        data = [[Paragraph(h.replace('\n', '<br/>'), hdl if i < 2 else hd) for i, h in enumerate(heads2)]]
        for r in rs:
            lo = min(r['src'].values()) if r.get('src') else None
            hi = max(r['src'].values()) if r.get('src') and len(r['src']) > 1 else None
            cut = (r['ting'] - r['wish']) / r['ting']
            data.append([Paragraph(f"#{s['rank']} {r['name']}", cell), Paragraph(r['strength'], cell), Paragraph(eur(r['ting']), rt), Paragraph(eur(r.get('other')), rt), Paragraph(eur(lo), rt), Paragraph(eur(hi), rt),
                         Paragraph(f"<b>{eur(r['rec'])}</b>", rt), Paragraph(f"{1 - r['ting'] / r['rec']:.0%}", rt), Paragraph(f"<b>{eur(r['wish'])}</b>", rt),
                         Paragraph(f'−{cut:.0%}' if cut > 0.005 else '–', rt)])
        story.append(KeepTogether([tbl(data, cw), Spacer(1, 7)]))
    nots = [t for t in ts.ranking() if not ts.catalog_rows(t[0]) and t[0] not in ('HGH',)][:5]
    story.append(Paragraph('Hinweise', h2))
    story.append(Paragraph('Die Wunschpreise sind Verhandlungsziele, keine Zusagen. Bei Ting zählt zuerst der Abgleich mit den Preisen der anderen Lieferantin (Spalte „Andere Lief.“); der zweite, niedrigere Wert im Ting-PDF ist unbestätigt und nicht eingerechnet. Doppelkammern: Ting-Einkauf liegt dort bereits bei etwa einem Viertel des Verkaufspreises (Marge 74 %), deshalb steht dort kein Wunschpreis.', body))
    doc.build(story)
    print('geschrieben', OUT)
    for s in summary:
        print(s['rank'], s['sub'], s['rows'], f"Marge {s['margin']:.0%}" if s['margin'] else '', 'Ersparnis best', round(s['save_best']), 'wish', round(s['save_wish']))
    print('Summe best', round(total_save_best), 'wish', round(total_save_wish))


if __name__ == '__main__':
    main()
