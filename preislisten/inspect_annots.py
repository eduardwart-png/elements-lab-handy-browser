import pymupdf, collections, json
d = pymupdf.open("/Users/eduardwart/Desktop/Ting_Pens.pdf"); p = d[0]
an = list(p.annots())
out = []
for a in an:
    x = d.xref_object(a.xref, compressed=False)
    out.append((round(a.rect.y0), round(a.rect.x0), a.info.get("content"), a.info.get("subject"), a.get_text() if hasattr(a, "get_text") else None))
print(out[:5])
import re
print(d.xref_object(an[0].xref, compressed=False)[:900])
