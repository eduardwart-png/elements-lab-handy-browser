from render_supplier import rows, load
from fill_prices import fill, model_fill
o = load(); step = round(10 / o['rate'], 2)
allr, log = fill(rows(o))
for r in allr:
    if r.get('dual_est') and r['dual'] is not None and 'single' not in r:
        r['single'] = round(r['dual'] - step, 2); r['single_est'] = True
allr, log = model_fill(allr, log, step)
print(log['model'])
print("ladder est", len(log['est']), "modelled", len(log['modelled']), "struck products", len(log['na_dual']), "struck rows", sum(len(v) for v in log['na_dual'].values()))
viol = [(n, d, p) for n, d, p in log['modelled'] if any(r['dose'] == d and (r.get('alias') or r['name']) == n and r['vial'] and p < r['vial'] for r in allr)]
print("modelled where dual10 < vial10:", len(viol), viol[:12])
print("rows with dual but no single:", [(r['name'], r['dose']) for r in allr if r.get('dual') is not None and r.get('single') is None][:10])
print("struck:", sorted(log['na_dual']))
