from __future__ import annotations

import base64
import json
import math
import random
from pathlib import Path
from textwrap import dedent

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from PIL import ImageChops

ROOT = Path('C:/Users/eduar/elements-lab-flagship')
ASSETS = ROOT / 'assets'
LOGOS = ASSETS / 'logos'
PRODUCTS_DIR = ASSETS / 'products'
SCENES = ASSETS / 'scenes'
BASE = ASSETS / 'base-photos-final'
for p in [ASSETS, LOGOS, PRODUCTS_DIR, SCENES, ROOT / 'qa', ROOT / 'evidence', ROOT / 'evidence' / 'screenshots']:
    p.mkdir(parents=True, exist_ok=True)

GRAPHITE = '#2A2F36'
NEAR_BLACK = '#0D1115'
OFF_WHITE = '#F7F7F8'
PETROL = '#0D5B6B'
MUTED = '#6B747D'
LINE = '#D8DDE0'

IMG_DIR = ROOT / 'img'
IMG_DIR.mkdir(parents=True, exist_ok=True)


def write_qr_codes(products):
    import qrcode
    for p in products:
        qr_path = ROOT / p['qr']
        qr_path.parent.mkdir(parents=True, exist_ok=True)
        payload = f"https://eduardwart-png.github.io/elements-lab-handy-browser/#batch={p['batch']}"
        img = qrcode.make(payload, border=2)
        img = img.resize((300, 300))
        img.save(qr_path)

PRODUCTS = [
    dict(id='bpc-157', num='01', name='BPC-157', concentration='5 mg', price='24,90 €', code='EL-BPC-005', batch='EL-BPC5-26001', category='Tissue Research', featured=True, desc='Batch-orientierte In-vitro-Forschungsware für Tissue-Biology-Modelle.'),
    dict(id='tb-500', num='02', name='TB-500', concentration='5 mg', price='36,90 €', code='EL-TB5-005', batch='EL-TB5-26001', category='Tissue Research', featured=False, desc='Research Compound für analytische Laborbetrachtung zellulärer Bewegungsmodelle.'),
    dict(id='ghk-cu', num='03', name='GHK-Cu', concentration='50 mg', price='27,90 €', code='EL-GHK-050', batch='EL-GHK50-26001', category='Copper Peptide', featured=True, desc='Kupferbindendes Tripeptid für dokumentierte Forschungs- und Materialanalyse.'),
    dict(id='ipamorelin', num='04', name='Ipamorelin', concentration='5 mg', price='27,90 €', code='EL-IPA-005', batch='EL-IPA5-26001', category='Endocrine Research', featured=False, desc='Research Compound für Rezeptor- und Signalmodell-Systeme im Laborumfeld.'),
    dict(id='kpv', num='05', name='KPV', concentration='10 mg', price='36,90 €', code='EL-KPV-010', batch='EL-KPV10-26001', category='Tripeptide Research', featured=True, desc='Tripeptid für In-vitro-Research-Informationen mit klarer Chargenführung.'),
    dict(id='selank', num='06', name='Selank', concentration='5 mg', price='27,90 €', code='EL-SEL-005', batch='EL-SEL5-26001', category='Neuropeptide Research', featured=False, desc='Heptapeptid für neurochemische Forschungsmodelle ohne Human-Use-Kommunikation.'),
    dict(id='semax', num='07', name='Semax', concentration='5 mg', price='27,90 €', code='EL-SMX-005', batch='EL-SMX5-26001', category='Neuropeptide Research', featured=False, desc='Research Compound für Laborstudien an Peptid- und Signalpfad-Modellen.'),
    dict(id='mots-c', num='08', name='MOTS-C', concentration='10 mg', price='36,90 €', code='EL-MOT-010', batch='EL-MOT10-26001', category='Mitochondrial Research', featured=True, desc='Mitochondrialer Research-Kontext für analytische Zellmodell-Dokumentation.'),
    dict(id='cjc-1295-no-dac', num='09', name='CJC-1295 No DAC', concentration='5 mg', price='36,90 €', code='EL-CJC-005', batch='EL-CJC5-26001', category='Endocrine Research', featured=False, desc='No-DAC Research Compound für strukturierte Rezeptor- und Signalmodell-Prüfung.'),
    dict(id='nad-plus', num='10', name='NAD+', concentration='500 mg', price='44,90 €', code='EL-NAD-500', batch='EL-NAD500-26001', category='Cofactor Research', featured=True, desc='Cofactor-Research-Produkt mit technischer Chargen- und Produktcodierung.'),
    dict(id='5-amino-1mq', num='11', name='5-Amino-1MQ', concentration='5 mg', price='54,90 €', code='EL-AMQ-005', batch='EL-AMQ5-26001', category='Metabolic Research', featured=True, desc='Premium-nahes Research Compound für Labor- und Stoffwechselmodell-Kontexte.'),
    dict(id='bpc-157-tb-500', num='12', name='BPC-157 + TB-500', concentration='5 mg + 5 mg', price='46,90 €', code='EL-BT-010', batch='EL-BT10-26001', category='Research Bundle', featured=True, desc='Kombinierte Research-Ware für einheitliche Tissue-Research-Portfolioführung.'),
    dict(id='epithalon', num='13', name='Epithalon', concentration='50 mg', price='94,90 €', code='EL-EPI-050', batch='EL-EPI50-26001', category='Longevity Research', featured=True, desc='Premium-Anker im Sortiment für dokumentierte Labor- und Peptidmodell-Analyse.'),
]

for product in PRODUCTS:
    product['image'] = f'assets/products/{product["id"]}-vial.png'
    product['detailImage'] = f'assets/products/{product["id"]}-detail.png'
    product['macroImage'] = 'assets/scenes/macro-detail.png'
    product['packagingImage'] = 'assets/scenes/packaging-shot.png'
    product['qr'] = f'img/qr-{product["batch"]}.png'


def rgb(hex_color: str):
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgba(hex_color: str, a: int = 255):
    return (*rgb(hex_color), a)


def font(size: int, bold: bool = False, mono: bool = False):
    candidates = []
    if mono:
        candidates += ['C:/Windows/Fonts/CascadiaMono.ttf', 'C:/Windows/Fonts/consola.ttf']
    if bold:
        candidates += ['C:/Windows/Fonts/segoeuib.ttf', 'C:/Windows/Fonts/arialbd.ttf']
    candidates += ['C:/Windows/Fonts/segoeui.ttf', 'C:/Windows/Fonts/arial.ttf']
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def text_center(draw: ImageDraw.ImageDraw, xy, text, fnt, fill, anchor='mm'):
    draw.text(xy, text, font=fnt, fill=fill, anchor=anchor)


def linear_gradient(size, top, bottom):
    w, h = size
    img = Image.new('RGBA', size)
    draw = ImageDraw.Draw(img)
    t = rgb(top); b = rgb(bottom)
    for y in range(h):
        k = y / max(1, h - 1)
        col = tuple(int(t[i] * (1 - k) + b[i] * k) for i in range(3)) + (255,)
        draw.line([(0, y), (w, y)], fill=col)
    return img


def add_noise(img: Image.Image, amount=9, alpha=18):
    w, h = img.size
    noise = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    px = noise.load()
    for _ in range(int(w * h * amount / 9000)):
        x = random.randrange(w); y = random.randrange(h)
        v = random.randrange(255)
        px[x, y] = (v, v, v, random.randrange(0, alpha))
    return Image.alpha_composite(img.convert('RGBA'), noise)


def draw_el_mark(d: ImageDraw.ImageDraw, x, y, s, dark=True, img=None):
    """Draw the TRUE Eddy-approved EL monogram: traced 1:1 from the approved
    reference image (faceted E made of three angled chevron bars with a
    notched cut, faceted L with a leaning vertical stroke and chevron foot).
    Coordinates below are the exact traced polygon vertices from the
    reference logo, normalized to a 1200x1080 box and scaled to (x,y,s).
    Pass `img` (the RGBA image `d` draws on) to properly punch the small
    transparent notch hole in the E; without it the hole is skipped."""
    ink_e = rgba(OFF_WHITE, 255) if dark else rgba(GRAPHITE, 255)
    ink_l = rgba(PETROL, 255)

    REF_W, REF_H = 1200.0, 1080.0
    e_poly = [(583,79),(225,307),(227,801),(553,1022),(660,946),(344,739),(336,631),(572,473),(577,342),(344,475),(338,377),(583,214)]
    l_poly = [(715,136),(603,215),(604,870),(661,917),(960,724),(948,587),(718,726)]
    hole_poly = [(576,604),(568,600),(388,718),(384,730),(470,791),(487,790),(575,726)]

    def to_canvas(poly):
        return [(x + (px / REF_W) * s, y + (py / REF_H) * s) for px, py in poly]

    d.polygon(to_canvas(e_poly), fill=ink_e)
    d.polygon(to_canvas(l_poly), fill=ink_l)

    if img is not None:
        # Punch the notch hole as true transparency (works regardless of the
        # underlying background — logo canvas, label panel, box front, etc.)
        hole_canvas = to_canvas(hole_poly)
        mask = Image.new('L', img.size, 0)
        ImageDraw.Draw(mask).polygon(hole_canvas, fill=255)
        clear = Image.new('RGBA', img.size, (0, 0, 0, 0))
        img.paste(clear, (0, 0), mask)
    else:
        d.polygon(to_canvas(hole_poly), fill=rgba(OFF_WHITE, 255))


def el_mark_svg_path(s=100):
    """SVG path data for the traced EL monogram (two colored polygons + a notch
    hole), scaled into a 0..s coordinate box. {e} and {l} are format placeholders
    for the two fill colors."""
    REF_W, REF_H = 1200.0, 1080.0
    e_poly = [(583,79),(225,307),(227,801),(553,1022),(660,946),(344,739),(336,631),(572,473),(577,342),(344,475),(338,377),(583,214)]
    l_poly = [(715,136),(603,215),(604,870),(661,917),(960,724),(948,587),(718,726)]
    hole_poly = [(576,604),(568,600),(388,718),(384,730),(470,791),(487,790),(575,726)]

    def pts(poly):
        return ' '.join(f'{(px/REF_W)*s:.2f},{(py/REF_H)*s:.2f}' for px, py in poly)

    e_id = f'elmaske{int(s*1000)}'
    return (
        f'<defs><mask id="{e_id}"><rect x="0" y="0" width="{s:.2f}" height="{s:.2f}" fill="white"/>'
        f'<polygon points="{pts(hole_poly)}" fill="black"/></mask></defs>'
        f'<polygon points="{pts(e_poly)}" fill="{{e}}" mask="url(#{e_id})"/>'
        f'<polygon points="{pts(l_poly)}" fill="{{l}}"/>'
    )


def logo_svg(kind='primary', dark=False):
    """kind: primary (icon+wordmark horizontal, ~230px wide for desktop header),
    secondary (icon over wordmark stacked), icon (mark only, for mobile), badge (seal)."""
    ink = OFF_WHITE if dark else GRAPHITE
    mark_e = OFF_WHITE if dark else GRAPHITE
    mark_l = PETROL
    mark_size = 100

    if kind == 'icon':
        w, h = 140, 140
        mx, my = 20, 20
        mark = el_mark_svg_path(mark_size).format(e=mark_e, l=mark_l)
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<g transform="translate({mx} {my})">{mark}</g>
</svg>'''

    if kind == 'secondary':
        w, h = 360, 260
        mx = (w - mark_size) / 2
        my = 20
        mark = el_mark_svg_path(mark_size).format(e=mark_e, l=mark_l)
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<g transform="translate({mx:.1f} {my})">{mark}</g>
<text x="{w/2}" y="182" text-anchor="middle" font-family="'Space Grotesk','Segoe UI',Arial,sans-serif" font-size="30" font-weight="700" letter-spacing="6" fill="{ink}">ELEMENTS</text>
<text x="{w/2}" y="216" text-anchor="middle" font-family="'Space Grotesk','Segoe UI',Arial,sans-serif" font-size="30" font-weight="700" letter-spacing="6" fill="{ink}">LABS</text>
</svg>'''

    if kind == 'badge':
        w, h = 280, 280
        mark_size2 = 84
        mx = (w - mark_size2) / 2
        my = 56
        mark = el_mark_svg_path(mark_size2).format(e=mark_e, l=mark_l)
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<circle cx="{w/2}" cy="{h/2}" r="128" fill="none" stroke="{PETROL}" stroke-width="2"/>
<g transform="translate({mx:.1f} {my})">{mark}</g>
<text x="{w/2}" y="206" text-anchor="middle" font-family="'Space Grotesk','Segoe UI',Arial,sans-serif" font-size="19" font-weight="700" letter-spacing="4" fill="{ink}">ELEMENTS</text>
<text x="{w/2}" y="230" text-anchor="middle" font-family="'Space Grotesk','Segoe UI',Arial,sans-serif" font-size="19" font-weight="700" letter-spacing="4" fill="{ink}">LABS</text>
</svg>'''

    w, h = 620, 160
    mx, my = 26, 30
    mark = el_mark_svg_path(mark_size).format(e=mark_e, l=mark_l)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<g transform="translate({mx} {my})">{mark}</g>
<text x="166" y="76" font-family="'Space Grotesk','Segoe UI',Arial,sans-serif" font-size="40" font-weight="700" letter-spacing="7" fill="{ink}">ELEMENTS</text>
<text x="166" y="120" font-family="'Space Grotesk','Segoe UI',Arial,sans-serif" font-size="40" font-weight="700" letter-spacing="7" fill="{ink}">LABS</text>
</svg>'''


