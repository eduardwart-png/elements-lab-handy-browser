import pymupdf
d = pymupdf.open("Elements Labs Einkaufsübersicht Vials und Doppelkammer.pdf")
print(d.page_count)
o = "/Users/eduardwart/.hermes/cache/scratch/preis/img/"
d[0].get_pixmap(dpi=90).save(o + "s0.png"); d[1].get_pixmap(dpi=80).save(o + "s1.png"); d[d.page_count - 1].get_pixmap(dpi=80).save(o + "sl.png")
