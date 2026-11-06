#!/usr/bin/env python3
"""Veraltete Elements-Labs-Listen finden und in den Papierkorb legen (Eddy 25.10.2026: "Wenn eine Liste veraltet ist, loescht die raus ...
es darf keine Reibungspunkte geben").

Massgeblich ist ausschliesslich ~/Desktop/Elements_Lab/{1 FÜR TING, 2 FÜR RENÉ, 3 FÜR EDDY (intern)}. Jede von uns erzeugte Liste mit bekanntem Namen
ausserhalb davon (Downloads, Desktop, Dokumente) ist veraltet, sobald sie sich vom aktuellen Stand unterscheidet. Veraltete Listen kommen in den
Papierkorb (~/.Trash, wiederherstellbar) und werden protokolliert. Lieferanten-Quellen (VERKAUFSBLATT, EUR PRICE, Wholesale, Ting_Pens/Vials) und
fremde Projekte werden nie angefasst.

  listen_aufraeumen.py --pruefen [--json]    nur melden, Exit 1 bei veralteten Listen oder abweichendem Desktop-Stand
  listen_aufraeumen.py --aufraeumen          veraltete Kopien in den Papierkorb legen (Exit 0 wenn danach alles sauber)
Desktop-Stand gegen den frischen Listenlauf (Staging _out/desktop): weicht er ab, wird nur gemeldet (Abhilfe: pipeline_v3.sh cutover --freigabe-eddy).
"""
import hashlib
import json
import re
import shutil
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HOME = Path.home()
DESK = HOME / 'Desktop' / 'Elements_Lab'
CANON_DIRS = ('1 FÜR TING', '2 FÜR RENÉ', '3 FÜR EDDY (intern)')
PARTNER_DIR = '4 FÜR KOOPERATIONSPARTNER'   # eigene Partner-Listen (partner_listen.py): nie als veraltet melden, Kopien davon (z. B. beim Versand) bleiben liegen
STAGING_OUT = HOME / 'Projekte-Mac/elements-lab-telegram-staging/_out/desktop'
ROOTS = [HOME / 'Desktop', HOME / 'Downloads', HOME / 'Documents']
LOG = HOME / 'Projekte-Mac/_DATA/ELEMENTS_STRATEGIE_20261024/listen_aufraeumen_log.jsonl'
MAX_DEPTH = 3

# Namen unserer Listen aller bisherigen Staende (auch Telegram-Duplikate wie "... (1).pdf")
PATTERNS = [re.compile(p, re.I) for p in (
    r'^elements[-_ ]labs[-_ ]preisliste',
    r'^aktuelle elements labs liste',
    r'^preisliste f(ü|u|ue)r kunden',
    r'^elements labs preispositionierung',
    r'^margen\s*[–-]\s*einkauf',
    r'^ting-preischeck',
    r'^top-20 bestseller',
    r'^elements labs shop design-paket',
    r'^elements labs.*(liste|preise?)\.(pdf|xlsx|csv)$',
)]
SOURCE = re.compile(r'verkaufsblatt|eur price|wholesale|ting_pens|ting_vials', re.I)
SKIP_PARTS = ('Projekte-Mac', 'Obsidian', 'node_modules', '.git', 'archiv', 'Library', 'EDDY – AKTUELL')


def is_list(p: Path) -> bool:
    return not SOURCE.search(p.name) and any(rx.search(p.name) for rx in PATTERNS)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def content_sig(p: Path) -> str:
    """Inhaltsstempel: PDF = normalisierter Text (Erstellzeit im Binaerstand ist egal), XLSX = Blattinhalt, sonst Bytes."""
    try:
        if p.suffix.lower() == '.pdf':
            try:
                import pymupdf as fitz
            except ImportError:
                import fitz
            txt = '\n'.join(pg.get_text() for pg in fitz.open(p))
            return 'pdf:' + hashlib.sha256(re.sub(r'\s+', ' ', txt).encode()).hexdigest()
        if p.suffix.lower() == '.xlsx':
            import zipfile
            z = zipfile.ZipFile(p)
            data = b''.join(z.read(n) for n in sorted(z.namelist()) if n.startswith('xl/worksheets/') or n == 'xl/sharedStrings.xml')
            return 'xlsx:' + hashlib.sha256(data).hexdigest()
    except Exception:  # noqa: BLE001 - ohne Textleser faellt der Vergleich auf Bytes zurueck
        pass
    return 'raw:' + sha(p)


