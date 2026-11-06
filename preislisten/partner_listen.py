#!/usr/bin/env python3
"""Partner-Preislisten (Vials + Cartridges) im Elements-Labs-Design aus den beiden Lieferantenlisten (intern, Eddy 25.10.2026).

Eingabe : ~/Desktop/Ting_Vials Kopie.pdf, ~/Desktop/Ting_Pens Kopie.pdf (nur lesen; sichtbare Preise, Pruefung per OCR siehe pruefe_partnerlisten.py)
Ausgabe : ~/Desktop/Elements_Lab/4 FÜR KOOPERATIONSPARTNER/*.pdf  (neu gerendert, keine Spur der Quelle: kein Name, keine Kontakte, keine Codes,
          keine versteckten Ebenen, keine Metadaten) und intern _DATA/.../partnerlisten/zuordnung.csv (Quellcode -> Anzeige, alter/neuer Preis)
Preise  : sichtbarer Quellpreis x 1,15, kaufmaennisch auf Cent (USD wie in der Quelle).

  partner_listen.py            baut Daten + PDFs
  partner_listen.py --daten    nur Daten (JSON/CSV)
"""
import csv
import json
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
HOME = Path.home()
QUELLE = HERE / 'quellen_extrahiert'
OUT_DIR = HOME / 'Desktop/Elements_Lab/4 FÜR KOOPERATIONSPARTNER'
INTERN = HOME / 'Projekte-Mac/_DATA/ELEMENTS_STRATEGIE_20261024/partnerlisten'
SRC_VIALS = HOME / 'Desktop/Ting_Vials Kopie.pdf'
SRC_PENS = HOME / 'Desktop/Ting_Pens Kopie.pdf'
FAKTOR = Decimal('1.15')
STAND = '25.10.2026'
STAND_EN = '25 Oct 2026'

