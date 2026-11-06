"""Eine Lieferanten-Übersicht (PDF): Vials + Doppelkammer, günstigste Preise, Elements-Labs-Logo + Produktbild."""
import math
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.platypus import Image as RLImage
from PIL import Image

from fill_prices import fill, model_fill
from analyse_prices import DUAL_ALIAS, key, load
from render_lists import ORDER, logo_png
STAND = '24.10.2026'


def eur(v):
    """Ganze Zehner-Euro, deutsches Tausenderformat (1.280 €)."""
    return f'{int(round(v)):,}'.replace(',', '.') + ' €'


def ceil10(v):
    return int(math.ceil(round(v, 6) / 10.0)) * 10

HERE = Path(__file__).resolve().parent
OUT = HERE / 'Elements Labs Einkaufsübersicht Vials und Doppelkammer.pdf'
PET, INK, MUTED, SOFT, LINE = colors.HexColor('#0D5B6B'), colors.HexColor('#172027'), colors.HexColor('#66717B'), colors.HexColor('#EEF2F3'), colors.HexColor('#E1E5E7')


STEP_MIN = 0.97  # naechstkleinere Dosierung mindestens 3 % guenstiger (keine gleichen Preise fuer verschiedene Dosierungen)
DUAL_MIN = 1.15  # Doppelkammer mindestens 15 % teurer als das Vial gleicher Dosierung
SAME = {'TB-500 (Full-Length)': 'TB-500', 'Oxytocin (Pharma-Qualität)': 'Oxytocin',
        'CJC-1295 (ohne DAC) + Ipamorelin (5 mg + 5 mg)': 'CJC-1295 + Ipamorelin', 'TB-500 Fragment': 'TB-500 Fragment'}
RENAME = {'TB Frag': 'TB-500 Fragment'}


def rows(o):
    """One line per product+dose; Vial price and Doppelkammer price side by side. Cartridge variants that have no
    1:1 vial counterpart (Melanotan I/II, Oxytocin Industriequalität, Retatrutide 80 mg ...) get their own line without a vial price."""
    vmap, order = {}, []
    for v in o['vials']:
        name = RENAME.get(v['name'], v['name'])
        r = dict(section=v['section'], name=name, dose=v['dose'], vial=v['best_eur'], dual=None)
        vmap[key(name, v['dose'])] = r
        order.append(r)
    extra = []
    for d in o['dual']:
        sgl = round(d['single_usd'] * 10 / o['rate'], 2)
        tgt = vmap.get(key(SAME.get(d['name'], d['name']), d['dose'])) if (d['name'] in SAME or key(d['name'], d['dose']) in vmap) else None
        if tgt and tgt['dual'] is None:
            tgt['dual'] = round(d['dual_usd'] * 10 / o['rate'], 2)
            tgt['single'] = sgl
            if d['name'] != tgt['name'] and d['name'] not in ('TB-500 Fragment',):
                tgt['alias'] = d['name']
        else:
            extra.append(dict(section=d['section'], name=d['name'], dose=d['dose'], vial=None, dual=round(d['dual_usd'] * 10 / o['rate'], 2), single=sgl))
    out = list(order)
    num = lambda r: float(r['dose'].split()[0].replace(',', '.'))
    for e in extra:
        base = e['name'].split(' (')[0]
        idx = [i for i, r in enumerate(out) if r['section'] == e['section'] and r['name'].split(' (')[0] == base]
        pos = len(out)
        if idx:
            after = [i for i in idx if num(out[i]) <= num(e)]
            pos = (after[-1] if after else idx[0] - 1) + 1
            if base == 'Oxytocin':
                pos = idx[-1] + 1
        else:
            same = [i for i, r in enumerate(out) if r['section'] == e['section']]
            pos = (same[-1] + 1) if same else len(out)
        out.insert(pos, e)
    return out