def walk(root: Path):
    if not root.is_dir():
        return
    base = len(root.parts)
    for p in root.rglob('*'):
        if len(p.parts) - base > MAX_DEPTH or not p.is_file():
            continue
        s = str(p)
        if any(part in s for part in SKIP_PARTS) or p.name == '.DS_Store':
            continue
        yield p


def canonical_files():
    out = {}
    for d in CANON_DIRS:
        base = DESK / d
        if base.is_dir():
            for p in base.iterdir():
                if p.is_file() and p.name != '.DS_Store':
                    out[f'{d}/{p.name}'] = p
    return out


def expected_files():
    out = {}
    if STAGING_OUT.is_dir():
        for p in STAGING_OUT.rglob('*'):
            if p.is_file() and p.name != '.DS_Store':
                out[str(p.relative_to(STAGING_OUT))] = p
    return out


def analyse():
    canon = canonical_files()
    expected = expected_files()
    canon_sigs = {content_sig(p) for rel, p in canon.items() if is_list(p)}
    partner = DESK / PARTNER_DIR
    if partner.is_dir():
        canon_sigs |= {content_sig(p) for p in partner.iterdir() if p.is_file() and is_list(p)}
    stale_copies, desktop_abweichung, fremd_in_kanon = [], [], []
    canon_set = {p.resolve() for p in canon.values()}
    for root in ROOTS:
        for p in walk(root):
            if p.resolve() in canon_set or DESK in p.parents:
                continue
            if is_list(p) and content_sig(p) not in canon_sigs:
                stale_copies.append(p)
    for rel, p in canon.items():
        # Liste im massgeblichen Ordner, die der aktuelle Lauf gar nicht mehr erzeugt (z. B. alter Dateiname)
        if is_list(p) and expected and rel not in expected and not rel.startswith('2 FÜR RENÉ'):
            fremd_in_kanon.append(p)
    for rel, e in expected.items():
        d = canon.get(rel)
        if d is None:
            desktop_abweichung.append(f'fehlt auf dem Desktop: {rel}')
        elif rel.startswith('2 FÜR RENÉ') and d.suffix == '.zip':
            continue
        elif content_sig(d) != content_sig(e):
            desktop_abweichung.append(f'weicht vom frischen Listenlauf ab: {rel}')
    return stale_copies, fremd_in_kanon, desktop_abweichung


def to_trash(p: Path) -> Path:
    trash = HOME / '.Trash'
    trash.mkdir(exist_ok=True)
    dst = trash / p.name
    if dst.exists():
        dst = trash / f'{p.stem} {time.strftime("%Y%m%d-%H%M%S")}{p.suffix}'
    shutil.move(str(p), str(dst))
    return dst


def main(argv):
    stale, fremd, abw = analyse()
    todo = stale + fremd
    moved = []
    if '--aufraeumen' in argv:
        for p in todo:
            dst = to_trash(p)
            moved.append((str(p), str(dst)))
        if moved:
            LOG.parent.mkdir(parents=True, exist_ok=True)
            with LOG.open('a') as fh:
                for src, dst in moved:
                    fh.write(json.dumps({'zeit': time.strftime('%Y-%m-%dT%H:%M:%S'), 'von': src, 'nach': dst}, ensure_ascii=False) + '\n')
        stale, fremd, abw = analyse()
    result = {
        'veraltete_kopien': [str(p) for p in stale],
        'unbekannte_listen_im_massgeblichen_ordner': [str(p) for p in fremd],
        'desktop_weicht_ab': abw,
        'in_papierkorb': moved,
        'sauber': not stale and not fremd and not abw,
    }
    if '--json' in argv:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        for k in ('in_papierkorb',):
            for src, dst in moved:
                print(f'Papierkorb: {src}')
        for p in stale:
            print(f'VERALTET: {p}')
        for p in fremd:
            print(f'VERALTET (im massgeblichen Ordner): {p}')
        for a in abw:
            print(f'ABWEICHUNG: {a}')
        print('SAUBER' if result['sauber'] else 'NICHT SAUBER')
    return 0 if result['sauber'] else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