# ---------------------------------------------------------------- Namen (Quelle -> Anzeige; offensichtliche Tippfehler der Quelle bereinigt)
VIAL_NAMES = {
    'Semaglutide': 'Semaglutide', 'Tirzepatide': 'Tirzepatide', 'Retatrutide': 'Retatrutide', 'Mazdutide': 'Mazdutide', 'Liraglutide': 'Liraglutide',
    'Cagrilintide': 'Cagrilintide', 'AOD9605': 'AOD9604', 'HGH -191AA(Somatropin);': 'HGH 191AA (Somatropin)', 'Adipotide/FTTP': 'Adipotide / FTTP',
    'L-carnitine': 'L-Carnitine', 'Lemon Bottle': 'Lemon Bottle', 'Lipo-c': 'Lipo-C', 'MOTS-C': 'MOTS-c', 'SLU-PP-322': 'SLU-PP-332',
    'Cagrisema (2.5mg+2.5mg)': 'CagriSema (2.5 mg + 2.5 mg)', '5-Amino-1mq': '5-Amino-1MQ', 'Tesamorelin': 'Tesamorelin', 'BPC157': 'BPC-157', 'TB500': 'TB-500',
    'GHK-Cu': 'GHK-Cu', 'Sermorelin Acetate': 'Sermorelin Acetate', 'IGF-1 LR3': 'IGF-1 LR3', 'Epithalon': 'Epithalon', 'NP810/SNAP8': 'Snap-8',
    'SS-31': 'SS-31', 'GT/GTT/Glutathione': 'Glutathione', 'NAD': 'NAD+', 'DSIP': 'DSIP', 'Selank': 'Selank', 'Semax': 'Semax', 'Dihexa': 'Dihexa',
    'Oxytocin Acetate': 'Oxytocin Acetate', 'G25': 'GHRP-2 Acetate', 'G65': 'GHRP-6 Acetate', 'Ipamorelin': 'Ipamorelin', 'CJC 1295 with DAC': 'CJC-1295 (With DAC)',
    'CJC 1295(without DAC)': 'CJC-1295 (Without DAC)', 'Kisspetin-10': 'Kisspeptin-10', 'HCG': 'HCG', 'HG75/HMG': 'HMG', 'FRAG': 'HGH Fragment 176-191',
    'Thymalin': 'Thymalin', 'Thymosin alpha 1': 'Thymosin Alpha-1', 'LL375': 'LL-37', 'Hexarelin Acetate': 'Hexarelin Acetate', 'KPV': 'KPV', 'VIP5': 'VIP', 'VIP10': 'VIP',
    'ARA290': 'ARA-290', 'E3K': 'EPO', 'AHK-CU': 'AHK-Cu', 'P41/PT141': 'PT-141', 'Melanotan I': 'Melanotan I', 'Melanotan II': 'Melanotan II', 'Aicar': 'AICAR',
    'F410': 'FOXO4-DRI', 'BPC5mg + TB5mg': 'BPC-157 + TB-500', 'GLOW (TB10+BP10+GHK50)': 'GLOW (BPC-157 + GHK-Cu + TB-500)',
    'KLOW (TB10+BPC10+GHK50+KPV10)': 'KLOW (BPC-157 + TB-500 + GHK-Cu + KPV)', 'ACE 031': 'ACE-031', 'CP10': 'CJC-1295 (Without DAC) + Ipamorelin',
    'Survodutide': 'Survodutide', 'FMP2': 'FMP2', 'B-12/B12': 'B-12', 'Bac. Water (Bacteriostatic Water)': 'Bacteriostatic Water',
    'WA (Bacteriostatic Water)': 'Bacteriostatic Water',
}
# Zeilen, deren Name/Spezifikation aus dem Code der Quelle stammt (Namenszelle fehlt oder ist mehrdeutig)
VIAL_ROW_OVERRIDES = {
    'LG5': ('Liraglutide', None), 'LG10': ('Liraglutide', None), 'LG30': ('Liraglutide', None),
    'LC216': ('Lipo-C 216', None), 'LC526': ('Lipo-C 526', None),
    'BB20': ('BPC-157 + TB-500 (10 mg + 10 mg)', None), 'BB10': ('BPC-157 + TB-500 (5 mg + 5 mg)', None),
    'CP10': ('CJC-1295 (Without DAC) + Ipamorelin', '5mg + 5mg'),
    'GLOW/BBG70': ('GLOW (BPC-157 + GHK-Cu + TB-500)', None), 'KLOW/BBKG80': ('KLOW (BPC-157 + TB-500 + GHK-Cu + KPV)', None),
    'EPO': ('EPO', None),
}
VIAL_SECTION_TITLE = {
    'WEIGHT LOSS & FAT REDUCTION': 'Weight Loss & Fat Reduction', 'REPAIR & RECOVERY': 'Repair & Recovery', 'BEAUTY & ANTI-AGING': 'Beauty & Anti-Aging',
    'SLEEP & NEUROLOGICAL SUPPORT': 'Sleep & Neurological Support', 'HORMONE & GROWTH': 'Hormone & Growth', 'ORGAN SUPPORT': 'Organ Support',
    'PEPTIDE BLENDS': 'Peptide Blends', 'SUPPLIES': 'Supplies',
}
PEN_NAMES = {
    'CJC-1295 (ohne DAC)': 'CJC-1295 (Without DAC)', 'CJC-1295 (mit DAC)': 'CJC-1295 (With DAC)', 'Oxytocin (Pharma-Qualität)': 'Oxytocin Acetate – Pharmaceutical Grade',
    'Oxytocin (Industriequalität)': 'Oxytocin Acetate – Industrial Grade', 'CJC-1295 (ohne DAC) + Ipamorelin (5 mg + 5 mg)': 'CJC-1295 (Without DAC) + Ipamorelin (5 mg + 5 mg)',
    'Gonadorelin': 'Gonadorelin Acetate', 'Thymalin': 'Thymalin', 'GHRP-2': 'GHRP-2 Acetate', 'GHRP-6': 'GHRP-6 Acetate', 'Sermorelin': 'Sermorelin Acetate',
    'Thymosin Alpha-1': 'Thymosin Alpha-1', 'TB-500 (Full-Length)': 'TB-500 (Full-Length)', 'GLOW (BPC-157 + GHK-Cu + TB-500)': 'GLOW (BPC-157 + GHK-Cu + TB-500)',
}
PEN_SECTIONS = [(402, 'Weight Management'), (1300, 'Repair & Recovery'), (1577, 'Peptide & Neuro Support'), (2628, 'Hormone & Growth Support'), (3279, 'Metabolic, Beauty & Blends')]
PEN_SECTION_MOVE = {'Melanotan I': 'Peptide & Neuro Support'}   # Abschnittsbalken der Quelle trennt Melanotan I und II: beide in denselben Abschnitt
PEN_SKIP = {('KLOW', '80mg', 17)}   # zweite, unklare KLOW-Zeile der Quelle (anderer Preis als die beschriebene KLOW-80-mg-Zeile)
PEN_SPEC_FIX = {}                    # Quelle gedruckte Angabe bleibt (LIR30 steht in der Quelle als 20 mg)


