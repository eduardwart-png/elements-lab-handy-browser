#!/usr/bin/env python3
"""make_bundle.py - packt den lauffaehigen Shop (ohne Geheimnisse, ohne Bauhilfen) fuer einen Reserveknoten.

Ergebnis: dist/shop-standby.tar.gz  (Inhalt: miniapp/ ohne runtime, evidence, .venv-build, asset-cache*, katalog-bilder, tests)
Geheimnisse (runtime/.env.elements, wrangler-Anmeldung) werden NIE eingepackt; bootstrap.sh bekommt sie getrennt per SSH.
"""
import tarfile
import time
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "miniapp"
OUT = Path(__file__).resolve().parent / "dist"
SKIP_DIRS = {"runtime", "evidence", ".venv-build", "asset-cache", "asset-cache-current", "katalog-bilder", "tests", "__pycache__", "tools", "extensions"}
SKIP_SUFFIX = {".command", ".pyc", ".orig", ".sqlite", ".sqlite3", ".db"}

OUT.mkdir(exist_ok=True)
target = OUT / "shop-standby.tar.gz"
n = 0
with tarfile.open(target, "w:gz") as tar:
    for p in sorted(SRC.rglob("*")):
        rel = p.relative_to(SRC)
        if any(part in SKIP_DIRS for part in rel.parts) or p.suffix in SKIP_SUFFIX or not p.is_file():
            continue
        tar.add(p, arcname=f"miniapp/{rel}")
        n += 1
    (SRC / "runtime").exists()
print(f"{n} Dateien, {target.stat().st_size/1e6:.1f} MB -> {target} ({time.strftime('%Y-%m-%d %H:%M')})")
