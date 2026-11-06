"""Reproducible, isolated build from the owner's exact Vercel reference.
Only public/ is served. Evidence, supplier drafts and credentials stay private.
"""
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'evidence/reference-current'
PUBLIC = ROOT / 'public'


def data_from_html(html, element):
    match = re.search(r'id="' + element + r'"[^>]*>(.*?)</script>', html, re.S)
    if not match:
        raise ValueError('Missing reference data: ' + element)
    return json.loads(match[1])


def json_script(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')


sys.path.insert(0, str(Path(__file__).resolve().parent / 'tools'))
import dedicated_pages  # noqa: E402


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Reference changed; review required: ' + old[:80])
    return text.replace(old, new)


def versioned_catalog():
    """Embeds the catalogue with content-hash query strings so edited images are never served stale."""
    catalog = json.loads((ROOT/'data/catalog.json').read_text())
    def ver(ref):
        if not ref:
            return ref
        base = ref.split('?')[0]
        for src in (ROOT/'extensions'/base, ROOT/'katalog-bilder'/Path(base).name if base.startswith('assets/catalog-user/') else None):
            if src and src.is_file():
                return base + '?v=' + hashlib.sha256(src.read_bytes()).hexdigest()[:8]
        return base
    catalog['items'] = [entry for entry in catalog['items'] if not entry.get('sample')]
    catalog['dual_chamber'] = []
    for entry in catalog['items']:
        entry['image'] = ver(entry.get('image'))
    return catalog


def optimize_images():
    """PNG (1.3-1.7 MB each) -> WebP; rewrites references. Visual design unchanged."""
    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit('Pillow fehlt: .venv-build/bin/python build.py verwenden') from exc
    converted = 0
    for png in sorted((PUBLIC/'assets').rglob('*.png')):
        with Image.open(png) as im:
            im.load()
            limit = 1800 if 'scenes' in png.parts else 1600
            if max(im.size) > limit:
                im.thumbnail((limit, limit), Image.LANCZOS)
            im.convert('RGBA' if im.mode in ('RGBA','LA','P') else 'RGB').save(png.with_suffix('.webp'), 'WEBP', quality=92, method=6)
        png.unlink()
        converted += 1
    # Small card thumbnails: 15 full-size images per list would stall phones.
    for webp in sorted((PUBLIC/'assets/products').rglob('*.webp')):
        if webp.stem.endswith(('-card', '-detail')) or 'pen' in webp.stem:
            continue
        with Image.open(webp) as im:
            im.load()
            im.thumbnail((560, 560), Image.LANCZOS)
            im.save(webp.with_name(webp.stem + '-card.webp'), 'WEBP', quality=84, method=6)
    pattern = re.compile(r'(assets/[A-Za-z0-9_./-]+)\.png')
    for name in ['index.html','app.js','styles.css','i18n.js','variants.js']:
        f = PUBLIC/name
        text = pattern.sub(r'\1.webp', f.read_text())
        if name == 'variants.js':
            text = text.replace(".png'", ".webp'")
        f.write_text(text)
    return converted


def _build():
    html = (SOURCE / 'index.html').read_text()
    raw = data_from_html(html, 'productData')
    products_path = ROOT / 'data/products.json'
    if not products_path.exists():
        products_path.parent.mkdir(parents=True, exist_ok=True)
        products = []
        for p in raw:
            p = dict(p)
            p['price_cents'] = int(p['price'].replace(' €', '').replace('.', '').replace(',', ''))
            p['stock_status'] = 'UNCONFIRMED'
            p['format'] = 'vial'
            products.append(p)
        products_path.write_text(json.dumps(products, ensure_ascii=False, indent=2) + '\n')
    products = json.loads(products_path.read_text())
    existing = {p['id']: p for p in products}
    merged = []
    for original in raw:
        p = dict(existing.pop(original['id'], original))
        p.setdefault('price_cents', int(original['price'].replace(' €', '').replace('.', '').replace(',', '')))
        p.setdefault('stock_status', 'UNCONFIRMED')
        p.setdefault('format', 'vial')
        merged.append(p)
    products = merged + list(existing.values())
    products_path.write_text(json.dumps(products, ensure_ascii=False, indent=2) + '\n')
    seen = set()
    for p in products:
        if p['id'] in seen:
            raise ValueError('Duplicate product')
        seen.add(p['id'])
        cents = p['price_cents']
        if type(cents) is not int or cents < 1:
            raise ValueError('Invalid integer price')
        p['price'] = f'{cents // 100},{cents % 100:02d} €'
    research = data_from_html(html, 'researchData')
    html = re.sub(r'(<script id="productData"[^>]*>).*?(</script>)', lambda m: m[1] + json_script(products) + m[2], html, flags=re.S)
    html = re.sub(r'(<script id="researchData"[^>]*>).*?(</script>)', lambda m: m[1] + json_script(research) + m[2], html, flags=re.S)
    html = html.replace('width=device-width, initial-scale=1', 'width=device-width, initial-scale=1, viewport-fit=cover')
    html = html.replace('</head>', '<link rel="stylesheet" href="miniapp.css">\n<script src="https://telegram.org/js/telegram-web-app.js"></script>\n</head>')
    formats = json.loads((ROOT / 'data/shop-formats.json').read_text())
    for p in formats:
        image_path = ROOT / 'asset-cache-current' / p['image']
        p['image'] += '?v=' + hashlib.sha256(image_path.read_bytes()).hexdigest()[:8]
        if p.get('thumb'):
            p['thumb'] += '?v=' + hashlib.sha256((ROOT / 'asset-cache-current' / p['thumb']).read_bytes()).hexdigest()[:8]
    html = replace_once(html, '<script src="app.js?v=flagship-03"></script>', '<script id="catalogData" type="application/json">' + json_script(versioned_catalog()) + '</script>\n<script id="formatData" type="application/json">' + json_script(formats) + '</script>\n<script id="packData" type="application/json">' + json_script(json.loads((ROOT / 'data/catalog-packs.json').read_text())) + '</script>\n<script id="termsData" type="application/json">' + json_script(json.loads((ROOT / 'data/terms.json').read_text())) + '</script>\n<script src="terms.js"></script>\n<script src="telegram.js"></script>\n<script src="zoom.js"></script>\n<script src="shop-formats.js"></script>\n<script src="app.js?v=telegram-02"></script>')
    html = html.replace('<a href="#products" data-i18n="nav.products">', '<a href="#dual-chamber" data-i18n="mini.dual">Doppelkammer</a><a href="#accessories" data-i18n="format.pen">Mehrweg-Pen</a><a href="#packs" data-i18n="shop.navPacks">10er-Packs</a><a href="#products" data-i18n="nav.products">')
    html = html.replace('<main id="app"', '<div id="environmentNotice" class="environment-notice" role="status">Testversion · keine Bestellungen oder Zahlungen nach außen</div><main id="app"')
    nav = '<nav class="mini-bottom-nav" aria-label="Shop-Navigation">'
    for route, key, icon in [('home','mini.home','M3 10l9-7 9 7v11H3z M9 21v-8h6v8'),('products/vial','shop.navVials','M4 5h16v15H4z M8 5V3h8v2'),('dual-chamber','shop.navDual','M5 3h14v18H5z M5 12h14'),('accessories','shop.navPen','M9 3h6v4H9z M8 7h8v14H8z'),('packs','shop.navPacks','M4 4h7v7H4z M13 4h7v7h-7z M4 13h7v7H4z M13 13h7v7h-7z'),('cart','nav.cart','M3 3h2l3 13h11l2-10H6 M9 21h.01 M18 21h.01')]:
        nav += f'<a href="#{route}" data-mini-route="{route}"><svg aria-hidden="true" viewBox="0 0 24 24"><path d="{icon}"/></svg><span data-i18n="{key}"></span>' + ('<span id="miniCartCount" aria-label="Artikel im Warenkorb"></span>' if route=='cart' else '') + '</a>'
    html = html.replace('</body>', nav + '</nav></body>')
    html = html.replace('id="ageGate" class="age-gate-overlay"', 'id="ageGate" class="age-gate-overlay" role="dialog" aria-modal="true" aria-labelledby="ageGateTitle"')
    html = html.replace('<h2 data-i18n="age.title">', '<h2 id="ageGateTitle" data-i18n="age.title">')
    html = replace_once(html, 'Bevor Sie fortfahren', 'Bevor du fortfährst')
    html = replace_once(html, 'Sind Sie 18 Jahre oder älter?', 'Bist du 18 Jahre oder älter?')
    # Storage may be disabled in embedded browsers: never block the whole UI.
    html = html.replace("if(localStorage.getItem('elementsAgeGateConfirmed')==='1'){document.getElementById('ageGate').classList.add('hidden');}", "try{if(localStorage.getItem('elementsAgeGateConfirmed')==='1'){document.getElementById('ageGate').classList.add('hidden');}}catch(e){console.info('Session-only storage');}")
    js = (SOURCE/'app.js').read_text()
    js = re.sub(r' onmouse(?:over|out)="[^"]*"', '', js)
    js = re.sub(r'(?<!products/)reusable-pen(?!\.)', 'mehrweg-pen', js)
    js = js.replace('<img src="${pen.image}"', '<img src="assets/products/reusable-pen-wide.png"')
    js = js.replace('src="assets/hero-focus/pen.webp" width="172" height="1600"', 'src="assets/products/reusable-pen-wide.png" width="1810" height="930"')
    js = replace_once(js, "function pById(id){return sellableProducts.find(p=>p.id===id)}", "function pById(id){const key=id==='reusable-pen'?'mehrweg-pen':id.endsWith('-dual')?'dual-'+id.slice(0,-5):id;return sellableProducts.find(p=>p.id===key)||window.ELShop.byId(key)}")
    # Impressum/Datenschutz: kein "PRE-LAUNCH STATUS"-Banner (Checkliste T12), Rest der Seite unveraendert
    js, banner = re.subn(r'<div style="[^"]*"><strong>\$\{esc\(t\(\'legal\.preLaunch\'\)\)\}</strong>.*?</div>', '', js, count=1, flags=re.S)
    if banner != 1:
        raise ValueError('Reference changed; review required: legal pre-launch banner')
    js = replace_once(js, "if(h==='cart')return cartPage();", "if(h==='cart')return window.ELShop.cartPage();")
    js = replace_once(js, "function removeFromCart(id){delete cart[id];saveCart();render()}", "function removeFromCart(id){if(window.ELMini.isBusy())return;delete cart[id];saveCart();render()}")
    js = js.replace("localStorage.getItem(key)", "window.ELStore.get(key)").replace("localStorage.setItem(key,'1')", "window.ELStore.set(key,'1')")
    js = js.replace("JSON.parse(localStorage.getItem('elementsCart') || '{}')", "window.ELMini.cleanCart(JSON.parse(window.ELStore.get('elementsTelegramCart') || '{}'))")
    js = js.replace("localStorage.setItem('elementsCart', JSON.stringify(cart));", "window.ELStore.set('elementsTelegramCart', JSON.stringify(cart));")
    js = replace_once(js, "Object.values(cart).reduce((a,b)=>a+b,0)}", "Object.values(cart).reduce((a,b)=>a+b,0);window.ELMini.syncNav();}")
    js = replace_once(js, "function addToCart(id,qty=1){cart[id]=(cart[id]||0)+qty;saveCart();toast(t('cart.added'));}", "function addToCart(id,qty=1){if(!pById(id)||!Number.isInteger(qty)||qty<1)return;cart[id]=Math.min(99,(cart[id]||0)+qty);saveCart();toast(t('cart.added'));}")
    js = replace_once(js, "function setQty(id,qty){if(qty<=0) delete cart[id]; else cart[id]=qty;saveCart();render()}", "function setQty(id,qty){if(window.ELMini.isBusy()||!pById(id)||!Number.isInteger(qty))return;if(qty<=0)delete cart[id];else cart[id]=Math.min(99,qty);saveCart();render()}")
    js = replace_once(js, "const h=decodeURIComponent(location.hash.slice(1)||'home');", "let h;try{h=decodeURIComponent(window.ELMini.launchRoute(location.hash)||'home');}catch(e){return window.ELMini.notFound();}\n  if(h==='catalog')return window.ELMini.hasCatalog()?window.ELMini.catalogPage():researchHubPage();\n  if(h==='dual-chamber'){catalogForm='dual';return productsPage();}\n  if(h==='accessories')return penDetail();\n  if(h==='packs')return window.ELShop.packsPage();")
    js = replace_once(js, "        </div>\n        ${researchReminder}\n", "        </div>\n        ${window.ELShop.packBlock(p)}\n        ${researchReminder}\n")
    # Haendler-Anzeige (Inhaber 24.10.2026): 10er-Pack-Preis + Preis je Stueck und "inklusive Pen" direkt unter dem Einzelpreis; Pen-Block statt "Pen separat hinzufuegen"
    js = replace_once(js, '<div class="price" style="margin:10px 0 18px">${p.price}</div>', '<div class="price" style="margin:10px 0 18px">${p.price}</div>\n        ${window.ELShop.priceExtras(p)}')
    js = replace_once(js, '${optionalPen()}', '${window.ELShop.penIncluded()}')
    # Vertrauenszeile (Versand, Lieferzeit, Direktbezug, 10er-Pack) auch auf Doppelkammer-Seiten, gleiche Texte wie bei Vial
    js = replace_once(js, "${window.ELShop.penIncluded()}`:trustBadges}", "${window.ELShop.penIncluded()}${trustBadges}`:trustBadges}")
    js = replace_once(js, "${esc(formLabel(lead))} · ${n}", "${esc(formLabel(lead))}${lead.form==='dual'?' · '+esc(t('shop.penIncluded')):''} · ${n}")
    js = replace_once(js, "<p class=\"compound-meta\">${esc(t('products.noResults'))}</p>", "${window.ELShop.emptyProducts((document.getElementById('searchInput')||{}).value||'')}")
    js = replace_once(js, '\n\n    <section class="section evidence-band">', '\n    ${window.ELShop?window.ELShop.catalogTeaser():\'\'}\n\n    <section class="section evidence-band">')
    js = replace_once(js, '<a class="primary-btn" data-hero-primary href="#products/dual">${esc(t(\'focus.dualCTA\'))}</a>', '<a class="primary-btn" data-hero-primary href="#packs">${esc(t(\'focus.shopCTA\'))}</a>')  # Owner 24.10.2026: Shop im Fokus
    js = replace_once(js, '<a class="secondary-btn" data-hero-pen href="#product=mehrweg-pen">${esc(t(\'format.penDetails\'))}</a>\n        </div>', '<a class="secondary-btn" data-hero-pen href="#products/vial">${esc(t(\'focus.vialCTA\'))}</a>\n        </div>${window.ELTerms?window.ELTerms.strip():\'\'}')
    js = replace_once(js, "history.replaceState(null,'','#products/'+catalogForm);", "history.replaceState(null,'','#products/'+catalogForm);window.ELMini.sync();")
    js = dedicated_pages.apply(js, replace_once)
    js = replace_once(js, "(p.name+(p.code||'')+(p.batch||'')+p.category).toLowerCase().includes(q)", "window.ELShop.match(p.name+' '+p.concentration+' '+(p.code||'')+' '+(p.batch||'')+' '+p.category,q)")
    # Suche mit Dosis ("Semaglutid 15"): Karte verlinkt die passende Variante der Gruppe statt der Standardvariante
    js = replace_once(js, "if(cf.value)list=list.filter(g=>g.lead.category===cf.value);", "list=list.map(g=>({...g,pick:q?window.ELShop.pickVariant(g.variants,q):''}));if(cf.value)list=list.filter(g=>g.lead.category===cf.value);")
    js = replace_once(js, "function productCard(g){\n  const lead=g.lead,", "function productCard(g){\n  const lead=g.lead, target=g.pick||lead.id,")
    js = replace_once(js, '<a class=\"primary-btn card-options\" href=\"#product=${lead.id}\"', '<a class=\"primary-btn card-options\" href=\"#product=${target}\"')
    js = replace_once(js, '<a class=\"product-img-wrap\" href=\"#product=${lead.id}\" aria-label', '<a class=\"product-img-wrap\" href=\"#product=${target}\" aria-label')
    js = replace_once(js, "location.hash='products';setTimeout(()=>document.getElementById('searchInput')", "location.hash='products/vial';setTimeout(()=>document.getElementById('searchInput')")
    js = replace_once(js, "${n} ${esc(t('products.variants'))}", "${n} ${esc(n===1?t('products.variant1'):t('products.variants'))}")
    js = replace_once(js, "const bbh=document.getElementById('batchSubmitHome');", "const bi=document.getElementById('batchInput');if(bi)bi.addEventListener('keydown',e=>{if(e.key==='Enter'&&bb)bb.click()});const bbh=document.getElementById('batchSubmitHome');")
    js = replace_once(js, "if(co)co.onclick=()=>document.getElementById('checkoutDemo').classList.remove('hidden');", "if(co)co.onclick=()=>window.ELMini.checkout();")
    js = re.sub(r'<div id="checkoutDemo".*?</div>', '<div id="orderFeedback" role="status" aria-live="polite"></div>', js)
    js = replace_once(js, "window.scrollTo({top:0,left:0,behavior:'instant'});}", "if(window.__lastRoute!==location.hash)window.scrollTo({top:0,left:0,behavior:'instant'});window.__lastRoute=location.hash;window.ELMini.sync();}")
    js = js.replace('<div class="prod-tabs" role="tablist">', '<div class="prod-tabs" role="tablist" aria-label="Produktinformationen">')
    js = js.replace('role="tab" data-tab="${esc(tb.id)}"', 'role="tab" id="tab-${esc(tb.id)}" aria-controls="panel-${esc(tb.id)}" aria-selected="${i===0}" tabindex="${i===0?0:-1}" data-tab="${esc(tb.id)}"')
    js = js.replace('data-tab="${esc(tb.id)}" role="tabpanel"', 'data-tab="${esc(tb.id)}" id="panel-${esc(tb.id)}" aria-labelledby="tab-${esc(tb.id)}" role="tabpanel"')
    i18n = (SOURCE/'i18n.js').read_text()
    i18n = i18n.replace("localStorage.getItem('elementsLang')", "window.ELStore.get('elementsLang')").replace("localStorage.setItem('elementsLang', code)", "window.ELStore.set('elementsLang', code)")
    # Texte der Vorlage, die im ausgelieferten i18n.js nicht mehr stehen duerfen (Checkliste T12 und Texte des Inhabers 25.10.2026)
    i18n = replace_once(i18n, "'age.title':'Bevor Sie fortfahren'", "'age.title':'Bevor du fortfährst'")
    i18n = replace_once(i18n, "'age.question':'Sind Sie 18 Jahre oder älter?'", "'age.question':'Bist du 18 Jahre oder älter?'")
    i18n = replace_once(i18n, "'detail.chooseSize':'Choisir le format'", "'detail.chooseSize':'Choisir la quantité'")
    # Du-Form im deutschen Shop (Inhaber 25.10.2026) und kein Status-Satz "PRE_LAUNCH" im Research-Hub (Absatz sonst unveraendert)
    i18n = replace_once(i18n, "Geben Sie Ihre Batchnummer ein", "Gib deine Batchnummer ein")
    i18n = replace_once(i18n, "So finden Sie Ihre Batch-ID", "So findest du deine Batch-ID")
    i18n = replace_once(i18n, "— Sie erhalten eine Rückmeldung", "— du erhältst eine Rückmeldung")
    i18n = replace_once(i18n, "erreichen Sie Elements Labs direkt", "erreichst du Elements Labs direkt")
    for status_sentence in (" Elements Labs befindet sich im PRE_LAUNCH-Status — keine kommerziellen Transaktionen sind aktiv.",
                            " Elements Labs is in PRE_LAUNCH status — no commercial transactions are active.",
                            " Elements Labs est en statut PRE_LAUNCH — aucune transaction commerciale n\\'est active."):
        i18n = replace_once(i18n, status_sentence, "")
    i18n, dropped = re.subn(r"^[ \t]*'(?:legal\.preLaunch|legal\.preLaunchText|tab\.shipStatus)':[^\n]*\n", '', i18n, flags=re.M)
    if dropped != 9:
        raise ValueError('Reference changed; review required: pre-launch texts (%d)' % dropped)
    i18n, imprint = re.subn(r" (?:Interim-Status|Interim status|Statut intermédiaire ): PRE_LAUNCH\.", '', i18n)
    if imprint != 3:
        raise ValueError('Reference changed; review required: imprint status (%d)' % imprint)
    dual_range = iter(['Doppelkammer inklusive Pen', 'Dual chamber, pen included', 'Double chambre, stylo inclus'])
    i18n, ranges = re.subn(r'"focus\.dualRange": "(?:[^"\\]|\\.)*"', lambda m: '"focus.dualRange": "' + next(dual_range) + '"', i18n)
    if ranges != 3:
        raise ValueError('Reference changed; review required: focus.dualRange (%d)' % ranges)
    pen_text = iter(['In jeder Doppelkammer enthalten. Dieser Artikel ist ein zusätzlicher Mehrweg-Pen.', 'Included with every dual chamber. This item is an additional reusable pen.', 'Inclus avec chaque double chambre. Cet article est un stylo réutilisable supplémentaire.'])
    i18n, pens = re.subn(r'"format\.penNotIncluded": "(?:[^"\\]|\\.)*"', lambda m: '"format.penNotIncluded": "' + next(pen_text) + '"', i18n)
    if pens != 3:
        raise ValueError('Reference changed; review required: format.penNotIncluded (%d)' % pens)
    trust = iter([("Direktbezug", "10er-Pack mit Preis je Stück"), ("Direct sourcing", "10-pack with price per piece"), ("Achat direct", "Pack de 10 avec prix à la pièce")])
    i18n, trusts = re.subn(r"'detail\.trust3':'[^']*','detail\.trust4':'[^']*'", lambda m: "'detail.trust3':'%s','detail.trust4':'%s'" % next(trust), i18n)
    if trusts != 3:
        raise ValueError('Reference changed; review required: detail.trust3/4 (%d)' % trusts)
    # Do not claim no third-party script or captured requests in a Telegram test.
    i18n += '\n' + (ROOT/'extensions/i18n-extra.js').read_text()
    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    PUBLIC.mkdir()
    for name, text in [('index.html',html),('app.js',js),('i18n.js',i18n),('styles.css',(SOURCE/'styles.css').read_text()),('variants.js',(SOURCE/'variants.js').read_text().replace("id:p.id+'-dual'", "id:'dual-'+p.id").replace("id:'reusable-pen'", "id:'mehrweg-pen'").replace("concentration:p.concentration,price:p.price,category:p.category,", "concentration:p.concentration,price:window.ELShop.formatPrice('dual-'+p.id,p.price),category:p.category,"))]:
        (PUBLIC/name).write_text(text)
    for name in ['telegram.js','zoom.js','shop-formats.js','terms.js','miniapp.css']:
        shutil.copyfile(ROOT/'extensions'/name, PUBLIC/name)
    # Install storage before i18n/source scripts without exposing any secrets.
    html=(PUBLIC/'index.html').read_text().replace('<script src="i18n.js?v=flagship-03">','<script src="storage.js"></script><script src="i18n.js?v=flagship-03">')
    (PUBLIC/'index.html').write_text(html)
    shutil.copyfile(ROOT/'extensions/storage.js',PUBLIC/'storage.js')
    refs=set(re.findall(r'(?:assets|img)/[A-Za-z0-9_./-]+\.(?:png|jpg|webp|svg|woff2)', html+js+(SOURCE/'styles.css').read_text()))
    missing=[]
    for ref in sorted(refs):
        src=ROOT/'asset-cache-current'/ref
        if not src.is_file():
            if (ROOT/'extensions'/ref).is_file() or ref.startswith('assets/catalog-user/'):
                continue
            missing.append(ref)
            continue
        dst=PUBLIC/ref;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
    # Extension artwork (own schematic graphics, sample catalogue tiles) and operator images.
    shutil.copytree(ROOT/'extensions/assets', PUBLIC/'assets', dirs_exist_ok=True, ignore=shutil.ignore_patterns('shop'))
    user_images = ROOT/'katalog-bilder'
    if user_images.is_dir():
        (PUBLIC/'assets/catalog-user').mkdir(parents=True, exist_ok=True)
        for img in user_images.iterdir():
            if img.is_file() and img.suffix.lower() in {'.png','.jpg','.jpeg','.webp','.svg'}:
                shutil.copyfile(img, PUBLIC/'assets/catalog-user'/img.name)
    shutil.copyfile(ROOT/'extensions/sw.js', PUBLIC/'sw.js')
    optimize_images()
    build_id = hashlib.sha256(b''.join(p.read_bytes() for p in sorted(PUBLIC.rglob('*')) if p.is_file() and p.name != 'sw.js')).hexdigest()[:10]
    sw = PUBLIC/'sw.js'
    sw.write_text(sw.read_text().replace('__BUILD__', build_id))
    manifest={'reference':'https://elements-labs-flagship.vercel.app/','products':len(products),'groups':len({p['group'] for p in products}),'missing_assets':missing,'asset_count':len(refs),'files':{str(p.relative_to(PUBLIC)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(PUBLIC.rglob('*')) if p.is_file()}}
    (ROOT/'evidence/build.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if missing:
        raise FileNotFoundError('Missing reference assets: '+json.dumps(missing))
    print(json.dumps({'products':manifest['products'],'groups':manifest['groups'],'assets':len(refs),'status':'PASS'}))

def build():
    """Build into public.next and swap, so a running server never serves a half-written tree."""
    global PUBLIC
    final = PUBLIC
    staging = final.parent / (final.name + '.next')
    previous = final.parent / (final.name + '.prev')
    PUBLIC = staging
    try:
        _build()
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    finally:
        PUBLIC = final
    shutil.rmtree(previous, ignore_errors=True)
    moved = False
    try:
        if final.exists():
            final.rename(previous)
            moved = True
        staging.rename(final)
    except OSError:
        if moved and not final.exists():
            previous.rename(final)
        shutil.rmtree(staging, ignore_errors=True)
        raise
    shutil.rmtree(previous, ignore_errors=True)


if __name__=='__main__':
    build()
