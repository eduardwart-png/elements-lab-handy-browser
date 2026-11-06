import pymupdf, re, json
f = "Elements Labs Einkaufsübersicht Vials und Doppelkammer.pdf"
d = pymupdf.open(f)
t = "\n".join(p.get_text() for p in d)
bad = re.compile(r"aupson|whatsapp|\+852|www\.|\.com|wholesale|ting|chinese|http|@|[\u4e00-\u9fff]", re.I)
print(d.page_count, "hits", sorted(set(m.group(0) for m in bad.finditer(t))), "je Kartusche" in t, "10er-Packung" in t)
o = json.load(open("merged.json"))
for nm, dose in (("Retatrutide", "10 mg"), ("Semaglutide", "10 mg"), ("Tirzepatide", "40 mg")):
    x = next(v for v in o["dual"] if v["name"] == nm and v["dose"] == dose)
    print(nm, dose, "USD", x["dual_usd"], "-> 10er EUR", round(x["dual_usd"] * 10 / o["rate"], 2))
d[0].get_pixmap(dpi=110).save("vorschau_seite1.png")
