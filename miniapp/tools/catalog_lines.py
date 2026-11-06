"""Verkaufsblatt des Inhabers (10er-Katalogpreise, Vial und Doppelkammer) als Shop-Katalog.

Preise stehen exakt wie im PDF (preislisten/verkaufsblatt_parsed.json, erzeugt von parse_verkaufsblatt.py). Nur Schreibweisen der Namen werden
bereinigt, Abschnitte nach Substanz zugeordnet (die Abschnittsbalken im PDF sind gegen die Zeilen versetzt). Identische Doppelzeilen
(Bac. Water/WA, KLOW/KLOW80) erscheinen einmal.
"""
import json
import re
from pathlib import Path

PARSED = Path(__file__).resolve().parents[2] / 'preislisten' / 'verkaufsblatt_parsed.json'

SEC_WEIGHT, SEC_REPAIR, SEC_BEAUTY, SEC_NEURO, SEC_HORMONE, SEC_ORGAN, SEC_BLEND, SEC_SUPPLY = (
    'Gewichtsmanagement & Fettreduktion', 'Regeneration & Reparatur', 'Beauty & Anti-Aging', 'Schlaf & Nervensystem', 'Hormone & Wachstum',
    'Immunsystem & Organregulation', 'Peptid-Blends', 'Lösungsmittel & Ergänzungen')
SECTIONS = [SEC_WEIGHT, SEC_REPAIR, SEC_BEAUTY, SEC_NEURO, SEC_HORMONE, SEC_ORGAN, SEC_BLEND, SEC_SUPPLY]

