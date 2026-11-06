import pymupdf, re, plistlib, base64
d = pymupdf.open("/Users/eduardwart/Desktop/Ting_Pens.pdf"); p = d[0]
a = list(p.annots())[0]
obj = d.xref_object(a.xref, compressed=False)
print(re.sub(r"\(([A-Za-z0-9+/=\s]{200,})\)", "(<b64>)", obj)[:1500])
mm = re.search(r"/AAPL:AKAnnotationObject \(([A-Za-z0-9+/=\s]+)\)", obj)
pl = plistlib.loads(base64.b64decode(mm.group(1)))
for i, o in enumerate(pl["$objects"]):
    s = repr(o)
    print(i, type(o).__name__, s[:160])
