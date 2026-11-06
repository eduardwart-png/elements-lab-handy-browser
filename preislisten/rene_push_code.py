"""Code-Stand des Live-Shops (miniapp/) kontrolliert in Renés Repo-Kopie uebernehmen (Gegenstueck zu rene_sync.py pull-code).

Warum: rene_sync.py push-data kopiert nur Daten (terms.json, Preise ...). Aendern sich Konditionen-Schluessel oder Frontend-Code, braucht René den passenden Code,
sonst bricht sein Test-Shop (24.10./25.10.: alter terms.py verlangt shipping_cents, neues terms.json hat den Schluessel nicht mehr).

Aufruf:  python rene_push_code.py [Zielordner]              Trockenlauf: zeigt Dateien, scannt auf verbotene Begriffe, aendert nichts
         python rene_push_code.py [Zielordner] --apply      kopiert; Zielordner ist nach Vorgabe eine Scratch-Kopie oder Renés Repo (kein Commit, kein Push)
Regeln wie make_design_package.py: EXCLUDE_FILES (Preislogik/Einkauf/interne Tests) werden nie kopiert, FORBIDDEN-Muster brechen ab.
Zielordner wird NIE neu aufgebaut oder geloescht; es werden nur Dateien aus der Positivliste ueberschrieben oder ergaenzt.
"""
import filecmp
import re
import shutil
import sys
from pathlib import Path

PRE = Path('/Users/eduardwart/Projekte-Mac')
LIVE = PRE / 'elements-lab-telegram/miniapp'
DEFAULT_TARGET = PRE / 'elements-lab-telegram-shop-design'
sys.path.insert(0, str(PRE / 'elements-lab-telegram/preislisten'))
sys.dont_write_bytecode = True
import make_design_package as mdp  # noqa: E402  (nur EXCLUDE_FILES/FORBIDDEN lesen, baut nichts)

# Positivliste: nur Laufzeit-Code und Tests, die ohne interne Dateien laufen
ROOT_FILES = ['bot.py', 'build.py', 'live.py', 'server.py', 'terms.py']
CODE_DIRS = ['extensions', 'tests']      # plus Produktbilder aus asset-cache-current (siehe candidates)
# zusaetzlich nie (interne Preis-/Listen-/Sortiment-Tests, lesen preislisten/ oder Lieferantendaten)
EXTRA_EXCLUDE = {'tests/test_preisfamilie.py', 'tests/test_sortiment.py', 'tests/test_pricing.py', 'tests/test_texte.py'}


def candidates():
    out = []
    for f in ROOT_FILES:
        out.append(Path(f))
    for d in CODE_DIRS:
        for p in sorted((LIVE / d).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc' and p.name != '.DS_Store':
                out.append(p.relative_to(LIVE))
    # Produktbilder (reine Bilddateien, keine Preise/Lieferantendaten): neue oder geaenderte Dateien aus asset-cache-current
    for p in sorted((LIVE / 'asset-cache-current').rglob('*')):
        if p.is_file() and p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.svg') and p.name != '.DS_Store':
            out.append(p.relative_to(LIVE))
    return [rel for rel in out if rel.as_posix() not in mdp.EXCLUDE_FILES and rel.as_posix() not in EXTRA_EXCLUDE]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    apply = '--apply' in sys.argv
    target = Path(args[0]) if args else DEFAULT_TARGET
    if not (target / 'build.py').is_file():
        sys.exit(f'Zielordner {target} sieht nicht wie ein Shop-Ordner aus')
    verboten, aenderungen = [], []
    for rel in candidates():
        src, dst = LIVE / rel, target / rel
        try:
            text = src.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            text = ''
        hits = sorted({m.group(0) for m in mdp.FORBIDDEN.finditer(text)})
        if hits:
            verboten.append((rel.as_posix(), hits))
        if not dst.is_file():
            aenderungen.append(('neu', rel))
        elif not filecmp.cmp(src, dst, shallow=False):
            aenderungen.append(('geaendert', rel))
    for art, rel in aenderungen:
        print(f'  {art:9} {rel.as_posix()}')
    print(f'{len(aenderungen)} Dateien zu uebernehmen; Zielordner {target}')
    if verboten:
        for r, h in verboten:
            print(f'VERBOTEN in {r}: {h}')
        sys.exit('Abbruch: verbotene Begriffe im Code-Stand (nichts kopiert)')
    if apply:
        for art, rel in aenderungen:
            (target / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(LIVE / rel, target / rel)
        print('kopiert:', len(aenderungen))


if __name__ == '__main__':
    main()