# raw name in the PDF -> (display name, section)
NAMES = {
    'Semaglutide': ('Semaglutide', SEC_WEIGHT), 'Tirzepatide': ('Tirzepatide', SEC_WEIGHT), 'Retatrutide': ('Retatrutide', SEC_WEIGHT),
    'Mazdutide': ('Mazdutide', SEC_WEIGHT), 'Liraglutide': ('Liraglutide', SEC_WEIGHT), 'Cagrilintide': ('Cagrilintide', SEC_WEIGHT),
    'AOD9605': ('AOD-9604', SEC_WEIGHT), 'AOD9604': ('AOD-9604', SEC_WEIGHT), 'Adipotide/FTTP': ('Adipotide (FTTP)', SEC_WEIGHT),
    'L-carnitine': ('L-Carnitine', SEC_WEIGHT), 'Lemon Bottle': ('Lemon Bottle', SEC_WEIGHT), 'Lipo-c': ('Lipo-C', SEC_WEIGHT),
    'MOTS-C': ('MOTS-c', SEC_WEIGHT), 'MOTS-c': ('MOTS-c', SEC_WEIGHT), 'SLU-PP-322': ('SLU-PP-322', SEC_WEIGHT),
    'Cagrisema (2.5mg+2.5mg)': ('CagriSema (2,5 mg + 2,5 mg)', SEC_WEIGHT), '5-Amino-1mq': ('5-Amino-1MQ', SEC_WEIGHT), '5Amino/MQ': ('5-Amino-1MQ', SEC_WEIGHT),
    'Survodutide': ('Survodutide', SEC_WEIGHT), 'Aicar': ('AICAR', SEC_WEIGHT), 'Matrixyl': ('Matrixyl', SEC_BEAUTY),
    'HGH -191AA(Somatropin);': ('HGH 191AA (Somatropin)', SEC_HORMONE),
    'BPC157': ('BPC-157', SEC_REPAIR), 'BPC 157': ('BPC-157', SEC_REPAIR), 'TB500': ('TB-500', SEC_REPAIR), 'TB 500 Fragment': ('TB-500 Fragment', SEC_REPAIR),
    'TB 500 Full-Length': ('TB-500 (Full-Length)', SEC_REPAIR), 'GHK-CU': ('GHK-Cu', SEC_REPAIR), 'GHK-Cu': ('GHK-Cu', SEC_REPAIR),
    'Tesamorelin': ('Tesamorelin', SEC_REPAIR), 'Sermorelin Acetate': ('Sermorelin Acetate', SEC_REPAIR), 'Sermorelin': ('Sermorelin Acetate', SEC_REPAIR),
    'IGF-1 LR3': ('IGF-1 LR3', SEC_REPAIR), 'IGF-1LR3': ('IGF-1 LR3', SEC_REPAIR),
    'Epithalon': ('Epithalon', SEC_BEAUTY), 'NP810/SNAP8': ('Snap-8', SEC_BEAUTY), 'SS-31': ('SS-31', SEC_BEAUTY),
    'GT/GTT/Glutathione': ('Glutathione', SEC_BEAUTY), 'Glutathione': ('Glutathione', SEC_BEAUTY), 'NAD': ('NAD+', SEC_BEAUTY),
    'DSIP': ('DSIP', SEC_NEURO), 'Selank': ('Selank', SEC_NEURO), 'Semax': ('Semax', SEC_NEURO), 'Dihexa': ('Dihexa', SEC_NEURO),
    'Oxytocin Acetate': ('Oxytocin Acetate', SEC_NEURO), 'Oxytocin Acetate - Pharmaceutical Grade': ('Oxytocin Acetate (Pharmaceutical Grade)', SEC_NEURO),
    'Oxytocin Acetate - Industrial Grade': ('Oxytocin Acetate (Industrial Grade)', SEC_NEURO),
    'G25': ('GHRP-2 Acetate', SEC_HORMONE), 'GHRP-2 Acetate': ('GHRP-2 Acetate', SEC_HORMONE), 'G65': ('GHRP-6 Acetate', SEC_HORMONE),
    'GHRP-6 Acetate': ('GHRP-6 Acetate', SEC_HORMONE), 'Ipamorelin': ('Ipamorelin', SEC_HORMONE),
    'CJC 1295 with DAC': ('CJC-1295 (mit DAC)', SEC_HORMONE), 'CJC-1295 With DAC': ('CJC-1295 (mit DAC)', SEC_HORMONE),
    'CJC 1295(without DAC)': ('CJC-1295 (ohne DAC)', SEC_HORMONE), 'CJC-1295 Without DAC': ('CJC-1295 (ohne DAC)', SEC_HORMONE),
    'Kisspetin-10': ('Kisspeptin-10', SEC_HORMONE), 'KissPeptin-10': ('Kisspeptin-10', SEC_HORMONE), 'HCG': ('HCG', SEC_HORMONE), 'HG75/HMG': ('HMG', SEC_HORMONE),
    'FRAG': ('HGH Fragment 176-191 (FRAG)', SEC_HORMONE), 'Gonadorelin Acetate': ('Gonadorelin Acetate', SEC_HORMONE),
    'Thymalin': ('Thymalin', SEC_ORGAN), 'Thymosin alpha 1': ('Thymosin Alpha-1', SEC_ORGAN), 'Thymosin Alpha-1': ('Thymosin Alpha-1', SEC_ORGAN),
    'LL375': ('LL-37', SEC_ORGAN), 'KK37': ('LL-37', SEC_ORGAN), 'Hexarelin Acetate': ('Hexarelin Acetate', SEC_ORGAN), 'KPV': ('KPV', SEC_ORGAN),
    'VIP5': ('VIP', SEC_ORGAN), 'VIP10': ('VIP', SEC_ORGAN), 'VIP': ('VIP', SEC_ORGAN), 'ARA290': ('ARA-290', SEC_ORGAN), 'Ara-290': ('ARA-290', SEC_ORGAN),
    'E3K': ('EPO', SEC_ORGAN), 'AHK-CU': ('AHK-Cu', SEC_ORGAN), 'P41/PT141': ('PT-141', SEC_ORGAN), 'PT-141': ('PT-141', SEC_ORGAN),
    'Melanotan I': ('Melanotan I (MT-1)', SEC_ORGAN), 'MT-1 (Melanotan 1 Acetate)': ('Melanotan I (MT-1)', SEC_ORGAN),
    'Melanotan II': ('Melanotan II (MT-2)', SEC_ORGAN), 'MT-2 (Melanotan 1 Acetate)': ('Melanotan II (MT-2)', SEC_ORGAN),  # PDF-Tippfehler "MT-2 (Melanotan 1 ...)"
    'F410': ('FOXO4-DRI', SEC_ORGAN), 'FOXO4-DRI': ('FOXO4-DRI', SEC_ORGAN), 'Vilon': ('Vilon', SEC_ORGAN), 'Adamax': ('Adamax', SEC_ORGAN),
    'ACE 031': ('ACE-031', SEC_BLEND), 'FMP2': ('FMP2', SEC_BLEND),
    'BPC5mg + TB5mg': ('BPC-157 + TB-500', SEC_BLEND), 'GLOW (TB10+BP10+GHK50)': ('GLOW (BPC-157 + TB-500 + GHK-Cu)', SEC_BLEND),
    'BPC157 10mg+GHK-cu50mg+TB500 10mg': ('GLOW (BPC-157 + TB-500 + GHK-Cu)', SEC_BLEND),
    'KLOW (TB10+BPC10+GHK50+KPV10)': ('KLOW (BPC-157 + TB-500 + GHK-Cu + KPV)', SEC_BLEND),
    'BPC157 10mg+TB500 10mg+GHKcu50mg+KPV10 mg': ('KLOW (BPC-157 + TB-500 + GHK-Cu + KPV)', SEC_BLEND), 'KLOW': ('KLOW (BPC-157 + TB-500 + GHK-Cu + KPV)', SEC_BLEND),
    'CP10': ('CJC-1295 (ohne DAC) + Ipamorelin', SEC_BLEND), 'CJC-1295 Without DAC 5mg+Ipamorelin 5mg': ('CJC-1295 (ohne DAC) + Ipamorelin', SEC_BLEND),
    'B-12/B12': ('Vitamin B12', SEC_SUPPLY), 'Bac. Water (Bacteriostatic Water)': ('Bacteriostatic Water', SEC_SUPPLY), 'WA (Bacteriostatic Water)': ('Bacteriostatic Water', SEC_SUPPLY),
}
STRENGTH_FIX = {  # sonst wird die Staerke im PDF mit Zusatz gedruckt
    ('BPC-157 + TB-500', '10 mg'): '10 mg (5 mg + 5 mg)', ('BPC-157 + TB-500', '20 mg'): '20 mg (10 mg + 10 mg)',
    ('GLOW (BPC-157 + TB-500 + GHK-Cu)', '70 mg'): '70 mg (10 + 50 + 10)', ('KLOW (BPC-157 + TB-500 + GHK-Cu + KPV)', '80 mg'): '80 mg (10 + 10 + 50 + 10)',
    ('CJC-1295 (ohne DAC) + Ipamorelin', '10 mg'): '10 mg (5 mg + 5 mg)',
}

