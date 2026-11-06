
/* ===== AGE GATE INIT (P0) — runs before all other code ===== */
(function initAgeGate(){
  const key='elementsAgeGateConfirmed';
  const overlay=document.getElementById('ageGate');
  if(!overlay)return;
  if(window.ELStore.get(key)==='1'){overlay.classList.add('hidden');return;}
  document.body.classList.add('age-gate-open');
  let ageYes=false;
  const yBtn=document.getElementById('ageYes'),nBtn=document.getElementById('ageNo'),cb=document.getElementById('ageCheckbox'),confirmBtn=document.getElementById('ageConfirmBtn'),blockedMsg=document.getElementById('ageBlockedMsg');
  function upd(){confirmBtn.disabled=!(ageYes&&cb.checked);}
  yBtn.onclick=function(){ageYes=true;yBtn.classList.add('selected');nBtn.classList.remove('selected');blockedMsg.style.display='none';upd();};
  nBtn.onclick=function(){ageYes=false;nBtn.classList.add('selected');yBtn.classList.remove('selected');blockedMsg.style.display='block';confirmBtn.disabled=true;};
  cb.onchange=upd;
  confirmBtn.onclick=function(){window.ELStore.set(key,'1');overlay.classList.add('hidden');document.body.classList.remove('age-gate-open');};
})();

/* ===== UTILITIES ===== */
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
const products = JSON.parse(document.getElementById('productData').textContent);
window.__ELEMENTS_PRODUCTS__ = products;
const {dual:dualProducts,pen} = window.buildVariantCatalog(products);
const sellableProducts=[...products,...dualProducts,pen];
window.__ELEMENTS_OFFERS__=sellableProducts;
let catalogForm='dual',catalogDedicated=false;
function formLabel(p){return t('format.'+(p.form||'vial'));}
window.__ELEMENTS_RESEARCH__ = JSON.parse((document.getElementById('researchData')||{textContent:'{}'}).textContent);
const money = v => Number(String(v).replace('€','').replace('.','').replace(',','.').trim());
const fmt = n => n.toLocaleString('de-DE',{style:'currency',currency:'EUR'});
let cart = {};
try{cart = window.ELMini.cleanCart(JSON.parse(window.ELStore.get('elementsTelegramCart') || '{}'));}catch(e){cart = {};}
const app = document.getElementById('app');
function saveCart(){window.ELStore.set('elementsTelegramCart', JSON.stringify(cart)); updateCartCount();}
function updateCartCount(){document.getElementById('cartCount').textContent = Object.values(cart).reduce((a,b)=>a+b,0);window.ELMini.syncNav();}
function toast(t){const el=document.getElementById('toast');el.textContent=t;el.classList.add('show-toast');setTimeout(()=>el.classList.remove('show-toast'),1500)}
function addToCart(id,qty=1){if(!pById(id)||!Number.isInteger(qty)||qty<1)return;cart[id]=Math.min(99,(cart[id]||0)+qty);saveCart();toast(t('cart.added'));}
function removeFromCart(id){if(window.ELMini.isBusy())return;delete cart[id];saveCart();render()}
function setQty(id,qty){if(window.ELMini.isBusy()||!pById(id)||!Number.isInteger(qty))return;if(qty<=0)delete cart[id];else cart[id]=Math.min(99,qty);saveCart();render()}
function pById(id){const key=id==='reusable-pen'?'mehrweg-pen':id.endsWith('-dual')?'dual-'+id.slice(0,-5):id;return sellableProducts.find(p=>p.id===key)||window.ELShop.byId(key)}
/* ===== VARIANT GROUPING ===== */
function concNum(c){const m=String(c).replace(',','.').match(/([\d.]+)/);return m?parseFloat(m[1]):0}
function variantsOf(g,form='vial'){return (form==='dual'?dualProducts:products).filter(p=>p.group===g).sort((a,b)=>concNum(a.concentration)-concNum(b.concentration))}
/* One representative entry per product group, cheapest variant first. */
function productGroups(form='vial'){
  const seen=[];
  products.forEach(p=>{if(!seen.includes(p.group))seen.push(p.group)});
  return seen.map(g=>{
    const v=variantsOf(g,form);
    const lead=v.slice().sort((a,b)=>money(a.price)-money(b.price))[0];
    return {group:g,variants:v,lead,featured:v.some(x=>x.featured),
            minPrice:Math.min(...v.map(x=>money(x.price)))};
  });
}
function groupOf(id){const p=pById(id);return p?p.group:null}
/* Localized product fields — names/codes/batches stay language-neutral. */
function pDesc(p){return t(p.descKey||('desc.'+p.group))}
function pCat(p){return t('cat.'+p.category)}
function pByBatch(b){return products.find(p=>p.batch.toLowerCase()===String(b||'').toLowerCase())}

/* ===== PRODUCT CARD (group-aware) ===== */
function productCard(g){
  const lead=g.lead, target=g.pick||lead.id, n=g.variants.length, multi=n>1;
  const priceLabel = multi
    ? `<span class="price"><em class="price-from">${esc(t('products.from'))}</em> ${lead.price}</span>`
    : `<span class="price">${lead.price}</span>`;
  const metaLabel = multi
    ? `${g.variants.map(v=>esc(v.concentration)).join(' · ')}`
    : esc(lead.concentration);
  // Open the detail so users deliberately choose packaging before adding.
  const action = `<a class="primary-btn card-options" href="#product=${target}" aria-label="${esc(t('products.openAria',{name:lead.name}))}">${esc(t('products.options'))}</a>`;
  return `<article class="product-card ${g.featured?'featured':''}" data-product-card data-format="${lead.form||'vial'}" data-group="${g.group}">
    <div class="card-top"><span>${lead.num}</span><span>${esc(formLabel(lead))}${lead.form==='dual'?' · '+esc(t('shop.penIncluded')):''} · ${n} ${esc(n===1?t('products.variant1'):t('products.variants'))}</span></div>
    <a class="product-img-wrap" href="#product=${target}" aria-label="${esc(t('products.openAria',{name:lead.name}))}"><img src="${lead.image.replace(/\.webp(\?|$)/,'-card.webp$1')}" width="560" height="392" alt="${esc(lead.name)} ${esc(lead.concentration)} Elements Labs ${esc(formLabel(lead))}"></a>
    <h3>${esc(lead.name)}</h3>
    <div class="compound-meta">${metaLabel}</div>
    <div class="price-row">${priceLabel}${action}</div>
  </article>`;
}
function resultText(n){return n+' '+t(n===1?'fmt.substance1':'fmt.substances')}
function formatHero(){const dual=catalogForm==='dual';return `<header class="format-hero"><div class="eyebrow">ELEMENTS LABS · ${esc(t('fmt.catalog'))}</div><h1 class="page-title">${esc(t(dual?'fmt.dualTitle':'fmt.vialTitle'))}</h1><p class="lead">${esc(t(dual?'fmt.dualLead':'fmt.vialLead'))}</p>${window.ELShop.navigation()}</header>`}
function renderProductGrid(list){return list.length?list.map(productCard).join(''):`${window.ELShop.emptyProducts((document.getElementById('searchInput')||{}).value||'')}`}

