"""Konditionen (Inhaber 24.10.2026): Mindestbestellwert = Direktlieferung, Versand immer inklusive, Sammelbestellung nur unterhalb des
Mindestbestellwerts, Mengenrabatt nur auf rabattfaehige 10er-Packs. Eine Quelle (data/terms.json); Server und Frontend (extensions/terms.js)
rechnen identisch, tests/test_terms.py prueft die Paritaet."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class MinOrderError(ValueError):
    def __init__(self, minimum_cents, subtotal_cents):
        super().__init__('Minimum order value not reached')
        self.minimum_cents, self.subtotal_cents = minimum_cents, subtotal_cents


def load_terms():
    return json.loads((ROOT / 'data/terms.json').read_text())


def relaxed(terms=None):
    """Konditionen ohne Mindestwert und Rabatt (fuer Altfaelle in Tests)."""
    t = dict(terms or load_terms())
    t.update(min_order_cents=0, collective_min_cents=0, tiers=[])
    return t


def short_eur(cents):
    """Betrag fuer Texte: 500 € / 2.500 € / 499,99 € (wie ELTerms.short in terms.js, dort mit geschuetztem Leerzeichen vor dem Euro-Zeichen)."""
    return f'{cents // 100:,}'.replace(',', '.') + (f',{cents % 100:02d}' if cents % 100 else '') + ' €'


def text_vars(terms=None):
    """Konditionen als Textbausteine fuer bot.py und make_pricelist.py (gleich zu ELTerms.vars() in terms.js, Sprache DE)."""
    t = terms or load_terms()
    w = t['delivery_weeks']
    return {'min': short_eur(t['min_order_cents']), 'cmin': short_eur(t['collective_min_cents']), 'wk': f"{w['min']} bis {w['max']}",
            'tiers': ' · '.join(f"{x['percent']} % ab {short_eur(x['min_cents'])}" for x in t['tiers'])}


def calc(lines, terms, collective=False):
    """lines: iterable of (quantity, unit_price_cents or None, discount_ok). Alle Betraege in Cent, ganzzahlig.
    Stufe und Mindestwert zaehlen den Warenwert vor Rabatt; Rabatt nur auf rabattfaehige Zeilen; Versand ist immer 0.
    Sammelbestellung gilt nur unterhalb des Mindestbestellwerts; ab dem Mindestbestellwert wird der Wunsch verworfen (Direktlieferung)."""
    lines = list(lines)
    subtotal = sum(q * c for q, c, _ in lines if c is not None)
    eligible = sum(q * c for q, c, ok in lines if c is not None and ok)
    percent = max([t['percent'] for t in terms['tiers'] if subtotal >= t['min_cents']] or [0])
    discount = eligible * percent // 100
    net = subtotal - discount
    direct = subtotal >= terms['min_order_cents']
    collective = bool(collective) and not direct
    minimum = terms['collective_min_cents'] if collective else terms['min_order_cents']
    quote = sum(c is None for _, c, _ in lines)
    return {'subtotal_cents': subtotal, 'eligible_cents': eligible, 'discount_percent': percent, 'discount_cents': discount, 'shipping_cents': 0,
            'collective': collective, 'direct': direct, 'payable_cents': None if quote else net, 'min_order_cents': minimum, 'min_ok': subtotal >= minimum}
