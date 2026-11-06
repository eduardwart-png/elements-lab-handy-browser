"""Real browser acceptance for the current 25-vial / 25-dual / pen shop.
Run through browser_exec; BASE_URL may be provided (default isolated preview).
Telegram identity acceptance remains a separate real Telegram test.
"""
import json
from pathlib import Path
import shutil
import sqlite3
import time

js = globals()['js']
goto_url = globals()['goto_url']
wait_for_load = globals()['wait_for_load']
cdp = globals()['cdp']
capture_screenshot = globals()['capture_screenshot']
ROOT = Path('/Users/eduardwart/Projekte-Mac/elements-lab-telegram/miniapp')
OUT = ROOT / 'evidence/current-browser-acceptance.json'
BASE = globals().get('BASE_URL', 'http://127.0.0.1:8767/')
results = {'environment': 'real Chromium browser; isolated preview, not Telegram identity acceptance', 'base': BASE,
           'responsive': [], 'variants': [], 'search': [], 'languages': [], 'screenshots': [], 'status': 'RUNNING'}

def save():
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2))

def route(value):
    js('location.hash=' + json.dumps(value) + ';render()')

def rows():
    db = ROOT / 'runtime/acceptance-preview.sqlite3'
    if not db.exists():
        return 0
    with sqlite3.connect(db) as connection:
        return connection.execute('SELECT count(*) FROM requests').fetchone()[0]

cdp('Page.addScriptToEvaluateOnNewDocument', source="window.__qaErrors=[];addEventListener('error',e=>__qaErrors.push(e.message));addEventListener('unhandledrejection',e=>__qaErrors.push(String(e.reason)));")
# Altfaelle der Abnahme laufen ohne Konditionen (nach jeder Navigation neu gesetzt, vor dem ersten Rendern)
cdp('Page.addScriptToEvaluateOnNewDocument', source="document.addEventListener('DOMContentLoaded',()=>{const t=window.ELTerms&&window.ELTerms.terms;if(!t)return;window.__realTerms=JSON.parse(JSON.stringify(t));t.min_order_cents=0;t.collective_min_cents=0;t.shipping_cents=0;t.tiers.length=0;});")
goto_url(BASE)
wait_for_load()
for _ in range(40):
    if js("document.readyState==='complete' && typeof window.ELShop==='object'"):
        break
    time.sleep(.25)
js("setLang('de');if(!document.getElementById('ageGate').classList.contains('hidden')){document.getElementById('ageYes').click();document.getElementById('ageCheckbox').checked=true;document.getElementById('ageCheckbox').dispatchEvent(new Event('change'));document.getElementById('ageConfirmBtn').click()};applyStaticTranslations()")
assert js("!document.body.classList.contains('age-gate-open')")
js("(()=>{const t=ELTerms.terms;if(!window.__realTerms)window.__realTerms=JSON.parse(JSON.stringify(t));t.min_order_cents=0;t.collective_min_cents=0;t.shipping_cents=0;t.tiers.length=0;})()")  # Altfaelle ohne Konditionen; echte Konditionen: Abschnitt 'terms' unten
results['navigation'] = js("Array.from(document.querySelectorAll('.mini-bottom-nav [data-i18n]')).map(x=>x.textContent)")
assert len(results['navigation']) == 6 and all(results['navigation'])
ids = js("[...window.__ELEMENTS_PRODUCTS__,...JSON.parse(document.getElementById('formatData').textContent).filter(x=>!x.pack_size)].map(x=>x.id)")
assert len(set(ids)) == len(ids) == 51
pack_ids = js("JSON.parse(document.getElementById('formatData').textContent).filter(x=>x.pack_size).map(x=>x.id)")
assert len(set(pack_ids)) == len(pack_ids) == 50
save()

routes = ['home','products','dual-chamber','accessories','catalog','product=retatrutide-10','product=dual-retatrutide-10','cart','info','batch-lookup']
for width, height in [(320,740),(390,844),(430,932),(768,1024),(844,390),(1440,1000)]:
    cdp('Emulation.setDeviceMetricsOverride',width=width,height=height,deviceScaleFactor=1,mobile=width<961)
    checks = []
    for name in routes:
        route(name)
        row = js("({width:innerWidth,scroll:document.documentElement.scrollWidth,heading:document.querySelector('#app h1')?.textContent||document.querySelector('#app h2')?.textContent})")
        row['route'] = name
        assert row['scroll'] <= width + 1, row
        assert row['heading'], row
        checks.append(row)
    results['responsive'].append({'width':width,'height':height,'routes':checks})
    save()