def logo_png(path: Path, kind='primary', dark=False):
    svg_map = {'icon': (280, 280), 'secondary': (720, 520), 'badge': (720, 720), 'primary': (1240, 320)}
    size = svg_map.get(kind, (1240, 320))
    scale = size[0] / {'icon': 140, 'secondary': 360, 'badge': 280, 'primary': 620}[kind]
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ink = rgba(OFF_WHITE if dark else GRAPHITE, 255)

    if kind == 'icon':
        mx, my, ms = 20 * scale, 20 * scale, 100 * scale
        draw_el_mark(d, mx, my, ms, dark=dark, img=img)
    elif kind == 'secondary':
        ms = 100 * scale
        mx = (size[0] - ms) / 2
        my = 20 * scale
        draw_el_mark(d, mx, my, ms, dark=dark, img=img)
        text_center(d, (size[0] // 2, int(182 * scale)), 'ELEMENTS', font(int(30 * scale), True), ink)
        text_center(d, (size[0] // 2, int(216 * scale)), 'LABS', font(int(30 * scale), True), ink)
    elif kind == 'badge':
        ms = 84 * scale
        mx = (size[0] - ms) / 2
        my = 56 * scale
        d.ellipse([size[0] * 0.5 - 128 * scale, size[1] * 0.5 - 128 * scale, size[0] * 0.5 + 128 * scale, size[1] * 0.5 + 128 * scale], outline=rgba(PETROL, 255), width=max(2, int(2 * scale)))
        draw_el_mark(d, mx, my, ms, dark=dark, img=img)
        text_center(d, (size[0] // 2, int(206 * scale)), 'ELEMENTS', font(int(19 * scale), True), ink)
        text_center(d, (size[0] // 2, int(230 * scale)), 'LABS', font(int(19 * scale), True), ink)
    else:
        mx, my, ms = 26 * scale, 30 * scale, 100 * scale
        draw_el_mark(d, mx, my, ms, dark=dark, img=img)
        d.text((166 * scale, 46 * scale), 'ELEMENTS', font=font(int(40 * scale), True), fill=ink)
        d.text((166 * scale, 90 * scale), 'LABS', font=font(int(40 * scale), True), fill=ink)

    img.save(path)


def write_logos():
    for kind in ['primary', 'secondary', 'icon', 'badge']:
        for mode in ['light', 'dark']:
            dark = mode == 'dark'
            (LOGOS / f'el-{kind}-{mode}.svg').write_text(logo_svg(kind, dark), encoding='utf-8')
            logo_png(LOGOS / f'el-{kind}-{mode}.png', kind, dark)


def paste_qr(base: Image.Image, product, box):
    qr_path = ROOT / product['qr']
    if not qr_path.exists():
        return
    qr = Image.open(qr_path).convert('RGBA').resize((box[2] - box[0], box[3] - box[1]), Image.Resampling.LANCZOS)
    base.alpha_composite(qr, (box[0], box[1]))


# ---------------------------------------------------------------------------
# PHOTO-REAL VIAL + CONTINUOUS LABEL COMPOSITING (v2: real base photography,
# GrabCut-cut, single fused label panel — replaces the old PIL-drawn vial).
# ---------------------------------------------------------------------------

VIAL_MASTER = BASE / 'vial-master.png'
BOX_MASTER = BASE / 'box-closed-cutout.png'
STUDIO_BG = BASE / 'studio-bg-final-2.jpg'


def build_continuous_label(product, w, h):
    """One single continuous label panel (no split, no seam): EL monogram,
    ELEMENTS LABS wordmark, product name, concentration, product code, batch,
    QR/analysis corner, Research Use Only line."""
    label = Image.new('RGBA', (w, h), rgba(OFF_WHITE, 250))
    label = add_noise(label, amount=6, alpha=10)
    d = ImageDraw.Draw(label)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(h * 0.05), outline=rgba(LINE, 255), width=2)
    d.rectangle([0, 0, w, max(4, int(h * 0.035))], fill=rgba(PETROL, 255))

    pad = int(w * 0.09)
    mark_s = int(h * 0.15)
    draw_el_mark(d, pad, int(h * 0.09), mark_s, dark=False, img=label)
    d.text((pad + mark_s * 1.30, int(h * 0.095)), 'ELEMENTS LABS', font=font(int(h * 0.075), True), fill=rgba(GRAPHITE, 255))
    d.text((pad + mark_s * 1.30, int(h * 0.095) + int(h * 0.082)), product['code'], font=font(int(h * 0.045), False, True), fill=rgba(MUTED, 255))

    line_y = int(h * 0.34)
    d.line([pad, line_y, w - pad, line_y], fill=rgba(LINE, 255), width=2)

    name_size = int(h * 0.125) if len(product['name']) < 12 else int(h * 0.095)
    d.text((w // 2, int(h * 0.46)), product['name'], font=font(name_size, True), fill=rgba(NEAR_BLACK, 255), anchor='mm')
    d.text((w // 2, int(h * 0.58)), product['concentration'], font=font(int(h * 0.09), True), fill=rgba(PETROL, 255), anchor='mm')

    line_y2 = int(h * 0.70)
    d.line([pad, line_y2, w - pad, line_y2], fill=rgba(LINE, 255), width=1)

    d.text((pad, int(h * 0.76)), 'Research Use Only', font=font(int(h * 0.05), True), fill=rgba(GRAPHITE, 255))
    d.text((pad, int(h * 0.855)), product['batch'], font=font(int(h * 0.042), False, True), fill=rgba(MUTED, 255))

    qr_size = int(h * 0.22)
    qr_box = (w - pad - qr_size, int(h * 0.72), w - pad, int(h * 0.72) + qr_size)
    paste_qr(label, product, qr_box)
    d.text((w - pad - qr_size, qr_box[3] + int(h * 0.01)), 'Analysis', font=font(int(h * 0.035), False, True), fill=rgba(MUTED, 255))

    return label


def wrap_label_on_glass(label_img, target_w, target_h, curvature=0.16):
    """Simulate the label wrapped on a cylindrical vial via edge shading
    (cylindrical light falloff) while keeping the text sharp and legible —
    real small-vial labels read almost flat at this scale."""
    label_img = label_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    w, h = label_img.size
    shade = Image.new('L', (w, h), 255)
    sd = ImageDraw.Draw(shade)
    edge = max(1, int(w * curvature))
    for x in range(edge):
        k = x / edge
        val = int(255 * (0.55 + 0.45 * k))
        sd.line([(x, 0), (x, h)], fill=val)
    for x in range(w - edge, w):
        k = (w - x) / edge
        val = int(255 * (0.55 + 0.45 * k))
        sd.line([(x, 0), (x, h)], fill=val)
    shaded = ImageChops.multiply(label_img.convert('RGB'), Image.merge('RGB', (shade, shade, shade)))
    return Image.merge('RGBA', (*shaded.split(), label_img.split()[3]))


def compose_vial(product, canvas_w=900, canvas_h=1300, label_scale=1.0):
    """Compose one product vial photo: real base photograph (studio-shot glass
    vial, GrabCut-cut) + continuous wrapped label with EL branding."""
    vial = Image.open(VIAL_MASTER).convert('RGBA')
    vw, vh = vial.size
    scale = (canvas_h * 0.82) / vh
    new_w, new_h = int(vw * scale), int(vh * scale)
    vial_r = vial.resize((new_w, new_h), Image.Resampling.LANCZOS)

    canvas = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    vx = (canvas_w - new_w) // 2
    vy = canvas_h - new_h - int(canvas_h * 0.03)

    shadow = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sh_y = vy + new_h - int(new_h * 0.02)
    sd.ellipse([vx - new_w * 0.22, sh_y - 14, vx + new_w * 1.22, sh_y + 30], fill=(13, 17, 21, 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    canvas.alpha_composite(shadow)

    canvas.alpha_composite(vial_r, (vx, vy))

    lab_w = int(new_w * 0.72 * label_scale)
    lab_h = int(new_h * 0.30 * label_scale)
    lab_x = vx + (new_w - lab_w) // 2
    lab_y = vy + int(new_h * 0.395)

    label = build_continuous_label(product, 640, int(640 * lab_h / lab_w))
    label = wrap_label_on_glass(label, lab_w, lab_h)
    canvas.alpha_composite(label, (lab_x, lab_y))

    return canvas


def studio_bg_crop(size):
    """Crop a clean region of the real studio photo background (no synthetic gradient)."""
    photo = Image.open(STUDIO_BG).convert('RGBA')
    pw, ph = photo.size
    target_w, target_h = size
    scale = max(target_w / pw, target_h / ph) * 1.08
    photo_r = photo.resize((int(pw * scale), int(ph * scale)), Image.Resampling.LANCZOS)
    rw, rh = photo_r.size
    ox = (rw - target_w) // 2
    oy = int((rh - target_h) * 0.35)
    return photo_r.crop((ox, oy, ox + target_w, oy + target_h))


def product_assets():
    for p in PRODUCTS:
        vial = compose_vial(p, 900, 1300)
        vial.save(PRODUCTS_DIR / f'{p["id"]}-vial.png')

        bg = studio_bg_crop((1280, 980)).convert('RGBA')
        bg = add_noise(bg, amount=3, alpha=6)

        shadow = Image.new('RGBA', bg.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        sd.ellipse([255, 745, 630, 810], fill=(13, 17, 21, 36))
        sd.ellipse([655, 735, 1030, 820], fill=(13, 17, 21, 28))
        shadow = shadow.filter(ImageFilter.GaussianBlur(18))
        bg.alpha_composite(shadow)

        box = Image.open(BOX_MASTER).convert('RGBA')
        bw, bh = box.size
        bscale = 340 / bw
        box_r = box.resize((int(bw * bscale), int(bh * bscale)), Image.Resampling.LANCZOS)
        box_h = box_r.size[1]
        bg.alpha_composite(box_r, (700, 780 - box_h))

        vial_detail = compose_vial(p, 560, 820, label_scale=1.05)
        bg.alpha_composite(vial_detail, (140, 60))

        gloss = Image.new('RGBA', bg.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(gloss)
        gd.rounded_rectangle([64, 68, 172, 850], radius=50, fill=(255, 255, 255, 30))
        bg = Image.alpha_composite(bg, gloss)
        bg.save(PRODUCTS_DIR / f'{p["id"]}-detail.png')


def scene_assets():
    # Hero scene: real studio backdrop + 3 vials + 1 packaging box, all grounded
    # on one shared contact-shadow line so nothing floats.
    bg = studio_bg_crop((1800, 1280)).convert('RGBA')
    bg = add_noise(bg, amount=3, alpha=6)
    d = ImageDraw.Draw(bg)

    shadow = Image.new('RGBA', bg.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse([260, 990, 950, 1060], fill=(13, 17, 21, 55))
    sd.ellipse([980, 995, 1550, 1065], fill=(13, 17, 21, 45))
    shadow = shadow.filter(ImageFilter.GaussianBlur(22))
    bg.alpha_composite(shadow)

    box = Image.open(BOX_MASTER).convert('RGBA')
    bw, bh = box.size
    bscale = 400 / bw
    box_r = box.resize((int(bw * bscale), int(bh * bscale)), Image.Resampling.LANCZOS)
    box_h = box_r.size[1]
    bg.alpha_composite(box_r, (1180, 1030 - box_h))

    positions = [(PRODUCTS[10], 660), (PRODUCTS[9], 500), (PRODUCTS[12], 520)]
    xs = [700, 410, 990]
    ground_y = 1015
    for (p, target_h_v), x in zip(positions, xs):
        vial = compose_vial(p, int(target_h_v * 0.62), target_h_v)
        bg.alpha_composite(vial, (x, ground_y - target_h_v))

    # No text overlay on the hero photo itself — it is pure product photography,
    # matching the approved reference (headline/copy live in the HTML layer).
    bg.save(SCENES / 'hero-studio-scene.png')

    # Group shot — all 13 vials, identical geometry/label grid, real backdrop
    group = studio_bg_crop((2200, 1220)).convert('RGBA')
    group = add_noise(group, amount=3, alpha=7)
    d = ImageDraw.Draw(group)
    x0 = 110
    for i, p in enumerate(PRODUCTS):
        col = i % 7; row = i // 7
        target_h_v = 300 if row == 0 else 268
        x = x0 + col * 285 + (70 if row else 0)
        y = 240 + row * 330
        vial = compose_vial(p, int(target_h_v * 0.62), target_h_v)
        group.alpha_composite(vial, (x, y))
    # No baked-in title text: this photo is reused as a family-grid tile with
    # its own HTML figcaption, so an image-baked headline would duplicate it.
    group.save(SCENES / 'group-product-shot.png')

    # Packaging shot: box + vials, real backdrop, shared ground line
    pack = studio_bg_crop((1600, 1120)).convert('RGBA')
    pack = add_noise(pack, amount=3, alpha=6)
    box = Image.open(BOX_MASTER).convert('RGBA')
    bw, bh = box.size
    bscale = 560 / bw
    box_r = box.resize((int(bw * bscale), int(bh * bscale)), Image.Resampling.LANCZOS)
    box_h = box_r.size[1]
    ground_y = 920
    pack.alpha_composite(box_r, (200, ground_y - box_h))
    vial = compose_vial(PRODUCTS[0], 460, 760)
    pack.alpha_composite(vial, (920, ground_y - 760))
    vial2 = compose_vial(PRODUCTS[10], 400, 660)
    pack.alpha_composite(vial2, (1220, ground_y - 660))
    pack.save(SCENES / 'packaging-shot.png')

    # Metabolic family shot: distinct grouping (2 vials, different angle/count
    # than the other 3 family photos) so all 4 family cards use genuinely
    # different photography, not the same image relabeled.
    meta = studio_bg_crop((1500, 1120)).convert('RGBA')
    meta = add_noise(meta, amount=3, alpha=6)
    md_shadow = Image.new('RGBA', meta.size, (0, 0, 0, 0))
    msd = ImageDraw.Draw(md_shadow)
    msd.ellipse([280, 900, 700, 960], fill=(13, 17, 21, 45))
    msd.ellipse([760, 895, 1180, 965], fill=(13, 17, 21, 40))
    md_shadow = md_shadow.filter(ImageFilter.GaussianBlur(18))
    meta.alpha_composite(md_shadow)
    v1 = compose_vial(PRODUCTS[7], 340, 560)
    meta.alpha_composite(v1, (330, 900 - 560))
    v2 = compose_vial(PRODUCTS[11], 380, 640)
    meta.alpha_composite(v2, (830, 900 - 640))
    meta.save(SCENES / 'family-metabolic-shot.png')

    # Quality scene: a gloved hand holding an ELEMENTS LABS vial in a blurred
    # lab setting (matches the approved reference's quality/analysis photo —
    # not a generic stock-lab mockup, and the SAME vial family used everywhere
    # else on the site).
    hand_path = ROOT / 'assets' / 'base-photos-final' / 'hand-glove-4-clean3.png'
    if hand_path.exists():
        hand = Image.open(hand_path).convert('RGBA')
        hw, hh = hand.size  # source photo is 701x841
        target_h = 1120
        scale = target_h / hh
        hand_r = hand.resize((int(hw * scale), target_h), Image.Resampling.LANCZOS)
        canvas = Image.new('RGBA', (900, 1120), (0, 0, 0, 0))
        hx = (900 - hand_r.size[0]) // 2
        canvas.alpha_composite(hand_r, (hx, 0))
        # Vial grip in the source photo spans roughly x 0.30-0.68 of its own
        # width, y 0.05-0.90 of its own height (where we masked the fake
        # bottle out). Place our real branded vial into that exact slot.
        grip_x0 = hx + int(hand_r.size[0] * 0.30)
        grip_x1 = hx + int(hand_r.size[0] * 0.68)
        grip_w = grip_x1 - grip_x0
        grip_y0 = int(target_h * 0.03)
        grip_h = int(target_h * 0.90)
        vial = compose_vial(PRODUCTS[0], int(grip_w * 0.95), int(grip_h * 1.02), label_scale=0.85)
        vx = grip_x0 + grip_w // 2 - vial.size[0] // 2
        canvas.alpha_composite(vial, (vx, grip_y0 - int(grip_h * 0.02)))
        canvas.save(SCENES / 'quality-hand-vial.png')


    # Macro detail — close crop on glass/label edge/cap, real backdrop.
    # No baked-in caption box: HTML captions (figcaption) already label this
    # image wherever it's used, so an image-baked text box would be a
    # redundant "box without function" per house rule.
    macro = studio_bg_crop((1500, 980)).convert('RGBA')
    macro = add_noise(macro, amount=4, alpha=8)
    vial = compose_vial(PRODUCTS[10], 900, 1500, label_scale=1.15)
    macro.alpha_composite(vial, (60, -280))
    macro.save(SCENES / 'macro-detail.png')


def data_url(path: Path) -> str:
    ext = path.suffix.lower().lstrip('.')
    mime = {'svg': 'image/svg+xml', 'woff2': 'font/woff2', 'woff': 'font/woff'}.get(ext, f'image/{"jpeg" if ext in ["jpg","jpeg"] else ext}')
    return f'data:{mime};base64,' + base64.b64encode(path.read_bytes()).decode('ascii')


FONTS_DIR = ASSETS / 'fonts'
FONT_WEIGHTS = [
    ('space-grotesk-0.woff2', 400, 'normal'),
    ('space-grotesk-1.woff2', 500, 'normal'),
    ('space-grotesk-2.woff2', 600, 'normal'),
    ('space-grotesk-3.woff2', 700, 'normal'),
]


def font_face_css(inline: bool) -> str:
    faces = []
    for fname, weight, style in FONT_WEIGHTS:
        fpath = FONTS_DIR / fname
        if not fpath.exists():
            continue
        src = data_url(fpath) if inline else f'assets/fonts/{fname}'
        faces.append(
            f"@font-face{{font-family:'Space Grotesk';font-style:{style};font-weight:{weight};"
            f"font-display:swap;src:url('{src}') format('woff2')}}"
        )
    return ''.join(faces)


CSS = r'''
:root{
  --graphite:#2A2F36;--near-black:#0D1115;--off-white:#F7F7F8;--petrol:#0D5B6B;--ink:#172027;--muted:#66717B;--line:#E1E5E7;--panel:#FFFFFF;--soft:#EEF2F3;--radius:10px;--radius-lg:16px;--max:1280px;--shadow:0 20px 48px rgba(13,17,21,.10);--sans:"Space Grotesk","Segoe UI",Roboto,Arial,sans-serif;--mono:"Cascadia Mono","SFMono-Regular","Segoe UI Mono",monospace}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--off-white);color:var(--ink);font-family:var(--sans);line-height:1.5;overflow-x:hidden}a{color:inherit;text-decoration:none}button,input,select{font:inherit}
.site-header{position:sticky;top:0;z-index:40;display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:20px;max-width:var(--max);margin:0 auto;padding:16px 24px;background:rgba(247,247,248,.94);backdrop-filter:blur(18px);border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:13px;font-weight:850;letter-spacing:.13em}.brand img{width:230px;height:auto;display:block}.brand .brand-mobile{display:none}
.main-nav{display:flex;gap:30px;justify-content:center;color:#55606A;font-size:13px;font-weight:600;letter-spacing:.02em;text-transform:uppercase}.main-nav a{padding:8px 0;border-bottom:2px solid transparent}.main-nav a:hover,.main-nav a.active{color:var(--near-black);border-color:var(--petrol)}
.header-actions{display:flex;gap:10px;align-items:center}.menu-toggle{display:none}
.secondary-btn,.ghost-btn,.menu-toggle,.search-open{border:1px solid var(--graphite);background:transparent;color:var(--graphite);border-radius:var(--radius);padding:13px 22px;cursor:pointer;transition:.2s ease;font-weight:650;font-size:14px}
.primary-btn{border:1px solid var(--near-black);background:var(--near-black);color:white;border-radius:var(--radius);padding:13px 22px;cursor:pointer;transition:.2s ease;font-weight:650;font-size:14px}
.cart-link{display:flex;align-items:center;gap:8px;border:1px solid var(--near-black);background:var(--near-black);color:white;border-radius:var(--radius);padding:11px 18px;cursor:pointer;transition:.2s ease;font-weight:650;font-size:13px;text-transform:uppercase;letter-spacing:.04em}
.primary-btn:hover,.secondary-btn:hover,.cart-link:hover,.ghost-btn:hover{transform:translateY(-1px);box-shadow:0 8px 18px rgba(13,17,21,.14)}
.cart-link span{display:inline-grid;place-items:center;min-width:20px;height:20px;background:var(--petrol);color:white;border-radius:50%;font:800 11px var(--mono)}
.section{max-width:var(--max);margin:0 auto;padding:76px 24px}
.hero{min-height:auto;display:grid;grid-template-columns:.86fr 1.14fr;gap:56px;align-items:center;padding-top:56px;padding-bottom:56px}
.eyebrow{font:750 11px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--petrol);margin-bottom:14px}
.hero h1,.page-title{font-size:clamp(40px,4.6vw,66px);line-height:1.04;letter-spacing:-.03em;margin:0 0 20px;color:var(--near-black);font-weight:700}
.hero h1 span,.page-title span{color:var(--petrol)}
.lead{font-size:clamp(15px,1.2vw,17px);color:var(--muted);max-width:520px;margin:0 0 26px;line-height:1.6}
.cta-row{display:flex;gap:12px;flex-wrap:wrap;margin-top:6px}
.trust-row{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:38px;padding-top:32px;border-top:1px solid var(--line)}
.trust-row div{display:flex;flex-direction:column;gap:6px}
.trust-row .trust-icon{width:34px;height:34px;border:1.5px solid var(--graphite);border-radius:50%;display:grid;place-items:center;margin-bottom:2px;flex-shrink:0}
.trust-row strong{font-size:13px;color:var(--near-black);font-weight:700;letter-spacing:.01em}
.trust-row span{font-size:12px;color:var(--muted);line-height:1.5}
.trust-matrix{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:30px}.trust-matrix div,.metric-card{padding:17px;background:rgba(255,255,255,.72);border:1px solid var(--line);border-radius:var(--radius)}.trust-matrix strong,.metric-card strong{display:block;font-size:14px;color:var(--near-black);margin-bottom:5px}.trust-matrix span,.metric-card span{font-size:12px;color:var(--muted)}
.hero-photo,.wide-photo{position:relative;background:transparent;border-radius:var(--radius-lg);overflow:hidden}
.hero-photo img,.wide-photo img{display:block;width:100%;height:auto}
.photo-caption{position:absolute;left:20px;bottom:20px;padding:10px 14px;border-radius:8px;background:rgba(255,255,255,.86);border:1px solid var(--line);backdrop-filter:blur(14px);font:750 10px var(--mono);letter-spacing:.07em;text-transform:uppercase;color:var(--graphite)}
.section-head{margin-bottom:32px;display:flex;align-items:end;justify-content:space-between;gap:24px}
.section-head h2{font-size:clamp(28px,3vw,42px);line-height:1.08;letter-spacing:-.028em;margin:0;color:var(--near-black);font-weight:700}
.section-head p{max-width:520px;color:var(--muted);margin:0;font-size:14px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:20px}
.product-card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:16px;display:flex;flex-direction:column;position:relative;overflow:hidden;min-height:420px;transition:.2s ease}
.product-card:hover{border-color:var(--graphite);box-shadow:0 12px 28px rgba(13,17,21,.08)}
.card-top{display:flex;justify-content:space-between;font:750 9px var(--mono);color:var(--muted);text-transform:uppercase;letter-spacing:.07em;margin:0 0 12px}
.product-img-wrap{display:grid;place-items:center;background:linear-gradient(180deg,#FAFBFB,#F1F3F4);border-radius:8px;min-height:190px;margin-bottom:14px;overflow:hidden}
.product-img-wrap img{width:78%;height:auto;filter:drop-shadow(0 14px 18px rgba(13,17,21,.12))}
.product-card h3{margin:0 0 5px;font-size:17px;letter-spacing:-.014em;color:var(--near-black);font-weight:700}
.compound-meta{font-size:12.5px;color:var(--muted);line-height:1.55}
.price-row{display:flex;align-items:center;justify-content:space-between;margin-top:auto;padding-top:12px}
.price{font:750 18px/1 var(--sans);letter-spacing:-.015em}
.status{font:750 10px var(--mono);color:var(--petrol);text-transform:uppercase;letter-spacing:.06em}
.card-actions{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:12px}
.card-actions .secondary-btn{padding:9px 14px;font-size:12.5px;flex:1;text-align:center}
.price-row .primary-btn{width:36px;height:36px;padding:0;display:grid;place-items:center;flex-shrink:0;font-size:0;border-radius:50%}

.price-row .primary-btn:before{content:"+";font-size:20px;line-height:1;color:#fff;font-family:var(--sans)}
.quality-suite{background:var(--near-black);border-radius:var(--radius-lg);overflow:hidden;display:grid;grid-template-columns:1.3fr 1fr}
.quality-suite .quality-copy{padding:52px 48px;color:var(--off-white)}
.quality-suite .quality-copy .eyebrow{color:#7FB3BE}
.quality-suite .quality-copy h2{color:#fff;font-size:clamp(26px,2.6vw,36px);line-height:1.12;letter-spacing:-.025em;margin:0 0 16px;font-weight:700}
.quality-suite .quality-copy p{color:rgba(247,247,248,.72);font-size:14.5px;line-height:1.65;max-width:440px;margin:0 0 22px}
.quality-suite .quality-copy a.link-arrow{color:#fff;font:750 12px var(--mono);text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid rgba(255,255,255,.4);padding-bottom:2px}
.quality-suite .quality-photo{position:relative;overflow:hidden;background:#0A0D10}
.quality-suite .quality-photo img{width:100%;height:100%;object-fit:cover;display:block;opacity:.92}
.batch-suite{background:#fff;color:var(--ink);padding:44px 40px;border-radius:var(--radius-lg);border:1px solid var(--line);border-top:3px solid var(--petrol)}

.batch-suite .eyebrow{color:var(--petrol)}

.batch-suite h2{color:var(--near-black);font-size:clamp(24px,2.3vw,30px);line-height:1.12;letter-spacing:-.02em;margin:0 0 12px;font-weight:700}

.batch-suite p{color:var(--muted);font-size:13.5px;line-height:1.6;margin:0 0 22px}

.batch-suite .batch-input-row{display:flex;gap:10px}

.batch-suite input{flex:1;padding:14px 16px;border-radius:8px;border:1px solid var(--line);background:#F6F8F8;color:var(--ink);font-size:14px}

.batch-suite input:focus{outline:none;border-color:var(--petrol);background:#fff}

.batch-suite input::placeholder{color:var(--muted)}
.batch-suite .batch-submit{width:48px;height:48px;border-radius:8px;border:none;background:var(--petrol);color:#fff;font-size:18px;cursor:pointer;flex-shrink:0}

.batch-suite .batch-submit:hover{background:var(--near-black)}

.batch-suite .link-arrow{display:inline-block;margin-top:16px;color:var(--graphite);font:750 12px var(--mono);text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid var(--line);padding-bottom:2px}
.quality-batch-grid{display:grid;grid-template-columns:1.55fr 1fr;gap:24px;align-items:stretch}
.process{counter-reset:step;list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:12px}
.process li{counter-increment:step;position:relative;padding:16px 16px 16px 52px;background:#fff;border:1px solid var(--line);border-radius:var(--radius)}
.process li:before{content:counter(step,decimal-leading-zero);position:absolute;left:16px;top:18px;font:750 13px var(--mono);color:var(--petrol)}
.process strong{display:block;margin-bottom:4px;font-size:14px}
.coa-preview,.cart-panel,.partner-panel{background:#fff;border:1px solid var(--line);border-radius:var(--radius-lg);padding:26px;box-shadow:0 12px 32px rgba(13,17,21,.06)}
.report{position:relative;background:#FCFCFD;color:var(--near-black);border:1px solid var(--line);border-radius:var(--radius);padding:22px}
.report-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:16px}
.report-grid div{padding:11px;border:1px solid var(--line);border-radius:8px;background:white}
.report-grid span{display:block;font:750 9px var(--mono);letter-spacing:.07em;text-transform:uppercase;color:var(--muted);margin-bottom:4px}
.report-grid strong{font-size:13px}
.doc-note{font-size:12.5px;color:var(--muted);line-height:1.6;margin-top:14px;padding-top:14px;border-top:1px solid var(--line)}
.detail-layout{display:grid;grid-template-columns:1.1fr .9fr;gap:44px;align-items:start}
.gallery{display:grid;gap:14px}
.gallery-main{background:transparent;border-radius:var(--radius-lg);overflow:hidden}
.gallery-main img{display:block;width:100%;height:auto}
.thumbs{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.thumbs img{width:100%;border:1px solid var(--line);border-radius:8px;background:#fff}
.purchase{position:sticky;top:100px;padding:0 0 0 8px}
.purchase h1{font-size:clamp(30px,3vw,42px);line-height:1.05;letter-spacing:-.03em;margin:0 0 13px;color:var(--near-black);font-weight:700}
.spec-list{display:grid;grid-template-columns:1fr 1fr;gap:11px;margin:22px 0}
.spec-list div{padding:13px;background:#F6F8F8;border:1px solid var(--line);border-radius:8px}
.spec-list span{display:block;font:750 9px var(--mono);color:var(--muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:4px}
.spec-list strong{font-size:15px}
.filters{display:grid;grid-template-columns:1.5fr .8fr .8fr;gap:12px;margin-bottom:24px}
.filters input,.filters select,.batch-panel input{padding:12px 15px;background:#fff;border:1px solid var(--line);border-radius:8px;color:var(--ink)}
.batch-panel{background:#fff;border:1px solid var(--line);border-radius:var(--radius-lg);padding:26px}
.batch-panel input{width:100%;margin-bottom:14px}
.qr{width:120px;height:120px;border-radius:8px;background:#fff;padding:6px;display:block;margin-top:16px;border:1px solid var(--line)}
.cart-line{display:grid;grid-template-columns:1.2fr .7fr .7fr auto;gap:16px;align-items:center;padding:16px 0;border-bottom:1px solid var(--line)}
.qty{display:flex;gap:6px;align-items:center}
.qty button{width:36px;height:36px;border-radius:50%;border:1px solid var(--line);background:#fff}
.total{font:750 26px/1 var(--sans);text-align:right;margin:20px 0}
.hidden{display:none}
.footer{max-width:var(--max);margin:0 auto;padding:56px 24px 40px;display:grid;grid-template-columns:2fr 1.3fr 1.2fr;gap:28px;color:var(--muted);font-size:13px;border-top:1px solid var(--line)}
.footer strong{color:var(--near-black)}
.footer a{display:block;color:var(--muted);margin-bottom:8px}
.research-only{grid-column:1/-1;text-align:center;font:750 10px var(--mono);text-transform:uppercase;letter-spacing:.06em;color:var(--muted);padding-top:16px;border-top:1px solid var(--line)}
.faq-list{display:flex;flex-direction:column;gap:12px}
.faq-list details{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:16px}
.faq-list summary{font-weight:700;cursor:pointer;font-size:14px}
.legal{max-width:820px}
.family-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
.family-grid figure{margin:0;border-radius:var(--radius);overflow:hidden;background:#F1F3F4;position:relative}
.family-grid img{width:100%;height:220px;object-fit:cover;display:block}
.family-grid figcaption{position:absolute;left:14px;bottom:14px;color:#fff;font-size:13px;font-weight:700;text-shadow:0 2px 8px rgba(0,0,0,.5)}
.family-grid figcaption span{display:block;font-size:11px;font-weight:500;opacity:.85;margin-top:2px}
.internal-badge{display:inline-block;background:#F2C94C;color:#101418;font:750 10px var(--mono);letter-spacing:.06em;text-transform:uppercase;padding:6px 12px;border-radius:6px}
.skip-link{position:absolute;left:12px;top:-60px;background:var(--near-black);color:#fff;padding:12px 18px;border-radius:0 0 8px 8px;z-index:100;transition:top .2s}
.skip-link:focus{top:0}
.partner-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}
.kpi{padding:18px;background:#F6F8F8;border:1px solid var(--line);border-radius:var(--radius)}
.kpi span{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
.kpi strong{display:block;font-size:24px;margin:7px 0 4px}
.partner-table{width:100%;border-collapse:collapse;font-size:13px}
.partner-table th,.partner-table td{padding:11px 10px;text-align:left;border-bottom:1px solid var(--line)}
.partner-table th{font:750 10px var(--mono);text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
#toast{position:fixed;bottom:22px;right:22px;z-index:60;background:var(--near-black);color:white;border:1px solid rgba(255,255,255,.12);border-radius:8px;padding:12px 18px;font-size:13px;box-shadow:var(--shadow);opacity:0;transform:translateY(10px);transition:opacity .25s,transform .25s;pointer-events:none}
#toast.show-toast{opacity:1;transform:translateY(0)}
.research-profile{margin-top:56px;padding-top:40px;border-top:1px solid var(--line)}
.research-profile .rp-head{margin-bottom:28px}
.research-profile .rp-head h2{font-size:clamp(24px,2.4vw,32px);letter-spacing:-.02em;margin:0 0 8px;color:var(--near-black);font-weight:700}
.research-profile .rp-head p{color:var(--muted);font-size:13.5px;margin:0}
.rp-grid{display:grid;grid-template-columns:1fr 1fr;gap:28px 40px;margin-bottom:28px}
.rp-block h4{font-size:11px;font-weight:750;text-transform:uppercase;letter-spacing:.08em;color:var(--petrol);margin:0 0 8px}
.rp-block p{font-size:14px;line-height:1.65;color:var(--ink);margin:0}
.rp-topics{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px}
.rp-topics span{font-size:12px;padding:6px 12px;border:1px solid var(--line);border-radius:20px;color:var(--graphite);background:#F6F8F8}
.rp-status{display:inline-flex;align-items:center;gap:6px;font:750 10px var(--mono);text-transform:uppercase;letter-spacing:.06em;color:var(--petrol);padding:5px 10px;border:1px solid var(--line);border-radius:6px;margin-bottom:20px}
.rp-status:before{content:"";width:6px;height:6px;border-radius:50%;background:var(--petrol)}
.rp-refs{margin-top:8px;display:flex;flex-direction:column;gap:10px}
.rp-refs .rp-ref{font-size:12.5px;color:var(--muted);line-height:1.5;padding:10px 12px;background:#F6F8F8;border-radius:8px}
.rp-refs .rp-ref a{color:var(--petrol);text-decoration:underline}
.rp-disclaimer{margin-top:24px;font-size:12px;color:var(--muted);line-height:1.6;padding:14px;background:#FBFBFC;border:1px solid var(--line);border-radius:8px}
@media(max-width:640px){.rp-grid{grid-template-columns:1fr}}
@media(min-width:1000px){#productGrid{grid-template-columns:repeat(6,1fr)}}
@media(max-width:960px){.site-header{grid-template-columns:auto auto auto;gap:10px}.menu-toggle{display:block;margin-left:auto}.main-nav{position:absolute;left:14px;right:14px;top:70px;display:none;flex-direction:column;justify-content:flex-start;background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px;box-shadow:var(--shadow)}.main-nav.open{display:flex}.search-open{display:none}.hero,.detail-layout,.quality-suite,.quality-batch-grid{grid-template-columns:1fr}.hero{min-height:auto;padding-top:40px}.trust-row{grid-template-columns:1fr}.family-grid{grid-template-columns:repeat(2,1fr)}.filters{grid-template-columns:1fr}.footer{grid-template-columns:1fr}.cart-line{grid-template-columns:1fr;align-items:start}.total{text-align:left}.section{padding:52px 18px}.section-head{display:block}.purchase{position:relative;top:0;padding-left:0}.spec-list{grid-template-columns:1fr 1fr}.quality-suite .quality-photo{min-height:220px}}
@media(max-width:540px){.site-header{padding:12px 12px}.brand .brand-desktop{display:none}.brand .brand-mobile{display:block;width:40px;height:40px}.cart-link,.primary-btn,.secondary-btn,.ghost-btn,.menu-toggle{padding:10px 14px}.hero h1,.page-title{font-size:36px}.section{padding:44px 14px}.cards{grid-template-columns:repeat(2,1fr)}.report-grid,.thumbs,.spec-list{grid-template-columns:1fr}.family-grid{grid-template-columns:1fr}.hero-photo,.wide-photo,.gallery-main{border-radius:12px}.photo-caption{left:10px;bottom:10px;font-size:9px}.product-card{min-height:auto}.product-img-wrap{min-height:170px}.qr{width:96px;height:96px}.header-actions{gap:6px}.main-nav{top:62px}.footer{padding-bottom:32px}.quality-suite .quality-copy{padding:32px 24px}.batch-suite{padding:32px 24px}}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}
'''

APP = r'''
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
const products = JSON.parse(document.getElementById('productData').textContent);
window.__ELEMENTS_PRODUCTS__ = products;
window.__ELEMENTS_RESEARCH__ = JSON.parse((document.getElementById('researchData')||{textContent:'{}'}).textContent);
const money = v => Number(String(v).replace('€','').replace('.','').replace(',','.').trim());
const fmt = n => n.toLocaleString('de-DE',{style:'currency',currency:'EUR'});
let cart = {};
try{cart = JSON.parse(localStorage.getItem('elementsCart') || '{}');}catch(e){cart = {};}
const app = document.getElementById('app');
function saveCart(){localStorage.setItem('elementsCart', JSON.stringify(cart)); updateCartCount();}
function updateCartCount(){document.getElementById('cartCount').textContent = Object.values(cart).reduce((a,b)=>a+b,0)}
function toast(t){const el=document.getElementById('toast');el.textContent=t;el.classList.add('show-toast');setTimeout(()=>el.classList.remove('show-toast'),1500)}
function addToCart(id,qty=1){cart[id]=(cart[id]||0)+qty;saveCart();toast('Zum Warenkorb hinzugefügt');}
function removeFromCart(id){delete cart[id];saveCart();render()}
function setQty(id,qty){if(qty<=0) delete cart[id]; else cart[id]=qty;saveCart();render()}
function pById(id){return products.find(p=>p.id===id)}
function pByBatch(b){return products.find(p=>p.batch.toLowerCase()===String(b||'').toLowerCase())}
function productCard(p){return `<article class="product-card ${p.featured?'featured':''}" data-product-card data-id="${p.id}"><div class="card-top"><span>${p.num}</span><span>${p.batch}</span></div><a class="product-img-wrap" href="#product=${p.id}" aria-label="${p.name} öffnen"><img src="${p.image}" alt="${p.name} ${p.concentration} Elements Labs Vial"></a><h3>${p.name}</h3><div class="compound-meta">${p.concentration}</div><div class="price-row"><span class="price">${p.price}</span><button class="primary-btn" data-add="${p.id}" aria-label="${p.name} zum Warenkorb hinzufügen" title="Add to Cart"></button></div></article>`}
function report(p){return `<div class="report" data-coa="${p.id}"><div class="eyebrow">Batch Documentation</div><h3>${p.name}</h3><div class="report-grid"><div><span>Product Code</span><strong>${p.code}</strong></div><div><span>Batch</span><strong>${p.batch}</strong></div></div><p class="doc-note">Laboratory Analysis: No verified external report is currently linked to this batch. Certificates appear here automatically once issued.</p></div>`}
function home(){const featured=products.filter(p=>p.featured).slice(0,6);return `<section class="section hero" id="home-hero"><div><div class="eyebrow">European Research Brand</div><h1>ELEMENTS LABS.<br><span>Precision research</span> commerce.</h1><p class="lead">High-purity research compounds. Rigorous batch traceability. Engineered for serious research.</p><div class="cta-row"><a class="primary-btn" href="#products">Explore Products</a><a class="secondary-btn" href="#quality">Quality &amp; Documentation</a></div><div class="trust-row"><div><div class="trust-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3"/></svg></div><strong>Research Use</strong><span>For laboratory research purposes only.</span></div><div><div class="trust-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z"/></svg></div><strong>Quality Assured</strong><span>Strict sourcing and quality control.</span></div><div><div class="trust-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 2l8 4.5v9L12 20l-8-4.5v-9L12 2z"/></svg></div><strong>Batch Traceability</strong><span>Traceable batches and documentation for every lot.</span></div></div></div><figure class="hero-photo"><img src="assets/scenes/hero-studio-scene.png" alt="ELEMENTS LABS Produktfotografie mit Vials und Verpackung"></figure></section><section class="section"><div class="section-head"><div><div class="eyebrow">Featured Products</div><h2>13 Produkte, ein Standard.</h2></div><a class="secondary-btn" href="#products">Alle Produkte</a></div><div class="cards">${featured.map(productCard).join('')}</div></section>${qualityBatchBlock()}${researchLibrarySection()}${familySection()}<section class="section"><div class="section-head"><div><div class="eyebrow">FAQ / Support</div><h2>Häufige Fragen.</h2></div><p>Antworten zu Bestellung, Dokumentation und Research-Einsatz.</p></div><div class="faq-list"><details open><summary>Wofür ist das Portfolio bestimmt?</summary><p>Für Research-Kontexte. Keine Einnahme, keine Anwendung, keine therapeutische oder diagnostische Kommunikation.</p></details><details><summary>Was zeigt die Batch-Suche?</summary><p>Sie verbindet Produkt, Charge, Code und Analysefelder in einer festen Struktur. Nur echte Prüfwerte werden veröffentlicht.</p></details></div></section>`}
function researchLibrarySection(){return `<section class="section"><div class="section-head"><div><div class="eyebrow">Research Library</div><h2>13 quellenbasierte Research Profiles.</h2></div><a class="secondary-btn" href="#quality">Zur Research Library</a></div><div class="cards">${products.slice(0,6).map(p=>{const rp=(window.__ELEMENTS_RESEARCH__||{})[p.id];return `<article class="product-card" style="min-height:190px"><div class="card-top"><span>${p.num}</span><span>${esc(p.category)}</span></div><h3>${p.name}</h3><p class="compound-meta">${rp?esc(rp.research_focus||''):esc(p.category)+' — Profil folgt.'}</p><div class="price-row" style="margin-top:auto;padding-top:14px"><a class="secondary-btn" href="#product=${p.id}">Research Profile</a></div></article>`;}).join('')}</div></section>`}
function familySection(){const cats=[{name:'Peptides',count:products.filter(p=>p.category.includes('Peptide')||p.category.includes('Tissue')).length,img:'assets/scenes/group-product-shot.png'},{name:'Regenerative',count:products.filter(p=>p.category.includes('Copper')||p.category.includes('Tripeptide')).length,img:'assets/scenes/packaging-shot.png'},{name:'Longevity',count:products.filter(p=>p.category.includes('Longevity')||p.category.includes('Cofactor')).length,img:'assets/scenes/macro-detail.png'},{name:'Metabolic',count:products.filter(p=>p.category.includes('Metabolic')||p.category.includes('Mitochondrial')||p.category.includes('Endocrine')||p.category.includes('Neuropeptide')).length,img:'assets/scenes/family-metabolic-shot.png'}];return `<section class="section family-section"><div class="section-head"><div><div class="eyebrow">Our Product Families</div><h2>Our Product Families.</h2></div><a class="secondary-btn" href="#products">View All Products</a></div><div class="family-grid">${cats.map(c=>`<figure><img src="${c.img}" alt="ELEMENTS LABS ${c.name}"><figcaption>${c.name}<span>${c.count} products</span></figcaption></figure>`).join('')}</div></section>`}
function productsPage(){return `<section class="section"><div class="section-head"><div><div class="eyebrow">Catalog</div><h1 class="page-title">13 Research <span>Products.</span></h1></div><p>Alle verbindlichen Produkte mit korrekter Konzentration, Preis, Produktcode und Batch-ID.</p></div><div class="filters"><input id="searchInput" placeholder="Search compound, code or batch" aria-label="Produkt suchen"><select id="categoryFilter" aria-label="Kategorie filtern"><option value="">Alle Kategorien</option>${[...new Set(products.map(p=>p.category))].map(c=>`<option>${c}</option>`).join('')}</select><select id="sortFilter" aria-label="Sortierung wählen"><option value="featured">Featured zuerst</option><option value="price-asc">Preis aufsteigend</option><option value="price-desc">Preis absteigend</option></select></div><div class="cards" id="productGrid" aria-live="polite">${products.map(productCard).join('')}</div></section>`}
function qualityBatchBlock(){return `<section class="section" id="quality-section"><div class="quality-batch-grid"><div class="quality-suite"><div class="quality-copy"><div class="eyebrow">Quality &amp; Analysis</div><h2>Uncompromising quality.<br>Complete transparency.</h2><p>Jede Charge folgt derselben Dokumentationsstruktur: Produktcode, Batch-ID, Analysefelder und QR-Zugriff sind konsistent verknüpft.</p><a class="link-arrow" href="#quality">Learn more about our quality →</a></div><div class="quality-photo"><img src="assets/scenes/quality-hand-vial.png" alt="ELEMENTS LABS Quality Verification"></div></div><div class="batch-suite"><div class="eyebrow">Batch Lookup</div><h2>Verify your batch.<br>Instantly.</h2><p>Enter your batch number to view documentation and product details.</p><div class="batch-input-row"><input id="batchInputHome" placeholder="Enter batch number" aria-label="Batch-ID eingeben"><button class="batch-submit" id="batchSubmitHome" aria-label="Batch prüfen">→</button></div><a class="link-arrow" href="#batch-lookup">How to find your batch →</a></div></div></section>`}
function qualityBlock(full=true){return qualityBatchBlock()}
function qualityPage(){return `<section class="section" style="padding-bottom:0"><div class="section-head"><div><div class="eyebrow">Quality & Analysis</div><h1 class="page-title">Quality <span>& Analysis Hub.</span></h1></div><p>Batch-Dokumentation, Zertifikats-Struktur, Produktspezifikation und Rückverfolgbarkeit an einem Ort.</p></div></section>${qualityBatchBlock()}<section class="section"><div class="section-head"><div><div class="eyebrow">Analysis Library</div><h2>13/13 Produkte dokumentiert.</h2></div><p>Jeder Eintrag folgt derselben Struktur; Laborwerte erscheinen, sobald sie extern verifiziert sind.</p></div><div class="cards">${products.map(p=>`<article class="product-card" style="min-height:220px"><div class="card-top"><span>${p.code}</span><span>${p.batch}</span></div><h3>${p.name}</h3><p class="compound-meta">${p.concentration}</p><div class="price-row"><span class="status">Dokumentation</span><a href="#product=${p.id}" class="secondary-btn">Öffnen</a></div></article>`).join('')}</div></section>`}
function batchPage(batch=''){const p=pByBatch(batch);return `<section class="section"><div class="section-head"><div><div class="eyebrow">Batch Lookup</div><h1 class="page-title">Batchnummer <span>prüfen.</span></h1></div><p>Produkt, Konzentration, Code und Analysefelder werden über die Batch-ID verbunden.</p></div><div class="batch-panel"><input id="batchInput" value="${esc(batch||'')}" placeholder="z. B. EL-BPC5-26001" aria-label="Batch-ID eingeben"><div class="cta-row"><button class="primary-btn" id="batchBtn">Batch prüfen</button><button class="secondary-btn" id="sampleBatch">Erste Batch-ID einsetzen</button></div><div id="batchResult" style="margin-top:22px">${p?batchResult(p):batchHint(batch)}</div></div></section>`}
function batchHint(batch){return batch?`<p class="compound-meta">Keine Batch-ID „${esc(batch)}“ gefunden. Akzeptierte Start-Batches: ${products.slice(0,4).map(p=>p.batch).join(' · ')} · weitere im Katalog.</p>`:`<p class="compound-meta">Akzeptierte Start-Batches: ${products.slice(0,4).map(p=>p.batch).join(' · ')} · weitere im Katalog.</p>`}
function batchResult(p){return `<div class="detail-layout" style="padding:0;border:0;background:transparent"><div><img class="qr" src="${p.qr}" alt="QR zu ${p.batch}"><div class="product-img-wrap" style="max-width:260px;margin-top:16px"><img src="${p.image}" alt="${p.name} Vial"></div></div><div><div class="eyebrow">Batch Result</div><h2>${p.name}</h2><p>${p.concentration} · ${p.code} · ${p.batch}</p><div class="report-grid"><div><span>Product Code</span><strong>${p.code}</strong></div><div><span>Batch</span><strong>${p.batch}</strong></div></div><p class="doc-note">Laboratory Analysis: No verified external report is currently linked to this batch.</p><div class="cta-row"><a class="primary-btn" href="#product=${p.id}">Produktdetail</a><a class="secondary-btn" href="#quality">Research Library</a></div></div></div>`}
function researchProfileBlock(p){const rp=(window.__ELEMENTS_RESEARCH__||{})[p.id];if(!rp)return '';const refs=(rp.references||[]).map(r=>`<div class="rp-ref">${esc(r.author||'')}${r.author?', ':''}<em>${esc(r.journal||'')}</em>${r.year?' ('+r.year+')':''}.${r.identifier?' '+esc(r.identifier)+'.':''}${r.url?` <a href="${esc(r.url)}" target="_blank" rel="noopener">Quelle ansehen</a>`:''}</div>`).join('');const topics=(rp.key_research_topics||[]).map(t=>`<span>${esc(t)}</span>`).join('');const statusMap={'preclinical':'Preclinical','early clinical':'Early Clinical','limited clinical':'Limited Clinical','investigational':'Investigational'};const statusRaw=String(rp.research_status||'');const statusShort=statusRaw.split(';')[0].split('.')[0];const statusLabel=statusMap[statusRaw.toLowerCase()]||esc(statusShort.length>60?statusShort.slice(0,57)+'…':statusShort);return `<div class="research-profile"><div class="rp-head"><div class="eyebrow">Research Profile</div><h2>Scientific Overview</h2><p>Quellenbasierte Zusammenfassung; keine Dosierungs- oder Anwendungsempfehlung.</p></div><div class="rp-status">${statusLabel}</div><div class="rp-grid"><div class="rp-block"><h4>Classification</h4><p>${esc(rp.research_class||'')} · ${esc(rp.molecular_type||'')}</p></div><div class="rp-block"><h4>Research Focus</h4><p>${esc(rp.research_focus||'')}</p></div><div class="rp-block"><h4>Mechanistic Context</h4><p>${esc(rp.mechanism_summary||'')}</p></div><div class="rp-block"><h4>Current Evidence</h4><p>${esc(rp.evidence_summary||'')}</p></div></div><div class="rp-block" style="margin-bottom:20px"><h4>Research Topics</h4><div class="rp-topics">${topics}</div></div><div class="rp-block" style="margin-bottom:20px"><h4>Limitations</h4><p>${esc(rp.limitations||'')}</p></div><div class="rp-block"><h4>References</h4><div class="rp-refs">${refs}</div></div><p class="rp-disclaimer">Wissenschaftliche Information aus öffentlich zugänglicher, überwiegend präklinischer Forschung. Keine Behandlungs-, Dosierungs- oder Anwendungsempfehlung. Research Use Only.</p></div>`}
function productDetail(id){const p=pById(id);if(!p)return `<section class="section"><div class="section-head"><div><div class="eyebrow">Products</div><h1 class="page-title">Produkt <span>nicht gefunden.</span></h1></div><p>Dieses Produkt existiert nicht im aktuellen Katalog.</p></div><a class="primary-btn" href="#products">Zum Katalog</a></section>`;return `<section class="section"><a href="#products" class="secondary-btn">← Zurück zum Katalog</a><div class="detail-layout" style="margin-top:22px"><div class="gallery"><div class="gallery-main"><img src="${p.detailImage}" alt="${p.name} Elements Labs Produktbild"></div><div class="thumbs"><img src="${p.image}" alt="${p.name} Vial"><img src="${p.packagingImage}" alt="Elements Labs Packaging"><img src="${p.macroImage}" alt="Elements Labs Macro Detail"></div></div><aside class="purchase"><div class="eyebrow">${p.num} · ${p.category}</div><h1>${p.name}</h1><p class="lead">${p.desc}</p><div class="price" style="margin:10px 0 18px">${p.price}</div><div class="spec-list"><div><span>Konzentration</span><strong>${p.concentration}</strong></div><div><span>Einheit</span><strong>1 Vial</strong></div><div><span>Product Code</span><strong>${p.code}</strong></div><div><span>Batch</span><strong>${p.batch}</strong></div></div><p class="compound-meta"><strong>Research Notice:</strong> Not for human consumption. No therapeutic, diagnostic, veterinary or dosing claims.</p><div class="cta-row"><button class="primary-btn" data-add="${p.id}">Add to Cart</button><a class="secondary-btn" href="#batch=${p.batch}">Batch anzeigen</a></div></aside></div>${researchProfileBlock(p)}<div class="section-head" style="margin-top:56px;padding-top:40px;border-top:1px solid var(--line)"><div><div class="eyebrow">Product Documentation</div><h2>Batch &amp; Specifications</h2></div><p>Produktdaten bleiben exakt; Analysewerte erscheinen ausschließlich nach echter Prüfung.</p></div>${report(p)}</section>`}
function cartPage(){const items=Object.entries(cart).map(([id,qty])=>({p:pById(id),qty})).filter(x=>x.p);const total=items.reduce((s,x)=>s+money(x.p.price)*x.qty,0);return `<section class="section"><div class="section-head"><div><div class="eyebrow">Cart</div><h1 class="page-title">Warenkorb <span>prüfen.</span></h1></div><p>Produktauswahl, Mengen und Summen im Überblick. Bestellanfragen werden individuell von Elements Labs bearbeitet.</p></div><div class="cart-panel">${items.length?items.map(x=>`<div class="cart-line"><strong>${x.p.name}<br><span class="compound-meta">${x.p.concentration} · ${x.p.batch}</span></strong><span>${x.p.price}</span><div class="qty"><button data-qty="${x.p.id}" data-delta="-1" aria-label="${x.p.name} Menge verringern">−</button><span>${x.qty}</span><button data-qty="${x.p.id}" data-delta="1" aria-label="${x.p.name} Menge erhöhen">+</button></div><button class="ghost-btn" data-remove="${x.p.id}" aria-label="${x.p.name} entfernen">Remove</button></div>`).join(''):'<p class="compound-meta">Der Warenkorb ist leer.</p>'}<p class="compound-meta">Anzeige inklusive Umsatzsteuer, zzgl. Versand nach Absprache.</p><div class="total" id="cartTotal">${fmt(total)}</div><div class="cta-row"><button class="primary-btn" id="checkoutBtn" ${items.length?'':'disabled'}>Bestellanfrage senden</button><a class="secondary-btn" href="#products">Weiter einkaufen</a></div><div id="checkoutDemo" class="hidden" style="margin-top:20px"><span class="internal-badge">Anfrage erfasst</span><p>Elements Labs bearbeitet Bestellanfragen individuell — Sie erhalten eine Rückmeldung mit Verfügbarkeit und Versandoptionen.</p></div></div></section>`}
function about(){return `<section class="section legal"><div class="eyebrow">About</div><h1 class="page-title">European Research Commerce, <span>präzise geführt.</span></h1><p class="lead">ELEMENTS LABS positioniert Research-Produkte über Materialklarheit, dokumentierte Batch-Struktur und zurückhaltendes Premium-Design.</p><p>Die Marke vermeidet Fitness-, Supplement- und Pharma-Anmutung. Der Fokus liegt auf reproduzierbaren Produktvisuals, systematischer Informationsarchitektur und einem ehrlichen Analyse-Framework.</p></section>`}
function faq(){return `<section class="section legal"><div class="eyebrow">FAQ</div><h1 class="page-title">Research-only <span>clarity.</span></h1><div class="faq-list"><details open><summary>Sind Bestellungen bereits aktiv?</summary><p>Bestellanfragen können bereits über den Warenkorb gestellt werden. Elements Labs bestätigt Verfügbarkeit und Versandoptionen individuell.</p></details><details><summary>Sind Laborberichte veröffentlicht?</summary><p>Nein. Die Seite zeigt die Dokumentationsstruktur. Nur echte, extern geprüfte Analysewerte werden veröffentlicht.</p></details><details><summary>Gibt es medizinische Aussagen?</summary><p>Nein. Keine Einnahme-, Dosierungs-, Therapie-, Diagnose- oder Human-Use-Anleitung.</p></details><details><summary>Warum Batch Lookup?</summary><p>Das System verbindet Produkt, Charge und Berichtszugriff eindeutig und nachvollziehbar.</p></details></div></section>`}
function contact(){return `<section class="section legal"><div class="eyebrow">Support</div><h1 class="page-title">Kontakt <span>Elements Labs.</span></h1><p class="lead">Für Bestellanfragen, Fachfragen und Kooperationen erreichen Sie Elements Labs direkt.</p><div class="batch-panel"><p><strong>ELEMENTS LABS</strong><br>Research-only commerce structure<br>Germany / EU market focus</p><p class="compound-meta">Keine medizinische Beratung. Keine Human-Use-Kommunikation.</p></div></section>`}
function legal(kind){return `<section class="section legal"><div class="eyebrow">Legal</div><h1 class="page-title">${kind==='privacy'?'Datenschutz':'Impressum'}</h1><p class="compound-meta"><strong>Betreiberkennzeichnung nach § 5 TMG</strong><br>Elements Labs · Research-only commerce structure · Germany / EU market focus.</p><p>${kind==='privacy'?'Diese Website nutzt kein Tracking und keine Analyse-Cookies.':'Elements Labs · Research-only commerce structure · Germany / EU market focus.'}</p><p>Research-use-only. No human consumption. No medical, therapeutic, diagnostic or veterinary claims.</p></section>`}
function route(){const h=decodeURIComponent(location.hash.slice(1)||'home');if(h.startsWith('product='))return productDetail(h.split('=')[1]);if(h.startsWith('batch='))return batchPage(h.split('=')[1]);if(h==='products')return productsPage();if(h==='quality')return qualityPage();if(h==='batch-lookup')return batchPage();if(h==='about')return about();if(h==='faq')return faq();if(h==='contact')return contact();if(h==='cart')return cartPage();if(h==='legal-datenschutz')return legal('privacy');if(h==='legal-impressum')return legal('imprint');return home()}
function bind(){document.querySelectorAll('[data-add]').forEach(b=>b.onclick=()=>addToCart(b.dataset.add));document.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>removeFromCart(b.dataset.remove));document.querySelectorAll('[data-qty]').forEach(b=>b.onclick=()=>setQty(b.dataset.qty,(cart[b.dataset.qty]||0)+Number(b.dataset.delta)));const co=document.getElementById('checkoutBtn');if(co)co.onclick=()=>document.getElementById('checkoutDemo').classList.remove('hidden');const bb=document.getElementById('batchBtn');if(bb)bb.onclick=()=>{const v=document.getElementById('batchInput').value.trim();location.hash='batch='+encodeURIComponent(v)};const bbh=document.getElementById('batchSubmitHome');if(bbh)bbh.onclick=()=>{const v=document.getElementById('batchInputHome').value.trim();location.hash='batch='+encodeURIComponent(v)};const bih=document.getElementById('batchInputHome');if(bih)bih.addEventListener('keydown',e=>{if(e.key==='Enter'){location.hash='batch='+encodeURIComponent(bih.value.trim())}});const sb=document.getElementById('sampleBatch');if(sb)sb.onclick=()=>{document.getElementById('batchInput').value=products[0].batch};const si=document.getElementById('searchInput');if(si){const cf=document.getElementById('categoryFilter'),sf=document.getElementById('sortFilter'),grid=document.getElementById('productGrid');const apply=()=>{let list=[...products];const q=si.value.toLowerCase();if(q)list=list.filter(p=>(p.name+p.code+p.batch+p.category).toLowerCase().includes(q));if(cf.value)list=list.filter(p=>p.category===cf.value);if(sf.value==='price-asc')list.sort((a,b)=>money(a.price)-money(b.price));if(sf.value==='price-desc')list.sort((a,b)=>money(b.price)-money(a.price));if(sf.value==='featured')list.sort((a,b)=>(b.featured?1:0)-(a.featured?1:0));grid.innerHTML=list.map(productCard).join('');bind()};[si,cf,sf].forEach(x=>x.oninput=apply)}document.querySelectorAll('.main-nav a').forEach(a=>a.classList.toggle('active',('#'+(location.hash.slice(1)||'home'))===a.getAttribute('href')))}
function render(){app.innerHTML=route();bind();updateCartCount();app.focus({preventScroll:true});window.scrollTo({top:0,left:0,behavior:'instant'});}
window.addEventListener('hashchange',render);render();
document.getElementById('menuToggle').onclick=()=>{const n=document.getElementById('mainNav');n.classList.toggle('open');document.getElementById('menuToggle').setAttribute('aria-expanded',n.classList.contains('open'))};document.addEventListener('click',e=>{if(e.target.closest('#mainNav a')){document.getElementById('mainNav').classList.remove('open');document.getElementById('menuToggle').setAttribute('aria-expanded','false')}if(e.target.matches('[data-action="focus-search"]')){location.hash='products';setTimeout(()=>document.getElementById('searchInput')?.focus(),50)}const nav=document.getElementById('mainNav'),tog=document.getElementById('menuToggle');if(nav.classList.contains('open')&&!nav.contains(e.target)&&!tog.contains(e.target)){nav.classList.remove('open');tog.setAttribute('aria-expanded','false')}});document.addEventListener('keydown',e=>{if(e.key==='Escape'){const nav=document.getElementById('mainNav');if(nav.classList.contains('open')){nav.classList.remove('open');document.getElementById('menuToggle').setAttribute('aria-expanded','false');document.getElementById('menuToggle').focus()}}});
'''

QA_JS = r'''
const fs=require('fs');const path=require('path');const http=require('http');const WebSocket=require('ws');
function getJson(url){return new Promise((resolve,reject)=>{const req=http.request(url,res=>{let d='';res.on('data',c=>d+=c);res.on('end',()=>{try{resolve(JSON.parse(d))}catch(e){reject(new Error('bad json '+d.slice(0,200)))}})});req.on('error',reject);req.end();});}
class CDP{constructor(ws){this.ws=ws;this.id=1;this.pending=new Map();this.errors=[];this.sessionId=null;this.ws.onmessage=ev=>{const msg=JSON.parse(ev.data);if(msg.id&&this.pending.has(msg.id)){this.pending.get(msg.id)(msg);this.pending.delete(msg.id);return;}const m=msg.method,p=msg.params||{};if(m==='Runtime.exceptionThrown')this.errors.push('exception: '+(p.exceptionDetails?.exception?.description||p.exceptionDetails?.text||JSON.stringify(p.exceptionDetails)).slice(0,500));if(m==='Runtime.consoleAPICalled'&&p.type==='error')this.errors.push('console.error: '+(p.args||[]).map(a=>a.value||a.description||'').join(' ').slice(0,500));if(m==='Log.entryAdded'&&p.entry?.level==='error')this.errors.push('log.error: '+(p.entry.text||'').slice(0,500));};}async open(){if(this.ws.readyState===1)return;await new Promise((res,rej)=>{this.ws.onopen=res;this.ws.onerror=rej;});}async send(method,params={},sessionId=this.sessionId){const id=this.id++;const payload={id,method,params};if(sessionId)payload.sessionId=sessionId;this.ws.send(JSON.stringify(payload));const msg=await new Promise((res,rej)=>{const t=setTimeout(()=>{this.pending.delete(id);rej(new Error('CDP timeout '+method));},15000);this.pending.set(id,m=>{clearTimeout(t);res(m);});});if(msg.error)throw new Error(method+' '+JSON.stringify(msg.error));return msg.result;}close(){this.ws.close();}}
const root=process.argv[2]||'C:/Users/eduar/elements-lab-flagship';const file=process.argv[3]||'index.html';const outDir=path.join(root,'evidence','screenshots');fs.mkdirSync(outDir,{recursive:true});
const expected=[['bpc-157','BPC-157','5 mg','24,90 €','EL-BPC5-26001','EL-BPC-005'],['tb-500','TB-500','5 mg','36,90 €','EL-TB5-26001','EL-TB5-005'],['ghk-cu','GHK-Cu','50 mg','27,90 €','EL-GHK50-26001','EL-GHK-050'],['ipamorelin','Ipamorelin','5 mg','27,90 €','EL-IPA5-26001','EL-IPA-005'],['kpv','KPV','10 mg','36,90 €','EL-KPV10-26001','EL-KPV-010'],['selank','Selank','5 mg','27,90 €','EL-SEL5-26001','EL-SEL-005'],['semax','Semax','5 mg','27,90 €','EL-SMX5-26001','EL-SMX-005'],['mots-c','MOTS-C','10 mg','36,90 €','EL-MOT10-26001','EL-MOT-010'],['cjc-1295-no-dac','CJC-1295 No DAC','5 mg','36,90 €','EL-CJC5-26001','EL-CJC-005'],['nad-plus','NAD+','500 mg','44,90 €','EL-NAD500-26001','EL-NAD-500'],['5-amino-1mq','5-Amino-1MQ','5 mg','54,90 €','EL-AMQ5-26001','EL-AMQ-005'],['bpc-157-tb-500','BPC-157 + TB-500','5 mg + 5 mg','46,90 €','EL-BT10-26001','EL-BT-010'],['epithalon','Epithalon','50 mg','94,90 €','EL-EPI50-26001','EL-EPI-050']];
(async()=>{const v=await getJson('http://127.0.0.1:9333/json/version');const c=new CDP(new WebSocket(v.webSocketDebuggerUrl));await c.open();const t=await c.send('Target.createTarget',{url:'about:blank'},null);const a=await c.send('Target.attachToTarget',{targetId:t.targetId,flatten:true},null);c.sessionId=a.sessionId;for(const m of ['Page.enable','Runtime.enable','Log.enable','DOM.enable'])await c.send(m,{});const failures=[],evidence=[];const url=h=>'file:///'+root.replace(/\\/g,'/')+'/'+file+'#'+(h||'home');const fail=m=>failures.push(m);const assert=(cond,msg)=>{if(!cond)fail(msg)};async function evalJS(expr){const r=await c.send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true});if(r.exceptionDetails){fail('JS exception '+(r.exceptionDetails.exception?.description||r.exceptionDetails.text||''));return null}return r.result.value}async function waitFor(expr,timeout=7000){const s=Date.now();while(Date.now()-s<timeout){if(await evalJS(`Boolean(${expr})`))return true;await new Promise(r=>setTimeout(r,80));}fail('wait timeout '+expr);return false}async function viewport(w,h){await c.send('Emulation.setDeviceMetricsOverride',{width:w,height:h,deviceScaleFactor:1,mobile:w<600});}async function nav(h,sel='#app'){await c.send('Page.navigate',{url:url(h)});await waitFor(`document.readyState==='complete' && document.querySelector(${JSON.stringify(sel)})`,9000);await new Promise(r=>setTimeout(r,180));}async function click(sel){await evalJS(`(()=>{const e=document.querySelector(${JSON.stringify(sel)}); if(!e)return false; e.scrollIntoView({block:'center',behavior:'instant'}); e.click(); return true})()`);await new Promise(r=>setTimeout(r,150));}async function setInput(sel,val){await evalJS(`(()=>{const e=document.querySelector(${JSON.stringify(sel)}); e.focus(); e.value=${JSON.stringify(val)}; e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true})); return e.value;})()`);await new Promise(r=>setTimeout(r,120));}async function setSelect(sel,val){await evalJS(`(()=>{const e=document.querySelector(${JSON.stringify(sel)}); e.value=${JSON.stringify(val)}; e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true})); return e.value;})()`);await new Promise(r=>setTimeout(r,120));}async function snap(name,full=false){const res=await c.send('Page.captureScreenshot',{format:'png',fromSurface:true,captureBeyondViewport:full});const p=path.join(outDir,name+'.png');fs.writeFileSync(p,Buffer.from(res.data,'base64'));evidence.push('screenshot: '+p);return p}async function clipSnap(name,sel){await evalJS(`(()=>{const e=document.querySelector(${JSON.stringify(sel)}); if(e) e.scrollIntoView({block:'center',behavior:'instant'});})()`);await new Promise(r=>setTimeout(r,200));const r=await evalJS(`(()=>{const e=document.querySelector(${JSON.stringify(sel)}); if(!e)return null; const b=e.getBoundingClientRect(); return {x:Math.max(0,Math.round(b.left)),y:Math.max(0,Math.round(b.top)),width:Math.round(Math.min(innerWidth,b.width)),height:Math.round(Math.min(innerHeight,b.height))};})()`);if(r&&r.width>10&&r.height>10){const full=await c.send('Page.captureScreenshot',{format:'png'});const p=path.join(outDir,name+'-full.png');fs.writeFileSync(p,Buffer.from(full.data,'base64'));fs.writeFileSync(path.join(outDir,name+'-rect.json'),JSON.stringify(r));evidence.push('screenshot(pending crop): '+p);}}
await viewport(1440,1050);await nav('products','[data-product-card]');let res=await evalJS(`(()=>{const body=document.body.innerText; const cards=[...document.querySelectorAll('[data-product-card]')]; const products=window.__ELEMENTS_PRODUCTS__||[]; const imgs=[...document.images].map(i=>({src:i.getAttribute('src'),complete:i.complete,nw:i.naturalWidth})); return {body,count:cards.length,dataCount:products.length,imgs};})()`);assert(res.count===13,`product cards ${res.count} != 13`);assert(res.dataCount===13,`product data ${res.dataCount} != 13`);for(const [id,n,conc,price,batch,code] of expected){assert(res.body.includes(n),'missing '+n);assert(res.body.includes(conc),'missing '+conc);assert(res.body.includes(price),'missing '+price);assert(res.body.includes(batch),'missing '+batch);}assert(res.imgs.every(i=>i.complete&&i.nw>0),'one or more product images not loaded');evidence.push('Product hard check PASS: 13/13 names, concentrations, prices, batches, image loads (product code shown on detail/batch pages by design).');await setInput('#searchInput','nad');let r=await evalJS(`(()=>({count:document.querySelectorAll('[data-product-card]').length,text:document.body.innerText}))()`);assert(r.count===1&&r.text.includes('NAD+')&&r.text.includes('500 mg'),'search nad failed');await setInput('#searchInput','');await setSelect('#sortFilter','price-desc');r=await evalJS(`(()=>{const card=document.querySelector('[data-product-card]');return {name:card.querySelector('h3').innerText,price:card.querySelector('.price').innerText};})()`);assert(r.name==='Epithalon'&&r.price.includes('94,90'),'sort price-desc failed');evidence.push('Catalog interactions PASS: search and sort.');
for(const h of ['home','products','quality','batch-lookup','about','faq','contact','cart','legal-impressum','legal-datenschutz']){await nav(h,'#app');const body=await evalJS('document.body.innerText');assert(body.length>220,'route too short '+h);assert(!/\b(DEMO|SAMPLE|TEST|PLACEHOLDER|MOCKUP|PROTOTYPE)\b/.test(body),'visible banned marker on '+h);assert(!/Atomlogo|DNA|Molecule|molecule/i.test(body),'old logo marker on '+h);}evidence.push('Public route scan PASS: banned visible markers 0; old atom/DNA/molecule references 0.');
for(const [id,n,conc,price,batch,code] of expected){await nav('product='+id,'[data-coa]');const body=await evalJS('document.body.innerText');assert(body.includes(n)&&body.includes(conc)&&body.includes(price)&&body.includes(batch)&&body.includes(code),'product detail incomplete '+id);assert(!/\b(DEMO|SAMPLE|TEST|PLACEHOLDER|MOCKUP|PROTOTYPE)\b/.test(body),'banned marker on detail '+id);}evidence.push('Product detail PASS: 13/13 complete and no banned public markers.');
for(const [id,n,conc,price,batch,code] of expected){await nav('batch='+encodeURIComponent(batch),'#batchResult');r=await evalJS(`(()=>{const body=document.body.innerText; const img=document.querySelector('.qr'); return {body,complete:img&&img.complete,nw:img&&img.naturalWidth,src:img&&img.getAttribute('src')};})()`);assert(r.body.includes(n)&&r.body.includes(conc)&&r.body.includes(batch)&&r.body.includes(code),'batch incomplete '+batch);assert(r.complete&&r.nw>0,'QR not loaded '+batch);if(file.includes('standalone'))assert(String(r.src).startsWith('data:image/png;base64,'),'standalone QR not data URL '+batch);}evidence.push('Batch PASS: 13/13 batch IDs resolve with QR.');
await nav('home');await evalJS(`localStorage.removeItem('elementsCart'); cart={}; render(); true`);await nav('products','[data-add="bpc-157"]');await click('[data-add="bpc-157"]');await click('[data-add="nad-plus"]');await nav('cart','#cartTotal');r=await evalJS(`(()=>({text:document.body.innerText,total:document.querySelector('#cartTotal').innerText,count:document.querySelector('#cartCount').innerText}))()`);assert(r.text.includes('BPC-157')&&r.text.includes('NAD+')&&r.total.includes('69,80')&&r.count==='2','cart add/total failed');await click('button[data-qty="bpc-157"][data-delta="1"]');await waitFor(`document.querySelector('#cartTotal').innerText.includes('94,70')`);await click('button[data-remove="nad-plus"]');r=await evalJS(`(()=>({text:document.body.innerText,total:document.querySelector('#cartTotal').innerText,count:document.querySelector('#cartCount').innerText}))()`);assert(r.text.includes('BPC-157')&&!r.text.includes('NAD+')&&r.total.includes('49,80')&&r.count==='2','cart remove failed');evidence.push('Cart PASS: add, remove, quantity, total.');
for(const [w,h,hash] of [[390,950,'home'],[430,950,'home'],[768,1050,'home'],[1440,1050,'home'],[1920,1080,'home'],[390,950,'products'],[390,950,'cart'],[390,950,'quality'],[390,950,'batch-lookup']]){await viewport(w,h);await nav(hash,'#app');const ov=await evalJS(`(()=>{const de=document.documentElement; const bad=[...document.querySelectorAll('body *')].map(el=>{const b=el.getBoundingClientRect();return {cls:String(el.className||''),right:Math.round(b.right),left:Math.round(b.left),width:Math.round(b.width)}}).filter(x=>x.width>0&&(x.right>de.clientWidth+2||x.left<-2)).slice(0,6);return {overflow:de.scrollWidth-de.clientWidth,bad};})()`);assert(ov.overflow<=2&&ov.bad.length===0,`overflow ${w} ${hash} ${JSON.stringify(ov)}`);}evidence.push('Responsive PASS: 390, 430, 768, 1440, 1920 and key mobile routes.');
await viewport(1440,1050);await nav('home');await snap('desktop-home',true);await clipSnap('hero-close-up','.hero-photo');await viewport(390,950);await nav('home');await snap('mobile-home',true);await viewport(1440,1050);await nav('products','[data-product-card]');await snap('product-grid',true);await nav('product=bpc-157','.gallery-main');await snap('product-detail-bpc-157',true);await clipSnap('vial-close-up','.gallery-main');await nav('product=epithalon','.gallery-main');await snap('product-detail-epithalon',true);await nav('home');await clipSnap('family-grid','.family-grid');await clipSnap('quality-batch','.quality-batch-grid');await nav('quality');await snap('quality',true);await nav('batch=EL-AMQ5-26001','#batchResult');await snap('batch-lookup',true);await nav('cart','#cartTotal');await snap('cart',true);
await c.send('Target.closeTarget',{targetId:t.targetId},null).catch(()=>{});c.close();const result={file,failures,evidence,consoleErrors:[...new Set(c.errors)]};const out=path.join(root,'evidence',file.includes('standalone')?'production_qa_standalone.json':'production_qa_index.json');fs.writeFileSync(out,JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));process.exit((failures.length||result.consoleErrors.length)?1:0);})().catch(e=>{console.error(e.stack||e);process.exit(2);});
'''

STATIC_QA = r'''
from pathlib import Path
import json, re, sys
root = Path(sys.argv[1])
html = (root / '_standalone.html').read_text(encoding='utf-8')
fail=[]
if re.search(r'<script\s+[^>]*src=', html, re.I): fail.append('script src remains')
if re.search(r'<link\s+[^>]*stylesheet', html, re.I): fail.append('stylesheet link remains')
if re.search(r'(C:\\Users|C:/Users)', html): fail.append('absolute Windows path remains')
outside = re.sub(r'<script\b.*?</script>', '', html, flags=re.I|re.S)
bad = re.findall(r'\b(?:src|href)=["\'](?!#|mailto:|tel:|https?:|data:)[^"\']+', outside, re.I)
if bad: fail.append('relative html dependency remains '+json.dumps(bad[:10]))
products = json.loads(re.search(r'<script id="productData" type="application/json">(.*?)</script>', html, re.S).group(1))
if len(products)!=13: fail.append('product data count !=13')
for key in ['name','concentration','price','batch','code','image','detailImage','qr']:
    if any(not p.get(key) for p in products): fail.append('missing '+key)
for p in products:
    for key in ['image','detailImage','macroImage','packagingImage','qr']:
        if not str(p.get(key,'')).startswith('data:image/'): fail.append(f'{p["id"]} {key} not inlined')
public_text = re.sub(r'<script\b.*?</script>', '', html, flags=re.I|re.S)
public_text = re.sub(r'<style\b.*?</style>', '', public_text, flags=re.I|re.S)
if re.search(r'\b(DEMO|SAMPLE|TEST|MOCKUP|PROTOTYPE)\b', public_text, re.I): fail.append('banned public marker remains in HTML shell')
if re.search(r'\bPLACEHOLDER\b(?!\s*[:{])', public_text, re.I): fail.append('banned public marker (placeholder) remains in HTML shell')
if fail:
    print('FAIL standalone static: '+ '; '.join(dict.fromkeys(fail))); sys.exit(1)
print('PASS standalone static: self-contained HTML, products=13, images/QR inlined, banned shell markers=0')
'''


RESEARCH_PROFILES = {
    "bpc-157": {
        "id": "bpc-157",
        "research_class": "Synthetisches Pentadecapeptid (gastroprotektiv/regenerativ)",
        "molecular_type": "Peptid, 15 Aminosaeuren (Gastric Pentadecapeptide, Sequenz aus Magensaft-Protein abgeleitet)",
        "research_focus": "Praeklinische Forschung zu Gewebereparatur: Sehnen-, Band-, Muskel- und Knochenheilung, gastrointestinale Zytoprotektion, Angiogenese, Endothelschutz",
        "mechanism_summary": "In Tiermodellen wird eine Foerderung der Angiogenese ueber VEGFR2-Aktivierung und den Akt-eNOS-Signalweg (Stickstoffmonoxid-Produktion) beschrieben. Weitere untersuchte Signalwege umfassen ERK1/2 (mit c-Fos, c-Jun, Egr-1), FAK-Paxillin (Zelladhaesion/-migration) sowie eine Modulation von Wachstumshormonrezeptor-Expression in Sehnenfibroblasten. Zusaetzlich werden entzuendungsmodulierende Effekte (Reduktion von COX-2, IL-6, TNF-alpha) sowie Interaktionen mit dopaminergen/serotonergen Systemen berichtet.",
        "research_context": "BPC-157 wurde erstmals 1993 aus humanem Magensaft isoliert und ist seit den 1990er-Jahren Gegenstand einer umfangreichen Zahl praeklinischer Studien einer kroatischen Forschungsgruppe (Sikiric et al.) sowie zunehmend anderer Labore, die sich mit Wundheilung, GI-Laesionen und muskuloskelettaler Regeneration befassen.",
        "evidence_summary": "Die Evidenzbasis besteht ueberwiegend aus Nager- und Kaninchenmodellen (Sehnen-, Band-, Muskeltranssektion, Frakturheilung, GI-Fisteln, Kolitis). Eine systematische Uebersichtsarbeit (HSS Journal 2025) identifizierte 36 Studien, davon 35 praeklinisch und lediglich 1 klinische (retrospektive) Studie. Eine Phase-II-Studie zur Colitis ulcerosa (PL-14736) wurde konferenzberichtet, jedoch nie vollstaendig peer-reviewed publiziert; ein 2015 begonnener Phase-I-Sicherheitstrial (NCT02637284) wurde 2016 ohne veroeffentlichte Ergebnisse abgebrochen. Eine kleine 2025er Pilotstudie (n=2, intravenoes) berichtete keine akuten Nebenwirkungen.",
        "key_research_topics": [
            "Angiogenese (VEGFR2/Akt/eNOS-Signalweg)",
            "Sehnen-, Band- und Muskelheilung in Nagermodellen",
            "Gastrointestinale Zytoprotektion und Fistelheilung",
            "Entzuendungsmodulation (COX-2, IL-6, TNF-alpha)",
            "Frakturheilung (Kaninchen-Nonunion-Modell)",
            "Dopaminerge/serotonerge Modulation im ZNS"
        ],
        "limitations": "Nahezu die gesamte Evidenz stammt aus Tiermodellen (Ratte, Kaninchen, Schwein); kontrollierte randomisierte Humanstudien fehlen. Die einzige beim Menschen erhobene Wirksamkeitsdaten (retrospektive Kniepatienten-Kohorte, n=12) ist unkontrolliert. Die FDA stufte BPC-157 2023 als Kategorie-2-Bulk-Substanz mit ungeklaerter Sicherheitslage ein; mehrere Sportverbaende (WADA, UFC, NFL) haben die Substanz verboten.",
        "research_status": "Ausschliesslich praeklinisch/experimentell; keine behoerdliche Zulassung fuer eine therapeutische Indikation; in mehreren Laendern/Sportverbaenden reguliert oder verboten",
        "references": [
            {
                "author": "Sikiric P, Seiwerth S, Rucman R, et al.",
                "journal": "Current Pharmaceutical Design",
                "year": "2011",
                "identifier": "PMID: 21548867",
                "url": "https://pubmed.ncbi.nlm.nih.gov/21548867/"
            },
            {
                "author": "Sikiric P, Seiwerth S, Rucman R, et al.",
                "journal": "Current Medicinal Chemistry",
                "year": "2012",
                "identifier": "PMID: 22300085",
                "url": "https://pubmed.ncbi.nlm.nih.gov/22300085/"
            },
            {
                "author": "Systematic Review Authors (HSS Journal)",
                "journal": "HSS Journal: The Musculoskeletal Journal of Hospital for Special Surgery",
                "year": "2025",
                "identifier": "PMID: 40756949",
                "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12313605/"
            },
            {
                "author": "Sikiric P, Hahm KB, Blagaic AB, et al.",
                "journal": "Gut and Liver",
                "year": "2020",
                "identifier": "PMID: 31158953",
                "url": "https://www.gutnliver.org/journal/view.html?doi=10.5009%2Fgnl18490"
            }
        ]
    },
    "tb-500": {
        "id": "tb-500",
        "research_class": "Synthetisches Peptid-Fragment / kommerzielle Bezeichnung fuer Thymosin-Beta-4-verwandte Produkte",
        "molecular_type": "Peptid; TB-500 wird in der wissenschaftlichen Literatur als kommerzielle Bezeichnung fuer synthetische, mit Thymosin-Beta-4 (Tb4, 43 Aminosaeuren) verwandte Produkte behandelt",
        "research_focus": "Praeklinische Forschung zu Zellmigration, Angiogenese und Geweberegeneration ueber Aktin-Sequestrierung; Schwerpunkte in Wund-/Hautheilung, vaskulaerer/endothelialer Forschung und okulaeren Modellen",
        "mechanism_summary": "Der am besten charakterisierte Mechanismus von Thymosin-Beta-4 ist die reversible Sequestrierung von G-Aktin ueber eine WH2-Domaene, die die Zellmigration durch Lamellipodienbildung foerdert. Daneben werden eine Hochregulation von VEGF-A (teilweise ueber nukleaere MRTF-A-Interaktion), Notch-Signalwege bei der Angiogenese, PI3K/Akt/eNOS-Signaltransduktion sowie eine Modulation von NF-kB-vermittelter Entzuendung beschrieben.",
        "research_context": "Thymosin Beta-4 ist ein natuerlich vorkommendes, weit verbreitetes Peptid mit gut dokumentierter Rolle in Zellmigration und Wundheilung (Goldstein, Kleinman u.a., seit den 1990er-Jahren). Die Bezeichnung TB-500 wird ueberwiegend im kommerziellen/Freizeit-Kontext fuer synthetische Praeparate verwendet, deren direkte Erforschung deutlich sparsamer ist als jene von Tb4 selbst.",
        "evidence_summary": "Ein Scoping Review (Applied Sciences, 2026) katalogisierte 80 eingeschlossene Studien zu Tb4/TB-500 aus PubMed, Europe PMC und ClinicalTrials.gov; 87,5% der Interventionsstudien betrafen Tb4, nur eine Studie direkt TB-500 (limitiert auf Metabolitennachweis und In-vitro-Fibroblasten-Screening). Humanevidenz war auf okulaere/kornea- und Haut-/Wundmodelle konzentriert; direkte muskuloskelettale Humanevidenz fuer TB-500 fehlt weitgehend. Fuer Tb4 existieren fruehe klinische Studien zu dermalen Wunden und Augenverletzungen (Goldstein/Kleinman-Gruppe).",
        "key_research_topics": [
            "G-Aktin-Sequestrierung (WH2-Domaene) und Zellmigration",
            "Angiogenese ueber VEGF-A, Notch- und PI3K/Akt/eNOS-Signalwege",
            "Dermale Wundheilung in diabetischen und gealterten Maeusemodellen",
            "Kornea-/Augenepithelheilung",
            "Kardioprotektion nach Ischaemie (praeklinisch)",
            "Entzuendungsmodulation via NF-kB"
        ],
        "limitations": "Direkte Studien zu TB-500 als eigenstaendiger Wirkstoff sind extrem selten; die Mehrheit der zitierten Mechanismus- und Wirksamkeitsdaten bezieht sich auf Thymosin Beta-4 (Tb4), nicht auf das kommerziell als TB-500 vertriebene Produkt, dessen Aequivalenz zu Tb4 in der Literatur uneinheitlich behandelt wird. Muskuloskelettale Gewebekategorien (Sehne, Band, Muskel, Bandscheibe) sind in der Evidenzbasis unterrepraesentiert; Humanevidenz mit direktem Bezug zu muskuloskelettalen Anwendungen ist limitiert.",
        "research_status": "Ueberwiegend praeklinisch/in-vitro; fuer Tb4 vereinzelte fruehe klinische Studien (Haut, Auge, Herz), fuer TB-500 spezifisch nahezu keine direkte Humanevidenz; keine behoerdliche Zulassung",
        "references": [
            {
                "author": "Scoping Review Authors",
                "journal": "Applied Sciences (MDPI)",
                "year": "2026",
                "identifier": "DOI: 10.3390/app16126202",
                "url": "https://doi.org/10.3390/app16126202"
            },
            {
                "author": "Goldstein AL, Hannappel E, Sosne G, Kleinman HK",
                "journal": "Expert Opinion on Biological Therapy",
                "year": "2012",
                "identifier": "PMID: 22074294",
                "url": "https://pubmed.ncbi.nlm.nih.gov/22074294"
            },
            {
                "author": "Treadwell T, Kleinman HK, Crockford D, Hardy MA, Guarnera GT, Goldstein AL",
                "journal": "Annals of the New York Academy of Sciences",
                "year": "2012",
                "identifier": "PMID: 23050815",
                "url": "https://pubmed.ncbi.nlm.nih.gov/23050815"
            },
            {
                "author": "Philp D, Badamchian M, Scheremeta B, Nguyen M, Goldstein AL, Kleinman HK",
                "journal": "Wound Repair and Regeneration",
                "year": "2003",
                "identifier": "PMID: 12581423",
                "url": "https://pubmed.ncbi.nlm.nih.gov/12581423"
            }
        ]
    },
    "ghk-cu": {
        "id": "ghk-cu",
        "research_class": "Kupfer-Tripeptid-Komplex (Kollagen-abgeleitetes Signalpeptid)",
        "molecular_type": "Tripeptid-Kupfer(II)-Komplex, Glycyl-L-Histidyl-L-Lysin (GHK) gebunden an Cu2+",
        "research_focus": "Forschung zu Hautregeneration, Kollagen-/Elastinsynthese, Wundheilung und Genexpressionsmodulation",
        "mechanism_summary": "GHK ist eine Sequenz aus der Alpha-2(I)-Kette von Typ-I-Kollagen und wird bei Gewebeschaedigung proteolytisch freigesetzt; der Komplex mit Cu(II) gilt als biologisch relevante Form. Beschriebene Mechanismen umfassen Stimulation der Kollagen-, Glykosaminoglykan- und Decorin-Synthese, Modulation von Metalloproteinasen (MMP1/2) und deren Inhibitoren (TIMP1), Kupfer-abhaengige Aktivierung von Lysyloxidase fuer Kollagenvernetzung sowie breite Effekte auf die Genexpression (laut Connectivity-Map-Analysen Modulation eines relevanten Anteils des menschlichen Genoms).",
        "research_context": "GHK wurde 1973 aus humanem Plasma isoliert; die Konzentration im Plasma sinkt nachweislich mit dem Alter (ca. 200 ng/mL bei 20 Jahren vs. 80 ng/mL bei 60 Jahren). Seit den 1980er-Jahren (Maquart et al.) als moegliches fruehes Signalmolekuel der Hautreparatur untersucht; umfangreiche kosmetische Dermatologie-Forschung seit den 1990er-Jahren (Pickart et al.).",
        "evidence_summary": "Im Gegensatz zu BPC-157 und TB-500 existieren fuer GHK-Cu mehrere randomisierte, placebokontrollierte klinische Studien am Menschen im kosmetischen/dermatologischen Bereich (z.B. Gesichtscremes ueber 12 Wochen bei photogealterter Haut, n=71; periokulaere Anwendung, n=41), die Verbesserungen von Hautdichte, Faltentiefe und Kollagenproduktion zeigten. Fuer chronische Wunden (diabetische Fussulzera, venoese Ulzera) bleibt die Evidenz auf Tiermodelle und kleine Beobachtungsdaten beschraenkt. Die topische Hautpenetration insbesondere liposomaler Formulierungen gilt methodisch als ungeklaerter Bereich.",
        "key_research_topics": [
            "Kollagen- und Elastinsynthese in Hautfibroblasten",
            "Genexpressionsmodulation (Connectivity-Map-Analysen)",
            "Wundheilung in diabetischen und ischaemischen Nagermodellen",
            "Kosmetische Anti-Aging-Studien (randomisiert, placebokontrolliert)",
            "Nerven- und Gefaessneubildung (Neurotrophine, SPARC-Protein-Fragmente)",
            "Antioxidative und entzuendungshemmende Effekte"
        ],
        "limitations": "Klinische Evidenz beschraenkt sich weitgehend auf kosmetische/dermatologische Endpunkte an intakter Haut; direkte Studien zu chronischen oder komplexen Wunden beim Menschen sind rar. Die Hautpenetration des hydrophilen Peptids bleibt ein methodisch ungeloestes Problem, das die klinische Translation limitiert. Der Wirkstoff ist zudem empfindlich gegenueber enzymatischem Abbau (Carboxypeptidasen) in Wundmilieus.",
        "research_status": "Kombination aus praeklinischer Forschung und mehreren klinischen kosmetischen Studien am Menschen; breit in kosmetischen Produkten eingesetzt, jedoch nicht als Arzneimittel fuer Wundheilungsindikationen zugelassen",
        "references": [
            {
                "author": "Pickart L, Margolina A",
                "journal": "International Journal of Molecular Sciences",
                "year": "2018",
                "identifier": "PMID: 29986520",
                "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6073405/"
            },
            {
                "author": "Pickart L",
                "journal": "Journal of Biomaterials Science, Polymer Edition",
                "year": "2008",
                "identifier": "PMID: 18644225",
                "url": "https://pubmed.ncbi.nlm.nih.gov/18644225"
            },
            {
                "author": "Arul V, et al.",
                "journal": "Journal of Biomedical Materials Research Part B",
                "year": "2005",
                "identifier": "PMID: 15803494",
                "url": "https://pubmed.ncbi.nlm.nih.gov/15803494"
            },
            {
                "author": "Ogorek K, et al.",
                "journal": "Molecules",
                "year": "2025",
                "identifier": "PMID: 39795193",
                "url": "https://pubmed.ncbi.nlm.nih.gov/39795193"
            }
        ]
    },
    "ipamorelin": {
        "id": "ipamorelin",
        "research_class": "Synthetisches Pentapeptid, selektives Growth-Hormone-Secretagogue (GHS-R1a-Agonist)",
        "molecular_type": "Pentapeptid, Aib-His-D-2-Nal-D-Phe-Lys-NH2 (CAS 170851-70-4)",
        "research_focus": "Forschung zur selektiven Stimulation der Wachstumshormon(GH)-Ausschuettung ueber den Ghrelin-Rezeptor (GHS-R1a) ohne relevante Beeinflussung von ACTH, Cortisol oder Prolaktin",
        "mechanism_summary": "Ipamorelin bindet als Agonist an den GHS-R1a-Rezeptor (Ghrelin-Rezeptor) somatotroper Hypophysenzellen und loest ueber eine Gq/PLC/IP3-Kaskade eine kalziumvermittelte Exozytose gespeicherter GH-Vesikel aus. Im Unterschied zu aelteren GH-freisetzenden Peptiden (GHRP-6, GHRP-2) zeigte Ipamorelin in tierexperimentellen Studien (Schwein) selbst bei Dosen ueber dem 200-fachen der GH-wirksamen ED50 keine signifikante Erhoehung von ACTH oder Cortisol.",
        "research_context": "Ipamorelin wurde von Novo Nordisk entwickelt und 1998 von Raun et al. als 'erstes selektives Growth-Hormone-Secretagogue' beschrieben; es entstand aus einem Chemieprogramm, das GHRP-1-Analoga ohne das zentrale Ala-Trp-Dipeptid untersuchte.",
        "evidence_summary": "Die Originalpublikation (Raun et al. 1998) dokumentiert In-vitro-Daten an primaeren Rattenhypophysenzellen sowie In-vivo-Daten an wachen Schweinen zur Rezeptorselektivitaet. Eine Humanstudie (Gobburu et al. 1999) untersuchte Pharmakokinetik/Pharmakodynamik bei gesunden maennlichen Probanden mittels Dosis-Eskalationsdesign (5 Infusionsraten, je n=8) und beschreibt eine terminale Halbwertszeit von ca. 2 Stunden sowie einen GH-Ausschuettungspeak nach ca. 0,67 Stunden. Eine behoerdliche Zulassung fuer eine therapeutische Indikation liegt nicht vor.",
        "key_research_topics": [
            "Selektive GHS-R1a-Rezeptoraktivierung",
            "Pulsatile Wachstumshormon-Ausschuettung",
            "Pharmakokinetik/-dynamik beim Menschen (Dosis-Eskalationsstudie)",
            "Vergleichende Rezeptorselektivitaet gegenueber GHRP-2/GHRP-6",
            "Interaktion mit Somatostatin-vermittelter GH-Suppression",
            "Kombinationsforschung mit GHRH-Analoga (z.B. CJC-1295) in praeklinischen/experimentellen Kontexten"
        ],
        "limitations": "Die zentrale Selektivitaetsstudie (Raun et al. 1998) wurde primaer an Schweinen und Ratten durchgefuehrt; die verfuegbare Humanevidenz (Gobburu et al. 1999) beschraenkt sich auf eine kleine Pharmakokinetik/-dynamik-Studie ohne Wirksamkeitsendpunkte fuer eine spezifische Indikation. Langzeitsicherheits- und Wirksamkeitsdaten beim Menschen fuer therapeutische Anwendungen fehlen; keine grossen randomisierten kontrollierten Studien bekannt.",
        "research_status": "Fruehe klinische Pharmakologie (Phase-I-aehnliche PK/PD-Studie) plus umfangreiche praeklinische tierexperimentelle Charakterisierung; kein zugelassenes Arzneimittel, reiner Forschungsstatus",
        "references": [
            {
                "author": "Raun K, Hansen BS, Johansen NL, et al.",
                "journal": "European Journal of Endocrinology",
                "year": "1998",
                "identifier": "PMID: 9849822",
                "url": "https://pubmed.ncbi.nlm.nih.gov/9849822"
            },
            {
                "author": "Gobburu JV, Agerso H, Jusko WJ, Ynddal L",
                "journal": "Pharmaceutical Research",
                "year": "1999",
                "identifier": "PMID: 10496658",
                "url": "https://pubmed.ncbi.nlm.nih.gov/10496658/"
            }
        ]
    },
    "kpv": {
        "id": "kpv",
        "research_class": "Melanocortin-derived tripeptide",
        "molecular_type": "Tripeptide (Lys-Pro-Val), C-terminal fragment of alpha-MSH (11-13)",
        "research_focus": "Anti-inflammatory signaling in intestinal and dermal tissue models",
        "mechanism_summary": "KPV is the C-terminal tripeptide of alpha-melanocyte-stimulating hormone (alpha-MSH). Preclinical work indicates it is taken up by intestinal epithelial and immune cells via the PepT1 di/tripeptide transporter, after which it inhibits NF-kB and MAP-kinase inflammatory signaling and reduces secretion of pro-inflammatory cytokines (TNF-alpha, IL-1beta, IL-6). Unlike the parent alpha-MSH molecule, KPV's anti-inflammatory action appears largely independent of classical melanocortin receptor (MC1-R) activation and cAMP signaling, pointing instead to a receptor-independent or IL-1beta-pathway-related mode of action.",
        "research_context": "Investigated as a candidate anti-inflammatory research tool for inflammatory bowel disease (IBD) and skin inflammation models, building on decades of alpha-MSH immunomodulation research.",
        "evidence_summary": "Evidence is exclusively preclinical (in vitro cell culture and rodent models). No published human clinical trials were identified. Key preclinical findings: KPV reduced pro-inflammatory cytokine secretion and colitis severity in DSS- and TNBS-induced mouse colitis models via PepT1-mediated uptake (Dalmasso et al., 2008); KPV reduced leukocyte accumulation in a mouse crystal-induced peritonitis model independent of MC1-R/cAMP signaling (Getting et al., 2003); broader alpha-MSH/KPV anti-inflammatory literature reviewed by Luger et al. (2003).",
        "key_research_topics": [
            "NF-kB and MAP-kinase inflammatory signaling inhibition",
            "PepT1-mediated cellular peptide uptake",
            "Rodent colitis models (DSS-, TNBS-induced)",
            "Melanocortin receptor-independent anti-inflammatory activity",
            "IL-1beta pathway interaction"
        ],
        "limitations": "No controlled human trials identified in the literature; all efficacy signals derive from rodent models and cultured cell lines. Pharmacokinetics, dosing, long-term safety, and effects in human inflammatory disease remain uncharacterized. Purity and sourcing are not standardized outside controlled research settings.",
        "research_status": "Preclinical (in vitro and rodent in vivo); not evaluated in registered human clinical trials",
        "references": [
            {
                "author": "Getting SJ, Schioth HB, Perretti M",
                "journal": "Journal of Pharmacology and Experimental Therapeutics",
                "year": 2003,
                "identifier": "PMID 12750433",
                "url": "https://pubmed.ncbi.nlm.nih.gov/12750433/"
            },
            {
                "author": "Dalmasso G, Charrier-Hisamuddin L, Nguyen HTT, Yan Y, Sitaraman S, Merlin D",
                "journal": "Gastroenterology",
                "year": 2008,
                "identifier": "PMID 18061177",
                "url": "https://pubmed.ncbi.nlm.nih.gov/18061177/"
            },
            {
                "author": "Luger TA, Scholzen TE, Brzoska T, Bohm M",
                "journal": "Annals of the New York Academy of Sciences",
                "year": 2003,
                "identifier": "PMID 12851308",
                "url": "https://pubmed.ncbi.nlm.nih.gov/12851308/"
            }
        ]
    },
    "selank": {
        "id": "selank",
        "research_class": "Synthetic tuftsin-derived heptapeptide",
        "molecular_type": "Heptapeptide (Thr-Lys-Pro-Arg-Pro-Gly-Pro), synthetic analog of the immune peptide tuftsin",
        "research_focus": "Anxiolytic and nootropic activity via GABAergic, serotonergic, and enkephalinergic modulation",
        "mechanism_summary": "Selank is a synthetic extension of tuftsin engineered for metabolic stability. Proposed mechanisms include positive allosteric modulation of GABA-A receptor binding, inhibition of enkephalin-degrading enzymes (raising endogenous enkephalin/leu-enkephalin tone), and modulation of expression of genes involved in GABAergic neurotransmission (GABA receptor subunits, transporters, ion channels) in rodent brain tissue. Its interaction with benzodiazepine-site modulators (e.g., diazepam) appears non-additive, suggesting overlapping but distinct binding behavior from classical benzodiazepines.",
        "research_context": "Developed at the Institute of Molecular Genetics of the Russian Academy of Sciences; approved in Russia as a prescription anxiolytic for generalized anxiety disorder and neurasthenia. Outside Russia it remains an investigational research compound.",
        "evidence_summary": "Evidence includes a Russian human clinical study and multiple rodent mechanistic studies. Clinical: a controlled comparison in 62 patients with generalized anxiety disorder/neurasthenia reported anxiolytic efficacy comparable to the benzodiazepine medazepam, without added sedation (Zozulya et al., 2008, published in Russian). Mechanistic/preclinical: inhibition of enkephalin-degrading aminopeptidases in blood serum (Zozulya et al., 2001); altered expression of GABAergic neurotransmission-related genes in rat frontal cortex (Volkova et al., 2016); review of allosteric GABA-receptor modulation and benzodiazepine interaction (Vyunova et al., 2018).",
        "key_research_topics": [
            "GABA-A receptor allosteric modulation",
            "Enkephalin-degrading enzyme inhibition",
            "Gene expression changes in GABAergic neurotransmission",
            "Comparative anxiolytic activity vs. benzodiazepines",
            "Stress-response and cytokine modulation"
        ],
        "limitations": "The principal human clinical data (Zozulya et al., 2008) is a single, older, Russian-language study with limited methodological transparency by current international trial-reporting standards; independent replication in peer-reviewed international journals is limited. Most detailed mechanistic work is in rodent models. Long-term human safety data are sparse outside Russian regulatory use.",
        "research_status": "Approved pharmaceutical in Russia (GAD/neurasthenia); investigational/research-only status in most other jurisdictions; mechanistic evidence base mixed human clinical + rodent preclinical",
        "references": [
            {
                "author": "Vyunova TV, Andreeva LA, Shevchenko KV, Myasoedov NF, Shram SI",
                "journal": "Protein and Peptide Letters",
                "year": 2018,
                "identifier": "PMID 30255741",
                "url": "https://pubmed.ncbi.nlm.nih.gov/30255741"
            },
            {
                "author": "Zozulya AA, Neznamov GG, Siuniakov SA, Kost NV, Zozulia SA, Sokolov OY, Davydova IA, Telesheva ES",
                "journal": "Zhurnal Nevrologii i Psikhiatrii Imeni S.S. Korsakova",
                "year": 2008,
                "identifier": "PMID 18454096",
                "url": "https://pubmed.ncbi.nlm.nih.gov/18454096"
            },
            {
                "author": "Volkova AA, Shadrina MI, Kolomin TA, Andreeva LA, Limborska SA, Myasoedov NF, Dergunova LV",
                "journal": "Frontiers in Pharmacology",
                "year": 2016,
                "identifier": "PMID 26924987",
                "url": "https://pubmed.ncbi.nlm.nih.gov/26924987/"
            },
            {
                "author": "Zozulya AA, Kost NV, Sokolov OY, Gabaeva MV, Grivennikov IA, Andreeva LN, Zolotarev YA, Ivanov SV, Andryushchenko AV, Myasoedov NF, Smulevich AB",
                "journal": "Bulletin of Experimental Biology and Medicine",
                "year": 2001,
                "identifier": "PMID 11550013",
                "url": "https://pubmed.ncbi.nlm.nih.gov/11550013/"
            }
        ]
    },
    "semax": {
        "id": "semax",
        "research_class": "Synthetic ACTH-fragment neuropeptide",
        "molecular_type": "Heptapeptide, synthetic analog of ACTH(4-10) with an added Pro-Gly-Pro tripeptide extension",
        "research_focus": "Neuroprotection and cognitive/neurotrophic modulation via BDNF/NGF signaling",
        "mechanism_summary": "Semax is a non-hormonally-active fragment of adrenocorticotropic hormone (ACTH) engineered for enzymatic stability. Preclinical studies report that intranasal Semax rapidly upregulates brain-derived neurotrophic factor (BDNF) and nerve growth factor (NGF) gene/protein expression in rat hippocampus, frontal cortex, and basal forebrain, with time-dependent, tissue-specific kinetics (early rise within ~90 minutes, return toward baseline by 24 hours). Specific, calcium-dependent binding sites for Semax have been identified in rat basal forebrain membranes, suggesting a distinct (non-ACTH-receptor) binding interaction linked to neurotrophin induction.",
        "research_context": "Developed in Russia and used there as a registered prescription nootropic/neuroprotective drug for stroke and cognitive indications; studied internationally primarily as a preclinical neurotrophin-signaling research tool.",
        "evidence_summary": "Evidence spans rodent mechanistic studies and Russian clinical trials in stroke patients. Mechanistic: Semax stimulated BDNF/trkB expression in rat hippocampus (Dolotov et al., 2006); comparative BDNF/NGF gene expression dynamics across hippocampus, frontal cortex, and retina (Shadrina et al., 2010). Clinical: a Russian trial of early rehabilitation combined with Semax reported increased plasma BDNF and improved motor/functional recovery in ischemic stroke patients (Gusev et al., 2018).",
        "key_research_topics": [
            "BDNF and NGF gene/protein induction",
            "Neurotrophin receptor (trkB) expression modulation",
            "Rodent models of cerebral ischemia and hypoxia",
            "Intranasal delivery pharmacodynamics",
            "Post-stroke rehabilitation and cognitive recovery (Russian clinical use)"
        ],
        "limitations": "Clinical trials are predominantly from Russian research groups and published in Russian-language or regional journals, limiting independent international replication and methodological scrutiny by Western trial standards. Mechanistic BDNF/NGF findings are largely from rodent brain tissue; extrapolation to human neurochemistry is not fully established. Semax is not approved by the FDA/EMA.",
        "research_status": "Approved prescription drug in Russia for stroke/cognitive indications; investigational/research-only status elsewhere; mechanistic evidence base mixed rodent preclinical + Russian clinical",
        "references": [
            {
                "author": "Dolotov OV, Karpenko EA, Inozemtseva LS, Seredenina TS, Levitskaya NG, Rozyczka J, Dubynina EV, Novosadova EV, Andreeva LA, Alfeeva LY, Kamensky AA, Grivennikov IA, Myasoedov NF, Engele J",
                "journal": "Brain Research",
                "year": 2006,
                "identifier": "PMID 16635254",
                "url": "https://pubmed.ncbi.nlm.nih.gov/16635254"
            },
            {
                "author": "Shadrina M, Kolomin T, Agapova T, Agniullin Y, Shram S, Slominsky P, Limborska S, Myasoedov N",
                "journal": "Journal of Molecular Neuroscience",
                "year": 2010,
                "identifier": "PMID 19662538",
                "url": "https://pubmed.ncbi.nlm.nih.gov/19662538"
            },
            {
                "author": "Gusev EI, Martynov MY, Kamchatnov PR, et al.",
                "journal": "Zhurnal Nevrologii i Psikhiatrii Imeni S.S. Korsakova",
                "year": 2018,
                "identifier": "PMID 29798983",
                "url": "https://pubmed.ncbi.nlm.nih.gov/29798983/"
            }
        ]
    },
    "mots-c": {
        "id": "mots-c",
        "research_class": "Mitochondrial-derived peptide (MDP)",
        "molecular_type": "16-amino-acid peptide encoded by a short open reading frame within the mitochondrial 12S rRNA gene",
        "research_focus": "Mitochondrial-nuclear signaling in metabolic regulation, insulin sensitivity, and exercise physiology",
        "mechanism_summary": "MOTS-c is translated from a short open reading frame in mitochondrial DNA and translocates to the nucleus under metabolic stress to regulate nuclear gene expression, acting as a mitochondrial-nuclear retrograde signal. Its primary described target is skeletal muscle, where it inhibits the folate-methionine cycle and downstream de novo purine biosynthesis, causing AICAR accumulation and activation of AMPK. Downstream effects include increased GLUT4-mediated glucose uptake, altered fatty acid oxidation, and modulation of inflammatory signaling (NF-kB) pathways.",
        "research_context": "Discovered in 2015 as part of a broader class of mitochondrial-derived peptides (alongside humanin); investigated as an 'exercise mimetic' candidate and metabolic/aging regulator.",
        "evidence_summary": "Evidence is predominantly preclinical, from rodent and cell-culture studies, with human data limited to correlational exercise-response measurements (not peptide administration trials). Key findings: MOTS-c treatment prevented age- and high-fat-diet-induced insulin resistance and obesity in mice via AMPK activation (Lee et al., 2015); MOTS-c improved physical performance, muscle homeostasis, and running capacity in aged mice, and endogenous MOTS-c rose in human skeletal muscle and plasma after acute exercise (Reynolds et al., 2021 — the exercise-induced-rise finding is in humans; the therapeutic peptide-administration findings are in mice only).",
        "key_research_topics": [
            "AMPK activation via folate-methionine/purine pathway inhibition",
            "Skeletal muscle glucose uptake (GLUT4 translocation)",
            "Age-related physical decline and muscle homeostasis in rodent models",
            "Exercise-induced endogenous MOTS-c levels in humans (observational)",
            "Insulin resistance and diet-induced obesity models"
        ],
        "limitations": "No published interventional human trials of administered MOTS-c peptide were identified; all therapeutic/administration efficacy data are from mouse and cell-culture models. Human evidence is limited to observational measurement of endogenous MOTS-c changes with exercise, which does not establish efficacy or safety of exogenous peptide administration. Long-term safety, pharmacokinetics, and dosing in humans are uncharacterized.",
        "research_status": "Preclinical (rodent and in vitro); human data limited to observational endogenous biomarker studies, not interventional peptide trials",
        "references": [
            {
                "author": "Lee C, Zeng J, Drew BG, Sallam T, Martin-Montalvo A, Wan J, Kim SJ, Mehta H, Hevener AL, de Cabo R, Cohen P",
                "journal": "Cell Metabolism",
                "year": 2015,
                "identifier": "PMID 25738459",
                "url": "https://pubmed.ncbi.nlm.nih.gov/25738459/"
            },
            {
                "author": "Reynolds JC, Lai RW, Woodhead JST, Joly JH, Mitchell CJ, Cameron-Smith D, Lu R, Cohen P, Graham NA, Benayoun BA, Lee C, et al.",
                "journal": "Nature Communications",
                "year": 2021,
                "identifier": "PMID 33473109; doi 10.1038/s41467-020-20790-0",
                "url": "https://www.nature.com/articles/s41467-020-20790-0"
            },
            {
                "author": "Lee C, Kim KH, Cohen P",
                "journal": "Free Radical Biology and Medicine",
                "year": 2016,
                "identifier": "PMID 27216708",
                "url": "https://pubmed.ncbi.nlm.nih.gov/27216708/"
            }
        ]
    },
    "cjc-1295-no-dac": {
        "id": "cjc-1295-no-dac",
        "research_class": "Growth Hormone Secretagogue (GHRH Analog)",
        "molecular_type": "Synthetic peptide (29 amino acids, tetrasubstituted GHRH(1-29) analog, no albumin-binding DAC moiety)",
        "research_focus": "Investigated in vitro and in early-phase human pharmacology studies as a short-acting growth-hormone-releasing hormone receptor (GHRH-R) agonist intended to produce pulsatile, physiological growth hormone (GH) secretion.",
        "mechanism_summary": "CJC-1295 No DAC (also termed Modified GRF (1-29) or tetrasubstituted GRF(1-29)) is the native-sequence core of human GHRH(1-29) carrying four amino acid substitutions (D-Ala2, Gln8, Ala15, Leu27) that confer resistance to cleavage by dipeptidyl peptidase-IV (DPP-IV), the primary enzyme responsible for rapid degradation of endogenous GHRH. It acts as an agonist at the GHRH receptor (GHRHR) on anterior pituitary somatotrophs, activating adenylyl cyclase/cAMP/PKA signaling to stimulate synthesis and pulsatile release of growth hormone, which in turn increases hepatic IGF-1 output. Because it lacks the maleimidopropionamide-lysine linker that allows the related molecule CJC-1295 (with DAC) to covalently bind Cys-34 of serum albumin, it is not retained in circulation and is cleared much faster than the DAC-conjugated form.",
        "research_context": "The tetrasubstituted GHRH(1-29) core was characterized by Jetté et al. (2005) in the process of developing the long-acting albumin-conjugated molecule CJC-1295 (with DAC); the no-DAC (unconjugated) form shares this same stabilized peptide backbone. The isolated contribution of the D-Ala2 substitution to reduced metabolic clearance in humans was established earlier by Soule et al. (1994) using native GHRH(1-29) analogs. The rigorous human pharmacokinetic and pharmacodynamic data that exist for this compound class (Teichman et al. 2006; Ionescu & Frohman 2006) were generated using the DAC-conjugated, long-acting form of CJC-1295, not the no-DAC variant specifically.",
        "evidence_summary": "Evidence for the tetrasubstituted DPP-IV-resistant peptide backbone itself derives from published in vitro DPP-IV stability assays and in vivo rat pituitary/GH secretion experiments (Jetté et al., 2005, rat model). Human GH/IGF-1 pharmacodynamic data (dose-dependent, multi-day GH and IGF-1 elevation; preserved pulsatile GH secretion) were obtained specifically with the DAC-conjugated, albumin-binding form of CJC-1295 in healthy adult volunteers (Teichman et al., 2006; Ionescu & Frohman, 2006). No dedicated, peer-reviewed human pharmacokinetic or pharmacodynamic study of the unconjugated (no-DAC) peptide alone has been identified in the literature search underlying this profile; commonly cited half-life figures (~30 minutes) for the no-DAC form are derived from its structural design rationale (loss of the albumin anchor) rather than from a dedicated clinical PK trial.",
        "key_research_topics": [
            "GHRH receptor agonism and pituitary somatotroph signaling (cAMP/PKA pathway)",
            "DPP-IV resistance conferred by D-Ala2/Gln8/Ala15/Leu27 substitutions",
            "Comparison of pulsatile GH secretion patterns versus sustained GH elevation (no-DAC vs. DAC-conjugated forms)",
            "Metabolic clearance and half-life determinants of modified GHRH(1-29) analogs",
            "Downstream IGF-1 induction via hepatic GH receptor signaling"
        ],
        "limitations": "Direct, dedicated human pharmacokinetic/pharmacodynamic data for the no-DAC (unconjugated) peptide specifically are sparse in the peer-reviewed literature; most rigorous human GH/IGF-1 response data available for this peptide class were generated using the distinct, longer-acting DAC-conjugated molecule and cannot be assumed to transfer quantitatively to the no-DAC form. No clinical development program advanced this specific unconjugated peptide to regulatory approval for any indication; it is not an approved drug and has research-use status only.",
        "research_status": "Preclinical/early translational research compound; foundational peptide chemistry and DPP-IV stability data are rat/in-vitro based, while human GH-axis pharmacodynamic data in the literature pertain to the related DAC-conjugated molecule rather than this no-DAC form specifically. Not FDA-approved for any indication.",
        "references": [
            {
                "author": "Jetté L, Léger R, Thibaudeau K, Benquet C, Robitaille M, Pellerin I, Paradis V, van Wyk P, Pham K, Bridon DP",
                "journal": "Endocrinology",
                "year": "2005",
                "identifier": "PMID: 15817669; doi:10.1210/en.2004-1286",
                "url": "https://pubmed.ncbi.nlm.nih.gov/15817669/"
            },
            {
                "author": "Teichman SL, Neale A, Lawrence B, Gagnon C, Castaigne JP, Frohman LA",
                "journal": "Journal of Clinical Endocrinology & Metabolism",
                "year": "2006",
                "identifier": "PMID: 16352683",
                "url": "https://pubmed.ncbi.nlm.nih.gov/16352683/"
            },
            {
                "author": "Ionescu M, Frohman LA",
                "journal": "Journal of Clinical Endocrinology & Metabolism",
                "year": "2006",
                "identifier": "PMID: 17018654",
                "url": "https://pubmed.ncbi.nlm.nih.gov/17018654/"
            },
            {
                "author": "Soule S, King JA, Millar RP",
                "journal": "Journal of Clinical Endocrinology & Metabolism",
                "year": "1994",
                "identifier": "PMID: 7962295; doi:10.1210/jcem.79.4.7962295",
                "url": "https://pubmed.ncbi.nlm.nih.gov/7962295/"
            }
        ]
    },
    "nad-plus": {
        "id": "nad-plus",
        "research_class": "Metabolic Cofactor / Cellular Energetics Research Compound",
        "molecular_type": "Endogenous dinucleotide coenzyme (nicotinamide adenine dinucleotide); research typically uses NAD+ itself or its biosynthetic precursors (e.g., nicotinamide riboside, nicotinamide mononucleotide)",
        "research_focus": "Studied as a central cellular redox coenzyme and signaling substrate whose age-related decline is investigated as a potential contributor to metabolic dysfunction, and whose restoration via direct administration or precursor supplementation is studied for effects on cellular energetics, insulin sensitivity, and markers of aging.",
        "mechanism_summary": "NAD+ serves a dual biological role: as a hydride-carrying coenzyme in hundreds of redox reactions central to glycolysis, the TCA cycle, and oxidative phosphorylation, and as a consumed co-substrate for NAD+-dependent signaling enzymes including sirtuins (SIRT1-7), poly(ADP-ribose) polymerases (PARPs), and the ectoenzyme CD38. Because NAD+ is continuously consumed by these enzymes, cellular levels depend on ongoing salvage synthesis from precursors such as nicotinamide, nicotinamide riboside (NR), and nicotinamide mononucleotide (NMN); NAD+ itself has limited direct cellular uptake, making precursor-based or formulation-based delivery strategies a central focus of the field.",
        "research_context": "NAD+ biology in aging was framed as a major geroscience target following the 2018 review by Rajman, Chwalek and Sinclair summarizing preclinical in vivo evidence for NAD-boosting molecules across models of aging, neurodegeneration, and metabolic disease. Human translational work has focused predominantly on the precursors NR and NMN rather than on direct NAD+ administration, given bioavailability constraints; a 2021 randomized controlled trial (Yoshino/Klein group) tested NMN specifically in postmenopausal women with prediabetes, and a 2025 review (Vinten et al., Nature Metabolism) critically summarized clinical evidence for NAD+ precursor supplementation across tissues.",
        "evidence_summary": "Preclinical rodent studies (reviewed in Rajman et al., 2018) report that restoring NAD+ levels via precursor administration in aged or diseased animals can improve markers of metabolic, cardiovascular, and neurological health and, in some models, extend lifespan; this preclinical evidence is broad but derived largely from mouse models, not humans. In humans, a randomized, placebo-controlled, double-blind trial of oral NMN (250 mg/day for 10 weeks) in postmenopausal women with prediabetes found improved skeletal-muscle insulin sensitivity and insulin signaling without a measurable increase in muscle NAD+ content itself, and without change in body composition or fasting glucose (Yoshino et al., Science, 2021). A 2025 review (Vinten et al., Nature Metabolism) concludes that evidence for an age-related NAD+ decline in human tissues is inconsistent across studies and that human clinical trials of NAD+ precursors have shown only limited and tissue-specific efficacy to date, underscoring a substantial preclinical-to-clinical translation gap.",
        "key_research_topics": [
            "NAD+ as a co-substrate for sirtuins, PARPs, and CD38",
            "Age-related decline in tissue NAD+ levels: human evidence versus rodent models",
            "Precursor pharmacology: nicotinamide riboside (NR) and nicotinamide mononucleotide (NMN) bioavailability and salvage pathway kinetics",
            "Skeletal muscle insulin sensitivity and insulin signaling responses to NMN supplementation",
            "Circulating versus intracellular NAD+ compartments and their distinct biomarker correlates",
            "Translational gap between preclinical rodent efficacy and human clinical trial outcomes"
        ],
        "limitations": "Evidence for age-related NAD+ decline in human tissues is inconsistent across studies and not uniformly reproducible; human clinical trials of NAD+ precursors have generally shown modest, tissue-specific, or absent effects relative to the pronounced benefits reported in rodent models. Direct oral NAD+ has substantially different pharmacokinetics from its precursors and is degraded extensively in the gut before systemic absorption, so preclinical or precursor-based findings should not be assumed to generalize to direct NAD+ administration. Most rigorous human RCT data available concern specific precursors (NR, NMN) in narrow populations (e.g., postmenopausal prediabetic women) over short durations (weeks), limiting generalizability.",
        "research_status": "Active clinical and preclinical research area; several human RCTs of NAD+ precursors have been completed, but findings are mixed and evidence for direct NAD+ administration in humans remains comparatively sparse. No NAD+ or NAD+-precursor product is FDA-approved as a drug for anti-aging or metabolic indications; supplement-marketed forms are not equivalent to the standardized research material referenced in the cited literature.",
        "references": [
            {
                "author": "Rajman L, Chwalek K, Sinclair DA",
                "journal": "Cell Metabolism",
                "year": "2018",
                "identifier": "PMID: 29514064; doi:10.1016/j.cmet.2018.02.011",
                "url": "https://pubmed.ncbi.nlm.nih.gov/29514064/"
            },
            {
                "author": "Yoshino M, Yoshino J, Kayser BD, Patti GJ, Franczyk MP, Mills KF, Sindelar M, Pietka T, Patterson BW, Imai SI, Klein S",
                "journal": "Science",
                "year": "2021",
                "identifier": "PMID: 33888596; doi:10.1126/science.abe9985",
                "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8550608/"
            },
            {
                "author": "Vinten KT, Trętowicz MM, Coskun E, van Weeghel M, Cantó C, Zapata-Pérez R, Janssens GE, Houtkooper RH",
                "journal": "Nature Metabolism",
                "year": "2025",
                "identifier": "PMID: 41083806; doi:10.1038/s42255-025-01387-7",
                "url": "https://www.nature.com/articles/s42255-025-01387-7"
            }
        ]
    },
    "5-amino-1mq": {
        "id": "5-amino-1mq",
        "research_class": "Nicotinamide N-Methyltransferase (NNMT) Inhibitor",
        "molecular_type": "Small-molecule quinolinium compound (5-amino-1-methylquinolinium), not a peptide",
        "research_focus": "Investigated in preclinical rodent models as a selective, membrane-permeable inhibitor of nicotinamide N-methyltransferase (NNMT), an enzyme implicated in adipocyte energy metabolism, for effects on diet-induced obesity, hepatic steatosis, glucose tolerance, and skeletal muscle regeneration.",
        "mechanism_summary": "5-Amino-1MQ inhibits NNMT, the cytosolic enzyme that transfers a methyl group from S-adenosylmethionine (SAM) to nicotinamide (NAM), producing 1-methylnicotinamide (1-MNA). By blocking this reaction, 5-Amino-1MQ is reported to increase intracellular NAD+ and SAM availability (since less nicotinamide and methyl-donor capacity is diverted through the NNMT reaction) and to suppress lipogenesis in adipocytes; proposed downstream effects include increased NAD+-dependent SIRT1 activity. In diet-induced obese (DIO) mouse models, this mechanism has been linked to reduced fat mass accumulation, improved glucose tolerance and insulin sensitivity, and reduced hepatic triglyceride accumulation, generally without significant changes in food intake.",
        "research_context": "5-Amino-1MQ was identified and characterized by Neelakantan, Watowich and colleagues at the University of Texas Medical Branch as part of a structure-activity relationship program developing membrane-permeable quinolinium-based NNMT inhibitors (foundational report: Neelakantan et al., Biochemical Pharmacology, 2018). The same research group subsequently extended this work to aged skeletal muscle regeneration (Neelakantan et al., 2019) and, together with collaborators, to prediabetic/metabolic phenotypes and pharmacokinetics in DIO mice (Babula et al., Diabetes, Obesity and Metabolism, 2024). Related studies from the same group examined combined NNMT inhibition with calorie-restricted diet in obese mice.",
        "evidence_summary": "All identified evidence for 5-Amino-1MQ is preclinical, generated in cultured adipocyte/myoblast cell systems and in diet-induced obese mouse models; no human clinical trial data for this compound were identified. Key preclinical findings include: dose-dependent limitation of body weight and fat mass gain without altering food intake in DIO mice; improved oral glucose tolerance and suppressed hyperinsulinemia; reduced hepatic steatosis, liver weight, and liver triglycerides; and, in a separate line of work, activation of senescent muscle stem cells and improved regenerative capacity in aged mouse skeletal muscle following injury. In vitro selectivity assays reported no meaningful inhibition of related SAM-dependent methyltransferases, NAMPT, or SIRT1 at pharmacologically relevant concentrations, supporting mechanistic specificity for NNMT within the tested assay panel.",
        "key_research_topics": [
            "NNMT inhibition and adipocyte lipogenesis suppression",
            "Body composition, fat mass, and hepatic steatosis outcomes in diet-induced obese mice",
            "Glucose tolerance and insulin sensitivity in prediabetic mouse phenotypes",
            "Skeletal muscle stem cell (muSC) senescence reversal and regenerative capacity in aged mice",
            "Selectivity profiling against related methyltransferases and NAD+ salvage pathway enzymes",
            "Pharmacokinetics and tissue distribution following subcutaneous dosing in mice",
            "Combined NNMT inhibition with calorie-restricted diet and effects on gut microbiome composition"
        ],
        "limitations": "All available evidence is derived from in vitro cell culture systems and rodent (primarily mouse) models; no human pharmacokinetic, safety, or efficacy data for 5-Amino-1MQ were identified in the literature reviewed. The compound has poor oral bioavailability in mice (subcutaneous dosing is typically used in murine studies), and pharmacokinetic behavior has been reported to differ between species (e.g., rats versus mice), which constrains extrapolation. Long-term safety, chronic dosing tolerability, and carcinogenicity/genotoxicity data in any species were not identified in the sources reviewed for this profile.",
        "research_status": "Early-stage preclinical research compound; used as a pharmacological tool/probe molecule for NNMT target validation in academic research settings. Not approved by any regulatory agency for human use, and no registered human clinical trials were identified.",
        "references": [
            {
                "author": "Neelakantan H, Vance V, Wetzel MD, Wang HL, McHardy SF, Finnerty CC, Hommel JD, Watowich SJ",
                "journal": "Biochemical Pharmacology",
                "year": "2018",
                "identifier": "PMID: 29155147; doi:10.1016/j.bcp.2017.11.007",
                "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5826726/"
            },
            {
                "author": "Neelakantan H, Brightwell CR, Graber TG, Maroto R, Wang HYL, McHardy SF, Papaconstantinou J, Fry CS, Watowich SJ",
                "journal": "Biochemical Pharmacology",
                "year": "2019",
                "identifier": "PMID: 30753815; doi:10.1016/j.bcp.2019.02.008",
                "url": "https://www.sciencedirect.com/science/article/abs/pii/S0006295219300462"
            },
            {
                "author": "Babula JAJ, Bui D, Stevenson HL, Watowich SJ, Neelakantan H",
                "journal": "Diabetes, Obesity and Metabolism",
                "year": "2024",
                "identifier": "PMID: 39161060; doi:10.1111/dom.15879",
                "url": "https://pubmed.ncbi.nlm.nih.gov/39161060/"
            }
        ]
    },
    "bpc-157-tb-500": {
        "id": "bpc-157-tb-500",
        "research_class": "Regenerative / Tissue-Repair Peptide Combination",
        "molecular_type": "Peptide blend: BPC-157 (synthetic gastric pentadecapeptide, 15 amino acids) + TB-500 (synthetic fragment of Thymosin beta-4, a 43-amino-acid actin-binding protein)",
        "research_focus": "Preclinical investigation of combined angiogenic, cytoprotective, and actin-mediated cell-migration pathways relevant to tendon, ligament, muscle, and soft-tissue repair models.",
        "mechanism_summary": "BPC-157 is studied for modulation of the nitric oxide (NO) system via the Akt-eNOS axis, VEGFR2-mediated angiogenesis, ERK1/2 signaling, and upregulation of growth-hormone receptor expression in tendon fibroblasts, with reported cytoprotective and anti-inflammatory activity across gastrointestinal and musculoskeletal injury models. TB-500 is the synthetic analogue of the LKKTETQ actin-binding domain of Thymosin beta-4; the parent molecule sequesters G-actin, promotes keratinocyte and endothelial cell migration, reduces myofibroblast-driven scarring/fibrosis, and has documented roles in dermal wound healing and cardiac progenitor cell mobilization. Combination protocols are hypothesized (not established) to act on complementary steps of the repair cascade -- BPC-157 upstream on vascularization/growth-factor signaling, TB-500 on cytoskeletal reorganization and cell motility -- but dedicated combination pharmacology data are sparse.",
        "research_context": "Both peptides originate from distinct discovery programs: BPC-157 was isolated from human gastric juice (Sikiric et al., early 1990s) and studied predominantly in rodent tendon-transection, muscle-crush, and GI-ulcer models. TB-500 derives from decades of Thymosin beta-4 research in wound healing, corneal repair, and cardiac regeneration. The pairing (colloquially the 'Wolverine stack' in non-academic peptide-research communities) reflects mechanistic-complementarity reasoning rather than a body of peer-reviewed combination trials; a 2026 scoping review found only a single included study directly evaluating TB-500 itself, with the bulk of Thymosin beta-4 literature using the full-length native protein, not the TB-500 fragment.",
        "evidence_summary": "Evidence for BPC-157 is exclusively preclinical: rodent Achilles-tendon transection, muscle-crush, and ligament models report accelerated healing, increased tendon fibroblast outgrowth, angiogenesis, and GH-receptor upregulation. A 2025 narrative review (McGuire et al.) identified only three small human pilot studies (intra-articular knee pain, interstitial cystitis, IV safety/pharmacokinetics) with no controlled efficacy trials. TB-500/Thymosin beta-4 evidence is broader for the parent molecule (in vitro, animal wound-healing, and Phase II dermal-wound human trials) but a 2026 scoping review (McGuire, Hughes, Maak, Cushman; 80 studies from 1,772 records) found direct musculoskeletal tissue categories (tendon, ligament, muscle, cartilage, spine/disc) comparatively sparse, human evidence concentrated in ocular/cornea and skin/wound settings, and only one study evaluating TB-500 specifically. No peer-reviewed studies were identified that test the BPC-157 + TB-500 combination directly in a controlled design; claims of synergy in commercial/community sources are mechanistic extrapolation, not experimental confirmation.",
        "key_research_topics": [
            "Angiogenesis and VEGF/VEGFR2 signaling in tendon and muscle repair",
            "Nitric oxide (NO) pathway and Akt-eNOS modulation (BPC-157)",
            "G-actin sequestration and cytoskeletal-driven cell migration (TB-500/Thymosin beta-4)",
            "Tendon-to-bone and ligament healing models",
            "Anti-inflammatory and anti-fibrotic (myofibroblast-reducing) activity",
            "Gastrointestinal mucosal cytoprotection (BPC-157-specific)",
            "Cardiac and corneal repair research (Thymosin beta-4 parent molecule)"
        ],
        "limitations": "Human data for BPC-157 are limited to three small uncontrolled pilot studies; no randomized controlled trials exist. TB-500-specific (versus full-length Thymosin beta-4) evidence is minimal -- a 2026 scoping review located only one study directly testing TB-500. No controlled study has evaluated the two-peptide combination; synergy claims are mechanistic hypotheses. Neither compound is approved by the FDA, EMA, or comparable regulatory bodies for any clinical indication; BPC-157 is explicitly listed as prohibited by WADA in some sport contexts. Long-term safety, dosing standardization, and pharmacokinetics in humans remain uncharacterized.",
        "research_status": "Preclinical (animal/in vitro) for both compounds individually; no controlled human efficacy trials; no peer-reviewed data on the combination. Research-use-only status -- not approved for human therapeutic use.",
        "references": [
            {
                "author": "McGuire FP, Martinez R, Lenz A, Skinner L, Cushman DM",
                "journal": "Current Reviews in Musculoskeletal Medicine",
                "year": "2025",
                "identifier": "PMID: 40789979; DOI: 10.1007/s12178-025-09990-7",
                "url": "https://pubmed.ncbi.nlm.nih.gov/40789979/"
            },
            {
                "author": "Staresinic M, Sebecic B, Patrlj L, Jadrijevic S, Suknaic S, Perovic D, et al.",
                "journal": "Journal of Orthopaedic Research",
                "year": "2003",
                "identifier": "PMID: 14554208",
                "url": "https://pubmed.ncbi.nlm.nih.gov/14554208/"
            },
            {
                "author": "Seiwerth S, Rucman R, Turkovic B, Sever M, Klicek R, Radic B, et al.",
                "journal": "Current Pharmaceutical Design",
                "year": "2018",
                "identifier": "PMID: 29998800",
                "url": "https://pubmed.ncbi.nlm.nih.gov/29998800/"
            },
            {
                "author": "Goldstein AL, Hannappel E, Sosne G, Kleinman HK",
                "journal": "Expert Opinion on Biological Therapy",
                "year": "2012",
                "identifier": "PMID: 22074294",
                "url": "https://pubmed.ncbi.nlm.nih.gov/22074294/"
            },
            {
                "author": "McGuire F, Hughes E, Maak T, Cushman DM",
                "journal": "Applied Sciences",
                "year": "2026",
                "identifier": "DOI: 10.3390/app16126202",
                "url": "https://www.mdpi.com/2076-3417/16/12/6202"
            }
        ]
    },
    "epithalon": {
        "id": "epithalon",
        "research_class": "Longevity / Neuroendocrine Bioregulator Peptide",
        "molecular_type": "Synthetic tetrapeptide, Ala-Glu-Asp-Gly (AEDG), CAS 307297-39-8, synthetic analogue of the natural pineal gland extract Epithalamin/Epithalamine",
        "research_focus": "Cellular senescence and telomerase biology, pineal gland function and melatonin regulation, and long-term geroprotective outcomes in aged model organisms and observational human cohorts.",
        "mechanism_summary": "Epithalon is studied for induction of telomerase catalytic subunit expression and enzymatic activity in telomerase-negative human somatic cell cultures, associated with telomere elongation and extended replicative capacity beyond the normal Hayflick limit in vitro. A proposed direct peptide-chromatin interaction (short acidic peptides binding AT-rich promoter regions, including the hTERT promoter) has been advanced by the originating research group as a mechanism distinct from classical receptor-ligand signaling, though this 'peptide bioregulation' model has not been independently mechanistically confirmed outside the Khavinson research network. Separately, Epithalon/Epithalamin is studied for restoration of age-related decline in pineal melatonin synthesis, with downstream effects reported on circadian rhythm, antioxidant enzyme activity (SOD, glutathione peroxidase), and neuroendocrine-immune parameters in aged animals and elderly human subjects.",
        "research_context": "Epithalon was developed by Prof. Vladimir Khavinson and colleagues at the St. Petersburg Institute of Bioregulation and Gerontology (Russia) as a synthetic short-peptide mimic of the natural bovine pineal extract Epithalamin/Epithalamine. The research program spans in vitro telomerase/chromatin studies, rodent and invertebrate lifespan/tumor-incidence experiments, and multi-year observational human cohorts in elderly and geriatric populations, largely originating from one research group and its direct collaborators in Russia and Ukraine; independent replication outside this network is limited.",
        "evidence_summary": "In vitro: Khavinson, Bondarev, and Butyugov (2003) reported that Epithalon induced telomerase catalytic subunit expression, enzymatic activity, and telomere elongation in telomerase-negative human fetal fibroblast cultures, a finding frequently cited as the mechanistic anchor for telomerase claims; a related 2004 study reported peptide-associated overcoming of the somatic-cell division limit. Animal studies: multiple Anisimov/Khavinson rodent studies (CBA mice, SHR mice, HER-2/neu transgenic mice, Drosophila) reported increased maximum lifespan (on the order of 10-25% in some cohorts) and reduced spontaneous or induced tumor incidence (mammary, colon) with cyclic Epitalon/Epithalamin administration, alongside comparable studies showing melatonin itself increased tumor incidence in some models -- underscoring model-dependent and non-uniform effects. Human evidence: is exclusively observational/uncontrolled, most notably a 6-8 year follow-up of 266 elderly persons (Khavinson & Morozov, 2003) reporting reduced mortality with Thymalin and/or Epithalamin courses, and a 12-year follow-up in elderly coronary-disease patients (Korkushko et al., 2006) reporting improved cardiovascular outcomes with Epithalamin added to standard care. These human studies used the natural extract (Epithalamin), not necessarily the synthetic tetrapeptide, were unblinded, lacked placebo control, and originate from a single research network.",
        "key_research_topics": [
            "Telomerase activation and telomere elongation in human somatic cell cultures",
            "Chromatin remodeling / direct peptide-DNA interaction hypothesis (hTERT promoter)",
            "Pineal gland melatonin synthesis and circadian rhythm regulation",
            "Lifespan extension and spontaneous tumor incidence in rodent and invertebrate models",
            "Oxidative stress markers (SOD, glutathione peroxidase, lipid peroxidation) in aged tissue",
            "Long-term observational cohorts in elderly and cardiovascular-aging human populations"
        ],
        "limitations": "The overwhelming majority of Epithalon/Epithalamin publications originate from one research group (Khavinson and close collaborators) with limited independent replication. Human data are observational and uncontrolled, without randomization, blinding, or placebo arms in the cited long-term cohorts. In vitro telomerase induction has not been confirmed by an independently mechanistically distinct pathway, and the proposed direct-chromatin-binding model remains a hypothesis specific to this research network. Telomerase reactivation is a hallmark of most human cancers, so a chronic risk-benefit relationship in humans is not established despite reduced tumor incidence reported in some rodent cohorts. Epithalon is not approved by the FDA, EMA, or any comparable regulatory body for any indication and is distributed only as a research compound.",
        "research_status": "Preclinical (in vitro cell culture, rodent/invertebrate lifespan studies) plus long-term uncontrolled human observational cohorts using the related natural extract Epithalamin; no randomized controlled human clinical trials of the synthetic tetrapeptide have been identified. Research-use-only status.",
        "references": [
            {
                "author": "Khavinson VKh, Bondarev IE, Butyugov AA",
                "journal": "Bulletin of Experimental Biology and Medicine",
                "year": "2003",
                "identifier": "PMID: 12937682; DOI: 10.1023/A:1025493705728",
                "url": "https://pubmed.ncbi.nlm.nih.gov/12937682/"
            },
            {
                "author": "Khavinson VK, Morozov VG",
                "journal": "Neuroendocrinology Letters",
                "year": "2003",
                "identifier": "PMID: 14523363",
                "url": "https://pubmed.ncbi.nlm.nih.gov/14523363/"
            },
            {
                "author": "Korkushko OV, Khavinson VK, Shatilo VB, Antonyuk-Shcheglova IA",
                "journal": "Bulletin of Experimental Biology and Medicine",
                "year": "2006",
                "identifier": "PMID: 17426848; DOI: 10.1007/s10517-006-0365-z",
                "url": "https://pubmed.ncbi.nlm.nih.gov/17426848/"
            },
            {
                "author": "Anisimov VN, Khavinson VK, Popovich IG, Zabezhinski MA, Alimova IN, Rosenfeld SV, et al.",
                "journal": "Biogerontology",
                "year": "2003",
                "identifier": "PMID: 14501183; DOI: 10.1023/A:1025114230714",
                "url": "https://pubmed.ncbi.nlm.nih.gov/14501183/"
            },
            {
                "author": "Anisimov VN, Khavinson VK, Mikhalski AI, Yashin AI",
                "journal": "Mechanisms of Ageing and Development",
                "year": "2001",
                "identifier": "PMID: 11163623; DOI: 10.1016/S0047-6374(00)00184-6",
                "url": "https://pubmed.ncbi.nlm.nih.gov/11163623/"
            }
        ]
    }
}


def build_html(products, inline=False):
    icon = data_url(LOGOS / 'el-icon-light.svg')
    logo = data_url(LOGOS / 'el-primary-light.svg') if inline else 'assets/logos/el-primary-light.svg'
    icon_logo = data_url(LOGOS / 'el-icon-light.svg') if inline else 'assets/logos/el-icon-light.svg'
    fonts_css = font_face_css(inline)
    pdata = json.dumps(products, ensure_ascii=False, separators=(',', ':'))
    rdata = json.dumps(RESEARCH_PROFILES, ensure_ascii=False, separators=(',', ':'))
    css_part = f'<style>{fonts_css}{CSS}</style>' if inline else f'<style>{fonts_css}</style><link rel="stylesheet" href="styles.css" />'
    js_part = f'<script>{APP}</script>' if inline else '<script src="app.js"></script>'
    return dedent(f'''<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ELEMENTS LABS — Research Compounds & Documentation</title>
    <meta name="description" content="ELEMENTS LABS: research-grade peptides and compounds with batch traceability, product specifications and QR verification. Research use only." />
  <link rel="icon" href="{icon}" />
  {css_part}
</head>
<body>
  <a href="#app" class="skip-link">Zum Hauptinhalt springen</a>
  <header class="site-header" id="top">
    <a class="brand" href="#home" aria-label="ELEMENTS LABS Home"><img class="brand-desktop" src="{logo}" alt="ELEMENTS LABS"><img class="brand-mobile" src="{icon_logo}" alt="ELEMENTS LABS"></a>
    <button class="menu-toggle" id="menuToggle" aria-expanded="false" aria-controls="mainNav">Menu</button>
    <nav id="mainNav" class="main-nav" aria-label="Hauptnavigation">
      <a href="#products">Products</a><a href="#quality">Quality</a><a href="#batch-lookup">Batch Lookup</a><a href="#about">About</a><a href="#faq">FAQ</a>
    </nav>
    <div class="header-actions"><button class="search-open" data-action="focus-search">Search</button><a class="cart-link" href="#cart">Cart <span id="cartCount">0</span></a></div>
  </header>
  <main id="app" tabindex="-1"></main>
  <script id="productData" type="application/json">{pdata}</script>
  <script id="researchData" type="application/json">{rdata}</script>
  {js_part}
  <footer class="footer">
    <div><strong>ELEMENTS LABS</strong><p>Research-grade compounds for laboratory use. Consistent packaging, batch traceability and documented specifications across the full portfolio.</p></div>
    <div><a href="#legal-impressum">Impressum</a><a href="#legal-datenschutz">Datenschutz</a><a href="#contact">Support</a></div>
    <div><strong>Research Notice</strong><p>Not for human consumption. No therapeutic, diagnostic, veterinary or dosing claims.</p></div>
    <div class="research-only">Research Use Only · No Human Consumption · No Medical Claims</div>
  </footer>
  <div id="toast" role="status" aria-live="polite"></div>
</body>
</html>
''')


def standalone_products():
    data = []
    for p in PRODUCTS:
        q = dict(p)
        for key in ['image','detailImage','macroImage','packagingImage','qr']:
            q[key] = data_url(ROOT / q[key])
        data.append(q)
    return data


def main():
    write_qr_codes(PRODUCTS)
    write_logos()
    product_assets()
    scene_assets()
    (ROOT / 'styles.css').write_text(CSS, encoding='utf-8')
    (ROOT / 'app.js').write_text(APP, encoding='utf-8')
    (ROOT / 'index.html').write_text(build_html(PRODUCTS, inline=False), encoding='utf-8')
    (ROOT / '_standalone.html').write_text(build_html(standalone_products(), inline=True), encoding='utf-8')
    (ROOT / 'qa' / 'cdp_production_qa.js').write_text(QA_JS, encoding='utf-8')
    (ROOT / 'qa' / 'standalone_static_check.py').write_text(STATIC_QA, encoding='utf-8')
    print('Built ELEMENTS LABS production assets and site')
    print(json.dumps({
        'products': len(PRODUCTS),
        'logos': sorted(p.name for p in LOGOS.glob('*')),
        'scenes': sorted(p.name for p in SCENES.glob('*')),
        'product_images': len(list(PRODUCTS_DIR.glob('*.png'))),
    }, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
