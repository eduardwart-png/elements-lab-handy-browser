"""Kunden-Preisliste (PDF) fuer den Bot-Befehl /preisliste: Verkaufspreise je Vial und Doppelkammer (inklusive Pen) als Einzelpreis, 10er-Pack und Preis je Stueck.
Keine Einkaufs-, Lieferanten- oder Marktdaten.
Quelle: miniapp/tools/catalog_lines.lines() (identisch mit den Packpreisen im Shop), miniapp/data/products.json und shop-formats.json (Einzelpreise) und miniapp/data/terms.json (Konditionen).
Ausgabe: miniapp/data/preisliste.pdf
"""
import datetime
import json
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus import Image as RLImage
from reportlab.platypus import KeepTogether

HERE = Path(__file__).resolve().parent
MINI = HERE.parent / 'miniapp'
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(MINI / 'tools'))
sys.path.insert(0, str(MINI))
import catalog_lines as cl  # noqa: E402
from render_lists import logo_png  # noqa: E402
from terms import text_vars  # noqa: E402

OUT = MINI / 'data' / 'preisliste.pdf'
INK, MUTED, PET, PET2, SOFT, LINE = colors.HexColor('#172027'), colors.HexColor('#66717B'), colors.HexColor('#0D5B6B'), colors.HexColor('#2F7B8A'), colors.HexColor('#EEF4F5'), colors.HexColor('#D9DEE2')


def eur(cents):
    """130 € / 84,90 €: ganze Euro ohne Nachkommastellen, sonst mit Komma."""
    text = f'{cents // 100:,}'.replace(',', '.')
    return text + (f',{cents % 100:02d}' if cents % 100 else '') + ' €'