/* ===== PRODUCT DETAIL TABS (V7) ===== */
function productTabContent(p){
  const rp=(window.__ELEMENTS_RESEARCH__||{})[p.researchKey||p.id];
  const tabs=[
    {id:'desc',label:t('tab.desc')},
    {id:'coa',label:t('tab.coa')},
    {id:'use',label:t('tab.use')},
    {id:'storage',label:t('tab.storage')},
    {id:'disclaimer',label:t('tab.disclaimer')},
    {id:'shipping',label:t('tab.shipping')},
    {id:'faq',label:t('tab.faq')}
  ];
  const warnBox=`<div style="display:flex;align-items:flex-start;gap:8px;background:#FEF2F2;border:1px solid #FCA5A5;border-radius:6px;padding:10px 14px;margin:14px 0;font-size:13px;color:#7F1D1D;font-weight:600"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="flex-shrink:0;margin-top:1px"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>${esc(t('tab.warnBox'))}</div>`;
  const ctx=rp?(rp.research_context||rp.evidence_summary||'').slice(0,500):'';
  const contents={
    desc:`<p>${esc(pDesc(p))}</p>${rp?`<h4>${esc(t('tab.researchFocus'))}</h4><p>${esc(rp.research_focus||'')}</p><h4>${esc(t('tab.sciContext'))}</h4><p>${esc(ctx)}${ctx.length>=500?'…':''}</p>`:''}`,
    coa:`<p>${esc(t('tab.coaP1'))}</p>
<div style="background:#FFF3CD;border:1px solid #F0C040;border-radius:6px;padding:12px 16px;margin:16px 0;font-size:13px"><strong>${esc(t('tab.coaStatus'))}</strong><br>${esc(t('tab.coaStatusText'))}</div>
<h4>${esc(t('tab.coaH'))}</h4><p>${esc(t('tab.coaList'))}</p>`,
    use:rp?`<p>${esc(t('tab.useP1'))}</p>
<h4>${esc(t('tab.useH1'))}</h4><p>${esc(rp.research_focus||'')}</p>
<h4>${esc(t('tab.useH2'))}</h4><p>${esc(rp.mechanism_summary||'')}</p>${warnBox}`
    :`<p>${esc(t('tab.useFallback'))}</p>${warnBox}`,
    storage:`<p>${esc(t('tab.storageP1'))}</p>
<h4>${esc(t('tab.storageH'))}</h4>
<ul><li>${esc(t('tab.storageLi1'))}</li><li>${esc(t('tab.storageLi2'))}</li><li>${esc(t('tab.storageLi3'))}</li><li>${esc(t('tab.storageLi4'))}</li></ul>
<p style="font-size:12.5px;color:var(--muted)">${esc(t('tab.storageNote'))}</p>`,
    disclaimer:`<p>${esc(t('tab.discP1'))}</p>
<div style="display:flex;align-items:flex-start;gap:10px;background:#FEF2F2;border:1px solid #FCA5A5;border-radius:8px;padding:16px;margin:16px 0;font-size:13px;color:#7F1D1D">
<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="flex-shrink:0;margin-top:1px"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
<span><strong>${esc(t('tab.discStrong'))}</strong> ${esc(t('tab.discText'))}</span>
</div>
<p>${esc(t('tab.discP2'))}</p>`,
    shipping:`<p>${esc(t('tab.shipP1'))}</p>
<div style="background:#FFF3CD;border:1px solid #F0C040;border-radius:6px;padding:12px 16px;margin:16px 0;font-size:13px">
<strong>${esc(t('tab.shipStatus'))}</strong> — ${esc(t('tab.shipStatusText'))}
</div>
<p>${esc(t('tab.shipContact'))} <a href="#contact" style="color:var(--petrol)">${esc(t('tab.shipContactLink'))}</a>.</p>`,
    faq:`<div class="faq-list">
<details open><summary>${esc(t('tab.faqQ1'))}</summary><p>${esc(t('tab.faqA1'))}</p></details>
<details><summary>${esc(t('tab.faqQ2'))}</summary><p>${esc(t('tab.faqA2'))}</p></details>
<details><summary>${esc(t('tab.faqQ3'))}</summary><p>${esc(t('tab.faqA3'))}</p></details>
<details><summary>${esc(t('tab.faqQ4'))}</summary><p>${esc(t('tab.faqA4a'))} <a href="#contact" style="color:var(--petrol)">${esc(t('tab.faqA4link'))}</a>${esc(t('tab.faqA4b'))}</p></details>
</div>`
  };
  return `<div class="prod-tabs-container">
    <div class="prod-tabs" role="tablist" aria-label="Produktinformationen">
      ${tabs.map((tb,i)=>`<button class="prod-tab${i===0?' active':''}" role="tab" id="tab-${esc(tb.id)}" aria-controls="panel-${esc(tb.id)}" aria-selected="${i===0}" tabindex="${i===0?0:-1}" data-tab="${esc(tb.id)}">${esc(tb.label)}</button>`).join('')}
    </div>
    ${tabs.map((tb,i)=>`<div class="prod-tab-content${i===0?' active':''}" data-tab="${esc(tb.id)}" id="panel-${esc(tb.id)}" aria-labelledby="tab-${esc(tb.id)}" role="tabpanel">${contents[tb.id]||''}</div>`).join('')}
  </div>`;
}

/* ===== STATIC BLOCKS ===== */
function report(p){return `<div class="report" data-coa="${p.id}"><div class="eyebrow">${esc(t('report.eyebrow'))}</div><h3>${esc(p.name)}</h3><div class="report-grid"><div><span>${esc(t('detail.code'))}</span><strong>${p.code}</strong></div><div><span>${esc(t('detail.batch'))}</span><strong>${p.batch}</strong></div></div><p class="doc-note">${esc(t('report.note'))}</p></div>`}

