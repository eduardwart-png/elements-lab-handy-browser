import pymupdf, re
f = "Elements Labs Einkaufsübersicht Vials und Doppelkammer.pdf"
d = pymupdf.open(f)
print(d.page_count)
d[0].get_pixmap(dpi=90).save("/Users/eduardwart/.hermes/cache/scratch/preis/img/sup0.png")
d[3].get_pixmap(dpi=70).save("/Users/eduardwart/.hermes/cache/scratch/preis/img/sup3.png")
t = "\n".join(p.get_text() for p in d)
bad = re.compile(r"aupson|whatsapp|\+852|www\.|\.com|wholesale|ting|chinese|http|@|[\u4e00-\u9fff]", re.I)
print("hits", sorted(set(m.group(0) for m in bad.finditer(t))), d.metadata["author"], d.metadata["title"])