cdp('Emulation.setDeviceMetricsOverride',width=390,height=844,deviceScaleFactor=1,mobile=True)
for pid in ids:
    route('product=' + pid)
    row = js("""(async()=>{
      const button=document.querySelector('#app [data-add]');
      const image=document.querySelector('.gallery-main img,.gallery img,.product-detail img');
      if(image&&!image.complete)await Promise.race([new Promise(resolve=>{image.addEventListener('load',resolve,{once:true});image.addEventListener('error',resolve,{once:true})}),new Promise(resolve=>setTimeout(resolve,5000))]);
      return {id:button?.dataset.add,heading:document.querySelector('#app h1')?.textContent,imageLoaded:!!image?.naturalWidth,tabs:document.querySelectorAll('.prod-tab').length};
    })()""")
    assert row['id'] == pid and row['imageLoaded'], (pid,row)
    if not pid.startswith('dual-') and pid != 'mehrweg-pen':
        assert row['tabs'] == 7, row
    results['variants'].append(row)
    save()
assert len({x['id'] for x in results['variants']}) == 51

route('dual-chamber')
assert js("document.getElementById('formatFilter').value")=='dual'
js("document.getElementById('searchInput').value='Retatrutide';document.getElementById('searchInput').dispatchEvent(new Event('input'))")
assert js("document.querySelectorAll('#productGrid .product-card').length")==1
results['search'].append({'query':'Retatrutide','groups':1})
js("document.getElementById('searchInput').value='';document.getElementById('categoryFilter').value='Neuro Research';document.getElementById('categoryFilter').dispatchEvent(new Event('input'))")
assert js("document.querySelectorAll('#productGrid .product-card').length")==2
results['search'].append({'category':'Neuro Research','groups':2})
js("document.getElementById('searchInput').value='ZZZ-NOT-A-PRODUCT';document.getElementById('searchInput').dispatchEvent(new Event('input'))")
assert js("document.querySelectorAll('#productGrid .product-card').length")==0
js("document.getElementById('searchInput').value='';document.getElementById('categoryFilter').value='';document.getElementById('categoryFilter').dispatchEvent(new Event('input'))")
route('accessories')
assert js("document.querySelector('#app h1').innerText")=='Mehrweg-Pen'

# Telegram appends launch parameters to the fragment: the route must survive and the hash must be cleaned.
for entry, expected in [('#cart&tgWebAppData=x&tgWebAppVersion=8.0','cart'),('#dual-chamber&tgWebAppPlatform=ios','dual-chamber'),('#tgWebAppData=x','')]:
    goto_url('about:blank'); goto_url(BASE + entry); wait_for_load(); time.sleep(.8)
    js("if(!document.getElementById('ageGate').classList.contains('hidden')){document.getElementById('ageYes').click();document.getElementById('ageCheckbox').checked=true;document.getElementById('ageCheckbox').dispatchEvent(new Event('change'));document.getElementById('ageConfirmBtn').click()}")
    h = js("location.hash")
    assert 'tgWebApp' not in h and h.lstrip('#') == expected, (entry, h)
    heading = js("document.querySelector('#app h1').innerText")
    assert (expected != 'cart' or 'Warenkorb' in heading) and (expected != 'dual-chamber' or 'Doppelkammer' in heading), (entry, heading)
results['launch_hash'] = 'route preserved and cleaned'
# Search finds concentrations; no placeholder content anywhere in the customer-facing navigation.
route('products/vial'); time.sleep(.6)
assert js("document.getElementById('formatFilter').value")=='vial'
js("document.getElementById('searchInput').value='20 mg';document.getElementById('searchInput').dispatchEvent(new Event('input'))")
assert js("document.querySelectorAll('#productGrid .product-card').length") > 3
js("document.getElementById('searchInput').value='';document.getElementById('searchInput').dispatchEvent(new Event('input'))")
nav_routes = js("Array.from(document.querySelectorAll('.mini-bottom-nav a')).map(a=>a.dataset.miniRoute)")
assert nav_routes == ['home','products/vial','dual-chamber','accessories','packs','cart'], nav_routes
for r_ in ['home','products/vial','dual-chamber','accessories','packs','catalog','info','cart']:
    route(r_)
    text = js("document.getElementById('app').innerText + document.querySelector('.footer').innerText")
    assert not any(x in text for x in ['Musterzeile','SAMPLE','Muster-Eintr']), r_
