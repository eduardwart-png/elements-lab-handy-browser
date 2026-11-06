import json
from PIL import Image
r = json.load(open("quellen_extrahiert/ting_pens_zeilen.json"))
im = Image.open("/Users/eduardwart/.hermes/cache/scratch/preis/img/pens_orig.png")
pairs = [("BC5", "BC10"), ("G25", "G210"), ("MS20", "MS40")]
ml = [i for i, x in enumerate(r) if x['code'] == 'ML10']
print("ML10 idx", ml, [(x['name'], x['spec'], x['y']) for x in r if x['code'] in ('ML10',)])
out = []
for a, b in pairs:
    ya = next(x['y'] for x in r if x['code'] == a); 
    c = im.crop((0, ya - 130, im.width, ya + 260)); c = c.resize((1800, int(c.height * 1800 / c.width)))
    c.save(f"/Users/eduardwart/.hermes/cache/scratch/preis/img/gap_{a}.png"); print(a, ya)
i = ml[0]; ya = r[i]['y']
c = im.crop((0, ya - 130, im.width, ya + 360)); c = c.resize((1800, int(c.height * 1800 / c.width))); c.save("/Users/eduardwart/.hermes/cache/scratch/preis/img/gap_ML10.png")