def build():
    o = load()
    allr, log = fill(rows(o))
    step = round(10 / o['rate'], 2)
    for r in allr:  # ladder-filled cartridge prices: single = dual minus 1 USD per piece
        if r.get('dual_est') and r['dual'] is not None and 'single' not in r:
            r['single'] = round(r['dual'] - step, 2); r['single_est'] = True
    allr, log = model_fill(allr, log, step)
    log['raw'] = [{'name': r.get('alias') or r['name'], 'dose': r['dose'], 'vial': r.get('vial'), 'dual': r.get('dual'), 'dual_est': bool(r.get('dual_est')), 'section': r['section']} for r in allr]  # reale Einkaufspreise vor allen Wunsch-Regeln
    # best-possible list for the negotiation: a smaller dose never costs more than the next larger one, and a Doppelkammer is always
    # at least DUAL_MIN (15 %) dearer than the vial of the same dose (Owner 24.10.2026). Calculated cartridge prices are raised to the
    # minimum; where the cartridge price comes from the supplier list, the vial price is set lower instead (wish price for the negotiation).
    log['clamped'], log['dual_min'] = [], []
    groups = {}
    for r in allr:
        groups.setdefault((r.get('alias') or r['name'], r['dose'].split()[-1]), []).append(r)
    for _ in range(12):
        changed = False
        for r in allr:
            if r.get('vial') is not None and r.get('dual') is not None and r['dual'] < r['vial'] * DUAL_MIN - 0.0049:
                nm = r.get('alias') or r['name']
                if r.get('dual_est'):
                    log['dual_min'].append((nm, r['dose'], 'dual', r['dual'], round(r['vial'] * DUAL_MIN, 2)))
                    r['dual'] = math.ceil(r['vial'] * DUAL_MIN * 100) / 100
                else:
                    log['dual_min'].append((nm, r['dose'], 'vial', r['vial'], math.floor(r['dual'] / DUAL_MIN * 100) / 100))
                    r['vial'] = math.floor(r['dual'] / DUAL_MIN * 100) / 100  # abgerundet: Vial x 1,15 liegt nie ueber der Doppelkammer
                    r['vial_est'] = True
                changed = True
        for (nm, unit), rs in groups.items():
            rs.sort(key=lambda r: float(r['dose'].split()[0].replace(',', '.')))
            for col in ('vial', 'dual'):
                floor = None
                for r in reversed(rs):
                    if r.get(col) is None:
                        continue
                    if floor is not None and r[col] > floor * STEP_MIN:
                        log['clamped'].append((nm, r['dose'], col, r[col], round(floor * STEP_MIN, 2)))
                        r[col] = math.floor(floor * STEP_MIN * 100) / 100
                        r[col + '_est'] = True if col == 'vial' else r.get(col + '_est')
                        changed = True
                    floor = r[col] if floor is None else min(floor, r[col])
        if not changed:
            break
    # Zehner-Preise (Owner 24.10.2026): jeder Preis wird auf volle 10 EUR aufgerundet; Abstandsregeln danach nur noch durch Anheben gesichert
    log['tens_raised'] = []
    for r in allr:
        for col in ('vial', 'dual'):
            if r.get(col) is not None:
                r[col] = ceil10(r[col])
    for _ in range(20):
        changed = False
        for r in allr:
            if r.get('vial') is not None and r.get('dual') is not None and r['dual'] < ceil10(r['vial'] * DUAL_MIN):
                r['dual'] = ceil10(r['vial'] * DUAL_MIN)
                changed = True
        for (nm, unit), rs in groups.items():
            rs.sort(key=lambda r: float(r['dose'].split()[0].replace(',', '.')))
            for col in ('vial', 'dual'):
                prev = None
                for r in rs:
                    if r.get(col) is None:
                        continue
                    if prev is not None and r[col] < prev + 10:
                        log['tens_raised'].append((nm, r['dose'], col, r[col], prev + 10))
                        r[col] = prev + 10
                        changed = True
                    prev = r[col]
        if not changed:
            break
    import top_seller as _ts
    star_set = set(_ts.top20())
    for r in allr:
        nm_ = r.get('alias') or r['name']
        c_ = _ts.canon(nm_)
        combo = '+' in nm_.replace('NAD+', '')
        r['star'] = c_ in star_set and (not combo or c_ == 'BPC-157 + TB-500')
    sec_idx = {s: i for i, s in enumerate(ORDER)}
    allr.sort(key=lambda r: sec_idx[r['section']])  # stable
    logo, (lw, lh) = logo_png()
    W, H = A4
    m = 15 * mm
    doc = BaseDocTemplate(str(OUT), pagesize=A4, leftMargin=m, rightMargin=m, topMargin=14 * mm, bottomMargin=17 * mm,
                          title='Elements Labs · Einkaufsübersicht Vials und Doppelkammer', author='Elements Labs')

    def foot(c, d):
        c.saveState()
        c.setStrokeColor(LINE); c.line(m, 12.5 * mm, W - m, 12.5 * mm)
        c.setFont('Helvetica', 8); c.setFillColor(MUTED)
        c.drawString(m, 8 * mm, f'Elements Labs · Preisübersicht Vials & Doppelkammer · Stand {STAND} · Preise in Euro')
        c.drawRightString(W - m, 8 * mm, f'Seite {d.page}')
        c.restoreState()

    doc.addPageTemplates([PageTemplate(id='p', frames=[Frame(m, 17 * mm, W - 2 * m, H - 31 * mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=foot)])
    h1 = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=21, leading=25, textColor=INK, spaceAfter=3)
    sub = ParagraphStyle('sub', fontName='Helvetica', fontSize=10, leading=14, textColor=MUTED)
    body = ParagraphStyle('b', fontName='Helvetica', fontSize=9.2, leading=12.6, textColor=INK, spaceAfter=3)
    cell = ParagraphStyle('c', fontName='Helvetica', fontSize=9, leading=11.3, textColor=INK)
    cellb = ParagraphStyle('cb', parent=cell, fontName='Helvetica-Bold')
    rt = ParagraphStyle('rt', parent=cell, alignment=2)
    rtb = ParagraphStyle('rtb', parent=rt, fontName='Helvetica-Bold')
    na = ParagraphStyle('na', parent=rt, fontSize=7.4, textColor=colors.HexColor('#9AA3AA'))
    mu = ParagraphStyle('mu', parent=rt, textColor=colors.HexColor('#9AA3AA'))

    img = Image.open(HERE / 'bild' / 'elements_labs_produktbild.png')
    iw = 88 * mm
    ih = iw * img.height / img.width
    lg = RLImage(str(logo), width=56 * mm, height=56 * mm * lh / lw)
    lg.hAlign = 'LEFT'
    left = [lg, Spacer(1, 10), Paragraph('Preisübersicht<br/>Vials &amp; Doppelkammer', h1), Spacer(1, 2),
            Paragraph(f'Günstigste Einkaufspreise · Stand {STAND}', sub), Spacer(1, 8),
            Paragraph('<b>Vial:</b> Preis je Packung mit 10 Vials.', body),
            Paragraph('<b>Doppelkammer:</b> Preis je Packung mit 10 Kartuschen.', body),
            Paragraph('<font color="#B54708" size="7.2"><b>TOP</b></font> = Schwerpunktprodukt (zählt zu den 20 meistverkauften Wirkstoffen in Deutschland/Europa). Hier ist der beste Preis besonders wichtig.', body),
            Paragraph('Alle Preise in Euro, auf volle 10 € aufgerundet. <font color="#0D5B6B"><b>*</b></font> = rechnerisch ergänzt bzw. angepasst (Preisstaffel, Basispreis des Vials, Doppelkammer mindestens 15 % über dem Vial). <strike>Durchgestrichen</strike> = in dieser Ausführung nicht bestellbar.', body)]
    head = Table([[left, RLImage(str(HERE / 'bild' / 'elements_labs_produktbild.png'), width=iw, height=ih)]], colWidths=[W - 2 * m - iw - 4 * mm, iw + 4 * mm])
    head.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
    story = [head, Spacer(1, 10)]

    cw = [W - 2 * m - 90 * mm, 24 * mm, 33 * mm, 33 * mm]
    secs = []
    for r in allr:
        if not secs or secs[-1][0] != r['section']:
            secs.append((r['section'], []))
        secs[-1][1].append(r)
    for sec, rs in secs:
        data = [[Paragraph(sec, ParagraphStyle('s', parent=cellb, textColor=colors.white)), '', '', ''],
                [Paragraph('Produkt', cellb), Paragraph('Dosierung', cellb), Paragraph('Vial<br/>10er-Packung', ParagraphStyle('h', parent=rtb, leading=10.5)),
                 Paragraph('Doppelkammer<br/>10er-Packung', ParagraphStyle('h2', parent=rtb, leading=10.5))]]
        st = [('SPAN', (0, 0), (-1, 0)), ('BACKGROUND', (0, 0), (-1, 0), PET), ('BACKGROUND', (0, 1), (-1, 1), SOFT), ('LINEBELOW', (0, 1), (-1, 1), 0.8, PET),
              ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 2.6), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.6)]
        for r in rs:
            nm = r.get('alias') or r['name']
            def pc(col):
                if r.get(col) is not None:
                    return Paragraph(('<font color="#0D5B6B"><b>*</b></font> ' if r.get(col + '_est') else '') + f"<b>{eur(r[col])}</b>", rt)
                return Paragraph('<strike>nicht bestellbar</strike>', na)
            data.append([Paragraph(('<font color="#B54708" size="7.2"><b>TOP</b></font> <b>' + nm + '</b>') if r.get('star') else nm, cell), Paragraph(r['dose'], cell), pc('vial'), pc('dual')])
            st.append(('LINEBELOW', (0, len(data) - 1), (-1, len(data) - 1), 0.25, LINE))
        t = Table(data, colWidths=cw, repeatRows=2)
        t.setStyle(TableStyle(st))
        story += [t, Spacer(1, 8)]
    have = {(r.get('alias') or r['name']) for r in allr if r['dual'] is not None}
    nd = sorted((f"{n} ({', '.join(ds)})" if n in have else n) for n, ds in log['na_dual'].items())
    nv = sorted({n for n, _ in log['na_vial']})
    story.append(KeepTogether([Paragraph('Hinweise zur Bestellbarkeit', ParagraphStyle('hh', parent=cellb, fontSize=11, textColor=PET, spaceBefore=4, spaceAfter=4)),
        Paragraph('<b>Nicht als Doppelkammer bestellbar</b> (durchgestrichen, kein Kartuschenpreis in der Liste): ' + ', '.join(nd) + '.', body),
        Spacer(1, 4), Paragraph('<b>Nicht als Vial bestellbar:</b> ' + ', '.join(nv) + '.', body),
        Spacer(1, 6), Paragraph('<b>Berechnungsgrundlage</b>', ParagraphStyle('hh2', parent=cellb, fontSize=11, textColor=PET, spaceAfter=3)),
        Paragraph(f"<b>Vial:</b> niedrigster Preis je Produkt und Dosierung aus allen vorliegenden Listen; bei der USD-Liste gilt der darunterliegende Basispreis, wenn er niedriger ist ({len(o['base_used'])} Positionen). USD-Preise sind mit dem EZB-Kurs vom {o['rate_date'][8:]}.{o['rate_date'][5:7]}.{o['rate_date'][:4]} (1 EUR = {str(o['rate']).replace('.', ',')} USD) umgerechnet.", body),
        Paragraph(f"<b>Abstand Vial/Doppelkammer:</b> Die Doppelkammer ist bei jeder Dosierung mindestens 15 % teurer als das Vial ({len(log['dual_min'])} Preise entsprechend angepasst).", body),
        Paragraph(f"<b>Staffel:</b> Eine kleinere Dosierung ist immer mindestens 3 % günstiger als die nächstgrößere ({len(log['clamped'])} Preise entsprechend angepasst).", body),
        Paragraph(f"<b>Doppelkammer:</b> Preis je Kartusche mal 10. Wo die Kartuschen-Liste ein Produkt oder eine Dosierung nicht enthält (*), ist der Preis berechnet: bei vorhandener Staffel nach der Staffel des Produkts, sonst aus dem Vial-Basispreis nach der Kurve aller {log['model']['n']} Produkte mit beiden Preisen (Abweichung im Median {log['model']['median_err']*100:.0f} %, in 9 von 10 Fällen unter {log['model']['p90_err']*100:.0f} %). Der Doppelkammer-Preis liegt dabei nie unter dem Vial-Preis.", body),
        ]))
    doc.build(story)
    global LAST_LOG
    LAST_LOG = log
    return allr


LAST_LOG = None
if __name__ == '__main__':
    r = build()
    for c in LAST_LOG['clamped']:
        print('clamp', c)
    print(len(r), 'rows;', sum(1 for x in r if x['vial'] is not None), 'with vial;', sum(1 for x in r if x['dual'] is not None), 'with dual;',
          sum(1 for x in r if x['vial'] is not None and x['dual'] is not None), 'both')
