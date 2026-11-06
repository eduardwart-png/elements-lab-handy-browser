/* Official Telegram WebApp bridge + shop extras. Works without Telegram in preview mode. */
window.ELMini = (() => {
  const rawProducts = JSON.parse(document.getElementById('productData').textContent);
  const formatsElement = document.getElementById('formatData');
  const formatProducts = formatsElement ? JSON.parse(formatsElement.textContent) : [];
  const packElement = document.getElementById('packData');
  const packProducts = packElement ? JSON.parse(packElement.textContent) : [];
  const allProducts = [...rawProducts, ...(Array.isArray(formatProducts) ? formatProducts : []), ...(Array.isArray(packProducts) ? packProducts : [])];
  const allowed = new Set(allProducts.map(p => p.id));
  const catalogue = JSON.parse(document.getElementById('catalogData').textContent);
  const catalogIds = new Set(catalogue.items.map(p => p.id));
  const tg = window.Telegram?.WebApp;
  /* Crash reports go to the shop's own service log so a failure inside Telegram becomes visible to us. */
  document.addEventListener('error', e => {
    const img = e.target;
    if (img?.tagName === 'IMG' && /-card\.webp/.test(img.src) && !img.dataset.fallback) { img.dataset.fallback = '1'; img.src = img.src.replace('-card.webp', '.webp'); }
  }, true);
  let reported = 0;
  function report(message, source, line) {
    if (reported++ >= 5 || typeof fetch !== 'function') return;
    try {
      fetch('/api/client-error', {method: 'POST', keepalive: true, headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({m: String(message || '').slice(0, 160), s: String(source || '').slice(-60), l: Number.isInteger(line) ? line : 0,
          r: String(location.hash || '').slice(0, 60), p: tg?.platform || '', v: tg?.version || ''})}).catch(() => {});
    } catch (e) { /* reporting must never break the shop */ }
  }
  if (typeof window.addEventListener === 'function') {
    window.addEventListener('error', e => report(e.message, e.filename, e.lineno));
    window.addEventListener('unhandledrejection', e => report(e.reason?.message || e.reason, '', 0));
  }
  const WISH = 'elementsWishlist', HIST = 'elementsHistory';
  let orderTimeoutMs = 20000, mainAction = 'cart', mode = 'preview', busy = false, pending = null, botName = '', lastReceipt = null;
  const filter = {q: '', cat: ''};
  const trail = [];
  let lastRoute = '', listState = {}, scrollMemo = {};
  const canon = h => (h === '#products/dual' ? '#dual-chamber' : h);
  const LIST_ROUTE = /^#(products(\/(vial|dual))?|dual-chamber|packs)$/;
  /* Scrollposition je Liste: laufend mitschreiben (nicht erst beim hashchange lesen, dann hat der Browser sie teils schon
     zurueckgesetzt) und beim Zurueck so lange nachfuehren, bis das Layout steht. Eine Nutzergeste bricht das Nachfuehren ab. */
  let restoreStop = null, restoreRoute = '';
  const hereRoute = () => canon('#' + (launchRoute(location.hash) || 'home'));
  if (typeof window.addEventListener === 'function') {
    /* Zwischen Hashwechsel und Render gehoert scrollY noch zum alten DOM. Wiederherstellungswerte bleiben unveraendert. */
    window.addEventListener('scroll', () => {
      const here = hereRoute();
      if (!restoreStop && here === canon(lastRoute)) scrollMemo[here] = window.scrollY;
    }, {passive: true});
    window.addEventListener('hashchange', e => {
      try {
        const old = canon('#' + launchRoute(new URL(e.oldURL).hash));
        if (typeof scrollMemo[old] !== 'number') scrollMemo[old] = window.scrollY;
      } catch (err) { /* no scroll memo */ }
    });
  }
  document.addEventListener('click', e => {
    const here = hereRoute(), href = e.target.closest?.('a[href]')?.getAttribute('href');
    if (!LIST_ROUTE.test(here) || !href?.startsWith('#product=')) return;
    if (restoreStop) restoreStop();
    scrollMemo[here] = window.scrollY;
  }, true);
  function restoreScroll(top, route) {
    if (restoreStop) restoreStop();
    const jump = () => window.scrollTo({top, left: 0, behavior: 'instant'});
    jump();
    if (typeof requestAnimationFrame !== 'function' || typeof window.addEventListener !== 'function') return;
    const started = Date.now(), gestures = ['touchstart', 'wheel', 'mousedown', 'pointerdown', 'keydown'];
    let alive = true;
    const stop = () => {
      alive = false;
      gestures.forEach(name => window.removeEventListener(name, stop, true));
      if (restoreStop === stop) { restoreStop = null; restoreRoute = ''; }
    };
    gestures.forEach(name => window.addEventListener(name, stop, {capture: true, passive: true}));
    restoreStop = stop; restoreRoute = route;
    const step = () => {
      if (!alive) return;
      if (Math.abs(window.scrollY - top) > 1) jump();
      if (Date.now() - started < 2500) requestAnimationFrame(step); else stop();
    };
    requestAnimationFrame(step);
  }
  function rememberList() {
    const here = canon('#' + (launchRoute(location.hash) || 'home'));
    if (!LIST_ROUTE.test(here)) return;
    const value = id => document.getElementById(id)?.value || '';
    listState[here] = {q: value('searchInput'), cat: value('categoryFilter'), sort: value('sortFilter')};
    const canonical = '#' + (launchRoute(location.hash) || 'home');
  }
  function restoreList(raw, cameFromDetail) {
    const here = canon(raw), saved = listState[here];
    if (!cameFromDetail || !LIST_ROUTE.test(here)) return;
    if (saved) {  // Vial-/Doppelkammer-Katalog: Filter zurueckholen; #packs behaelt seine Filter in shop-formats.js
      const set = (id, v) => { const el = document.getElementById(id); if (el && v) el.value = v; };
      set('categoryFilter', saved.cat); set('sortFilter', saved.sort); set('searchInput', saved.q);
      const search = document.getElementById('searchInput');
      if (search && (saved.q || saved.cat || saved.sort)) search.dispatchEvent(new Event('input'));
    }
    const top = scrollMemo[here];
    if (typeof top === 'number') restoreScroll(top, here);
  }

  /* Telegram appends launch parameters (tgWebAppData, ...) to the URL fragment. Keep only the shop route. */
  function launchRoute(hash) {
    const parts = String(hash || '').replace(/^#/, '').split('&').filter(x => x && !x.startsWith('tgWebApp'));
    return parts.join('&');
  }
  /* Bot buttons carry the target as ?r=<route>: the query survives whatever Telegram does to the fragment. */
  function queryRoute(search) {
    const value = new URLSearchParams(search || '').get('r') || '';
    return /^[A-Za-z0-9=\/_-]{1,80}$/.test(value) ? value : '';
  }
  if (typeof location !== 'undefined' && typeof history !== 'undefined' && new URLSearchParams(location.search).has('r')) {
    const target = queryRoute(location.search), own = launchRoute(location.hash);
    try { history.replaceState(null, '', location.pathname + (own || target ? '#' + (own || target) : '')); } catch (e) { console.info('Launch query kept'); }
  }
  if (typeof location !== 'undefined' && /tgWebApp/.test(location.hash || '')) {
    const route = launchRoute(location.hash);
    try { history.replaceState(null, '', location.pathname + location.search + (route ? '#' + route : '')); } catch (e) { console.info('Launch hash kept'); }
  }
  const hasCatalog = () => catalogue.items.some(p => p.published === true && !p.sample);
  function mainButton(items, hash) {
    const count = Object.values(items || {}).reduce((a, b) => a + b, 0);
    if (!count) return null;
    const sum = window.ELShop ? window.ELShop.summary(items) : {known_total_cents: 0, quote_items: 0};
    if (launchRoute(hash) === 'cart') return window.ELTerms && window.ELTerms.blocked(sum) ? {text: t('tm.minSend'), action: 'send', blocked: true} : {text: t('mini.send'), action: 'send'};
    const total = window.ELShop && window.ELShop.totalCents ? window.ELShop.totalCents(sum) : sum.known_total_cents;
    return {text: sum.quote_items ? `${t('shop.request')} · ${count}` : `${t('nav.cart')} · ${fmt(total / 100)}`, action: 'cart'};
  }

  function cleanCart(input) {
    const result = {};
    if (!input || typeof input !== 'object' || Array.isArray(input)) return result;
    for (const [id, qty] of Object.entries(input)) {
      if (allowed.has(id) && Number.isInteger(qty) && qty > 0 && qty <= 99) result[id] = qty;
    }
    return result;
  }
  function readList(key, valid) {
    try {
      const v = JSON.parse(window.ELStore.get(key) || '[]');
      return Array.isArray(v) ? v.filter(valid) : [];
    } catch (e) { return []; }
  }
  const wishlist = () => [...new Set(readList(WISH, x => typeof x === 'string' && catalogIds.has(x)))];
  const orderHistory = () => readList(HIST, x => x && typeof x.id === 'string' && /^EL-TEST-[A-F0-9]{16}$/.test(x.id) && (Number.isInteger(x.total_cents) || x.total_cents === null)).slice(0, 8);
  function toggleWish(id) {
    if (!catalogIds.has(id)) return;
    const list = wishlist(), i = list.indexOf(id);
    if (i >= 0) list.splice(i, 1); else list.push(id);
    window.ELStore.set(WISH, JSON.stringify(list));
    tg?.HapticFeedback?.selectionChanged?.();
  }
  const priceLabel = p => Number.isInteger(p.price_cents) && p.price_cents > 0 ? fmt(p.price_cents / 100) : t('mini.priceOnRequest');
  const shareLink = payload => botName ? `https://t.me/${botName}?start=${payload}` : location.origin + '/';
  async function share(text, link) {
    if (tg?.openTelegramLink && tg.initData) {
      tg.openTelegramLink('https://t.me/share/url?url=' + encodeURIComponent(link) + '&text=' + encodeURIComponent(text));
      return;
    }
    try {
      if (navigator.share) { await navigator.share({title: 'Elements Labs', text, url: link}); return; }
      await navigator.clipboard.writeText(text + '\n' + link);
      toast(t('mini.copied'));
    } catch (e) { console.info('Share not available'); }
  }

  function catalogueLinks() {
    return `<div class="catalog-switch"><a class="secondary-btn" href="#products">${esc(t('mini.shop'))}</a><a class="secondary-btn" href="#catalog">${esc(t('mini.catalog'))}</a><a class="secondary-btn" href="#dual-chamber">${esc(t('mini.dual'))}</a></div>`;
  }
  function catalogCards() {
    const wished = new Set(wishlist());
    const q = filter.q.trim().toLowerCase();
    const items = catalogue.items.filter(p => p.published === true && (!filter.cat || p.category === filter.cat) &&
      (!q || (p.name + ' ' + (p.category || '') + ' ' + (p.description || '')).toLowerCase().includes(q)));
    if (!items.length) return `<div class="catalog-empty">${esc(t('mini.noResults'))}</div>`;
    return `<div class="cat-grid">${items.map(p => `<article class="cat-card"><div class="cat-img"><img src="${esc(p.image || '')}" alt="${esc(p.name)}" width="400" height="300" loading="lazy" decoding="async">${p.sample ? `<span class="cat-badge">${esc(t('mini.sample'))}</span>` : ''}</div><div class="cat-body"><div class="eyebrow">${esc(p.category || '')}</div><h2>${esc(p.name)}</h2><p>${esc(p.description || '')}</p><div class="cat-foot"><div><strong>${esc(priceLabel(p))}</strong><small>${esc(p.availability || '')}</small></div><button type="button" class="wish-btn" data-wish="${esc(p.id)}" aria-pressed="${wished.has(p.id)}">${esc(wished.has(p.id) ? t('mini.saved') : t('mini.save'))}</button></div></div></article>`).join('')}</div>`;
  }
  function catalogPage() {
    const items = catalogue.items.filter(p => p.published === true);
    const cats = [...new Set(items.map(p => p.category).filter(Boolean))];
    const wish = wishlist().length;
    const chips = [['', t('mini.all')], ...cats.map(c => [c, c])].map(([v, l]) => `<button type="button" class="chip" data-cat="${esc(v)}" aria-pressed="${filter.cat === v}">${esc(l)}</button>`).join('');
    return `<section class="section"><div class="eyebrow">ELEMENTS LABS · ${esc(t('mini.catalog'))}</div><h1 class="page-title">${esc(t('mini.catalogTitle'))}</h1><p class="lead">${esc(t('mini.catalogLead'))}</p>${catalogueLinks()}<div class="catalog-summary"><div><strong>${items.length}</strong><span>${esc(t('mini.catalogCount'))}</span></div><div><strong id="wishCount">${wish}</strong><span>${esc(t('mini.wishlist'))}</span></div><div><strong>${catalogue.dual_chamber.length}</strong><span>${esc(t('mini.systems'))}</span></div></div>${items.length ? `<div class="cat-tools"><label class="visually-hidden" for="catalogSearch">${esc(t('mini.search'))}</label><input id="catalogSearch" type="search" inputmode="search" autocomplete="off" placeholder="${esc(t('mini.search'))}" value="${esc(filter.q)}"><div class="chips" role="group" aria-label="${esc(t('mini.categories'))}">${chips}</div><button type="button" class="secondary-btn" id="shareWish"${wish ? '' : ' disabled'}>${esc(t('mini.shareWish'))}</button></div><div id="catalogGrid">${catalogCards()}</div>` : `<div class="catalog-empty">${esc(t('mini.catalogEmpty'))}</div>`}${items.some(p => p.sample) ? `<p class="sample-note">${esc(t('mini.sampleNote'))}</p>` : ''}</section>`;
  }
  function dualPage() {
    return `<section class="section"><div class="eyebrow">ELEMENTS LABS · ${esc(t('mini.catalog'))}</div><h1 class="page-title">${esc(t('mini.dualTitle'))}</h1><p class="lead">${esc(t('mini.dualLead'))}</p>${catalogueLinks()}<div class="dual-grid">${catalogue.dual_chamber.map(p => `<article class="dual-card"><img class="dual-art" src="${esc(p.image || '')}" alt="${esc(t('mini.schema'))}: ${esc(p.manufacturer)} ${esc(p.name)}" width="720" height="430" loading="lazy" decoding="async"><p class="dual-note">${esc(t('mini.schemaNote'))}</p><div class="eyebrow">${esc(p.manufacturer)}</div><h2>${esc(p.name)}</h2><p>${esc(p.kind)}</p><span class="catalog-status">${esc(t('mini.pending'))}</span><p>${esc(p.supply)}</p><blockquote lang="en">${esc(p.quote)}</blockquote><details><summary>${esc(t('mini.open'))}</summary><ul>${p.missing.map(x => `<li>${esc(x)}</li>`).join('')}</ul></details><a class="source-link" href="${esc(p.source)}" target="_blank" rel="noopener noreferrer">${esc(t('mini.source'))} ↗</a></article>`).join('')}</div></section>`;
  }
  function notFound() {
    return `<section class="section"><h1 class="page-title">${esc(t('detail.notFound1'))}</h1><a class="primary-btn" href="#products">${esc(t('detail.toCatalog'))}</a></section>`;
  }
  function renderHistory() {
    document.getElementById('orderHistory')?.remove();
    const list = orderHistory();
    if (!list.length || (location.hash || '') !== '#cart') return;
    const host = document.getElementById('orderFeedback');
    if (!host) return;
    host.insertAdjacentHTML('afterend', `<div id="orderHistory"><h3>${esc(t('mini.history'))}</h3><ul>${list.map(h => `<li><code>${esc(h.id)}</code><span>${esc(h.total_cents === null ? t('shop.quote') : fmt(h.total_cents / 100))}</span><small>${esc(new Date(h.at).toLocaleString())}</small></li>`).join('')}</ul></div>`);
  }
  function renderReceipt() {
    const host = document.getElementById('orderFeedback');
    if (!host || !lastReceipt || (location.hash || '') !== '#cart') return;
    const amount = lastReceipt.total_cents === null ? t('shop.extra') : fmt(lastReceipt.total_cents / 100);
    host.textContent = t('mini.received') + lastReceipt.id + '\n' + amount + (lastReceipt.notified ? '\n' + t('mini.notified') : '');
    if (Object.keys(cleanCart(cart)).length) host.textContent += '\n' + t('mini.remaining');
    host.dataset.orderId = lastReceipt.id;
  }
  function bindCatalog() {
    const search = document.getElementById('catalogSearch');
    if (!search) return;
    const grid = document.getElementById('catalogGrid');
    const refresh = () => {
      grid.innerHTML = catalogCards();
      document.getElementById('wishCount').textContent = String(wishlist().length);
      const sw = document.getElementById('shareWish');
      if (sw) sw.disabled = !wishlist().length;
      document.querySelectorAll('[data-cat]').forEach(c => c.setAttribute('aria-pressed', String(c.dataset.cat === filter.cat)));
    };
    search.oninput = () => { filter.q = search.value.slice(0, 80); refresh(); };
    document.querySelectorAll('[data-cat]').forEach(c => c.onclick = () => { filter.cat = c.dataset.cat; refresh(); });
    grid.onclick = e => {
      const b = e.target.closest('[data-wish]');
      if (!b) return;
      toggleWish(b.dataset.wish);
      refresh();
    };
    document.getElementById('shareWish').onclick = () => {
      const names = catalogue.items.filter(p => wishlist().includes(p.id)).map(p => '• ' + p.name);
      share(t('mini.wishlist') + ' – Elements Labs\n' + names.join('\n'), shareLink('katalog'));
    };
  }
  function shareProduct() {
    document.getElementById('shareProduct')?.remove();
    const m = /^#product=(.+)$/.exec(location.hash || '');
    if (!m) return;
    let id; try { id = decodeURIComponent(m[1]); } catch (e) { return; }
    const p = allProducts.find(x => x.id === id);
    const host = document.querySelector('#app .section, #app section');
    if (!p || !host) return;
    host.insertAdjacentHTML('beforeend', `<button type="button" class="secondary-btn" id="shareProduct">${esc(t('mini.share'))}</button>`);
    document.getElementById('shareProduct').onclick = () => share(`${p.name} ${p.concentration} – Elements Labs`, shareLink('p_' + id));
  }
  function lazyImages() {
    document.querySelectorAll('#app img:not([loading])').forEach((img, i) => {
      img.decoding = 'async';
      if (i >= (img.closest('#productGrid') ? 8 : 2) && !img.closest('.hero-scene')) img.loading = 'lazy';
    });
  }
  function syncNav() {
    const count = Object.values(cart).reduce((a, b) => a + b, 0);
    const badge = document.getElementById('miniCartCount');
    if (badge) badge.textContent = count ? String(count) : '';
    if (tg?.initData && tg.MainButton) {
      const state = count && !document.body.classList.contains('age-gate-open') ? mainButton(cart, location.hash) : null;
      if (state) {
        mainAction = state.action;
        tg.MainButton.setParams({text: state.text, color: state.blocked ? '#8A949B' : '#0D5B6B', text_color: '#ffffff', is_active: !state.blocked});
        tg.MainButton.show();
      } else tg.MainButton.hide();
    }
  }
  function contactHelp() {
    if ((location.hash || '') !== '#contact' || document.getElementById('contactHelp')) return;
    const host = document.querySelector('#app .section');
    if (host) host.insertAdjacentHTML('beforeend', `<div id="contactHelp" class="contact-help"><p>${esc(t('mini.contactHelp'))}</p><a class="primary-btn" href="#cart">${esc(t('nav.cart'))}</a></div>`);
  }
  document.addEventListener('input', () => setTimeout(rememberList, 0), true);
  document.addEventListener('change', () => setTimeout(rememberList, 0), true);
  document.addEventListener('focusin', e => { if (e.target.matches?.('input,select,textarea')) document.body.classList.add('kbd-open'); });
  document.addEventListener('focusout', e => { if (!e.relatedTarget?.matches?.('input,select,textarea')) document.body.classList.remove('kbd-open'); });
  if (typeof window.addEventListener === 'function') {
    window.addEventListener('pagehide', () => document.body.classList.remove('kbd-open'));
    window.addEventListener('hashchange', () => { if (!document.activeElement?.matches?.('input,select,textarea')) document.body.classList.remove('kbd-open'); });
  }
  function busyControls() {
    document.querySelectorAll('[data-qty],[data-remove]').forEach(control => {control.disabled = busy;});
  }
  function sync() {
    const current = '#' + (launchRoute(location.hash) || 'home');
    if (trail[trail.length - 1] !== current) {
      if (/^#products\/(vial|dual)$/.test(current) && ['#products', '#dual-chamber'].includes(trail[trail.length - 1])) trail[trail.length - 1] = current;
      else if (trail.length > 1 && trail[trail.length - 2] === current) trail.pop();
      else trail.push(current);
    }
    const cameFromDetail = lastRoute.startsWith('#product=');
    if (restoreStop && restoreRoute !== canon(current)) restoreStop();
    lastRoute = current;
    const back = document.querySelector('#app a.secondary-btn[href="#products"]');
    if (back && /^#product=/.test(current)) {
      const id = decodeURIComponent(current.slice(9));
      back.setAttribute('href', trail[trail.length - 2] === '#packs' ? '#packs' : id === 'mehrweg-pen' || id === 'reusable-pen' ? '#accessories' : id.startsWith('dual-') || id.endsWith('-dual') ? '#dual-chamber' : '#products/vial');
    }
    const productId = /^#product=(.+)$/.exec(current)?.[1] || '';
    const isPen = current === '#accessories' || productId === 'mehrweg-pen' || productId === 'reusable-pen';
    const isDual = current === '#dual-chamber' || current === '#products' || current === '#products/dual' || productId.startsWith('dual-') || productId.endsWith('-dual');
    document.querySelectorAll('[data-mini-route]').forEach(a => {
      const route = a.dataset.miniRoute;
      const active = (route === 'home' && current === '#home') || (route === 'products/vial' && (current === '#products/vial' || (productId && !isPen && !isDual))) || (route === 'dual-chamber' && isDual) || (route === 'accessories' && isPen) || (route === 'cart' && current === '#cart');
      if (active) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
    });
    if (tg?.initData && tg.BackButton) {
      if (current !== '#home') tg.BackButton.show(); else tg.BackButton.hide();
    }
    const notice = document.getElementById('environmentNotice');
    if (notice) notice.textContent = t('mini.test');
    const co = document.getElementById('checkoutBtn');
    if (co && !co.disabled) co.textContent = t('mini.send');
    syncNav();
    busyControls();
    window.ELShop?.bind();
    bindCatalog(); shareProduct(); renderHistory(); renderReceipt(); lazyImages(); contactHelp(); if (window.ELZoom) window.ELZoom.decorate();
    restoreList(current, cameFromDetail);
    document.querySelectorAll('.prod-tab').forEach((tab, index, tabs) => {
      const update = () => tabs.forEach(x => {const selected = x.classList.contains('active');x.setAttribute('aria-selected', String(selected));x.tabIndex = selected ? 0 : -1;});
      tab.addEventListener('click', update);
      tab.onkeydown = e => {
        let n;
        if (e.key === 'ArrowRight') n = (index + 1) % tabs.length;
        if (e.key === 'ArrowLeft') n = (index + tabs.length - 1) % tabs.length;
        if (e.key === 'Home') n = 0;
        if (e.key === 'End') n = tabs.length - 1;
        if (n !== undefined) {e.preventDefault();tabs[n].click();tabs[n].focus();}
      };
    });
  }
  async function checkout() {
    const button = document.getElementById('checkoutBtn'), feedback = document.getElementById('orderFeedback');
    if (busy || !button || !feedback) return;
    if (window.ELStore.get('elementsAgeGateConfirmed') !== '1') {feedback.textContent = t('age.blocked');return;}
    const items = Object.entries(cleanCart(cart)).map(([id, quantity]) => ({id, quantity}));
    if (!items.length) {feedback.textContent = t('mini.empty');return;}
    const orderSum = window.ELShop ? window.ELShop.summary(cart) : null;
    if (window.ELTerms && window.ELTerms.blocked(orderSum)) {feedback.textContent = t('tm.blocked');return;}
    const collective = !!(orderSum && orderSum.terms && orderSum.terms.collective);
    const fingerprint = JSON.stringify(items) + (collective ? '|collective' : '');
    let timer = null;
    busy = true; lastReceipt = null; feedback.textContent = ''; feedback.removeAttribute('data-order-id');
    button.disabled = true; button.setAttribute('aria-busy', 'true'); busyControls();
    try {
      if (!pending || pending.fingerprint !== fingerprint) pending = {fingerprint, id: (crypto.randomUUID ? crypto.randomUUID() : Array.from(crypto.getRandomValues(new Uint8Array(16)), b => b.toString(16).padStart(2, '0')).join(''))};
      const controller = new AbortController();
      timer = setTimeout(() => controller.abort(), orderTimeoutMs);
      const response = await fetch('/api/orders', {signal: controller.signal, method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json', 'X-Telegram-Init-Data': tg?.initData || ''}, body: JSON.stringify(collective ? {request_id: pending.id, items, research_confirmed: true, collective: true} : {request_id: pending.id, items, research_confirmed: true})});
      const result = await response.json();
      if (!response.ok || result.status !== 'LOCAL_TEST_SAVED') throw Object.assign(new Error(result.error || 'Request failed'), {code: result.code});
      const list = orderHistory().filter(h => h.id !== result.id);
      list.unshift({id: result.id, total_cents: result.total_cents, at: new Date().toISOString()});
      window.ELStore.set(HIST, JSON.stringify(list.slice(0, 8)));
      lastReceipt = result;
      pending = null;
      const remaining = cleanCart(cart);
      for (const item of items) {
        const count = (remaining[item.id] || 0) - item.quantity;
        if (count > 0) remaining[item.id] = count; else delete remaining[item.id];
      }
      cart = remaining;
      saveCart();
      render();
      renderReceipt();
      tg?.HapticFeedback?.notificationOccurred('success');
    } catch (e) {
      const currentFeedback = document.getElementById('orderFeedback');
      if (currentFeedback) {
        currentFeedback.textContent = t(e.code === 'AUTH_EXPIRED' ? 'mini.reopen' : e.code === 'RATE_LIMITED' ? 'mini.wait' : e.code === 'MIN_ORDER' ? 'tm.blocked' : 'mini.error');
        currentFeedback.removeAttribute('data-order-id');
      }
      tg?.HapticFeedback?.notificationOccurred('error');
    } finally {
      clearTimeout(timer);
      busy = false;
      busyControls();
      const currentButton = document.getElementById('checkoutBtn');
      if (currentButton) {currentButton.disabled = !Object.keys(cleanCart(cart)).length || !!(window.ELTerms && window.ELShop && window.ELTerms.blocked(window.ELShop.summary(cart)));currentButton.removeAttribute('aria-busy');}
    }
  }
  function safeAreas() {
    const style = document.documentElement.style;
    for (const [key, area] of [['safe', tg?.safeAreaInset], ['content', tg?.contentSafeAreaInset]]) {
      for (const edge of ['top', 'bottom']) {
        const n = Number(area?.[edge] || 0);
        style.setProperty(`--mini-${key === 'safe' ? 'safe' : 'content'}-${edge}`, `${Number.isFinite(n) ? Math.max(0, n) : 0}px`);
      }
    }
  }
  /* CloudStorage: cart, wishlist, language and history follow the user across devices. */
  const SYNC_KEYS = ['elementsTelegramCart', WISH, HIST, 'elementsLang'];
  function cloudSync() {
    const cloud = tg?.CloudStorage;
    if (!cloud || !tg.initData || !tg.isVersionAtLeast?.('6.9')) return;
    const timers = {};
    window.ELStore.onSet((key, value, fromCloud) => {
      if (fromCloud || !SYNC_KEYS.includes(key) || String(value).length > 3800) return;
      clearTimeout(timers[key]);
      timers[key] = setTimeout(() => cloud.setItem(key, String(value), () => {}), 600);
    });
    cloud.getItems(SYNC_KEYS, (err, values) => {
      if (err || !values) return;
      let changed = false;
      for (const key of SYNC_KEYS) {
        if (values[key] && !window.ELStore.get(key)) {window.ELStore.set(key, values[key], true);changed = true;}
      }
      if (changed) {
        const lang = window.ELStore.get('elementsLang');
        if (lang && typeof setLang === 'function' && document.documentElement.lang !== lang) { try { setLang(lang); } catch (e) { console.info('Language sync skipped'); } }
        try { cart = cleanCart(JSON.parse(window.ELStore.get('elementsTelegramCart') || '{}')); } catch (e) { cart = {}; }
        render();
      }
    });
  }
  document.addEventListener('click', e => {
    const h = tg?.HapticFeedback; if (!h || !tg.initData) return;
    if (e.target.closest('[data-add]')) h.impactOccurred('light');
    else if (e.target.closest('[data-qty],.mini-bottom-nav a,.chip')) h.selectionChanged();
  }, true);
  document.addEventListener('DOMContentLoaded', async () => {
    applyStaticTranslations();
    if ('serviceWorker' in navigator && location.protocol === 'https:') navigator.serviceWorker.register('/sw.js').catch(() => console.info('Offline cache unavailable'));
    if (tg?.initData) {
      tg.ready(); tg.expand();
      if (tg.isVersionAtLeast?.('6.1')) {tg.setHeaderColor('#F7F7F8');tg.setBackgroundColor('#F7F7F8');}
      if (tg.isVersionAtLeast?.('7.10')) tg.setBottomBarColor?.('#F7F7F8');
      if (tg.isVersionAtLeast?.('7.7')) tg.disableVerticalSwipes?.();
      safeAreas();
      tg.onEvent('safeAreaChanged', safeAreas); tg.onEvent('contentSafeAreaChanged', safeAreas);
      tg.BackButton?.onClick(() => {if (window.ELZoom && window.ELZoom.isOpen()) {window.ELZoom.close(); return;} if (trail.length > 1) history.back(); else location.hash = 'home';});
      tg.MainButton?.onClick(() => {if (mainAction === 'send') checkout(); else location.hash = 'cart';});
      const start = tg.initDataUnsafe?.start_param;
      if (start && allowed.has(start)) location.hash = 'product=' + encodeURIComponent(start);
      else if (start === 'katalog') location.hash = 'catalog';
      cloudSync();
    }
    try {const r = await fetch('/api/config');if (r.ok) {const c = await r.json();mode = c.mode;botName = /^[A-Za-z0-9_]{5,32}$/.test(c.bot || '') ? c.bot : '';}} catch (e) {console.info('Preview configuration unavailable');}
    sync();
    const observer = new MutationObserver(() => {const blocked = document.body.classList.contains('age-gate-open');document.getElementById('app').inert = blocked;document.querySelector('.site-header').inert = blocked;document.querySelector('.footer').inert = blocked;syncNav();});
    observer.observe(document.body, {attributes: true, attributeFilter: ['class']});
    const blocked = document.body.classList.contains('age-gate-open');
    document.getElementById('app').inert = blocked; document.querySelector('.site-header').inert = blocked; document.querySelector('.footer').inert = blocked;
    document.getElementById('ageGate').addEventListener('keydown', e => {
      if (e.key !== 'Tab') return;
      const focusables = [...document.getElementById('ageGate').querySelectorAll('button:not(:disabled),input,a[href]')].filter(x => x.offsetParent !== null);
      const first = focusables[0], last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) {e.preventDefault();last?.focus();}
      else if (!e.shiftKey && document.activeElement === last) {e.preventDefault();first?.focus();}
    });
  });
  return {restoreScroll, scrollMemo: () => scrollMemo, isBusy: () => busy, cleanCart, catalogPage, dualPage, notFound, sync, syncNav, checkout, wishlist, toggleWish, launchRoute, queryRoute, mainButton, hasCatalog, setOrderTimeout: ms => { orderTimeoutMs = ms; }};
})();
