# ELEMENTS LABS V7 — KONKURRENZ-ANALYSE-UPGRADE
Branch: flagship-v6-enterprise (weiterarbeiten, NICHT neuer Branch). Repo: C:\Users\eduar\elements-lab-flagship

## KONTEXT
Konkurrenzseite `glowingpeptides.com` (Betreiber: ISAD E-COMMERCE SPÓŁKA Z O.O., Poznań/Polen) wurde analysiert. Sie ist in einigen strukturellen Punkten stärker als unser aktueller V6-Stand. Diese Punkte werden jetzt gezielt übernommen — OHNE unser bereits gelocktes Brand-System (Logo, Farben, Master-Vial, Preise, Legal-Hold-Struktur) zu verändern. Es geht um FUNKTIONALE/STRUKTURELLE Verbesserungen, nicht um ein Redesign.

## WAS DIE KONKURRENZ BESSER MACHT (konkret, mit Beleg)

1. **18+ Age-Gate beim Seiteneintritt.** Vor jedem Seitenaufruf: Modal "Willkommen" mit (a) Dropdown "Sind Sie 18 Jahre oder älter? Ja/Nein", (b) Sprachwahl, (c) Pflicht-Checkbox "Ich bestätige, dass die auf dieser Website angezeigten Produkte ausschließlich für Forschungszwecke bestimmt sind und nicht für den menschlichen Verzehr, medizinische Anwendungen oder diagnostische/therapeutische Zwecke verwendet werden dürfen", (d) Button "Website betreten" — erst danach ist die Seite sichtbar (Rest bleibt verdeckt/geblurred dahinter). Bei "Nein" → Weiterleitung weg von der Seite (z.B. auf eine neutrale Seite, kein Content-Zugriff).

2. **Produktseiten-Tab-Struktur.** Statt einem langen Fließtext: Tabs "Beschreibung", "Labortest / COA (Certificate of Analysis)", "Anwendungsbereiche", "Lagerung", "Haftungsausschluss", "Versand & Rückgabe", "FAQ" (produktspezifische FAQ, z.B. Zollgebühren EU, Kundenservice-Kontakt, Produktsicherheit, Verbraucherverantwortung).

3. **Trust-Badges direkt am Produkt/Global:** "Kostenloser Versand ab X€", "Versand aus Europa", "24/7 Kundendienst" als Icon-Reihe — bei uns bereits im Ansatz vorhanden (trust-row), aber am Produkt selbst (Detail-Seite) fehlt das noch.

4. **Deutlicher, wiederkehrender Research-Only-Disclaimer** nicht nur im Footer, sondern als eigener CTA-naher Hinweis direkt unter dem "In den Warenkorb"-Button auf jeder Produktseite ("⚠️ Nur zu Forschungszwecken").

5. **Wissensbereich / Info-Hub** als eigene Content-Sektion: "Was sind Peptide?", "Verwendungszweck" (klare Abgrenzung zur Anwendung am Menschen), "Qualität & Analytik" (COA/HPLC/SDS erklärt), "Gesetzeslage & Verantwortung", "Sicherer Umgang & Lagerung", "FAQ". Das baut Vertrauen auf und erklärt COA-Konzept, bevor der Nutzer den Batch-Verify nutzt.

6. **Variantenauswahl bei mehreren Konzentrationen** (Dropdown "5mg/10mg/20mg" direkt auf der Produktkarte/Karteikarte, nicht erst im Detail) — bei uns nur relevant für MOTS-C (10/20/40mg) und Extended Range; NICHT die Kernpreise/Konzentrationen der anderen SKUs ändern (die sind gelockt auf 10mg Standard).

## WAS NICHT ÜBERNOMMEN WIRD (bewusst, Unterschiede bleiben)

- KEINE "Kaufe 3, zahle 2"-Rabattaktion — nicht Teil des Premium-Markenbilds (§ Zielbild: kein Billigshop).
- KEIN Sortiment-Wildwuchs (47 Produkte) — unsere CORE/EXTENDED/LEGAL_HOLD-Struktur bleibt exakt wie in BUILD_BRIEF_V6_ENTERPRISE.md festgelegt.
- KEINE dunklen/schwarzen Produktfoto-Hintergründe als Standard — unser Off-White-dominiertes Brand-System bleibt LOCKED, das Master-Vial-Bild bleibt die visuelle Quelle.
- KEINE eigenen Polen-Firmendaten erfinden — unsere Legal-Seite bleibt ehrlich PRE_LAUNCH, bis echte Daten vorliegen (Konkurrenz hat eine echte eingetragene Firma, wir (noch) nicht — das wird NICHT vorgetäuscht).

## UMSETZUNG (konkret, Schritt für Schritt)

### 1. Age-Gate (P0, höchste Priorität — Eddy hat das explizit gefordert)
- Neues Modal-Overlay, das beim ersten Laden JEDER Seite (index.html + alle Hash-Routen) erscheint, bevor der Content sichtbar ist (Hintergrund geblurred/abgedunkelt).
- State in `localStorage` (`elementsAgeGateConfirmed`), damit es nicht bei jeder internen Navigation erneut erscheint — nur bei neuem Seitenbesuch/Session.
- Inhalt (eigene Formulierung, keine wörtliche Kopie der Konkurrenztexte):
  - Titel: "Bevor Sie fortfahren"
  - Frage: "Sind Sie 18 Jahre oder älter?" → Ja/Nein-Auswahl (Button-Paar reicht, kein Dropdown nötig)
  - Pflicht-Checkbox: "Ich bestätige, dass die auf dieser Website angebotenen Produkte ausschließlich für wissenschaftliche Forschungszwecke bestimmt sind und weder für den menschlichen oder tierischen Verzehr noch für medizinische, diagnostische oder therapeutische Zwecke vorgesehen sind."
  - Button "Bestätigen und fortfahren" ist erst aktiv, wenn Ja + Checkbox gesetzt sind.
  - Bei "Nein" oder Nichtbestätigung: Hinweistext "Diese Website ist nur für volljährige Nutzer im Forschungskontext zugänglich." + Link weg (z.B. auf eine externe neutrale Seite oder einfach Seiteninhalt gesperrt lassen).
