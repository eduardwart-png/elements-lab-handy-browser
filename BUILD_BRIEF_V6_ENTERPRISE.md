# ELEMENTS LABS — ENTERPRISE FLAGSHIP V6 BUILD BRIEF
Arbeitsverzeichnis: C:\Users\eduar\elements-lab-flagship (Git-Repo, GitHub Pages: eduardwart-png/elements-lab-handy-browser)

Du bist Claude Code, arbeitest autonom, ohne Rückfragen an einen Nutzer (es ist niemand da, der antwortet). Wenn du an einen echten Blocker stößt (fehlende externe Rechtsdaten, fehlendes Labor, fehlende reale Firmendaten), trage den passenden Status-Code ein (siehe unten) statt zu erfinden. NIE Platzhalter-Rechtsdaten, NIE erfundene DOI/PMID, NIE Fake-COAs.

## HARTE GRUNDREGEL
Diese Website wird NEU als Enterprise-Flagship aufgebaut. Der bisherige visuelle Stand ist KEINE Designreferenz mehr — nur technische Datenquelle für brauchbare Funktionen (Routing, Cart, Search, Filter, Batch-Lookup-Logik).

**Verbindliche Assets, NICHT neu erfinden — bereits vorhanden, LOCKED:**
- Logo: `assets/logos/el-primary-light.svg` / `el-primary-dark.svg` / `el-icon-*.svg` / `el-secondary-*.svg` / `el-badge-*.svg` (geometrisches EL-Monogramm, Graphit `#2A2F36` + Petrol `#0D5B6B`)
- Master Vial/Packaging: `assets/base-photos-final/vial-master.png`, `assets/base-photos-final/box-master.jpg`, `box-master2.jpg`

Falls diese Dateien beim Start fehlen: STOP, schreibe `MASTER_ASSET_MISSING` in den Report — NICHT selbst ein neues Logo/Vial generieren. (Stand jetzt: beide vorhanden, verifiziert.)

## FARBEN (bereits korrekt in styles.css, beibehalten)
Graphite `#2A2F36` · Near Black `#0D1115` · Off White `#F7F7F8` (dominierend) · Deep Petrol `#0D5B6B` (nur Akzente, KEINE großen petrolfarbenen Flächen)

## TYPOGRAFIE (bereits korrekt, beibehalten)
Space Grotesk primär. Mono-Font nur für Batch/SKU/Report-ID/technische Metadaten.

---

## PHASE 1 — SSOT & PRODUKT-/PREISMATRIX (P0, zuerst)

Ersetze die alte PRODUCTS-Liste in `build_elements_site_v2.py` (und app.js Datenquelle) durch die neue CORE RANGE:

| id | name | concentration | price_de_gross | category |
|---|---|---|---|---|
| bpc-157 | BPC-157 | 10 mg | 39,90 € | Tissue Research |
| tb-500 | TB-500 | 10 mg | 69,90 € | Tissue Research |
| ipamorelin | Ipamorelin | 10 mg | 39,90 € | Endocrine Research |
| kpv | KPV | 10 mg | 54,90 € | Tripeptide Research |
| selank | Selank | 10 mg | 34,90 € | Neuropeptide Research |
| semax | Semax | 10 mg | 34,90 € | Neuropeptide Research |
| mots-c-10 | MOTS-C | 10 mg | 39,90 € | Mitochondrial Research |
| mots-c-20 | MOTS-C | 20 mg | 59,90 € | Mitochondrial Research |
| mots-c-40 | MOTS-C | 40 mg | 89,90 € | Mitochondrial Research |
| cjc-1295-no-dac | CJC-1295 No DAC | 10 mg | 54,90 € | Endocrine Research |
| 5-amino-1mq | 5-Amino-1MQ | 10 mg | 59,90 € | Metabolic Research |
| bpc-157-tb-500 | BPC-157 + TB-500 | 10 mg + 10 mg | 74,90 € | Research Bundle |
| epithalon | Epithalon | 10 mg | 29,90 € | Longevity Research |