assert not any('catalog' in x or 'systems' in x for x in js("Array.from(document.querySelectorAll('#mainNav a')).map(a=>a.getAttribute('href'))"))
# Cart +/- keeps the scroll position.
js("cart={'bpc-157':1,'dual-retatrutide-10':1,'mehrweg-pen':1};saveCart()")
route('cart'); js("window.scrollTo({top:200,left:0,behavior:'instant'})"); time.sleep(.2)
js("document.querySelector('[data-qty]').click()"); time.sleep(.2)
assert js("window.scrollY") > 100, js("window.scrollY")
results['catalog_hidden_and_search'] = 'ok'

# Bot buttons use ?r=<route>.
for entry, expected in [('?r=dual-chamber','dual-chamber'),('?r=product%3Ddual-bpc-157','product=dual-bpc-157'),('?r=cart#tgWebAppData=x','cart')]:
    goto_url('about:blank'); goto_url(BASE + entry); wait_for_load(); time.sleep(.8)
    h = js("location.hash.slice(1)"); q = js("location.search")
    assert h == expected and q == '', (entry, h, q)
# Back from a detail page keeps filter and scroll position of the list.
route('products/vial'); time.sleep(.5)
js("document.getElementById('searchInput').value='ret';document.getElementById('searchInput').dispatchEvent(new Event('input'))"); time.sleep(.3)
before = js("document.querySelectorAll('#productGrid .product-card').length")
js("window.scrollTo({top:150,left:0,behavior:'instant'})"); time.sleep(.2)
js("document.querySelector('#productGrid [href^=\"#product=\"]').click()"); time.sleep(.6)
assert js("location.hash").startswith('#product='), js("location.hash")
js("history.back()"); time.sleep(.9)
assert js("document.getElementById('searchInput').value") == 'ret'
assert js("document.querySelectorAll('#productGrid .product-card').length") == before
assert js("window.scrollY") >= 100, js("window.scrollY")
# Batch lookup: Enter works in the main input too.
route('batch-lookup'); time.sleep(.4)
js("const i=document.getElementById('batchInput');i.value='EL-RET10-26001';i.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}))"); time.sleep(.4)
assert 'batch=' in js("location.hash"), js("location.hash")
# Plural, pen back button spacing, keyboard hides the bottom navigation, contact page offers a next step.
route('products/vial'); time.sleep(.4)
assert 'VARIANTEN' in js("document.getElementById('productGrid').innerText").upper() and '1 VARIANTEN' not in js("document.getElementById('productGrid').innerText").upper()
route('accessories'); time.sleep(.4)
gap = js("(()=>{const b=document.querySelector('#app .format-tabs').getBoundingClientRect(),g=document.querySelector('#app .gallery').getBoundingClientRect();return g.top-b.bottom})()")
assert gap > 4, gap
route('products/vial'); time.sleep(.3)
js("document.getElementById('searchInput').dispatchEvent(new FocusEvent('focusin',{bubbles:true}))"); time.sleep(.3)
assert js("getComputedStyle(document.querySelector('.mini-bottom-nav')).display") == 'none'
js("document.getElementById('searchInput').dispatchEvent(new FocusEvent('focusout',{bubbles:true}))"); time.sleep(.4)
assert js("getComputedStyle(document.querySelector('.mini-bottom-nav')).display") != 'none'
route('contact'); time.sleep(.4)
assert js("!!document.querySelector('#contactHelp a[href=\"#cart\"]')")
results['bot_query_back_state_batch_enter'] = 'ok'

