/* Konditionen (Inhaber 24.10.2026): Mindestbestellwert = Direktlieferung, Versand immer inklusive, Sammelbestellung nur unterhalb des
   Mindestbestellwerts, Mengenrabatt nur auf rabattfaehige 10er-Packs. Rechnet identisch zu terms.py (tests/test_terms.py prueft die Paritaet).
   Alle Betraege in Cent. Alle Zahlen in Texten kommen aus data/terms.json (#termsData), nie aus Textliteralen. */
window.ELTerms = (() => {
  const el = document.getElementById('termsData');
  const terms = el ? JSON.parse(el.textContent) : {min_order_cents: 0, collective_min_cents: 0, delivery_weeks: {min: 2, max: 3}, tiers: []};
  const KEY = 'elementsCollective';
  /* Texte mit Platzhaltern, die erst beim Aufruf gefuellt werden (t(key, vars)) */
  const dict = {
      "de": {
          "tm.sub": "Zwischensumme",
          "tm.discountOn": "Mengenrabatt {p} % auf {base}",
          "tm.shipLabel": "Versand",
          "tm.shipIncl": "inklusive",
          "tm.collectiveShip": "Sammelversand",
          "tm.min": "Mindestbestellwert {min}: noch {x} fehlen. Alternativ Sammelbestellung ab {cmin}.",
          "tm.minCollective": "Sammelbestellung ab {cmin}: noch {x} fehlen.",
          "tm.tier": "Noch {x} bis {p} % Mengenrabatt auf rabattfähige 10er-Packs",
          "tm.tierScope": "Die Stufe zählt den gesamten Warenwert. Rabatt gibt es nur auf 10er-Packs ohne den Hinweis „ohne Mengenrabatt“.",
          "tm.tierNone": "Mengenrabatt-Stufe {p} % erreicht, aber kein rabattfähiger 10er-Pack im Warenkorb: Rabatt 0,00 €.",
          "tm.collective": "Sammelbestellung",
          "tm.collectiveNote": "Für Warenwerte von {cmin} bis unter {min}: versandkostenfrei, gebündelte Lieferung mit weiteren Bestellungen. Ab {min} liefern wir direkt.",
          "tm.blocked": "Bitte den Mindestbestellwert erreichen oder Sammelbestellung wählen.",
          "tm.minSend": "Mindestbestellwert noch nicht erreicht",
          "s.min": "Mindestbestellwert {min} · Versand inklusive",
          "s.tier": "{p} % Mengenrabatt ab {x}",
          "s.time": "Lieferzeit {wk} Wochen",
          "s.group": "Sammelbestellung {cmin} bis unter {min}"
      },
      "en": {
          "tm.sub": "Subtotal",
          "tm.discountOn": "Volume discount {p} % on {base}",
          "tm.shipLabel": "Shipping",
          "tm.shipIncl": "included",
          "tm.collectiveShip": "Group shipping",
          "tm.min": "Minimum order {min}: {x} missing. Alternatively, a group order from {cmin}.",
          "tm.minCollective": "Group order from {cmin}: {x} missing.",
          "tm.tier": "{x} more for {p} % volume discount on eligible 10-packs",
          "tm.tierScope": "The tier counts your whole order value. The discount applies only to 10-packs without the note “no volume discount”.",
          "tm.tierNone": "The {p} % tier is reached, but there is no eligible 10-pack in your cart: discount 0,00 €.",
          "tm.collective": "Group order",
          "tm.collectiveNote": "For order values from {cmin} to under {min}: shipping included, delivered together with other orders. From {min} we ship directly.",
          "tm.blocked": "Please reach the minimum order value or choose a group order.",
          "tm.minSend": "Minimum order not reached yet",
          "s.min": "Minimum order {min} · shipping included",
          "s.tier": "{p} % volume discount from {x}",
          "s.time": "Delivery in {wk} weeks",
          "s.group": "Group order {cmin} to under {min}"
      },
      "fr": {
          "tm.sub": "Sous-total",
          "tm.discountOn": "Remise quantité {p} % sur {base}",
          "tm.shipLabel": "Livraison",
          "tm.shipIncl": "incluse",
          "tm.collectiveShip": "Livraison groupée",
          "tm.min": "Commande minimum {min} : il manque {x}. Sinon, commande groupée dès {cmin}.",
          "tm.minCollective": "Commande groupée dès {cmin} : il manque {x}.",
          "tm.tier": "Encore {x} pour {p} % de remise sur les packs de 10 éligibles",
          "tm.tierScope": "Le palier compte la valeur totale de la commande. La remise ne s’applique qu’aux packs de 10 sans la mention « sans remise quantité ».",
          "tm.tierNone": "Palier de {p} % atteint, mais aucun pack de 10 éligible dans le panier : remise 0,00 €.",
          "tm.collective": "Commande groupée",
          "tm.collectiveNote": "Pour des commandes de {cmin} à moins de {min} : livraison incluse, expédition groupée avec d’autres commandes. Dès {min}, nous livrons directement.",
          "tm.blocked": "Atteignez la commande minimum ou choisissez la commande groupée.",
          "tm.minSend": "Commande minimum non atteinte",
          "s.min": "Commande minimum {min} · livraison incluse",
          "s.tier": "{p} % de remise dès {x}",
          "s.time": "Livraison en {wk} semaines",
          "s.group": "Commande groupée {cmin} à moins de {min}"
      }
  };
  /* Texte fuer unveraenderte Stellen in app.js/i18n.js: Konditionen werden beim Laden eingesetzt */
  const loadTexts = {
      "de": {
          "tab.shipP1": "Lieferzeit: {wk} Wochen (Direktbezug). Ab einem Warenwert von {min} liefern wir versandkostenfrei. Von {cmin} bis unter {min} ist eine Sammelbestellung möglich: versandkostenfrei, gebündelte Lieferung.",
          "faq.a1": "Du kannst deine Auswahl im Warenkorb als Testanfrage speichern. Zahlung und Außenversand gibt es in dieser Version noch nicht. Mindestbestellwert {min}, Versand inklusive, Lieferzeit {wk} Wochen.",
          "cart.vatNote": "Preise in Euro. Versand ab {min} Warenwert inklusive. Die Verfügbarkeit ist nicht bestätigt; Testversion ohne verbindlichen Kauf.",
          "detail.trust1": "Versand ab {min} inklusive",
          "detail.trust2": "Lieferzeit {wk} Wochen"
      },
      "en": {
          "tab.shipP1": "Delivery time: {wk} weeks (direct sourcing). From an order value of {min} we ship free of charge. From {cmin} to under {min} a group order is possible: shipping included, delivered together with other orders.",
          "faq.a1": "You can save your selection in the cart as a test request. This version has no payment and no external shipping yet. Minimum order {min}, shipping included, delivery in {wk} weeks.",
          "cart.vatNote": "Prices in euro. Shipping included from {min} order value. Availability is not confirmed; test version without a binding purchase.",
          "detail.trust1": "Shipping included from {min}",
          "detail.trust2": "Delivery in {wk} weeks"
      },
      "fr": {
          "tab.shipP1": "Délai de livraison : {wk} semaines (achat direct). Dès {min} de commande, la livraison est offerte. De {cmin} à moins de {min}, une commande groupée est possible : livraison incluse, expédition groupée.",
          "faq.a1": "Vous pouvez enregistrer votre sélection dans le panier comme demande test. Cette version ne comporte pas encore de paiement ni d’envoi externe. Commande minimum {min}, livraison incluse, délai {wk} semaines.",
          "cart.vatNote": "Prix en euros. Livraison incluse dès {min} de commande. La disponibilité n’est pas confirmée ; version test sans achat ferme.",
          "detail.trust1": "Livraison incluse dès {min}",
          "detail.trust2": "Livraison en {wk} semaines"
      }
  };
  const WORD = {de: 'ab', en: 'from', fr: 'dès'}, TO = {de: 'bis', en: 'to', fr: 'à'};
  const short = cents => (cents / 100).toLocaleString('de-DE', {minimumFractionDigits: cents % 100 ? 2 : 0, maximumFractionDigits: 2}) + '\u00a0€';
  const varsFor = lang => {
    const l = WORD[lang] ? lang : 'de', w = terms.delivery_weeks || {min: 2, max: 3};
    return {min: short(terms.min_order_cents), cmin: short(terms.collective_min_cents), wk: `${w.min} ${TO[l]} ${w.max}`,
      tiers: terms.tiers.map(x => `${x.percent} % ${WORD[l]} ${short(x.min_cents)}`).join(' · ')};
  };
  const vars = () => varsFor(typeof window.getLang === 'function' ? window.getLang() : 'de');
  const fill = (text, v) => String(text).replace(/\{(\w+)\}/g, (m, k) => (k in v ? v[k] : m));
  if (window.__EL_I18N__) for (const lang of Object.keys(dict)) if (window.__EL_I18N__[lang]) {
    Object.assign(window.__EL_I18N__[lang], dict[lang]);
    for (const [key, text] of Object.entries(loadTexts[lang] || {})) window.__EL_I18N__[lang][key] = fill(text, varsFor(lang));
  }
  const money = cents => fmt(cents / 100);
  const getCollective = () => { try { return window.ELStore.get(KEY) === '1'; } catch (e) { return false; } };
  const setCollective = on => { try { window.ELStore.set(KEY, on ? '1' : '0'); } catch (e) { /* storage unavailable */ } };
  function calc(lines, collective) {
    let subtotal = 0, eligible = 0, quote = 0;
    for (const [qty, cents, ok] of lines) {
      if (!Number.isInteger(cents)) { quote++; continue; }
      subtotal += qty * cents;
      if (ok) eligible += qty * cents;
    }
    const percent = terms.tiers.reduce((best, tier) => subtotal >= tier.min_cents ? Math.max(best, tier.percent) : best, 0);
    const discount = Math.floor(eligible * percent / 100);
    const net = subtotal - discount;
    const direct = subtotal >= terms.min_order_cents;
    const group = !!collective && !direct;
    const minimum = group ? terms.collective_min_cents : terms.min_order_cents;
    return {subtotal_cents: subtotal, eligible_cents: eligible, discount_percent: percent, discount_cents: discount, shipping_cents: 0, collective: group, direct,
      payable_cents: quote ? null : net, min_order_cents: minimum, min_ok: subtotal >= minimum, net_cents: net};
  }
  function nextTier(c) {
    return terms.tiers.filter(x => c.subtotal_cents < x.min_cents).sort((a, b) => a.min_cents - b.min_cents)[0] || null;
  }
  function panel(sum) {
    const c = sum.terms;
    if (!c || !sum.quantity) return '';
    const v = vars();
    const rows = [`<div><span>${esc(t('tm.sub'))}</span><b>${esc(money(c.subtotal_cents))}</b></div>`];
    if (c.discount_cents) rows.push(`<div class="tm-discount"><span>${esc(fill(t('tm.discountOn'), {p: c.discount_percent, base: money(c.eligible_cents)}))}</span><b>−${esc(money(c.discount_cents))}</b></div>`);
    rows.push(`<div><span>${esc(c.collective ? t('tm.collectiveShip') : t('tm.shipLabel'))}</span><b>${esc(t('tm.shipIncl'))}</b></div>`);
    const tier = nextTier(c);
    const hints = [];
    if (!c.min_ok) hints.push(`<p class="tm-warn" id="minOrderNote">${esc(fill(t(c.collective ? 'tm.minCollective' : 'tm.min'), {...v, x: money(c.min_order_cents - c.subtotal_cents)}))}</p>`);
    if (tier) hints.push(`<p class="tm-tier">${esc(fill(t('tm.tier'), {x: money(tier.min_cents - c.subtotal_cents), p: tier.percent}))}</p>`);
    if (c.discount_percent && !c.discount_cents) hints.push(`<p class="tm-tier">${esc(fill(t('tm.tierNone'), {p: c.discount_percent}))}</p>`);
    else if ((tier || c.discount_percent) && c.eligible_cents < c.subtotal_cents) hints.push(`<p class="tm-tier">${esc(t('tm.tierScope'))}</p>`);
    const group = c.direct ? '' : `<label class="tm-collective"><input type="checkbox" id="collectiveToggle"${getCollective() ? ' checked' : ''}><span><strong>${esc(t('tm.collective'))}</strong><small>${esc(fill(t('tm.collectiveNote'), v))}</small></span></label>`;
    return `<div class="tm-box"><div class="tm-lines">${rows.join('')}</div>${hints.join('')}${group}</div>`;
  }
  function bind() {
    const box = document.getElementById('collectiveToggle');
    if (box) box.onchange = () => { setCollective(box.checked); if (typeof window.render === 'function') window.render(); };
  }
  const blocked = sum => !!(sum && sum.terms && !sum.terms.min_ok);
  function strip() {
    const v = vars();
    const items = [fill(t('s.min'), v), ...terms.tiers.map(x => fill(t('s.tier'), {p: x.percent, x: short(x.min_cents)})), fill(t('s.time'), v), fill(t('s.group'), v)];
    return `<div class="tm-strip" role="list">${items.map(x => `<span role="listitem">${esc(x)}</span>`).join('')}</div>`;
  }
  return {terms, calc, panel, bind, strip, blocked, getCollective, setCollective, vars, short};
})();
