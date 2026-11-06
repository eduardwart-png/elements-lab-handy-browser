from render_supplier import rows, load
from fill_prices import fill
r, log = fill(rows(load()))
print("rows", len(r), "est vial", sum(1 for e in log['est'] if e[0] == 'vial'), "est dual", sum(1 for e in log['est'] if e[0] == 'dual'))
print("struck dual cells", sum(len(v) for v in log['na_dual'].values()), "products", len(log['na_dual']), "| struck vial", log['na_vial'])
print("both empty", [x['name'] for x in r if x['vial'] is None and x['dual'] is None])