# Round 2 findings: alias list state, detail back link target, history trail.
route('dual-chamber'); time.sleep(.5)
js("document.getElementById('searchInput').value='ret';document.getElementById('searchInput').dispatchEvent(new Event('input'))"); time.sleep(.5)
n_dual = js("document.querySelectorAll('#productGrid .product-card').length")
js("document.querySelector('#productGrid [href^=\"#product=\"]').click()"); time.sleep(.6)
assert js("document.querySelector('#app a.secondary-btn').getAttribute('href')") == '#dual-chamber', js("document.querySelector('#app a.secondary-btn').getAttribute('href')")
js("history.back()"); time.sleep(.9)
assert js("document.getElementById('searchInput').value") == 'ret' and js("document.querySelectorAll('#productGrid .product-card').length") == n_dual
route('products/vial'); time.sleep(.4)
js("document.querySelector('#productGrid [href^=\"#product=\"]').click()"); time.sleep(.5)
assert js("document.querySelector('#app a.secondary-btn').getAttribute('href')") == '#products/vial'
route('accessories'); time.sleep(.4)
assert js("document.querySelector('#app a.secondary-btn[href]')?.getAttribute('href')") in ('#accessories', '#products', None) 
results['round2_alias_back'] = 'ok'

# Customer journeys: every area opens with its own overview (round 3 owner finding).
expect = {'products/vial': ('Vials', 'Vials'), 'dual-chamber': ('Doppelkammern', 'Doppelkammer'), 'accessories': ('Mehrweg-Pen', 'Mehrweg-Pen')}
for r_, (h1, tab) in expect.items():
    route(r_); time.sleep(.7)
    got = js("({h1:document.querySelector('#app h1').innerText, active:[...document.querySelectorAll('.format-tabs a[aria-current=page]')].map(a=>a.innerText), nav:[...document.querySelectorAll('.mini-bottom-nav a[aria-current=page]')].length})")
    assert got['h1'] == h1 and len(got['active']) == 1 and got['active'][0].startswith(tab) and got['nav'] == 1, (r_, got)
    assert 'Doppelkammern. Pen. Vials.' not in js("document.getElementById('app').innerText"), r_
for r_ in ('products/vial', 'dual-chamber'):
    route(r_); time.sleep(.6)
    n = js("document.querySelectorAll('#productGrid .product-card').length")
    assert js("document.getElementById('resultCount').innerText").startswith(str(n) + ' '), (r_, n)
    assert js("document.querySelectorAll('#productGrid .price').length") == n
    tabs = js("[...document.querySelectorAll('.format-tabs a span')].map(s=>s.innerText)")
    assert tabs[:2] == [str(n), str(n)] and tabs[2] == '1', (r_, tabs)
    assert js("getComputedStyle(document.getElementById('formatFilter')).display") == 'none'
    assert js("location.hash") == '#' + r_  # filter use must not rewrite the route
    js("document.getElementById('categoryFilter').selectedIndex=1;document.getElementById('categoryFilter').dispatchEvent(new Event('input'))"); time.sleep(.3)
    assert js("location.hash") == '#' + r_ and 0 < js("document.querySelectorAll('#productGrid .product-card').length") < n
# Switching between the areas through the tabs ends on the right page every time.
route('products/vial'); time.sleep(.5)
js("[...document.querySelectorAll('.format-tabs a')].find(a=>a.getAttribute('href')==='#dual-chamber').click()"); time.sleep(.6)
assert js("document.querySelector('#app h1').innerText") == 'Doppelkammern'
js("[...document.querySelectorAll('.format-tabs a')].find(a=>a.getAttribute('href')==='#accessories').click()"); time.sleep(.6)
assert js("document.querySelector('#app h1').innerText") == 'Mehrweg-Pen' and js("!!document.querySelector('[data-add]')")
js("[...document.querySelectorAll('.format-tabs a')].find(a=>a.getAttribute('href')==='#products/vial').click()"); time.sleep(.6)
assert js("document.querySelector('#app h1').innerText") == 'Vials'
# Pen: the buy button is on screen without scrolling past the bottom navigation.
route('accessories'); time.sleep(.6)
box = js("(()=>{const b=document.querySelector('[data-add]').getBoundingClientRect(),n=document.querySelector('.mini-bottom-nav').getBoundingClientRect();return {bottom:b.bottom,navTop:n.top,vh:innerHeight}})()")
assert box['bottom'] <= box['navTop'] + 1, box
# Review round 3: alias route highlights its tab; back link of a dual-chamber variant returns to the dual list.
route('products/dual'); time.sleep(.6)
assert js("[...document.querySelectorAll('.format-tabs a[aria-current=page]')].map(a=>a.innerText.split('\\n')[0])") == ['Doppelkammer']
route('dual-chamber'); time.sleep(.4)
js("location.hash='product=retatrutide-10-dual'"); time.sleep(.8)
assert js("document.querySelector('#app a.secondary-btn')?.getAttribute('href')") == '#dual-chamber', js("document.querySelector('#app a.secondary-btn')?.getAttribute('href')")
results['customer_journeys'] = 'ok'

