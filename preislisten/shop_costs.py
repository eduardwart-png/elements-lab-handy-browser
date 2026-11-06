"""Interne Einkaufspreise je Shop-Produkt (10er-Vial / 10er-Doppelkammer) aus der Lieferanten-Übersicht. Nie öffentlich."""
import json
from pathlib import Path
import render_supplier

HERE = Path(__file__).resolve().parent
SHOP = HERE.parent / 'miniapp'
# shop id -> (row name as in the supplier overview, dose label)
MAP = {
 'retatrutide-10': ('Retatrutide', '10 mg'), 'retatrutide-20': ('Retatrutide', '20 mg'), 'retatrutide-30': ('Retatrutide', '30 mg'),
 'tirzepatide-10': ('Tirzepatide', '10 mg'), 'tirzepatide-20': ('Tirzepatide', '20 mg'), 'tirzepatide-30': ('Tirzepatide', '30 mg'),
 'semaglutide-10': ('Semaglutide', '10 mg'), 'semaglutide-20': ('Semaglutide', '20 mg'), 'semaglutide-30': ('Semaglutide', '30 mg'),
 'bpc-157': ('BPC-157', '10 mg'), 'tb-500': ('TB-500', '10 mg'), 'bpc-157-tb-500': ('BPC-157 + TB-500 (10 mg + 10 mg)', '20 mg'),
 'cjc-1295-no-dac': ('CJC-1295 (ohne DAC)', '10 mg'), 'ipamorelin': ('Ipamorelin', '10 mg'),
 'ghk-cu-50': ('GHK-Cu', '50 mg'), 'ghk-cu-100': ('GHK-Cu', '100 mg'),
 'mots-c-10': ('MOTS-c', '10 mg'), 'mots-c-20': ('MOTS-c', '20 mg'), 'mots-c-40': ('MOTS-c', '40 mg'),
 'nad-plus-500': ('NAD+', '500 mg'), 'nad-plus-1000': ('NAD+', '1000 mg'),
 '5-amino-1mq': ('5-Amino-1MQ', '50 mg'), 'epithalon': ('Epithalon', '50 mg'), 'selank': ('Selank', '10 mg'), 'semax': ('Semax', '10 mg'),
}

if __name__ == '__main__':
    rows = render_supplier.build()
    idx = {}
    for r in rows:
        idx.setdefault((r['name'], r['dose']), r)
        if r.get('alias'): idx.setdefault((r['alias'], r['dose']), r)
    out, miss = {}, []
    for pid, key in MAP.items():
        r = idx.get(key)
        if r is None:
            cands = sorted({(x['name'], x['dose']) for x in rows if x['name'].split()[0].lower() == key[0].split()[0].lower()})
            miss.append((pid, key, cands[:12])); continue
        out[pid] = dict(vial10_eur=r['vial'], dual10_eur=r['dual'], dual_calculated=bool(r.get('dual_est')), vial_calculated=bool(r.get('vial_est')))
    for m in miss: print('MISSING', m)
    (HERE / 'shop_costs.json').write_text(json.dumps(out, indent=1))
    print(len(out), 'mapped', sum(1 for v in out.values() if v['dual10_eur'] is None), 'without dual')
    for k, v in out.items(): print(k, v)
