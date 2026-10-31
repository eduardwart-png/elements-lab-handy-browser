# Feature-Karte – Elements Labs Telegram-Shop (Mini-App)

- **Zweck:** Vage Meldungen („der Button oben rechts geht nicht“) ohne Code-Suche einer Oberfläche und einer Codestelle zuordnen.
- **Stand des Codes**, keine Live-Prüfung, kein Server gestartet, keine Datenbank gelesen. Zeilennummern gelten für den Arbeitsbaum vom 26.10.2026 und verschieben sich bei jeder Codeänderung.
- **Vorlage:** `OBSIDIAN__GODSTANDARD/_templates/FEATURE_MAP_TEMPLATE.md` existiert nicht; Muster waren `dev__community-control/docs/FEATURE_MAP.md` und `dev__hotel-direct-core/docs/FEATURE-MAP.md`.
- **Quelle:** gezielt gelesen (rg/sed): `miniapp/server.py`, `bot.py`, `support.py`, `live.py`, `terms.py`, `build.py`, `public/{index.html,app.js,telegram.js,shop-formats.js,terms.js,zoom.js,i18n.js,sw.js}`, `tests/*`, Wurzel `index.html`/`app.js`. Nicht gelesen: Schlüssel/`.env` und Kostendateien; die Karte nennt keine Preiswerte.

## Wichtig vor dem Bearbeiten: wo wird wirklich geändert?

`miniapp/public/` ist **Build-Ausgabe** (`build.py` schreibt sie, Webroot des Servers). Dort nie von Hand ändern, die Zeilen unten dienen nur zum **Finden**.

| Datei in `public/` | Ursprung (hier ändern, dann `python3 build.py`) |
|---|---|
| `telegram.js`, `shop-formats.js`, `terms.js`, `zoom.js`, `storage.js`, `miniapp.css` | identische Kopie aus `miniapp/extensions/<gleicher Name>` (per `cmp` gleich) |
| `sw.js` | `extensions/sw.js` (weicht ab, build.py ändert beim Kopieren) |
| `app.js`, `index.html`, `i18n.js`, `styles.css`, `variants.js` | Referenz `evidence/reference-current/<Name>` plus Ersetzungen in `build.py` (`replace_once`, Zeilen ~80–260); `i18n.js` zusätzlich `extensions/i18n-extra.js` |
| Datenblöcke in `index.html` (`#productData`, `#formatData`, `#packData`, `#catalogData`, `#termsData`) | `data/products.json`, `data/shop-formats.json`, `data/catalog-packs.json`, `data/catalog.json`, `data/terms.json` |

Die Frontend-Tests (`tests/*.cjs`) laden `extensions/*.js`, nicht `public/`.

Schreibweise: `P` = `miniapp/public/`, `E` = `miniapp/extensions/`, `S` = `miniapp/server.py`, `B` = `miniapp/bot.py`, `SU` = `miniapp/support.py`, `L` = `miniapp/live.py`. Zeilen in `P/app.js` sind sehr lang (viele Funktionen in einer Zeile): Zeile finden, dann per Funktionsname suchen.

## Schnell-Einstieg für vage Meldungen

| Meldung | Zuerst prüfen |
|---|---|
| „Button oben rechts“ | Suche (F5), Warenkorb-Link (F6), Sprache (F4), Menü (F3) – alle in `P/index.html:41–49` |
| „Altersabfrage kommt nicht weg / blockiert alles“ | F1; Speicher `elementsAgeGateConfirmed` in `P/storage.js` |
| „Bestellung senden geht nicht“ | F16 (Knopf `#checkoutBtn`, `P/telegram.js:325`), dann B4 (`POST /api/orders`, `S:306`), Fehlertext aus `#orderFeedback` |
| „Unten ‚Warenkorb‘ / Telegram-Knopf falsch“ | F7 (untere Leiste), F25 (MainButton/BackButton) |
| „Seite leer / ‚nicht gefunden‘“ | Routing F22 (`route()`), Startparameter F23 |
| „Bot antwortet nicht“ | C1–C10 (`bot.py`/`support.py`), Prozess D1 (`live.py`) |
| „Preis/Rabatt/Mindestbestellwert falsch“ | F15 (Anzeige `terms.js`) und F16/B4 (serverseitig `terms.py`) – beide müssen gleich rechnen (`tests/terms_calc.cjs`) |

