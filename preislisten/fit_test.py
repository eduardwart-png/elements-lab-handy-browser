import json, statistics as st, math
from analyse_prices import DUAL_ALIAS, key, load
o = load(); R = o['rate']
vm = {key(v['name'], v['dose']): v for v in o['vials']}
P = []
for d in o['dual']:
    v = vm.get(key(DUAL_ALIAS.get(d['name'], d['name']), d['dose']))
    if v: P.append((d['name'], d['dose'], v['best_eur'] / 10, d['dual_usd'] / R, d['dual_usd'] / R - 0 ))
x = [p[2] for p in P]; y = [p[3] for p in P]
n = len(P); mx, my = st.mean(x), st.mean(y)
b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sum((a - mx) ** 2 for a in x); a0 = my - b * mx
res = [c - (a0 + b * a) for a, c in zip(x, y)]
print(n, "dual_eur = %.2f + %.3f * vial_per_vial_eur" % (a0, b), "MAE %.2f" % st.mean(abs(r) for r in res), "median dual %.2f" % st.median(y))
# log-log
lx = [math.log(a) for a in x]; ly = [math.log(c) for c in y]
mlx, mly = st.mean(lx), st.mean(ly)
bb = sum((a - mlx) * (c - mly) for a, c in zip(lx, ly)) / sum((a - mlx) ** 2 for a in lx); aa = mly - bb * mlx
rel = [abs(math.exp(aa + bb * a) - c) / c for a, c in zip(lx, y)]
print("loglog: dual = %.3f * vial^%.3f" % (math.exp(aa), bb), "median rel err %.0f%%" % (100 * st.median(rel)), "p90 %.0f%%" % (100 * sorted(rel)[int(0.9 * len(rel))]))
# dual price vs dose within product: step structure
by = {}
for d in o['dual']: by.setdefault(d['name'], []).append((d['num'], d['dual_usd'], d['single_usd']))
print({k: v for k, v in list(by.items())[:6]})
print("dual-single diff all 1:", all(d['dual_usd'] - d['single_usd'] == 1 for d in o['dual']))
