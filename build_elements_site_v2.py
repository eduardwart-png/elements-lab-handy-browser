from __future__ import annotations

import base64
import json
import math
import random
from pathlib import Path
from textwrap import dedent

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops, ImageEnhance

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


def text_center(draw, xy, text, fnt, fill, anchor='mm'):
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


def add_noise(img, amount=9, alpha=18):
    w, h = img.size
    noise = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    px = noise.load()
    for _ in range(int(w * h * amount / 9000)):
        x = random.randrange(w); y = random.randrange(h)
        v = random.randrange(255)
        px[x, y] = (v, v, v, random.randrange(0, alpha))
    return Image.alpha_composite(img.convert('RGBA'), noise)


# V6 CORE RANGE — 13 public SKUs (PLANNING_PRICE, no live batch release)
PRODUCTS = [
    dict(id='bpc-157', num='01', name='BPC-157', concentration='10 mg', price='39,90 €', code='EL-BPC-010', batch='EL-BPC10-26001', category='Tissue Research', featured=True, price_status='PLANNING_PRICE', desc='Research compound for tissue biology, cytoprotection and angiogenesis studies.'),
    dict(id='tb-500', num='02', name='TB-500', concentration='10 mg', price='69,90 €', code='EL-TB5-010', batch='EL-TB510-26001', category='Tissue Research', featured=True, price_status='PLANNING_PRICE', desc='Thymosin Beta-4 fragment research compound for actin-mediated cell migration models.'),
    dict(id='ipamorelin', num='03', name='Ipamorelin', concentration='10 mg', price='39,90 €', code='EL-IPA-010', batch='EL-IPA10-26001', category='Endocrine Research', featured=False, price_status='PLANNING_PRICE', desc='Research compound for GH receptor and signaling model systems.'),
    dict(id='kpv', num='04', name='KPV', concentration='10 mg', price='54,90 €', code='EL-KPV-010', batch='EL-KPV10-26001', category='Tripeptide Research', featured=True, price_status='PLANNING_PRICE', desc='Alpha-MSH-derived tripeptide for immunomodulation and intestinal research models.'),
    dict(id='selank', num='05', name='Selank', concentration='10 mg', price='34,90 €', code='EL-SEL-010', batch='EL-SEL10-26001', category='Neuropeptide Research', featured=False, price_status='PLANNING_PRICE', desc='Heptapeptide for neurochemical and GABA-ergic research models.'),
    dict(id='semax', num='06', name='Semax', concentration='10 mg', price='34,90 €', code='EL-SMX-010', batch='EL-SMX10-26001', category='Neuropeptide Research', featured=False, price_status='PLANNING_PRICE', desc='ACTH-derived research compound for BDNF and peptide signaling pathway models.'),
    dict(id='mots-c-10', num='07', name='MOTS-C', concentration='10 mg', price='39,90 €', code='EL-MOT-010', batch='EL-MOT10-26001', category='Mitochondrial Research', featured=True, price_status='PLANNING_PRICE', desc='Mitochondria-derived peptide for mitochondrial-nuclear retrograde signaling research.'),
    dict(id='mots-c-20', num='08', name='MOTS-C', concentration='20 mg', price='59,90 €', code='EL-MOT-020', batch='EL-MOT20-26001', category='Mitochondrial Research', featured=False, price_status='PLANNING_PRICE', desc='Mitochondria-derived peptide for mitochondrial-nuclear retrograde signaling research.'),
    dict(id='mots-c-40', num='09', name='MOTS-C', concentration='40 mg', price='89,90 €', code='EL-MOT-040', batch='EL-MOT40-26001', category='Mitochondrial Research', featured=False, price_status='PLANNING_PRICE', desc='Mitochondria-derived peptide for mitochondrial-nuclear retrograde signaling research.'),
    dict(id='cjc-1295-no-dac', num='10', name='CJC-1295 No DAC', concentration='10 mg', price='54,90 €', code='EL-CJC-010', batch='EL-CJC10-26001', category='Endocrine Research', featured=False, price_status='PLANNING_PRICE', desc='Mod GRF 1-29 research compound for GH secretagogue receptor model studies.'),
    dict(id='5-amino-1mq', num='11', name='5-Amino-1MQ', concentration='10 mg', price='59,90 €', code='EL-AMQ-010', batch='EL-AMQ10-26001', category='Metabolic Research', featured=True, price_status='PLANNING_PRICE', desc='Small molecule NNMT inhibitor for metabolic and NAD+ pathway research.'),
    dict(id='bpc-157-tb-500', num='12', name='BPC-157 + TB-500', concentration='10 mg + 10 mg', price='74,90 €', code='EL-BT5-010', batch='EL-BT510-26001', category='Research Bundle', featured=True, price_status='PLANNING_PRICE', desc='Dual tissue research bundle for angiogenesis and cell migration model studies.'),
    dict(id='epithalon', num='13', name='Epithalon', concentration='10 mg', price='29,90 €', code='EL-EPI-010', batch='EL-EPI10-26001', category='Longevity Research', featured=True, price_status='PLANNING_PRICE', desc='Tetrapeptide for telomerase activation and longevity research models.'),
]