Diese Preise sind **PLANNING PRICES** — trage in jedes SKU-Datenobjekt `price_status: "PLANNING_PRICE"` ein, bis Landed Cost berechnet ist (siehe Cost-YAML unten). Zeige auf der Website den Preis normal an (er ist ja real geplant), aber im internen Datensatz (JSON, nicht auf der Seite sichtbar) den Status führen.

EXTENDED RANGE (technisch vorbereiten, NICHT prominent auf Homepage, eigene Kategorie/Filter): GHK-Cu 50mg/100mg, NAD+ 100mg/500mg/1000mg, Epithalon 50mg, BPC-157 5mg, TB-500 5mg — nur falls wirtschaftlich sinnvoll und Lieferant sie real anbietet. Keine erfundenen Konzentrationen.

LEGAL HOLD (NICHT öffentlich listen): Semaglutid/Tirzepatid/Retatrutid Liefervarianten 10/15/20/30/40mg intern als Datensatz mit `release_status: "LEGAL_HOLD"` anlegen, aber aus Produktgrid/Sitemap/Navigation ausschließen (keine URL, kein Link, kein SEO-Indexierung). Falls Retatrutid aus dem Vorlauf schon öffentlich gelistet ist (siehe research_retatrutide.json falls vorhanden) → aus öffentlicher Liste entfernen, Status auf LEGAL_HOLD setzen, bis schriftliche Rechtsprüfung vorliegt.

### Landed Cost Modell
Für jede öffentlich gelistete SKU eine YAML/JSON-Struktur mit den Feldern aus dem Master-Prompt (`supplier_cost, international_shipping, customs, import_cost, lab_cost, coa_cost, packaging, label, fulfillment, payment_fee, vat, returns_reserve, other_cost, landed_cost, gross_margin, net_margin, recommended_price, approved_price`). Da echte Lieferantenpreise NICHT in diesem Repo vorliegen: alle Kostenfelder auf `null` setzen mit `"status": "AWAITING_REAL_SUPPLIER_DATA"`, `approved_price: null`, `price_status: "PLANNING_PRICE"`. NICHTS erfinden. Datei: `data/landed_cost_matrix.json`.

---

## PHASE 2 — DATENMODELLE (Gerüst, real befüllbar, keine Fantasiedaten)

Lege folgende Dateien unter `data/` an, jeweils als Array/Objekt pro SKU bzw. global, EXAKT nach den YAML-Feldern aus dem Master-Prompt:
- `data/compliance_reach_clp.json` (pro SKU, alle Felder `null`/`"NOT_REVIEWED"`)
- `data/coa_schema.json` (Template + je SKU ein leerer Eintrag, `result_status: "NOT_TESTED"`, `published: false`)
- `data/lab_registry.json` (leer/Platzhalter-Schema, `iso_17025: null`)
- `data/supplier_registry.json` (Platzhalter-Schema `approved: false`)
- `data/country_matrix.json` (DE, PL, + generische EU-Platzhalterzeile, `sales_allowed: null`, `legal_review: "NOT_STARTED"`)
- `data/release_status.json` — Gesamtprojekt-Status:
```json
{"DESIGN_READY":null,"DATA_READY":null,"LEGAL_READY":false,"COMPLIANCE_READY":false,"LAB_READY":false,"CERTIFICATES_READY":false,"PAYMENT_READY":false,"SHIPPING_READY":false,"TECH_READY":null,"LIVE_READY":false}
```
- `data/legal_entity_status.json`: `{"status":"PRE_LAUNCH","note":"Keine realen polnischen Firmendaten vorhanden — nicht erfinden. Warten auf: Firmenname, Rechtsform, Adresse, KRS/Registerinfo, VAT-ID, EU-VAT, EORI."}`
- `data/tax_review_status.json`: `{"status":"CROSS_BORDER_TAX_REVIEW_REQUIRED","note":"Ort der Geschäftsleitung/DE-PL Anknüpfung ungeprüft — Hermes simuliert keine Steuerrechtsfreigabe."}`