## A. Shop-Oberflächen (Mini-App, Hash-Routing)

Zugriff: lokal `python3 server.py --port 8766` → `http://127.0.0.1:8766/#<route>` (`Shop-Vorschau.command`); Telegram über `Live-starten.command` (Menüknopf „🛒 Shop öffnen“, `L:155`). Routing: `route()` in `P/app.js:323`.

| # | Feature (sichtbarer Name) | Zugriffsweg | Selektor / DOM-Anker | Datei:Zeile (Frontend → Backend) | Test | Liest (nur Dateinamen) |
|---|---|---|---|---|---|---|
| F1 | Alterssperre „Bevor du fortfährst“ | erster Aufruf, vor allem anderen | `#ageGate`, `#ageYes`, `#ageNo`, `#ageCheckbox`, `#ageConfirmBtn` | `P/index.html:14–32`; Logik `P/app.js:2–15`; Prüfung vor Senden `P/telegram.js:328`. Backend: keines | `tests/test_fixes_public.py:46` (Text „du“); `tests/browser_acceptance.py` | `i18n.js` (Texte `age.*`) |
| F2 | Kopfzeile / Logo „ELEMENTS LABS“ | immer sichtbar, Link `#home` | `header.site-header#top`, `a.brand` | `P/index.html:34–35` | `tests/browser_acceptance.py` | `assets/logos/*` |
| F3 | Menü-Knopf „Menu“ (Hauptnavigation) | Kopfzeile, mobil | `#menuToggle`, `#mainNav` | `P/index.html:36–38`; Klick `P/app.js:442`; aktive Markierung `P/app.js:402` | `tests/browser_acceptance.py` | – |
| F4 | Sprachwahl DE / EN / FR | Kopfzeile oben rechts | `[data-lang-toggle]`, `[data-lang-btn="de|en|fr"]`, `.lang-dropdown` | `P/index.html:41–47`; Klick `P/app.js:406–423`; `setLang` `P/i18n.js:651`, `t()` `P/i18n.js:659`; Speicher `elementsLang` | `tests/test_fixes_public.py:69`; `browser_acceptance.py` (DE/EN/FR) | `i18n.js`, `extensions/i18n-extra.js` |
| F5 | „Search“ (Knopf oben rechts) | Kopfzeile → springt auf `#products/vial` und setzt Fokus | `.search-open[data-action="focus-search"]` | `P/index.html:49`; Klick `P/app.js:445` | `tests/browser_acceptance.py` | – |
| F6 | „Cart 0“ (Warenkorb-Link oben rechts, Zähler) | Kopfzeile → `#cart` | `a.cart-link`, `#cartCount` | `P/index.html:49`; Zähler `P/app.js:34` (`updateCartCount`) | `tests/test_pending_cart.cjs`; `browser_acceptance.py` | Speicher `elementsTelegramCart` (`P/app.js:33`) |
| F7 | Untere Leiste: Start · Vials · Doppelkammer · Pen · Packs · Warenkorb | unten, nur Mini-App | `nav.mini-bottom-nav`, `[data-mini-route]`, `#miniCartCount` | `P/index.html:73` (aus `build.py:~135–139`); aktiv/Zähler `P/telegram.js:248` (`syncNav`), `P/telegram.js:277` (`sync`), `P/telegram.js:295` | `tests/test_launch_and_nav.cjs` | – |
| F8 | Startseite | `#home` (leer) | `app > section.hero#home-hero` | `P/app.js:140` (`home()`); 10er-Pack-Teaser `P/shop-formats.js:254` | `tests/test_reference_refresh.py:29` | `products.json`, `catalog-packs.json` |
| F9 | Vials-Katalog (mit Format-/Kategorie-/Sortierfilter, Suche) | `#products/vial` | `#productGrid`, `#searchInput`, `#categoryFilter`, `#sortFilter`, `#formatFilter`, `[data-product-card]` | `P/app.js:200` (`productsPage`), Route `P/app.js:326`; Filter-Logik `P/app.js:370`; Leerzustand `P/shop-formats.js:292` | `tests/test_fixes_public.py:63`; `tests/test_dose_search.cjs`; `tests/test_build.py:11` | `products.json` |
| F10 | Doppelkammer inkl. Pen | `#dual-chamber` (auch `#products/dual`) | gleiche Anker wie F9; Karten `[data-format="dual"]` | Route `P/app.js:326`; Karten `P/app.js:61` (`productCard`); `P/shop-formats.js:74–82` | `tests/test_formats.py:9`; `tests/test_reference_refresh.py:18`; `test_shop_ui.cjs` | `shop-formats.json` |
| F11 | Produktseite (Tabs, Menge, „In den Warenkorb“, Batch zeigen, Format wählen) | `#product=<id>` | `.prod-tab[data-tab]`, `.prod-tab-content`, `button[data-add]`, `a[href^="#batch="]`, `.variant-picker` | `P/app.js:214` (`productDetail`), „In den Warenkorb“ `P/app.js:255`, Format-Wahl `P/app.js:269`, Tabs `P/app.js:84` und `P/app.js:396`; Packblock `P/shop-formats.js:116`; Hinzufügen `P/app.js:36` / Klick `P/app.js:349` | `tests/test_fixes_public.py:58`; `browser_acceptance.py` (alle Variantenseiten) | `products.json`, `shop-formats.json`, `researchData` (in `index.html`) |
| F12 | Mehrweg-Pen | `#accessories` / `#product=mehrweg-pen` | `.pen-page`, `.accessory-card`, `.optional-pen` | Route `P/app.js:328`; `P/app.js:275` (`penDetail`), `P/app.js:273–274`; Detail `P/shop-formats.js:84` | `tests/test_reference_refresh.py:10` | `shop-formats.json` |
| F13 | 10er-Packs (Komplettkatalog, Filter-Chips, Einzelzelle zum Hinzufügen) | `#packs` | `.packs-page`, `[data-pack-type]`, `[data-pack-section]`, `[data-pack-query]`, `button.pack-cell[data-add]` | Route `P/app.js:329`; `P/shop-formats.js:247` (`packsPage`), Zelle `:224–227`, Zeile `:229`, Neuaufbau `:260`, Leerzustand `:292` | `tests/test_shop_ui.cjs`; `tests/test_preisfamilie.py:57`; `tests/test_quotes.py:56` | `catalog-packs.json` |
| F14 | Warenkorb (Mengen +/−, Entfernen, Summe, Hinweis Preis auf Anfrage) | `#cart` | `.quote-cart`, `[data-qty][data-delta]`, `[data-remove]`, `#cartTotal` | Route `P/app.js:338` → `P/shop-formats.js:90` (`cartPage`; die ältere `cartPage` `P/app.js:278` wird nicht mehr genutzt); Summen `P/shop-formats.js:54` (`summary`); Klicks `P/app.js:350–351` | `tests/test_pending_cart.cjs`; `tests/test_shop_ui.cjs` | Speicher `elementsTelegramCart` |
| F15 | Konditionen-Feld: Mindestbestellwert, Sammelbestellung, Mengenrabatt | im Warenkorb und auf `#packs` | `#collectiveToggle`, `#minOrderNote`, `.tm-warn`, `.tm-collective` | `P/terms.js:111` (`calc`), `:130` (`panel`), `:143` (Schalter), `:151` (`strip`); Serverseite `miniapp/terms.py:40` (`calc`) | `tests/test_terms.py:35/65/106/116`; `tests/terms_calc.cjs` (Parität JS↔Python) | `terms.json` |
| F16 | „Bestellanfrage senden“ (Testanfrage, kein Versand/Zahlung) | Warenkorb-Knopf; Telegram-MainButton „senden“ | `#checkoutBtn`, `#orderFeedback[data-order-id]` | Front `P/telegram.js:325` (`checkout`), `fetch('/api/orders')` `:342`; Backend `S:301` (`do_POST`) → `S:64` (`save_request`), Mindestbestellwert `S:102`, Rate-Limit `S:131`, Referenz `EL-TEST-…` `S:132`, Fehlerabbildung `S:319–328`, Telegram-Bestätigung `S:329–347` | `tests/test_server.py:44/57/68`; `tests/test_quotes.py:28`; `tests/test_order_timeout.cjs`; `tests/test_pending_cart.cjs` | schreibt `runtime/test-requests.sqlite3`; liest `products.json`, `terms.json` |
| F17 | Eigene letzte Anfragen / Quittung im Warenkorb | nach Senden, `#cart` | `#orderHistory`, `#orderFeedback` | `P/telegram.js:191` (`renderHistory`), `:199` (`renderReceipt`) | – (kein eigener Test gefunden) | Speicher (Verlauf, max. 8) |
| F18 | Chargen-Suche „Batch Lookup“ | `#batch-lookup`, `#batch=<id>`; Eingabe auf Startseite | `#batchInput`, `#batchSubmit`, `#batchInputHome`, `#batchSubmitHome`, `#sampleBatch` | `P/app.js:207` (`batchPage`), `:209` (`batchResult`), Eingabe `:357–361`; Route `P/app.js:331` und `:334` | `tests/browser_acceptance.py` (gültige/ungültige Suche) | `products.json` (Feld batch) |
| F19 | Qualität / Zertifikate / Research Library | `#quality`, `#certificates`, `#info` (= `#research-hub`) | `#quality-section`, `.report[data-coa]` | `P/app.js:205` (`qualityPage`), `:137` (`report`), `:284` (`certificates`), `:288` (`researchHubPage`), `:211` (`researchProfileBlock`) | `tests/test_texte.py:19` (nur veraltete Formulierungen) | `researchData` (in `index.html`) |
| F20 | About · FAQ · Kontakt (Hilfe-Block) | `#about`, `#faq`, `#contact` | `section.legal`, `.faq-list`, `#contactHelp` | `P/app.js:281–283`; Kontakt-Hilfe `P/telegram.js:261` (`contactHelp`) | `tests/test_texte.py:19` (nur veraltete Formulierungen) | `i18n.js` |
| F21 | Impressum · Datenschutz (Fußzeile) | `#legal-impressum`, `#legal-datenschutz` | `footer.footer a[href^="#legal"]` | `P/index.html:66–71`; `P/app.js:285` (`legal`) | `tests/test_fixes_public.py:29` | `i18n.js` |
| F22 | Routing / „Nicht gefunden“ | jeder Hash | – | `P/app.js:323` (`route`), `render` `:435`, `hashchange` `:437`; Fehlerseite `P/telegram.js:188` (`notFound`) | `tests/test_launch_and_nav.cjs`; `tests/test_build_swap_and_links.py:30` | – |
| F23 | Startparameter / Deep-Link `?start=p_<produkt>` und `?tgWebAppStartParam` | Telegram-Link | – | `P/telegram.js:103` (`launchRoute`), `:108` (`queryRoute`), `:113` | `tests/test_launch_and_nav.cjs` | – |
| F24 | Scroll-Wiederherstellung und Listen-Zustand | Zurück aus Produktseite | – | `P/telegram.js:61` (`restoreScroll`), `:82` (`rememberList`), `:89` (`restoreList`) | `tests/test_scroll_restore.cjs` | – |
| F25 | Telegram-Knöpfe: MainButton (Warenkorb/Senden), BackButton | nur in Telegram (`initData`) | `Telegram.WebApp.MainButton/BackButton` | `P/telegram.js:121` (`mainButton`), `:252–258`, `:300`, `:424–425`; Safe-Areas `:375` | – (kein direkter Test gefunden); `evidence/telegram-simulator.json` (nur Schnittstellenprobe) | – |
| F26 | Merkliste (Herz) und Zusatzkatalog „Katalog“ | `#catalog` (nur sichtbar, wenn veröffentlichte Artikel existieren) | `[data-wish]`, `[data-cat]`, `.cat-grid` | `P/telegram.js:120` (`hasCatalog`), `:146` (`toggleWish`), `:167–183` (`catalogPage`), `:207` (`bindCatalog`) | Merkliste: `tests/test_frontend.cjs:15–19`; Katalogseite: kein Test gefunden | `catalog.json` (Stand: leer, `items: []`) |
| F27 | Teilen-Knopf (Produkt) | Produktseite | `#shareProduct` | `P/telegram.js:155` (`share`), `:231` (`shareProduct`) | – (kein eigener Test gefunden) | – |
| F28 | Bild-Vergrößerung (Zoom) | Klick auf Produktbild | `[data-zoomable]`, Overlay | `P/zoom.js:60` (`open`), `:54` (`close`), `:118` (`decorate`) | `tests/test_zoom.cjs`; `tests/test_fixes_public.py:69` | – |
| F29 | Cloud-Sync Warenkorb/Merkliste/Sprache | in Telegram, automatisch | – | `P/telegram.js:386` (`cloudSync`); Speicherschicht `P/storage.js:18` (`ELStore`) | – (kein Test gefunden) | Telegram CloudStorage |
| F30 | Offline-Cache (Service-Worker) | automatisch | – | `P/sw.js:7`; Quelle `E/sw.js` | – | – |
| F31 | Absturzmeldung des Browsers an den Server | automatisch bei JS-Fehlern | – | Front `P/telegram.js:19` (`report`) → `POST /api/client-error` `S:304` → `S:271` (`client_error`, max. 30/min, Log `CLIENT-ERROR`) | `tests/test_http_and_bot.py:67` | `runtime/service.log` (Ausgabe) |