for product in PRODUCTS:
    product['image'] = f'assets/products/{product["id"]}-vial.png'
    product['detailImage'] = f'assets/products/{product["id"]}-detail.png'
    product['macroImage'] = 'assets/scenes/macro-detail.png'
    product['packagingImage'] = 'assets/scenes/packaging-shot.png'
    product['qr'] = f'img/qr-{product["batch"]}.png'


def write_qr_codes(products):
    import qrcode
    for p in products:
        qr_path = ROOT / p['qr']
        qr_path.parent.mkdir(parents=True, exist_ok=True)
        payload = f"https://eduardwart-png.github.io/elements-lab-handy-browser/#batch={p['batch']}"
        img = qrcode.make(payload, border=2)
        img = img.resize((300, 300))
        img.save(qr_path)


# ---------------------------------------------------------------------------
# EL MONOGRAM v3 — true interlocking geometric E + L
# ---------------------------------------------------------------------------

def draw_el_mark(d: ImageDraw.ImageDraw, x, y, s, dark=True):
    """Draw the interlocking EL monogram at position (x,y) with size s (square box)."""
    ink_e = rgba(OFF_WHITE if dark else GRAPHITE, 255) if not dark else rgba(GRAPHITE, 255)
    # NOTE: 'dark' historically meant "for dark backgrounds" -> mark should be light.
    ink_e = rgba(OFF_WHITE, 255) if dark else rgba(GRAPHITE, 255)
    ink_l = rgba(PETROL, 255)
    bar = s * 0.20
    r = max(2, int(bar * 0.16))

    d.rounded_rectangle([x, y, x + bar, y + s], radius=r, fill=ink_e)
    d.rounded_rectangle([x, y, x + s * 0.70, y + bar], radius=r, fill=ink_e)
    mid_y = y + s / 2 - bar / 2
    d.rounded_rectangle([x, mid_y, x + s * 0.52, mid_y + bar], radius=r, fill=ink_e)

    l_x = x + s * 0.52
    d.rounded_rectangle([l_x, y, l_x + bar, y + s], radius=r, fill=ink_l)

    bottom_y = y + s - bar
    split_x = x + s * 0.52
    d.rounded_rectangle([x, bottom_y, split_x + bar, y + s], radius=r, fill=ink_e)
    d.rounded_rectangle([split_x, bottom_y, x + s, y + s], radius=r, fill=ink_l)


def el_mark_svg_path(s=100):
    """Return SVG markup (rects) for the EL monogram at a given box size, colors as placeholders."""
    bar = s * 0.20
    r = round(bar * 0.16, 2)
    l_x = s * 0.52
    mid_y = s / 2 - bar / 2
    bottom_y = s - bar
    split_x = s * 0.52
    parts = [
        f'<rect x="0" y="0" width="{bar:.2f}" height="{s:.2f}" rx="{r}" fill="{{e}}"/>',
        f'<rect x="0" y="0" width="{s*0.70:.2f}" height="{bar:.2f}" rx="{r}" fill="{{e}}"/>',
        f'<rect x="0" y="{mid_y:.2f}" width="{s*0.52:.2f}" height="{bar:.2f}" rx="{r}" fill="{{e}}"/>',
        f'<rect x="{l_x:.2f}" y="0" width="{bar:.2f}" height="{s:.2f}" rx="{r}" fill="{{l}}"/>',
        f'<rect x="0" y="{bottom_y:.2f}" width="{split_x+bar:.2f}" height="{bar:.2f}" rx="{r}" fill="{{e}}"/>',
        f'<rect x="{split_x:.2f}" y="{bottom_y:.2f}" width="{s-split_x:.2f}" height="{bar:.2f}" rx="{r}" fill="{{l}}"/>',
    ]
    return '\n'.join(parts)