---

## PHASE 3 — SCIENTIFIC RESEARCH LIBRARY (echte Quellen, Web-Recherche PFLICHT)

Für jedes der 13 CORE-RANGE-Produkte (bei mots-c die drei Konzentrationen zählen als 1 Compound) ein Research Profile nach dem YAML-Schema (compound, classification, molecular_type, cas, formula, molecular_weight, sequence, research_focus, mechanism_summary, research_context, evidence_summary, limitations, evidence_level, references, last_reviewed, reviewed_by).

Nutze WebSearch/WebFetch für PubMed/NIH/peer-reviewed Journals/DOI. Jede Referenz braucht einen echten Link (PMID oder DOI), den du tatsächlich abgerufen/verifiziert hast. Wenn du für ein Produkt in vertretbarer Zeit keine belastbare Quelle findest: `evidence_level: "insufficient_public_data"`, `references: []` — NICHT erfinden. Reihenfolge auf der Produktseite: Classification → Molecular Information → Research Focus → Mechanistic Context → Evidence Summary → Current Research Topics → Limitations → References, mit klarer Kennzeichnung präklinisch/in vitro/Tiermodell/klinisch.

Datei: `data/research_profiles.json`.

Falls bereits eine `research_retatrutide.json` im Repo existiert: NICHT für die öffentliche Core-Range verwenden (Retatrutid ist LEGAL_HOLD), aber als internen Datensatz mit LEGAL_HOLD-Flag übernehmen statt zu verwerfen.

---

## PHASE 4 — CERTIFICATE / BATCH / QR SYSTEM

- Jede öffentlich gelistete SKU bekommt eine Batch-ID nach Schema `EL-<CODE><CONC>-<JAHR><LFDNR>` (Format aus altem Code übernehmen).
- QR pro Batch (bereits vorhandene qrcode-Pipeline in build_elements_site_v2.py wiederverwenden/anpassen) → Ziel `/batch/<batch-id>` (Hash-Route wie bisher `#batch=<id>`).
- Batch-Verify-Seite: Ergebnis ist IMMER einer von: VERIFIED / NOT FOUND / NOT RELEASED. Da real keine Charge freigegeben ist (kein Labor, kein COA), müssen ALLE Batches aktuell `NOT RELEASED` zurückgeben — NICHT als „VERIFIED" ausgeben, auch wenn die SKU existiert. Baue das SKU-Release-Gate (LEGAL_CHECK, SUPPLIER_VERIFIED, IMPORT_OK, SDS_CLP_OK, SAMPLE_RECEIVED, LAB_TESTED, LAB_PASS, COA_UPLOADED, PRODUCT_DATA_VERIFIED, PRICE_APPROVED, WEBSITE_RELEASED) real in die Datenstruktur ein, alle Flags aktuell `false` außer ggf. PRODUCT_DATA_VERIFIED.
- Certificate-Page zeigt konsequent: "Kein Batch aktuell freigegeben — Zertifikate erscheinen automatisch bei Release" statt Fake-Dokumenten. Keine Dummy-Stempel.

---

## PHASE 5 — WEBSITE-ARCHITEKTUR & SEITEN

Struktur: HOME, PRODUCTS, PRODUCT DETAIL, RESEARCH LIBRARY, QUALITY, CERTIFICATES, BATCH VERIFY, ABOUT, FAQ, CONTACT, CART, CHECKOUT, LEGAL.

Homepage NUR: 1. Hero 2. Featured Products 3. Quality & Certificate Proof 4. Research Library 5. Batch Verification 6. Footer (optional kurze About-Ebene). Keine Füllboxen, keine 20 Sektionen.

