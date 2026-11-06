"""Merge the supplier lists into one best-price table (internal) and the clean customer-facing rows.

Inputs (never published): two EUR workbooks (10-vial packs), one USD PDF (10-vial packs, extracted),
one USD PDF with dual-/single-chamber cartridges (extracted, price sequence OCR-checked).
Output: merged.json = {"vials": [...], "dual": [...], "audit": [...]}; no supplier identity leaves this folder.
"""
import collections
import json
import re
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
DESK = Path.home() / 'Desktop'
USD_PER_EUR = 1.1193  # ECB reference rate 2026-10-23
RATE_DATE = '2026-10-23'

SECTION_DE = {
    'Weight Loss & Fat Reduction': 'Gewichtsmanagement & Fettreduktion',
    'Repair & Recovery': 'Regeneration & Reparatur',
    'Beauty & Anti-aging': 'Beauty & Anti-Aging',
    'Sleep & Nervous System': 'Schlaf & Nervensystem',
    'Hormone & Growth': 'Hormone & Wachstum',
    'Immunity & Organ Regulation': 'Immunsystem & Organregulation',
    'Combination Sets': 'Kombinationssets',
    'Accessories': 'Zubehör',
    'Others': 'Weitere Produkte',
}

# row number in the workbooks -> display name (supplier typos / Chinese-name columns are not used)
NAME_FIX = {
    **{r: 'CJC-1295 (mit DAC)' for r in (165, 166, 167)}, **{r: 'CJC-1295 (ohne DAC)' for r in (168, 169, 170)},
    **{r: 'GHRP-2' for r in (154, 155, 156)}, **{r: 'GHRP-6' for r in (157, 158, 159)},
    185: 'Thymosin Alpha-1', 186: 'Thymosin Alpha-1', **{r: 'AHK-Cu' for r in (80, 81, 82)}, **{r: 'L-Carnitin' for r in (62, 63, 64, 65)},
    44: 'Cagrilintide + Semaglutide', 45: 'Cagrilintide + Semaglutide', 46: 'Cagrilintide + Semaglutide',
    59: '5-Amino-1MQ', 60: '5-Amino-1MQ', 61: '5-Amino-1MQ',
    67: 'Lipo-C (Variante 120)', 68: 'MIC (Lipo-C mit B12)',
    71: 'BPC-157', 72: 'BPC-157', 73: 'BPC-157', 74: 'BPC-157', 75: 'TB-500', 76: 'TB-500', 77: 'TB-500',
    98: 'Follistatin 344', 105: 'FOXO4-DRI', 106: 'FOXO4-DRI', 108: 'Snap-8', 109: 'Snap-8', 56: 'Adipotide', 57: 'Adipotide', 58: 'Adipotide',
    120: 'GLOW (BPC-157 + GHK-Cu + TB-500)', 121: 'KLOW (BPC-157 + TB-500 + GHK-Cu + KPV)',
    184: 'Thymalin', 193: 'Cardiogen / Cortagen / Crystagen', 187: 'LL-37',
    199: 'BPC-157 + TB-500 (5 mg + 5 mg)', 200: 'BPC-157 + TB-500 (10 mg + 10 mg)',
    201: 'BPC-157 + TB-500 (15 mg + 15 mg)', 202: 'BPC-157 + TB-500 (20 mg + 20 mg)',
    203: 'Semax + Selank (10 mg + 10 mg)', 204: 'CJC-1295 + Ipamorelin', 205: 'CJC-1295 + Ipamorelin',
    206: 'Retatrutide + Tirzepatide', 207: 'Tesamorelin + Ipamorelin (10 mg + 5 mg)',
    210: 'Bacteriostatisches Wasser', 211: 'Bacteriostatisches Wasser', 212: 'Essigsäure', 213: 'Essigsäure',
    214: 'Bacteriostatisches Wasser', 215: 'Bacteriostatisches Wasser',
    229: 'Melanotan I/II', 234: 'PT-141', 243: 'Botulinum toxin', 245: 'Frag 17-23', 220: 'ACE-031', 221: 'ACTH 1-39',
    194: 'ARA-290', 195: 'ARA-290', 190: 'VIP', 191: 'VIP', 188: 'KPV', 189: 'KPV',
}
SPEC_FIX = {214: '3ml*10 vials'}  # supplier typo: WA3 listed with 10 ml, same product as BA3

