"""Zwei Richtungen zwischen Eddys Live-Shop (miniapp/) und Renés Repo-Kopie (elements-lab-telegram-shop-design/):

  python rene_sync.py push-data   Datenstand (Preise, Katalog, Bedingungen, Preisliste) ins Repo schreiben, committen, pushen
  python rene_sync.py pull-code   Renés Aenderungen holen und mit dem Live-Shop vergleichen (nur anzeigen)
  python rene_sync.py pull-code --apply   uebernehmen, Tests laufen lassen; bei Fehlern wird zurueckgesetzt (kein Neustart)

Der Zielordner wird NIE neu aufgebaut (make_design_package.py loescht ihn und waere hier gefaehrlich).
"""
import filecmp
import os
import shutil
import subprocess
import sys
from pathlib import Path

PRE = Path('/Users/eduardwart/Projekte-Mac')
LIVE = PRE / 'elements-lab-telegram/miniapp'
REPO = PRE / 'elements-lab-telegram-shop-design'
DATA_FILES = ['data/products.json', 'data/shop-formats.json', 'data/catalog-packs.json', 'data/catalog.json', 'data/catalog-template.csv', 'data/terms.json', 'data/preisliste.pdf']
CODE_SKIP = ('data/', 'public/', 'runtime/', 'asset-cache', '.git', '.venv-build', 'evidence/', '__pycache__', 'README_RENE.md', 'UEBERGABE_RENE.md', 'Test-starten.command', '.gitignore')
ENV = {**os.environ, 'GIT_AUTHOR_NAME': 'eduardwart-png', 'GIT_COMMITTER_NAME': 'eduardwart-png', 'GIT_AUTHOR_EMAIL': 'eduard.wart@googlemail.com', 'GIT_COMMITTER_EMAIL': 'eduard.wart@googlemail.com'}


def git(*args, cwd=REPO):
    r = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, env=ENV)
    return r.returncode, (r.stdout + r.stderr).strip()


def push_data():
    changed = []
    for rel in DATA_FILES:
        src, dst = LIVE / rel, REPO / rel
        if src.is_file() and (not dst.is_file() or not filecmp.cmp(src, dst, shallow=False)):
            shutil.copy2(src, dst)
            changed.append(rel)
    if not changed:
        print('Datenstand unveraendert.')
        return
    git('add', '-A')
    print(git('commit', '-q', '-m', 'Datenstand von Eddy: ' + ', '.join(Path(c).name for c in changed))[1])
    print(git('push', '-q', 'origin', 'main'), '| geaendert:', changed)


def code_files():
    out = []
    for p in sorted(REPO.rglob('*')):
        rel = p.relative_to(REPO).as_posix()
        if p.is_file() and not rel.startswith(CODE_SKIP) and not any(part in ('__pycache__', '.git') for part in p.parts):
            out.append(rel)
    return out


def pull_code(apply):
    print(git('pull', '--rebase', '-q', 'origin', 'main')[1] or 'pull ok')
    diffs = [r for r in code_files() if not (LIVE / r).is_file() or not filecmp.cmp(REPO / r, LIVE / r, shallow=False)]
    print('Abweichungen zum Live-Shop:', len(diffs))
    for r in diffs:
        print('  ', r, '(neu)' if not (LIVE / r).is_file() else '')
    if not apply or not diffs:
        return
    backup = LIVE.parent / '_live_backup_before_rene'
    if backup.exists():
        shutil.rmtree(backup)
    for r in diffs:
        if (LIVE / r).is_file():
            (backup / r).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(LIVE / r, backup / r)
        (LIVE / r).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / r, LIVE / r)
    py = LIVE / '.venv-build/bin/python'
    ok = subprocess.run([str(py), 'build.py'], cwd=LIVE, capture_output=True, text=True).returncode == 0
    t = subprocess.run([str(py), '-m', 'unittest', 'discover', '-s', 'tests'], cwd=LIVE, capture_output=True, text=True)
    ok = ok and t.returncode == 0
    print('Tests:', [l for l in (t.stdout + t.stderr).splitlines() if l.startswith(('Ran', 'OK', 'FAILED'))])
    if not ok:
        for r in diffs:
            b = backup / r
            if b.is_file():
                shutil.copy2(b, LIVE / r)
            else:
                (LIVE / r).unlink(missing_ok=True)
        subprocess.run([str(py), 'build.py'], cwd=LIVE, capture_output=True)
        print('FEHLER: zurueckgesetzt, nichts uebernommen.')
        sys.exit(1)
    print('Uebernommen. Live-Neustart erfolgt separat: launchctl kickstart -k gui/$(id -u)/dev.elementslabs.telegram-shop')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'push-data':
        push_data()
    elif cmd == 'pull-code':
        pull_code('--apply' in sys.argv)
    else:
        print(__doc__)