def logo_svg(kind='primary', dark=False):
    """kind: primary (icon+wordmark horizontal), secondary (icon over wordmark stacked),
    icon (mark only), badge (seal/circle)."""
    ink = OFF_WHITE if dark else GRAPHITE
    mark_e = OFF_WHITE if dark else GRAPHITE
    mark_l = PETROL
    mark_size = 100

    if kind == 'icon':
        w, h = 140, 140
        mx, my = 20, 20
        mark = el_mark_svg_path(mark_size).format(e=mark_e, l=mark_l)
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<g transform="translate({mx} {my})">{mark}</g>
</svg>'''
        return svg

    if kind == 'secondary':
        w, h = 360, 260
        mx = (w - mark_size) / 2
        my = 20
        mark = el_mark_svg_path(mark_size).format(e=mark_e, l=mark_l)
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<g transform="translate({mx:.1f} {my})">{mark}</g>
<text x="{w/2}" y="182" text-anchor="middle" font-family="'Space Grotesk','Segoe UI',Arial,sans-serif" font-size="30" font-weight="700" letter-spacing="6" fill="{ink}">ELEMENTS</text>
<text x="{w/2}" y="216" text-anchor="middle" font-family="'Space Grotesk','Segoe UI',Arial,sans-serif" font-size="30" font-weight="700" letter-spacing="6" fill="{ink}">LABS</text>
</svg>'''
        return svg

    if kind == 'badge':
        w, h = 280, 280
        mark_size2 = 84
        mx = (w - mark_size2) / 2
        my = 56
        mark = el_mark_svg_path(mark_size2).format(e=mark_e, l=mark_l)
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<circle cx="{w/2}" cy="{h/2}" r="128" fill="none" stroke="{PETROL}" stroke-width="2"/>
<g transform="translate({mx:.1f} {my})">{mark}</g>
<text x="{w/2}" y="206" text-anchor="middle" font-family="'Space Grotesk','Segoe UI',Arial,sans-serif" font-size="19" font-weight="700" letter-spacing="4" fill="{ink}">ELEMENTS</text>
<text x="{w/2}" y="230" text-anchor="middle" font-family="'Space Grotesk','Segoe UI',Arial,sans-serif" font-size="19" font-weight="700" letter-spacing="4" fill="{ink}">LABS</text>
</svg>'''
        return svg

    # primary: icon + horizontal wordmark, sized for ~230px wide desktop header use
    w, h = 620, 160
    mx, my = 26, 30
    mark = el_mark_svg_path(mark_size).format(e=mark_e, l=mark_l)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<g transform="translate({mx} {my})">{mark}</g>
<text x="166" y="76" font-family="'Space Grotesk','Segoe UI',Arial,sans-serif" font-size="40" font-weight="700" letter-spacing="7" fill="{ink}">ELEMENTS</text>
<text x="166" y="120" font-family="'Space Grotesk','Segoe UI',Arial,sans-serif" font-size="40" font-weight="700" letter-spacing="7" fill="{ink}">LABS</text>
</svg>'''
    return svg


