import json, re, collections, openpyxl, pymupdf
for f in ["Wholesale EUR price", "EUR PRICE"]:
    ws = openpyxl.load_workbook(f"/Users/eduardwart/Desktop/{f}.xlsx", data_only=True).worksheets[0]
    specs = collections.Counter(re.sub(r"[\d.,]+\s*(mg|iu|ml|mcg|g)?\s*", "", str(r[2]).lower()) for r in ws.iter_rows(min_row=3, values_only=True) if r[2])
    print(f, "spec patterns:", specs.most_common(8))
    print(" sections:", [r[0] for r in ws.iter_rows(values_only=True) if r[0] and r[1] is None and r[4] is None])
    print(" any dual/cartridge/pen words:", [r[:3] for r in ws.iter_rows(values_only=True) if any(w in " ".join(str(c).lower() for c in r if c) for w in ("dual", "cartridge", "pen", "chamber", "kartusche"))][:10])
for f in ["Ting_Vials", "Ting_Pens"]:
    d = pymupdf.open(f"/Users/eduardwart/Desktop/{f}.pdf")
    print(f, "pages", d.page_count, [p.rect for p in d][:3], "text chars", sum(len(p.get_text()) for p in d))
    t = "\n".join(p.get_text() for p in d)
    print(" words:", {w: len(re.findall(w, t, re.I)) for w in ("dual", "cartridge", "pen", "chamber", "single", "vial")})
    print(t[:600].replace("\n", " | "))
v = json.load(open("quellen_extrahiert/ting_vials_roh.json"))
print(len(v), v[:2])
print(collections.Counter(re.sub(r"[\d.,]+", "", str(x.get('spec', '')).lower()).strip() for x in v).most_common(10))
