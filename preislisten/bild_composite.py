"""Composite product image: Elements Labs vial | dual-chamber cartridge + pen, on white, from the shop's own product images."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
from scipy import ndimage as ndi

ASSET = Path('/Users/eduardwart/Projekte-Mac/elements-lab-telegram/miniapp/public/assets/products')
OUT = Path(__file__).resolve().parent / 'bild'


def cutout(path, tol=22, soft=2.0):
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(float)
    h, w, _ = a.shape
    # local background estimate: median of a thin frame, gradient-aware via blurred border fill
    border = np.concatenate([a[:6].reshape(-1, 3), a[-6:].reshape(-1, 3), a[:, :6].reshape(-1, 3), a[:, -6:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    dist = np.sqrt(((a - bg) ** 2).sum(axis=2))
    # use colour distance to a per-pixel background built by row/col interpolation of the border
    top, bot = a[:6].mean(axis=0), a[-6:].mean(axis=0)
    left, right = a[:, :6].mean(axis=1), a[:, -6:].mean(axis=1)
    ys = np.linspace(0, 1, h)[:, None, None]
    xs = np.linspace(0, 1, w)[None, :, None]
    bgmap = 0.5 * ((1 - ys) * top[None] + ys * bot[None]) + 0.5 * ((1 - xs) * left[:, None, :] + xs * right[:, None, :])
    dist = np.sqrt(((a - bgmap) ** 2).sum(axis=2))
    fg = dist > tol
    fg = ndi.binary_closing(fg, iterations=3)
    fg = ndi.binary_fill_holes(fg)
    lab, n = ndi.label(fg)
    if n > 1:
        sizes = ndi.sum(fg, lab, range(1, n + 1))
        keep = [i + 1 for i, s in enumerate(sizes) if s > 0.15 * max(sizes)]
        fg = np.isin(lab, keep)
    fg = ndi.binary_opening(fg, iterations=2)
    m = Image.fromarray((fg * 255).astype('uint8')).filter(ImageFilter.GaussianBlur(soft))
    rgba = im.copy()
    rgba.putalpha(m)
    box = rgba.getchannel('A').point(lambda v: 255 if v > 40 else 0).getbbox()
    return rgba.crop(box)


def shadow(size, w, h):
    s = Image.new('L', size, 0)
    d = ImageDraw.Draw(s)
    d.ellipse((size[0] / 2 - w / 2, size[1] / 2 - h / 2, size[0] / 2 + w / 2, size[1] / 2 + h / 2), fill=90)
    return s.filter(ImageFilter.GaussianBlur(h / 2.2))


if __name__ == '__main__':
    import sys
    tol = float(sys.argv[1]) if len(sys.argv) > 1 else 22
    items = {'vial': cutout(ASSET / 'retatrutide-10-vial.webp', tol), 'dual': cutout(ASSET / 'dual-chamber/retatrutide-10.webp', tol),
             'pen': cutout(ASSET / 'reusable-pen.webp', tol)}
    for k, v in items.items():
        print(k, v.size)
        bgw = Image.new('RGB', v.size, 'white')
        bgw.paste(v, mask=v.getchannel('A'))
        bgw.save(OUT / f'cut_{k}.png')
