#!/bin/zsh
# Preis-Pipeline v3 (STAGING): Erzeuger -> v3-Tabelle (preisfamilie_v3.csv -> preisempfehlung.json -> Shop-Daten) -> alle PDFs/Tabellen
# nach _out/desktop/<Ordner>/<heutiger Desktop-Dateiname> + Kundenpreisliste nach miniapp/data/preisliste.pdf (Bot) -> maschinelle Pruefung.
#   pipeline_v3.sh                      Neuaufbau + Pruefung. Schreibt NUR im Staging (kein Desktop, kein push-data, kein Neustart).
#   pipeline_v3.sh pruefen              nur die Pruefung (_out/pruefung_v3.json, _out/render/)
#   pipeline_v3.sh marge                nur die interne Margenliste (mit Kundensicht) neu + Pruefung; fasst miniapp/ nicht an
#   Kennzahlen-Datei der Kundensicht: ZEILEN_CSV=<datei> (Standard team5/zeilen_F.csv, falls vorhanden, sonst team4/zeilen_M1_E2.csv)
#   pipeline_v3.sh cutover --freigabe-eddy   ERST NACH EDDYS JA: alte Desktop-Dateien archivieren, neue Dateien auf den Desktop kopieren.
set -e
setopt null_glob pipefail
S=$HOME/Projekte-Mac/elements-lab-telegram-staging
P=$S/preislisten
M=$S/miniapp
V=$HOME/.hermes/tools/elements-preis/v/bin/python
SHOPPY=$M/.venv-build/bin/python
[[ -x $SHOPPY ]] || SHOPPY=$V  # Staging hat kein .venv-build: Team-Python (stdlib + pymupdf/openpyxl/reportlab) genuegt fuer apply_pricing/build/tests
O=$S/_out
D=$O/desktop
TING="1 FÜR TING"; RENE="2 FÜR RENÉ"; EDDY="3 FÜR EDDY (intern)"
DESK=$HOME/Desktop/Elements_Lab
export PYTHONDONTWRITEBYTECODE=1
STRAT=$HOME/Projekte-Mac/_DATA/ELEMENTS_STRATEGIE_20261024
if [[ -z ${ZEILEN_CSV:-} ]]; then
  if [[ -f $STRAT/team6/zeilen_G.csv ]]; then ZEILEN_CSV=$STRAT/team6/zeilen_G.csv; elif [[ -f $STRAT/team5/zeilen_F.csv ]]; then ZEILEN_CSV=$STRAT/team5/zeilen_F.csv; else ZEILEN_CSV=$STRAT/team4/zeilen_M1_E2.csv; fi
fi
[[ -f $ZEILEN_CSV ]] || { echo "Kennzahlen-Datei fehlt: $ZEILEN_CSV" >&2; exit 4; }
export ZEILEN_CSV  # marge_pdf.py und pruefe_listen_v3.py lesen dieselbe Datei

marge() {
  # Margenliste mit Kundensicht -> _out/desktop/3 FÜR EDDY (intern)/ unter dem bisherigen Namen, danach Pruefung
  mkdir -p "$D/$EDDY"
  cd $P
  echo "Kennzahlen-Datei: $ZEILEN_CSV"
  $V marge_pdf.py | head -1 | cut -c1-140
  cp "Elements Labs Margenübersicht.pdf" "$D/$EDDY/MARGEN – Einkauf, Verkauf, Marge je Produkt.pdf"
}

