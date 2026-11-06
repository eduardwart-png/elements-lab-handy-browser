from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
B = Path(__file__).resolve().parent / 'bild'
vial, dual, pen = (Image.open(B / f'rb_{k}.png') for k in ('vial', 'dual', 'pen'))
def tidy(im):
    a = im.getchannel('A').filter(ImageFilter.MinFilter(3))
    a = a.point(lambda x: 0 if x < 24 else x)
    im = im.copy(); im.putalpha(a)
    return im.crop(a.point(lambda x: 255 if x > 100 else 0).getbbox())
vial, dual, pen = tidy(vial), tidy(dual), tidy(pen)
sc = lambda im, h: im.resize((round(im.width * h / im.height), h), Image.LANCZOS)
v, d, p = sc(vial, 760), sc(dual, 640), sc(pen, 700)
W, H, base = 1500, 1040, 840
yy = np.linspace(0, 1, H)[:, None]
bg = np.zeros((H, W, 3), dtype=float)
top, bot = np.array([250, 251, 252.]), np.array([228, 234, 237.])
bg[:] = top + (bot - top) * (yy ** 1.4)[:, :, None]
img = Image.fromarray(bg.astype('uint8'))

def shadow(im, cx):
    s = Image.new('L', (W, H), 0)
    ImageDraw.Draw(s).ellipse((cx - im.width * 0.5, base - 6, cx + im.width * 0.5, base + 12), fill=130)
    near = s.filter(ImageFilter.GaussianBlur(7))
    s2 = Image.new('L', (W, H), 0)
    ImageDraw.Draw(s2).ellipse((cx - im.width * 0.95, base - 22, cx + im.width * 0.95, base + 40), fill=70)
    far = s2.filter(ImageFilter.GaussianBlur(26))
    for m in (far, near):
        img.paste(Image.new('RGB', (W, H), (95, 110, 118)), mask=m)

def place(im, cx):
    shadow(im, cx)
    img.paste(im, (round(cx - im.width / 2), base - im.height), im)

cv, cd, cp = 500, 970, 1120
place(v, cv); place(d, cd); place(p, cp)
f = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 38)
fb = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 38, index=1)
dr = ImageDraw.Draw(img)
def cap(txt, cx, y=905):
    w = dr.textlength(txt, font=fb)
    dr.text((cx - w / 2, y), txt, font=fb, fill=(23, 32, 39))
    hw = dr.textlength(txt, font=fb) / 2
    dr.line((cx - hw, y + 58, cx + hw, y + 58), fill=(13, 91, 107), width=5)
cap('Vial', cv)
cap('Doppelkammer + Pen', (cd + cp) / 2)
img.save(B / 'elements_labs_produktbild.png', optimize=True)
print(img.size)