for language in ['en','fr','de']:
    js('setLang(' + json.dumps(language) + ')')
    route('dual-chamber')
    assert js('document.documentElement.lang') == language
    labels = js("Array.from(document.querySelectorAll('.mini-bottom-nav [data-i18n]')).map(x=>x.textContent)")
    assert all(labels), labels
    results['languages'].append({'language':language,'heading':js("document.querySelector('#app h1').innerText"),'nav':labels})

route('batch=EL-RET10-26001')
assert js("document.getElementById('batchResult').innerText.includes('Retatrutide')")
route('batch=NOT-A-REAL-BATCH')
assert js("document.getElementById('batchResult').innerText.includes('NOT-A-REAL-BATCH')")
route('product=does-not-exist')
assert js("document.querySelectorAll('#app [data-add]').length") == 0
route('%E0%A4%A')
assert js("!!document.querySelector('#app h1')")

js("cart={};saveCart()")
for pid in ['bpc-157','dual-retatrutide-10','mehrweg-pen']:
    route('product=' + pid)
    js("document.querySelector('#app [data-add]').click()")
route('cart')
assert js("document.querySelectorAll('.quote-line').length") == 3
assert 'NaN' not in js("document.querySelector('#app').innerText")
before = rows()
js("document.getElementById('checkoutBtn').click()")
saved = ''
for _ in range(50):
    saved = js("document.getElementById('orderFeedback').dataset.orderId||''")
    if saved:
        break
    time.sleep(.2)
assert saved.startswith('EL-TEST-'), js("document.getElementById('orderFeedback').textContent")
assert js('Object.keys(cart).length') == 0
assert js("document.getElementById('checkoutBtn').disabled")
assert rows() == before + 1
with sqlite3.connect(ROOT / 'runtime/acceptance-preview.sqlite3') as connection:
    payload = json.loads(connection.execute('SELECT payload FROM requests WHERE id=?',(saved,)).fetchone()[0])
assert payload['total_cents'] == 14980 and payload['known_total_cents'] == 14980 and payload['quote_items'] == 0
assert len(payload['items']) == 3
results['saved_request'] = {'id':saved,'known_total_cents':14980,'quote_items':0,'row_count_before':before,'row_count_after':rows()}
# A second click on the disabled button sends nothing (server-side idempotency is covered by the unit tests).
js("document.getElementById('checkoutBtn').click()")
time.sleep(.3)
assert rows() == before + 1
assert js("document.getElementById('orderFeedback').dataset.orderId") == saved

# Deliberate UI error for a fresh cart: no false success and no write.
js("addToCart('bpc-157');addToCart('dual-retatrutide-10');addToCart('mehrweg-pen');render()")
js("window.__realFetch=window.fetch;window.fetch=async()=>({ok:false,json:async()=>({error:'deliberate acceptance failure'})});document.getElementById('checkoutBtn').click()")
time.sleep(.25)
assert not js("document.getElementById('orderFeedback').dataset.orderId")
assert js("document.getElementById('orderFeedback').textContent.includes('nicht gespeichert')")
assert not js("document.getElementById('checkoutBtn').disabled")
assert rows() == before + 1
js("window.fetch=window.__realFetch")
results['negative_paths'] = ['unknown product','unknown batch','malformed route','failed save has no success state and no write','second click on disabled button sends no request']

