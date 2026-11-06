"""Analysis of the merged supplier lists (internal; neutral list labels A-D, no supplier identity)."""
import json
import re
import statistics as st
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent

DUAL_ALIAS = {  # cartridge name -> vial-list name (only where it is the same substance)
    'Oxytocin (Pharma-Qualität)': 'Oxytocin', 'Oxytocin (Industriequalität)': 'Oxytocin',
    'TB-500 (Full-Length)': 'TB-500', 'TB-500 Fragment': 'TB Frag',
    'Melanotan I': 'Melanotan I/II', 'Melanotan II': 'Melanotan I/II',
    'CJC-1295 (ohne DAC) + Ipamorelin (5 mg + 5 mg)': 'CJC-1295 + Ipamorelin',
    'Thymosin Alpha-1': 'Thymosin Alpha-1', 'LL-37': 'LL-37',
}


def key(name, dose):
    return (re.sub(r'[^a-z0-9+]', '', name.lower()), dose)


def load():
    return json.loads((HERE / 'merged.json').read_text())


def compute(o):
    V, D = o['vials'], o['dual']
    r = {}
    # coverage
    r['rows'] = dict(A=sum(1 for v in V if v['wholesale_eur'] is not None), B=sum(1 for v in V if v['list_eur'] is not None),
                     C=sum(1 for v in V if v['ting_usd'] is not None), D=len(D) + len(o['dual_held']), final_vials=len(V), final_dual=len(D))
    r['products'] = len({v['name'] for v in V})
    both = [v for v in V if v['wholesale_eur'] is not None and v['ting_usd'] is not None]
    r['matched_AC'] = len(both)
    r['only_C'] = [(v['name'], v['dose']) for v in V if v['wholesale_eur'] is None]
    r['only_AB'] = sum(1 for v in V if v['ting_usd'] is None)
    # price levels
    ratio_ba = [v['list_eur'] / v['wholesale_eur'] for v in V if v['list_eur'] and v['wholesale_eur']]
    r['B_vs_A'] = dict(min=min(ratio_ba), median=st.median(ratio_ba), max=max(ratio_ba), n=len(ratio_ba))
    ratio_ca = [v['ting_eur'] / v['wholesale_eur'] for v in both]
    r['C_vs_A'] = dict(min=min(ratio_ca), median=st.median(ratio_ca), max=max(ratio_ca), n=len(ratio_ca),
                       cheaper=sum(1 for x in ratio_ca if x < 0.999), equal=sum(1 for x in ratio_ca if 0.999 <= x <= 1.001),
                       dearer=sum(1 for x in ratio_ca if x > 1.001))
    # savings: one pack of every dose
    ab = [v for v in V if v['wholesale_eur'] is not None]
    r['sum_A'] = sum(v['wholesale_eur'] for v in ab)
    r['sum_B'] = sum(v['list_eur'] for v in ab)
    r['sum_best_ab'] = sum(v['best_eur'] for v in ab)
    r['saving_vs_A'] = r['sum_A'] - r['sum_best_ab']
    r['saving_vs_B'] = r['sum_B'] - r['sum_best_ab']
    by_cat = defaultdict(lambda: dict(n=0, A=0.0, best=0.0, c_wins=0))
    for v in ab:
        c = by_cat[v['section']]
        c['n'] += 1
        c['A'] += v['wholesale_eur']
        c['best'] += v['best_eur']
        c['c_wins'] += v['best_source'].startswith('Ting')
    r['by_cat'] = {k: dict(v, saving=v['A'] - v['best'], pct=(v['A'] - v['best']) / v['A'] * 100) for k, v in by_cat.items()}
    # biggest single savings
    sv = sorted(((v['wholesale_eur'] - v['best_eur'], v) for v in ab if v['best_eur'] < v['wholesale_eur']), key=lambda x: -x[0])
    r['top_savings'] = [(round(s, 2), v['name'], v['dose'], v['wholesale_eur'], v['best_eur']) for s, v in sv[:12]]
    r['wins_C'] = len(sv)
    # vial vs cartridge
    vmap = {key(v['name'], v['dose']): v for v in V}
    pairs = []
    for d in D:
        vn = DUAL_ALIAS.get(d['name'], d['name'])
        v = vmap.get(key(vn, d['dose']))
        if v:
            per_vial = v['best_eur'] / 10
            pairs.append(dict(section=d['section'], name=d['name'], dose=d['dose'], vial_pack=v['best_eur'], per_vial=per_vial,
                              cartridge=d['dual_eur'], single_usd=d['single_usd'], premium=d['dual_eur'] / per_vial - 1))
    r['pairs'] = pairs
    r['dual_without_vial'] = [(d['name'], d['dose']) for d in D if key(DUAL_ALIAS.get(d['name'], d['name']), d['dose']) not in vmap]
    r['vial_without_dual'] = len({v['name'] for v in V}) - len({DUAL_ALIAS.get(d['name'], d['name']) for d in D if key(DUAL_ALIAS.get(d['name'], d['name']), d['dose']) in vmap})
    if pairs:
        pr = [p['premium'] for p in pairs]
        r['premium'] = dict(n=len(pr), median=st.median(pr), mean=st.mean(pr), min=min(pr), max=max(pr),
                            cheaper=sum(1 for x in pr if x < 0))
    # price per mg
    pm = defaultdict(list)
    for v in V:
        if v['unit'] == 'mg' and v['num'] > 0:
            pm[v['name']].append((v['num'], v['best_eur'], v['best_eur'] / v['num']))
    r['per_mg'] = {n: sorted(x) for n, x in pm.items() if len(x) >= 2}
    # anomalies: monotonic
    anomalies = []
    byp = defaultdict(list)
    for v in V:
        byp[(v['name'], v['unit'])].append(v)
    for (name, unit), rs in byp.items():
        rs.sort(key=lambda x: x['num'])
        for lo, hi in zip(rs, rs[1:]):
            if lo['best_eur'] > hi['best_eur'] + 1e-9:
                anomalies.append(dict(liste='Vials', name=name, lo=lo['dose'], plo=lo['best_eur'], hi=hi['dose'], phi=hi['best_eur'],
                                      lo_src=lo['best_source'], hi_src=hi['best_source']))
    byd = defaultdict(list)
    for d in D:
        byd[(d['name'], d['unit'])].append(d)
    for (name, unit), rs in byd.items():
        rs.sort(key=lambda x: x['num'])
        for lo, hi in zip(rs, rs[1:]):
            if lo['dual_eur'] > hi['dual_eur'] + 1e-9:
                anomalies.append(dict(liste='Doppelkammer', name=name, lo=lo['dose'], plo=lo['dual_eur'], hi=hi['dose'], phi=hi['dual_eur'], lo_src='D', hi_src='D'))
    r['anomalies'] = anomalies
    big = [(v['name'], v['dose'], v['wholesale_eur'], v['ting_eur']) for v in both if v['ting_eur'] / v['wholesale_eur'] < 0.7 or v['ting_eur'] / v['wholesale_eur'] > 1.6]
    r['outliers_C'] = big
    return r


if __name__ == '__main__':
    r = compute(load())
    for k in ('rows', 'products', 'matched_AC', 'only_AB', 'B_vs_A', 'C_vs_A', 'sum_A', 'sum_B', 'sum_best_ab', 'saving_vs_A', 'saving_vs_B', 'wins_C', 'premium', 'vial_without_dual'):
        print(k, r.get(k))
    print('only_C', r['only_C'])
    print('by_cat', {k: (round(v['pct'], 1), v['n']) for k, v in r['by_cat'].items()})
    print('top', r['top_savings'][:6])
    print('pairs', len(r['pairs']), 'dual without vial', r['dual_without_vial'])
    print('anomalies', len(r['anomalies']), [(a['liste'], a['name'], a['lo'], a['hi']) for a in r['anomalies']])
    print('outliers C', len(r['outliers_C']), r['outliers_C'][:8])
