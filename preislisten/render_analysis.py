"""Preisanalyse (Excel + PDF) from merged.json. Neutral list labels A-D; no supplier identity."""
import io
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus import Image as RLImage

from analyse_prices import compute, load
from render_lists import ORDER, STAND, eur, logo_png

HERE = Path(__file__).resolve().parent
PET = '#0D5B6B'
LABEL = {'A': 'Liste A · Wholesale-EUR-Datei (je 10 Vials)', 'B': 'Liste B · EUR-Preislisten-Datei (je 10 Vials)',
         'C': 'Liste C · Vials-PDF (USD, je 10 Vials)', 'D': 'Liste D · Kartuschen-PDF (USD, je Kartusche)'}
SHORT = {'Wholesale-EUR-Liste': 'A', 'EUR-Preisliste': 'B', 'Ting-USD-Liste': 'C'}


def pct(x, d=1):
    return f'{x * 100:.{d}f} %'.replace('.', ',')


def findings(o, r):
    cat_best = max(r['by_cat'].items(), key=lambda kv: kv[1]['pct'])
    top = r['top_savings'][0]
    return [
        f"Vollständigkeit: Alle {len(o['trace'])} Zeilen der vier Listen sind verarbeitet (A 228, B 228, C 126, D 115). {len(o['trace']) - 1} davon sind in der Elements-Liste berücksichtigt (gleiche Produkte aus mehreren Listen werden zu einer Zeile zusammengeführt: {r['rows']['final_vials'] + r['rows']['final_dual']} Zeilen). 1 Zeile ist offen: die zweite KLOW-Zeile in Liste D mit abweichendem Preis.",
        f"Ergebnis: {r['rows']['final_vials']} Vial-Zeilen ({r['products']} Produkte) und {r['rows']['final_dual']} Doppelkammer-Zeilen in der Elements-Labs-Liste.",
        f"Bester Preis: In {r['wins_C']} von {r['matched_AC']} direkt vergleichbaren Zeilen ist Liste C (USD) günstiger als Liste A; in {r['C_vs_A']['dearer']} Zeilen ist sie teurer. Der Median von C liegt bei {pct(r['C_vs_A']['median'] - 1)} über A, die Streuung ist groß ({pct(r['C_vs_A']['min'] - 1, 0)} bis +{pct(r['C_vs_A']['max'] - 1, 0)}).",
        f"Einsparung: Wer von jeder Dosis eine Packung kauft, zahlt bei Liste A {eur(r['sum_A'])}, bei Liste B {eur(r['sum_B'])} und mit den besten Preisen {eur(r['sum_best_ab'])} (−{eur(r['saving_vs_A'])} gegenüber A, −{eur(r['saving_vs_B'])} gegenüber B).",
        f"Größter Hebel: {cat_best[0]} (−{pct(cat_best[1]['pct'] / 100)} gegenüber A). Größte Einzelersparnis: {top[1]} {top[2]} um {eur(top[0])} je Packung ({eur(top[3])} → {eur(top[4])}).",
        f"Liste B ist durchgehend {pct(r['B_vs_A']['min'] - 1, 0)} bis {pct(r['B_vs_A']['max'] - 1, 0)} teurer als Liste A (Median {pct(r['B_vs_A']['median'] - 1)}); sie gewinnt nie. Sie zeigt aber, welchen Aufschlag der Lieferant selbst auf seine Großhandelspreise legt.",
        f"Doppelkammer vs. Vial: Eine Doppelkammer-Kartusche kostet im Einkauf im Median {pct(r['premium']['median'], 0)} mehr als ein einzelnes Vial derselben Dosis ({r['premium']['n']} Paare). In {r['premium']['cheaper']} Fällen ist die Kartusche günstiger als das Vial. Für {r['vial_without_dual']} Vial-Produkte gibt es keinen Kartuschenpreis.",
        f"Auffälligkeiten: {len(r['anomalies'])} Preise, bei denen eine kleinere Dosis mehr kostet als die nächstgrößere (stammen aus der Mischung der Listen), und {len(r['outliers_C'])} Zeilen mit sehr großer Abweichung zwischen Liste A und C (> 30 % billiger oder > 60 % teurer).",
    ]


