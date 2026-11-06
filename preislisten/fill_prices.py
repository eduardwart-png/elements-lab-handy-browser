"""Fehlende Preise nach der Preisstaffel des jeweiligen Produkts ergänzen; Produkte ohne Staffel als nicht bestellbar markieren."""
from collections import defaultdict

num = lambda r: float(r['dose'].split()[0].replace(',', '.'))
disp = lambda r: r.get('alias') or r['name']


def estimate(points, x):
    """points: sorted [(dose, price)], >=2. Linear between neighbours; outside the range slope of the nearest segment."""
    pts = sorted(points)
    lo = [p for p in pts if p[0] < x]
    hi = [p for p in pts if p[0] > x]
    if lo and hi:
        (x0, y0), (x1, y1) = lo[-1], hi[0]
        y = y0 + (y1 - y0) * (x - x0) / (x1 - x0)
        return round(min(max(y, min(y0, y1)), max(y0, y1)), 2)
    if hi:  # below range
        (x0, y0), (x1, y1) = hi[0], hi[1]
        slope = max((y1 - y0) / (x1 - x0), 0)
        return round(max(y0 - slope * (x0 - x), 0.6 * y0), 2)
    (x0, y0), (x1, y1) = lo[-2], lo[-1]  # above range
    slope = (y1 - y0) / (x1 - x0)
    if slope <= 0 and len(lo) >= 3:
        slope = (lo[-2][1] - lo[-3][1]) / (lo[-2][0] - lo[-3][0])
    return round(y1 + max(slope, 0) * (x - x1), 2)


def fill(rows):
    # Melanotan: the vial list has one 'I/II' line; both cartridge lines get that vial price
    mel = next((r for r in rows if r['name'] == 'Melanotan I/II'), None)
    if mel:
        for r in rows:
            if r['name'] in ('Melanotan I', 'Melanotan II') and r['vial'] is None:
                r['vial'] = mel['vial']
        rows.remove(mel)
    log = dict(est=[], na_vial=[], na_dual=defaultdict(list))
    for col, other in (('vial', 'dual'), ('dual', 'vial')):
        groups = defaultdict(list)
        for r in rows:
            groups[r['name']].append(r)
        for name, rs in groups.items():
            known = [(num(r), r[col]) for r in rs if r[col] is not None]
            for r in rs:
                if r[col] is not None:
                    continue
                if len(known) >= 2:
                    r[col] = estimate(known, num(r))
                    r[col + '_est'] = True
                    log['est'].append((col, disp(r), r['dose'], r[col]))
                else:
                    r[col + '_na'] = True
                    (log['na_vial'].append((disp(r), r['dose'])) if col == 'vial' else log['na_dual'][disp(r)].append(r['dose']))
    return rows, log


NOT_CARTRIDGE = {'Bacteriostatisches Wasser', 'Essigsäure', 'Lemon Bottle', 'Botulinum toxin', 'EPO', 'HGH', 'HMG', 'Vitamin B12', 'L-Carnitin',
                 'Cerebrolysin', 'Dulaglutide', 'Follistatin 344', 'GDF-8', 'MIC (Lipo-C mit B12)'}


def model_fill(rows, log, step):
    """Cartridge price for products the cartridge list does not contain: fitted from all products that have both a vial and a
    cartridge price (dual = a * (vial price per vial)^b, per single cartridge); results are per 10 and flagged as calculated."""
    import math, statistics as st
    pts = [(r['vial'] / 10, r['dual'] / 10) for r in rows if r['vial'] is not None and r['dual'] is not None and not r.get('dual_est')]
    lx = [math.log(a) for a, _ in pts]; ly = [math.log(b) for _, b in pts]
    mx, my = st.mean(lx), st.mean(ly)
    b = sum((x - mx) * (y - my) for x, y in zip(lx, ly)) / sum((x - mx) ** 2 for x in lx)
    a = math.exp(my - b * mx)
    rel = sorted(abs(a * (x / 1) ** b - y) / y for x, y in ((math.exp(u), math.exp(v)) for u, v in zip(lx, ly)))
    log['model'] = dict(a=a, b=b, n=len(pts), median_err=rel[len(rel) // 2], p90_err=rel[int(len(rel) * 0.9)])
    log['modelled'], struck = [], defaultdict(list)
    for r in rows:
        if r.get('dual_na'):
            name = disp(r)
            if r['vial'] is None or r['name'] in NOT_CARTRIDGE or r['section'] in ('Zubehör',) or r['name'].startswith('Lipo-C'):
                struck[name].append(r['dose'])
                continue
            r['dual'] = round(10 * a * (r['vial'] / 10) ** b, 2)
            if r['dual'] < r['vial']:  # Vial bleibt günstiger als Doppelkammer
                r['dual'] = round(r['vial'] * 1.05, 2)
                log.setdefault('floored', []).append((name, r['dose']))
            r['dual_est'] = True
            r['dual_na'] = False
            r['single'] = round(r['dual'] - step, 2)
            r['single_est'] = True
            log['modelled'].append((name, r['dose'], r['dual']))
    log['na_dual'] = struck
    return rows, log
