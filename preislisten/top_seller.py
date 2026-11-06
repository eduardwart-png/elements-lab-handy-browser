"""Top-Seller-Rangfolge aus der Bestseller-Sortierung (WooCommerce Store-API orderby=popularity) von 5 EU-Shops + Zuordnung zu unseren Katalogzeilen."""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'miniapp' / 'tools'))

RANKS = HERE / 'markt_bestseller.json'  # Stand 24.10.2026: Sortierung 'meistverkauft' von 5 EU-Shops (Store-API)
ACCESSORY = ('wasser', 'water', 'spritze', 'syringe', 'tupfer', 'swab', 'tuch', 'tücher', 'kanüle', 'cold', 'disinfect', 'cartridge')
ALIASES = [
    (r'retatrutid|\brt\d+|glp-?3|\breta\b', 'Retatrutide'), (r'tirzepatid|\bt3rz|\btrz\b', 'Tirzepatide'), (r'semaglutid', 'Semaglutide'), (r'glow', 'GLOW-Blend'), (r'klow', 'KLOW-Blend'),
    (r'bpc.?157\s*(\+|&|und)\s*tb', 'BPC-157 + TB-500'), (r'bpc.?157|\bbp157', 'BPC-157'), (r'tb.?500', 'TB-500'), (r'ghk|\bcu\s*\d+\s*mg', 'GHK-Cu'), (r'mots', 'MOTS-C'),
    (r'cjc.?1295', 'CJC-1295'), (r'ipamorelin|\bip\d+', 'Ipamorelin'), (r'epithalon', 'Epithalon'), (r'selank', 'Selank'), (r'semax', 'Semax'), (r'tesamorelin', 'Tesamorelin'),
    (r'ss-?31', 'SS-31'), (r'\bkpv', 'KPV'), (r'thymosin', 'Thymosin Alpha-1'), (r'melanotan|\bmt-?[12]', 'Melanotan'), (r'nad\+?', 'NAD+'), (r'll-?37', 'LL-37'), (r'cagrilint', 'Cagrilintide'),
    (r'5-?amino', '5-Amino-1MQ'), (r'hgh|somatropin', 'HGH'), (r'dsip', 'DSIP'), (r'l-carnitin', 'L-Carnitine'), (r'aod', 'AOD-9604'), (r'mazdutid', 'Mazdutide'), (r'survodutid', 'Survodutide'),
]


def canon(title):
    t = title.lower()
    if any(a in t for a in ACCESSORY):
        return 'ZUBEHOER'
    for pat, name in ALIASES:
        if re.search(pat, t):
            return name
    return None


def ranking():
    ranks = json.loads(RANKS.read_text())
    score, shops, first = defaultdict(float), defaultdict(set), {}
    for shop, lst in ranks.items():
        used = set()
        for pos, title in enumerate(lst[:25]):
            c = canon(title)
            if c and c != 'ZUBEHOER' and c not in used:
                used.add(c)
                score[c] += max(0, 26 - pos)
                shops[c].add(shop)
                first.setdefault(c, {})[shop] = pos + 1
    return sorted(((c, s, shops[c], first[c]) for c, s in score.items()), key=lambda x: (-x[1]))


def catalog_rows(substance):
    """Katalogzeilen (Vial/Doppelkammer) zu einem Wirkstoff; Blends werden nicht in Einzelwirkstoffe gemischt."""
    import catalog_lines as cl
    out = []
    for x in cl.lines(recommend=False):
        n = x['name']
        if substance in ('GLOW-Blend', 'KLOW-Blend'):
            ok = n.upper().startswith(substance[:4])
        elif substance == 'BPC-157':
            ok = n == 'BPC-157'
        elif substance == 'CJC-1295':
            ok = n.startswith('CJC-1295') and 'Ipamorelin' not in n
        elif substance == 'Melanotan':
            ok = n.startswith('Melanotan')
        else:
            ok = n.lower() == substance.lower() or n.lower().startswith(substance.lower() + ' (')
        if ok:
            out.append(x)
    return out


def top20():
    """Die 20 meistverkauften Wirkstoffe, die im Katalog vorkommen (Reihenfolge = Rang)."""
    return [t[0] for t in ranking() if catalog_rows(t[0])][:20]


if __name__ == '__main__':
    top = ranking()
    print(len(top), 'Wirkstoffe in Rangfolge')
    n = 0
    for c, s, sh, pos in top:
        rows = catalog_rows(c)
        print(f'{c:18} Punkte {s:4.0f} Shops {len(sh)} im Katalog: {len(rows)} Zeilen', dict(pos))
        n += 1
        if n >= 30:
            break
