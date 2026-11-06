#!/bin/zsh
# Gesamte Preis-Pipeline nach Daten-/Regeländerung: Erzeuger -> Tests -> PDFs (Desktop) -> Repo-Daten. Neustart/ZIP separat.
set -e
P=~/Projekte-Mac/elements-lab-telegram/preislisten
M=~/Projekte-Mac/elements-lab-telegram/miniapp
V=~/.hermes/tools/elements-preis/v/bin/python
T="$HOME/Desktop/Elements_Lab/3 FÜR EDDY (intern)"
cd $P
$V ~/.hermes/cache/scratch/run_pos.py | tail -1
$V sortiment_ergaenzung.py | head -1
$V empfehlung.py | tail -2
cd $M
.venv-build/bin/python tools/apply_pricing.py | tail -1
.venv-build/bin/python build.py | tail -1
.venv-build/bin/python -m unittest discover -s tests -p "test_*.py" 2>&1 | grep -E "^(Ran|OK|FAILED|FAIL:|ERROR:)"
cd $P
for s in make_pricelist.py top20_pdf.py ting_pdf.py marge_pdf.py; do $V $s | tail -1 | cut -c1-110; done
cp $M/data/preisliste.pdf "$T/Preisliste für Kunden (auch im Bot).pdf"
cp "Elements Labs Ting-Preischeck.pdf" "$T/Ting-Preischeck, Verhandlung, Händlermarge.pdf"
cp "Elements Labs Top-20 Bestseller.pdf" "$T/Top-20 Bestseller mit Preisen.pdf"
cp "Elements Labs Margenübersicht.pdf" "$T/MARGEN – Einkauf, Verkauf, Marge je Produkt.pdf"
$V rene_sync.py push-data | tail -1
