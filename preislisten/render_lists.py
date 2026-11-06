"""Render the clean customer-facing 'Aktuelle Elements Labs Liste' (PDF + XLSX, logo, no supplier data)
and the internal comparison workbook (stays in the project folder)."""
import json
from datetime import date
from pathlib import Path

import openpyxl
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak
from reportlab.platypus import Image as RLImage

HERE = Path(__file__).resolve().parent
DESK = Path.home() / 'Desktop'
PETROL = colors.HexColor('#0D5B6B')
INK = colors.HexColor('#172027')
MUTED = colors.HexColor('#66717B')
SOFT = colors.HexColor('#EEF2F3')
LINE = colors.HexColor('#E1E5E7')
ORDER = ['Gewichtsmanagement & Fettreduktion', 'Regeneration & Reparatur', 'Beauty & Anti-Aging', 'Schlaf & Nervensystem',
         'Hormone & Wachstum', 'Immunsystem & Organregulation', 'Kombinationssets', 'Zubehör', 'Weitere Produkte']
STAND = date(2026, 10, 23).strftime('%d.%m.%Y')
TITLE = 'Aktuelle Elements Labs Liste'


def eur(v):
    return f'{v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.') + ' €'


def logo_png():
    src = HERE / 'el-primary-light.png'
    out = HERE / 'el-logo-trimmed.png'
    im = Image.open(src).convert('RGBA')
    box = im.getchannel('A').getbbox()
    im = im.crop(box)
    pad = 24
    canvas = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (255, 255, 255, 0))
    canvas.paste(im, (pad, pad))
    canvas.save(out)
    return out, canvas.size


def grouped(rows):
    idx = {s: i for i, s in enumerate(ORDER)}
    return sorted(rows, key=lambda r: idx[r['section']])  # stable: keeps source order inside a section


def customer_rows(data):
    vials = [dict(section=v['section'], name=v['name'], dose=v['dose'], price=v['best_eur'], price2=round(v['best_eur'] / 10, 2)) for v in data['vials']]
    dual = [dict(section=d['section'], name=d['name'], dose=d['dose'], price=d['dual_eur']) for d in data['dual']]
    single = [dict(section=d['section'], name=d['name'], dose=d['dose'], price=round(d['single_usd'] / data['rate'], 2)) for d in data['dual'] if d.get('single_usd')]
    return grouped(vials), grouped(dual), grouped(single)


