"""Sortimentsergaenzung (Owner 24.10.2026): jedes Produkt und jede Dosis aus den Lieferantenlisten (merged.json), die das Verkaufsblatt nicht enthaelt,
wird als 10er-Pack in den Katalog aufgenommen. Ausnahme: Zubehoer (nur Bac. Water ist verkaeuflich). Ergebnis: sortiment_ergaenzung.json
(von miniapp/tools/catalog_lines.py gelesen). Der Verkaufspreis kommt wie bei allen Zeilen aus empfehlung.py (Platzhalter hier = 3 x Einkauf)."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'miniapp' / 'tools'))
import catalog_lines as cl  # noqa: E402
import ting_check as tc  # noqa: E402
from positionierung import canon  # noqa: E402

OUT = HERE / 'sortiment_ergaenzung.json'
SECTION = {'Kombinationssets': cl.SEC_BLEND, 'Weitere Produkte': cl.SEC_ORGAN, 'Regeneration & Reparatur': cl.SEC_REPAIR, 'Beauty & Anti-Aging': cl.SEC_BEAUTY,
           'Schlaf & Nervensystem': cl.SEC_NEURO, 'Hormone & Wachstum': cl.SEC_HORMONE, 'Immunsystem & Organregulation': cl.SEC_ORGAN,
           'Gewichtsmanagement & Fettreduktion': cl.SEC_WEIGHT}
SKIP_SECTIONS = {'Zubehör'}  # nur Bac. Water ist als Zubehoer verkaeuflich
NAME_FIX = {'HGH': 'HGH 191AA (Somatropin)', 'TB Frag': 'TB-500 Fragment', 'CJC-1295 + Ipamorelin': 'CJC-1295 (ohne DAC) + Ipamorelin', 'Botulinum toxin': 'Botulinum Toxin',
            'Sermorelin': 'Sermorelin Acetate', 'GHRP-2': 'GHRP-2 Acetate', 'GHRP-6': 'GHRP-6 Acetate', 'Hexarelin': 'Hexarelin Acetate', 'Oxytocin': 'Oxytocin Acetate',
            'Gonadorelin': 'Gonadorelin Acetate', 'Frag 17-23': 'Frag 17-23', 'MK677': 'MK-677'}


def ceil10(v):
    return int(-(-round(v, 6) // 10)) * 10


def split_blend(name, dose):
    x = re.match(r'^(.*?) \((\d+ mg \+ \d+ mg)\)$', name)
    if x:
        return x.group(1), f'{dose} ({x.group(2)})'
    return name, dose


def build():
    mg = json.loads((tc.HERE / 'merged.json').read_text())
    rate = mg['rate']
    sheet = cl.lines(recommend=False)
    sheet = [x for x in sheet if not x.get('supplement')]
    # Abdeckung: Katalogzeile (Form, Dosis) -> aufgeloeste Lieferantenzeilen
    covered = set()
    sec_by_name = {}
    disp_by_canon = {}
    for x in sheet:
        sec_by_name.setdefault(x['name'], x['section'])
        disp_by_canon.setdefault(canon(x['name']), x['name'])
        d = tc.dose_of(x['strength'])
        target = tc.ALIAS.get((x['form'], x['name']), x['name'])
        covered.add((x['form'], d, target))
        covered.add((x['form'], d, canon(target)))
    out, seen = [], {(x['form'], x['name'], x['strength']) for x in sheet}
    for form, key in (('vial', 'vials'), ('dual', 'dual')):
        for v in mg[key]:
            if v.get('section') in SKIP_SECTIONS:
                continue
            d = tc.dose_of(v['dose'])
            if d is None:
                continue
            if (form, d, v['name']) in covered or (form, d, canon(v['name'])) in covered or (form, d, canon(NAME_FIX.get(v['name'], v['name']))) in covered:
                continue
            if form == 'vial':
                cands = [x for x in (v.get('ting_vis') and v['ting_vis'] / rate, v.get('wholesale_eur'), v.get('list_eur')) if x]
                ek = v['ting_vis'] / rate if v.get('ting_vis') else (min(x for x in (v.get('wholesale_eur'), v.get('list_eur')) if x) if cands else None)
            else:
                ek = v['dual_usd'] * 10 / rate
            if ek is None:
                continue
            name, strength = split_blend(NAME_FIX.get(v['name'], v['name']), v['dose'])
            name = disp_by_canon.get(canon(name), name)  # gleiche Substanz wie im Verkaufsblatt: dessen Schreibweise und Abschnitt uebernehmen
            kk = (form, name, strength)
            if kk in seen:
                continue
            seen.add(kk)
            section = sec_by_name.get(name) or SECTION[v['section']]
            out.append(dict(form=form, name=name, strength=strength, section=section, code=v.get('code') or ('X' + str(len(out))), price_cents=ceil10(3 * ek) * 100, supplement=True))
    order = {s: i for i, s in enumerate(cl.SECTIONS)}
    out.sort(key=lambda r: (r['form'] != 'vial', order[r['section']], r['name'], tc.dose_of(r['strength'])))
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == '__main__':
    rows = build()
    print(len(rows), 'Ergaenzungszeilen (Vial', sum(r['form'] == 'vial' for r in rows), '/ Dual', sum(r['form'] == 'dual' for r in rows), ')')
    for r in rows:
        print(' ', r['form'], '|', r['name'], '|', r['strength'], '|', r['section'][:18], '|', r['price_cents'] // 100)
