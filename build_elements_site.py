from __future__ import annotations

import base64
import json
import math
import random
from pathlib import Path
from textwrap import dedent

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path('C:/Users/eduar/elements-lab-flagship')
ASSETS = ROOT / 'assets'
LOGOS = ASSETS / 'logos'
PRODUCTS_DIR = ASSETS / 'products'
SCENES = ASSETS / 'scenes'
for p in [ASSETS, LOGOS, PRODUCTS_DIR, SCENES, ROOT / 'qa', ROOT / 'evidence', ROOT / 'evidence' / 'screenshots']:
    p.mkdir(parents=True, exist_ok=True)

GRAPHITE = '#2A2F36'
NEAR_BLACK = '#0D1115'
OFF_WHITE = '#F7F7F8'
PETROL = '#0D5B6B'
MUTED = '#6B747D'
LINE = '#D8DDE0'

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


def draw_el_mark(draw: ImageDraw.ImageDraw, x, y, s, dark=True):
    e = rgba(GRAPHITE if dark else OFF_WHITE, 255)
    l = rgba(PETROL, 255)
    u = max(2, int(s / 18))
    # Geometric E
    draw.rounded_rectangle([x, y, x + s * 0.19, y + s], radius=u, fill=e)
    draw.rounded_rectangle([x, y, x + s * 0.58, y + s * 0.18], radius=u, fill=e)
    draw.rounded_rectangle([x, y + s * 0.41, x + s * 0.49, y + s * 0.59], radius=u, fill=e)
    draw.rounded_rectangle([x, y + s * 0.82, x + s * 0.58, y + s], radius=u, fill=e)
    # Geometric L
    lx = x + s * 0.69
    draw.rounded_rectangle([lx, y, lx + s * 0.18, y + s], radius=u, fill=l)
    draw.rounded_rectangle([lx, y + s * 0.82, x + s * 1.18, y + s], radius=u, fill=l)


def logo_svg(kind='primary', dark=False):
    bg = 'none'
    ink = OFF_WHITE if dark else GRAPHITE
    mark_e = OFF_WHITE if dark else GRAPHITE
    mark_l = PETROL
    if kind == 'icon':
        w, h = 180, 180; mark_x, mark_y, s = 38, 34, 86; text = ''
    elif kind == 'secondary':
        w, h = 380, 260; mark_x, mark_y, s = 136, 26, 86; text = '<text x="190" y="184" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="31" font-weight="800" letter-spacing="7" fill="%s">ELEMENTS</text><text x="190" y="220" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="31" font-weight="800" letter-spacing="7" fill="%s">LABS</text>' % (ink, ink)
    elif kind == 'badge':
        w, h = 260, 260; mark_x, mark_y, s = 78, 62, 80; text = '<circle cx="130" cy="130" r="116" fill="none" stroke="%s" stroke-width="2"/><text x="130" y="186" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="21" font-weight="800" letter-spacing="4" fill="%s">ELEMENTS</text><text x="130" y="214" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="21" font-weight="800" letter-spacing="4" fill="%s">LABS</text>' % (PETROL, ink, ink)
    else:
        w, h = 520, 150; mark_x, mark_y, s = 34, 30, 70; text = '<text x="158" y="68" font-family="Segoe UI, Arial, sans-serif" font-size="42" font-weight="800" letter-spacing="8" fill="%s">ELEMENTS</text><text x="158" y="112" font-family="Segoe UI, Arial, sans-serif" font-size="42" font-weight="800" letter-spacing="8" fill="%s">LABS</text>' % (ink, ink)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<rect width="100%" height="100%" fill="{bg}"/>