G, R, B, S, H, I, W_ = ('Gewichtsmanagement & Fettreduktion', 'Regeneration & Reparatur', 'Beauty & Anti-Aging', 'Schlaf & Nervensystem',
                       'Hormone & Wachstum', 'Immunsystem & Organregulation', 'Weitere Produkte')
DUAL_SECTION = {**{n: G for n in ('Semaglutide', 'Tirzepatide', 'Retatrutide', 'Cagrilintide', 'Mazdutide', 'Liraglutide', 'AOD9604')},
                **{n: R for n in ('BPC-157', 'TB-500 Fragment', 'TB-500 (Full-Length)', 'GHK-Cu', 'GLOW (BPC-157 + GHK-Cu + TB-500)',
                                  'KLOW (BPC-157 + TB-500 + GHK-Cu + KPV)')},
                **{n: H for n in ('CJC-1295 (ohne DAC)', 'CJC-1295 (mit DAC)', 'CJC-1295 (ohne DAC) + Ipamorelin (5 mg + 5 mg)', 'Ipamorelin', 'GHRP-2', 'GHRP-6',
                                  'Sermorelin', 'HCG', 'IGF-1 LR3', 'Tesamorelin', 'Kisspeptin-10', 'Gonadorelin')},
                **{n: S for n in ('DSIP', 'Selank', 'Semax', 'Oxytocin (Pharma-Qualität)', 'Oxytocin (Industriequalität)')},
                **{n: I for n in ('KPV', 'Thymalin', 'Thymosin Alpha-1', 'ARA-290', 'VIP', 'LL-37')},
                **{n: B for n in ('Epithalon', 'SS-31', 'Matrixyl', 'NAD+', 'Glutathione', 'MOTS-c', '5-Amino-1MQ', 'FOXO4-DRI')}}

# Ting vial code -> workbook row (spec/name differences that the automatic code match cannot resolve)
TING_MAP = {'LG5': 36, 'LG10': 37, 'LG30': 38, '332-5': 244, 'IG01': 94, 'Snap8': 108, 'DI10/DHA10': 132, 'OT5': 137,
            'OT10': 138, 'LL375/LL37': 187, 'KPV10': 189, 'VIP5': 190, 'VIP10': 191, 'MT1': 229, 'ML10': 229,
            'GLOW/BBG70': 120, 'KLOW/BBKG80': 121, 'CP10': 204, 'WA3': 210}
TING_EXTRA = {'332-10': ('SLU-PP-332', '10 mg'), 'B12/B-12': ('Vitamin B12', '10 mg')}
TING_HELD_BACK = {}
TING_EXTRA_ML = {'LC216': ('Lipo-C (Variante 216)', '10 ml'), 'LC526': ('Lipo-C (Variante 526)', '10 ml')}


def norm(s):
    return re.sub(r'[^a-z0-9.]', '', str(s).lower())


def parse_spec(spec):
    m = re.match(r'\s*([\d.]+)\s*(mg|mcg|iu|ml)\b', str(spec), re.I)
    if not m:
        raise ValueError('spec ' + repr(spec))
    num, unit = m.group(1), m.group(2).lower()
    if unit == 'mcg':
        unit = 'mcg'
    num = num.rstrip('0').rstrip('.') if '.' in num else num
    label = {'mg': 'mg', 'mcg': 'mcg', 'iu': 'IU', 'ml': 'ml'}[unit]
    return f'{num} {label}', float(m.group(1)), unit


def usd_to_eur(v):
    return round(v / USD_PER_EUR + 1e-9, 2)