/* ===== HOME (V7 Flagship) ===== */
function home(){
  return `
    <section class="focus-hero" id="home-hero" aria-labelledby="focus-title">
      <div class="focus-copy">
        <div class="eyebrow">${esc(t('focus.eyebrow'))}</div>
        <h1 id="focus-title">${esc(t('focus.title1'))}<br><span>${esc(t('focus.title2'))}</span></h1>
        <p>${esc(t('focus.lead'))}</p>
        <div class="cta-row">
          <a class="primary-btn" data-hero-primary href="#packs">${esc(t('focus.shopCTA'))}</a>
          <a class="secondary-btn" data-hero-pen href="#products/vial">${esc(t('focus.vialCTA'))}</a>
        </div>${window.ELTerms?window.ELTerms.strip():''}
      </div>
      <div class="format-stage generated-stage">
        <picture class="hero-picture"><source media="(max-width:620px)" srcset="assets/hero-focus/home-mobile.webp"><img src="assets/hero-focus/home-desktop.webp" width="1800" height="1208" fetchpriority="high" alt="${esc(t('focus.sceneAlt'))}"></picture>
        <div class="stage-links">
          <a class="stage-product stage-pen" href="#product=mehrweg-pen"><span>${esc(t('format.pen'))}<small>${pen.price}</small></span></a>
          <a class="stage-product stage-dual" href="#products/dual"><span>${esc(t('format.dual'))}<small>Retatrutide 10 mg</small></span></a>
          <a class="stage-product stage-vial" href="#products/vial"><span>${esc(t('focus.vialCTA'))}<small>Retatrutide 10 mg</small></span></a>
        </div>
      </div>
    </section>
    <div class="focus-notice"><strong>${esc(t('focus.research'))}</strong><span>${esc(t('focus.preview'))}</span></div>
    ${window.ELShop?window.ELShop.catalogTeaser():''}

    <section class="section evidence-band">
      <div class="evidence-photo"><img src="assets/scenes/packaging-duo.webp" alt="Elements Labs packaging with BPC-157 and 5-Amino-1MQ"></div>
      <div class="evidence-copy">
        <div class="eyebrow">${esc(t('home.evidenceEyebrow'))}</div>
        <h2>${esc(t('home.evidenceTitle'))}</h2>
        <p>${esc(t('home.evidenceText'))}</p>
        <div class="evidence-points"><span>${esc(t('home.evidence1'))}</span><span>${esc(t('home.evidence2'))}</span><span>${esc(t('home.evidence3'))}</span></div>
        <a class="primary-btn" href="#batch-lookup">${esc(t('home.checkBatch'))}</a>
      </div>
    </section>

    ${qualityBatchBlock()}
    ${familySection()}
    <section class="section research-invite">
      <div>
        <div class="eyebrow">${esc(t('home.libraryEyebrow'))}</div>
        <h2>${esc(t('home.libraryTitle1'))}<br>${esc(t('home.libraryTitle2'))}</h2>
      </div>
      <p>${esc(t('home.libraryText'))}</p>
      <a class="secondary-btn" href="#info">${esc(t('home.openLibrary'))}</a>
    </section>`;
}

function researchLibrarySection(){return `<section class="section"><div class="section-head"><div><div class="eyebrow">${esc(t('lib.eyebrow'))}</div><h2>${esc(t('lib.title',{n:products.filter(p=>(window.__ELEMENTS_RESEARCH__||{})[p.researchKey||p.id]).length}))}</h2></div><a class="secondary-btn" href="#quality">${esc(t('lib.toLibrary'))}</a></div><div class="cards">${products.slice(0,6).map(p=>{const rp=(window.__ELEMENTS_RESEARCH__||{})[p.researchKey||p.id];return `<article class="product-card" style="min-height:190px"><div class="card-top"><span>${p.num}</span><span>${esc(pCat(p))}</span></div><h3>${esc(p.name)}</h3><p class="compound-meta">${rp?esc(rp.research_focus||''):esc(pCat(p))+' '+esc(t('hub.profileFollows'))}</p><div class="price-row" style="margin-top:auto;padding-top:14px"><a class="secondary-btn" href="#product=${p.id}">${esc(t('rp.eyebrow'))}</a></div></article>`;}).join('')}</div></section>`}

function familySection(){const cats=[{name:t('family.metabolic'),count:products.filter(p=>p.category==='Metabolic Research').length,img:'assets/scenes/retatrutide-single.webp'},{name:t('family.peptide'),count:products.filter(p=>p.category==='Peptide & Recovery Research').length,img:'assets/scenes/group-product-shot.webp'},{name:t('family.cellular'),count:products.filter(p=>p.category==='Cellular & Longevity Research').length,img:'assets/scenes/closure-macro.webp'},{name:t('family.neuro'),count:products.filter(p=>p.category==='Neuro Research').length,img:'assets/scenes/packaging-shot.webp'}];return `<section class="section family-section"><div class="section-head"><div><div class="eyebrow">${esc(t('family.eyebrow'))}</div><h2>${esc(t('family.title'))}</h2></div><a class="secondary-btn" href="#products">${esc(t('family.viewAll'))}</a></div><div class="family-grid">${cats.map(c=>`<figure><img src="${c.img}" alt="ELEMENTS LABS ${esc(c.name)}"><figcaption>${esc(c.name)}<span>${c.count} ${esc(t('family.count'))}</span></figcaption></figure>`).join('')}<div class="fg-brand"><svg class="fg-mark" viewBox="0 0 34 34"><defs><mask id="fgmark"><rect x="0" y="0" width="34.00" height="34.00" fill="white"/><polygon points="16.32,19.01 16.09,18.89 10.99,22.60 10.88,22.98 13.32,24.90 13.80,24.87 16.29,22.86" fill="black"/></mask></defs><polygon points="16.52,2.49 6.38,9.66 6.43,25.22 15.67,32.17 18.70,29.78 9.75,23.26 9.52,19.86 16.21,14.89 16.35,10.77 9.75,14.95 9.58,11.87 16.52,6.74" fill="#F7F7F8" mask="url(#fgmark)"/><polygon points="20.26,4.28 17.08,6.77 17.11,27.39 18.73,28.87 27.20,22.79 26.86,18.48 20.34,22.86" fill="#0D5B6B"/></svg><p>${products.length} ${esc(t('family.brandLine1'))}<br>${esc(t('family.brandLine2'))}</p><a href="#products">${esc(t('family.viewAll'))} &rarr;</a></div></div></section>`}