# --- 10er-Packungen (Split-Einkauf): Katalogseite, Produktseiten, Warenkorb, Preis-Konsistenz
cdp('Emulation.setDeviceMetricsOverride',width=390,height=844,deviceScaleFactor=1,mobile=True)
js("setLang('de');cart={};saveCart()")
route('packs')
time.sleep(.4)
row = js("({rows:document.querySelectorAll('#packList .pack-row').length,groups:document.querySelectorAll('#packList .pack-group').length,cells:document.querySelectorAll('#packList .pack-cell[data-add]').length,stats:[...document.querySelectorAll('.pack-stats strong')].map(x=>x.textContent),tabs:document.querySelectorAll('#app .format-tabs a').length,active:document.querySelector('#app .format-tabs a[aria-current=page]')?.getAttribute('href'),scroll:document.documentElement.scrollWidth,count:document.getElementById('packCount').textContent})")
assert row['cells'] == 239 and row['groups'] == 8 and row['stats'][:2] == ['124', '115'] and row['tabs'] == 4 and row['scroll'] <= 391 and row['active'] == '#packs', row
assert row['rows'] > 130, row
# type filter: only Doppelkammer cells
js("document.querySelector('[data-pack-type=\"dual_pack\"]').click()")
only_dual = js("({cells:document.querySelectorAll('#packList .pack-cell[data-add]').length,vial:document.querySelectorAll('#packList [data-add^=\"cat-vial\"],#packList [data-add$=\"-x10\"]:not([data-add^=\"dual-\"]):not([data-add^=\"cat-dual\"])').length})")
assert only_dual == {'cells': 115, 'vial': 0}, only_dual
js("document.querySelector('[data-pack-type=\"\"]').click()")
# section filter from the chips
js("document.querySelector('[data-pack-section=\"Hormone & Wachstum\"]').click()")
sec = js("({groups:document.querySelectorAll('#packList .pack-group').length,title:document.querySelector('#packList .pack-group h2').firstChild.textContent,pressed:document.querySelector('[data-pack-section=\"Hormone & Wachstum\"]').getAttribute('aria-pressed')})")
assert sec == {'groups': 1, 'title': 'Hormone & Wachstum', 'pressed': 'true'}, sec
js("document.querySelector('[data-pack-section=\"\"]').click()")
# search
js("(()=>{const q=document.getElementById('packSearch');q.value='retatrutide';q.dispatchEvent(new Event('input',{bubbles:true}))})()")
found = js("[...document.querySelectorAll('#packList .pack-row .pack-name strong')].map(x=>x.textContent)")
assert found and all('retatrutide' in x.lower() for x in found) and len(found) >= 8, found
js("(()=>{const q=document.getElementById('packSearch');q.value='zzzz';q.dispatchEvent(new Event('input',{bubbles:true}))})()")
assert js("document.querySelectorAll('#packList .pack-row').length") == 0 and 'Keine Treffer' in js("document.getElementById('packList').innerText")
js("(()=>{const q=document.getElementById('packSearch');q.value='retatrutide';q.dispatchEvent(new Event('input',{bubbles:true}))})()")
# prices of the owner's sales sheet in the cells
cell = js("(()=>{const b=document.querySelector('#packList [data-add=\"retatrutide-20-x10\"]');return {price:b.querySelector('strong').textContent,label:b.getAttribute('aria-label')}})()")
expected = js("fmt(ELShop.byId('retatrutide-20-x10').price_cents/100)")  # Preis aus den Shopdaten, nicht fest verdrahtet
assert cell['price'] == expected and '10er-Pack' in cell['label'], (cell, expected)
js("document.querySelector('#packList [data-add=\"retatrutide-10-x10\"]').click()")
assert js("cart['retatrutide-10-x10']") == 1
# catalogue-only article (no product page): orderable, cart line without broken link
js("(()=>{const q=document.getElementById('packSearch');q.value='semaglutide';q.dispatchEvent(new Event('input',{bubbles:true}))})()")
js("document.querySelector('#packList [data-add=\"cat-vial-semaglutide-40-mg\"]').click()")
assert js("cart['cat-vial-semaglutide-40-mg']") == 1
route('cart')
cl = js("({lines:document.querySelectorAll('.quote-line').length,hrefs:[...document.querySelectorAll('.quote-line h2 a')].map(a=>a.getAttribute('href')),imgs:[...document.querySelectorAll('.quote-line img[src^=\"data:\"]')].every(i=>i.complete&&i.naturalWidth>0),total:document.getElementById('cartTotal').textContent,sum:fmt(ELShop.summary(cart).known_total_cents/100)})")
assert cl['lines'] == 2 and '#packs' in cl['hrefs'] and cl['imgs'] and cl['total'] == cl['sum'], cl
js("cart={};saveCart()")
route('packs')
time.sleep(.3)
js("(()=>{const q=document.getElementById('packSearch');q.value='retatrutide';q.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('#packList .pack-name a[href=\\\"#product=retatrutide-10\\\"]').click()})()")
time.sleep(.5)
assert js("location.hash") == '#product=retatrutide-10', js("location.hash")
assert js("document.querySelector('#app a.secondary-btn')?.getAttribute('href')") == '#packs', 'back from a product opened out of the packs list returns to the packs list'
js("history.back()")
time.sleep(.4)
assert js("location.hash") == '#packs'
js("cart={};saveCart()")
js("document.querySelector('#packList [data-add=\"retatrutide-10-x10\"]')?.click()")
# home teaser and the banner on the format pages lead into the catalogue
route('home')
time.sleep(.5)
teaser = js("({has:!!document.querySelector('.pack-teaser'),links:document.querySelectorAll('.pack-teaser-sections a').length,title:document.querySelector('.pack-teaser h2')?.textContent,scroll:document.documentElement.scrollWidth})")
assert teaser['has'] and teaser['links'] == 8 and teaser['scroll'] <= 391 and '230' in teaser['title'], teaser
js("document.querySelector('.pack-teaser-sections a[data-pack-section=\"Beauty & Anti-Aging\"]').click()")
time.sleep(.5)
assert js("location.hash") == '#packs'
assert js("document.querySelector('[data-pack-section=\"Beauty & Anti-Aging\"]').getAttribute('aria-pressed')") == 'true' and js("document.querySelectorAll('#packList .pack-group').length") == 1
route('dual-chamber')
time.sleep(.4)
assert js("!!document.querySelector('.pack-banner')") and js("document.querySelector('.pack-banner').getAttribute('href')") == '#packs'
js("cart={};saveCart()")
route('packs')
time.sleep(.3)
js("document.querySelector('#packList [data-add=\"retatrutide-10-x10\"]').click()")
assert js("cart['retatrutide-10-x10']") == 1
results['packs_page'] = {'cells': 239, 'groups': 8, 'rows': row['rows'], 'tabs': 4, 'dual_only_cells': 115}
for pid, pack_id in [('retatrutide-10','retatrutide-10-x10'),('semaglutide-20','semaglutide-20-x10'),('dual-retatrutide-10','dual-retatrutide-10-x10'),('dual-tirzepatide-30','dual-tirzepatide-30-x10')]:
    route('product=' + pid)
    info = js("""(()=>{const f=JSON.parse(document.getElementById('formatData').textContent);const pack=f.find(x=>x.id=="%s");const own=f.find(x=>x.id=="%s");
      const buttons=[...document.querySelectorAll('#app [data-add]')].map(b=>b.dataset.add);
      const block=document.querySelector('.pack-offer');
      return {first:buttons[0],buttons,packPrice:pack.price,ownPrice:own?own.price:null,shown:document.querySelector('.price')?.textContent.trim(),block:block?block.innerText:'',scroll:document.documentElement.scrollWidth}})()""" % (pack_id, pid))
    assert info['first'] == pid and pack_id in info['buttons'], info
    assert info['packPrice'].replace(' ', '\xa0') in info['block'].replace(' ', '\xa0'), info
    assert info['ownPrice'] is None or info['shown'].replace('\xa0', ' ') == info['ownPrice'], info   # dual detail shows the dual price, not the vial price
    assert info['scroll'] <= 391, info