# ------------------------------------------------------------------ charts
def chart_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=170, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


def chart_savings(r):
    cats = sorted([c for c in ORDER if c in r['by_cat']], key=lambda c: r['by_cat'][c]['pct'], reverse=True)
    vals = [r['by_cat'][c]['pct'] for c in cats]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.barh(cats[::-1], vals[::-1], color=PET)
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 0.08, i, f'{v:.1f} %'.replace('.', ','), va='center', fontsize=8)
    ax.set_xlabel('Ersparnis durch besten Preis gegenüber Liste A (%)', fontsize=8)
    ax.tick_params(labelsize=8)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    return chart_png(fig)


def chart_ratio(o):
    rat = [v['ting_eur'] / v['wholesale_eur'] for v in o['vials'] if v['ting_eur'] and v['wholesale_eur']]
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    ax.hist([min(x, 2.0) for x in rat], bins=24, color='#2A2F36')
    ax.axvline(1.0, color=PET, lw=1.2)
    ax.set_ylim(0, ax.get_ylim()[1] * 1.18)
    ax.text(0.99, ax.get_ylim()[1] * 0.97, 'C günstiger ←', color=PET, fontsize=8, ha='right', va='top')
    ax.text(1.01, ax.get_ylim()[1] * 0.97, '→ C teurer', color=PET, fontsize=8, ha='left', va='top')
    ax.set_xlabel('Preis Liste C (umgerechnet) geteilt durch Preis Liste A  (<1 = C günstiger; Werte >2 bei 2 gekappt)', fontsize=8)
    ax.set_ylabel('Anzahl Zeilen', fontsize=8)
    ax.tick_params(labelsize=8)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    return chart_png(fig)


def chart_premium(r):
    import statistics as st
    by = {}
    for p in r['pairs']:
        by.setdefault(p['section'], []).append(p['premium'])
    cats = sorted([c for c in ORDER if c in by], key=lambda c: st.median(by[c]), reverse=True)
    vals = [st.median(by[c]) * 100 for c in cats]
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    overall = st.median([p['premium'] for p in r['pairs']]) * 100
    ax.axvline(overall, color='#2A2F36', lw=1, ls='--')
    ax.text(overall + 1, -0.45, f'Gesamt-Median +{overall:.0f} %'.replace('.', ','), fontsize=8, color='#2A2F36')
    ax.barh(cats[::-1], vals[::-1], color=PET)
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 1, i, f'+{v:.0f} %', va='center', fontsize=8)
    ax.set_xlabel('Median-Aufschlag Kartusche gegenüber einzelnem Vial gleicher Dosis (Einkauf, %)', fontsize=8)
    ax.tick_params(labelsize=8)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    return chart_png(fig)


def glp_text(o):
    g = [v for v in o['vials'] if v['name'] in ('Semaglutide', 'Tirzepatide', 'Retatrutide') and v['wholesale_eur'] and v['ting_eur']]
    o_ = [v for v in o['vials'] if v['name'] not in ('Semaglutide', 'Tirzepatide', 'Retatrutide') and v['wholesale_eur'] and v['ting_eur']]
    gc = sum(1 for v in g if v['ting_eur'] < v['wholesale_eur'])
    oc = sum(1 for v in o_ if v['ting_eur'] < v['wholesale_eur'])
    return (f'Bei Semaglutide, Tirzepatide und Retatrutide ist Liste C in {gc} von {len(g)} vergleichbaren Zeilen günstiger als Liste A, bei allen anderen Produkten nur in {oc} von {len(o_)}. '
            'Deshalb lohnt der Vergleich je Zeile und nicht je Liste.')


