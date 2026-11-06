import json, re, pymupdf, collections
d = pymupdf.open("/Users/eduardwart/Desktop/Ting_Vials.pdf"); p = d[0]
sp = []
for b in p.get_text("dict")["blocks"]:
    for l in b.get("lines", []):
        for s in l["spans"]:
            sp.append((s["bbox"][0], (s["bbox"][1] + s["bbox"][3]) / 2, s["text"], s["color"]))
codes = [(y, t) for x, y, t, c in sp if x < 260 and re.fullmatch(r"[A-Z0-9/\-]{2,12}", t) and not t.isalpha()]
prices = [(x, y, t, c) for x, y, t, c in sp if re.fullmatch(r"\$\d+", t)]
out = []
for y, code in sorted(codes):
    near = [(x, t, c) for x, yy, t, c in prices if abs(yy - y) < 9]
    dark = sorted({int(t[1:]) for x, t, c in near if c != 0}); blk = sorted({int(t[1:]) for x, t, c in near if c == 0})
    out.append((code, dark, blk))
print(len(out))
diff = [o for o in out if o[1] and o[2] and o[1] != o[2]]
lower = [o for o in diff if min(o[1]) < min(o[2])]
print("rows with differing hidden layer", len(diff), "of which hidden LOWER than visible", len(lower))
print(lower[:12]); print([o for o in diff if o not in lower][:8])
json.dump(out, open("quellen_extrahiert/ting_vials_layers.json", "w"))
