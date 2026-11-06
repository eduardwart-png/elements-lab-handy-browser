import json, re, statistics as st
lay = {c: (d, b) for c, d, b in json.load(open("quellen_extrahiert/ting_vials_layers.json"))}
t = json.load(open("quellen_extrahiert/ting_vials_roh.json"))
import openpyxl
W = openpyxl.load_workbook("/Users/eduardwart/Desktop/Wholesale EUR price.xlsx", data_only=True).active
E = openpyxl.load_workbook("/Users/eduardwart/Desktop/EUR PRICE.xlsx", data_only=True).active
rv, rh, rve, rhe = [], [], [], []
rows = []
for r in t:
    if not r.get('xrow') or r['code'] not in lay: continue
    d, b = lay[r['code']]
    if not d: continue
    vis = int(re.sub(r"\D", "", r['price'])); hid = d[0]
    w = W.cell(r['xrow'], 5).value; e = E.cell(r['xrow'], 5).value
    rows.append((r['code'], vis, hid, w, e))
    rv.append(vis / 1.1193 / w); rh.append(hid / 1.1193 / w)
print(len(rows))
print("visible/wholesale  median %.3f  stdev %.3f" % (st.median(rv), st.pstdev(rv)))
print("hidden/wholesale   median %.3f  stdev %.3f" % (st.median(rh), st.pstdev(rh)))
print("share |hidden-wholesale|<=5%%: %.0f%%   visible: %.0f%%" % (100*sum(abs(x-1)<=.05 for x in rh)/len(rh), 100*sum(abs(x-1)<=.05 for x in rv)/len(rv)))
for x in rows[:20]: print(x)