/* ===== PAGES ===== */
function catalogEntrance(){return `<header class="catalog-entry">
  <div class="catalog-heading"><h1>${esc(t('focus.catalogTitle'))}</h1><p>${esc(t('focus.catalogLead'))}</p></div>
  <div class="catalog-formats">
    <a class="catalog-dual" href="#products/dual" aria-current="${catalogForm==='dual'?'true':'false'}"><div><h2>${esc(t('format.dual'))}</h2><p>${esc(t('focus.dualRange'))}</p><span class="text-link">${esc(t('focus.dualCTA'))} &rarr;</span></div><img class="catalog-scene" src="assets/hero-focus/catalog-flatlay.webp" width="1800" height="1005" alt="${esc(t('focus.catalogAlt'))}"></a>
    <a class="catalog-pen" href="#product=mehrweg-pen"><img src="assets/products/reusable-pen-wide.webp" width="1810" height="930" alt="${esc(t('focus.penAlt'))}"><div><h2>${esc(t('format.pen'))}</h2><strong>${pen.price}</strong><p>${esc(t('focus.penShort'))}</p><span class="text-link">${esc(t('format.penDetails'))} &rarr;</span></div></a>
  </div>
  <div class="catalog-vial"><a href="#products/vial" aria-current="${catalogForm==='vial'?'true':'false'}">${esc(t('focus.vialCTA'))} &rarr;</a><span>${esc(t('focus.rangeNote'))}</span></div>
</header>`;}
function productsPage(){const groups=productGroups(catalogForm);return `<section class="section catalog-section${catalogDedicated?' catalog-dedicated':''}">${catalogDedicated?formatHero():catalogEntrance()}<div class="filters"><select id="formatFilter"${catalogDedicated?' hidden':''} aria-label="${esc(t('format.choose'))}">${['dual','vial'].map(f=>`<option value="${f}" ${f===catalogForm?'selected':''}>${esc(t('format.'+f))}</option>`).join('')}</select><input id="searchInput" placeholder="${esc(t('products.search'))}" aria-label="${esc(t('products.searchAria'))}"><select id="categoryFilter" aria-label="${esc(t('products.categoryAria'))}"><option value="">${esc(t('products.allCategories'))}</option>${[...new Set(products.map(p=>p.category))].map(c=>`<option value="${esc(c)}">${esc(t('cat.'+c))}</option>`).join('')}</select><select id="sortFilter" aria-label="${esc(t('products.sortAria'))}"><option value="featured">${esc(t('products.sortFeatured'))}</option><option value="price-asc">${esc(t('products.sortAsc'))}</option><option value="price-desc">${esc(t('products.sortDesc'))}</option></select></div>${catalogDedicated?'<p class="result-count" id="resultCount" aria-live="polite">'+esc(resultText(groups.length))+'</p>':''}<div class="cards" id="productGrid" aria-live="polite">${renderProductGrid(groups)}</div></section>`}

function qualityBatchBlock(){return `<section class="section" id="quality-section"><div class="quality-batch-grid"><div class="quality-suite"><div class="quality-copy"><div class="eyebrow">${esc(t('quality.eyebrow'))}</div><h2>${esc(t('quality.title1'))}<br>${esc(t('quality.title2'))}</h2><p>${esc(t('quality.text'))}</p><a class="link-arrow" href="#quality">${esc(t('quality.learnMore'))}</a></div><div class="quality-photo"><img src="assets/scenes/quality-retatrutide-hand.webp" alt="Retatrutide vial in Elements Labs quality verification"></div></div><div class="batch-suite"><div class="eyebrow">${esc(t('batch.eyebrow'))}</div><h2>${esc(t('batch.homeTitle1'))}<br>${esc(t('batch.homeTitle2'))}</h2><p>${esc(t('batch.homeText'))}</p><div class="batch-input-row"><input id="batchInputHome" placeholder="${esc(t('batch.placeholder'))}" aria-label="${esc(t('batch.aria'))}"><button class="batch-submit" id="batchSubmitHome" aria-label="${esc(t('batch.submitAria'))}">→</button></div><a class="link-arrow" href="#batch-lookup">${esc(t('batch.howTo'))}</a></div></div></section>`}
function qualityBlock(full=true){return qualityBatchBlock()}

function qualityPage(){return `<section class="section" style="padding-bottom:0"><div class="section-head"><div><div class="eyebrow">${esc(t('quality.eyebrow'))}</div><h1 class="page-title">${esc(t('quality.pageTitle1'))} <span>${esc(t('quality.pageTitle2'))}</span></h1></div><p>${esc(t('quality.pageLead'))}</p></div></section>${qualityBatchBlock()}<section class="section"><div class="section-head"><div><div class="eyebrow">${esc(t('quality.libEyebrow'))}</div><h2>${esc(t('quality.libTitle',{n:products.length}))}</h2></div><p>${esc(t('quality.libText'))}</p></div><div class="cards">${products.map(p=>`<article class="product-card" style="min-height:280px"><div class="product-img-wrap" style="min-height:100px;margin-bottom:10px"><img src="${p.image}" alt="${esc(p.name)} ${esc(p.concentration)}" style="width:60%"></div><div class="card-top"><span>${p.code}</span><span>${p.batch}</span></div><h3>${esc(p.name)}</h3><p class="compound-meta">${esc(p.concentration)}</p><div class="price-row"><span class="status">${esc(t('quality.doc'))}</span><a href="#product=${p.id}" class="secondary-btn">${esc(t('quality.open'))}</a></div></article>`).join('')}</div></section>`}

function batchPage(batch=''){const p=pByBatch(batch);return `<section class="section"><div class="section-head"><div><div class="eyebrow">${esc(t('batch.eyebrow'))}</div><h1 class="page-title">${esc(t('batch.pageTitle1'))} <span>${esc(t('batch.pageTitle2'))}</span></h1></div><p>${esc(t('batch.pageLead'))}</p></div><div class="batch-panel"><input id="batchInput" value="${esc(batch||'')}" placeholder="${esc(t('batch.placeholder'))}" aria-label="${esc(t('batch.aria'))}"><div class="cta-row"><button class="primary-btn" id="batchBtn">${esc(t('batch.check'))}</button><button class="secondary-btn" id="sampleBatch">${esc(t('batch.sample'))}</button></div><div id="batchResult" style="margin-top:22px">${p?batchResult(p):batchHint(batch)}</div></div></section>`}
function batchHint(batch){const list=products.slice(0,4).map(p=>p.batch).join(' · ');return `<p class="compound-meta">${esc(batch?t('batch.notFound',{batch:batch,list:list}):t('batch.hint',{list:list}))}</p>`}
function batchResult(p){return `<div class="detail-layout" style="padding:0;border:0;background:transparent"><div><img class="qr" src="${p.qr}" alt="${esc(t('batch.qrAlt',{batch:p.batch}))}"><div class="product-img-wrap" style="max-width:260px;margin-top:16px"><img src="${p.image}" alt="${esc(t('batch.vialAlt',{name:p.name}))}"></div></div><div><div class="eyebrow">${esc(t('batch.result'))}</div><div class="not-released-banner" style="background:#FFF3CD;border:1px solid #F0C040;border-radius:6px;padding:10px 14px;margin-bottom:16px;font-size:13px"><strong>${esc(t('batch.notReleased'))}</strong> — ${esc(t('batch.notReleasedText'))}</div><h2>${esc(p.name)}</h2><p>${esc(p.concentration)} · ${p.code} · ${p.batch}</p><div class="report-grid"><div><span>${esc(t('detail.code'))}</span><strong>${p.code}</strong></div><div><span>${esc(t('detail.batch'))}</span><strong>${p.batch}</strong></div><div><span>${esc(t('batch.releaseStatus'))}</span><strong style="color:#B45309">${esc(t('batch.notReleased'))}</strong></div><div><span>${esc(t('batch.certificate'))}</span><strong>${esc(t('batch.notAvailable'))}</strong></div></div><p class="doc-note">${esc(t('batch.labNote'))}</p><div class="cta-row"><a class="primary-btn" href="#product=${p.id}">${esc(t('batch.productDetail'))}</a><a class="secondary-btn" href="#certificates">${esc(t('batch.certificates'))}</a></div></div></div>`}

