const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const { chromium, devices } = require('playwright-core');
const ROOT = path.resolve(__dirname, '..');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const OUT = path.join(ROOT, 'evidence', 'handy-browser');
fs.mkdirSync(OUT, {recursive:true});
const navRoutes = ['products','quality','batch-lookup','about','faq'];
const directRoutes = ['home','products','quality','batch-lookup','about','faq','contact','cart'];
const batches = ['EL-BPC5-26001','EL-TB5-26001','EL-GHK50-26001','EL-IPA5-26001','EL-KPV10-26001','EL-SEL5-26001','EL-SMX5-26001','EL-MOT10-26001','EL-CJC5-26001','EL-NAD500-26001','EL-AMQ5-26001','EL-BT10-26001','EL-EPI50-26001'];
function assert(c,m){ if(!c) throw new Error(m); }
function clean(name){ return name.replace(/[^a-z0-9_-]+/gi,'-').toLowerCase(); }
async function noOverflow(page, label){
  const r = await page.evaluate(() => {
    const vw = document.documentElement.clientWidth;
    const bad = [];
    for (const el of document.body.querySelectorAll('*')) {
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden') continue;
      const b = el.getBoundingClientRect();
      if (b.width < 1 || b.height < 1) continue;
      if (b.right > vw + 2 || b.left < -2) bad.push({tag:el.tagName, cls:String(el.className||''), id:el.id, text:(el.innerText||el.alt||'').slice(0,70), left:b.left, right:b.right, width:b.width});
    }
    return {vw, sw:document.documentElement.scrollWidth, bad:bad.slice(0,10)};
  });
  assert(r.sw <= r.vw + 2, `${label}: document overflow ${JSON.stringify(r)}`);
  assert(r.bad.length === 0, `${label}: element overflow ${JSON.stringify(r.bad)}`);
}
async function topHit(page, selector, label){
  const loc = page.locator(selector).first();
  await loc.scrollIntoViewIfNeeded();
  await page.waitForTimeout(80);
  const r = await loc.evaluate(el => {
    const b = el.getBoundingClientRect();
    const x = b.left + Math.min(Math.max(b.width/2, 2), b.width-2);
    const y = b.top + Math.min(Math.max(b.height/2, 2), b.height-2);
    const top = document.elementFromPoint(x,y);
    return {ok: top === el || el.contains(top), top: top ? top.tagName+'.'+String(top.className||'') : 'none', rect:{x:b.x,y:b.y,w:b.width,h:b.height}};
  });
  assert(r.ok, `${label}: covered by ${r.top} ${JSON.stringify(r.rect)}`);
}
async function route(page, hash){
  await page.goto(`file://${ROOT.replace(/\\/g,'/')}/index.html#${hash}`, {waitUntil:'networkidle'});
  await page.waitForSelector('#app');
}
(async()=>{
  const browser = await chromium.launch({executablePath:CHROME, headless:true, args:['--no-sandbox']});
  const context = await browser.newContext({...devices['Pixel 5'], viewport:{width:393,height:851}, isMobile:true, hasTouch:true});
  const page = await context.newPage();
  const consoleErrors=[];
  page.on('console', m => { if(m.type()==='error') consoleErrors.push(m.text()); });
  page.on('pageerror', e => consoleErrors.push(String(e)));
  await route(page, 'home');
  await noOverflow(page, 'mobile home');
  await topHit(page, '#menuToggle', 'hamburger');
  await page.tap('#menuToggle');
  await page.waitForSelector('#mainNav.open');
  await noOverflow(page, 'mobile nav open');
  for (const h of navRoutes) {
    await page.tap('#menuToggle').catch(()=>{});
    if (!(await page.locator('#mainNav.open').count())) await page.tap('#menuToggle');
    await topHit(page, `#mainNav a[href="#${h}"]`, `nav ${h}`);
    await page.tap(`#mainNav a[href="#${h}"]`);
    await page.waitForFunction(hash => location.hash === '#' + hash, h);
    assert(await page.locator('#mainNav.open').count() === 0, `mobile menu stayed open after ${h}`);
    await noOverflow(page, `mobile nav route ${h}`);
  }
  for (const h of directRoutes) { await route(page, h); await noOverflow(page, `mobile direct route ${h}`); }
  await route(page, 'products');
  assert(await page.locator('[data-product-card]').count() === 13, 'product card count != 13');
  await page.fill('#searchInput','nad');
  await page.waitForTimeout(100);
  assert(await page.locator('[data-product-card]').count() === 1, 'search filter failed');
  await page.selectOption('#sortFilter','price-desc');
  await noOverflow(page, 'products filtered');
  await route(page, 'product=bpc-157');
  await topHit(page, '[data-add="bpc-157"]', 'add to cart');
  await page.tap('[data-add="bpc-157"]');
  await route(page, 'cart');
  assert((await page.textContent('#cartTotal')).includes('24,90'), 'cart total wrong');
  for (const b of batches) {
    await route(page, 'batch=' + encodeURIComponent(b));
    assert((await page.textContent('#app')).includes(b), 'batch missing '+b);
    await noOverflow(page, 'batch '+b);
  }
  await route(page,'home'); await page.screenshot({path:path.join(OUT,'mobile-home-browser.png'), fullPage:false});
  await route(page,'products'); await page.screenshot({path:path.join(OUT,'mobile-products-browser.png'), fullPage:false});
  await route(page,'product=epithalon'); await page.screenshot({path:path.join(OUT,'mobile-product-epithalon-browser.png'), fullPage:false});
  await route(page,'batch=EL-AMQ5-26001'); await page.screenshot({path:path.join(OUT,'mobile-batch-browser.png'), fullPage:false});
  await route(page,'cart'); await page.screenshot({path:path.join(OUT,'mobile-cart-browser.png'), fullPage:false});
  await browser.close();
  assert(consoleErrors.length === 0, 'console errors: '+consoleErrors.join(' | '));
  console.log('HANDY_BROWSER_QA PASS');
  console.log('screenshots=' + OUT);
})();
