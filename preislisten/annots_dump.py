import pymupdf, re, json
d = pymupdf.open("/Users/eduardwart/Desktop/Ting_Pens.pdf"); p = d[0]
res = []
for a in p.annots():
    ap = d.xref_get_key(a.xref, "AP/N")
    xr = int(ap[1].split()[0]) if ap[0] == "xref" else None
    s = d.xref_stream(xr).decode("latin1") if xr else ""
    txt = re.findall(r"\((.*?)\)\s*Tj|\[(.*?)\]\s*TJ", s)
    res.append(dict(y=round(a.rect.y0, 1), x=round(a.rect.x0, 1), x1=round(a.rect.x1, 1), y1=round(a.rect.y1, 1), stream=s[:300], txt=txt, mod=d.xref_get_key(a.xref, "M")[1]))
json.dump(res, open("quellen_extrahiert/ting_pens_annots_raw.json", "w"), indent=1)
print(len(res))
for r in res[:5]: print(r)
print(res[-1])
print("rect x range", min(r['x'] for r in res), max(r['x1'] for r in res), "y range", min(r['y'] for r in res), max(r['y1'] for r in res))