function researchProfileBlock(p){const rp=(window.__ELEMENTS_RESEARCH__||{})[p.researchKey||p.id];if(!rp)return '';const refs=(rp.references||[]).map(r=>`<div class="rp-ref">${esc(r.author||'')}${r.author?', ':''}<em>${esc(r.journal||'')}</em>${r.year?' ('+r.year+')':''}.${r.identifier?' '+esc(r.identifier)+'.':''}${r.url?` <a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(t('rp.viewSource'))}</a>`:''}</div>`).join('');const topics=(rp.key_research_topics||[]).map(x=>`<span>${esc(x)}</span>`).join('');const statusRaw=String(rp.research_status||'');const statusShort=statusRaw.split(';')[0].split('.')[0];const statusLabel=esc(statusShort.length>60?statusShort.slice(0,57)+'…':statusShort);return `<div class="research-profile"><div class="rp-head"><div class="eyebrow">${esc(t('rp.eyebrow'))}</div><h2>${esc(t('rp.title'))}</h2><p>${esc(t('rp.subtitle'))}</p></div><div class="rp-status">${statusLabel}</div><div class="rp-grid"><div class="rp-block"><h4>${esc(t('rp.classification'))}</h4><p>${esc(rp.research_class||'')} · ${esc(rp.molecular_type||'')}</p></div><div class="rp-block"><h4>${esc(t('rp.focus'))}</h4><p>${esc(rp.research_focus||'')}</p></div><div class="rp-block"><h4>${esc(t('rp.mechanism'))}</h4><p>${esc(rp.mechanism_summary||'')}</p></div><div class="rp-block"><h4>${esc(t('rp.evidence'))}</h4><p>${esc(rp.evidence_summary||'')}</p></div></div><div class="rp-block" style="margin-bottom:20px"><h4>${esc(t('rp.topics'))}</h4><div class="rp-topics">${topics}</div></div><div class="rp-block" style="margin-bottom:20px"><h4>${esc(t('rp.limitations'))}</h4><p>${esc(rp.limitations||'')}</p></div><div class="rp-block"><h4>${esc(t('rp.references'))}</h4><div class="rp-refs">${refs}</div></div><p class="rp-disclaimer">${esc(t('rp.disclaimer'))}</p></div>`}

/* ===== PRODUCT DETAIL (variant-aware, i18n) ===== */
function productDetail(id){
  const p=pById(id);
  if(!p)return `<section class="section"><div class="section-head"><div><div class="eyebrow">${esc(t('products.eyebrow'))}</div><h1 class="page-title">${esc(t('detail.notFound1'))} <span>${esc(t('detail.notFound2'))}</span></h1></div><p>${esc(t('detail.notFoundText'))}</p></div><a class="primary-btn" href="#products">${esc(t('detail.toCatalog'))}</a></section>`;

  if(p.id===pen.id)return penDetail();
  const variants=variantsOf(p.group,p.form||'vial');
  const variantPicker = variants.length>1 ? `<div class="variant-picker">
      <div class="variant-label">${esc(t('detail.chooseSize'))}</div>
      <div class="variant-options" role="group" aria-label="${esc(t('detail.chooseSize'))}">
        ${variants.map(v=>`<a class="variant-opt${v.id===p.id?' active':''}" href="#product=${v.id}" aria-current="${v.id===p.id?'true':'false'}">
          <span class="vo-conc">${esc(v.concentration)}</span>
          <span class="vo-price">${esc(v.price)}</span>
          ${v.featured?`<span class="vo-badge">${esc(t('detail.bestValue'))}</span>`:''}
        </a>`).join('')}
      </div>
    </div>` : '';

  const researchReminder=`<div style="display:flex;align-items:center;gap:8px;background:#FFF8E1;border:1px solid #F0C040;border-radius:6px;padding:8px 12px;margin-top:10px;font-size:12px;color:#7A5C00;font-weight:600"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>${esc(t('detail.researchOnly'))}</div>`;
  const badge=(label,path)=>`<div style="display:flex;align-items:center;gap:7px;font-size:12px;color:var(--muted);font-weight:600"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--petrol)" stroke-width="2">${path}</svg>${esc(label)}</div>`;
  const trustBadges=`<div style="display:flex;gap:14px;flex-wrap:wrap;margin-top:16px;padding-top:14px;border-top:1px solid var(--line)">${badge(t('detail.trust1'),'<path d="M5 12l5 5L20 7"/>')}${badge(t('detail.trust2'),'<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-4 0v2"/>')}${badge(t('detail.trust3'),'<path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z"/>')}${badge(t('detail.trust4'),'<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>')}</div>`;

  return `<section class="section">
    <a href="#products" class="secondary-btn">${esc(t('detail.back'))}</a>
    <div class="detail-layout" style="margin-top:22px">
      <div class="gallery">
        <div class="gallery-main"><img src="${p.detailImage}" alt="${p.form==='dual'?esc(p.name+' '+p.concentration+' '+t('format.dual')):esc(t('detail.imgAlt',{name:p.name}))}"></div>
      </div>
      <aside class="purchase">
        <div class="eyebrow">${p.num} · ${esc(pCat(p))}</div>
        <h1>${esc(p.name)}</h1>
        <p class="lead">${esc(pDesc(p))}</p>
        <div class="price" style="margin:10px 0 18px">${p.price}</div>
        ${window.ELShop.priceExtras(p)}
        ${formatPicker(p)}
        ${variantPicker}
        <div class="spec-list">
          <div><span>${esc(t('detail.concentration'))}</span><strong>${esc(p.concentration)}</strong></div>
          <div><span>${esc(t('detail.unit'))}</span><strong>${p.form==='dual'?esc(t('format.dualUnit')):esc(t('detail.unitValue'))}</strong></div>
          ${p.form==='dual'?`<div><span>${esc(t('format.status'))}</span><strong>${esc(t('format.noRelease'))}</strong></div>`:`<div><span>${esc(t('detail.code'))}</span><strong>${p.code}</strong></div><div><span>${esc(t('detail.batch'))}</span><strong>${p.batch}</strong></div>`}
        </div>
        <div class="cta-row">
          <button class="primary-btn" data-add="${p.id}">${esc(t('detail.addToCart'))}</button>
          ${p.form==='dual'?'':`<a class="secondary-btn" href="#batch=${p.batch}">${esc(t('detail.showBatch'))}</a>`}
        </div>
        ${window.ELShop.packBlock(p)}
        ${researchReminder}
        ${p.form==='dual'?`<p class="variant-notice">${esc(t('format.noReleaseText'))}</p>${window.ELShop.penIncluded()}${trustBadges}`:trustBadges}
      </aside>
    </div>
    ${p.form==='dual'?`<div class="variant-notice"><h2>${esc(t('format.dual'))}</h2><p>${esc(t('format.previewNotice'))}</p></div>`:productTabContent(p)}
    ${p.form==='dual'?'':researchProfileBlock(p)}
    ${p.form==='dual'?'':`<div class="section-head" style="margin-top:56px;padding-top:40px;border-top:1px solid var(--line)"><div><div class="eyebrow">${esc(t('detail.docEyebrow'))}</div><h2>${esc(t('detail.docTitle'))}</h2></div><p>${esc(t('detail.docText'))}</p></div>${report(p)}`}
  </section>`;
}

