// Stabile Eingangstuer des Elements-Labs-Shops. Die Adresse dieser Worker/Domain bleibt gleich,
// das Ziel (ORIGIN = aktueller Tunnel des Shop-Servers) wird von live.py/publish.py gesetzt.
// Ist das Ziel nicht erreichbar, zeigt der Worker eine freundliche Seite statt eines Fehlers.
const AUS = `<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Elements Labs</title>
<body style="font-family:system-ui;background:#0b0b0f;color:#eee;display:grid;place-items:center;min-height:100vh;margin:0;text-align:center">
<div><h1 style="font-weight:600">Elements Labs</h1><p>Der Shop startet gerade neu.<br>Bitte in wenigen Minuten erneut öffnen.</p></div>`;
export default {
  async fetch(request, env) {
    const origin = (env.ORIGIN || '').replace(/\/$/, '');
    if (!origin) return new Response(AUS, {status: 503, headers: {'content-type': 'text/html;charset=utf-8', 'retry-after': '120'}});
    const url = new URL(request.url);
    const ziel = origin + url.pathname + url.search;
    const h = new Headers(request.headers);
    h.delete('host'); h.delete('cf-connecting-ip'); h.delete('x-forwarded-for');
    if (h.has('origin')) h.set('origin', origin);           // Server prueft Origin gegen seine Tunneladresse
    const init = {method: request.method, headers: h, redirect: 'manual'};
    if (!['GET', 'HEAD'].includes(request.method)) init.body = request.body;
    try {
      const r = await fetch(ziel, init);
      if (r.status === 530 || r.status === 502 || r.status === 1033)
        return new Response(AUS, {status: 503, headers: {'content-type': 'text/html;charset=utf-8', 'retry-after': '120'}});
      const out = new Headers(r.headers);
      const loc = out.get('location');
      if (loc && loc.startsWith(origin)) out.set('location', url.origin + loc.slice(origin.length));
      return new Response(r.body, {status: r.status, headers: out});
    } catch (e) {
      return new Response(AUS, {status: 503, headers: {'content-type': 'text/html;charset=utf-8', 'retry-after': '120'}});
    }
  }
};