<g transform="translate({mark_x} {mark_y})">
<rect x="0" y="0" width="16" height="{s}" rx="2" fill="{mark_e}"/>
<rect x="0" y="0" width="50" height="16" rx="2" fill="{mark_e}"/>
<rect x="0" y="{s*0.41:.1f}" width="43" height="16" rx="2" fill="{mark_e}"/>
<rect x="0" y="{s-16}" width="50" height="16" rx="2" fill="{mark_e}"/>
<rect x="{s*0.66:.1f}" y="0" width="16" height="{s}" rx="2" fill="{mark_l}"/>
<rect x="{s*0.66:.1f}" y="{s-16}" width="50" height="16" rx="2" fill="{mark_l}"/>
</g>{text}
</svg>'''
    return svg


def logo_png(path: Path, kind='primary', dark=False):
    if kind == 'icon':
        size = (512, 512); mark = (150, 118, 230)
    elif kind == 'secondary':
        size = (900, 620); mark = (345, 70, 210)
    elif kind == 'badge':
        size = (720, 720); mark = (250, 150, 220)
    else:
        size = (1300, 380); mark = (95, 82, 182)
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ink = rgba(OFF_WHITE if dark else GRAPHITE, 255)
    draw_el_mark(d, mark[0], mark[1], mark[2], dark=not dark)
    if kind == 'badge':
        d.ellipse([42, 42, size[0]-42, size[1]-42], outline=rgba(PETROL, 255), width=6)
        text_center(d, (size[0]//2, 505), 'ELEMENTS', font(56, True), ink)
        text_center(d, (size[0]//2, 585), 'LABS', font(56, True), ink)
    elif kind == 'secondary':
        text_center(d, (size[0]//2, 430), 'ELEMENTS', font(68, True), ink)
        text_center(d, (size[0]//2, 515), 'LABS', font(68, True), ink)
    elif kind == 'primary':
        d.text((385, 112), 'ELEMENTS', font=font(92, True), fill=ink)
        d.text((385, 220), 'LABS', font=font(92, True), fill=ink)
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
    qr = Image.open(qr_path).convert('RGBA').resize((box[2]-box[0], box[3]-box[1]), Image.Resampling.LANCZOS)
    base.alpha_composite(qr, (box[0], box[1]))


def vial_png(product, w=900, h=1100, transparent=True, large_label=False):
    random.seed(product['id'])
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0) if transparent else rgba(OFF_WHITE, 255))
    d = ImageDraw.Draw(img)
    cx = w // 2
    body_w = int(w * .27)
    body_h = int(h * .66)
    top = int(h * .19)
    left = cx - body_w // 2
    right = cx + body_w // 2
    bottom = top + body_h

    # compact grounded contact shadow, not a floating ellipse
    shadow = Image.new('RGBA', (w, h), (0,0,0,0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse([left-58, bottom-18, right+58, bottom+28], fill=(13,17,21,44))
    sd.ellipse([left+20, bottom-7, right-20, bottom+13], fill=(13,17,21,62))
    shadow = shadow.filter(ImageFilter.GaussianBlur(13))
    img.alpha_composite(shadow)

    # body silhouette with shoulders, thick edge, glass depth
    glass = Image.new('RGBA', (w, h), (0,0,0,0))
    gd = ImageDraw.Draw(glass)
    body_points = [(left+22, top+52), (left+48, top+8), (right-48, top+8), (right-22, top+52), (right-8, bottom-70), (right-38, bottom-12), (left+38, bottom-12), (left+8, bottom-70)]
    gd.polygon(body_points, fill=(246,251,252,42))
    gd.line(body_points + [body_points[0]], fill=(139,158,168,82), width=3, joint='curve')
    gd.rounded_rectangle([left+12, top+68, right-12, bottom-22], radius=body_w//2-18, outline=(255,255,255,116), width=3)
    gd.rounded_rectangle([left+body_w*.12, top+42, left+body_w*.22, bottom-90], radius=30, fill=(255,255,255,78))
    gd.rounded_rectangle([right-body_w*.20, top+86, right-body_w*.13, bottom-106], radius=22, fill=(13,91,107,34))
    gd.line([left+34, top+110, left+30, bottom-110], fill=(51,68,79,34), width=2)
    gd.line([right-34, top+108, right-30, bottom-112], fill=(51,68,79,38), width=2)
    gd.ellipse([left+35, bottom-56, right-35, bottom-13], outline=(86,101,112,82), width=3)
    gd.ellipse([left+52, bottom-42, right-52, bottom-22], fill=(226,235,238,34))
    for _ in range(46):
        x = random.randint(left+16, right-16); y = random.randint(top+42, bottom-92)
        gd.line([x, y, x+random.randint(-5,5), y+random.randint(12,36)], fill=(255,255,255,random.randint(10,30)), width=1)
    img.alpha_composite(glass)

    # neck, rubber stopper and ribbed aluminium crimp cap
    cap_w = int(body_w * .72)
    cap_left = cx - cap_w//2
    cap_right = cx + cap_w//2
    neck_top = top - 48
    d.rounded_rectangle([cap_left+18, neck_top+30, cap_right-18, top+42], radius=14, fill=(224,231,234,98), outline=(255,255,255,150), width=2)
    d.ellipse([cap_left+18, top+27, cap_right-18, top+50], fill=(205,215,220,88), outline=(255,255,255,108), width=2)
    cap_grad = Image.new('RGBA', (cap_w, 56), (0,0,0,0))
    cd = ImageDraw.Draw(cap_grad)
    for yy in range(56):
        k = yy/55
        base = int(62*(1-k)+29*k)
        cd.line([(0,yy),(cap_w,yy)], fill=(base,base+5,base+9,255))
    cd.rounded_rectangle([0,0,cap_w-1,55], radius=11, outline=(14,17,20,255), width=2)
    for x in range(7, cap_w-6, 10):
        cd.line([x,7,x-2,49], fill=(120,130,136,145), width=2)
    cd.rounded_rectangle([cap_w*.23, 10, cap_w*.77, 27], radius=6, fill=(13,17,21,245))
    img.alpha_composite(cap_grad, (cap_left, neck_top))

    # label texture and exact label system, intentionally generated by text layer
    lab_w = int(body_w * .88)
    lab_h = int(body_h * (.44 if large_label else .38))
    lab_left = cx - lab_w//2
    lab_top = top + int(body_h * .265)
    label = Image.new('RGBA', (lab_w, lab_h), rgba(OFF_WHITE, 252))
    label = add_noise(label, amount=7, alpha=13)
    ld = ImageDraw.Draw(label)
    ld.rounded_rectangle([0,0,lab_w-1,lab_h-1], radius=7, outline=(204,211,215,255), width=2)
    ld.rectangle([0,0,lab_w,8], fill=rgba(PETROL, 255))
    draw_el_mark(ld, 18, 21, 39, dark=True)
    ld.text((76, 22), 'ELEMENTS LABS', font=font(16, True), fill=rgba(GRAPHITE,255))
    ld.text((76, 45), product['code'], font=font(11, False, True), fill=rgba(MUTED,255))
    ld.line([16, 78, lab_w-16, 78], fill=rgba(LINE,255), width=2)
    name_f = font(31 if len(product['name']) < 12 else 23, True)
    ld.text((lab_w//2, 112), product['name'], font=name_f, fill=rgba(NEAR_BLACK,255), anchor='mm')
    ld.text((lab_w//2, 149), product['concentration'], font=font(22, True), fill=rgba(PETROL,255), anchor='mm')
    ld.line([16, lab_h-78, lab_w-16, lab_h-78], fill=rgba(LINE,255), width=1)
    ld.text((16, lab_h-64), 'Research Use Only', font=font(12, True), fill=rgba(GRAPHITE,255))
    ld.text((16, lab_h-42), product['batch'], font=font(11, False, True), fill=rgba(MUTED,255))
    paste_qr(label, product, (lab_w-66, lab_h-68, lab_w-17, lab_h-19))
    ld.text((lab_w-67, lab_h-17), 'Analysis', font=font(9, False, True), fill=rgba(MUTED,255))
    # Subtle cylindrical light falloff over label edges
    mask = Image.new('L', (lab_w, lab_h), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0,0,lab_w-1,lab_h-1], radius=7, fill=255)
    edge = Image.new('RGBA', (lab_w, lab_h), (0,0,0,0))
    ed = ImageDraw.Draw(edge)
    ed.rectangle([0,0,10,lab_h], fill=(0,0,0,18))
    ed.rectangle([lab_w-10,0,lab_w,lab_h], fill=(0,0,0,14))
    label = Image.alpha_composite(label, edge)
    img.alpha_composite(label, (lab_left, lab_top))
    d.rounded_rectangle([lab_left, lab_top, lab_left+lab_w, lab_top+lab_h], radius=7, outline=(255,255,255,88), width=1)
    # Foreground glass reflection across label/body
    d.rounded_rectangle([left+body_w*.18, top+30, left+body_w*.25, bottom-70], radius=26, fill=(255,255,255,32))
    return img

def draw_box(img, xy, product=None, scale=1.0):
    d = ImageDraw.Draw(img)
    x,y,w,h = xy
    side = [(x+w*.76,y+20),(x+w,y+40),(x+w,y+h-18),(x+w*.76,y+h)]
    front = [x,y,x+w*.78,y+h]
    d.polygon(side, fill=(225,229,230,255), outline=(186,194,198,255))
    d.rounded_rectangle(front, radius=16, fill=rgba(OFF_WHITE,255), outline=(192,199,203,255), width=2)
    d.rectangle([x, y, x+w*.78, y+8], fill=rgba(PETROL,255))
    draw_el_mark(d, x+30, y+34, 50*scale, dark=True)
    d.text((x+96*scale,y+36), 'ELEMENTS LABS', font=font(18 if scale<=1 else 24, True), fill=rgba(GRAPHITE,255))
    if product:
        d.text((x+34,y+h*.47), product['name'], font=font(30 if scale<=1 else 38, True), fill=rgba(NEAR_BLACK,255))
        d.text((x+34,y+h*.58), product['concentration'], font=font(21 if scale<=1 else 28, True), fill=rgba(PETROL,255))
        d.text((x+34,y+h-54), product['batch'], font=font(13 if scale<=1 else 18, False, True), fill=rgba(MUTED,255))
    d.line([x+28,y+h-75,x+w*.72,y+h-75], fill=rgba(LINE,255), width=2)


def product_assets():
    for p in PRODUCTS:
        vial = vial_png(p, 900, 1100, True)
        vial.save(PRODUCTS_DIR / f'{p["id"]}-vial.png')
        bg = linear_gradient((1280, 980), '#FBFCFC', '#E8EEF0')
        bg = add_noise(bg, amount=5, alpha=10)
        d = ImageDraw.Draw(bg)
        # matte tabletop plane and contact shadows placed before products
        d.rounded_rectangle([120, 740, 1160, 865], radius=44, fill=(232,237,239,255), outline=(212,219,222,255), width=2)
        shadow = Image.new('RGBA', bg.size, (0,0,0,0))
        sd = ImageDraw.Draw(shadow)
        sd.ellipse([255, 720, 630, 785], fill=(13,17,21,36))
        sd.ellipse([655, 710, 1030, 800], fill=(13,17,21,28))
        shadow = shadow.filter(ImageFilter.GaussianBlur(18))
        bg.alpha_composite(shadow)
        box_layer = Image.new('RGBA', bg.size, (0,0,0,0))
        draw_box(box_layer, (672, 190, 330, 520), p, .92)
        bg.alpha_composite(box_layer)
        vial_small = vial.resize((540, 660), Image.Resampling.LANCZOS)
        bg.alpha_composite(vial_small, (184, 122))
        # foreground lens/softbox reflections
        gloss = Image.new('RGBA', bg.size, (0,0,0,0))
        gd = ImageDraw.Draw(gloss)
        gd.rounded_rectangle([64, 68, 172, 850], radius=50, fill=(255,255,255,42))
        gd.rounded_rectangle([1088, 80, 1172, 820], radius=42, fill=(255,255,255,30))
        bg = Image.alpha_composite(bg, gloss)
        bg.save(PRODUCTS_DIR / f'{p["id"]}-detail.png')

def scene_assets():
    # Hero scene
    bg = linear_gradient((1800, 1280), '#FCFCFD', '#E9EEF0')
    bg = add_noise(bg, amount=6, alpha=10)
    d = ImageDraw.Draw(bg)
    d.rounded_rectangle([90, 935, 1710, 1135], radius=70, fill=(214,220,223,112))
    d.rounded_rectangle([120, 900, 1680, 1065], radius=42, fill=(239,242,243,255), outline=(210,216,219,255), width=2)
    for x in [138, 1630]:
        d.rounded_rectangle([x, 220, x+36, 900], radius=20, fill=(255,255,255,70))
    for p, pos, size in [(PRODUCTS[10], (625,260), (530,648)), (PRODUCTS[9], (335,370), (430,526)), (PRODUCTS[12], (1010,345), (450,550))]:
        vial = Image.open(PRODUCTS_DIR / f'{p["id"]}-vial.png').convert('RGBA').resize(size, Image.Resampling.LANCZOS)
        bg.alpha_composite(vial, pos)
    draw_box(bg, (980, 615, 430, 350), PRODUCTS[10], 1.0)
    d.text((135, 118), 'ELEMENTS LABS', font=font(36, True), fill=rgba(GRAPHITE,255))
    d.text((135, 166), 'controlled product photography direction', font=font(21), fill=rgba(MUTED,255))
    bg.save(SCENES / 'hero-studio-scene.png')

    # Group shot with all 13 vials
    group = linear_gradient((2200, 1220), '#FBFBFC', '#E8ECEE')
    group = add_noise(group, amount=6, alpha=11)
    d = ImageDraw.Draw(group)
    d.rounded_rectangle([110, 980, 2090, 1125], radius=70, fill=(12,18,22,28))
    x0 = 115
    for i,p in enumerate(PRODUCTS):
        col = i % 7; row = i // 7
        size = (255, 312) if row == 0 else (238, 291)
        x = x0 + col * 285 + (70 if row else 0)
        y = 230 + row * 350
        vial = Image.open(PRODUCTS_DIR / f'{p["id"]}-vial.png').convert('RGBA').resize(size, Image.Resampling.LANCZOS)
        group.alpha_composite(vial, (x,y))
    d.text((120, 88), '13/13 Research Product Family', font=font(44, True), fill=rgba(GRAPHITE,255))
    d.text((120, 145), 'Same bottle geometry, same label grid, same packaging rule.', font=font(24), fill=rgba(MUTED,255))
    group.save(SCENES / 'group-product-shot.png')

    # Packaging shot
    pack = linear_gradient((1600, 1120), '#FCFCFD', '#ECEFF1')
    pack = add_noise(pack, amount=6, alpha=10)
    d = ImageDraw.Draw(pack)
    d.rounded_rectangle([80, 870, 1520, 1010], radius=60, fill=(13,17,21,28))
    draw_box(pack, (260, 220, 430, 610), PRODUCTS[0], 1.0)
    draw_box(pack, (605, 280, 440, 600), PRODUCTS[10], 1.0)
    draw_box(pack, (940, 240, 390, 560), PRODUCTS[12], 1.0)
    vial = Image.open(PRODUCTS_DIR / '5-amino-1mq-vial.png').convert('RGBA').resize((405,495), Image.Resampling.LANCZOS)
    pack.alpha_composite(vial, (1065, 505))
    pack.save(SCENES / 'packaging-shot.png')

    # Macro detail
    macro = linear_gradient((1500, 980), '#F8F9FA', '#EAEEF0')
    macro = add_noise(macro, amount=8, alpha=12)
    vial = Image.open(PRODUCTS_DIR / '5-amino-1mq-vial.png').convert('RGBA').resize((1060, 1295), Image.Resampling.LANCZOS)
    macro.alpha_composite(vial, (170, -150))
    md = ImageDraw.Draw(macro)
    md.rounded_rectangle([950, 150, 1345, 360], radius=28, fill=(255,255,255,198), outline=(207,214,218,255), width=2)
    md.text((990,190), 'Macro detail', font=font(31, True), fill=rgba(GRAPHITE,255))
    md.text((990,245), 'paper label · glass edge · graphite cap', font=font(21), fill=rgba(MUTED,255))
    macro.save(SCENES / 'macro-detail.png')


def data_url(path: Path) -> str:
    ext = path.suffix.lower().lstrip('.')
    mime = 'image/svg+xml' if ext == 'svg' else f'image/{"jpeg" if ext in ["jpg","jpeg"] else ext}'
    return f'data:{mime};base64,' + base64.b64encode(path.read_bytes()).decode('ascii')


CSS = r'''
:root{
  --graphite:#2A2F36;--near-black:#0D1115;--off-white:#F7F7F8;--petrol:#0D5B6B;--ink:#172027;--muted:#66717B;--line:#D9DEE1;--panel:#FFFFFF;--soft:#EEF2F3;--radius:26px;--max:1220px;--shadow:0 28px 70px rgba(13,17,21,.13);--sans:"Segoe UI",Roboto,Arial,sans-serif;--mono:"Cascadia Mono","SFMono-Regular","Segoe UI Mono",monospace}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--off-white);color:var(--ink);font-family:var(--sans);line-height:1.5;overflow-x:hidden}a{color:inherit;text-decoration:none}button,input,select{font:inherit}.site-header{position:sticky;top:0;z-index:40;display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:20px;max-width:var(--max);margin:0 auto;padding:18px 22px;background:rgba(247,247,248,.91);backdrop-filter:blur(18px);border-bottom:1px solid rgba(42,47,54,.12)}.brand{display:flex;align-items:center;gap:13px;font-weight:850;letter-spacing:.13em}.brand img{width:148px;height:auto;display:block}.main-nav{display:flex;gap:24px;justify-content:center;color:#55606A;font-size:14px}.main-nav a{padding:8px 0;border-bottom:1px solid transparent}.main-nav a:hover,.main-nav a.active{color:var(--near-black);border-color:var(--petrol)}.header-actions{display:flex;gap:10px;align-items:center}.menu-toggle{display:none}.secondary-btn,.ghost-btn,.menu-toggle,.search-open{border:1px solid var(--line);background:rgba(255,255,255,.62);color:var(--graphite);border-radius:999px;padding:11px 16px;cursor:pointer;transition:.2s ease}.primary-btn,.cart-link{border:1px solid var(--petrol);background:var(--near-black);color:white;border-radius:999px;padding:11px 17px;cursor:pointer;box-shadow:0 12px 24px rgba(13,17,21,.12);transition:.2s ease}.primary-btn:hover,.secondary-btn:hover,.cart-link:hover,.ghost-btn:hover{transform:translateY(-1px)}.cart-link span{display:inline-grid;place-items:center;min-width:22px;height:22px;margin-left:6px;background:var(--petrol);color:white;border-radius:50%;font:800 12px var(--mono)}.section{max-width:var(--max);margin:0 auto;padding:84px 22px}.hero{min-height:calc(100vh - 82px);display:grid;grid-template-columns:.92fr 1.08fr;gap:58px;align-items:center}.eyebrow{font:800 12px/1 var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--petrol);margin-bottom:16px}.hero h1,.page-title{font-size:clamp(45px,5.4vw,84px);line-height:1.02;letter-spacing:-.045em;margin:0 0 24px;color:var(--near-black)}.hero h1 span,.page-title span{color:var(--petrol)}.lead{font-size:clamp(17px,1.5vw,21px);color:var(--muted);max-width:600px;margin:0 0 30px}.cta-row{display:flex;gap:12px;flex-wrap:wrap;margin-top:22px}.trust-matrix{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:30px}.trust-matrix div,.metric-card{padding:17px;background:rgba(255,255,255,.72);border:1px solid var(--line);border-radius:18px}.trust-matrix strong,.metric-card strong{display:block;font-size:14px;color:var(--near-black);margin-bottom:5px}.trust-matrix span,.metric-card span{font-size:12px;color:var(--muted)}.hero-photo,.wide-photo{position:relative;background:linear-gradient(145deg,#fff,#EEF2F3);border:1px solid var(--line);border-radius:34px;box-shadow:var(--shadow);overflow:hidden}.hero-photo img,.wide-photo img{display:block;width:100%;height:auto}.photo-caption{position:absolute;left:22px;bottom:22px;padding:12px 15px;border-radius:14px;background:rgba(255,255,255,.82);border:1px solid rgba(217,222,225,.9);backdrop-filter:blur(14px);font:800 11px var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--graphite)}.section-head{margin-bottom:34px;display:flex;align-items:end;justify-content:space-between;gap:24px}.section-head h2{font-size:clamp(32px,3.5vw,52px);line-height:1.05;letter-spacing:-.032em;margin:0;color:var(--near-black)}.section-head p{max-width:560px;color:var(--muted);margin:0}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(285px,1fr));gap:24px}.product-card{background:var(--panel);border:1px solid var(--line);border-radius:28px;padding:18px;display:flex;flex-direction:column;position:relative;overflow:hidden;min-height:510px;box-shadow:0 18px 44px rgba(13,17,21,.08)}.product-card:before{content:"";position:absolute;inset:0 0 auto;height:6px;background:linear-gradient(90deg,var(--graphite),var(--petrol));opacity:.95}.card-top{display:flex;justify-content:space-between;font:800 10px var(--mono);color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin:8px 0 8px}.product-img-wrap{display:grid;place-items:center;background:linear-gradient(180deg,#F8FAFA,#ECEFF1);border:1px solid #E1E6E8;border-radius:23px;min-height:250px;margin-bottom:18px;overflow:hidden}.product-img-wrap img{width:82%;height:auto;filter:drop-shadow(0 18px 24px rgba(13,17,21,.14))}.product-card h3{margin:0 0 7px;font-size:22px;letter-spacing:-.018em;color:var(--near-black)}.compound-meta{font-size:13px;color:var(--muted);line-height:1.58}.price-row{display:flex;align-items:center;justify-content:space-between;margin-top:auto;padding-top:17px}.price{font:850 24px/1 var(--sans);letter-spacing:-.02em}.status{font:800 11px var(--mono);color:var(--petrol);text-transform:uppercase;letter-spacing:.07em}.card-actions{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:16px}.card-actions .secondary-btn,.card-actions .primary-btn{text-align:center;padding:12px 10px;font-size:13px}.quality-grid{display:grid;grid-template-columns:.92fr 1.08fr;gap:28px;align-items:start}.process{counter-reset:step;list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:14px}.process li{counter-increment:step;position:relative;padding:18px 18px 18px 58px;background:#fff;border:1px solid var(--line);border-radius:18px}.process li:before{content:counter(step,decimal-leading-zero);position:absolute;left:17px;top:20px;font:850 14px var(--mono);color:var(--petrol)}.process strong{display:block;margin-bottom:4px}.coa-preview,.batch-panel,.cart-panel,.partner-panel{background:#fff;border:1px solid var(--line);border-radius:28px;padding:28px;box-shadow:0 15px 42px rgba(13,17,21,.07)}.report{position:relative;background:#FCFCFD;color:var(--near-black);border:1px solid #DDE2E5;border-radius:18px;padding:24px}.report-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:18px}.report-grid div{padding:12px;border:1px solid #E1E5E8;border-radius:12px;background:white}.report-grid span{display:block;font:800 10px var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:4px}.report-grid strong{font-size:14px}.detail-layout{display:grid;grid-template-columns:1.05fr .95fr;gap:36px;align-items:start}.gallery{display:grid;gap:16px}.gallery-main{background:linear-gradient(180deg,#fff,#EEF2F3);border:1px solid var(--line);border-radius:32px;overflow:hidden;box-shadow:var(--shadow)}.gallery-main img{display:block;width:100%;height:auto}.thumbs{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.thumbs img{width:100%;border:1px solid var(--line);border-radius:18px;background:#fff}.purchase{position:sticky;top:100px;background:#fff;border:1px solid var(--line);border-radius:32px;padding:30px;box-shadow:0 20px 46px rgba(13,17,21,.09)}.purchase h1{font-size:clamp(38px,4vw,58px);line-height:1.02;letter-spacing:-.04em;margin:0 0 15px;color:var(--near-black)}.spec-list{display:grid;grid-template-columns:1fr 1fr;gap:13px;margin:24px 0}.spec-list div{padding:14px;background:#F6F8F8;border:1px solid var(--line);border-radius:14px}.spec-list span{display:block;font:800 10px var(--mono);color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px}.spec-list strong{font-size:16px}.filters{display:grid;grid-template-columns:1.5fr .8fr .8fr;gap:12px;margin-bottom:24px}.filters input,.filters select,.batch-panel input{padding:13px 15px;background:#fff;border:1px solid var(--line);border-radius:14px;color:var(--ink)}.batch-panel input{width:100%;margin-bottom:16px}.qr{width:128px;height:128px;border-radius:12px;background:#fff;padding:7px;display:block;margin-top:18px;border:1px solid var(--line)}.cart-line{display:grid;grid-template-columns:1.2fr .7fr .7fr auto;gap:16px;align-items:center;padding:18px 0;border-bottom:1px solid var(--line)}.qty{display:flex;gap:7px;align-items:center}.qty button{width:32px;height:32px;border-radius:50%;border:1px solid var(--line);background:#fff}.total{font:850 30px/1 var(--sans);text-align:right;margin:22px 0}.hidden{display:none}.footer{max-width:var(--max);margin:0 auto;padding:62px 22px 44px;display:grid;grid-template-columns:2fr 1.3fr 1.2fr;gap:28px;color:var(--muted);font-size:13px;border-top:1px solid var(--line)}.footer strong{color:var(--near-black)}.footer a{display:block;color:var(--muted);margin-bottom:8px}.research-only{grid-column:1/-1;text-align:center;font:800 11px var(--mono);text-transform:uppercase;letter-spacing:.06em;color:var(--muted);padding-top:18px;border-top:1px solid var(--line)}.faq-list{display:flex;flex-direction:column;gap:14px}.faq-list details{background:#fff;border:1px solid var(--line);border-radius:18px;padding:17px}.faq-list summary{font-weight:750;cursor:pointer}.legal{max-width:820px}.family-section .wide-photo{margin-top:10px}.brand-story{display:grid;grid-template-columns:.9fr 1.1fr;gap:32px;align-items:center}.brand-story img{width:100%;border-radius:30px;border:1px solid var(--line);box-shadow:var(--shadow)}.internal-badge{display:inline-block;background:#F2C94C;color:#101418;font:850 11px var(--mono);letter-spacing:.06em;text-transform:uppercase;padding:6px 12px;border-radius:8px}.partner-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}.kpi{padding:20px;background:#F6F8F8;border:1px solid var(--line);border-radius:16px}.kpi span{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}.kpi strong{display:block;font-size:26px;margin:8px 0 4px}.partner-table{width:100%;border-collapse:collapse;font-size:14px}.partner-table th,.partner-table td{padding:12px 10px;text-align:left;border-bottom:1px solid var(--line)}.partner-table th{font:800 11px var(--mono);text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}#toast{position:fixed;bottom:22px;right:22px;z-index:60;background:var(--near-black);color:white;border:1px solid rgba(255,255,255,.12);border-radius:13px;padding:12px 18px;font-size:13px;box-shadow:var(--shadow);opacity:0;transform:translateY(10px);transition:opacity .25s,transform .25s;pointer-events:none}#toast.show-toast{opacity:1;transform:translateY(0)}
@media(min-width:1000px){#productGrid{grid-template-columns:repeat(3,1fr)}#productGrid .product-card:last-child:nth-child(3n+1){grid-column:2}}
@media(max-width:960px){.site-header{grid-template-columns:auto auto auto;gap:10px}.menu-toggle{display:block;margin-left:auto}.main-nav{position:absolute;left:14px;right:14px;top:74px;display:none;flex-direction:column;justify-content:flex-start;background:#fff;border:1px solid var(--line);border-radius:20px;padding:16px;box-shadow:var(--shadow)}.main-nav.open{display:flex}.search-open{display:none}.hero,.quality-grid,.detail-layout,.brand-story{grid-template-columns:1fr}.hero{min-height:auto;padding-top:48px}.cards{grid-template-columns:1fr 1fr}.trust-matrix,.partner-kpis{grid-template-columns:1fr 1fr}.filters{grid-template-columns:1fr}.footer{grid-template-columns:1fr}.cart-line{grid-template-columns:1fr;align-items:start}.total{text-align:left}.section{padding:60px 18px}.section-head{display:block}.purchase{position:relative;top:0}.spec-list{grid-template-columns:1fr 1fr}}
@media(max-width:540px){.site-header{padding:12px 12px}.brand img{width:122px}.cart-link,.primary-btn,.secondary-btn,.ghost-btn,.menu-toggle{padding:10px 12px}.hero h1,.page-title{font-size:42px}.section{padding:48px 14px}.cards,.trust-matrix,.partner-kpis,.report-grid,.thumbs,.spec-list{grid-template-columns:1fr}.hero-photo,.wide-photo,.gallery-main{border-radius:24px}.photo-caption{left:12px;bottom:12px;font-size:9px}.product-card{min-height:500px}.product-img-wrap{min-height:240px}.partner-table{font-size:12px}.partner-table th,.partner-table td{padding:8px 5px}.qr{width:96px;height:96px}.header-actions{gap:6px}.main-nav{top:62px}.card-actions{grid-template-columns:1fr}.footer{padding-bottom:32px}}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}
'''

APP = r'''
const products = JSON.parse(document.getElementById('productData').textContent);
window.__ELEMENTS_PRODUCTS__ = products;
const internalMap = {"bpc-157":["3,91 €","Preisanker und Einstieg in das Research-Portfolio."],"tb-500":["8,83 €","Ergänzungsprodukt für Tissue-Research-Käufer."],"ghk-cu":["2,64 €","Attraktive Marge, starke visuelle Produktfarbe."],"ipamorelin":["4,26 €","Sortimentsbreite im Endocrine-Cluster."],"kpv":["5,60 €","Featured-Compound mit gutem Preis-/Wert-Verhältnis."],"selank":["3,99 €","Cluster-Produkt für Research-Breite."],"semax":["3,99 €","Paarprodukt zu Selank."],"mots-c":["6,20 €","Premium-naher Scientific-Cluster."],"cjc-1295-no-dac":["7,41 €","Sortimentsabdeckung für bekannte Nachfrage."],"nad-plus":["4,04 €","Hochattraktives Featured-Produkt mit starkem VK."],"5-amino-1mq":["3,45 €","Strategisches Hochmargenprodukt und Featured-Held."],"bpc-157-tb-500":["9,64 €","Bundle-Produkt mit klarer Conversion-Funktion."],"epithalon":["15,08 €","Premium-Anker mit höchstem VK."]};
const internalProducts = products.map(p=>{const [ek,positioning]=internalMap[p.id]||['',''];return {...p, ek, positioning};});
const money = v => Number(String(v).replace('€','').replace('.','').replace(',','.').trim());
const fmt = n => n.toLocaleString('de-DE',{style:'currency',currency:'EUR'});
let cart = JSON.parse(localStorage.getItem('elementsCart') || '{}');
const app = document.getElementById('app');
function saveCart(){localStorage.setItem('elementsCart', JSON.stringify(cart)); updateCartCount();}
function updateCartCount(){document.getElementById('cartCount').textContent = Object.values(cart).reduce((a,b)=>a+b,0)}
function toast(t){const el=document.getElementById('toast');el.textContent=t;el.classList.add('show-toast');setTimeout(()=>el.classList.remove('show-toast'),1500)}
function addToCart(id,qty=1){cart[id]=(cart[id]||0)+qty;saveCart();toast('Zum Warenkorb hinzugefügt');}
function removeFromCart(id){delete cart[id];saveCart();render()}
function setQty(id,qty){if(qty<=0) delete cart[id]; else cart[id]=qty;saveCart();render()}
function pById(id){return products.find(p=>p.id===id)}
function pByBatch(b){return products.find(p=>p.batch.toLowerCase()===String(b||'').toLowerCase())}
function productCard(p){return `<article class="product-card ${p.featured?'featured':''}" data-product-card data-id="${p.id}"><div class="card-top"><span>${p.num} · ${p.category}</span><span>${p.batch}</span></div><a class="product-img-wrap" href="#product=${p.id}" aria-label="${p.name} öffnen"><img src="${p.image}" alt="${p.name} ${p.concentration} Elements Labs Vial"></a><h3>${p.name}</h3><div class="compound-meta">${p.concentration} · ${p.code}</div><div class="price-row"><span class="price">${p.price}</span><span class="status">Batch-linked</span></div><p class="compound-meta">${p.desc}</p><div class="card-actions"><a class="secondary-btn" href="#product=${p.id}">Details</a><button class="primary-btn" data-add="${p.id}">Add to Cart</button></div></article>`}
function report(p){return `<div class="report" data-coa="${p.id}"><div class="eyebrow">Analysis structure</div><h3>Batch Documentation — ${p.name}</h3><p class="compound-meta">Dieses Panel bildet die spätere Berichtstruktur ab. Werte werden erst nach echter externer Analyse veröffentlicht.</p><div class="report-grid"><div><span>Compound</span><strong>${p.name}</strong></div><div><span>Batch</span><strong>${p.batch}</strong></div><div><span>COA</span><strong>Nicht veröffentlicht</strong></div><div><span>Lab</span><strong>Nicht veröffentlicht</strong></div><div><span>Date</span><strong>Nicht veröffentlicht</strong></div><div><span>Identity</span><strong>Ausstehend</strong></div><div><span>Purity</span><strong>Ausstehend</strong></div><div><span>Method</span><strong>Ausstehend</strong></div></div></div>`}
function home(){const featured=products.filter(p=>p.featured).slice(0,6);return `<section class="section hero" id="home-hero"><div><div class="eyebrow">European Premium Research Brand</div><h1>ELEMENTS LABS. <span>Research Commerce</span> mit realer Produktdisziplin.</h1><p class="lead">Eine helle, technische Premium-Marke für strukturierte Research-Ware: klare Vials, konsistente Verpackung, Batch-Traceability und Commerce ohne medizinische Claims.</p><div class="cta-row"><a class="primary-btn" href="#products">Produkte entdecken</a><a class="secondary-btn" href="#batch-lookup">Batch prüfen</a></div><div class="trust-matrix"><div><strong>13 Produkte</strong><span>vollständiges Startportfolio</span></div><div><strong>Ein Labelsystem</strong><span>einheitliche Verpackungslinie</span></div><div><strong>Batch-Struktur</strong><span>Produkt, Code und Charge verbunden</span></div><div><strong>Research Only</strong><span>keine Human-Use-Kommunikation</span></div></div></div><figure class="hero-photo"><img src="assets/scenes/hero-studio-scene.png" alt="ELEMENTS LABS Produktfotografie mit Vials und Verpackung"><figcaption class="photo-caption">macro studio · graphite / off-white / petrol</figcaption></figure></section><section class="section"><div class="section-head"><div><div class="eyebrow">Featured Products</div><h2>Portfolio mit einheitlicher Produktlogik.</h2></div><p>Jede Karte nutzt dieselbe Glasform, dasselbe Labelraster und dieselbe Informationshierarchie.</p></div><div class="cards">${featured.map(productCard).join('')}</div></section>${qualityBlock(false)}<section class="section family-section"><div class="section-head"><div><div class="eyebrow">Product Family</div><h2>13 Produkte, eine glaubwürdige Fertigungslinie.</h2></div><p>Keine zufälligen Farben, keine Clipart-Logos, keine wechselnden Glasformen: Die Vials wirken wie eine zusammenhängende Markenproduktion.</p></div><figure class="wide-photo"><img src="assets/scenes/group-product-shot.png" alt="ELEMENTS LABS Gruppe mit 13 Research Vials"><figcaption class="photo-caption">13/13 product family</figcaption></figure></section><section class="section brand-story"><div><div class="eyebrow">Packaging Direction</div><h2>Off-White Karton, Graphite-Typografie, Petrol-Akzent.</h2><p class="lead">Die Verpackung ist bewusst näher an Diagnostics, Labortechnik und Premium-Kosmetik als an Supplements oder Fitness-Commerce.</p><div class="cta-row"><a class="primary-btn" href="#quality">Quality System</a><a class="secondary-btn" href="#about">Brand Story</a></div></div><img src="assets/scenes/packaging-shot.png" alt="ELEMENTS LABS Premium Packaging mit Vial"></section><section class="section"><div class="section-head"><div><div class="eyebrow">FAQ / Support</div><h2>Klarheit vor Conversion-Hype.</h2></div><p>Die Seite bleibt commercefähig, ohne Laborwerte, Zertifikate oder Unternehmensdetails zu erfinden.</p></div><div class="faq-list"><details open><summary>Wofür ist das Portfolio vorgesehen?</summary><p>Für Research-Kontexte. Keine Einnahme, keine Anwendung, keine therapeutische oder diagnostische Kommunikation.</p></details><details><summary>Was zeigt die Batch-Suche?</summary><p>Sie verbindet Produkt, Charge, Code und vorbereitete Analysefelder. Reale Werte werden erst nach echter Prüfung ergänzt.</p></details><details><summary>Warum diese Bildwelt?</summary><p>Makro-Studiofotografie, klare Materialien und ein reproduzierbares Labelsystem machen die Marke glaubwürdig und skalierbar.</p></details></div></section>`}
function productsPage(){return `<section class="section"><div class="section-head"><div><div class="eyebrow">Catalog</div><h1 class="page-title">13 Research <span>Products.</span></h1></div><p>Alle verbindlichen Produkte mit korrekter Konzentration, Preis, Produktcode und Batch-ID.</p></div><div class="filters"><input id="searchInput" placeholder="Search compound, code or batch" aria-label="Produkt suchen"><select id="categoryFilter"><option value="">Alle Kategorien</option>${[...new Set(products.map(p=>p.category))].map(c=>`<option>${c}</option>`).join('')}</select><select id="sortFilter"><option value="featured">Featured zuerst</option><option value="price-asc">Preis aufsteigend</option><option value="price-desc">Preis absteigend</option></select></div><div class="cards" id="productGrid">${products.map(productCard).join('')}</div></section>`}
function qualityBlock(full=true){return `<section class="section" id="quality-section"><div class="section-head"><div><div class="eyebrow">Quality & Analysis</div><h2>${full?'Quality & Analysis':'Quality System'}</h2></div><p>Vorbereitete Struktur für Batch, COA, Labor, Datum, Identität, Reinheit, Methode, Report und QR-Zugriff.</p></div><div class="quality-grid"><ol class="process"><li><div><strong>Product Coding</strong><p class="compound-meta">Jedes Produkt erhält ein konsistentes Code- und Konzentrationsschema.</p></div></li><li><div><strong>Batch Assignment</strong><p class="compound-meta">Charge und Produktcode sind im Label, Katalog und Batch-Lookup identisch.</p></div></li><li><div><strong>External Analysis Fields</strong><p class="compound-meta">COA-, Labor-, Methodik- und Identitätsfelder sind vorbereitet, aber nicht erfunden.</p></div></li><li><div><strong>Report Access</strong><p class="compound-meta">QR und Batch-Seiten führen später zum passenden Prüfbericht.</p></div></li><li><div><strong>Commerce Release</strong><p class="compound-meta">Live-Betrieb erst nach echten Unternehmens-, Rechts- und Qualitätsdaten.</p></div></li></ol><div class="coa-preview">${report(products[10])}<div class="cta-row"><a class="primary-btn" href="#batch-lookup">Batch prüfen</a><a class="secondary-btn" href="#product=5-amino-1mq">Produktdetail ansehen</a></div></div></div></section>`}
function qualityPage(){return `${qualityBlock(true)}<section class="section"><div class="section-head"><div><div class="eyebrow">Analysis Library</div><h2>13/13 vorbereitete Report-Zugänge.</h2></div><p>Alle Einträge sind strukturell angelegt; keine nicht vorhandenen Laborergebnisse werden angezeigt.</p></div><div class="cards">${products.map(p=>`<article class="product-card" style="min-height:330px"><div class="card-top"><span>${p.code}</span><span>${p.batch}</span></div><h3>${p.name}</h3><p class="compound-meta">${p.concentration}</p><div class="price-row"><span class="status">Report Access</span><a href="#product=${p.id}" class="secondary-btn">Öffnen</a></div></article>`).join('')}</div></section>`}
function batchPage(batch=''){const p=pByBatch(batch);return `<section class="section"><div class="section-head"><div><div class="eyebrow">Batch Lookup</div><h1 class="page-title">Batchnummer <span>prüfen.</span></h1></div><p>Produkt, Konzentration, Code und vorbereitete Analysefelder werden über die Batch-ID verbunden.</p></div><div class="batch-panel"><input id="batchInput" value="${batch||''}" placeholder="z. B. EL-BPC5-26001"><div class="cta-row"><button class="primary-btn" id="batchBtn">Batch prüfen</button><button class="secondary-btn" id="sampleBatch">Erste Batch-ID einsetzen</button></div><div id="batchResult" style="margin-top:22px">${p?batchResult(p):batchHint()}</div></div></section>`}
function batchHint(){return `<p class="compound-meta">Akzeptierte Start-Batches: ${products.slice(0,4).map(p=>p.batch).join(' · ')} · weitere im Katalog.</p>`}
function batchResult(p){return `<div class="detail-layout" style="padding:0;border:0;background:transparent"><div><img class="qr" src="${p.qr}" alt="QR zu ${p.batch}"><div class="product-img-wrap" style="max-width:260px;margin-top:16px"><img src="${p.image}" alt="${p.name} Vial"></div></div><div><div class="eyebrow">Batch Result</div><h2>${p.name}</h2><p>${p.concentration} · ${p.code} · ${p.batch}</p><div class="report-grid"><div><span>COA</span><strong>Nicht veröffentlicht</strong></div><div><span>Lab</span><strong>Nicht veröffentlicht</strong></div><div><span>Identity</span><strong>Ausstehend</strong></div><div><span>Report</span><strong>Access vorbereitet</strong></div></div><div class="cta-row"><a class="primary-btn" href="#product=${p.id}">Produktdetail</a><a class="secondary-btn" href="#quality">Analysis Library</a></div></div></div>`}
function productDetail(id){const p=pById(id)||products[0];return `<section class="section"><a href="#products" class="secondary-btn">← Zurück zum Katalog</a><div class="detail-layout" style="margin-top:22px"><div class="gallery"><div class="gallery-main"><img src="${p.detailImage}" alt="${p.name} Elements Labs Produktbild"></div><div class="thumbs"><img src="${p.image}" alt="${p.name} Vial"><img src="${p.packagingImage}" alt="Elements Labs Packaging"><img src="${p.macroImage}" alt="Elements Labs Macro Detail"></div></div><aside class="purchase"><div class="eyebrow">${p.num} · ${p.category}</div><h1>${p.name}</h1><p class="lead">${p.desc}</p><div class="price" style="margin:10px 0 18px">${p.price}</div><div class="spec-list"><div><span>Konzentration</span><strong>${p.concentration}</strong></div><div><span>Einheit</span><strong>1 Vial</strong></div><div><span>Product Code</span><strong>${p.code}</strong></div><div><span>Batch</span><strong>${p.batch}</strong></div></div><p class="compound-meta"><strong>Research Notice:</strong> Not for human consumption. No therapeutic, diagnostic, veterinary or dosing claims.</p><div class="cta-row"><button class="primary-btn" data-add="${p.id}">Add to Cart</button><a class="secondary-btn" href="#batch=${p.batch}">Batch anzeigen</a></div></aside></div></section><section class="section"><div class="section-head"><div><div class="eyebrow">Product Documentation</div><h2>Research Information & Specifications</h2></div><p>Produktdaten bleiben exakt; Analysewerte werden erst nach echter Prüfung ergänzt.</p></div>${report(p)}</section>`}
function cartPage(){const items=Object.entries(cart).map(([id,qty])=>({p:pById(id),qty})).filter(x=>x.p);const total=items.reduce((s,x)=>s+money(x.p.price)*x.qty,0);return `<section class="section"><div class="section-head"><div><div class="eyebrow">Cart</div><h1 class="page-title">Warenkorb <span>prüfen.</span></h1></div><p>Funktionaler Warenkorb für Produktauswahl, Mengen und Summen. Checkout wird erst im Live-Betrieb aktiviert.</p></div><div class="cart-panel">${items.length?items.map(x=>`<div class="cart-line"><strong>${x.p.name}<br><span class="compound-meta">${x.p.concentration} · ${x.p.batch}</span></strong><span>${x.p.price}</span><div class="qty"><button data-qty="${x.p.id}" data-delta="-1">−</button><span>${x.qty}</span><button data-qty="${x.p.id}" data-delta="1">+</button></div><button class="ghost-btn" data-remove="${x.p.id}">Remove</button></div>`).join(''):'<p class="compound-meta">Der Warenkorb ist leer.</p>'}<p class="compound-meta">Anzeige inklusive Umsatzsteuer. Es wird keine Bestellung ausgelöst.</p><div class="total" id="cartTotal">${fmt(total)}</div><div class="cta-row"><button class="primary-btn" id="checkoutBtn">Checkout vorbereiten</button><a class="secondary-btn" href="#products">Weiter einkaufen</a></div><div id="checkoutDemo" class="hidden" style="margin-top:20px"><span class="internal-badge">Checkout inactive</span><p>Payment, Versand, Rechtstexte und Unternehmensdaten werden vor Live-Betrieb verbindlich angeschlossen.</p></div></div></section>`}
function about(){return `<section class="section legal"><div class="eyebrow">About</div><h1 class="page-title">European Research Commerce, <span>präzise geführt.</span></h1><p class="lead">ELEMENTS LABS positioniert Research-Produkte über Materialklarheit, dokumentierte Batch-Struktur und zurückhaltendes Premium-Design.</p><p>Die Marke vermeidet Fitness-, Supplement- und Pharma-Anmutung. Der Fokus liegt auf reproduzierbaren Produktvisuals, systematischer Informationsarchitektur und einem ehrlichen Analyse-Framework.</p></section>`}
function faq(){return `<section class="section legal"><div class="eyebrow">FAQ</div><h1 class="page-title">Research-only <span>clarity.</span></h1><div class="faq-list"><details open><summary>Sind Bestellungen bereits aktiv?</summary><p>Nein. Vor Live-Betrieb werden Payment, Rechtstexte, Versand und Unternehmensdaten verbindlich angeschlossen.</p></details><details><summary>Sind Laborberichte veröffentlicht?</summary><p>Nein. Die Website zeigt die Struktur. Echte Analysewerte werden erst nach externer Prüfung ergänzt.</p></details><details><summary>Gibt es medizinische Aussagen?</summary><p>Nein. Keine Einnahme-, Dosierungs-, Therapie-, Diagnose- oder Human-Use-Anleitung.</p></details><details><summary>Warum Batch Lookup?</summary><p>Das System verbindet Produkt, Charge und späteren Berichtszugriff nachvollziehbar.</p></details></div></section>`}
function contact(){return `<section class="section legal"><div class="eyebrow">Support</div><h1 class="page-title">Kontaktstruktur <span>für Live-Betrieb.</span></h1><p class="lead">Unternehmensdaten, rechtliche Pflichtangaben und Supportwege werden vor Veröffentlichung verbindlich eingetragen.</p><div class="batch-panel"><p><strong>ELEMENTS LABS</strong><br>Research-only commerce structure<br>Germany / EU market focus</p><p class="compound-meta">Keine medizinische Beratung. Keine Human-Use-Kommunikation.</p></div></section>`}
function partner(){const ip=internalProducts;return `<section class="section"><span class="internal-badge">INTERNAL — NOT PUBLIC</span><div class="section-head"><div><h1 class="page-title">Partner <span>View.</span></h1><p class="lead">Interne Wirtschaftlichkeits- und Portfolioansicht.</p></div></div><div class="partner-panel"><div class="partner-kpis"><div class="kpi"><span>Startportfolio</span><strong>13</strong><small>Research Products</small></div><div class="kpi"><span>Price Range</span><strong>24,90–94,90 €</strong><small>VK</small></div><div class="kpi"><span>Quality Model</span><strong>Batch + COA</strong><small>Struktur</small></div><div class="kpi"><span>Position</span><strong>Premium EU</strong><small>Research Commerce</small></div></div><table class="partner-table"><thead><tr><th>Produkt</th><th>Konz.</th><th>EK intern</th><th>VK</th><th>Positionierung</th></tr></thead><tbody>${ip.map(p=>`<tr><td>${p.name}</td><td>${p.concentration}</td><td>${p.ek}</td><td>${p.price}</td><td>${p.positioning}</td></tr>`).join('')}</tbody></table><p class="compound-meta"><strong>Annahme:</strong> Import, Labor, Steuer, Payment, Versand und Retouren sind noch nicht kalkuliert. Keine scheinexakten Gewinnzahlen.</p></div></section>`}
function legal(kind){return `<section class="section legal"><div class="eyebrow">Legal</div><h1 class="page-title">${kind==='privacy'?'Datenschutz':'Impressum'} <span>vorbereiten.</span></h1><p>Echte Betreiber-, Rechts- und Datenschutzdaten werden vor jeder Live-Schaltung fachlich geprüft und ergänzt.</p><p>Research-use-only. No human consumption. No medical, therapeutic, diagnostic or veterinary claims.</p></section>`}
function route(){const h=decodeURIComponent(location.hash.slice(1)||'home');if(h.startsWith('product='))return productDetail(h.split('=')[1]);if(h.startsWith('batch='))return batchPage(h.split('=')[1]);if(h==='products')return productsPage();if(h==='quality')return qualityPage();if(h==='batch-lookup')return batchPage();if(h==='about')return about();if(h==='faq')return faq();if(h==='contact')return contact();if(h==='cart')return cartPage();if(h==='internal-partner')return partner();if(h==='legal-datenschutz')return legal('privacy');if(h==='legal-impressum')return legal('imprint');return home()}
function bind(){document.querySelectorAll('[data-add]').forEach(b=>b.onclick=()=>addToCart(b.dataset.add));document.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>removeFromCart(b.dataset.remove));document.querySelectorAll('[data-qty]').forEach(b=>b.onclick=()=>setQty(b.dataset.qty,(cart[b.dataset.qty]||0)+Number(b.dataset.delta)));const co=document.getElementById('checkoutBtn');if(co)co.onclick=()=>document.getElementById('checkoutDemo').classList.remove('hidden');const bb=document.getElementById('batchBtn');if(bb)bb.onclick=()=>{const v=document.getElementById('batchInput').value.trim();location.hash='batch='+encodeURIComponent(v)};const sb=document.getElementById('sampleBatch');if(sb)sb.onclick=()=>{document.getElementById('batchInput').value=products[0].batch};const si=document.getElementById('searchInput');if(si){const cf=document.getElementById('categoryFilter'),sf=document.getElementById('sortFilter'),grid=document.getElementById('productGrid');const apply=()=>{let list=[...products];const q=si.value.toLowerCase();if(q)list=list.filter(p=>(p.name+p.code+p.batch+p.category).toLowerCase().includes(q));if(cf.value)list=list.filter(p=>p.category===cf.value);if(sf.value==='price-asc')list.sort((a,b)=>money(a.price)-money(b.price));if(sf.value==='price-desc')list.sort((a,b)=>money(b.price)-money(a.price));if(sf.value==='featured')list.sort((a,b)=>(b.featured?1:0)-(a.featured?1:0));grid.innerHTML=list.map(productCard).join('');bind()};[si,cf,sf].forEach(x=>x.oninput=apply)}document.querySelectorAll('.main-nav a').forEach(a=>a.classList.toggle('active',('#'+(location.hash.slice(1)||'home'))===a.getAttribute('href')))}
function render(){app.innerHTML=route();bind();updateCartCount();app.focus({preventScroll:true});window.scrollTo({top:0,left:0,behavior:'instant'});}
window.addEventListener('hashchange',render);render();
document.getElementById('menuToggle').onclick=()=>{const n=document.getElementById('mainNav');n.classList.toggle('open');document.getElementById('menuToggle').setAttribute('aria-expanded',n.classList.contains('open'))};document.addEventListener('click',e=>{if(e.target.matches('[data-action="focus-search"]')){location.hash='products';setTimeout(()=>document.getElementById('searchInput')?.focus(),50)}});
'''

QA_JS = r'''
const fs=require('fs');const path=require('path');const http=require('http');const WebSocket=require('ws');
function getJson(url){return new Promise((resolve,reject)=>{const req=http.request(url,res=>{let d='';res.on('data',c=>d+=c);res.on('end',()=>{try{resolve(JSON.parse(d))}catch(e){reject(new Error('bad json '+d.slice(0,200)))}})});req.on('error',reject);req.end();});}
class CDP{constructor(ws){this.ws=ws;this.id=1;this.pending=new Map();this.errors=[];this.sessionId=null;this.ws.onmessage=ev=>{const msg=JSON.parse(ev.data);if(msg.id&&this.pending.has(msg.id)){this.pending.get(msg.id)(msg);this.pending.delete(msg.id);return;}const m=msg.method,p=msg.params||{};if(m==='Runtime.exceptionThrown')this.errors.push('exception: '+(p.exceptionDetails?.exception?.description||p.exceptionDetails?.text||JSON.stringify(p.exceptionDetails)).slice(0,500));if(m==='Runtime.consoleAPICalled'&&p.type==='error')this.errors.push('console.error: '+(p.args||[]).map(a=>a.value||a.description||'').join(' ').slice(0,500));if(m==='Log.entryAdded'&&p.entry?.level==='error')this.errors.push('log.error: '+(p.entry.text||'').slice(0,500));};}async open(){if(this.ws.readyState===1)return;await new Promise((res,rej)=>{this.ws.onopen=res;this.ws.onerror=rej;});}async send(method,params={},sessionId=this.sessionId){const id=this.id++;const payload={id,method,params};if(sessionId)payload.sessionId=sessionId;this.ws.send(JSON.stringify(payload));const msg=await new Promise((res,rej)=>{const t=setTimeout(()=>{this.pending.delete(id);rej(new Error('CDP timeout '+method));},15000);this.pending.set(id,m=>{clearTimeout(t);res(m);});});if(msg.error)throw new Error(method+' '+JSON.stringify(msg.error));return msg.result;}close(){this.ws.close();}}
const root=process.argv[2]||'C:/Users/eduar/elements-lab-flagship';const file=process.argv[3]||'index.html';const outDir=path.join(root,'evidence','screenshots');fs.mkdirSync(outDir,{recursive:true});
const expected=[['bpc-157','BPC-157','5 mg','24,90 €','EL-BPC5-26001','EL-BPC-005'],['tb-500','TB-500','5 mg','36,90 €','EL-TB5-26001','EL-TB5-005'],['ghk-cu','GHK-Cu','50 mg','27,90 €','EL-GHK50-26001','EL-GHK-050'],['ipamorelin','Ipamorelin','5 mg','27,90 €','EL-IPA5-26001','EL-IPA-005'],['kpv','KPV','10 mg','36,90 €','EL-KPV10-26001','EL-KPV-010'],['selank','Selank','5 mg','27,90 €','EL-SEL5-26001','EL-SEL-005'],['semax','Semax','5 mg','27,90 €','EL-SMX5-26001','EL-SMX-005'],['mots-c','MOTS-C','10 mg','36,90 €','EL-MOT10-26001','EL-MOT-010'],['cjc-1295-no-dac','CJC-1295 No DAC','5 mg','36,90 €','EL-CJC5-26001','EL-CJC-005'],['nad-plus','NAD+','500 mg','44,90 €','EL-NAD500-26001','EL-NAD-500'],['5-amino-1mq','5-Amino-1MQ','5 mg','54,90 €','EL-AMQ5-26001','EL-AMQ-005'],['bpc-157-tb-500','BPC-157 + TB-500','5 mg + 5 mg','46,90 €','EL-BT10-26001','EL-BT-010'],['epithalon','Epithalon','50 mg','94,90 €','EL-EPI50-26001','EL-EPI-050']];
(async()=>{const v=await getJson('http://127.0.0.1:9333/json/version');const c=new CDP(new WebSocket(v.webSocketDebuggerUrl));await c.open();const t=await c.send('Target.createTarget',{url:'about:blank'},null);const a=await c.send('Target.attachToTarget',{targetId:t.targetId,flatten:true},null);c.sessionId=a.sessionId;for(const m of ['Page.enable','Runtime.enable','Log.enable','DOM.enable'])await c.send(m,{});const failures=[],evidence=[];const url=h=>'file:///'+root.replace(/\\/g,'/')+'/'+file+'#'+(h||'home');const fail=m=>failures.push(m);const assert=(cond,msg)=>{if(!cond)fail(msg)};async function evalJS(expr){const r=await c.send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true});if(r.exceptionDetails){fail('JS exception '+(r.exceptionDetails.exception?.description||r.exceptionDetails.text||''));return null}return r.result.value}async function waitFor(expr,timeout=7000){const s=Date.now();while(Date.now()-s<timeout){if(await evalJS(`Boolean(${expr})`))return true;await new Promise(r=>setTimeout(r,80));}fail('wait timeout '+expr);return false}async function viewport(w,h){await c.send('Emulation.setDeviceMetricsOverride',{width:w,height:h,deviceScaleFactor:1,mobile:w<600});}async function nav(h,sel='#app'){await c.send('Page.navigate',{url:url(h)});await waitFor(`document.readyState==='complete' && document.querySelector(${JSON.stringify(sel)})`,9000);await new Promise(r=>setTimeout(r,180));}async function click(sel){await evalJS(`(()=>{const e=document.querySelector(${JSON.stringify(sel)}); if(!e)return false; e.scrollIntoView({block:'center'}); e.click(); return true})()`);await new Promise(r=>setTimeout(r,150));}async function setInput(sel,val){await evalJS(`(()=>{const e=document.querySelector(${JSON.stringify(sel)}); e.focus(); e.value=${JSON.stringify(val)}; e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true})); return e.value;})()`);await new Promise(r=>setTimeout(r,120));}async function setSelect(sel,val){await evalJS(`(()=>{const e=document.querySelector(${JSON.stringify(sel)}); e.value=${JSON.stringify(val)}; e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true})); return e.value;})()`);await new Promise(r=>setTimeout(r,120));}async function snap(name,full=false){const res=await c.send('Page.captureScreenshot',{format:'png',fromSurface:true,captureBeyondViewport:full});const p=path.join(outDir,name+'.png');fs.writeFileSync(p,Buffer.from(res.data,'base64'));evidence.push('screenshot: '+p);return p}async function clipSnap(name,sel){const r=await evalJS(`(()=>{const e=document.querySelector(${JSON.stringify(sel)}); if(!e)return null; const b=e.getBoundingClientRect(); return {x:Math.max(0,b.left),y:Math.max(0,b.top),width:Math.min(innerWidth,b.width),height:Math.min(innerHeight,b.height),scale:1};})()`);if(r&&r.width>10&&r.height>10){const res=await c.send('Page.captureScreenshot',{format:'png',clip:r,fromSurface:true});const p=path.join(outDir,name+'.png');fs.writeFileSync(p,Buffer.from(res.data,'base64'));evidence.push('screenshot: '+p);}}
await viewport(1440,1050);await nav('products','[data-product-card]');let res=await evalJS(`(()=>{const body=document.body.innerText; const cards=[...document.querySelectorAll('[data-product-card]')]; const products=window.__ELEMENTS_PRODUCTS__||[]; const imgs=[...document.images].map(i=>({src:i.getAttribute('src'),complete:i.complete,nw:i.naturalWidth})); return {body,count:cards.length,dataCount:products.length,imgs};})()`);assert(res.count===13,`product cards ${res.count} != 13`);assert(res.dataCount===13,`product data ${res.dataCount} != 13`);for(const [id,n,conc,price,batch,code] of expected){assert(res.body.includes(n),'missing '+n);assert(res.body.includes(conc),'missing '+conc);assert(res.body.includes(price),'missing '+price);assert(res.body.includes(batch),'missing '+batch);assert(res.body.includes(code),'missing '+code);}assert(res.imgs.every(i=>i.complete&&i.nw>0),'one or more product images not loaded');evidence.push('Product hard check PASS: 13/13 names, concentrations, prices, batches, codes, image loads.');await setInput('#searchInput','nad');let r=await evalJS(`(()=>({count:document.querySelectorAll('[data-product-card]').length,text:document.body.innerText}))()`);assert(r.count===1&&r.text.includes('NAD+')&&r.text.includes('500 mg'),'search nad failed');await setInput('#searchInput','');await setSelect('#sortFilter','price-desc');r=await evalJS(`(()=>{const card=document.querySelector('[data-product-card]');return {name:card.querySelector('h3').innerText,price:card.querySelector('.price').innerText};})()`);assert(r.name==='Epithalon'&&r.price.includes('94,90'),'sort price-desc failed');evidence.push('Catalog interactions PASS: search and sort.');
for(const h of ['home','products','quality','batch-lookup','about','faq','contact','cart','legal-impressum','legal-datenschutz']){await nav(h,'#app');const body=await evalJS('document.body.innerText');assert(body.length>220,'route too short '+h);assert(!/\b(DEMO|SAMPLE|TEST|PLACEHOLDER|MOCKUP|PROTOTYPE)\b/i.test(body),'visible banned marker on '+h);assert(!/Atomlogo|DNA|Molecule|molecule/i.test(body),'old logo marker on '+h);}evidence.push('Public route scan PASS: banned visible markers 0; old atom/DNA/molecule references 0.');
for(const [id,n,conc,price,batch,code] of expected){await nav('product='+id,'[data-coa]');const body=await evalJS('document.body.innerText');assert(body.includes(n)&&body.includes(conc)&&body.includes(price)&&body.includes(batch)&&body.includes(code),'product detail incomplete '+id);assert(!/\b(DEMO|SAMPLE|TEST|PLACEHOLDER|MOCKUP|PROTOTYPE)\b/i.test(body),'banned marker on detail '+id);}evidence.push('Product detail PASS: 13/13 complete and no banned public markers.');
for(const [id,n,conc,price,batch,code] of expected){await nav('batch='+encodeURIComponent(batch),'#batchResult');r=await evalJS(`(()=>{const body=document.body.innerText; const img=document.querySelector('.qr'); return {body,complete:img&&img.complete,nw:img&&img.naturalWidth,src:img&&img.getAttribute('src')};})()`);assert(r.body.includes(n)&&r.body.includes(conc)&&r.body.includes(batch)&&r.body.includes(code),'batch incomplete '+batch);assert(r.complete&&r.nw>0,'QR not loaded '+batch);if(file.includes('standalone'))assert(String(r.src).startsWith('data:image/png;base64,'),'standalone QR not data URL '+batch);}evidence.push('Batch PASS: 13/13 batch IDs resolve with QR.');
await nav('home');await evalJS(`localStorage.removeItem('elementsCart'); cart={}; render(); true`);await nav('products','[data-add="bpc-157"]');await click('[data-add="bpc-157"]');await click('[data-add="nad-plus"]');await nav('cart','#cartTotal');r=await evalJS(`(()=>({text:document.body.innerText,total:document.querySelector('#cartTotal').innerText,count:document.querySelector('#cartCount').innerText}))()`);assert(r.text.includes('BPC-157')&&r.text.includes('NAD+')&&r.total.includes('69,80')&&r.count==='2','cart add/total failed');await click('button[data-qty="bpc-157"][data-delta="1"]');await waitFor(`document.querySelector('#cartTotal').innerText.includes('94,70')`);await click('button[data-remove="nad-plus"]');r=await evalJS(`(()=>({text:document.body.innerText,total:document.querySelector('#cartTotal').innerText,count:document.querySelector('#cartCount').innerText}))()`);assert(r.text.includes('BPC-157')&&!r.text.includes('NAD+')&&r.total.includes('49,80')&&r.count==='2','cart remove failed');evidence.push('Cart PASS: add, remove, quantity, total.');
for(const [w,h,hash] of [[390,950,'home'],[430,950,'home'],[768,1050,'home'],[1440,1050,'home'],[1920,1080,'home'],[390,950,'products'],[390,950,'cart'],[390,950,'quality'],[390,950,'batch-lookup']]){await viewport(w,h);await nav(hash,'#app');const ov=await evalJS(`(()=>{const de=document.documentElement; const bad=[...document.querySelectorAll('body *')].map(el=>{const b=el.getBoundingClientRect();return {cls:String(el.className||''),right:Math.round(b.right),left:Math.round(b.left),width:Math.round(b.width)}}).filter(x=>x.width>0&&(x.right>de.clientWidth+2||x.left<-2)).slice(0,6);return {overflow:de.scrollWidth-de.clientWidth,bad};})()`);assert(ov.overflow<=2&&ov.bad.length===0,`overflow ${w} ${hash} ${JSON.stringify(ov)}`);}evidence.push('Responsive PASS: 390, 430, 768, 1440, 1920 and key mobile routes.');
await viewport(1440,1050);await nav('home');await snap('desktop-home',true);await clipSnap('hero-close-up','.hero-photo');await viewport(390,950);await nav('home');await snap('mobile-home',true);await viewport(1440,1050);await nav('products','[data-product-card]');await snap('product-grid',true);await nav('product=bpc-157','.gallery-main');await snap('product-detail-bpc-157',true);await clipSnap('vial-close-up','.gallery-main');await nav('product=epithalon','.gallery-main');await snap('product-detail-epithalon',true);await nav('home');await clipSnap('group-product-shot','.family-section .wide-photo');await clipSnap('packaging','.brand-story img');await nav('quality');await snap('quality',true);await nav('batch=EL-AMQ5-26001','#batchResult');await snap('batch-lookup',true);await nav('cart','#cartTotal');await snap('cart',true);
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
if re.search(r'\b(DEMO|SAMPLE|TEST|PLACEHOLDER|MOCKUP|PROTOTYPE)\b', public_text, re.I): fail.append('banned public marker remains in HTML shell')
if fail:
    print('FAIL standalone static: '+ '; '.join(dict.fromkeys(fail))); sys.exit(1)
print('PASS standalone static: self-contained HTML, products=13, images/QR inlined, banned shell markers=0')
'''


def build_html(products, inline=False):
    icon = data_url(LOGOS / 'el-icon-light.svg')
    logo = data_url(LOGOS / 'el-primary-light.svg') if inline else 'assets/logos/el-primary-light.svg'
    pdata = json.dumps(products, ensure_ascii=False, separators=(',', ':'))
    css_part = f'<style>{CSS}</style>' if inline else '<link rel="stylesheet" href="styles.css" />'
    js_part = f'<script>{APP}</script>' if inline else '<script src="app.js"></script>'
    return dedent(f'''<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ELEMENTS LABS — Premium Research Commerce</title>
  <meta name="description" content="ELEMENTS LABS: Premium research product catalog with batch lookup, analysis structure and market-ready packaging direction." />
  <link rel="icon" href="{icon}" />
  {css_part}
</head>
<body>
  <header class="site-header" id="top">
    <a class="brand" href="#home" aria-label="ELEMENTS LABS Home"><img src="{logo}" alt="ELEMENTS LABS"></a>
    <button class="menu-toggle" id="menuToggle" aria-expanded="false" aria-controls="mainNav">Menu</button>
    <nav id="mainNav" class="main-nav" aria-label="Hauptnavigation">
      <a href="#products">Products</a><a href="#quality">Quality</a><a href="#batch-lookup">Batch Lookup</a><a href="#about">About</a><a href="#faq">FAQ</a>
    </nav>
    <div class="header-actions"><button class="search-open" data-action="focus-search">Search</button><a class="cart-link" href="#cart">Cart <span id="cartCount">0</span></a></div>
  </header>
  <main id="app" tabindex="-1"></main>
  <script id="productData" type="application/json">{pdata}</script>
  {js_part}
  <footer class="footer">
    <div><strong>ELEMENTS LABS</strong><p>Premium research commerce structure with consistent product photography, packaging, batch IDs and analysis access.</p></div>
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