function formatPicker(p){
  const base=p.sourceId||p.id;
  return `<div class="variant-picker"><div class="variant-label">${esc(t('format.choose'))}</div><div class="variant-options" role="group" aria-label="${esc(t('format.choose'))}">${['vial','dual'].map(f=>`<a data-form="${f}" class="variant-opt${f===(p.form||'vial')?' active':''}" aria-current="${f===(p.form||'vial')?'true':'false'}" href="#product=${base}${f==='dual'?'-dual':''}">${esc(t('format.'+f))}</a>`).join('')}</div></div>`;
}
function penCard(){return `<article class="product-card accessory-card"><a class="product-img-wrap" href="#product=mehrweg-pen"><img src="assets/products/reusable-pen-wide.webp" alt="${esc(pen.name)}"></a><h3>${esc(pen.name)}</h3><p class="compound-meta">${esc(t('format.penDescription'))}</p><div class="price-row"><span class="price">${pen.price}</span><a class="primary-btn" href="#product=mehrweg-pen">${esc(t('products.options'))}</a></div></article>`;}
function optionalPen(){return `<div class="optional-pen"><img src="assets/products/reusable-pen-wide.webp" alt="${esc(pen.name)}"><div><strong>${esc(t('format.optionalPen'))} · ${pen.price}</strong><p>${esc(t('format.penNotIncluded'))}</p><a href="#product=mehrweg-pen">${esc(t('format.penDetails'))}</a><button class="secondary-btn" data-add="mehrweg-pen">${esc(t('format.addPen'))}</button></div></div>`;}
function penDetail(){return `<section class="section pen-page"><header class="format-hero"><div class="eyebrow">ELEMENTS LABS · ${esc(t('fmt.catalog'))}</div></header>${window.ELShop.navigation()}<div class="detail-layout"><div class="gallery"><div class="gallery-main"><img src="assets/products/reusable-pen-wide.webp" alt="${esc(pen.name)}"></div></div><aside class="purchase"><div class="eyebrow">${esc(t('format.accessories'))}</div><h1>${esc(pen.name)}</h1><p class="lead">${esc(t('format.penDescription'))}</p><div class="price">${pen.price}</div><p class="variant-notice">${esc(t('format.penNotIncluded'))}</p><button class="primary-btn" data-add="mehrweg-pen">${esc(t('detail.addToCart'))}</button></aside></div></section>`;}

/* ===== CART ===== */
function cartPage(){const items=Object.entries(cart).map(([id,qty])=>({p:pById(id),qty})).filter(x=>x.p);const total=items.reduce((s,x)=>s+money(x.p.price)*x.qty,0);return `<section class="section"><div class="section-head"><div><div class="eyebrow">${esc(t('cart.eyebrow'))}</div><h1 class="page-title">${esc(t('cart.title1'))} <span>${esc(t('cart.title2'))}</span></h1></div><p>${esc(t('cart.lead'))}</p></div><div class="cart-panel">${items.length?items.map(x=>`<div class="cart-line"><strong>${esc(x.p.name)}<br><span class="compound-meta">${esc(x.p.concentration)} · ${esc(formLabel(x.p))}${x.p.batch?' · '+esc(x.p.batch):''}</span></strong><span>${x.p.price}</span><div class="qty"><button data-qty="${x.p.id}" data-delta="-1" aria-label="${esc(t('cart.decAria',{name:x.p.name}))}">−</button><span>${x.qty}</span><button data-qty="${x.p.id}" data-delta="1" aria-label="${esc(t('cart.incAria',{name:x.p.name}))}">+</button></div><button class="ghost-btn" data-remove="${x.p.id}" aria-label="${esc(t('cart.remAria',{name:x.p.name}))}">${esc(t('cart.remove'))}</button></div>`).join(''):`<p class="compound-meta">${esc(t('cart.empty'))}</p>`}<p class="compound-meta">${esc(t('cart.vatNote'))}</p><div class="total" id="cartTotal">${fmt(total)}</div><div class="cta-row"><button class="primary-btn" id="checkoutBtn" ${items.length?'':'disabled'}>${esc(t('cart.checkout'))}</button><a class="secondary-btn" href="#products">${esc(t('cart.continue'))}</a></div><div id="orderFeedback" role="status" aria-live="polite"></div></div></section>`}

