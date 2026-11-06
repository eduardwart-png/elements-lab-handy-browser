import pymupdf, re, plistlib, base64, json
d = pymupdf.open("/Users/eduardwart/Desktop/Ting_Pens.pdf"); p = d[0]
a = list(p.annots())[0]
obj = d.xref_object(a.xref, compressed=False)
mm = re.search(r"/AAPL:AKAnnotationObject \(([A-Za-z0-9+/=\s]+)\)", obj)
pl = plistlib.loads(base64.b64decode(mm.group(1)))
o = pl["$objects"]
print(o[1])
for i in range(30, len(o)): print(i, repr(o[i])[:300])