# ------------------------------------------------------------------ PDF
def build_pdf(vials, dual, single, path):
    logo, (lw, lh) = logo_png()
    W, H = A4
    left = right = 16 * mm
    doc = BaseDocTemplate(str(path), pagesize=A4, leftMargin=left, rightMargin=right, topMargin=16 * mm, bottomMargin=18 * mm,
                          title=TITLE, author='Elements Labs', subject='Preisliste', creator='Elements Labs')

    def footer(canvas, d):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.line(left, 13 * mm, W - right, 13 * mm)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(left, 8.5 * mm, f'{TITLE} · Stand {STAND} · Alle Preise in Euro, Änderungen vorbehalten')
        canvas.drawRightString(W - right, 8.5 * mm, f'Seite {d.page}')
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id='p', frames=[Frame(left, 18 * mm, W - left - right, H - 34 * mm, id='f', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=footer)])
    h1 = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=22, leading=26, textColor=INK, spaceAfter=2)
    sub = ParagraphStyle('sub', fontName='Helvetica', fontSize=10, leading=14, textColor=MUTED, spaceAfter=10)
    h2 = ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=14, leading=18, textColor=PETROL, spaceBefore=6, spaceAfter=4)
    cell = ParagraphStyle('c', fontName='Helvetica', fontSize=9.2, leading=11.5, textColor=INK)
    cellb = ParagraphStyle('cb', parent=cell, fontName='Helvetica-Bold')
    cw3 = [W - left - right - 62 * mm, 28 * mm, 34 * mm]
    cw4 = [W - left - right - 90 * mm, 26 * mm, 34 * mm, 30 * mm]
    story = []
    lw_mm = 62 * mm
    img = RLImage(str(logo), width=lw_mm, height=lw_mm * lh / lw)
    img.hAlign = 'LEFT'
    story.append(img)
    story.append(Spacer(1, 8))
    story.append(Paragraph(TITLE, h1))
    story.append(Paragraph(f'Stand {STAND} · Preise in Euro', sub))

    def section_tables(rows, price_head, price2_head=None):
        out, cur, bucket = [], None, []
        for r in rows + [None]:
            if r is None or r['section'] != cur:
                if bucket:
                    out.append(one_table(cur, bucket, price_head, price2_head))
                if r is None:
                    break
                cur, bucket = r['section'], []
            bucket.append(r)
        return out

    def one_table(section, rows, price_head, price2_head=None):
        n = 4 if price2_head else 3
        cw = cw4 if price2_head else cw3
        ph = ParagraphStyle('ph', parent=cellb, alignment=2)
        band = [Paragraph(section, ParagraphStyle('s', parent=cellb, textColor=colors.white))] + [''] * (n - 1)
        head = [Paragraph('Produkt', cellb), Paragraph('Dosierung', cellb), Paragraph(price_head, ph)] + ([Paragraph(price2_head, ph)] if price2_head else [])
        data = [band, head]
        styles = [('SPAN', (0, 0), (-1, 0)), ('BACKGROUND', (0, 0), (-1, 0), PETROL), ('BACKGROUND', (0, 1), (-1, 1), SOFT),
                  ('LINEBELOW', (0, 1), (-1, 1), 0.8, PETROL), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                  ('TOPPADDING', (0, 0), (-1, -1), 3.2), ('BOTTOMPADDING', (0, 0), (-1, -1), 3.2),
                  ('TOPPADDING', (0, 0), (-1, 0), 4.5), ('BOTTOMPADDING', (0, 0), (-1, 0), 4.5)]
        for r in rows:
            line = [Paragraph(r['name'], cell), Paragraph(r['dose'], cell), Paragraph(f"<b>{eur(r['price'])}</b>", ParagraphStyle('pr', parent=cell, alignment=2))]
            if price2_head:
                line.append(Paragraph(eur(r['price2']), ParagraphStyle('pr2', parent=cell, alignment=2, textColor=MUTED)))
            data.append(line)
            styles.append(('LINEBELOW', (0, len(data) - 1), (-1, len(data) - 1), 0.25, LINE))
        t = Table(data, colWidths=cw, repeatRows=2)
        t.setStyle(TableStyle(styles))
        return [t, Spacer(1, 9)]

    story.append(Paragraph('Teil 1 · Vials', h2))
    story.append(Paragraph('Preis je Packung mit 10 Vials; rechts der rechnerische Preis je einzelnem Vial.', sub))
    for blk in section_tables(vials, 'Preis je 10 Vials', 'Preis je Vial'):
        story.extend(blk)
    story.append(PageBreak())
    story.append(Paragraph('Teil 2 · Doppelkammer', h2))
    story.append(Paragraph('Preis je Doppelkammer-Kartusche.', sub))
    for blk in section_tables(dual, 'Preis je Kartusche'):
        story.extend(blk)
    story.append(PageBreak())
    story.append(Paragraph('Teil 3 · Einzelkammer', h2))
    story.append(Paragraph('Preis je Einzelkammer-Kartusche.', sub))
    for blk in section_tables(single, 'Preis je Kartusche'):
        story.extend(blk)
    doc.build(story)