/* ===== STATIC PAGES ===== */
function about(){return `<section class="section legal"><div class="eyebrow">${esc(t('about.eyebrow'))}</div><h1 class="page-title">${esc(t('about.title1'))} <span>${esc(t('about.title2'))}</span></h1><p class="lead">${esc(t('about.lead'))}</p><p>${esc(t('about.body'))}</p></section>`}
function faq(){return `<section class="section legal"><div class="eyebrow">${esc(t('faq.eyebrow'))}</div><h1 class="page-title">${esc(t('faq.title1'))} <span>${esc(t('faq.title2'))}</span></h1><div class="faq-list"><details open><summary>${esc(t('faq.q1'))}</summary><p>${esc(t('faq.a1'))}</p></details><details><summary>${esc(t('faq.q2'))}</summary><p>${esc(t('faq.a2'))}</p></details><details><summary>${esc(t('faq.q3'))}</summary><p>${esc(t('faq.a3'))}</p></details><details><summary>${esc(t('faq.q4'))}</summary><p>${esc(t('faq.a4'))}</p></details></div></section>`}
function contact(){return `<section class="section legal"><div class="eyebrow">${esc(t('contact.eyebrow'))}</div><h1 class="page-title">${esc(t('contact.title1'))} <span>${esc(t('contact.title2'))}</span></h1><p class="lead">${esc(t('contact.lead'))}</p><div class="batch-panel"><p><strong>ELEMENTS LABS</strong><br>${esc(t('contact.structure'))}<br>${esc(t('contact.market'))}</p><p class="compound-meta">${esc(t('contact.note'))}</p></div></section>`}
function certificates(){return `<section class="section legal"><div class="eyebrow">${esc(t('cert.eyebrow'))}</div><h1 class="page-title">${esc(t('cert.title1'))} <span>${esc(t('cert.title2'))}</span></h1><div style="background:#FFF3CD;border:1px solid #F0C040;border-radius:8px;padding:18px 22px;margin:22px 0"><strong>${esc(t('cert.noBatch'))}</strong><p style="margin:8px 0 0;font-size:14px;color:#555">${esc(t('cert.noBatchText'))}</p></div><div style="margin-top:30px"><div class="eyebrow">${esc(t('cert.gateEyebrow'))}</div><p class="compound-meta">${esc(t('cert.gateText'))}</p><p class="compound-meta" style="margin-top:12px">${esc(t('cert.statusLine',{n:products.length}))} <strong style="color:#B45309">NOT RELEASED</strong> (0 / ${products.length})</p></div></section>`}
function legal(kind){return `<section class="section legal"><div class="eyebrow">${esc(t('legal.eyebrow'))}</div><h1 class="page-title">${esc(kind==='privacy'?t('legal.privacy'):t('legal.imprint'))}</h1><p class="compound-meta"><strong>${esc(t('legal.operator'))}</strong><br>${esc(t('legal.operatorText'))}</p><p>${esc(kind==='privacy'?t('legal.privacyText'):t('legal.imprintText'))}</p><p class="compound-meta">${esc(t('legal.rou'))}</p></section>`}

/* ===== RESEARCH HUB / INFO (V7) ===== */
function researchHubPage(){
  const icons=[
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="28" height="28"><path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3"/></svg>`,
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="28" height="28"><path d="M12 2l8 4.5v9L12 20l-8-4.5v-9L12 2z"/></svg>`,
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="28" height="28"><path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z"/></svg>`,
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="28" height="28"><path d="M3 6l9-3 9 3v6c0 5.5-4 9.5-9 11C7 21.5 3 17.5 3 12V6z"/></svg>`,
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="28" height="28"><path d="M20 7H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z"/><path d="M12 12v.01"/><path d="M8 7V5"/><path d="M16 7V5"/></svg>`
  ];
  const hubs=[1,2,3,4,5].map((n,i)=>({icon:icons[i],title:t('hub.c'+n+'t'),body:t('hub.c'+n+'b')}));
  return `<section class="section">
    <div class="section-head">
      <div><div class="eyebrow">${esc(t('hub.eyebrow'))}</div><h1 class="page-title">${esc(t('hub.title1'))} <span>${esc(t('hub.title2'))}</span></h1></div>
      <p>${esc(t('hub.lead'))}</p>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:20px;margin-top:12px">
      ${hubs.map(h=>`<div style="background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:28px;transition:.2s ease">
        <div style="color:var(--petrol);margin-bottom:16px">${h.icon}</div>
        <h3 style="font-size:18px;font-weight:700;letter-spacing:-.014em;color:var(--near-black);margin:0 0 10px">${esc(h.title)}</h3>
        <p style="font-size:13.5px;color:var(--muted);line-height:1.65;margin:0">${esc(h.body)}</p>
      </div>`).join('')}
    </div>
    <div style="margin-top:48px;padding:32px;background:var(--near-black);border-radius:var(--radius-lg);color:#fff">
      <div class="eyebrow" style="color:#7FB3BE">${esc(t('hub.rouEyebrow'))}</div>
      <h2 style="font-size:clamp(20px,2.4vw,26px);line-height:1.12;letter-spacing:-.025em;margin:8px 0 12px;font-weight:700">${esc(t('hub.rouTitle'))}</h2>
      <p style="color:rgba(247,247,248,.72);font-size:14px;line-height:1.65;max-width:680px;margin:0">${esc(t('hub.rouText'))}</p>
    </div>
    <div style="margin-top:40px" class="section-head">
      <div><div class="eyebrow">${esc(t('hub.profilesEyebrow'))}</div><h2>${esc(t('hub.profilesTitle',{n:products.length}))}</h2></div>
      <a class="secondary-btn" href="#products">${esc(t('hub.toCatalog'))}</a>
    </div>
    <div class="cards">${products.slice(0,6).map(p=>{const rp=(window.__ELEMENTS_RESEARCH__||{})[p.researchKey||p.id];return `<article class="product-card" style="min-height:190px"><div class="card-top"><span>${p.num}</span><span>${esc(pCat(p))}</span></div><h3>${esc(p.name)}</h3><p class="compound-meta">${rp?esc(rp.research_focus||''):esc(pCat(p))+' '+esc(t('hub.profileFollows'))}</p><div class="price-row" style="margin-top:auto;padding-top:14px"><a class="secondary-btn" href="#product=${p.id}">${esc(t('home.openProfile'))}</a></div></article>`;}).join('')}</div>
  </section>`;
}

/* ===== ROUTER ===== */
function route(){
  let h;try{h=decodeURIComponent(window.ELMini.launchRoute(location.hash)||'home');}catch(e){return window.ELMini.notFound();}
  if(h==='catalog')return window.ELMini.hasCatalog()?window.ELMini.catalogPage():researchHubPage();
  if(h==='dual-chamber'||h==='products/dual'||h==='products/vial'){catalogForm=h==='products/vial'?'vial':'dual';catalogDedicated=true;return productsPage();}
  if(h==='products'){catalogForm='dual';catalogDedicated=false;return productsPage();}
  if(h==='accessories')return penDetail();
  if(h==='packs')return window.ELShop.packsPage();
  if(h.startsWith('product='))return productDetail(h.split('=')[1]);
  if(h.startsWith('batch='))return batchPage(h.split('=')[1]);
  if(h==='products'||h==='products/dual'||h==='products/vial'){catalogForm=h==='products/vial'?'vial':'dual';return productsPage();}
  if(h==='quality')return qualityPage();
  if(h==='batch-lookup')return batchPage();
  if(h==='about')return about();
  if(h==='faq')return faq();
  if(h==='contact')return contact();
  if(h==='cart')return window.ELShop.cartPage();
  if(h==='legal-datenschutz')return legal('privacy');
  if(h==='legal-impressum')return legal('imprint');
  if(h==='certificates')return certificates();
  if(h==='info'||h==='research-hub')return researchHubPage();
  return home();
}

