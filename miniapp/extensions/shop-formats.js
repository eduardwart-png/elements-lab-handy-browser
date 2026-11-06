/* Format-aware catalogue and quote cart. No invented prices or delivery claims. */
window.ELShop = (() => {
  const vials = JSON.parse(document.getElementById('productData').textContent);
  const formats = JSON.parse(document.getElementById('formatData').textContent);
  const packElement = document.getElementById('packData');
  const extraPacks = packElement ? JSON.parse(packElement.textContent) : [];
  const all = [...vials, ...formats, ...extraPacks];
  const dict = {
    de: {'shop.vials':'Vial-Ausführungen','shop.duals':'Doppelkammer-Ausführungen','shop.pen':'Mehrweg-Pen','shop.accessories':'Zubehör','shop.choose':'Ausführung wählen','shop.variants':'Varianten','shop.quote':'Preis auf Anfrage','shop.add':'Zur Anfrage hinzufügen','shop.request':'Unverbindliche Anfrage','shop.known':'Bekannte Positionen','shop.extra':'Weitere Preise auf Anfrage','shop.total':'Gesamtsumme','shop.schematic':'Schematische Darstellung · kein Produktfoto','shop.open':'Ausführung ansehen','shop.back':'Zur Übersicht','shop.lead':'Alle Ausführungen. Ein gemeinsamer Warenkorb.','shop.details':'Preis, genaue Ausstattung und Lieferumfang werden auf Anfrage geklärt. Eine Anfrage ist keine Bestellung.','shop.search':'Name oder Konzentration suchen','shop.all':'Alle Forschungsbereiche','shop.noResults':'Keine Treffer. Suche oder Bereich ändern.','shop.format':'Ausführung','shop.vial':'Vial','shop.dual':'Doppelkammer','shop.samples':'Weitere Materialien','shop.systems':'Technische Systemrecherche','shop.continue':'Weiter stöbern','shop.quantity':'Menge','shop.remove':'Entfernen','shop.empty':'Deine Anfrageliste ist noch leer.','shop.cartLead':'Prüfe Einzelartikel, 10er-Packs und Mengen. Bei 10er-Packs steht Menge 1 für 10 Stück. Rabatt und Versand siehst du in der Übersicht.','shop.ranges':'Unser Katalog','cat.Accessories':'Zubehör'},
    en: {'shop.vials':'Vial variants','shop.duals':'Dual-chamber variants','shop.pen':'Reusable pen','shop.accessories':'Accessories','shop.choose':'Choose a format','shop.variants':'variants','shop.quote':'Price on request','shop.add':'Add to request','shop.request':'Non-binding request','shop.known':'Priced items','shop.extra':'Additional prices on request','shop.total':'Total','shop.schematic':'Schematic artwork · not a product photo','shop.open':'View variant','shop.back':'Back to overview','shop.lead':'Every format. One shared request list.','shop.details':'Price, specific configuration and supply details are confirmed on request. A request is not an order.','shop.search':'Search name or concentration','shop.all':'All research areas','shop.noResults':'No results. Change your search or area.','shop.format':'Format','shop.vial':'Vial','shop.dual':'Dual chamber','shop.samples':'Additional materials','shop.systems':'Technical system research','shop.continue':'Continue browsing','shop.quantity':'Quantity','shop.remove':'Remove','shop.empty':'Your request list is empty.','shop.cartLead':'Review single items, 10-packs and quantities. For 10-packs, quantity 1 means 10 pieces. Discount and shipping are shown in the summary.','shop.ranges':'Our catalogue','cat.Accessories':'Accessories'},
    fr: {'shop.vials':'Versions flacon','shop.duals':'Versions double chambre','shop.pen':'Stylo réutilisable','shop.accessories':'Accessoires','shop.choose':'Choisir un format','shop.variants':'variantes','shop.quote':'Prix sur demande','shop.add':'Ajouter à la demande','shop.request':'Demande sans engagement','shop.known':'Articles chiffrés','shop.extra':'Autres prix sur demande','shop.total':'Total','shop.schematic':'Schéma · pas une photo produit','shop.open':'Voir la variante','shop.back':'Retour au catalogue','shop.lead':'Tous les formats. Un panier commun.','shop.details':'Prix, configuration et livraison à préciser sur demande. Une demande ne constitue pas une commande.','shop.search':'Rechercher un nom ou une concentration','shop.all':'Tous les domaines','shop.noResults':'Aucun résultat. Modifiez la recherche.','shop.format':'Format','shop.vial':'Flacon','shop.dual':'Double chambre','shop.samples':'Matériaux supplémentaires','shop.systems':'Recherche technique','shop.continue':'Continuer','shop.quantity':'Quantité','shop.remove':'Supprimer','shop.empty':'Votre liste est vide.','shop.cartLead':'Vérifiez articles à l’unité, packs de 10 et quantités. Pour les packs de 10, la quantité 1 correspond à 10 pièces. Remise et livraison figurent dans le récapitulatif.','shop.ranges':'Notre catalogue','cat.Accessories':'Accessoires'}
  };
  for (const [lang, values] of Object.entries(dict)) Object.assign(window.__EL_I18N__[lang], values);
  for (const lang of Object.keys(dict)) Object.assign(window.__EL_I18N__[lang], {'shop.navVials': lang==='fr'?'Flacons':'Vials', 'shop.navDual': lang==='fr'?'Double':'Dual', 'shop.navPen': lang==='fr'?'Stylo':'Pen'});
  Object.assign(window.__EL_I18N__.de, {'cat.Metabolic Research':'Metabolische Forschung','cat.Peptide & Recovery Research':'Peptid- & Regenerationsforschung','cat.Cellular & Longevity Research':'Zelluläre & Langlebigkeitsforschung','cat.Neuro Research':'Neurologische Forschung'});
  Object.assign(window.__EL_I18N__.de, {'mini.reopen':'Telegram-Sitzung abgelaufen. Bitte den Shop schließen und neu öffnen. Deine Auswahl bleibt gespeichert.','mini.wait':'Zu viele Anfragen in kurzer Zeit. Bitte in einer Minute erneut versuchen.'});
  Object.assign(window.__EL_I18N__.en, {'mini.reopen':'Telegram session expired. Close and reopen the shop. Your selection is saved.','mini.wait':'Too many requests. Please try again in one minute.'});
  Object.assign(window.__EL_I18N__.fr, {'mini.reopen':'Session Telegram expirée. Fermez et rouvrez la boutique. Votre sélection est enregistrée.','mini.wait':'Trop de demandes. Réessayez dans une minute.'});
  Object.assign(window.__EL_I18N__.de, {'mini.remaining':'Deine neu hinzugefügten Positionen bleiben im Warenkorb und wurden noch nicht gesendet.'});
  Object.assign(window.__EL_I18N__.en, {'mini.remaining':'Newly added items remain in your cart and have not been sent yet.'});
  Object.assign(window.__EL_I18N__.fr, {'mini.remaining':'Les nouveaux articles restent dans le panier et ne sont pas encore envoyés.'});
  Object.assign(window.__EL_I18N__.de, {'shop.navPacks':'10er-Packs','shop.packVial':'Vial · 10er-Pack','shop.packDual':'Doppelkammer inkl. Pen · 10er-Pack','shop.packTitle':'10er-Packs','shop.packOffer':'10er-Pack · 10 Stück','shop.packEach':'je Stück','shop.packSave':'günstiger je Stück als im Einzelkauf','shop.packAdd':'10er-Pack hinzufügen','shop.packNote':'Preis je 10er-Pack (10 Stück). Mindestbestellwert {min}, Versand inklusive; darunter Sammelbestellung ab {cmin}. Mengenrabatt nur auf 10er-Packs ohne den Hinweis „ohne Mengenrabatt“.','shop.packType':'Ausführung','shop.packAllTypes':'Vial und Doppelkammer'});
  Object.assign(window.__EL_I18N__.en, {'shop.navPacks':'10-packs','shop.packVial':'Vial · 10-pack','shop.packDual':'Dual chamber incl. pen · 10-pack','shop.packTitle':'10-packs','shop.packOffer':'10-pack · 10 pieces','shop.packEach':'each','shop.packSave':'cheaper per piece than buying single items','shop.packAdd':'Add 10-pack','shop.packNote':'Price per 10-pack (10 pieces). Minimum order {min}, shipping included; below that, a group order from {cmin}. Volume discount applies only to 10-packs without the note “no volume discount”.','shop.packType':'Format','shop.packAllTypes':'Vial and dual chamber'});
  Object.assign(window.__EL_I18N__.fr, {'shop.navPacks':'Packs de 10','shop.packVial':'Flacon · pack de 10','shop.packDual':'Double chambre, stylo incl. · pack de 10','shop.packTitle':'Packs de 10','shop.packOffer':'Pack de 10 · 10 pièces','shop.packEach':'la pièce','shop.packSave':'moins cher la pièce qu’à l’unité','shop.packAdd':'Ajouter le pack de 10','shop.packNote':'Prix par pack de 10 (10 pièces). Commande minimum {min}, livraison incluse ; en dessous, commande groupée dès {cmin}. La remise quantité ne s’applique qu’aux packs de 10 sans la mention « sans remise quantité ».','shop.packType':'Format','shop.packAllTypes':'Flacon et double chambre'});
  /* Haendler-Anzeige (Inhaber 24.10.2026): 10er-Preis unter dem Einzelpreis, Pen inklusive, Rabattkennzeichnung */
  Object.assign(window.__EL_I18N__.de, {'shop.noDiscount':'ohne Mengenrabatt','shop.packDiscountOk':'Mengenrabatt möglich: {tiers}','shop.packDiscountNo':'Ohne Mengenrabatt','shop.under10':'{label}: 10er-Pack {pack}, {unit} je Stück','shop.penIncluded':'inklusive Pen','shop.dualPen':'Doppelkammer inkl. Pen','shop.packPenNote':'Jede Doppelkammer im 10er-Pack inklusive Pen.','shop.penIncludedTitle':'Mehrweg-Pen inklusive','shop.penIncludedText':'Jede Doppelkammer wird mit Mehrweg-Pen geliefert. Du musst keinen Pen zusätzlich bestellen.','shop.lineTotal':'Zeilensumme','shop.maxQty':'Maximal {max} je Position. Für größere Mengen bitte mehrere Positionen oder eine zweite Anfrage nutzen.','shop.searchInPacks':'Auch in den 10er-Packs suchen: „{q}“'});
  Object.assign(window.__EL_I18N__.en, {'shop.noDiscount':'no volume discount','shop.packDiscountOk':'Volume discount: {tiers}','shop.packDiscountNo':'No volume discount','shop.under10':'{label}: 10-pack {pack}, {unit} each','shop.penIncluded':'pen included','shop.dualPen':'Dual chamber incl. pen','shop.packPenNote':'Every dual chamber in the 10-pack includes a pen.','shop.penIncludedTitle':'Reusable pen included','shop.penIncludedText':'Every dual chamber is supplied with a reusable pen. You do not need to order a pen separately.','shop.lineTotal':'Line total','shop.maxQty':'Maximum {max} per item. For larger quantities please use several items or a second request.','shop.searchInPacks':'Search the 10-packs too: “{q}”'});
  Object.assign(window.__EL_I18N__.fr, {'shop.noDiscount':'sans remise quantité','shop.packDiscountOk':'Remise quantité : {tiers}','shop.packDiscountNo':'Sans remise quantité','shop.under10':'{label} : pack de 10 à {pack}, {unit} la pièce','shop.penIncluded':'stylo inclus','shop.dualPen':'Double chambre, stylo incl.','shop.packPenNote':'Chaque double chambre du pack de 10 inclut un stylo.','shop.penIncludedTitle':'Stylo réutilisable inclus','shop.penIncludedText':'Chaque double chambre est livrée avec un stylo réutilisable. Inutile de commander un stylo en plus.','shop.lineTotal':'Total de la ligne','shop.maxQty':'Maximum {max} par article. Pour de plus grandes quantités, utilisez plusieurs articles ou une seconde demande.','shop.searchInPacks':'Chercher aussi dans les packs de 10 : « {q} »'});
  let query = '', category = '', activeKind = '';
  const MAX_QTY = 99;  // gleicher Wert wie addToCart/setQty in app.js, telegram.js und server.py
  let maxQtyBound = false;
  const byId = id => all.find(p => p.id === id);
  /* Suche ohne Rücksicht auf Bindestrich, Leerzeichen und Groß-/Kleinschreibung. Reine Zahlen müssen als ganze Zahl vorkommen ("15" findet 15 mg, nicht 150 mg). */
  const fold = s => String(s).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const squash = s => fold(s).replace(/[^a-z0-9]+/g, '');
  function match(haystack, query) {
    const tokens = fold(query).split(/\s+/).filter(Boolean), flat = squash(haystack), plain = fold(haystack);
    return tokens.every(tok => (/^\d+$/.test(tok) ? new RegExp('(^|[^0-9])' + tok + '([^0-9]|$)').test(plain) : flat.includes(squash(tok))));
  }
  /* Suche mit Dosis ("Semaglutid 15", "reta 30"): die Variante der Gruppe, deren Stoffmenge zu den Zahlen der Suche passt.
     Nur eindeutige Treffer; ohne Zahl oder bei mehreren Treffern bleibt es bei der Standardvariante (leer). */
  function pickVariant(variants, query) {
    const nums = fold(query).split(/\s+/).filter(tok => /^\d+$/.test(tok));
    if (!nums.length || !variants || variants.length < 2) return '';
    const hits = variants.filter(v => { const conc = fold(v.concentration || ''); return nums.every(n => new RegExp('(^|[^0-9])' + n + '([^0-9]|$)').test(conc)); });
    return hits.length === 1 ? hits[0].id : '';
  }
  const isPack = p => p.format === 'vial_pack' || p.format === 'dual_pack';
  const kindLabel = p => t(p.format === 'vial_pack' ? 'shop.packVial' : p.format === 'dual_pack' ? 'shop.packDual' : p.format === 'dual_chamber' ? 'shop.dualPen' : p.format === 'pen' ? 'shop.accessories' : 'shop.vial');
  const unitPrice = p => fmt(Math.round(p.price_cents / (p.pack_size || 1)) / 100);
  const formatPrice = (id, fallback) => (all.find(p => p.id === id) || {}).price || fallback;
  let packType = '';
  const price = p => Number.isInteger(p.price_cents) ? fmt(p.price_cents / 100) : t('shop.quote');
  function summary(input) {
    let known = 0, quote = 0, quantity = 0;
    const lines = [];
    for (const [id, qty] of Object.entries(input || {})) {
      const p = byId(id);
      if (!p || !Number.isInteger(qty) || qty < 1 || qty > MAX_QTY) continue;
      quantity += qty;
      lines.push([qty, Number.isInteger(p.price_cents) ? p.price_cents : null, !!p.discount_ok]);
      if (Number.isInteger(p.price_cents)) known += p.price_cents * qty; else quote++;
    }
    const terms = window.ELTerms ? window.ELTerms.calc(lines, window.ELTerms.getCollective()) : null;  // Sammelbestellung gilt nur unter dem Mindestbestellwert; calc verwirft den Wunsch sonst selbst
    return {known_total_cents: known, quote_items: quote, quantity, total_cents: quote ? null : known, terms, payable_cents: terms ? terms.payable_cents : (quote ? null : known)};
  }
  /* Eine Summenfunktion fuer Warenkorb, Telegram-MainButton und Leerzustand: leerer Warenkorb = 0, mit Preis auf Anfrage nur die bekannte Summe, sonst Zahlbetrag nach Rabatt */
  const totalCents = sum => (!sum.quantity ? 0 : sum.quote_items || !sum.terms ? sum.known_total_cents : sum.payable_cents);
  const groupCount = list => new Set(list.map(p => p.group || p.id)).size;
  function navigation(noBanner) {
    const packTotal = formats.filter(isPack).length + extraPacks.length;
    return `<nav class="format-tabs" aria-label="${esc(t('shop.choose'))}"><a href="#products/vial">${esc(t('shop.navVials'))}<span>${groupCount(vials)}</span></a><a href="#dual-chamber">${esc(t('shop.dual'))}<span>${groupCount(formats.filter(p=>p.format==='dual_chamber'))}</span></a><a href="#accessories">${esc(t('shop.pen'))}<span>1</span></a><a href="#packs">${esc(t('shop.navPacks'))}<span>${packTotal}</span></a></nav>${noBanner ? '' : `<a class="pack-banner" href="#packs" data-pack-open data-pack-section=""><strong>${esc(t('pk.bannerTitle', {n: packTotal}))}</strong><span>${esc(t('pk.bannerText'))}</span></a>`}`;
  }
  function cards(kind) {
    const matches = formats.filter(p => (kind === 'pack' ? isPack(p) && (!packType || p.format === packType) : p.format === kind) && (!category || p.category === category) && (!query || match(p.name + ' ' + p.concentration, query)));
    return matches.length ? matches.map(p => `<article class="format-card"><a class="format-image" href="#product=${encodeURIComponent(p.link || p.id)}"><img src="${esc(p.image)}" width="720" height="510" loading="lazy" decoding="async" alt="${esc(p.name)} ${esc(p.concentration)} · ${esc(kindLabel(p))} · ${esc(t('shop.schematic'))}"></a><div class="format-card-body"><span class="format-tag">${esc(kindLabel(p))}</span><h2><a href="#product=${encodeURIComponent(p.link || p.id)}">${esc(p.name)}</a></h2><p class="format-strength">${esc(p.concentration)}</p><div class="format-card-foot"><strong>${esc(price(p))}${isPack(p) ? `<small class="pack-unit">${esc(unitPrice(p))} ${esc(t('shop.packEach'))}</small>` : ''}</strong><button type="button" class="primary-btn" data-add="${esc(p.id)}" aria-label="${esc(t('shop.add'))}: ${esc(p.name)} ${esc(p.concentration)}">＋</button></div></div></article>`).join('') : `<p class="catalog-empty">${esc(t('shop.noResults'))}</p>`;
  }
  function page(kind) {
    if (activeKind !== kind) { query = ''; category = ''; activeKind = kind; }
    const list = formats.filter(p => p.format === kind), categories = [...new Set(list.map(p => p.category))];
    const title = kind === 'pen' ? 'shop.pen' : 'shop.duals';
    return `<section class="section format-page"><div class="eyebrow">ELEMENTS LABS · ${esc(t('shop.ranges'))}</div><h1 class="page-title">${esc(t(title))}<span class="format-heading-count">${list.length}</span></h1><p class="lead">${esc(t('shop.lead'))}</p>${navigation()}<div class="format-toolbar"><label class="format-search"><span class="visually-hidden">${esc(t('shop.search'))}</span><input id="formatSearch" type="search" placeholder="${esc(t('shop.search'))}" value="${esc(query)}"></label><label><span class="visually-hidden">${esc(t('shop.all'))}</span><select id="formatCategory"><option value="">${esc(t('shop.all'))}</option>${categories.map(c=>`<option value="${esc(c)}"${category===c?' selected':''}>${esc(t('cat.'+c))}</option>`).join('')}</select></label></div><div class="format-grid" id="formatGrid" data-kind="${kind}">${cards(kind)}</div><p class="format-footnote">${esc(t('shop.schematic'))}. ${esc(t('shop.details'))}</p></section>`;
  }
  function detail(id) {
    const p = formats.find(x=>x.id===id);
    if (!p) return '';
    const others = formats.filter(x=>x.group===p.group&&x.format===p.format);
    return `<section class="section format-detail"><a class="secondary-btn" href="#${p.format==='pen'?'accessories':'dual-chamber'}">← ${esc(t('shop.back'))}</a><div class="detail-layout"><div class="gallery"><img class="format-detail-image" src="${esc(p.image)}" width="720" height="510" alt="${esc(p.name)} · ${esc(t('shop.schematic'))}"><p class="format-footnote">${esc(t('shop.schematic'))}</p></div><aside class="purchase"><div class="eyebrow">ELEMENTS LABS · ${esc(kindLabel(p))}</div><h1>${esc(p.name)}</h1><p class="lead">${esc(p.concentration)}</p><div class="format-detail-price">${esc(price(p))}</div>${others.length>1?`<div class="variant-options" role="group" aria-label="${esc(t('detail.chooseSize'))}">${others.map(x=>`<a class="variant-opt${x.id===id?' active':''}" href="#product=${encodeURIComponent(x.id)}" aria-current="${x.id===id?'true':'false'}">${esc(x.concentration)}</a>`).join('')}</div>`:''}<dl class="format-specs"><div><dt>${esc(t('shop.format'))}</dt><dd>${esc(kindLabel(p))}</dd></div><div><dt>${esc(t('detail.concentration'))}</dt><dd>${esc(p.concentration)}</dd></div></dl><button class="primary-btn format-add" data-add="${esc(p.id)}">${esc(t('shop.add'))}</button><p class="format-footnote">${esc(t('shop.details'))}</p><a class="source-link" href="#cart">${esc(t('nav.cart'))} →</a></aside></div></section>`;
  }
  function cartPage() {
    const items = Object.entries(cart).map(([id, qty])=>({p:byId(id),qty})).filter(x=>x.p);
    const sum = summary(cart);
    return `<section class="section quote-cart"><div class="eyebrow">ELEMENTS LABS · ${esc(t('shop.request'))}</div><h1 class="page-title">${esc(t('nav.cart'))}<span class="format-heading-count">${sum.quantity}</span></h1><p class="lead">${esc(t('shop.cartLead'))}</p><div class="quote-layout"><div class="quote-lines">${items.length?items.map(({p,qty})=>`<article class="quote-line"><img src="${esc(p.thumb||p.image||packIcon(p))}" width="96" height="96" alt="${esc(p.name)}" loading="${p.thumb||p.image?'lazy':'eager'}"><div class="quote-line-copy"><span class="format-tag">${esc(kindLabel(p))}</span>${isPack(p) && !p.discount_ok ? `<span class="format-tag tag-nodisc">${esc(t('shop.noDiscount'))}</span>` : ''}<h2><a href="${p.catalog_only ? '#packs' : '#product=' + encodeURIComponent(p.link || p.id)}"${p.catalog_only ? ` data-pack-open data-pack-section="" data-pack-query="${esc((p.line_name || p.name) + ' ' + (p.line_strength || p.concentration))}"` : ''}>${esc(p.format==='pen'?t('format.pen'):p.name)}</a></h2><p>${esc(p.format==='pen'?'':p.concentration)}</p><strong>${esc(price(p))}</strong>${qty > 1 && Number.isInteger(p.price_cents) ? `<span class="line-total"><small>${esc(t('shop.lineTotal'))}</small> ${esc(fmt(p.price_cents * qty / 100))}</span>` : ''}<div class="qty"><button data-qty="${esc(p.id)}" data-delta="-1" aria-label="− ${esc(p.name)}">−</button><span aria-label="${esc(t('shop.quantity'))}">${qty}</span><button data-qty="${esc(p.id)}" data-delta="1" aria-label="＋ ${esc(p.name)}">＋</button></div></div><button class="ghost-btn quote-remove" data-remove="${esc(p.id)}" aria-label="${esc(t('shop.remove'))}: ${esc(p.name)}">×</button></article>`).join(''):`<div class="catalog-empty"><p>${esc(t('shop.empty'))}</p><a class="primary-btn" href="#products">${esc(t('shop.continue'))}</a></div>`}</div><aside class="quote-summary"><h2>${esc(t('shop.request'))}</h2>${window.ELTerms ? window.ELTerms.panel(sum) : ''}<div class="quote-total-label">${esc(t(sum.quote_items?'shop.known':'shop.total'))}</div><div class="total" id="cartTotal">${esc(fmt(totalCents(sum)/100))}</div>${sum.quote_items?`<p class="quote-price-note">＋ ${sum.quote_items} ${esc(t('shop.extra'))}</p>`:''}<p class="compound-meta">${esc(t('cart.vatNote'))}</p><button class="primary-btn" id="checkoutBtn"${items.length&&!(window.ELTerms&&window.ELTerms.blocked(sum))?'':' disabled'}>${esc(items.length&&window.ELTerms&&window.ELTerms.blocked(sum)?t('tm.minSend'):t('mini.send'))}</button><p class="format-footnote">${esc(t('shop.details'))}</p><div id="orderFeedback" role="status" aria-live="polite"></div></aside></div>${navigation()}</section>`;
  }
  const packIcon = p => 'data:image/svg+xml;utf8,' + encodeURIComponent(p.format === 'dual_pack' ? '<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 96 96"><rect width="96" height="96" fill="#f1f6f7"/><g fill="none" stroke="#0D5B6B" stroke-width="3"><rect x="34" y="10" width="28" height="76" rx="5"/><path d="M34 48h28M40 10V4h16v6"/></g></svg>' : '<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 96 96"><rect width="96" height="96" fill="#f1f6f7"/><g fill="none" stroke="#0D5B6B" stroke-width="3"><rect x="32" y="22" width="32" height="64" rx="5"/><path d="M38 22v-8h20v8M32 40h32"/></g></svg>');
  const centsOf = text => parseInt(String(text).replace(/\D/g, ''), 10) || 0;
  const packOf = p => { const pack = all.find(x => x.id === p.id + '-x10'); return pack && Number.isInteger(pack.price_cents) && pack.pack_size > 0 ? pack : null; };
  const tv = () => (window.ELTerms ? window.ELTerms.vars() : {});
  const packNote = () => t('shop.packNote', tv());
  /* Zeile direkt unter dem Einzelpreis: "<Ausführung> <Name> <Stärke>: 10er-Pack <Preis>, <Preis je Stück> je Stück". Ohne 10er-Pack: leer. */
  function packPriceLine(p) {
    const pack = packOf(p);
    if (!pack) return '';
    const label = [t(p.form === 'dual' ? 'shop.dual' : 'shop.vial'), p.name, p.concentration].join(' ');
    return `<p class="price-pack" data-pack="${esc(pack.id)}">${esc(t('shop.under10', {label, pack: price(pack), unit: unitPrice(pack)}))}</p>`;
  }
  /* Doppelkammer-Seite: "inklusive Pen" direkt am Preis; danach die 10er-Zeile. Beides unter dem Preis, vor Ausführungs- und Stärkenwahl. */
  function priceExtras(p) {
    const html = (p.form === 'dual' ? `<p class="pen-included">${esc(t('shop.penIncluded'))}</p>` : '') + packPriceLine(p);
    return html ? `<div class="price-extras">${html}</div>` : '';
  }
  function penIncluded() {
    const pen = formats.find(x => x.format === 'pen');
    return `<div class="optional-pen pen-included-block">${pen ? `<img src="${esc(pen.thumb || pen.image)}" alt="${esc(pen.name)}">` : ''}<div><strong>${esc(t('shop.penIncludedTitle'))}</strong><p>${esc(t('shop.penIncludedText'))}</p><a href="#product=mehrweg-pen">${esc(t('format.penDetails'))}</a></div></div>`;
  }
  function packBlock(p) {
    const pack = packOf(p);
    if (!pack) return '';
    const single = centsOf(p.price), each = pack.price_cents / pack.pack_size;
    const save = single > 0 && each < single ? Math.round((1 - each / single) * 100) : 0;
    const discount = `<p class="pack-discount${pack.discount_ok ? '' : ' pack-discount-no'}">${esc(pack.discount_ok ? t('shop.packDiscountOk', tv()) : t('shop.packDiscountNo'))}</p>`;
    const pen = p.form === 'dual' ? `<p class="format-footnote">${esc(t('shop.packPenNote'))}</p>` : '';
    return `<div class="pack-offer"><div class="pack-offer-head"><span class="format-tag">${esc(t('shop.packOffer'))}</span><strong class="pack-offer-price">${esc(price(pack))}</strong></div><p class="pack-offer-unit">${esc(unitPrice(pack))} ${esc(t('shop.packEach'))}${save ? ` · ${save} % ${esc(t('shop.packSave'))}` : ''}</p>${discount}${pen}<button type="button" class="secondary-btn pack-add" data-add="${esc(pack.id)}">${esc(t('shop.packAdd'))}</button><p class="format-footnote">${esc(packNote())}</p></div>`;
  }
  const SECTIONS = ['Gewichtsmanagement & Fettreduktion', 'Regeneration & Reparatur', 'Beauty & Anti-Aging', 'Schlaf & Nervensystem', 'Hormone & Wachstum', 'Immunsystem & Organregulation', 'Peptid-Blends', 'Lösungsmittel & Ergänzungen'];
  const SECTION_FR = ['Gestion du poids & réduction des graisses', 'Réparation & récupération', 'Beauté & anti-âge', 'Sommeil & système nerveux', 'Hormones & croissance', 'Immunité & soutien des organes', 'Mélanges de peptides', 'Solvants & compléments'];
  const SECTION_EN = ['Weight management & fat reduction', 'Repair & recovery', 'Beauty & anti-aging', 'Sleep & nervous system', 'Hormones & growth', 'Immune & organ support', 'Peptide blends', 'Solvents & supplements'];
  const packList = [...formats.filter(isPack), ...extraPacks].sort((a, b) => (a.order ?? 9999) - (b.order ?? 9999));
  const dictPk = {
    de: {'pk.eyebrow': 'KOMPLETTKATALOG · 10ER-PACKS',
      'pk.title': '10er-Packs im Direktbezug',
      'pk.lead': 'Alle {n} Pack-Artikel in {m} Bereichen. Jeder Preis gilt für 10 Stück derselben Substanz, Stoffmenge und Ausführung; der Preis je Stück steht darunter. Die Doppelkammer ist inklusive Pen. Einzelpreise findest du unter „Vials“ und „Doppelkammer“.',
      'pk.statVial': 'Vial-Packs',
      'pk.statDual': 'Doppelkammer-Packs',
      'pk.statSub': 'Substanzen',
      'pk.statSec': 'Bereiche',
      'pk.all': 'Alle',
      'pk.vial': 'Vial',
      'pk.dual': 'Doppelkammer',
      'pk.allSections': 'Alle Bereiche',
      'pk.search': 'Substanz suchen',
      'pk.results': '{n} Artikel · {m} Substanz-Zeilen',
      'pk.none': 'Keine Treffer. Suchbegriff oder Filter ändern.',
      'pk.col': 'Produkt',
      'pk.type': 'Ausführung',
      'pk.section': 'Bereich',
      'pk.per10': '10er-Pack',
      'pk.teaserTitle': 'Mehr als {n} Packs im Komplettkatalog',
      'pk.teaserLead': 'Suche nach einer Substanz und vergleiche die angebotenen Vial- und Doppelkammer-Ausführungen (Doppelkammer inklusive Pen). Preis je 10er-Pack und je Stück auf einen Blick.',
      'pk.teaserCta': 'Komplettkatalog öffnen',
      'pk.bannerTitle': 'Komplettkatalog: {n} Packs',
      'pk.bannerText': 'Vials und Doppelkammern inklusive Pen · Preis je Pack und je Stück →'},
    en: {'pk.eyebrow': 'FULL CATALOGUE · 10-PACKS',
      'pk.title': '10-packs, direct sourcing',
      'pk.lead': 'All {n} pack items in {m} areas. Every price covers 10 pieces of the same compound, amount and format; the price per piece is shown below it. The dual chamber includes a pen. Single prices are under “Vials” and “Dual chamber”.',
      'pk.statVial': 'Vial packs',
      'pk.statDual': 'Dual-chamber packs',
      'pk.statSub': 'Substances',
      'pk.statSec': 'Areas',
      'pk.all': 'All',
      'pk.vial': 'Vial',
      'pk.dual': 'Dual chamber',
      'pk.allSections': 'All areas',
      'pk.search': 'Search substance',
      'pk.results': '{n} items · {m} substance rows',
      'pk.none': 'No matches. Change the search or filter.',
      'pk.col': 'Product',
      'pk.type': 'Format',
      'pk.section': 'Area',
      'pk.per10': '10-pack',
      'pk.teaserTitle': 'More than {n} packs in the full catalogue',
      'pk.teaserLead': 'Search for a substance and compare the vial and dual-chamber formats on offer (dual chamber with pen included). Price per 10-pack and per piece at a glance.',
      'pk.teaserCta': 'Open full catalogue',
      'pk.bannerTitle': 'Full catalogue: {n} packs',
      'pk.bannerText': 'Vials and dual chambers with pen included · price per pack and per piece →'},
    fr: {'pk.eyebrow': 'CATALOGUE COMPLET · PACKS DE 10',
      'pk.title': 'Packs de 10 en achat direct',
      'pk.lead': 'Les {n} packs dans {m} domaines. Chaque prix couvre 10 pièces de la même substance, quantité et version ; le prix à la pièce figure en dessous. La double chambre inclut un stylo. Les prix à l’unité sont sous « Flacons » et « Double chambre ».',
      'pk.statVial': 'Packs flacons',
      'pk.statDual': 'Packs doubles chambres',
      'pk.statSub': 'Substances',
      'pk.statSec': 'Domaines',
      'pk.all': 'Tous',
      'pk.vial': 'Flacon',
      'pk.dual': 'Double chambre',
      'pk.allSections': 'Tous les domaines',
      'pk.search': 'Chercher une substance',
      'pk.results': '{n} articles · {m} lignes de substance',
      'pk.none': 'Aucun résultat. Modifiez la recherche ou le filtre.',
      'pk.col': 'Produit',
      'pk.type': 'Version',
      'pk.section': 'Domaine',
      'pk.per10': 'Pack de 10',
      'pk.teaserTitle': 'Plus de {n} packs dans le catalogue complet',
      'pk.teaserLead': 'Cherchez une substance et comparez les versions flacon et double chambre proposées (double chambre, stylo inclus). Prix par pack de 10 et à la pièce en un coup d’œil.',
      'pk.teaserCta': 'Ouvrir le catalogue complet',
      'pk.bannerTitle': 'Catalogue complet : {n} packs',
      'pk.bannerText': 'Flacons et doubles chambres, stylo inclus · prix par pack et à la pièce →'}
  };
  for (const lang of Object.keys(dictPk)) {
    Object.assign(window.__EL_I18N__[lang], dictPk[lang]);
    SECTIONS.forEach((name, k) => { window.__EL_I18N__[lang]['sec.' + name] = lang === 'de' ? name : (lang === 'fr' ? SECTION_FR : SECTION_EN)[k]; });
  }
  const secLabel = name => t('sec.' + name);
  let packSection = '', pendingSection = '', pendingQuery = '';
  function packRows() {
    const map = new Map();
    for (const p of packList) {
      const name = p.line_name || p.name, strength = p.line_strength || p.concentration, key = p.section + '|' + name + '|' + strength;
      let r = map.get(key);
      if (!r) { r = {key, name, strength, section: p.section, order: p.order ?? 9999, link: '', vial: null, dual: null}; map.set(key, r); }
      r.order = Math.min(r.order, p.order ?? 9999);
      if (p.format === 'vial_pack') r.vial = p; else r.dual = p;
      if (p.base_product_id && !r.link) r.link = p.base_product_id;
    }
    return [...map.values()].sort((a, b) => a.order - b.order);
  }
  const substanceOf = name => name.replace(/\s*\(.*$/, '').replace(/\s*\+.*$/, '').trim();
  function packStats() {
    const rows = packRows();
    return {rows, vials: packList.filter(p => p.format === 'vial_pack').length, duals: packList.filter(p => p.format === 'dual_pack').length,
      subs: new Set(rows.map(r => substanceOf(r.name).toLowerCase())).size, sections: SECTIONS.filter(sec => rows.some(r => r.section === sec))};
  }
  function packCell(p, label) {
    if (!p) return '<span class="pack-cell pack-cell-na" aria-hidden="true">–</span>';
    const flag = p.discount_ok ? '' : `<em class="pack-nodisc">${esc(t('shop.noDiscount'))}</em>`;
    return `<button type="button" class="pack-cell" data-add="${esc(p.id)}" aria-label="${esc(label)} ${esc(p.line_name || p.name)} ${esc(p.line_strength || p.concentration)} · ${esc(t('pk.per10'))} ${esc(price(p))} · ${esc(unitPrice(p))} ${esc(t('shop.packEach'))}${p.discount_ok ? '' : ' · ' + esc(t('shop.noDiscount'))} · ${esc(t('shop.packAdd'))}"><small>${esc(label)}</small><strong>${esc(price(p))}<small class="pack-unit">${esc(unitPrice(p))} ${esc(t('shop.packEach'))}</small></strong>${flag}<span class="pack-plus" aria-hidden="true">+</span></button>`;
  }
  function packRow(r) {
    const nameHtml = r.link ? `<a href="#product=${encodeURIComponent(r.link)}">${esc(r.name)}</a>` : esc(r.name);
    const showVial = !packType || packType === 'vial_pack', showDual = !packType || packType === 'dual_pack';
    return `<div class="pack-row"><div class="pack-name"><strong>${nameHtml}</strong><span>${esc(r.strength)}</span></div>${showVial ? packCell(r.vial, t('pk.vial')) : ''}${showDual ? packCell(r.dual, t('shop.dualPen')) : ''}</div>`;
  }
  function packFiltered() {
    const q = query.trim().toLowerCase();
    return packRows().filter(r => (!packType || r[packType === 'vial_pack' ? 'vial' : 'dual']) && (!packSection || r.section === packSection) && (!q || match(r.name + ' ' + r.strength, q)));
  }
  function packListHtml() {
    const rows = packFiltered();
    const cells = rows.reduce((n, r) => n + (packType === 'vial_pack' ? 1 : packType === 'dual_pack' ? 1 : (r.vial ? 1 : 0) + (r.dual ? 1 : 0)), 0);
    const html = rows.length ? SECTIONS.map(sec => {
      const part = rows.filter(r => r.section === sec);
      return part.length ? `<section class="pack-group"><h2>${esc(secLabel(sec))}<span>${part.reduce((n, r) => n + (packType === 'vial_pack' ? (r.vial ? 1 : 0) : packType === 'dual_pack' ? (r.dual ? 1 : 0) : (r.vial ? 1 : 0) + (r.dual ? 1 : 0)), 0)}</span></h2><div class="pack-head" aria-hidden="true"><span>${esc(t('pk.col'))}</span>${!packType || packType === 'vial_pack' ? `<span>${esc(t('pk.vial'))} · 10er</span>` : ''}${!packType || packType === 'dual_pack' ? `<span>${esc(t('pk.dual'))} · 10er</span>` : ''}</div>${part.map(packRow).join('')}</section>` : '';
    }).join('') : `<p class="pack-none">${esc(t('pk.none'))}</p>`;
    return {html, count: t('pk.results', {n: cells, m: rows.length})};
  }
  function packsPage() {
    if (activeKind !== 'pack') { query = pendingQuery; packType = ''; packSection = pendingSection; activeKind = 'pack'; }
    pendingSection = ''; pendingQuery = '';
    const st = packStats(), list = packListHtml();
    const chip = (attr, value, label, on) => `<button type="button" class="pack-chip" data-pack-${attr}="${esc(value)}" aria-pressed="${on ? 'true' : 'false'}">${esc(label)}</button>`;
    return `${window.ELTerms ? window.ELTerms.strip() : ''}<section class="section format-page packs-page"><header class="format-hero"><div class="eyebrow">${esc(t('pk.eyebrow'))}</div><h1 class="page-title">${esc(t('pk.title').replace(/10er-/g, '10er\u2011').replace(/10-/g, '10\u2011'))}<span class="format-heading-count">${packList.length}</span></h1><p class="lead">${esc(t('pk.lead', {n: packList.length, m: st.sections.length}))}</p><ul class="pack-stats"><li><strong>${st.vials}</strong><span>${esc(t('pk.statVial'))}</span></li><li><strong>${st.duals}</strong><span>${esc(t('pk.statDual'))}</span></li><li><strong>${st.subs}</strong><span>${esc(t('pk.statSub'))}</span></li><li><strong>${st.sections.length}</strong><span>${esc(t('pk.statSec'))}</span></li></ul>${navigation(true)}</header><div class="pack-toolbar"><label class="format-search"><span class="visually-hidden">${esc(t('pk.search'))}</span><input id="packSearch" type="search" placeholder="${esc(t('pk.search'))}" value="${esc(query)}" autocomplete="off"></label><div class="pack-chips pack-types" role="group" aria-label="${esc(t('pk.type'))}">${chip('type', '', t('pk.all'), !packType)}${chip('type', 'vial_pack', t('pk.vial'), packType === 'vial_pack')}${chip('type', 'dual_pack', t('pk.dual'), packType === 'dual_pack')}</div><div class="pack-chips pack-sections" role="group" aria-label="${esc(t('pk.section'))}">${chip('section', '', t('pk.allSections'), !packSection)}${st.sections.map(sec => chip('section', sec, secLabel(sec), packSection === sec)).join('')}</div></div><p class="result-count" id="packCount" aria-live="polite">${esc(list.count)}</p><div class="pack-list" id="packList">${list.html}</div><p class="format-footnote">${esc(packNote())}</p></section>`;
  }
  function catalogTeaser() {
    const st = packStats();
    const total = packList.length;
    const count = sec => packList.filter(p => p.section === sec).length;
    return `<section class="section pack-teaser"><div class="eyebrow">${esc(t('pk.eyebrow'))}</div><h2>${esc(t('pk.teaserTitle', {n: Math.floor(total / 10) * 10}))}</h2><p class="lead">${esc(t('pk.teaserLead'))}</p><ul class="pack-stats"><li><strong>${st.vials}</strong><span>${esc(t('pk.statVial'))}</span></li><li><strong>${st.duals}</strong><span>${esc(t('pk.statDual'))}</span></li><li><strong>${st.subs}</strong><span>${esc(t('pk.statSub'))}</span></li></ul><div class="pack-teaser-sections">${st.sections.map(sec => `<a href="#packs" data-pack-open data-pack-section="${esc(sec)}">${esc(secLabel(sec))}<span>${count(sec)}</span></a>`).join('')}</div><a class="primary-btn" href="#packs" data-pack-open data-pack-section="">${esc(t('pk.teaserCta'))}</a></section>`;
  }
  function rerenderPacks() {
    const host = document.getElementById('packList');
    if (!host) return;
    const list = packListHtml();
    host.innerHTML = list.html;
    const count = document.getElementById('packCount');
    if (count) count.textContent = list.count;
    document.querySelectorAll('[data-pack-type]').forEach(b => b.setAttribute('aria-pressed', b.dataset.packType === packType ? 'true' : 'false'));
    document.querySelectorAll('[data-pack-section]').forEach(b => { if (!b.hasAttribute('data-pack-open')) b.setAttribute('aria-pressed', b.dataset.packSection === packSection ? 'true' : 'false'); });
    host.querySelectorAll('[data-add]').forEach(b => b.onclick = () => addToCart(b.dataset.add));
  }
  if (typeof window.addEventListener === 'function') {
    // Filter bleiben beim Wechsel zu Produkt/Warenkorb und zurueck erhalten, jede andere Seite setzt sie zurueck
    window.addEventListener('hashchange', () => { if (!/^#(packs|product=|cart)/.test(location.hash)) activeKind = ''; });
  }
  if (typeof document.addEventListener === 'function') {
    document.addEventListener('input', event => {
      if (!event.target.matches || !event.target.matches('#packSearch')) return;
      query = event.target.value.slice(0, 80);
      rerenderPacks();
    });
    document.addEventListener('click', event => {
      const el = event.target.closest ? event.target.closest('[data-pack-type],[data-pack-section]') : null;
      if (!el) return;
      if (el.hasAttribute('data-pack-open')) { pendingSection = el.dataset.packSection || ''; pendingQuery = el.dataset.packQuery || ''; activeKind = ''; return; }
      if (!document.getElementById('packList')) return;
      if (el.hasAttribute('data-pack-type')) packType = el.dataset.packType; else packSection = el.dataset.packSection;
      event.preventDefault();
      rerenderPacks();
    });
  }
  /* Leere Trefferliste im Vial-/Doppelkammer-Katalog: Hinweis plus Link in die 10er-Packs mit demselben Suchbegriff */
  function emptyProducts(q) {
    const term = String(q || '').trim().slice(0, 80);
    return `<p class="compound-meta">${esc(t('products.noResults'))}</p>${term ? `<a class="secondary-btn" href="#packs" data-pack-open data-pack-section="" data-pack-query="${esc(term)}">${esc(t('shop.searchInPacks', {q: term}))}</a>` : ''}`;
  }
  function bindPage() {
    const input = document.getElementById('formatSearch'), select = document.getElementById('formatCategory'), grid = document.getElementById('formatGrid');
    if (input && select && grid) {
      const refresh = () => {query=input.value.slice(0,80);category=select.value;grid.innerHTML=cards(grid.dataset.kind);grid.querySelectorAll('[data-add]').forEach(b=>b.onclick=()=>addToCart(b.dataset.add));};
      input.oninput=refresh;select.onchange=refresh;
    }
    if (window.ELTerms) window.ELTerms.bind();
    if (!maxQtyBound) {  // Menge steht schon an der Obergrenze: kurze Rueckmeldung (Capture, laeuft vor dem Handler aus app.js)
      maxQtyBound = true;
      document.addEventListener('click', e => {
        const b = e.target.closest && e.target.closest('[data-add],[data-qty]');
        if (b && (b.dataset.add || Number(b.dataset.delta) > 0) && (cart[b.dataset.add || b.dataset.qty] || 0) >= MAX_QTY) toast(t('shop.maxQty', {max: MAX_QTY}));
      }, true);
    }
    const hash=(location.hash==='#products/dual'?'#dual-chamber':location.hash)||'#home';
    document.querySelectorAll('.format-tabs a').forEach(a=>{if(a.getAttribute('href')===hash)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});

  }
  return {pickVariant, byId, summary, totalCents, match, page, detail, cartPage, bind:bindPage, navigation, packBlock, priceExtras, penIncluded, emptyProducts, packsPage, catalogTeaser, formatPrice};
})();
