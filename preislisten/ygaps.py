import json, collections
r = json.load(open("quellen_extrahiert/ting_pens_zeilen.json"))
ys = [x['y'] for x in r]
g = [b - a for a, b in zip(ys, ys[1:])]
print("sorted?", ys == sorted(ys), "median gap", sorted(g)[len(g)//2], collections.Counter(g).most_common(5))
big = [(r[i]['code'], r[i+1]['code'], g[i]) for i in range(len(g)) if g[i] > 1.3 * sorted(g)[len(g)//2]]
print("bigger gaps (section bands or missing rows):", len(big)); print(big)
print("first y", ys[0], "last y", ys[-1])