# ------------------------------------------------------------------ PDF
def build_pdf(o, r, path):
    logo, (lw, lh) = logo_png()
    W, H = A4
    m = 16 * mm
    doc = BaseDocTemplate(str(path), pagesize=A4, leftMargin=m, rightMargin=m, topMargin=16 * mm, bottomMargin=18 * mm, title='Elements Labs · Preisanalyse', author='Elements Labs')

    def foot(c, d):
        c.saveState()
        c.setFont('Helvetica', 8)
        c.setFillColor(colors.HexColor('#66717B'))
        c.drawString(m, 9 * mm, f'Elements Labs · Preisanalyse Einkauf · intern · Stand {STAND}')
        c.drawRightString(W - m, 9 * mm, f'Seite {d.page}')
        c.restoreState()

    doc.addPageTemplates([PageTemplate(id='p', frames=[Frame(m, 18 * mm, W - 2 * m, H - 34 * mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=foot)])
    ink = colors.HexColor('#172027')
    h1 = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=21, leading=25, textColor=ink, spaceAfter=3)
    h2 = ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=13, leading=17, textColor=colors.HexColor(PET), spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle('b', fontName='Helvetica', fontSize=9.6, leading=13.4, textColor=ink, spaceAfter=4)
    bullet = ParagraphStyle('bl', parent=body, leftIndent=10, bulletIndent=0)
    small = ParagraphStyle('s', parent=body, fontSize=8.4, leading=11, textColor=colors.HexColor('#66717B'))
    st_ = []
    img = RLImage(str(logo), width=54 * mm, height=54 * mm * lh / lw)
    img.hAlign = 'LEFT'
    st_ += [img, Spacer(1, 6), Paragraph('Preisanalyse Einkauf', h1), Paragraph(f'Stand {STAND} · vier Listen · Preise in Euro (USD umgerechnet mit EZB-Kurs {str(o["rate"]).replace(".", ",")} vom {o["rate_date"][8:]}.{o["rate_date"][5:7]}.{o["rate_date"][:4]})', small)]
    kp = [['Zeilen verarbeitet', str(len(o['trace']))], ['Vial-Zeilen in der Liste', str(r['rows']['final_vials'])], ['Doppelkammer-Zeilen', str(r['rows']['final_dual'])],
          ['Produkte (Vials)', str(r['products'])], ['Liste C günstiger als A', f"{r['wins_C']} von {r['matched_AC']}"], ['Ersparnis je 1 Packung jeder Dosis', eur(r['saving_vs_A']) + ' ggü. A']]
    t = Table([[Paragraph(f'<b>{a}</b>', small), Paragraph(f'<b>{b}</b>', body)] for a, b in kp], colWidths=[62 * mm, 40 * mm])
    t.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, -1), 0.3, colors.HexColor('#E1E5E7')), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    st_ += [Spacer(1, 6), t, Paragraph('Ergebnisse', h2)]
    for f in findings(o, r):
        st_.append(Paragraph(f, bullet, bulletText='•'))
    st_.append(PageBreak())
    st_ += [Paragraph('Wo der beste Preis spart', h2), RLImage(chart_savings(r), width=W - 2 * m, height=(W - 2 * m) * 3.6 / 7.2)]
    st_ += [Paragraph('Liste C gegen Liste A', h2), RLImage(chart_ratio(o), width=W - 2 * m, height=(W - 2 * m) * 3.2 / 7.2),
            Paragraph(glp_text(o), body)]
    st_.append(PageBreak())
    st_ += [Paragraph('Doppelkammer gegenüber Vial', h2), RLImage(chart_premium(r), width=W - 2 * m, height=(W - 2 * m) * 3.4 / 7.2),
            Paragraph(f"Der Einkaufspreis einer Kartusche liegt im Median {pct(r['premium']['median'], 0)} über dem Preis eines einzelnen Vials (Packung ÷ 10). Im Shop kostet die Doppelkammer-Ausführung derzeit genau so viel wie das Vial (Quellpreis der Vorlage): Sobald die neuen Einkaufspreise gelten, ist diese Gleichsetzung wirtschaftlich nicht mehr tragfähig.", body)]
    st_.append(Paragraph('Entscheidungen und offene Punkte', h2))
    items = [
        'Aufschlag: Kein Aufschlag angewendet. Im Excel gibt es ein Blatt „Verkaufspreis-Rechner“ mit einer Eingabezelle für den Aufschlag in %. Der Wert 25 % ist nur ein Beispiel.',
        'Auffälligkeiten (' + str(len(r['anomalies'])) + '): ' + '; '.join(f"{a['name']} {a['lo']} ({eur(a['plo'])}) teurer als {a['hi']} ({eur(a['phi'])})" for a in r['anomalies']) + '. Unverändert gelassen.',
        'Zweite Doppelkammer-Liste: lag nicht vor. Die Auswertung rechnet sie nach Eingang einfach dazu.',
        'Liste A heißt „Wholesale“: Mindestabnahmemengen sind möglich und nicht geprüft.',
        'Liste D (Kartuschen) war ein Bild. Preise per Texterkennung gelesen und gegengeprüft; die Zeile „LIR30“ druckt 20 mg, übernommen als 30 mg (Code und Preisverlauf sprechen dafür).',
    ]
    for it in items:
        st_.append(Paragraph(it, bullet, bulletText='•'))
    doc.build(st_)


