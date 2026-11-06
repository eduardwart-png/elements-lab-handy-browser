import pymupdf, re
d = pymupdf.open("Elements Labs Einkaufsübersicht Vials und Doppelkammer.pdf")
t = "\n".join(p.get_text() for p in d)
print(d.page_count, re.findall(r"SLU-PP-332 \([^)]*\)", t), "stars", t.count("*"))
bad = re.compile(r"aupson|whatsapp|\+852|www\.|\.com|wholesale|ting|chinese|http|@|[\u4e00-\u9fff]", re.I)
print("hits", sorted(set(m.group(0) for m in bad.finditer(t))))
d[1].get_pixmap(dpi=85).save("/Users/eduardwart/.hermes/cache/scratch/preis/img/s1.png")
d[0].get_pixmap(dpi=110).save("vorschau_seite1.png")
