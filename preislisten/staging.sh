#!/bin/zsh
# Staging fuer den Elements-Labs-Shop (Lehre 24.10.2026: build.py schreibt DIREKT in den Live-Ordner public/ und
# der Server laedt den Katalog nur beim Start). Deshalb: nie im Live-Ordner bauen. Alles hier, Live nur per "promote".
#
#   staging.sh refresh        Live-Baum nach Staging kopieren (ohne runtime/, venv, Caches)
#   staging.sh build          build.py im Staging
#   staging.sh test           Python- und Node-Tests im Staging (Ergebnis in .tests_ok bei vollem Erfolg)
#   staging.sh serve          Staging-Server auf Port 8899 (Browser-QA), stop beendet ihn
#   staging.sh status         Unterschied Staging gegen Live (Dateizahl), Teststand, Serverstand
#   staging.sh promote --freigabe-eddy [--dry-run]
#                             Staging nach Live kopieren, Dienst neu starten, Live gegenpruefen. Nur nach Eddys Ja.
set -e
LIVE=~/Projekte-Mac/elements-lab-telegram
STG=~/Projekte-Mac/elements-lab-telegram-staging
PY=$LIVE/miniapp/.venv-build/bin/python
RS=(rsync -a --exclude 'miniapp/runtime/' --exclude '__pycache__/' --exclude '.venv-build/' --exclude '.DS_Store' --exclude 'node_modules/')

STGPATHS=(preislisten/pipeline_alles.sh preislisten/make_design_package.py preislisten/bild_composite.py miniapp/tests/browser_acceptance.py)
to_stg() { for f in $STGPATHS; do [[ -f $STG/$f ]] && sed -i '' "s#Projekte-Mac/elements-lab-telegram\\(-staging\\)\\{0,1\\}#Projekte-Mac/elements-lab-telegram-staging#g" $STG/$f; done; }
to_live() { for f in $STGPATHS; do [[ -f $STG/$f ]] && sed -i '' "s#Projekte-Mac/elements-lab-telegram-staging#Projekte-Mac/elements-lab-telegram#g" $STG/$f; done; }

case "$1" in
  paths)
    to_stg; echo "Pfade im Staging auf Staging gesetzt";;
  refresh)
    mkdir -p $STG
    $RS --delete $LIVE/ $STG/
    mkdir -p $STG/miniapp/runtime
    to_stg   # absolute Live-Pfade in den wenigen Hilfsskripten auf Staging umbiegen (nur in der Kopie)
    rm -f $STG/miniapp/.tests_ok
    echo "staging aktuell: $STG";;
  build)
    cd $STG/miniapp && $PY build.py | tail -1;;
  test)
    cd $STG/miniapp
    out=$($PY -m unittest discover -s tests -p "test_*.py" 2>&1 | grep -E "^(Ran|OK|FAILED|FAIL:|ERROR:)") || true
    echo $out
    bad=0
    for f in tests/test_*.cjs; do node $f >/dev/null 2>&1 && echo "OK $f" || { echo "FAIL $f"; bad=1; }; done
    if print -r -- "$out" | tr "\n" " " | grep -q "Ran [0-9]* tests.* OK" && [[ $bad == 0 ]]; then date +%s > .tests_ok; echo "TESTS GRUEN"; else rm -f .tests_ok; echo "TESTS ROT"; exit 1; fi;;
  serve)
    cd $STG/miniapp
    $PY server.py --port 8899 --mode preview >/tmp/staging-server.log 2>&1 &
    echo $! > $STG/miniapp/runtime/staging.pid
    sleep 3; curl -s localhost:8899/health; echo;;
  stop)
    [[ -f $STG/miniapp/runtime/staging.pid ]] && kill $(cat $STG/miniapp/runtime/staging.pid) 2>/dev/null && rm -f $STG/miniapp/runtime/staging.pid; echo gestoppt;;
  status)
    echo "Dateien, die sich unterscheiden (Staging gegen Live, ohne runtime/Caches):"
    to_live
    rsync -rcn --delete --exclude 'miniapp/runtime/' --exclude '__pycache__/' --exclude '.venv-build/' --exclude '.DS_Store' --out-format='%n' $STG/ $LIVE/ | grep -v '/$' | head -60
    to_stg
    [[ -f $STG/miniapp/.tests_ok ]] && echo "Tests im Staging gruen seit $(date -r $(cat $STG/miniapp/.tests_ok) +%H:%M)" || echo "Tests im Staging: nicht gruen/nicht gelaufen"
    curl -s localhost:8899/health 2>/dev/null && echo " (Staging-Server)" || true;;
  promote)
    [[ "$2" == "--freigabe-eddy" ]] || { echo "ABBRUCH: ohne Freigabe von Eddy kein Live-Gang"; exit 2; }
    [[ -f $STG/miniapp/.tests_ok ]] || { echo "ABBRUCH: Tests im Staging nicht gruen"; exit 3; }
    to_live
    if [[ "$3" == "--dry-run" ]]; then
      echo "DRY-RUN: wuerde kopieren:"; to_live; rsync -rcn --delete --exclude 'miniapp/runtime/' --exclude '__pycache__/' --exclude '.venv-build/' --exclude '.DS_Store' --out-format='%n' $STG/ $LIVE/ | grep -v '/$' | head -80; to_stg; exit 0
    fi
    stamp=$(date +%Y%m%d-%H%M%S)
    mkdir -p ~/Projekte-Mac/_DATA/ELEMENTS_STRATEGIE_20261024/live-sicherung-$stamp
    rsync -a --exclude 'runtime/' --exclude '__pycache__/' --exclude '.venv-build/' --exclude 'asset-cache/' --exclude 'asset-cache-current/' --exclude 'evidence/' $LIVE/miniapp/ ~/Projekte-Mac/_DATA/ELEMENTS_STRATEGIE_20261024/live-sicherung-$stamp/miniapp/
    rsync -a $LIVE/preislisten/ ~/Projekte-Mac/_DATA/ELEMENTS_STRATEGIE_20261024/live-sicherung-$stamp/preislisten/
    $RS --exclude '.tests_ok' $STG/ $LIVE/
    to_stg
    python3 ~/.hermes/cache/scratch/live_restart_probe.py 2>&1 | tail -12
    echo "LIVE aktualisiert. Sicherung: _DATA/ELEMENTS_STRATEGIE_20261024/live-sicherung-$stamp";;
  *)
    sed -n 2,12p $0;;
esac
