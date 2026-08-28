
const { chromium } = require('playwright');
const path = require('path');
(async()=>{
  const root = process.argv[2];
  const browser = await chromium.launch({headless:true});
  const page = await browser.newPage({viewport:{width:390,height:900}});
  const url = 'file:///' + path.join(root,'_standalone.html').replace(/\\/g,'/');
  const errors=[];
  page.on('console', m => { if(m.type()==='error') errors.push(m.text()); });
  await page.goto(url+'#products');
  await page.waitForSelector('[data-product-card]');
  const count = await page.locator('[data-product-card]').count();
  await page.click('[data-add="bpc-157"]');
  await page.goto(url+'#cart');
  await page.waitForSelector('#cartTotal');
  const cart = await page.textContent('body');
  await page.goto(url+'#batch=EL-AMQ5-26001');
  await page.waitForSelector('#batchResult');
  const batch = await page.textContent('#batchResult');
  const qrSrc = await page.locator('.qr').first().getAttribute('src');
  const overflow = await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
  await browser.close();
  if(count!==13 || !cart.includes('24,90') || !batch.includes('EL-AMQ5-26001') || !String(qrSrc).startsWith('data:image/png;base64,') || overflow>2 || errors.length){
    console.error(JSON.stringify({count, cart:cart.slice(0,120), batch, qrSrc:String(qrSrc).slice(0,30), overflow, errors}, null, 2));
    process.exit(1);
  }
  console.log('PASS standalone file:// interactive: products=13 cart=batch QR=data mobile-overflow=0');
})();
