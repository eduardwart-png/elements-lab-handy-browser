import pymupdf, re, json, plistlib, base64
d = pymupdf.open("/Users/eduardwart/Desktop/Ting_Pens.pdf"); p = d[0]
out = []
for a in p.annots():
    obj = d.xref_object(a.xref, compressed=False)
    m = re.search(r"/AAPL:AKAnnotationObject \((.*?)\)\s*/", obj, re.S)
    raw = obj
    strings = []
    mm = re.search(r"/AAPL:AKAnnotationObject \(([A-Za-z0-9+/=\s]+)\)", obj)
    if mm:
        try:
            pl = plistlib.loads(base64.b64decode(mm.group(1)))
            objs = pl["$objects"]
            strings = [o for o in objs if isinstance(o, str) and len(o) < 200 and not o.startswith(("NS", "AK", "$", "should", "text", "typing", "original", "foreground", "rotation", "stroke", "Helvetica"))]
            # attributed text may be RTF bytes
            for o in objs:
                if isinstance(o, (bytes, bytearray)) and (o[:5] == b"{\\rtf" or b"rtf" in o[:20]):
                    strings.append("RTF:" + o.decode("latin1")[:400])
        except Exception as e:
            strings = ["ERR " + repr(e)]
    out.append((round(a.rect.y0), round(a.rect.x0), round(a.rect.x1), strings))
for o in out[:6]: print(o)
json.dump(out, open("quellen_extrahiert/ting_pens_annots_decoded.json", "w"), indent=1, ensure_ascii=False)
print(len(out))
