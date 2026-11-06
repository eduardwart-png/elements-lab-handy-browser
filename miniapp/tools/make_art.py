"""Generates the schematic illustrations (own artwork, no manufacturer imagery).
Output: extensions/assets/dual/*.svg and extensions/assets/catalog/*.svg
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INK, PETROL, LINE, PANEL = '#2A2F36', '#0D5B6B', '#D9DEE2', '#F7F7F8'
ICON = ('<g transform="translate({x} {y}) scale({s})"><polygon points="48.58,7.31 18.75,28.43 18.92,74.17 46.08,94.63 55.00,87.59 28.67,68.43 28.00,58.43 '
        '47.67,43.80 48.08,31.67 28.67,43.98 28.17,34.91 48.58,19.81" fill="#2A2F36"/><polygon points="59.58,12.59 50.25,19.91 50.33,80.56 55.08,84.91 '
        '80.00,67.04 79.00,54.35 59.83,67.22" fill="#0D5B6B"/></g>')


def head(w, h, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="{label}">'
            f'<rect width="{w}" height="{h}" fill="{PANEL}"/><rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" fill="none" stroke="{LINE}"/>')


def brand(x, y, s=0.5):
    return (ICON.format(x=x, y=y, s=s) +
            f'<text x="{x+52}" y="{y+32}" font-family="Space Grotesk,Arial,sans-serif" font-size="21" font-weight="700" letter-spacing="2" fill="{INK}">ELEMENTS LABS</text>')


def label(x, y, tx, ty, text, anchor='middle'):
    return (f'<line x1="{x}" y1="{y}" x2="{tx}" y2="{ty}" stroke="{PETROL}" stroke-width="1"/>'
            f'<circle cx="{x}" cy="{y}" r="2.6" fill="{PETROL}"/>'
            f'<text x="{tx}" y="{ty + (24 if ty > y else -8)}" text-anchor="{anchor}" font-family="Arial,sans-serif" font-size="22" fill="{INK}">{text}</text>')


def cartridge(system, subtitle, form):
    w, h = 720, 430
    s = head(w, h, f'Schema Doppelkammer-System: {system}')
    s += brand(28, 22)
    s += f'<text x="{w-28}" y="40" text-anchor="end" font-family="Arial,sans-serif" font-size="21" font-weight="700" fill="{PETROL}">{system}</text>'
    s += f'<text x="{w-28}" y="68" text-anchor="end" font-family="Arial,sans-serif" font-size="18" fill="#5b6570">{subtitle}</text>'
    y0, y1 = 170, 270
    s += f'<rect x="96" y="{y0}" width="520" height="{y1-y0}" rx="10" fill="#ffffff" stroke="{INK}" stroke-width="2"/>'
    # liquid chamber (rear)
    s += f'<rect x="132" y="{y0+6}" width="190" height="{y1-y0-12}" fill="#cfe6ec" opacity=".85"/>'
    s += f'<path d="M132 {y0+30} q24 -9 48 0 t48 0 t48 0 t46 0" fill="none" stroke="{PETROL}" stroke-width="1.2" opacity=".6"/>'
    # dry substance chamber (front) - dots
    s += f'<rect x="354" y="{y0+6}" width="196" height="{y1-y0-12}" fill="#f3efe6"/>'
    for i in range(34):
        s += f'<circle cx="{366 + (i*37)%176}" cy="{y0+62+(i*53)%34}" r="2.2" fill="#b9a98a"/>'
    # bypass bulge on barrel wall
    s += f'<path d="M322 {y0} v-0 q0 -14 14 -14 h60 q14 0 14 14" fill="#ffffff" stroke="{INK}" stroke-width="2"/>'
    s += f'<line x1="338" y1="{y0-6}" x2="394" y2="{y0-6}" stroke="{PETROL}" stroke-width="2" stroke-dasharray="4 3"/>'
    # stoppers
    s += f'<rect x="118" y="{y0+3}" width="14" height="{y1-y0-6}" rx="3" fill="{INK}"/>'
    s += f'<rect x="322" y="{y0+3}" width="14" height="{y1-y0-6}" rx="3" fill="{PETROL}"/>'
    s += f'<rect x="550" y="{y0+3}" width="14" height="{y1-y0-6}" rx="3" fill="{INK}"/>'
    if form == 'syringe':
        s += f'<rect x="60" y="{y0+34}" width="36" height="32" fill="#fff" stroke="{INK}" stroke-width="2"/>'
        s += f'<line x1="132" y1="{y0+50}" x2="60" y2="{y0+50}" stroke="{INK}" stroke-width="4"/>'
        s += f'<rect x="36" y="{y0+18}" width="10" height="64" rx="2" fill="{INK}"/>'
        s += f'<rect x="616" y="{y0+40}" width="40" height="20" fill="#fff" stroke="{INK}" stroke-width="2"/>'
    else:
        s += f'<rect x="76" y="{y0+36}" width="22" height="28" fill="#fff" stroke="{INK}" stroke-width="2"/>'
        s += f'<rect x="616" y="{y0+30}" width="26" height="40" rx="4" fill="#fff" stroke="{INK}" stroke-width="2"/>'
    s += label(228, y0 + 26, 200, 350, 'Lösungsmittelkammer')
    s += label(452, y0 + 62, 500, 350, 'Trockenstoffkammer')
    s += label(329, y0 + 90, 329, 312, 'Mittelstopfen')
    s += label(366, y0 - 14, 366, 128, 'Bypass-Zone')
    s += label(125, y0 + 14, 110, 128, 'Kolben')
    s += label(557, y0 + 14, 590, 128, 'Verschluss')
    s += '</svg>'
    return s


DUAL = {
    'schott-dc': ('SCHOTT Pharma · Cartridges DC', 'Primärpackmittel · Karpule', 'cartridge'),
    'stevanato-dc': ('Stevanato Group · Dual Chamber', 'Primärpackmittel · Karpule', 'cartridge'),
    'vetter-vlk': ('Vetter · V-LK', 'Primärpackmittel · Karpule', 'cartridge'),
    'vetter-lyoject': ('Vetter · Lyo-Ject', 'Primärpackmittel · Spritze', 'syringe'),
    'nipro-dcpfs': ('Nipro · Dual Chamber PFS', 'Primärpackmittel · Spritze', 'syringe'),
    'ypsomed-lyotwist': ('Ypsomed · LyoTwist', 'Plattform · Lizenzangebot', 'cartridge'),
}

ICONS = {
    'rack': ''.join(f'<circle cx="{150+c*34}" cy="{120+r*34}" r="12" fill="none" stroke="{INK}" stroke-width="2"/>' for r in range(3) for c in range(4)),
    'cooler': f'<rect x="120" y="115" width="160" height="90" rx="8" fill="none" stroke="{INK}" stroke-width="2.5"/><path d="M160 115v-16h80v16" fill="none" stroke="{INK}" stroke-width="2.5"/><line x1="120" y1="145" x2="280" y2="145" stroke="{PETROL}" stroke-width="2.5"/>',
    'thermo': f'<rect x="188" y="85" width="24" height="100" rx="12" fill="none" stroke="{INK}" stroke-width="2.5"/><circle cx="200" cy="200" r="20" fill="{PETROL}"/><line x1="200" y1="110" x2="200" y2="190" stroke="{PETROL}" stroke-width="5"/>',
    'scale': f'<path d="M110 205h180" stroke="{INK}" stroke-width="3"/><rect x="130" y="165" width="140" height="40" rx="5" fill="none" stroke="{INK}" stroke-width="2.5"/><rect x="165" y="140" width="70" height="12" fill="{PETROL}"/><rect x="150" y="173" width="40" height="14" fill="none" stroke="{INK}" stroke-width="2"/>',
    'label': f'<path d="M130 120h110l30 30-30 30H130z" fill="none" stroke="{INK}" stroke-width="2.5"/><circle cx="148" cy="150" r="6" fill="{PETROL}"/><line x1="170" y1="140" x2="228" y2="140" stroke="{INK}" stroke-width="2"/><line x1="170" y1="156" x2="214" y2="156" stroke="{INK}" stroke-width="2"/>',
    'wipes': f'<rect x="130" y="150" width="140" height="48" rx="6" fill="none" stroke="{INK}" stroke-width="2.5"/><path d="M150 150c10-30 30-34 60-34 20 0 36 10 40 34" fill="none" stroke="{PETROL}" stroke-width="2.5"/><line x1="146" y1="174" x2="254" y2="174" stroke="{INK}" stroke-width="2"/>',
    'gloves': f'<path d="M140 195v-60c0-12 18-12 18 0v-22c0-12 18-12 18 0v-6c0-12 18-12 18 0v8c0-12 18-12 18 0v50l14-18c9-8 22 2 14 12l-34 50c-8 10-18 14-32 14h-20c-14 0-22-8-22-20z" fill="none" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round"/>',
    'pipette': f'<path d="M210 80h22v66l-11 56-11-56z" fill="none" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round"/><rect x="204" y="62" width="34" height="18" rx="4" fill="{PETROL}"/><line x1="221" y1="190" x2="221" y2="206" stroke="{PETROL}" stroke-width="3"/>',
}


def tile(key):
    s = head(400, 300, 'Mustergrafik Zusatzkatalog') + brand(20, 14, 0.4)
    s += ICONS[key]
    s += f'<text x="20" y="284" font-family="Arial,sans-serif" font-size="15" fill="#5b6570">Platzhalter · bitte durch Artikelbild ersetzen</text></svg>'
    return s


def main():
    d = ROOT / 'extensions/assets/dual'
    c = ROOT / 'extensions/assets/catalog'
    d.mkdir(parents=True, exist_ok=True)
    c.mkdir(parents=True, exist_ok=True)
    for key, (name, sub, form) in DUAL.items():
        (d / f'{key}.svg').write_text(cartridge(name, sub, form))
    for key in ICONS:
        (c / f'{key}.svg').write_text(tile(key))
    print('dual', len(DUAL), 'catalog', len(ICONS))


if __name__ == '__main__':
    main()
