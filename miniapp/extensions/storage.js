/* Persistent where available, in-memory otherwise. No shared website cart. */
/* A script that fails to load (tunnel hiccup after the host woke up) leaves a half-initialised shop: reload up to three times instead of showing a broken page. */
(() => {
  if (typeof document === 'undefined' || typeof document.addEventListener !== 'function' || typeof location === 'undefined') return;
  document.addEventListener('error', event => {
    const el = event.target;
    if (!el || el.tagName !== 'SCRIPT' || !el.src || !el.src.startsWith(location.origin)) return;
    let tries = 0;
    try { tries = parseInt(sessionStorage.getItem('elReloadTries') || '0', 10) || 0; } catch (e) { tries = 3; }
    if (tries >= 3) return;
    try { sessionStorage.setItem('elReloadTries', String(tries + 1)); } catch (e) { return; }
    setTimeout(() => location.reload(), 2500 * (tries + 1));
  }, true);
  if (typeof window !== 'undefined' && typeof window.addEventListener === 'function') {
    window.addEventListener('load', () => { try { sessionStorage.removeItem('elReloadTries'); } catch (e) { /* ignore */ } });
  }
})();
window.ELStore = (() => {
  const memory = new Map();
  const listeners = [];
  return {
    get(key) { if (memory.has(key)) return memory.get(key); try { return localStorage.getItem(key) ?? null; } catch(e) { return null; } },
    set(key, value, fromCloud = false) {
      memory.set(key, String(value));
      try { localStorage.setItem(key, String(value)); } catch(e) { console.info('Session-only storage'); }
      listeners.forEach(fn => { try { fn(key, String(value), fromCloud); } catch(e) { console.info('Storage listener failed'); } });
    },
    onSet(fn) { listeners.push(fn); }
  };
})();