# Shop-Produkt -> (Vial-Zeile, Doppelkammer-Zeile) als (Anzeigename, Staerke); None = nicht im Verkaufsblatt
MATCH = {}
for _n, _doses in (('retatrutide', (10, 20, 30)), ('tirzepatide', (10, 20, 30, 40)), ('semaglutide', (10, 15, 20, 30))):
    for _d in _doses:
        MATCH[f'{_n}-{_d}'] = ((_n.capitalize(), f'{_d} mg'),) * 2
MATCH.update({
    'bpc-157': (('BPC-157', '10 mg'),) * 2,
    'tb-500': (('TB-500', '10 mg'), ('TB-500 (Full-Length)', '10 mg')),
    'bpc-157-tb-500': (('BPC-157 + TB-500', '20 mg (10 mg + 10 mg)'), None),
    'cjc-1295-no-dac': (('CJC-1295 (ohne DAC)', '10 mg'),) * 2,
    'ipamorelin': (('Ipamorelin', '10 mg'),) * 2,
    'ghk-cu-50': (('GHK-Cu', '50 mg'),) * 2, 'ghk-cu-100': (('GHK-Cu', '100 mg'),) * 2,
    'mots-c-10': (('MOTS-c', '10 mg'),) * 2, 'mots-c-20': (('MOTS-c', '20 mg'),) * 2, 'mots-c-40': (('MOTS-c', '40 mg'),) * 2,
    'nad-plus-500': (('NAD+', '500 mg'),) * 2, 'nad-plus-1000': (('NAD+', '1000 mg'),) * 2,
    '5-amino-1mq': (('5-Amino-1MQ', '50 mg'),) * 2, 'epithalon': (('Epithalon', '50 mg'),) * 2,
    'selank': (('Selank', '10 mg'),) * 2, 'semax': (('Semax', '10 mg'),) * 2,
})


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower().replace('+', 'plus')).strip('-')


def tidy_strength(s):
    s = re.sub(r'\s+', ' ', s.replace('iu', 'IU')).strip()
    return s.replace('0.1 mg', '0,1 mg').replace('0.5 mg', '0,5 mg')


def _dose(s):
    m = re.match(r'\s*([\d.,]+)\s*([A-Za-z]+)', s)
    return (m.group(2).lower(), float(m.group(1).replace(',', '.'))) if m else ('', 0.0)


def _supplement_slot(out, item):
    """Einfuegestelle fuer eine Ergaenzungszeile: neben die Zeilen derselben Substanz (nach Dosis sortiert), sonst ans Ende des Abschnitts."""
    unit, dose = _dose(item['strength'])
    same = [i for i, x in enumerate(out) if x['form'] == item['form'] and x['name'] == item['name']]
    if same:
        for i in same:
            u, d = _dose(out[i]['strength'])
            if u == unit and d > dose:
                return i
        return same[-1] + 1
    sec = [i for i, x in enumerate(out) if x['form'] == item['form'] and x['section'] == item['section']]
    return sec[-1] + 1 if sec else len(out)