def each(cents, size=10):
    """Preis je Stueck mit zwei Nachkommastellen, wenn der Packpreis nicht durch die Stueckzahl teilbar ist (z. B. 155 € / 10 = 15,50 €)."""
    return eur(cents // size) if cents % size == 0 else eur(round(cents / size))


def single_prices():
    """(Abschnitt, Linienname, Staerke, Ausfuehrung) -> Einzelpreis in Cent. Nur Artikel mit eigener Produktseite (Vial und Doppelkammer) haben einen."""
    data = MINI / 'data'
    products = {p['id']: p['price_cents'] for p in json.loads((data / 'products.json').read_text())}
    formats = json.loads((data / 'shop-formats.json').read_text())
    duals = {p['base_product_id']: p['price_cents'] for p in formats if p.get('format') == 'dual_chamber'}
    out = {}
    for p in formats:
        if p.get('format') not in ('vial_pack', 'dual_pack') or not p.get('base_product_id'):
            continue
        key = (p['section'], p['line_name'], p['line_strength'], 'vial' if p['format'] == 'vial_pack' else 'dual')
        base = p['base_product_id']
        cents = products.get(base) if key[3] == 'vial' else duals.get(base)
        if cents:
            out[key] = cents
    return out


def main():
    terms = json.loads((MINI / 'data/terms.json').read_text())
    v = text_vars(terms)
    singles = single_prices()
    rows = {}
    for x in cl.lines():
        r = rows.setdefault((x['section'], x['name'], x['strength']), {'order': x['order']})
        r[x['form']] = x['price_cents']
        r['ok_' + x['form']] = bool(x.get('discount_ok'))
    for it in json.loads((MINI / 'data/shop-formats.json').read_text()):  # Shop-Pack ohne eigene Blattzeile (Doppelkammer BPC-157+TB-500)
        if it.get('format') in ('vial_pack', 'dual_pack') and not it.get('code') and it.get('line_name'):
            rows.setdefault((it['section'], it['line_name'], it['line_strength']), {'order': it['order']})['vial' if it['format'] == 'vial_pack' else 'dual'] = it['price_cents']
    sections = [s for s in cl.SECTIONS if any(k[0] == s for k in rows)]
    today = datetime.date.today().strftime('%d.%m.%Y')
    W, H = A4
    m = 14 * mm
    doc = BaseDocTemplate(str(OUT), pagesize=A4, leftMargin=m, rightMargin=m, topMargin=14 * mm, bottomMargin=16 * mm, title='Elements Labs · Preisliste', author='Elements Labs')

    def foot(c, d):
        c.saveState()
        c.setStrokeColor(LINE); c.line(m, 11 * mm, W - m, 11 * mm)
        c.setFont('Helvetica', 8); c.setFillColor(MUTED)
        c.drawString(m, 7 * mm, f'Elements Labs · Preisliste · Stand {today} · Preise in Euro · 10er-Pack = 10 Stück, je Stück = Packpreis geteilt durch 10')
        c.drawRightString(W - m, 7 * mm, f'Seite {d.page}')
        c.restoreState()

    doc.addPageTemplates([PageTemplate(id='p', frames=[Frame(m, 16 * mm, W - 2 * m, H - 30 * mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=foot)])
    h1 = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=22, leading=26, textColor=INK)
    sub = ParagraphStyle('sub', fontName='Helvetica', fontSize=10, leading=14, textColor=MUTED)
    cell = ParagraphStyle('c', fontName='Helvetica', fontSize=8.5, leading=10.5, textColor=INK)
    bold = ParagraphStyle('cb', parent=cell, fontName='Helvetica-Bold')
    right = ParagraphStyle('r', parent=cell, alignment=2)
    rbold = ParagraphStyle('rb', parent=right, fontName='Helvetica-Bold')
    rmuted = ParagraphStyle('rm', parent=right, textColor=MUTED)
    cwhite = ParagraphStyle('cw', parent=bold, textColor=colors.white, alignment=1)
    white = ParagraphStyle('w', parent=bold, textColor=colors.white)
    logo, (lw, lh) = logo_png()
    img = RLImage(str(logo), width=46 * mm, height=46 * mm * lh / lw)
    img.hAlign = 'LEFT'
    story = [img, Spacer(1, 6), Paragraph('Preisliste · Einzelartikel und 10er-Packs', h1),
             Paragraph(f'Vial und Doppelkammer inklusive Pen · Stand {today} · Lieferzeit {v["wk"]} Wochen', sub), Spacer(1, 8)]
    box = Table([[Paragraph('<b>Konditionen</b>', cell)], [Paragraph(
        f"Mindestbestellwert {v['min']} · <b>Versand inklusive</b> · Lieferzeit {v['wk']} Wochen<br/>"
        f"Mengenrabatt auf 10er-Packs: {v['tiers']} (im Warenkorb automatisch; ausgenommen Packs mit *)<br/>"
        f"Sammelbestellung von {v['cmin']} bis unter {v['min']}: versandkostenfrei, gebündelte Lieferung.", cell)]], colWidths=[W - 2 * m])
    box.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), SOFT), ('LEFTPADDING', (0, 0), (-1, -1), 10), ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]))
    story += [box, Spacer(1, 10)]
    cw = [0, 24 * mm] + [15 * mm, 18 * mm, 15 * mm] * 2
    cw[0] = W - 2 * m - sum(cw[1:])
    star = '<font color="#66717B"> *</font>'

    def cells(r, key, form):
        pack = r.get(form)
        if pack is None:
            return [Paragraph('–', rmuted)] * 3
        single = singles.get((key[0], key[1], key[2], form))
        return [Paragraph(eur(single) if single else '–', right if single else rmuted),
                Paragraph(eur(pack) + ('' if r.get('ok_' + form, True) else star), rbold),
                Paragraph(each(pack), right)]

    for sec in sections:
        keys = sorted([k for k in rows if k[0] == sec], key=lambda k: rows[k]['order'])
        data = [[Paragraph(sec, white)] + [''] * 7,
                [Paragraph('Produkt', bold), Paragraph('Dosierung', bold), Paragraph('Vial', cwhite), '', '', Paragraph('Doppelkammer · inklusive Pen', cwhite), '', ''],
                ['', '', Paragraph('Einzel', rbold), Paragraph('10er-Pack', rbold), Paragraph('je Stück', rbold), Paragraph('Einzel', rbold), Paragraph('10er-Pack', rbold), Paragraph('je Stück', rbold)]]
        for k in keys:
            r = rows[k]
            data.append([Paragraph(k[1], cell), Paragraph(k[2], cell)] + cells(r, k, 'vial') + cells(r, k, 'dual'))
        t = Table(data, colWidths=cw, repeatRows=3)
        t.setStyle(TableStyle([('SPAN', (0, 0), (-1, 0)), ('BACKGROUND', (0, 0), (-1, 0), PET), ('SPAN', (0, 1), (0, 2)), ('SPAN', (1, 1), (1, 2)), ('SPAN', (2, 1), (4, 1)), ('SPAN', (5, 1), (7, 1)),
                               ('BACKGROUND', (2, 1), (4, 1), PET), ('BACKGROUND', (5, 1), (7, 1), PET2), ('BACKGROUND', (0, 1), (1, 2), SOFT), ('BACKGROUND', (2, 2), (-1, 2), SOFT),
                               ('LINEBELOW', (0, 2), (-1, 2), 0.8, PET), ('LINEBELOW', (0, 3), (-1, -1), 0.25, LINE), ('LINEBEFORE', (2, 1), (2, -1), 0.5, LINE), ('LINEBEFORE', (5, 1), (5, -1), 0.5, LINE),
                               ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 2.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5), ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4)]))
        story += [t, Spacer(1, 8)]
    story.append(KeepTogether([Paragraph('* ohne Mengenrabatt. Einzelpreis nur für Artikel mit eigener Produktseite im Shop, sonst –. Jede Doppelkammer inklusive Pen. '
                                         'Bestellung direkt im Shop (Telegram-Bot) oder auf Anfrage. Preise freibleibend, Stand siehe Fußzeile.', sub)]))
    doc.build(story)
    if '--xlsx' in sys.argv:
        write_xlsx(Path(sys.argv[sys.argv.index('--xlsx') + 1]), sections, rows, singles, today)
    print('geschrieben', OUT, len(rows), 'Zeilen,', len(singles), 'Einzelpreise')