# ------------------------------------------------------------------ XLSX
def build_xlsx(vials, dual, single, path):
    logo, (lw, lh) = logo_png()
    wb = openpyxl.Workbook()
    petrol, ink = '0D5B6B', '172027'
    thin = Side(style='thin', color='E1E5E7')

    def sheet(ws, title, rows, price_head, note, price2_head=None):
        ws.sheet_view.showGridLines = False
        img = XLImage(str(logo))
        img.width, img.height = 230, int(230 * lh / lw)
        ws.add_image(img, 'A1')
        for r in range(1, 4):
            ws.row_dimensions[r].height = 22
        ws['A4'] = TITLE
        ws['A4'].font = Font(name='Helvetica', size=18, bold=True, color=ink)
        ws['A5'] = f'{title} · Stand {STAND} · Preise in Euro · {note}'
        ws['A5'].font = Font(name='Helvetica', size=10, color='66717B')
        ws.row_dimensions[4].height = 28
        head_row = 7
        for c, h in enumerate(['Produkt', 'Dosierung', price_head] + ([price2_head] if price2_head else []), 1):
            x = ws.cell(head_row, c, h)
            x.font = Font(name='Helvetica', bold=True, color='FFFFFF')
            x.fill = PatternFill('solid', fgColor=petrol)
            x.alignment = Alignment(horizontal='right' if c >= 3 else 'left', vertical='center')
        ws.row_dimensions[head_row].height = 22
        r, cur = head_row + 1, None
        for row in rows:
            if row['section'] != cur:
                cur = row['section']
                ws.cell(r, 1, cur).font = Font(name='Helvetica', bold=True, color=petrol)
                for c in range(1, 4 + (1 if price2_head else 0)):
                    ws.cell(r, c).fill = PatternFill('solid', fgColor='EEF2F3')
                ws.row_dimensions[r].height = 20
                r += 1
            ws.cell(r, 1, row['name']).font = Font(name='Helvetica', color=ink)
            ws.cell(r, 2, row['dose']).font = Font(name='Helvetica', color=ink)
            p = ws.cell(r, 3, row['price'])
            p.number_format = '#,##0.00 "€"'
            p.font = Font(name='Helvetica', bold=True, color=ink)
            p.alignment = Alignment(horizontal='right')
            if price2_head:
                q = ws.cell(r, 4, row['price2'])
                q.number_format = '#,##0.00 "€"'
                q.font = Font(name='Helvetica', color='66717B')
                q.alignment = Alignment(horizontal='right')
            for c in range(1, 4 + (1 if price2_head else 0)):
                ws.cell(r, c).border = Border(bottom=thin)
            r += 1
        ws.column_dimensions['A'].width = 58
        ws.column_dimensions['B'].width = 16
        ws.column_dimensions['C'].width = 22
        ws.column_dimensions['D'].width = 18
        ws.freeze_panes = ws.cell(head_row + 1, 1)
        ws.page_setup.orientation = 'portrait'
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_title_rows = f'{head_row}:{head_row}'
        ws.oddFooter.center.text = f'Elements Labs · {TITLE} · Stand {STAND}'

    ws = wb.active
    ws.title = 'Vials (10er Packung)'
    sheet(ws, 'Vials', vials, 'Preis je 10 Vials', 'je Packung mit 10 Vials', 'Preis je Vial')
    sheet(wb.create_sheet('Doppelkammer'), 'Doppelkammer', dual, 'Preis je Kartusche', 'je Doppelkammer-Kartusche')
    sheet(wb.create_sheet('Einzelkammer'), 'Einzelkammer', single, 'Preis je Kartusche', 'je Einzelkammer-Kartusche')
    wb.properties.creator = 'Elements Labs'
    wb.properties.title = TITLE
    wb.save(path)