js("document.querySelector('.pack-offer [data-add]').click()")
route('cart')
lines = js("document.querySelectorAll('.quote-line').length")
total_ui = js("document.getElementById('cartTotal').textContent")
total_js = js("fmt(ELShop.summary(cart).known_total_cents/100)")
assert lines == 2 and total_ui == total_js, (lines, total_ui, total_js)
assert js("document.querySelector('.quote-line a').getAttribute('href')").startswith('#product='), 'pack line links to its base product'
results['packs_cart'] = {'lines': lines, 'total': total_ui}
js("cart={};saveCart()")

# --- echte Konditionen: Mindestbestellwert, Versandpauschale, Gratisversand-Balken, Mengenrabatt, Sammelbestellung
js("(()=>{const t=ELTerms.terms,r=window.__realTerms;Object.assign(t,{min_order_cents:r.min_order_cents,collective_min_cents:r.collective_min_cents,shipping_cents:r.shipping_cents});t.tiers.splice(0,t.tiers.length,...r.tiers);ELTerms.setCollective(false)})()")
pack = js("ELShop.byId('retatrutide-20-x10')")
vial = js("window.__ELEMENTS_PRODUCTS__[0].id")
def panel(cart_expr):
    js("cart=" + cart_expr + ";saveCart();location.hash='cart';render()")
    time.sleep(.3)
    return js("({btn:document.getElementById('checkoutBtn').disabled,btnText:document.getElementById('checkoutBtn').textContent,total:document.getElementById('cartTotal').textContent,box:!!document.querySelector('.tm-box'),note:(document.getElementById('minOrderNote')||{}).textContent||'',bar:(document.querySelector('.tm-bar-text')||{}).textContent||'',collective:!!document.getElementById('collectiveToggle'),lines:[...document.querySelectorAll('.tm-lines > div')].map(x=>x.textContent)})")
