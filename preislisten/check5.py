import pymupdf, re
f = "Elements Labs Einkaufsübersicht Vials und Doppelkammer.pdf"
d = pymupdf.open(f)
t = "\n".join(p.get_text() for p in d)
bad = re.compile(r"aupson|whatsapp|\+852|www\.|\.com|wholesale|ting|chinese|http|@|[\u4e00-\u9fff]|einzel", re.I)
print(d.page_count, "hits", sorted(set(m.group(0) for m in bad.finditer(t))))
d[0].get_pixmap(dpi=110).save("vorschau_seite1.png")
d[d.page_count - 1].get_pixmap(dpi=70).save("/Users/eduardwart/.hermes/cache/scratch/preis/img/sl.png")