def logo_png(path: Path, kind='primary', dark=False):
    svg_map = {'icon': (280, 280), 'secondary': (720, 520), 'badge': (720, 720), 'primary': (1240, 320)}
    size = svg_map.get(kind, (1240, 320))
    scale = size[0] / {'icon': 140, 'secondary': 360, 'badge': 280, 'primary': 620}[kind]
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ink = rgba(OFF_WHITE if dark else GRAPHITE, 255)
    mark_scale = scale

    if kind == 'icon':
        mx, my, ms = 20 * scale, 20 * scale, 100 * scale
        draw_el_mark(d, mx, my, ms, dark=dark)
    elif kind == 'secondary':
        ms = 100 * scale
        mx = (size[0] - ms) / 2
        my = 20 * scale
        draw_el_mark(d, mx, my, ms, dark=dark)
        text_center(d, (size[0] // 2, int(182 * scale)), 'ELEMENTS', font(int(30 * scale), True), ink)
        text_center(d, (size[0] // 2, int(216 * scale)), 'LABS', font(int(30 * scale), True), ink)
    elif kind == 'badge':
        ms = 84 * scale
        mx = (size[0] - ms) / 2
        my = 56 * scale
        d.ellipse([size[0] * 0.5 - 128 * scale, size[1] * 0.5 - 128 * scale, size[0] * 0.5 + 128 * scale, size[1] * 0.5 + 128 * scale], outline=rgba(PETROL, 255), width=max(2, int(2 * scale)))
        draw_el_mark(d, mx, my, ms, dark=dark)
        text_center(d, (size[0] // 2, int(206 * scale)), 'ELEMENTS', font(int(19 * scale), True), ink)
        text_center(d, (size[0] // 2, int(230 * scale)), 'LABS', font(int(19 * scale), True), ink)
    else:  # primary
        mx, my, ms = 26 * scale, 30 * scale, 100 * scale
        draw_el_mark(d, mx, my, ms, dark=dark)
        d.text((166 * scale, 46 * scale), 'ELEMENTS', font=font(int(40 * scale), True), fill=ink)
        d.text((166 * scale, 90 * scale), 'LABS', font=font(int(40 * scale), True), fill=ink)

    img.save(path)


def write_logos():
    for kind in ['primary', 'secondary', 'icon', 'badge']:
        for mode in ['light', 'dark']:
            dark = mode == 'dark'
            (LOGOS / f'el-{kind}-{mode}.svg').write_text(logo_svg(kind, dark), encoding='utf-8')
            logo_png(LOGOS / f'el-{kind}-{mode}.png', kind, dark)


# ---------------------------------------------------------------------------
# PHOTO-REAL VIAL + CONTINUOUS LABEL COMPOSITING
# ---------------------------------------------------------------------------

VIAL_MASTER = BASE / 'vial-master.png'
BOX_MASTER = BASE / 'box-closed-cutout.png'
STUDIO_BG = BASE / 'studio-bg-final-2.jpg'


def paste_qr(base, product, box):
    qr_path = ROOT / product['qr']
    if not qr_path.exists():
        return
    qr = Image.open(qr_path).convert('RGBA').resize((box[2] - box[0], box[3] - box[1]), Image.Resampling.LANCZOS)
    base.alpha_composite(qr, (box[0], box[1]))


def build_continuous_label(product, w, h):
    """One single continuous label panel (no split, no seam) with:
    EL monogram, ELEMENTS LABS wordmark, product name, concentration,
    product code, batch, QR/analysis corner, Research Use Only line."""
    label = Image.new('RGBA', (w, h), rgba(OFF_WHITE, 250))
    label = add_noise(label, amount=6, alpha=10)
    d = ImageDraw.Draw(label)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(h * 0.05), outline=rgba(LINE, 255), width=2)
    d.rectangle([0, 0, w, max(4, int(h * 0.035))], fill=rgba(PETROL, 255))

    pad = int(w * 0.09)
    mark_s = int(h * 0.15)
    draw_el_mark(d, pad, int(h * 0.09), mark_s, dark=False)
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
    """Simulate the label being wrapped on a cylindrical vial: darken/lighten edges
    to suggest curvature (cylindrical light falloff), keep text undistorted (real
    labels on small vials read almost flat at this size, so keep it legible)."""
    label_img = label_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    w, h = label_img.size
    shade = Image.new('L', (w, h), 255)
    sd = ImageDraw.Draw(shade)
    edge = int(w * curvature)
    for x in range(edge):
        k = x / edge
        val = int(255 * (0.55 + 0.45 * k))
        sd.line([(x, 0), (x, h)], fill=val)
    for x in range(w - edge, w):
        k = (w - x) / edge
        val = int(255 * (0.55 + 0.45 * k))
        sd.line([(x, 0), (x, h)], fill=val)
    shaded = ImageChops.multiply(label_img.convert('RGB'), Image.merge('RGB', (shade, shade, shade)))
    out = Image.merge('RGBA', (*shaded.split(), label_img.split()[3]))
    return out


def compose_vial(product, canvas_w=900, canvas_h=1300, label_scale=1.0):
    """Compose one product vial photo: real base photo + continuous wrapped label."""
    vial = Image.open(VIAL_MASTER).convert('RGBA')
    vw, vh = vial.size
    scale = (canvas_h * 0.82) / vh
    new_w, new_h = int(vw * scale), int(vh * scale)
    vial_r = vial.resize((new_w, new_h), Image.Resampling.LANCZOS)

    canvas = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    vx = (canvas_w - new_w) // 2
    vy = canvas_h - new_h - int(canvas_h * 0.03)

    # soft grounded shadow beneath vial
    shadow = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sh_y = vy + new_h - int(new_h * 0.02)
    sd.ellipse([vx - new_w * 0.22, sh_y - 14, vx + new_w * 1.22, sh_y + 30], fill=(13, 17, 21, 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    canvas.alpha_composite(shadow)

    canvas.alpha_composite(vial_r, (vx, vy))

    # label geometry, proportion-matched to this specific vial-master crop
    lab_w = int(new_w * 0.72 * label_scale)
    lab_h = int(new_h * 0.30 * label_scale)
    lab_x = vx + (new_w - lab_w) // 2
    lab_y = vy + int(new_h * 0.395)

    label = build_continuous_label(product, 640, int(640 * lab_h / lab_w))
    label = wrap_label_on_glass(label, lab_w, lab_h)
    canvas.alpha_composite(label, (lab_x, lab_y))

    return canvas


def scene_bg(size, top='#FCFCFD', bottom='#E9EEF0', noise_amt=6, noise_alpha=10):
    bg = linear_gradient(size, top, bottom)
    bg = add_noise(bg, amount=noise_amt, alpha=noise_alpha)
    return bg


def studio_bg_crop(size):
    """Crop a clean region of the real studio photo background (no gradient synth)."""
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

        # detail scene: bigger canvas, vial + packaging box in soft studio backdrop
        bg = studio_bg_crop((1280, 980)).convert('RGBA')
        bg = add_noise(bg, amount=3, alpha=6)
        d = ImageDraw.Draw(bg)

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
    # Hero scene: real studio backdrop + 3 vials + 1 packaging box, grounded on
    # one shared tabletop plane so nothing floats and no dead empty shapes remain.
    hero_photo = studio_bg_crop((1800, 1280)).convert('RGBA')
    bg = hero_photo.copy()
    bg = add_noise(bg, amount=3, alpha=6)
    d = ImageDraw.Draw(bg)

    # shared soft contact-shadow band grounding all objects (no floating look)
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

    positions = [
        (PRODUCTS[10], 660),   # 5-Amino-1MQ, hero center-tall
        (PRODUCTS[9], 500),    # NAD+
        (PRODUCTS[12], 520),   # Epithalon
    ]
    xs = [700, 410, 990]
    ground_y = 1015
    for (p, target_h_v), x in zip(positions, xs):
        vial = compose_vial(p, int(target_h_v * 0.62), target_h_v)
        bg.alpha_composite(vial, (x, ground_y - target_h_v))

    d.text((135, 118), 'ELEMENTS LABS', font=font(34, True), fill=rgba(GRAPHITE, 255))
    d.text((135, 164), 'Premium research product photography', font=font(20), fill=rgba(MUTED, 255))
    bg.save(SCENES / 'hero-studio-scene.png')

    # Group shot — all 13 vials, same geometry, same label grid, real studio backdrop
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
    d.text((120, 88), '13/13 Research Product Family', font=font(42, True), fill=rgba(GRAPHITE, 255))
    d.text((120, 144), 'Identical bottle geometry, identical label grid, identical packaging rule.', font=font(23), fill=rgba(MUTED, 255))
    group.save(SCENES / 'group-product-shot.png')

    # Packaging shot: box + vial next to it, real studio backdrop
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

    # Macro detail — close crop on glass/label edge/cap, real studio backdrop
    macro = studio_bg_crop((1500, 980)).convert('RGBA')
    macro = add_noise(macro, amount=4, alpha=8)
    vial = compose_vial(PRODUCTS[10], 900, 1500, label_scale=1.15)
    macro.alpha_composite(vial, (60, -280))
    md = ImageDraw.Draw(macro)
    md.rounded_rectangle([950, 150, 1400, 370], radius=28, fill=(255, 255, 255, 205), outline=(207, 214, 218, 255), width=2)
    md.text((990, 190), 'Macro detail', font=font(30, True), fill=rgba(GRAPHITE, 255))
    md.text((990, 244), 'Real glass edge · label wrap · graphite crimp cap', font=font(19), fill=rgba(MUTED, 255))
    macro.save(SCENES / 'macro-detail.png')


def data_url(path: Path) -> str:
    ext = path.suffix.lower().lstrip('.')
    mime = {'svg': 'image/svg+xml', 'woff2': 'font/woff2', 'woff': 'font/woff'}.get(ext, f'image/{"jpeg" if ext in ["jpg", "jpeg"] else ext}')
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


print('Part 1 (logo + vial compositing engine) loaded OK')