def money(usd):
    return (Decimal(usd) * FAKTOR).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def fmt_money(d):
    return '$' + f'{d:,.2f}'


def fmt_spec(s):
    s = re.sub(r'\s*\*\s*', ' × ', s.strip())
    s = re.sub(r'(\d)\s*(vials)', r'\1 \2', s)
    s = re.sub(r'(?i)(\d+(?:\.\d+)?)\s*(iu)\b', lambda m: f'{m.group(1)} IU', s)
    s = re.sub(r'(?i)(\d+(?:\.\d+)?)\s*(mg|ml)\b', lambda m: f'{m.group(1)} {m.group(2).lower()}', s)
    return re.sub(r'\s+', ' ', s)


# ---------------------------------------------------------------- Daten
def vial_rows():
    import pymupdf
    roh = json.load(open(QUELLE / 'ting_vials_roh.json'))
    pg = pymupdf.open(SRC_VIALS)[0]
    spans = [(s['bbox'][1], s['bbox'][0], s['text'].strip(), s['size']) for b in pg.get_text('dict')['blocks'] for l in b.get('lines', []) for s in l['spans'] if s['text'].strip()]
    bars = sorted((y, t) for y, x, t, sz in spans if round(sz, 1) == 17.0)
    cells = sorted({(round(x['rect'].y0), round(x['rect'].y1)) for x in pg.get_drawings() if 495 <= x['rect'].width <= 505 and 200 <= x['rect'].x0 <= 210 and x['rect'].height >= 30})
    rows = []
    for r in roh:
        yc = r['y']
        sec = [t for y, t in bars if y < yc][-1]
        cell = next(((a, b) for a, b in cells if a <= yc <= b), None)
        names = [t for y, x, t, sz in spans if cell and sz in (12.0, 24.0) and 200 <= x <= 705 and cell[0] + 2 <= y + 12 <= cell[1] - 2]
        src_name = ' '.join(names)
        spec = r['spec'] if r.get('spec') else None
        ov = VIAL_ROW_OVERRIDES.get(r['code'])
        if ov:
            name = ov[0]
            spec = ov[1] or spec
        else:
            key = src_name if src_name in VIAL_NAMES else next((n for n in names if n in VIAL_NAMES), None)
            if key is None:
                raise SystemExit(f'Vials: Name fuer {r["code"]} nicht zuordenbar: {names!r}')
            name = VIAL_NAMES[key]
        if spec is None:
            raise SystemExit(f'Vials: Spezifikation fehlt: {r["code"]}')
        usd = int(r['price'].lstrip('$'))
        spec_txt = fmt_spec(spec if '*' in spec else spec + '*10vials') if r['code'] != 'CP10' else '5 mg + 5 mg × 10 vials'
        rows.append(dict(section=VIAL_SECTION_TITLE[sec], name=name, spec=spec_txt, usd=usd, new=money(usd), src_code=r['code'], src_name=src_name))
    seen, uniq = set(), []
    for r in rows:                          # identische Zeilen (gleicher Name, gleiche Spezifikation, gleicher Preis) nur einmal zeigen
        k = (r['section'], r['name'], r['spec'], r['usd'])
        if k in seen:
            r['entfallen'] = True
            continue
        seen.add(k)
        uniq.append(r)
    return uniq


