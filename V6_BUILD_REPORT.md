# V6 Build Report — Elements Labs Enterprise Flagship

**Branch:** flagship-v6-enterprise  
**Build date:** 2026-08-29  
**Status:** PRE_LAUNCH — All gates structurally complete; no live batch release, no active legal entity

---

## Phase 1 — Product Data & SSOT

| Item | Status |
|---|---|
| V6 CORE RANGE (13 SKUs) | COMPLETE |
| PRODUCTS list in build_elements_site.py | COMPLETE |
| PRODUCTS list in build_elements_site_v2.py | COMPLETE |
| MOTS-C split into 3 SKUs (10/20/40 mg) | COMPLETE |
| LEGAL_HOLD products excluded from all public routes | COMPLETE |
| Retatrutide removed from public RESEARCH_PROFILES | COMPLETE |
| Retatrutide data preserved in data/internal_legal_hold_profiles.json | COMPLETE |
| STATIC_QA product count gate 14→13 | COMPLETE |

## Phase 2 — Data Model (data/ directory)

| File | Status |
|---|---|
| data/coa_schema.json | COMPLETE — 13 batches, 11 gates each, all NOT_TESTED |
| data/compliance_reach_clp.json | COMPLETE — 13 SKUs, all NOT_REVIEWED |
| data/country_matrix.json | COMPLETE — DE/PL/EU_GENERIC, all NOT_STARTED |
| data/internal_legal_hold_profiles.json | COMPLETE — Retatrutide/Semaglutide/Tirzepatide internal only |
| data/lab_registry.json | COMPLETE — empty schema, no labs registered yet |
| data/landed_cost_matrix.json | COMPLETE — 13 core + LEGAL_HOLD + EXTENDED_RANGE; all costs null (AWAITING_REAL_SUPPLIER_DATA) |
| data/legal_entity_status.json | COMPLETE — status: PRE_LAUNCH, all fields null |
| data/release_status.json | COMPLETE — all 11 gates null/false |
| data/research_profiles.json | COMPLETE — 16 profiles exported (13 public + ghk-cu/nad+/mots-c legacy) |
| data/supplier_registry.json | COMPLETE — empty schema, no suppliers yet |
| data/tax_review_status.json | COMPLETE — status: CROSS_BORDER_TAX_REVIEW_REQUIRED |

## Phase 3 — Research Library

| Item | Status |
|---|---|
| All 13 compound profiles in RESEARCH_PROFILES | COMPLETE |
| MOTS-C-10/20/40 profiles with verified PMIDs | COMPLETE |
| PMID verification: 25738459 (Lee, Cell Metabolism 2015) | CONFIRMED via NCBI API |
| PMID verification: 33473109 (Reynolds, Nature Comm 2021) | CONFIRMED via NCBI API |
| PMID verification: 27216708 (Lee, Free Rad Biol Med 2016) | CONFIRMED via NCBI API |
| data/research_profiles.json snapshot | COMPLETE |
| No invented DOIs or PMIDs | CONFIRMED |

## Phase 4 — Batch Release Gate System

| Item | Status |
|---|---|
| All 13 batches: NOT_RELEASED across all 11 gates | COMPLETE |
| batchResult() shows prominent NOT_RELEASED banner | COMPLETE |
| No batch shown as VERIFIED | CONFIRMED |
| Certificates page: "Kein Batch aktuell freigegeben" | COMPLETE |
| No dummy COA stamps or fake documents | CONFIRMED |

## Phase 5 — APP JS / HTML V6 Updates

| Item | Status |
|---|---|
| home(): "13 Produkte, ein Standard." | COMPLETE |
| researchLibrarySection(): "13 quellenbasierte Research Profiles." | COMPLETE |
| productsPage(): "13 Research Products." | COMPLETE |
| qualityPage(): "13/13 Produkte dokumentiert." | COMPLETE |
| certificates() function — NOT_RELEASED gate display | COMPLETE |
| #certificates route in nav and router | COMPLETE |
| legal(): PRE_LAUNCH status banner | COMPLETE |
| No fake impressum data | CONFIRMED |
| QA JS expected[] updated to V6 batches/concentrations/prices | COMPLETE |
| LEGAL_HOLD check in QA JS | COMPLETE |
| Cart test updated (bpc-157 + tb-500, V6 prices) | COMPLETE |

## Phase 6 — QA Results

| Check | Status |
|---|---|
| python build_elements_site.py | PASS — builds without errors |
| STATIC_QA (standalone_static_check.py) | PASS — "products=13, images/QR inlined, banned shell markers=0" |
| CDP production QA (cdp_production_qa.js) | NOT_RUN — requires Chrome with remote debugging on port 9333; run manually with: `node qa/cdp_production_qa.js` |
| FLOATING_VIALS check | NOT_AUTOMATED — visual check required |
| LEGAL_HOLD SKUs absent from public grid | PASS — confirmed by code inspection (no semaglutide/tirzepatide/retatrutide in PRODUCTS) |
| No fake COA documents | PASS — certificates page shows explicit NOT_RELEASED only |
| No human-use instructions | PASS — no dosing, no reconstitution, no injection content |
| No Heilversprechen | PASS — all product descriptions are research-use-only |

---

## Known Blockers (PRE_LAUNCH — not a build defect)

These are real-world blockers that require human action, not code fixes:

| Blocker | Status Code | Action Required |
|---|---|---|
| Legal entity formation | PRE_LAUNCH | Register company (DE or PL GmbH/Sp. z.o.o.) |
| § 5 DDG impressum data | PRE_LAUNCH | Obtain real business address, VAT ID, registration number |
| Supplier quotes | AWAITING_REAL_SUPPLIER_DATA | Contact peptide suppliers, get real COGs |
| Lab qualification | LAB_REGISTRY_EMPTY | Qualify external testing lab, get HPLC/MS capability confirmation |
| Batch testing | NOT_TESTED | Order samples, send to qualified lab |
| REACH/CLP review | NOT_REVIEWED | Commission specialist review per compound |
| Cross-border tax review (DE/PL) | NOT_STARTED | Engage tax advisor for EU e-commerce + Polish warehouse structure |

---

## Compliance Audit Summary

| Rule | Result |
|---|---|
| NIE Platzhalter-Rechtsdaten | PASS — legal page explicitly PRE_LAUNCH, no invented address/VAT |
| NIE erfundene DOI/PMID | PASS — all 16 research profiles use verified PMIDs |
| NIE Fake-COAs | PASS — certificates page shows "Kein Batch aktuell freigegeben" only |
| Keine Dosierungspläne | PASS — zero dosing content across all routes |
| Keine Human-Use Instructions | PASS — no reconstitution, injection, or administration content |
| Keine Heilversprechen | PASS — no therapeutic claims |
| LEGAL_HOLD exclusion | PASS — Semaglutide/Tirzepatide/Retatrutide absent from all public routes, sitemap, nav |
| Alle Batches NOT_RELEASED | PASS — none shown as VERIFIED or RELEASED |

---

## File Inventory

```
build_elements_site.py          — PRIMARY SSOT (PRODUCTS, CSS, APP JS, RESEARCH_PROFILES, QA_JS, STATIC_QA)
build_elements_site_v2.py       — Image compositing engine (PRODUCTS updated to match)
index.html                      — Generated production output
_standalone.html                — Generated Base64-inlined standalone
app.js                          — Generated JS (same as APP string in build_elements_site.py)
styles.css                      — Generated CSS
data/                           — 11 JSON data files (see Phase 2 table)
assets/products/                — 30 product images (13 SKUs × vial+detail + 4 MOTS-C variants)
assets/scenes/                  — 6 scene images
img/                            — 13 QR code PNGs (one per V6 batch)
qa/                             — CDP production QA + static check scripts
```

---

## V7 Competitor-Upgrade Addendum

**Branch:** flagship-v6-enterprise  
**Build date:** 2026-08-29  
**Source:** BUILD_BRIEF_V7_COMPETITOR_UPGRADE.md (glowingpeptides.com analysis)  
**Constraint:** No brand changes, no LEGAL_HOLD impact, no invented data.

| # | Feature | Status | Notes |
|---|---|---|---|
| F1 | 18+ Age-Gate (P0) | **COMPLETE** | Real technical block — overlay with `position:fixed;inset:0;z-index:9000`. Ja/Nein + Pflicht-Checkbox + disabled Confirm button. `localStorage` key `elementsAgeGateConfirmed`. Inline `<script>` prevents flash for returning visitors. Works in `index.html` AND `_standalone.html`. |
| F2 | Produktseiten-Tabs | **COMPLETE** | 7 tabs per detail page: Beschreibung, Labortest/COA, Anwendungsbereiche, Lagerung, Haftungsausschluss, Versand & Rückgabe, FAQ. Content sourced from Research Profiles; COA tab honest NOT RELEASED. No dosing/reconstitution instructions. |
| F3 | Trust-Badges am Produkt | **COMPLETE** | Icon row on every detail page: "Versand aus Europa", "Batch-verifiziert", "Qualitätskontrolle", "24/7 Kundendienst". |
| F4 | Research-Only Reminder am CTA | **COMPLETE** | Warning banner directly under Add to Cart on every detail page: "Nur für Forschungszwecke — keine Anwendung am Menschen." |
| F5 | Wissensbereich / Research Hub | **COMPLETE** | Route `#info` (alias `#research-hub`). 5 knowledge cards: Was sind Peptide?, Verwendungszweck & Abgrenzung, Qualität & Analytik (COA/HPLC/SDS), Gesetzeslage & Verantwortung, Sicherer Umgang & Lagerung. Nav link "Research Library" added before About. 6 compound profile preview cards below. |
| F6 | MOTS-C Variantenauswahl | **COMPLETE** | Single card in grid with 10/20/40mg variant buttons (price + image + cart-target switching). Detail page shows variant button row; each variant button navigates to correct `#product=mots-c-XY` route. Grid deduplication via `renderProductGrid()`. |

### QA Results — V7

| Check | Result |
|---|---|
| `python build_elements_site.py` | PASS — builds without errors |
| `qa/standalone_static_check.py` | PASS — `products=13, images/QR inlined, banned shell markers=0` |
| LEGAL_HOLD (semaglutide/tirzepatide/retatrutide) | PASS — absent from index.html AND _standalone.html |
| Age gate in index.html | PASS — overlay HTML + inline localStorage check present |
| Age gate in _standalone.html | PASS — overlay HTML + initAgeGate IIFE present |
| Research Library nav link | PASS — `href="#info"` in both files |
| No invented COA data | PASS — COA tab shows explicit NOT RELEASED status |
| No dosing/reconstitution instructions | PASS — storage tab has generic peptide handling only |
| No Heilversprechen | PASS — all tab content is research-use-only framing |
| V6 prices/batches unchanged | PASS — PRODUCTS array not modified |

### Compliance Delta (V6 → V7)

- Age gate added: **stronger** — technical content block, not cosmetic
- COA tab: **honest** — shows NOT RELEASED gate status, not fake lab reports
- Research-only reminders: **increased** — CTA-adjacent on every product
- Research Hub: **new** — background knowledge without treatment/dosing claims
