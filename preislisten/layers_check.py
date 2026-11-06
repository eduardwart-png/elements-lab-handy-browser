import json, re, pymupdf, collections
d = pymupdf.open("/Users/eduardwart/Desktop/Ting_Vials.pdf"); p = d[0]
rows = collections.defaultdict(list)
for b in p.get_text("dict")["blocks"]:
    for l in b.get("lines", []):
        for s in l["spans"]:
            if re.fullmatch(r"\$\d+", s["text"]):
                rows[round(s["bbox"][1])].append((s["text"], s["color"]))
t = json.load(open("quellen_extrahiert/ting_vials_roh.json"))
ys = sorted(rows)
print(len(ys), len(t))
low = high = same = 0; ex = []
for y, r in zip(ys, t):
    ls = rows[y]
    dark = [int(x[0][1:]) for x in ls if x[1] != 0]
    vis = int(re.sub(r"\D", "", r['price']))
    if dark:
        if dark[0] < vis: low += 1; ex.append((r['code'], dark[0], vis))
        elif dark[0] > vis: high += 1
        else: same += 1
print("hidden dark layer: lower than visible", low, "higher", high, "same", same)
print(ex[:10])