def pen_rows():
    z = json.load(open(QUELLE / 'ting_pens_zeilen.json'))
    rows = []
    for r in z:
        if (r['code'], r['spec'], r['dual_usd']) in PEN_SKIP:
            continue
        yc = r['y'] / 2 + 8
        sec = [t for y, t in PEN_SECTIONS if y < yc][-1]
        name = PEN_NAMES.get(r['name'], r['name'])
        spec = fmt_spec(PEN_SPEC_FIX.get(r['code'], r['spec']))
        if r['code'] == 'LIR30':
            spec = '20 mg'   # in der Quelle so gedruckt
        sec = PEN_SECTION_MOVE.get(name, sec)
        rows.append(dict(section=sec, name=name, spec=spec, dual=r['dual_usd'], single=r['single_usd'], new_dual=money(r['dual_usd']), new_single=money(r['single_usd']),
                         src_code=r['code'], src_name=r['name'], yc=yc))
    for i in range(1, len(rows)):          # Abschnittsbalken der Quelle sitzt mitten in einer Namensgruppe: ganze Gruppe in den spaeteren Abschnitt
        if rows[i]['name'] == rows[i - 1]['name'] and rows[i]['section'] != rows[i - 1]['section']:
            j = i - 1
            while j >= 0 and rows[j]['name'] == rows[i]['name']:
                rows[j]['section'] = rows[i]['section']
                j -= 1
    return rows


def sections(rows):
    out = []
    for r in rows:
        if not out or out[-1][0] != r['section']:
            out.append((r['section'], []))
        out[-1][1].append(r)
    return out


# ---------------------------------------------------------------- PDF
def render(rows, kind, outfile, total=None):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import BaseDocTemplate, CondPageBreak, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.platypus import Image as RLImage
    from render_lists import logo_png
    INK, MUTED, PET, PET2, SOFT, LINE = (colors.HexColor(c) for c in ('#172027', '#66717B', '#0D5B6B', '#3F8190', '#EEF4F5', '#D9DEE2'))
    W, H = A4
    m = 14 * mm
    title = 'Peptide Price List' if kind == 'vials' else 'Cartridge Price List'
    sub = 'Vials · 10 vials per unit' if kind == 'vials' else 'Dual- and single-chamber cartridges'   # bewusst ohne Datum (Eddy 25.10.2026)
    footer = f'Elements Labs · {title} · Prices in USD, subject to confirmation'
    doc = BaseDocTemplate(str(outfile), pagesize=A4, leftMargin=m, rightMargin=m, topMargin=14 * mm, bottomMargin=16 * mm,
                          title=f'Elements Labs · {title}', author='Elements Labs', subject='', creator='Elements Labs')

    def foot(c, d):
        c.saveState()
        c.setStrokeColor(LINE)
        c.line(m, 11 * mm, W - m, 11 * mm)
        c.setFont('Helvetica', 8)
        c.setFillColor(MUTED)
        c.drawString(m, 7 * mm, footer)
        c.drawRightString(W - m, 7 * mm, f'Page {d.page}' + (f' of {total}' if total else ''))
        c.restoreState()

    doc.addPageTemplates([PageTemplate(id='p', frames=[Frame(m, 18 * mm, W - 2 * m, H - 32 * mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=foot)])
    h1 = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=22, leading=26, textColor=INK)
    subs = ParagraphStyle('sub', fontName='Helvetica', fontSize=10, leading=14, textColor=MUTED)
    cell = ParagraphStyle('c', fontName='Helvetica', fontSize=8.5, leading=10.5, textColor=INK)
    bold = ParagraphStyle('cb', parent=cell, fontName='Helvetica-Bold')
    right = ParagraphStyle('r', parent=cell, alignment=2)
    rbold = ParagraphStyle('rb', parent=right, fontName='Helvetica-Bold')
    white = ParagraphStyle('w', parent=bold, textColor=colors.white)
    cwhite = ParagraphStyle('cw', parent=white, alignment=1)
    logo, (lw, lh) = logo_png()
    img = RLImage(str(logo), width=46 * mm, height=46 * mm * lh / lw)
    img.hAlign = 'LEFT'
    story = [img, Spacer(1, 6), Paragraph(title, h1), Paragraph(sub, subs), Spacer(1, 10)]
    if kind == 'vials':
        cw = [82 * mm, 52 * mm, 0]
    else:
        cw = [0, 30 * mm, 40 * mm, 40 * mm]
    cw[0 if kind == 'pens' else 2] = W - 2 * m - sum(cw) + cw[0 if kind == 'pens' else 2]
    ncol = len(cw)
    for sec, rs in sections(rows):
        if kind == 'vials':
            head = [Paragraph('Product', bold), Paragraph('Specification', bold), Paragraph('Price (USD)', ParagraphStyle('hr', parent=bold, alignment=2))]
        else:
            head = [Paragraph('Product', bold), Paragraph('Specification', bold),
                    Paragraph('Dual-Chamber<br/>Price (USD)', ParagraphStyle('hr', parent=bold, alignment=2)), Paragraph('Single-Chamber<br/>Price (USD)', ParagraphStyle('hr2', parent=bold, alignment=2))]
        data = [[Paragraph(sec, white)] + [''] * (ncol - 1), head]
        for r in rs:
            if kind == 'vials':
                data.append([Paragraph(r['name'], cell), Paragraph(r['spec'], cell), Paragraph(fmt_money(r['new']), rbold)])
            else:
                data.append([Paragraph(r['name'], cell), Paragraph(r['spec'], cell), Paragraph(fmt_money(r['new_dual']), rbold), Paragraph(fmt_money(r['new_single']), right)])
        story.append(CondPageBreak(42 * mm))
        t = Table(data, colWidths=cw, repeatRows=2)
        groups, i0 = [], 2
        for k in range(3, len(data) + 1):
            if k == len(data) or rs[k - 2]['name'] != rs[i0 - 2]['name']:
                if k - i0 > 1:
                    groups.append(('NOSPLIT', (0, i0), (-1, k - 1)))
                i0 = k
        t.setStyle(TableStyle(groups + [('SPAN', (0, 0), (-1, 0)), ('NOSPLIT', (0, 0), (-1, min(3, len(data) - 1))), ('NOSPLIT', (0, max(0, len(data) - 3)), (-1, len(data) - 1)), ('BACKGROUND', (0, 0), (-1, 0), PET), ('BACKGROUND', (0, 1), (-1, 1), SOFT), ('LINEBELOW', (0, 1), (-1, 1), 0.8, PET),
                               ('LINEBELOW', (0, 2), (-1, -1), 0.4, LINE), ('ROWBACKGROUNDS', (0, 2), (-1, -1), [colors.white, colors.HexColor('#E4EDEF')]), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 2.8),
                               ('BOTTOMPADDING', (0, 0), (-1, -1), 2.8), ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4)]))
        story += [t, Spacer(1, 10)]
    doc.build(story)
    return doc.page