- Technisch: reines JS/CSS im bestehenden `app.js`/`styles.css`, kein neues Framework.

### 2. Produktseiten-Tabs
- `productDetail()`-Funktion in app.js erweitern um Tab-Navigation mit denselben Kategorien (Beschreibung, Labortest/COA, Anwendungsbereiche, Lagerung, Haftungsausschluss, Versand & Rückgabe, FAQ).
- Inhalte NEU und EIGENSTÄNDIG formulieren (keine Textübernahme von glowingpeptides.com — Urheberrecht/Wettbewerbsrecht), fachlich aber gleichwertig:
  - Beschreibung: aus vorhandenem Research Profile ableiten.
  - Labortest/COA: Verweis auf unser echtes Certificate-System (aktuell NOT_RELEASED, ehrlich kommunizieren, nicht wie Konkurrenz pauschale COA-Behauptung ohne Beleg übernehmen).
  - Anwendungsbereiche: aus Research Profile → research_context, rein wissenschaftlich, keine Human-Use-Sprache.
  - Lagerung: generische, fachlich korrekte Peptid-Lagerhinweise (kühl, trocken, lichtgeschützt, laut Herstellerangabe — ohne Rekonstitutions-/Dosierungsanleitung).
  - Haftungsausschluss: Research-Use-Only-Disclaimer.
  - Versand & Rückgabe: Verweis auf Legal-Seite (aktuell PRE_LAUNCH-Status ehrlich zeigen, keine erfundenen Versandzeiten vortäuschen, die wir nicht einhalten können).
  - FAQ: 3-4 produktbezogene Fragen (Qualitätssicherung, Verantwortung des Käufers, Kontakt).

### 3. Trust-Badges auf Produktdetailseite
- Kleine Icon-Reihe (wiederverwendbar aus Home-trust-row) direkt unter dem Preis/CTA-Bereich einbauen.

### 4. Research-Only-Reminder am CTA
- Kleiner Text mit Warn-Icon direkt unter "Add to Cart"-Button: "Nur für Forschungszwecke — keine Anwendung am Menschen."

### 5. Wissensbereich / Research Library ergänzen
- Neue Seite/Sektion "Info" oder Erweiterung der bestehenden Research-Library-Seite um 4-5 Unterseiten/Anker: Was sind Peptide?, Verwendungszweck & Abgrenzung, Qualität & Analytik (COA/HPLC/SDS erklärt), Gesetzeslage & Verantwortung (mit klarem Verweis auf unseren PRE_LAUNCH/LEGAL_HOLD-Status statt Rechtsberatung vorzutäuschen), Sicherer Umgang & Lagerung. Eigene, sachliche Texte — keine Kopie.
- In Hauptnavigation verlinken.

### 6. Variantenauswahl MOTS-C
- Auf der Produktkarte (Grid) und Detailseite für MOTS-C ein Dropdown/Button-Gruppe 10mg/20mg/40mg mit Preisumschaltung (39,90 € / 59,90 € / 89,90 €) statt drei separaten Karten im Grid. Das reduziert Grid-Redundanz nach Konkurrenz-Vorbild. Die anderen 12 SKUs bleiben wie gelockt (kein künstliches Aufblähen mit Fantasievarianten).

## HARTE GRENZEN (nochmal explizit)
- Keine erfundenen Firmendaten, keine erfundenen Lieferzeiten, keine erfundenen COA-Ergebnisse — auch nicht im neuen Content.
- Keine Dosierungs-/Rekonstitutionsanleitungen in "Lagerung" oder "Anwendungsbereiche".
- Age-Gate MUSS technisch funktionieren (nicht nur Kosmetik) — Content erst nach Bestätigung sichtbar, in _standalone.html genauso wie in index.html.
- Bestehende Preise/Batch-IDs/Legal-Hold-Ausschlüsse aus V6 NICHT verändern.

## QA VOR ABSCHLUSS
1. Age-Gate: neuer Inkognito-Load zeigt Gate, Bestätigung schaltet frei, State bleibt bei interner Navigation, Reload einer neuen Session zeigt Gate erneut (localStorage leeren zum Test).
2. Alle 13 Produktdetailseiten: Tabs vorhanden und befüllt, keine leeren Tabs.
3. MOTS-C Variantenumschaltung funktioniert, Preis/Batch/Bild wechseln korrekt mit.
4. Kein LEGAL_HOLD-Produkt in Navigation/Grid/Sitemap sichtbar (Regressionscheck aus V6 wiederholen).
5. Screenshot Home + 1 Produktdetail auf 390px und 1440px.
6. `python build_elements_site.py` läuft fehlerfrei, `qa/standalone_static_check.py` PASS.

## ABSCHLUSS
Commit(s) mit klaren Messages auf Branch `flagship-v6-enterprise`, Branch pushen. Kurzen Abschnitt an `V6_BUILD_REPORT.md` anhängen ("V7 Competitor-Upgrade Addendum") mit Status jedes Punkts oben (COMPLETE/PARTIAL/BLOCKED + Grund). Kein Merge nach master.