# ------------------------------------------------------------------ XLSX
def build_xlsx(o, r, path):
    wb = openpyxl.Workbook()
    head_fill = PatternFill('solid', fgColor='0D5B6B')
    soft = PatternFill('solid', fgColor='EEF2F3')

    def put(ws, rows, widths=None, money=()):
        for row in rows:
            ws.append(row)
        for c in ws[1]:
            c.font = Font(bold=True, color='FFFFFF')
            c.fill = head_fill
            c.alignment = Alignment(vertical='center', wrap_text=True)
        ws.freeze_panes = 'A2'
        for i, w in enumerate(widths or [], 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        for col in money:
            for c in ws[get_column_letter(col)][1:]:
                c.number_format = '#,##0.00 "€"'

    ws = wb.active
    ws.title = 'Zusammenfassung'
    ws.append(['Preisanalyse Einkauf · Elements Labs', ''])
    ws['A1'].font = Font(bold=True, size=16)
    ws.append(['Stand', STAND])
    ws.append(['Wechselkurs', f"1 EUR = {o['rate']} USD (EZB {o['rate_date']})"])
    ws.append([])
    for f in findings(o, r):
        ws.append([f])
    ws.column_dimensions['A'].width = 150
    for row in ws.iter_rows(min_row=5):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical='top')

    ws = wb.create_sheet('Abdeckung')
    rows = [['Liste', 'Beschreibung', 'Zeilen gelesen', 'in Elements-Liste', 'nicht übernommen']]
    held_d = len(o['dual_held'])
    rows += [['A', LABEL['A'], 228, 228, 0], ['B', LABEL['B'], 228, 228, 0], ['C', LABEL['C'], 126, 126, 0], ['D', LABEL['D'], 115, 115 - held_d, held_d]]
    rows += [[], ['Hinweise', 'A und B sind zeilengleich (gleiche Produkte/Dosierungen). Doppelte Zeilen innerhalb einer Liste wurden zu einer zusammengefasst (Anzahl siehe Auffälligkeiten).'],
             ['Nur in Liste C', ', '.join(f'{a} {b}' for a, b in r['only_C'])], ['Doppelkammer ohne Vial-Preis', ', '.join(f'{a} {b}' for a, b in r['dual_without_vial'])]]
    put(ws, rows, [10, 60, 16, 20, 20])

    ws = wb.create_sheet('Rückverfolgung')
    put(ws, [['Liste', 'Verweis', 'Angabe', 'Preis in Quelle', 'Ergebnis', 'Zeile in der Elements-Liste']] + [[t['liste'], t['ref'], t['angabe'], t['preis'], t['ergebnis'], t['ziel']] for t in o['trace']], [8, 18, 48, 14, 52, 48])

    ws = wb.create_sheet('Vergleich Vials')
    rows = [['Abschnitt', 'Produkt', 'Dosierung', 'A Wholesale €', 'B Preisliste €', 'C USD', 'C in €', 'Bester Preis €', 'Quelle', 'je Vial €', 'Ersparnis ggü. A €', 'Ersparnis ggü. A %']]
    for v in sorted(o['vials'], key=lambda v: ORDER.index(v['section'])):
        a = v['wholesale_eur']
        rows.append([v['section'], v['name'], v['dose'], a, v['list_eur'], v['ting_usd'], v['ting_eur'], v['best_eur'], SHORT[v['best_source']], round(v['best_eur'] / 10, 2),
                     round(a - v['best_eur'], 2) if a is not None else None, round((a - v['best_eur']) / a, 4) if a else None])
    put(ws, rows, [34, 40, 12, 14, 14, 10, 12, 14, 8, 11, 16, 16], money=(4, 5, 7, 8, 10, 11))
    for c in ws['L'][1:]:
        c.number_format = '0.0%'
    ws.auto_filter.ref = ws.dimensions

    ws = wb.create_sheet('Einsparung')
    rows = [['Abschnitt', 'Zeilen (A/B vergleichbar)', 'Summe A €', 'Summe bester Preis €', 'Ersparnis €', 'Ersparnis %', 'Zeilen mit C als Sieger']]
    for c in ORDER:
        if c in r['by_cat']:
            v = r['by_cat'][c]
            rows.append([c, v['n'], round(v['A'], 2), round(v['best'], 2), round(v['saving'], 2), round(v['pct'] / 100, 4), v['c_wins']])
    rows.append(['GESAMT', sum(v['n'] for v in r['by_cat'].values()), round(r['sum_A'], 2), round(r['sum_best_ab'], 2), round(r['saving_vs_A'], 2), round(r['saving_vs_A'] / r['sum_A'], 4), r['wins_C']])
    rows += [[], ['Größte Einzelersparnisse je Packung', '', '', '', '', '', ''], ['Produkt', 'Dosierung', 'Preis A €', 'Bester Preis €', 'Ersparnis €']]
    for s, n, d, a, b in r['top_savings']:
        rows.append([n, d, a, b, s])
    put(ws, rows, [40, 22, 16, 20, 14, 14, 20], money=(3, 4, 5))
    for c in ws['F'][1:len(ORDER) + 2]:
        c.number_format = '0.0%'

    ws = wb.create_sheet('Vial vs Kartusche')
    rows = [['Abschnitt', 'Produkt', 'Dosierung', 'Vial-Packung €', 'je Vial €', 'Kartusche Dual €', 'Aufschlag Kartusche']]
    for p in sorted(r['pairs'], key=lambda p: (ORDER.index(p['section']), p['name'])):
        rows.append([p['section'], p['name'], p['dose'], p['vial_pack'], round(p['per_vial'], 2), p['cartridge'], round(p['premium'], 4)])
    put(ws, rows, [34, 42, 12, 16, 12, 18, 18], money=(4, 5, 6))
    for c in ws['G'][1:]:
        c.number_format = '0%'
    ws.auto_filter.ref = ws.dimensions

    ws = wb.create_sheet('Preis pro mg')
    rows = [['Produkt', 'Dosierung mg', 'Bester Preis €', '€ je mg', 'günstigste Dosis je mg']]
    for n, lst in sorted(r['per_mg'].items()):
        best = min(lst, key=lambda x: x[2])
        for num, price, per in lst:
            rows.append([n, num, price, round(per, 3), 'ja' if num == best[0] else ''])
    put(ws, rows, [44, 14, 16, 12, 22], money=(3,))
    ws.auto_filter.ref = ws.dimensions

    ws = wb.create_sheet('Auffälligkeiten')
    rows = [['Art', 'Liste', 'Produkt', 'Detail']]
    for a in r['anomalies']:
        rows.append(['Dosis-Preis-Reihenfolge', a['liste'], a['name'], f"{a['lo']} kostet {eur(a['plo'])} ({a['lo_src']}), {a['hi']} kostet {eur(a['phi'])} ({a['hi_src']})"])
    for n, d, a, c in r['outliers_C']:
        rows.append(['Große Abweichung A↔C', 'Vials', f'{n} {d}', f'A {eur(a)} gegenüber C {eur(c)}'])
    for h in o['dual_held']:
        rows.append(['Nicht übernommen', 'Doppelkammer', f"{h['name']} {h['spec']}", h['flag']])
    for p in o['dual']:
        if p['flag']:
            rows.append(['Quelle korrigiert/gedeutet', 'Doppelkammer', f"{p['name']} {p['dose']}", p['flag']])
    for v in o['vials']:
        if v.get('dups'):
            rows.append(['Duplikat zusammengefasst', 'Vials', f"{v['name']} {v['dose']}", f"zusätzliche Quellzeile(n) {v['dups']}"])
    put(ws, rows, [28, 16, 44, 110])

    ws = wb.create_sheet('Verkaufspreis-Rechner')
    ws['A1'] = 'Aufschlag auf den Einkaufspreis (%)'
    ws['B1'] = 25
    ws['B1'].fill = PatternFill('solid', fgColor='FFF2CC')
    ws['C1'] = 'Beispielwert, bitte anpassen. Alle Preise unten rechnen sich automatisch neu.'
    ws.append([])
    ws.append(['Abschnitt', 'Produkt', 'Dosierung', 'Einkauf je 10 Vials €', 'Verkauf je 10 Vials €', 'Verkauf je Vial €', 'Gewinn je 10 Vials €'])
    for c in ws[3]:
        c.font = Font(bold=True, color='FFFFFF')
        c.fill = head_fill
    n = 4
    for v in sorted(o['vials'], key=lambda v: ORDER.index(v['section'])):
        ws.append([v['section'], v['name'], v['dose'], v['best_eur'], f'=ROUND(D{n}*(1+$B$1/100),2)', f'=ROUND(E{n}/10,2)', f'=E{n}-D{n}'])
        n += 1
    for col in 'DEFG':
        for c in ws[col][3:]:
            c.number_format = '#,##0.00 "€"'
    for i, w in enumerate([34, 42, 12, 20, 20, 18, 20], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = 'A4'

    ws = wb.create_sheet('Regeln')
    for line in [['Wechselkurs', f"1 EUR = {o['rate']} USD, EZB-Referenzkurs {o['rate_date']}; EUR = USD ÷ Kurs, auf Cent gerundet"],
                 ['Bester Preis', 'niedrigster Preis je Produkt und Dosierung über alle Listen'],
                 ['Aufschlag', 'keiner angewendet; Rechner-Blatt mit Beispielwert'],
                 ['Doppelkammer', 'nur die Dual-Chamber-Spalte; Single-Chamber nicht verwendet; zweite Doppelkammer-Liste lag nicht vor'],
                 ['Listen', ' | '.join(LABEL.values())],
                 ['Zuordnung', 'über Produktcode + Dosierung; Rest über feste Zuordnungstabelle (merge_prices.py); unklare Zeilen nie in die Liste'],
                 ['Lipo-C', 'Liste C enthält zwei weitere Lipo-C-Varianten (216, 526), als eigene Zeilen übernommen; Variante 120 steht in Liste A/B/C']]:
        ws.append(line)
    ws.column_dimensions['A'].width = 18
    ws.column_dimensions['B'].width = 160
    wb.properties.creator = 'Elements Labs'
    wb.properties.title = 'Preisanalyse Einkauf'
    wb.save(path)


if __name__ == '__main__':
    o = load()
    r = compute(o)
    build_xlsx(o, r, HERE / 'Elements Labs Preisanalyse.xlsx')
    build_pdf(o, r, HERE / 'Elements Labs Preisanalyse.pdf')
    print('ok')