def main(argv):
    vials, pens = vial_rows(), pen_rows()
    INTERN.mkdir(parents=True, exist_ok=True)
    with (INTERN / 'zuordnung.csv').open('w', newline='') as fh:
        w = csv.writer(fh, delimiter=';')
        w.writerow(['liste', 'abschnitt', 'quellcode_INTERN', 'quellname_INTERN', 'anzeige_name', 'spezifikation', 'quellpreis_usd', 'neuer_preis_usd', 'quellpreis_single_usd', 'neuer_preis_single_usd'])
        for r in vials:
            w.writerow(['vials', r['section'], r['src_code'], r['src_name'], r['name'], r['spec'], r['usd'], r['new'], '', ''])
        for r in pens:
            w.writerow(['cartridges', r['section'], r['src_code'], r['src_name'], r['name'], r['spec'], r['dual'], r['new_dual'], r['single'], r['new_single']])
    print(f'Daten: {len(vials)} Vial-Zeilen, {len(pens)} Cartridge-Zeilen; Zuordnung {INTERN / "zuordnung.csv"}')
    if '--daten' in argv:
        return 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for rows, kind, name in ((vials, 'vials', 'Elements Labs Preisliste Partner – Vials.pdf'), (pens, 'pens', 'Elements Labs Preisliste Partner – Cartridges.pdf')):
        n = render(rows, kind, OUT_DIR / name)
        render(rows, kind, OUT_DIR / name, total=n)
    print('PDFs:', *sorted(p.name for p in OUT_DIR.iterdir()), sep='\n  ')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
