# Elements Lab — Pre-Mortem & QA Contract

## Risiken und Gegenmaßnahmen
- Hero wirkt wie generischer Peptid-Shop → eigener Wordmark, modulare Element-Grafik, Quality-System im Hero.
- Farben wirken billig/neon → gedecktes Technical-Luxury-System, Cyan nur als Verification-Akzent.
- Produktbilder wirken KI-fehlerhaft → Vials/Labels als echte CSS/SVG-Komposition mit korrektem Text.
- Medizinische Claims → nur Research-Kontext, keine Einnahme, Dosierung, Heilung, Human Use.
- Produkte fehlen → automatischer 13/13 Product-, Price-, Batch- und COA-Test.
- Cart nur Deko → Playwright-Test für Add, Quantity, Remove, Total und Demo-Checkout.
- Batch Lookup nur Fake → echte Hash-Route und Eingabetest für alle 13 Batchnummern.
- COA wirkt wie echte Laborprüfung → jedes Report-Element trägt DEMO / SAMPLE REPORT.
- Partner View leakt intern öffentlich → nicht in öffentlicher Navigation, eigene Hash-Route.
- Mobile bricht → Viewport-Tests 390, 430, 768, 1440, 1920 mit Overflow-Check.

## Acceptance
BLOCKER=0, CRITICAL=0, MAJOR=0 vor Übergabe. Minor nur bei geringer Relevanz.