def write_xlsx(path, sections, rows, singles, today):
    """Dieselben Zeilen wie die PDF als Tabelle (LibreOffice-tauglich, Preise als Zahlen in Euro, keine Einkaufs-/Lieferantendaten)."""
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Preisliste'
    ws.append([f'Elements Labs · Preisliste · Einzelartikel und 10er-Packs · Stand {today} · Preise in Euro'])
    ws.append(['Vial und Doppelkammer inklusive Pen · 10er-Pack = 10 Stück · je Stück = Packpreis geteilt durch 10 · * = ohne Mengenrabatt'])
    ws.append([])
    head = ['Bereich', 'Produkt', 'Dosierung', 'Vial Einzel', 'Vial 10er-Pack', 'Vial je Stück', 'Doppelkammer (inkl. Pen) Einzel',
            'Doppelkammer (inkl. Pen) 10er-Pack', 'Doppelkammer (inkl. Pen) je Stück', 'ohne Mengenrabatt']
    ws.append(head)
    for c in ws[4]:
        c.font = Font(bold=True, color='FFFFFF'); c.fill = PatternFill('solid', fgColor='0D5B6B'); c.alignment = Alignment(wrap_text=True, vertical='center')
    ws['A1'].font = Font(bold=True, size=13)
    for sec in sections:
        for k in sorted([k for k in rows if k[0] == sec], key=lambda k: rows[k]['order']):
            r, line, nostar = rows[k], [sec, k[1], k[2]], []
            for form in ('vial', 'dual'):
                pack, single = r.get(form), singles.get((k[0], k[1], k[2], form))
                line += [single / 100 if single else None, pack / 100 if pack is not None else None, round(pack / 1000, 2) if pack is not None else None]
                if pack is not None and not r.get('ok_' + form, True):
                    nostar.append('Vial' if form == 'vial' else 'Doppelkammer')
            ws.append(line + [', '.join(nostar)])
    for col, w in zip('ABCDEFGHIJ', (34, 34, 14, 11, 13, 11, 14, 16, 14, 18)):
        ws.column_dimensions[col].width = w
    for row in ws.iter_rows(min_row=5, min_col=4, max_col=9):
        for c in row:
            c.number_format = '#,##0.00 €'
    ws.freeze_panes = 'D5'
    wb.properties.title, wb.properties.creator = 'Elements Labs · Preisliste', 'Elements Labs'
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


if __name__ == '__main__':
    main()
