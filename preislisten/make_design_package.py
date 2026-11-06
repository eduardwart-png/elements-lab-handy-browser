"""NICHT MEHR AUSFUEHREN, seit Rene im Repo arbeitet: loescht den Zielordner samt .git. Datenstand: rene_sync.py push-data.

Design-Paket fuer Rene (Shop-Gestaltung): kopiert miniapp/ OHNE Einkaufs-/Lieferantendaten, Zugangsdaten, Laufzeitdaten und Preislogik.

Aufruf: python make_design_package.py [Zielordner]   (Standard: ~/Projekte-Mac/elements-lab-telegram-shop-design)
Danach Pruefung auf verbotene Begriffe (Lieferant, Einkauf, Marktquellen, Zugangsdaten); bei Treffern bricht das Skript ab.
"""
import re
import shutil
import sys
import zipfile
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / 'miniapp'
DEST = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home() / 'Projekte-Mac' / 'elements-lab-telegram-shop-design'
EXCLUDE_DIRS = {'asset-cache', 'runtime', '.venv-build', '__pycache__', 'katalog-bilder', 'node_modules'}
EXCLUDE_FILES = {'tools/apply_pricing.py', 'tools/catalog_lines.py', 'tests/test_pricing.py', 'AENDERUNGEN.md', 'BERICHT.md', 'checkpoint.json', 'katalog.csv', 'README.md', '.DS_Store',
                 'Katalog-aktualisieren.command', 'data/reference-prices.json'}
KEEP_EVIDENCE = {'reference-current'}
FORBIDDEN = re.compile(r'\bting\b|Einkaufspreis|Einkaufskosten|Lieferantenpreis|Lieferantenliste|shop_costs|Wholesale|peptidehaus|qsc-eu|markt_preise|TOSHIBA|\.env\.elements=|ELEMENTS_TELEGRAM_BOT_TOKEN=\S|[0-9]{8,10}:[A-Za-z0-9_-]{30,}', re.I)
TEXT_SUFFIX = {'.py', '.js', '.json', '.md', '.css', '.html', '.txt', '.csv', '.cjs', '.command', '.gitignore'}


def keep(path: Path) -> bool:
    rel = path.relative_to(SRC)
    parts = rel.parts
    if any(p in EXCLUDE_DIRS for p in parts):
        return False
    if parts[0] == 'evidence' and not (len(parts) > 1 and parts[1] in KEEP_EVIDENCE):
        return False
    if rel.as_posix() in EXCLUDE_FILES or path.name == '.DS_Store' or path.suffix == '.pyc':
        return False
    return True


def main():
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    copied = 0
    for path in sorted(SRC.rglob('*')):
        if path.is_dir() or not keep(path):
            continue
        target = DEST / path.relative_to(SRC)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied += 1
    # Tests, die die ausgeschlossene Preislogik brauchen, ueberspringen statt scheitern
    tp = DEST / 'tests/test_terms.py'
    if tp.is_file():
        text = tp.read_text()
        text = text.replace("class OwnerPriceRules(unittest.TestCase):", "@unittest.skipUnless((ROOT / 'tools/catalog_lines.py').is_file(), 'Preislogik gehoert dem Inhaber, nicht im Design-Paket')\nclass OwnerPriceRules(unittest.TestCase):")
        tp.write_text(text)
    (DEST / 'README_RENE.md').write_text((Path(__file__).resolve().parent / 'README_RENE.md').read_text())
    (DEST / 'UEBERGABE_RENE.md').write_text((Path(__file__).resolve().parent / 'UEBERGABE_RENE.md').read_text())
    (DEST / '.gitignore').write_text('runtime/\n__pycache__/\n*.pyc\n.env\n.env.*\n.DS_Store\n.venv-build/\nevidence/build.json\n')
    hits = []
    for path in DEST.rglob('*'):
        if path.is_file() and (path.suffix in TEXT_SUFFIX or path.name == '.gitignore') and path.stat().st_size < 3_000_000:
            try:
                text = path.read_text(errors='ignore')
            except OSError:
                continue
            for match in FORBIDDEN.finditer(text):
                hits.append((str(path.relative_to(DEST)), match.group(0)[:40]))
    if hits:
        print('ABBRUCH, verbotene Begriffe:', hits[:20], len(hits))
        sys.exit(1)
    size = sum(f.stat().st_size for f in DEST.rglob('*') if f.is_file())
    archive = DEST.with_suffix('.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(DEST.rglob('*')):
            if f.is_file():
                z.write(f, f'Elements-Labs-Shop/{f.relative_to(DEST)}')
    print('Dateien', copied, f'{size / 1e6:.1f} MB', '->', DEST, '| ZIP', archive, f'{archive.stat().st_size / 1e6:.1f} MB')


if __name__ == '__main__':
    main()
