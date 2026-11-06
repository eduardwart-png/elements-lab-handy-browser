from PIL import Image
im = Image.open("/Users/eduardwart/.hermes/cache/scratch/preis/img/pens_orig.png")
c = im.crop((0, 560, im.width, 1000)); c = c.resize((1800, int(c.height * 1800 / c.width))); c.save("/Users/eduardwart/.hermes/cache/scratch/preis/img/pens_hdr.png")
c = im.crop((0, 8000, im.width, 8900)); c = c.resize((1800, int(c.height * 1800 / c.width))); c.save("/Users/eduardwart/.hermes/cache/scratch/preis/img/pens_end.png")