## B. Server-Endpunkte (`miniapp/server.py`)

| # | Feature | Route | Datei:Zeile | Test |
|---|---|---|---|---|
| B1 | Statische Auslieferung `public/` (ETag, gzip, CSP mit Hash der Inline-Skripte, Host-Prüfung, blockiert Punkt-Pfade) | `GET /…`, `HEAD` | `S:228` (`do_GET`), Host `S:220`, CSP `S:204–210`, Pfadsperre `S:238–241` | `tests/test_http_and_bot.py:34/122` |
| B2 | Konfiguration (Modus, Botname) | `GET /api/config` | `S:234` | `tests/test_http_and_bot.py:34` |
| B3 | Gesundheitsprobe | `GET /health` | `S:236` | `tests/test_http_and_bot.py:34`; Nutzer: `L:53` (`healthy`) |
| B4 | Bestellanfrage speichern | `POST /api/orders` | `S:306`, Logik `S:64`, Prüfung der Telegram-Anmeldung `S:36` (`validate_init_data`), Bestätigung an Absender `S:139–180` | `tests/test_server.py:44` |
| B5 | Browser-Fehlerbericht | `POST /api/client-error` | `S:304`, `S:271` | `tests/test_http_and_bot.py:67` |
| B6 | Serverstart / Modus `preview` oder `telegram` | `python3 server.py --port 8766 [--mode telegram --public-origin …]` | `S:367` (`main`), Produktladen `S:354` | `tests/test_server.py:15` |

