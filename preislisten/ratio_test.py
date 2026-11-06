import json, collections, statistics as st
from analyse_prices import DUAL_ALIAS, key, load
o = load()
vm = {key(v['name'], v['dose']): v for v in o['vials']}
rows = []
for d in o['dual']:
    v = vm.get(key(DUAL_ALIAS.get(d['name'], d['name']), d['dose']))
    if v and v.get('ting_usd'):
        rows.append((d['name'], d['dose'], d['dual_usd'], d['single_usd'], v['ting_usd'], v['ting_usd'] / 10, d['dual_usd'] / (v['ting_usd'] / 10)))
print(len(rows), "pairs with Ting vial price")
print(collections.Counter(round(r[6], 2) for r in rows).most_common(12))
for r in rows[:25]: print(r)
nm = [r for r in rows if abs(r[6] - 2) > 0.05]
print("not exactly 2x:", len(nm))
for r in nm[:25]: print(r)