terms_results = {}
r = panel("{'%s':1}" % vial)
assert r['btn'] and r['note'].startswith('Mindestbestellwert 500') and r['collective'] and 'Noch' in r['bar'], r
terms_results['below_minimum'] = r
js("document.getElementById('collectiveToggle').click()"); time.sleep(.3)
assert js("document.getElementById('checkoutBtn').disabled"), 'Sammelbestellung unter 200 EUR bleibt gesperrt'
js("ELTerms.setCollective(false)")
r = panel("{'retatrutide-20-x10':2}")
expected_total = js("fmt((2*ELShop.byId('retatrutide-20-x10').price_cents+ELTerms.terms.shipping_cents)/100)")  # aus den Shopdaten, nicht fest verdrahtet
assert 2 * pack['price_cents'] >= js("ELTerms.terms.min_order_cents") and 2 * pack['price_cents'] < js("ELTerms.terms.free_shipping_cents"), 'Testware muss zwischen Mindestwert und Gratisversand liegen'
assert not r['btn'] and r['total'] == expected_total and any('Versand' in x and '80' in x for x in r['lines']) and 'Noch' in r['bar'], (r, expected_total)
terms_results['minimum_reached'] = r
r = panel("{'retatrutide-20-x10':3}")
assert not r['btn'] and not r['collective'] and 'Gratisversand erreicht' in r['bar'] and any('kostenlos' in x for x in r['lines']), r
terms_results['free_shipping'] = r
r = panel("{'retatrutide-20-x10':7}")
if pack.get('discount_ok'):
    assert any('Mengenrabatt 5 %' in x for x in r['lines']), r
terms_results['volume_discount'] = r
panel("{'%s':5}" % vial)
js("document.getElementById('collectiveToggle').click()"); time.sleep(.3)
r = js("({btn:document.getElementById('checkoutBtn').disabled,lines:[...document.querySelectorAll('.tm-lines > div')].map(x=>x.textContent),total:document.getElementById('cartTotal').textContent})")
vial_cents = js("ELShop.byId('%s').price_cents" % vial)
if 5 * vial_cents >= 20000:
    assert not r['btn'] and any('Sammelversand' in x for x in r['lines']), r
terms_results['collective'] = r
js("ELTerms.setCollective(false)")
panel("{'retatrutide-20-x10':2}")
for attempt in range(3):
    try:
        shutil.copyfile(capture_screenshot(), ROOT / 'evidence/screenshots/current-cart-terms.png')
        break
    except RuntimeError:
        time.sleep(3)
results['terms'] = terms_results
js("(()=>{const t=ELTerms.terms;t.min_order_cents=0;t.collective_min_cents=0;t.shipping_cents=0;t.tiers.length=0;ELTerms.setCollective(false)})()")
js("cart={};saveCart()")
save()

for name, filename in [('home','current-home'),('products','current-vials'),('dual-chamber','current-duals'),('accessories','current-pen'),('product=dual-retatrutide-10','current-dual-detail'),('packs','current-packs'),('product=retatrutide-20','current-detail-pack'),('cart','current-cart')]:
    route(name)
    time.sleep(.2)
    target = ROOT / 'evidence/screenshots' / (filename+'.png')
    for attempt in range(3):  # headless capture can time out under load; the assertions above already ran
        try:
            shutil.copyfile(capture_screenshot(), target)
            break
        except RuntimeError:
            time.sleep(3)
            if attempt == 2:
                raise
    results['screenshots'].append(str(target))
results['errors'] = js('window.__qaErrors||[]')
assert not results['errors'], results['errors']
results['status'] = 'PASS'
save()
print(json.dumps({'status':'PASS','viewports':len(results['responsive']),'variants':len(results['variants']),'saved_request':saved,'errors':results['errors']},ensure_ascii=False))
print(str(OUT))