## C. Telegram-Bot (`bot.py`, `support.py`)

Zugriff: `@ElementsLabs_Shop_bot`; Befehlsliste `B:23`. Abfrage der Updates per Long-Polling `B:316` (`getUpdates`).

| # | Feature (sichtbarer Name) | Zugriffsweg | Datei:Zeile | Test |
|---|---|---|---|---|
| C1 | `/start` (Menü mit „🛒 SHOP ÖFFNEN“, Packs, Vials, Doppelkammer, Warenkorb) | Bot-Befehl privat | `B:89` (`reply_for`), `B:93`, Menü `B:123`, Senden `B:249` (`handle`) | `tests/test_http_and_bot.py:209` |
| C2 | `/shop /packs /vials /doppelkammer /pen /warenkorb /katalog` (öffnet Mini-App direkt am Bereich) | Bot-Befehle | `B:106–110`, Links `B:116` (`web_url`) | `tests/test_http_and_bot.py:223` |
| C3 | `/start p_<produkt>`, `/start packs|dual|pen|cart|katalog` (Deep-Links) | Link `t.me/…?start=…` | `B:93–101` | `tests/test_http_and_bot.py:209` |
| C4 | `/preisliste` und Knopf „📄 Preisliste (PDF)“ | Bot-Befehl / Callback `pricelist` | `B:104`, `B:192` (`send_pricelist`), `B:226` (`handle_callback`) | `tests/test_http_and_bot.py:248/259`; `tests/test_bot_resilience.py:25` |
| C5 | `/hilfe` | Bot-Befehl | `B:111` | `tests/test_texte.py:31` (Texte folgen `terms.json`) |
| C6 | Bot-Menü, Beschreibung, Kurzbeschreibung | beim Start | `B:286` (`main`), `B:295–297` | – |
| C7 | Kontakt-Weiterleitung `/kontakt` (je Person ein Thema in der Team-Gruppe, Sofortantworten) | Bot-Befehl / `?start=kontakt` | `SU:212–219` (`is_entry`, `wants_relay`), `SU:403` (`handle_private`), Thema `SU:376` (`ensure_topic`) | `tests/test_support_relay.py:111` |
| C8 | Team-Befehle `/offen /sperren /entsperren /schliessen` | nur interne Team-Gruppe | `SU:466` (`handle_team`), `/offen` `:482`, `/sperren` `:496`, `/entsperren` `:500`, `/schliessen` `:504` | `tests/test_support_relay.py:200/229` |
| C9 | Tages-Erinnerung offene Anfragen (nur wenn `ELEMENTS_SUPPORT_DIGEST=1`) | Zeitplan im Bot | `SU:525` (`digest_text`), `:536` (`maybe_digest`), `:558` (`poll_tick`) | `tests/test_support_relay.py:417/426` |
| C10 | Beitrittsanfrage Kunden-Gruppe („Händler oder Endkunde?“) | Gruppen-Beitrittsanfrage | `SU:567` (`handle_join_request`), `:587` (`handle_chat_member`), `:599` (`handle_role`) | kein Test gefunden |
| C11 | Einladungslinks mit Zähler | Werkzeug (CLI) | `tools/invite_links.py`; Zähler `SU:291/301/306` | `tests/test_invite_links.py:20` |