ADJUST = PARSED.parent / 'markt_10er.json'
SUPPLEMENT = PARSED.parent / 'sortiment_ergaenzung.json'
RECOMMEND = PARSED.parent / 'preisempfehlung.json'


def lines(adjusted=True, recommend=True):
    """Katalogzeilen in PDF-Reihenfolge (Vial zuerst), dedupliziert.

    adjusted=False: exakt alte Verkaufsliste (Blatt + Ergaenzung), unveraendert.
    adjusted=True (Standard): Packpreise der Preisfamilie v3 fuer alle Zeilen (preisempfehlung.json aus empfehlung.py).
    adjusted=True, recommend=False: nur Analyse-Zwischenstand (markt_10er.json) fuer positionierung.py/ting_check.py.
    """
    rows = json.loads(PARSED.read_text())
    out, seen = [], {}
    for r in rows:
        raw = 'HGH -191AA(Somatropin);' if r['name'].startswith('HGH') else r['name']
        name, section = NAMES[raw]
        strength = tidy_strength(r['strength'])
        if r['code'] == 'CP10' and r['form'] == 'vial':
            strength = '10 mg'
        strength = STRENGTH_FIX.get((name, strength), strength)
        if name == 'Lipo-C':
            name = f"Lipo-C ({r['code'][2:]})"
        if r['code'] in ('BB10', 'BB20') or name == 'BPC-157 + TB-500':
            pass
        key = (r['form'], name, strength)
        if key in seen:
            if seen[key]['price_cents'] != r['price_cents']:
                raise ValueError(f'Doppelzeile mit anderem Preis: {key}')
            continue  # identische Zeile
        item = dict(form=r['form'], name=name, strength=strength, section=section, code=r['code'], price_cents=r['price_cents'], order=len(out))
        seen[key] = item
        out.append(item)
    if SUPPLEMENT.is_file():  # Sortimentsergaenzung (Owner 24.10.2026): alles aus den Lieferantenlisten, was das Verkaufsblatt nicht enthaelt
        for r in json.loads(SUPPLEMENT.read_text()):
            key = (r['form'], r['name'], r['strength'])
            if key in seen:
                continue
            item = dict(form=r['form'], name=r['name'], strength=r['strength'], section=r['section'], code=r['code'], price_cents=r['price_cents'], order=len(out), supplement=True)
            seen[key] = item
            out.insert(_supplement_slot(out, item), item)
        for i, x in enumerate(out):
            x['order'] = i
    if adjusted and ADJUST.is_file():
        new = {(r['name'], r['strength']): round(r['new_eur'] * 100) for r in json.loads(ADJUST.read_text())}
        for x in out:
            if x['form'] == 'vial' and (x['name'], x['strength']) in new:
                x['owner_price_cents'], x['price_cents'] = x['price_cents'], new[(x['name'], x['strength'])]
    if adjusted and recommend and RECOMMEND.is_file():  # Preisebene = Preisfamilie v3 (preislisten/preisfamilie_v3.csv ueber empfehlung.py), setzt alle 340 Zeilen
        recs = json.loads(RECOMMEND.read_text())
        rec = {(r['form'], r['name'], r['strength']): round(r['price_eur'] * 100) for r in recs}
        ok = {(r['form'], r['name'], r['strength']): bool(r.get('discount_ok')) for r in recs}
        missing = [(x['form'], x['name'], x['strength']) for x in out if (x['form'], x['name'], x['strength']) not in rec]
        if missing or len(rec) != len(recs):
            raise ValueError(f'preisempfehlung.json deckt den Katalog nicht ab (fehlt {missing[:5]}) oder hat Doppelzeilen')
        for x in out:
            key = (x['form'], x['name'], x['strength'])
            x['discount_ok'] = ok.get(key, False)
            if key in rec and rec[key] != x['price_cents']:
                x.setdefault('owner_price_cents', x['price_cents'])
                x['price_cents'] = rec[key]
    return out


def money(cents):
    return f'{cents // 100},{cents % 100:02d} €'.replace('.', '')


if __name__ == '__main__':
    ls = lines()
    print(len(ls), sum(x['form'] == 'vial' for x in ls), sum(x['form'] == 'dual' for x in ls))
    index = {(x['form'], x['name'], x['strength']): x for x in ls}
    for pid, (v, d) in MATCH.items():
        for form, ref in (('vial', v), ('dual', d)):
            if ref and (form, *ref) not in index:
                print('KEIN TREFFER', pid, form, ref)
