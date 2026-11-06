import pymupdf, collections, json
for f in ["Ting_Vials", "Ting_Pens"]:
    d = pymupdf.open(f"/Users/eduardwart/Desktop/{f}.pdf"); p = d[0]
    an = list(p.annots() or [])
    print("==", f, "annots", len(an), collections.Counter(a.type[1] for a in an), "images", len(p.get_images()), "ocgs", d.get_ocgs() if hasattr(d, "get_ocgs") else None, "fonts", [x[3] for x in p.get_fonts()][:5])
    print(" contents streams", len(p.get_contents()), "drawings", len(p.get_drawings()))
    for a in an[:6]:
        print("  ", a.type, [round(x) for x in a.rect], a.info.get("content", "")[:80], a.colors)
d = pymupdf.open("/Users/eduardwart/Desktop/Ting_Vials.pdf"); p = d[0]
w = [x for x in p.get_text("words") if x[4].startswith("$")]
print("price words", len(w))
rows = collections.defaultdict(list)
for x in w: rows[round(x[1] / 4)].append((round(x[0]), x[4]))
for k in sorted(rows)[:8]: print(k, sorted(rows[k]))
# text colours / sizes of price spans
spans = []
for b in p.get_text("dict")["blocks"]:
    for l in b.get("lines", []):
        for s in l["spans"]:
            if s["text"].startswith("$"): spans.append((round(s["bbox"][1]), s["text"], hex(s["color"]), round(s["size"], 1), s["font"]))
print(sorted(spans)[:14])
print(collections.Counter((s[2], s[3]) for s in spans))