def main():
    W = openpyxl.load_workbook(DESK / 'Wholesale EUR price.xlsx', data_only=True).active
    E = openpyxl.load_workbook(DESK / 'EUR PRICE.xlsx', data_only=True).active
    ting = json.loads((HERE / 'quellen_extrahiert/ting_vials_roh.json').read_text())
    pens = json.loads((HERE / 'quellen_extrahiert/ting_pens_zeilen.json').read_text())

    items, section = [], None
    trace_xlsx = []
    for r in range(1, W.max_row + 1):
        a = W.cell(r, 1).value
        if a and W.cell(r, 2).value is None:
            section = a
            continue
        if W.cell(r, 5).value is None or a == 'English Name':
            continue
        assert [W.cell(r, c).value for c in (1, 2, 3, 4)] == [E.cell(r, c).value for c in (1, 2, 3, 4)], r
        spec = SPEC_FIX.get(r, W.cell(r, 3).value)
        label, num, unit = parse_spec(spec)
        items.append(dict(row=r, section=SECTION_DE[section], name=NAME_FIX.get(r, a), dose=label, num=num, unit=unit,
                          wholesale_eur=float(W.cell(r, 5).value), list_eur=float(E.cell(r, 5).value), ting_usd=None,
                          code=str(W.cell(r, 4).value)))
    by_row = {i['row']: i for i in items}
    for i in items:
        for lst, key in (('A', 'wholesale_eur'), ('B', 'list_eur')):
            trace_xlsx.append(dict(liste=lst, ref=f"Zeile {i['row']}", angabe=f"{i['name']} {i['dose']}", preis=f'{i[key]:.0f} €', ergebnis='übernommen/verglichen', ziel=f"{i['name']} {i['dose']}"))
    bycode = {}
    for i in items:
        bycode.setdefault(norm(i['code']), []).append(i)

    audit, extras, held = [], [], []
    trace = []
    # hidden underlying price layer of the vial PDF ("Basispreis"): dark text layer below the visible price
    lay = collections.defaultdict(list)
    for c, dk, bk in json.loads((HERE / 'quellen_extrahiert/ting_vials_layers.json').read_text()):
        lay[c].append(dk)
    base_used = []
    for t in ting:
        code = t['code']
        price = int(re.sub(r'\D', '', t['price']))
        visible = price
        hid = lay.get(t['code'], [])
        if len(hid) == 1 and len(hid[0]) == 1 and 0.4 <= hid[0][0] / visible <= 2.5 and hid[0][0] < visible:
            price = hid[0][0]  # Basispreis (hidden layer) is cheaper than the visible price
            base_used.append((t['code'], visible, price))
        spec = t.get('spec_pdf') or ''
        target = None
        if code in TING_HELD_BACK:
            held.append(dict(quelle='Ting_Vials', code=code, spec=spec, usd=price, grund=TING_HELD_BACK[code]))
            continue
        if code in TING_MAP:
            target = by_row[TING_MAP[code]]
        elif code in TING_EXTRA_ML:
            name, dose = TING_EXTRA_ML[code]
            extras.append(dict(row=None, section='Gewichtsmanagement & Fettreduktion', name=name, dose=dose, num=10.0, unit='ml',
                               wholesale_eur=None, list_eur=None, ting_usd=price, ting_vis=visible, ting_codes=[code], code=code))
            trace.append(dict(liste='C', ref=code, angabe=spec, preis=f'${price}', ergebnis='als eigene Zeile übernommen', ziel=f'{name} {dose}'))
            continue
        elif code in TING_EXTRA:
            name, dose = TING_EXTRA[code]
            extras.append(dict(row=None, section='Weitere Produkte', name=name, dose=dose, num=float(dose.split()[0]), unit='mg',
                               wholesale_eur=None, list_eur=None, ting_usd=price, ting_vis=visible, ting_codes=[code], code=code))
            trace.append(dict(liste='C', ref=code, angabe=spec, preis=f'${price}', ergebnis='nur in dieser Liste, als eigene Zeile übernommen', ziel=f'{name} {dose}'))
            continue
        elif t.get('xrow'):
            target = by_row[t['xrow']]
        if target is None:
            held.append(dict(quelle='Ting_Vials', code=code, spec=spec, usd=price, grund='keine Zuordnung'))
            trace.append(dict(liste='C', ref=code, angabe=spec, preis=f'${price}', ergebnis='NICHT übernommen: keine Zuordnung', ziel=''))
            continue
        trace.append(dict(liste='C', ref=code, angabe=spec, preis=f'${price}', ergebnis='mit Produkt aus Liste A/B verglichen', ziel=f"{target['name']} {target['dose']}"))
        target['ting_usd'] = price if target['ting_usd'] is None else min(target['ting_usd'], price)
        target['ting_vis'] = visible if target.get('ting_vis') is None else min(target['ting_vis'], visible)  # in der Liste sichtbarer Preis
        target['ting_codes'] = sorted(set(target.get('ting_codes', []) + [code]))
    items += extras

    # collapse identical product/dose rows (supplier duplicates), keep the lowest price per source
    merged = {}
    for i in items:
        key = (i['section'], i['name'], i['dose'])
        if key in merged:
            m = merged[key]
            for k in ('wholesale_eur', 'list_eur', 'ting_usd', 'ting_vis'):
                vals = [v for v in (m.get(k), i.get(k)) if v is not None]
                m[k] = min(vals) if vals else None
            m.setdefault('dups', []).append(i['row'])
        else:
            merged[key] = dict(i)
    vials = []
    for m in merged.values():
        cands = []
        if m['wholesale_eur'] is not None:
            cands.append((m['wholesale_eur'], 'Wholesale-EUR-Liste'))
        if m['list_eur'] is not None:
            cands.append((m['list_eur'], 'EUR-Preisliste'))
        if m['ting_usd'] is not None:
            cands.append((usd_to_eur(m['ting_usd']), 'Ting-USD-Liste'))
        best, src = min(cands)
        m['best_eur'], m['best_source'] = best, src
        m['ting_eur'] = usd_to_eur(m['ting_usd']) if m['ting_usd'] is not None else None
        vials.append(m)

    # dual-chamber list: single source today
    sec_by_name = {}
    for v in vials:
        sec_by_name.setdefault(norm(v['name']).replace('-', ''), v['section'])
    dual, dual_held, trace_p = [], [], []
    seen = {}
    for p in pens:
        if p['flag'].startswith('Quelle: zweite KLOW'):  # same blend listed twice with two prices -> keep the cheaper one
            p = dict(p, name='KLOW (BPC-157 + TB-500 + GHK-Cu + KPV)', flag='Quelle: KLOW 80mg doppelt gelistet ($22/$17), günstigster Preis übernommen')
        label, num, unit = parse_spec(p['spec'])
        k = (p['name'], label)
        if k in seen:
            old = seen[k]
            keep = old if old['dual_usd'] <= p['dual_usd'] else dict(old, dual_usd=p['dual_usd'], single_usd=p['single_usd'], flag=p['flag'])
            dual[dual.index(old)] = keep
            seen[k] = keep
            trace_p.append(dict(liste='D', ref=p['code'], angabe=f"{p['name']} {p['spec']}", preis=f"${p['dual_usd']}", ergebnis='doppelt gelistet, günstigster Preis übernommen', ziel=f"{p['name']} {label}"))
            continue
        trace_p.append(dict(liste='D', ref=p['code'], angabe=f"{p['name']} {p['spec']}", preis=f"${p['dual_usd']}", ergebnis='übernommen', ziel=f"{p['name']} {label}"))
        row = dict(name=p['name'], dose=label, num=num, unit=unit, section=DUAL_SECTION.get(p['name'], 'Weitere Produkte'),
                   dual_usd=p['dual_usd'], dual_eur=usd_to_eur(p['dual_usd']), single_usd=p['single_usd'], flag=p['flag'], code=p['code'])
        dual.append(row)
        seen[k] = row
    out = dict(base_used=base_used, trace=trace_xlsx + trace + trace_p, rate=USD_PER_EUR, rate_date=RATE_DATE, vials=vials, dual=dual, held=held, dual_held=dual_held)
    (HERE / 'merged.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


if __name__ == '__main__':
    o = main()
    from collections import Counter
    print('vial rows', len(o['vials']), 'dual rows', len(o['dual']), 'held', len(o['held']), len(o['dual_held']))
    print('winner source', Counter(v['best_source'] for v in o['vials']))
    print('dual sections', Counter(d['section'] for d in o['dual']))
