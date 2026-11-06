/* Bildvergroesserung fuer Produktbilder (Vial, Doppelkammer, Pen): Vollbild-Overlay.
   Erst eingepasst, per Tipp 2,2-fach mit Verschieben (Startausschnitt mittig), erneuter Tipp zurueck.
   Schliessen: X, Hintergrund, Escape, Zurueck-Taste des Browsers oder Telegram-BackButton (ein History-Eintrag).
   Die Seite darunter wird nicht gescrollt (nur overflow:hidden am html-Element, Position wird geprueft und zurueckgesetzt). */
window.ELZoom = (() => {
  const SCALE = 2.2;
  const label = key => (typeof t === 'function' ? t(key) : key);
  let overlay = null, stage = null, img = null, hint = null, closeBtn = null;
  let zoomed = false, pushed = false, savedY = 0, opener = null, down = null;

  const isOpen = () => !!overlay;

  /* Eingepasste Groesse in CSS-Pixeln: Bild vollstaendig im Fenster, Seitenverhaeltnis bleibt. */
  function fitSize(natW, natH, vw, vh) {
    const w = natW > 0 ? natW : vw, h = natH > 0 ? natH : vh;
    const k = Math.min(vw / w, vh / h);
    return {w: Math.max(1, Math.round(w * k)), h: Math.max(1, Math.round(h * k))};
  }

  function applySize() {
    if (!img || !stage) return;
    const vw = stage.clientWidth || window.innerWidth, vh = stage.clientHeight || window.innerHeight;
    const fit = fitSize(img.naturalWidth, img.naturalHeight, vw, vh);
    const k = zoomed ? SCALE : 1;
    img.style.width = Math.round(fit.w * k) + 'px';
    img.style.height = Math.round(fit.h * k) + 'px';
    stage.classList.toggle('is-zoomed', zoomed);
    const text = label(zoomed ? 'zoom.hintOut' : 'zoom.hintIn');
    img.setAttribute('aria-label', (img.getAttribute('alt') || '') + ' – ' + text);
    img.setAttribute('aria-pressed', zoomed ? 'true' : 'false');
    if (hint) hint.textContent = text;
    if (zoomed) {  // Startausschnitt mittig
      stage.scrollLeft = Math.max(0, (stage.scrollWidth - stage.clientWidth) / 2);
      stage.scrollTop = Math.max(0, (stage.scrollHeight - stage.clientHeight) / 2);
    } else {
      stage.scrollLeft = 0; stage.scrollTop = 0;
    }
  }

  function toggleZoom() { zoomed = !zoomed; applySize(); }

  function teardown() {
    if (!overlay) return;
    overlay.remove();
    overlay = stage = img = hint = closeBtn = null;
    zoomed = false;
    document.documentElement.classList.remove('zoom-open');
    if (Math.abs(window.scrollY - savedY) > 1) window.scrollTo({top: savedY, left: 0, behavior: 'instant'});
    const back = opener; opener = null;
    if (back && typeof back.focus === 'function') { try { back.focus({preventScroll: true}); } catch (e) { /* focus not possible */ } }
  }

  /* Schliessen per X, Hintergrund, Escape oder BackButton: den eigenen History-Eintrag wieder abbauen. */
  function close() {
    if (!overlay) return;
    teardown();
    if (pushed) { pushed = false; try { history.back(); } catch (e) { /* no history */ } }
  }

  function open(src, alt, from) {
    if (overlay || !src) return;
    savedY = window.scrollY;
    opener = from || null;
    overlay = document.createElement('div');
    overlay.id = 'zoomOverlay';
    overlay.className = 'zoom-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', label('zoom.dialog'));
    closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'zoom-close';
    closeBtn.setAttribute('aria-label', label('zoom.close'));
    closeBtn.innerHTML = '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg>';
    stage = document.createElement('div');
    stage.className = 'zoom-stage';
    img = document.createElement('img');
    img.className = 'zoom-img';
    img.setAttribute('role', 'button');
    img.setAttribute('tabindex', '0');
    img.setAttribute('alt', alt || '');
    img.decoding = 'async';
    img.src = src;
    hint = document.createElement('div');
    hint.className = 'zoom-hint';
    hint.setAttribute('aria-hidden', 'true');
    stage.appendChild(img);
    overlay.appendChild(stage);
    overlay.appendChild(closeBtn);
    overlay.appendChild(hint);
    document.body.appendChild(overlay);
    document.documentElement.classList.add('zoom-open');
    try { history.pushState({elZoom: 1}, '', location.href); pushed = true; } catch (e) { pushed = false; }
    zoomed = false;
    applySize();
    img.addEventListener('load', applySize);
    closeBtn.addEventListener('click', e => { e.stopPropagation(); close(); });
    /* Tipp (nicht Ziehen) auf das Bild wechselt die Ansicht, Tipp daneben schliesst. */
    stage.addEventListener('pointerdown', e => { down = {x: e.clientX, y: e.clientY, sl: stage.scrollLeft, st: stage.scrollTop}; });
    stage.addEventListener('click', e => {
      const moved = down && (Math.abs(e.clientX - down.x) > 8 || Math.abs(e.clientY - down.y) > 8 || stage.scrollLeft !== down.sl || stage.scrollTop !== down.st);
      down = null;
      if (moved) return;
      if (e.target === img) toggleZoom(); else close();
    });
    img.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleZoom(); } });
    overlay.addEventListener('keydown', e => {
      if (e.key === 'Escape') { e.preventDefault(); close(); return; }
      if (e.key !== 'Tab') return;
      const order = [closeBtn, img], at = order.indexOf(document.activeElement);
      e.preventDefault();
      order[(at + (e.shiftKey ? order.length - 1 : 1)) % order.length].focus();
    });
    closeBtn.focus({preventScroll: true});
  }

  /* Bilder der Produktseiten als Schaltflaeche kennzeichnen (nach jedem Rendern). */
  function decorate() {
    document.querySelectorAll('.gallery-main').forEach(host => {
      const pic = host.querySelector('img');
      if (!pic) return;
      host.setAttribute('data-zoomable', '');
      host.setAttribute('role', 'button');
      host.setAttribute('tabindex', '0');
      host.setAttribute('aria-label', label('zoom.open') + ': ' + (pic.getAttribute('alt') || ''));
    });
  }

  function trigger(host) {
    const pic = host && host.querySelector('img');
    if (pic) open(pic.currentSrc || pic.src, pic.getAttribute('alt') || '', host);
  }

  if (typeof document !== 'undefined' && typeof document.addEventListener === 'function') {
    document.addEventListener('click', e => {
      if (overlay || !e.target.closest) return;
      const host = e.target.closest('.gallery-main');
      if (host) trigger(host);
    });
    document.addEventListener('keydown', e => {
      if (overlay || (e.key !== 'Enter' && e.key !== ' ') || !e.target.matches || !e.target.matches('.gallery-main')) return;
      e.preventDefault();
      trigger(e.target);
    });
  }
  if (typeof window !== 'undefined' && typeof window.addEventListener === 'function') {
    window.addEventListener('popstate', () => { if (overlay) { pushed = false; teardown(); } });
    window.addEventListener('hashchange', () => { if (overlay) { pushed = false; teardown(); } });
  }
  return {open, close, isOpen, decorate, fitSize, SCALE};
})();