## D. Betrieb und Aufbau

| # | Feature | Zugriffsweg | Datei:Zeile | Test |
|---|---|---|---|---|
| D1 | Live-Betrieb (Tunnel + Server + Bot + Menüknopf, Selbstheilung, Mac wach halten) | `Live-starten.command` | `L:170` (`main`), `L:116` (`start_stack`), `L:66` (`restart_reason`), `L:88` (`keep_awake`), `L:46` (`tunnel_url`), `L:155` (`setChatMenuButton`) | `tests/test_live.py:15` |
| D2 | Shop-Build | `python3 build.py` (nicht im Betrieb ausführen, schreibt `public/`) | `build.py` (Ersetzungen ab ~`:80`, Katalog `:37`) | `tests/test_build.py:10`; `tests/test_build_swap_and_links.py:8` |
| D3 | Katalog nachpflegen | `Katalog-aktualisieren.command` mit `katalog.csv` | `tools/import_catalog.py` | kein direkter Test gefunden |
| D4 | Preisfamilie anwenden (Preisregeln) | Werkzeug | `tools/apply_pricing.py` | `tests/test_pricing.py:28`; `tests/test_preisfamilie.py:47` |

## E. Ältere Wurzel-Website (nicht die Mini-App)

`/index.html`, `/app.js`, `/styles.css` im Repo-Wurzelordner: statische Flagship-Seite (14 Produkte, eigener Warenkorb mit `localStorage` `elementsCart`). Gebaut aus `build_elements_site.py`; QA in `qa/*.js`. Anker: Menü `index.html` `#menuToggle`/`#mainNav`/`#cartCount`; Routing `app.js:38` (`route`), `app.js:21` (`home`), `:28` (`batchPage`), `:32` (`productDetail`), `:33` (`cartPage`), `:39` (`bind`), `:41` (`hashchange`), Menü-Klick `:42`. Tests: `qa/cdp_production_qa.js`, `qa/standalone_static_check.py` (Pfade im `package.json` zeigen auf einen Windows-Ordner, hier nicht lauffähig ohne Anpassung). Eine Meldung aus der Telegram-Mini-App betrifft **nicht** diese Dateien.

## Ablauf bei einer vagen Meldung (Beispiel)

„Der Button oben rechts geht nicht“ → Kopfzeile `P/index.html:41–49` → drei Kandidaten: Sprache (F4, `P/app.js:406`), Suche (F5, `P/app.js:445`), Warenkorb (F6, Link `#cart`, Route `P/app.js:338` → `P/shop-formats.js:90`). Wenn der Warenkorb leer wirkt: Speicher `elementsTelegramCart` (`P/app.js:30–33`) und Telegram-CloudStorage (F29). Änderung immer in `extensions/` bzw. `build.py`, danach Build und Tests (`python3 -m unittest discover -s tests`, `node tests/test_frontend.cjs`).

Stand: 2026-10-26, erzeugt aus Code, bei Aenderung aktualisieren