build() {
  local t0=$SECONDS
  mkdir -p "$D/$TING" "$D/$RENE" "$D/$EDDY" "$O/tmp"
  cd $P
  # 1) Erzeuger (Positionierung ohne Desktop-Ausgabe, Sortiment, Preisfamilie v3 -> preisempfehlung.json)
  $V -c "import positionierung as pz; from pathlib import Path; pz.OUT = Path('$O/tmp/positionierung.xlsx'); pz.main()" | tail -1
  $V sortiment_ergaenzung.py | head -1
  $V empfehlung.py | tail -1
  # 2) v3 in die Shop-Daten (Einzelpreise + Packs), Build, Tests
  cd $M
  $SHOPPY tools/apply_pricing.py | tail -1
  $SHOPPY build.py | tail -1
  $SHOPPY -m unittest discover -s tests -p "test_*.py" 2>&1 | grep -E "^(Ran|OK|FAILED|FAIL:|ERROR:)"
  [[ ${pipestatus[1]} -eq 0 ]] || { echo "Tests rot - Abbruch" >&2; exit 1; }
  # 3) PDFs und Tabellen
  cd $P
  $V make_pricelist.py --xlsx "$D/$EDDY/Preisliste für Kunden (Tabelle).xlsx" | tail -1 | cut -c1-140
  echo "Kennzahlen-Datei (Margenliste Kundensicht): $ZEILEN_CSV"
  for s in top20_pdf.py ting_pdf.py marge_pdf.py render_supplier.py; do $V $s | tail -1 | cut -c1-140; done
  # 4) Ablage mit den heutigen Desktop-Namen
  cp $M/data/preisliste.pdf "$D/$EDDY/Preisliste für Kunden (auch im Bot).pdf"
  cp "Elements Labs Ting-Preischeck.pdf" "$D/$EDDY/Ting-Preischeck, Verhandlung, Händlermarge.pdf"
  cp "Elements Labs Top-20 Bestseller.pdf" "$D/$EDDY/Top-20 Bestseller mit Preisen.pdf"
  cp "Elements Labs Margenübersicht.pdf" "$D/$EDDY/MARGEN – Einkauf, Verkauf, Marge je Produkt.pdf"
  cp "Elements Labs Einkaufsübersicht Vials und Doppelkammer.pdf" "$D/$TING/Elements Labs Preisliste (Bestpreis, Top-Produkte markiert).pdf"
  print -r -- "Nur diese Datei geht an Ting - und nur nach Freigabe durch Eddy. Enthält keine Verkaufspreise, keine Marge, keine andere Lieferantin.
TOP = Schwerpunktprodukt (Top-20 der meistverkauften Wirkstoffe)." > "$D/$TING/LIES MICH.txt"
  print -r -- "Nur für Eddy, nichts davon weitergeben (enthält Einkaufspreise und Margen). Preisstand: Preisfamilie v3, Mindestmarge 60 % (25.10.2026).
MARGEN: Einkauf, Verkauf und Marge je Produkt. Ting-Preischeck und Top-20: Einkauf, Verhandlung, Markt.
Ausnahme: Preisliste für Kunden (PDF und Tabelle) - die PDF bekommen Kunden auch über den Bot (/preisliste)." > "$D/$EDDY/LIES MICH.txt"
  # René: Übergabe-PDF ohne Preise unverändert übernehmen; das Design-Paket (ZIP) wird hier NICHT neu gebaut.
  cp "Elements Labs Shop - Uebergabe fuer Rene.pdf" "$D/$RENE/ZUERST LESEN - Übergabe für René.pdf"
  echo "Neuaufbau fertig in $((SECONDS - t0)) s"
  pruefen
  echo "Gesamt $((SECONDS - t0)) s"
}

pruefen() {
  cd $P
  $V pruefe_listen_v3.py
}

cutover() {
  if [[ "$1" != "--freigabe-eddy" ]]; then
    echo "cutover nur mit Eddys Freigabe: pipeline_v3.sh cutover --freigabe-eddy" >&2; exit 2
  fi
  [[ -f "$O/pruefung_v3.json" ]] && grep -q '"alles_ok": true' "$O/pruefung_v3.json" || { echo "Pruefung nicht gruen - kein Cutover" >&2; exit 3; }
  local A=$P/archiv-desktop/cutover_$(date +%Y%m%d_%H%M%S)
  mkdir -p "$A"
  # a) veraltete bzw. ersetzte Desktop-Dateien ins Archiv (nicht loeschen, damit Rueckweg bleibt)
  for f in "$DESK/$EDDY/Preisliste für Kunden (auch im Bot).pdf" "$DESK/$EDDY/Ting-Preischeck, Verhandlung, Händlermarge.pdf" \
           "$DESK/$EDDY/Top-20 Bestseller mit Preisen.pdf" "$DESK/$EDDY/MARGEN – Einkauf, Verkauf, Marge je Produkt.pdf" "$DESK/$EDDY/LIES MICH.txt" \
           "$DESK/$TING/Elements Labs Preisliste (Bestpreis, Top-Produkte markiert).pdf" "$DESK/$TING/LIES MICH.txt"; do
    [[ -e "$f" ]] && { mkdir -p "$A/${${f:h}:t}"; mv "$f" "$A/${${f:h}:t}/"; echo "archiviert: ${f#$DESK/}"; }
  done
  # b) neue Dateien kopieren (René-Ordner: nur LIES MICH/Übergabe bleiben, ZIP separat neu bauen)
  for dir in "$TING" "$EDDY"; do
    mkdir -p "$DESK/$dir"
    for f in "$D/$dir"/*; do cp "$f" "$DESK/$dir/"; echo "neu: $dir/${f:t}"; done
  done
  echo "Archiv: $A"
  echo "Nicht Teil des Cutovers: miniapp/data/preisliste.pdf + Shop-Daten ins Live-Repo (eigener Deploy), rene_sync.py push-data, Design-Paket-ZIP für René."
}

case "${1:-build}" in
  build) build ;;
  pruefen) pruefen ;;
  marge) marge; pruefen ;;
  cutover) cutover "$2" ;;
  *) echo "Aufruf: pipeline_v3.sh [pruefen | marge | cutover --freigabe-eddy]" >&2; exit 2 ;;
esac