/* ===== BIND (event delegation) ===== */
function bind(){
  // Cart buttons
  document.querySelectorAll('[data-add]').forEach(b=>b.onclick=()=>addToCart(b.dataset.add));
  document.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>removeFromCart(b.dataset.remove));
  document.querySelectorAll('[data-qty]').forEach(b=>b.onclick=()=>setQty(b.dataset.qty,(cart[b.dataset.qty]||0)+Number(b.dataset.delta)));
  // Checkout
  const co=document.getElementById('checkoutBtn');
  if(co)co.onclick=()=>window.ELMini.checkout();
  // Batch lookup
  const bb=document.getElementById('batchBtn');
  if(bb)bb.onclick=()=>{const v=document.getElementById('batchInput').value.trim();location.hash='batch='+encodeURIComponent(v)};
  const bi=document.getElementById('batchInput');if(bi)bi.addEventListener('keydown',e=>{if(e.key==='Enter'&&bb)bb.click()});const bbh=document.getElementById('batchSubmitHome');
  if(bbh)bbh.onclick=()=>{const v=document.getElementById('batchInputHome').value.trim();location.hash='batch='+encodeURIComponent(v)};
  const bih=document.getElementById('batchInputHome');
  if(bih)bih.addEventListener('keydown',e=>{if(e.key==='Enter'){location.hash='batch='+encodeURIComponent(bih.value.trim())}});
  const sb=document.getElementById('sampleBatch');
  if(sb)sb.onclick=()=>{document.getElementById('batchInput').value=products[0].batch};
  // Active format entrance still does work: bring the actual catalog controls
  // into view rather than leaving a same-fragment link as a silent no-op.
  document.querySelectorAll('.catalog-dual,.catalog-vial a').forEach(a=>{
    a.onclick=e=>{if(a.hash===location.hash){e.preventDefault();const filter=document.getElementById('formatFilter');filter?.focus({preventScroll:true});filter?.scrollIntoView({block:'center',behavior:'instant'});}};
  });
  // Product search/filter
  const si=document.getElementById('searchInput');
  if(si){
    const cf=document.getElementById('categoryFilter'),sf=document.getElementById('sortFilter'),ff=document.getElementById('formatFilter'),grid=document.getElementById('productGrid');
    const apply=()=>{
      catalogForm=ff.value;
      if(!catalogDedicated){history.replaceState(null,'','#products/'+catalogForm);window.ELMini.sync();}
      document.querySelectorAll('.catalog-dual,.catalog-vial a').forEach(a=>a.setAttribute('aria-current',a.hash==='#products/'+catalogForm?'true':'false'));
      let list=productGroups(catalogForm);
      const q=si.value.toLowerCase();
      if(q)list=list.filter(g=>g.variants.some(p=>window.ELShop.match(p.name+' '+p.concentration+' '+(p.code||'')+' '+(p.batch||'')+' '+p.category,q)));
      list=list.map(g=>({...g,pick:q?window.ELShop.pickVariant(g.variants,q):''}));if(cf.value)list=list.filter(g=>g.lead.category===cf.value);
      if(sf.value==='price-asc')list.sort((a,b)=>a.minPrice-b.minPrice);
      if(sf.value==='price-desc')list.sort((a,b)=>b.minPrice-a.minPrice);
      if(sf.value==='featured')list.sort((a,b)=>(b.featured?1:0)-(a.featured?1:0));
      grid.innerHTML=renderProductGrid(list);const rc=document.getElementById('resultCount');if(rc)rc.textContent=resultText(list.length);
      bind();
    };
    [si,cf,sf,ff].forEach(x=>x.oninput=apply);
  }
  // Product tabs (V7)
  document.querySelectorAll('.prod-tab').forEach(t=>{
    t.onclick=()=>{
      const c=t.closest('.prod-tabs-container');
      c.querySelectorAll('.prod-tab').forEach(x=>x.classList.remove('active'));
      c.querySelectorAll('.prod-tab-content').forEach(x=>x.classList.remove('active'));
      t.classList.add('active');
      const panel=c.querySelector(`.prod-tab-content[data-tab="${t.dataset.tab}"]`);
      if(panel)panel.classList.add('active');
    };
  });

  // Nav active state
  document.querySelectorAll('.main-nav a').forEach(a=>a.classList.toggle('active',('#'+(location.hash.slice(1).startsWith('products/')?'products':location.hash.slice(1)||'home'))===a.getAttribute('href')));
}

/* ===== LANGUAGE SWITCH ===== */
document.querySelectorAll('[data-lang-btn]').forEach(function(b){
  b.addEventListener('click',function(){
    setLang(b.getAttribute('data-lang-btn'));
    var dd = b.closest('.lang-dropdown');
    if(dd) dd.classList.remove('open');
    var toggle = document.querySelector('[data-lang-toggle]');
    if(toggle) toggle.setAttribute('aria-expanded','false');
  });
});
var langToggle = document.querySelector('[data-lang-toggle]');
if(langToggle){
  langToggle.addEventListener('click',function(e){
    e.stopPropagation();
    var dd = this.nextElementSibling;
    var open = dd.classList.toggle('open');
    this.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
}
document.addEventListener('click',function(e){
  var sw = document.querySelector('.lang-switch');
  if(sw && !sw.contains(e.target)){
    var dd = sw.querySelector('.lang-dropdown');
    var toggle = sw.querySelector('[data-lang-toggle]');
    if(dd) dd.classList.remove('open');
    if(toggle) toggle.setAttribute('aria-expanded','false');
  }
});

/* ===== RENDER LOOP ===== */
function render(){app.innerHTML=route();bind();updateCartCount();app.focus({preventScroll:true});if(window.__lastRoute!==location.hash)window.scrollTo({top:0,left:0,behavior:'instant'});window.__lastRoute=location.hash;window.ELMini.sync();}
window.render=render;
window.addEventListener('hashchange',render);
applyStaticTranslations();
render();

/* ===== MOBILE MENU ===== */
document.getElementById('menuToggle').onclick=()=>{const n=document.getElementById('mainNav');n.classList.toggle('open');document.getElementById('menuToggle').setAttribute('aria-expanded',n.classList.contains('open'))};
document.addEventListener('click',e=>{
  if(e.target.closest('#mainNav a')){document.getElementById('mainNav').classList.remove('open');document.getElementById('menuToggle').setAttribute('aria-expanded','false')}
  if(e.target.matches('[data-action="focus-search"]')){location.hash='products/vial';setTimeout(()=>document.getElementById('searchInput')?.focus(),50)}
  const nav=document.getElementById('mainNav'),tog=document.getElementById('menuToggle');
  if(nav.classList.contains('open')&&!nav.contains(e.target)&&!tog.contains(e.target)){nav.classList.remove('open');tog.setAttribute('aria-expanded','false')}
});
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'){const nav=document.getElementById('mainNav');if(nav.classList.contains('open')){nav.classList.remove('open');document.getElementById('menuToggle').setAttribute('aria-expanded','false');document.getElementById('menuToggle').focus()}}
});