Hero: Basis = Master-Vial/Packaging-Assets (`hero-studio-scene.png` neu komponieren falls nötig, aber Vial-Form/Label MUSS vial-master.png entsprechen). Links Markentext + max 2 CTAs, rechts 2-3 Vials + Packaging auf echter Oberfläche mit Bodenschatten. **Hard Gate: keine schwebenden Objekte (FLOATING_VIALS=0).**

Product Grid: großes Bild, reduzierter Text (Name, Konzentration, Preis, kleiner CTA), viel Weißraum, kein Billigshop-Rahmen.

Product Detail: editoriales Layout (kein Card-Grid) mit Research Profile, Product Specification, Batch Analysis (aktuell "kein Batch released"), Certificates, References.

Quality-Seite: realer Prozess (Supplier Qualification → Incoming Quarantine → Sampling → Independent Analysis → QA Review → Batch Release → Traceability → Certificate Publication) — als Prozessbeschreibung, NICHT als Behauptung dass das bereits für jede Charge geschehen ist.

Legal-Seite: Polen-Struktur als Zielbild beschreiben, aber `LEGAL_ENTITY_STATUS=PRE_LAUNCH` sichtbar, keine erfundenen Registerdaten/Adressen. Impressum-Platzhalter deutlich als "vor Live-Schaltung zu ergänzen" kennzeichnen (kein Fake-Impressum als wäre es echt).

## VERBOTENE INHALTE (hart, überall prüfen)
Keine Dosierungspläne, kein Reconstitution Calculator, keine Injizieranleitungen, keine Spritzenbilder, keine Human-Use Instructions, keine Heilversprechen, keine medizinischen Empfehlungen, keine Bodybuilding-/Abnehm-Versprechen, keine Dosierungstabellen, kein BAC-Water-Bundle im Human-Use-Kontext.

---

## PHASE 6 — QA (Pflicht vor Abschluss)

1. Node/Playwright oder vorhandene `qa/cdp_production_qa.js`-Pipeline erweitern und laufen lassen (existierendes Muster in `qa/` verwenden).
2. Screenshots: 390px, 430px, 768px, 1440px, 1920px — Home, Product Grid, Product Detail, Research Library, Quality, Certificates, Batch Verify, Footer.
3. Prüfen: 0 console errors, 0 broken links, FLOATING_VIALS=0, keine Fake-Zertifikate, keine LEGAL_HOLD-SKU im öffentlichen Grid/Sitemap.
4. Adversarial Self-Check: Würde ein Laborverantwortlicher das als echte Research-Marke oder als KI-Demo erkennen? Blocker/Critical/Major zählen, alle auf 0 vor Abschluss (oder explizit im Report auflisten, wenn Zeit/Budget nicht reicht).

---

## GIT / DEPLOY
Arbeite auf einem neuen Branch `flagship-v6-enterprise` (nicht direkt auf master committen, bis QA grün). Committe in sinnvollen Zwischenschritten mit klaren Messages. Push den Branch. KEIN Merge nach master, KEIN Force-Push, KEINE Veröffentlichung/Live-Schaltung auf eine echte Kundendomain ohne Rückfrage — GitHub Pages Preview-Branch ist ok.

## ABSCHLUSSBERICHT
Schreibe am Ende `V6_BUILD_REPORT.md` im Repo-Root nach dem FINAL-REPORT-Schema aus dem Master-Prompt (Brand/Products/Pricing/Poland-Legal/Compliance/Laboratory/Certificates/Research/Website/QA/Evidence), mit ehrlichen Status-Werten (PRE_LAUNCH, TRACKED, NOT_TESTED etc. wo zutreffend) statt beschönigt. Gib am Ende klar an, was noch AUSSTEHT und einen echten externen Input von Eddy braucht (Fachanwalt Polen/EU, echtes Labor, echte Lieferantenpreise, Firmendaten) — das sind KEINE Baustellen die du selbst lösen kannst.
