import json
from PIL import Image
rows = json.load(open("quellen_extrahiert/ting_pens_zeilen.json"))
print(len(rows), rows[0])
im = Image.open("/Users/eduardwart/.hermes/cache/scratch/preis/img/pens_orig.png")
H = im.height
n = 8
step = H // n
for i in range(n):
    y0, y1 = max(0, i * step - 30), min(H, (i + 1) * step + 30)
    c = im.crop((0, y0, im.width, y1))
    c = c.resize((1700, int(c.height * 1700 / c.width)))
    c.save(f"/Users/eduardwart/.hermes/cache/scratch/preis/img/vchk_{i}.png")
print(H)