# ------------------------------------------------------------------ internal audit
def build_audit(data, path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Vials Vergleich'
    ws.append(['Abschnitt', 'Produkt', 'Dosierung', 'Wholesale EUR', 'EUR-Preisliste', 'Ting USD', 'Ting in EUR', 'BESTER PREIS EUR', 'Quelle des besten Preises', 'Hinweis'])
    for v in grouped(data['vials']):
        hint = 'Duplikat in Quelle zusammengefasst' if v.get('dups') else ''
        ws.append([v['section'], v['name'], v['dose'], v['wholesale_eur'], v['list_eur'], v['ting_usd'], v['ting_eur'], v['best_eur'], v['best_source'], hint])
    ws2 = wb.create_sheet('Doppelkammer')
    ws2.append(['Abschnitt', 'Produkt', 'Dosierung', 'Ting Dual USD', 'Dual in EUR', 'Ting Single USD (nicht verwendet)', 'Quellcode', 'Hinweis'])
    for d in grouped(data['dual']):
        ws2.append([d['section'], d['name'], d['dose'], d['dual_usd'], d['dual_eur'], d['single_usd'], d['code'], d['flag']])
    ws3 = wb.create_sheet('Nicht übernommen')
    ws3.append(['Liste', 'Code', 'Angabe', 'Preis USD', 'Grund'])
    for h in data['held']:
        ws3.append([h['quelle'], h['code'], h['spec'], h['usd'], h['grund']])
    for d in data['dual_held']:
        ws3.append(['Ting_Pens', d['code'], f"{d['name']} {d['spec']}", d['dual_usd'], d['flag']])
    ws5 = wb.create_sheet('Auffälligkeiten')
    ws5.append(['Liste', 'Produkt', 'kleinere Dosis', 'Preis', 'größere Dosis', 'Preis', 'Beobachtung'])
    for liste, rows, key in (('Vials', data['vials'], 'best_eur'), ('Doppelkammer', data['dual'], 'dual_eur')):
        byp = {}
        for r in rows:
            byp.setdefault((r['name'], r['unit']), []).append(r)
        for (name, unit), rs in byp.items():
            rs.sort(key=lambda r: r['num'])
            for lo, hi in zip(rs, rs[1:]):
                if lo[key] > hi[key] + 1e-9:
                    ws5.append([liste, name, lo['dose'], lo[key], hi['dose'], hi[key], 'kleinere Dosis teurer als größere (bester Preis stammt aus unterschiedlichen Listen oder Quellfehler)'])
    ws4 = wb.create_sheet('Regeln')
    for line in [
        ['Wechselkurs', f"1 EUR = {data['rate']} USD (EZB-Referenzkurs {data['rate_date']}); EUR = USD / Kurs, 2 Nachkommastellen"],
        ['Bester Preis', 'niedrigster Preis je Produkt und Dosierung über alle Listen (EUR-Listen direkt, USD-Liste umgerechnet)'],
        ['Aufschlag', 'keiner angewendet - die Elements-Labs-Liste zeigt die besten Einkaufspreise unverändert'],
        ['Doppelkammer', 'nur die Dual-Chamber-Spalte; Single-Chamber wird nicht verwendet; eine weitere Doppelkammer-Liste lag nicht vor'],
        ['Quellen', 'Wholesale EUR price.xlsx, EUR PRICE.xlsx, Ting_Vials.pdf, Ting_Pens.pdf (Desktop)'],
    ]:
        ws4.append(line)
    for sh in wb.worksheets:
        for c in sh[1]:
            c.font = Font(bold=True)
        for col in sh.columns:
            sh.column_dimensions[col[0].column_letter].width = min(60, max(len(str(c.value or '')) for c in col) + 2)
    wb.save(path)


if __name__ == '__main__':
    data = json.loads((HERE / 'merged.json').read_text())
    vials, dual, single = customer_rows(data)
    build_pdf(vials, dual, single, HERE / 'Aktuelle Elements Labs Liste.pdf')
    build_xlsx(vials, dual, single, HERE / 'Aktuelle Elements Labs Liste.xlsx')
    build_audit(data, HERE / 'INTERN_Preisvergleich_mit_Quellen.xlsx')
    print('rows', len(vials), len(dual), len(single))
