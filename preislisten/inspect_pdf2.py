import pymupdf, collections
d = pymupdf.open("/Users/eduardwart/Desktop/Ting_Vials.pdf"); p = d[0]
clip = pymupdf.Rect(560, 400, 1280, 520)
p.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), clip=pymupdf.Rect(0, 395, 1280, 540)).save("/Users/eduardwart/.hermes/cache/scratch/preis/img/tv_crop.png")
# content-stream order of spans/drawings in the region of row y~423
items = []
for b in p.get_text("dict", sort=False)["blocks"]:
    for l in b.get("lines", []):
        for s in l["spans"]:
            if 410 < s["bbox"][1] < 440 and s["bbox"][0] > 950:
                items.append(("text", round(s["bbox"][0]), s["text"], hex(s["color"])))
print(items)
print([ (round(dr["rect"].x0), round(dr["rect"].y0), round(dr["rect"].x1), round(dr["rect"].y1), dr.get("fill")) for dr in p.get_drawings() if 405 < dr["rect"].y0 < 440 and dr["rect"].x1 > 900][:12])
t = p.get_text("words"); print([ (round(w[0]), round(w[1]), w[4]) for w in t if 410 < w[1] < 440])
