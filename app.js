
/* ===== AGE GATE INIT (P0) — runs before all other code ===== */
(function initAgeGate(){
  const key='elementsAgeGateConfirmed';
  const overlay=document.getElementById('ageGate');
  if(!overlay)return;
  if(localStorage.getItem(key)==='1'){overlay.classList.add('hidden');return;}
  document.body.classList.add('age-gate-open');
  let ageYes=false;
  const yBtn=document.getElementById('ageYes'),nBtn=document.getElementById('ageNo'),cb=document.getElementById('ageCheckbox'),confirmBtn=document.getElementById('ageConfirmBtn'),blockedMsg=document.getElementById('ageBlockedMsg');
  function upd(){confirmBtn.disabled=!(ageYes&&cb.checked);}
  yBtn.onclick=function(){ageYes=true;yBtn.classList.add('selected');nBtn.classList.remove('selected');blockedMsg.style.display='none';upd();};
  nBtn.onclick=function(){ageYes=false;nBtn.classList.add('selected');yBtn.classList.remove('selected');blockedMsg.style.display='block';confirmBtn.disabled=true;};
  cb.onchange=upd;
  confirmBtn.onclick=function(){localStorage.setItem(key,'1');overlay.classList.add('hidden');document.body.classList.remove('age-gate-open');};
})();

/* ===== UTILITIES ===== */
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
const products = JSON.parse(document.getElementById('productData').textContent);
window.__ELEMENTS_PRODUCTS__ = products;
window.__ELEMENTS_RESEARCH__ = JSON.parse((document.getElementById('researchData')||{textContent:'{}'}).textContent);
const money = v => Number(String(v).replace('€','').replace('.','').replace(',','.').trim());
const fmt = n => n.toLocaleString('de-DE',{style:'currency',currency:'EUR'});
let cart = {};
try{cart = JSON.parse(localStorage.getItem('elementsCart') || '{}');}catch(e){cart = {};}
const app = document.getElementById('app');
function saveCart(){localStorage.setItem('elementsCart', JSON.stringify(cart)); updateCartCount();}
function updateCartCount(){document.getElementById('cartCount').textContent = Object.values(cart).reduce((a,b)=>a+b,0)}
function toast(t){const el=document.getElementById('toast');el.textContent=t;el.classList.add('show-toast');setTimeout(()=>el.classList.remove('show-toast'),1500)}
function addToCart(id,qty=1){cart[id]=(cart[id]||0)+qty;saveCart();toast('Zum Warenkorb hinzugefügt');}
function removeFromCart(id){delete cart[id];saveCart();render()}
function setQty(id,qty){if(qty<=0) delete cart[id]; else cart[id]=qty;saveCart();render()}
function pById(id){return products.find(p=>p.id===id)}
function pByBatch(b){return products.find(p=>p.batch.toLowerCase()===String(b||'').toLowerCase())}

/* ===== PRODUCT CARD ===== */
function productCard(p){return `<article class="product-card ${p.featured?'featured':''}" data-product-card data-id="${p.id}"><div class="card-top"><span>${p.num}</span><span>${p.batch}</span></div><a class="product-img-wrap" href="#product=${p.id}" aria-label="${p.name} öffnen"><img src="${p.image}" alt="${p.name} ${p.concentration} Elements Labs Vial"></a><h3>${p.name}</h3><div class="compound-meta">${p.concentration}</div><div class="price-row"><span class="price">${p.price}</span><button class="primary-btn" data-add="${p.id}" aria-label="${p.name} zum Warenkorb hinzufügen" title="Add to Cart"><svg viewBox="0 0 24 24"><path d="M6 6h15l-1.5 9h-12z"/><circle cx="9" cy="20" r="1" fill="#fff" stroke="none"/><circle cx="18" cy="20" r="1" fill="#fff" stroke="none"/><path d="M6 6L4 3H2"/></svg></button></div></article>`}

/* ===== MOTS-C VARIANT CARD (V7) ===== */
function motsVariantCard(){
  const variants=[
    {id:'mots-c-10',label:'10 mg',price:'39,90 €',img:'assets/products/mots-c-10-vial.png'},
    {id:'mots-c-20',label:'20 mg',price:'59,90 €',img:'assets/products/mots-c-20-vial.png'},
    {id:'mots-c-40',label:'40 mg',price:'89,90 €',img:'assets/products/mots-c-40-vial.png'}
  ];
  const p=pById('mots-c-10');
  if(!p)return '';
  return `<article class="product-card featured" data-product-card data-id="mots-c-10">
    <div class="card-top"><span>${p.num}</span><span>Mitochondrial</span></div>
    <a class="product-img-wrap" href="#product=mots-c-10" aria-label="MOTS-C öffnen">
      <img class="mots-card-img" src="${variants[0].img}" alt="MOTS-C Elements Labs Vial">
    </a>
    <h3>MOTS-C</h3>
    <div class="compound-meta">Mitochondria-derived peptide — 3 Stärken</div>
    <div class="variant-btns">
      ${variants.map((v,i)=>`<button class="variant-btn mots-variant-btn${i===0?' active':''}" data-id="${v.id}" data-price="${v.price}" data-img="${v.img}">${v.label}</button>`).join('')}
    </div>
    <div class="price-row">
      <span class="price">${variants[0].price}</span>
      <button class="primary-btn" data-add="mots-c-10" aria-label="MOTS-C zum Warenkorb hinzufügen">
        <svg viewBox="0 0 24 24"><path d="M6 6h15l-1.5 9h-12z"/><circle cx="9" cy="20" r="1" fill="#fff" stroke="none"/><circle cx="18" cy="20" r="1" fill="#fff" stroke="none"/><path d="M6 6L4 3H2"/></svg>
      </button>
    </div>
  </article>`;
}

/* Render product grid with MOTS-C consolidation */
function renderProductGrid(list){
  let motsShown=false;
  return list.map(p=>{
    if(p.id.startsWith('mots-c-')){
      if(!motsShown){motsShown=true;return motsVariantCard();}
      return '';
    }
    return productCard(p);
  }).join('');
}

/* ===== PRODUCT DETAIL TABS (V7) ===== */
function productTabContent(p){
  const rp=(window.__ELEMENTS_RESEARCH__||{})[p.id];
  const tabs=[
    {id:'desc',label:'Beschreibung'},
    {id:'coa',label:'Labortest / COA'},
    {id:'use',label:'Anwendungsbereiche'},
    {id:'storage',label:'Lagerung'},
    {id:'disclaimer',label:'Haftungsausschluss'},
    {id:'shipping',label:'Versand & Rückgabe'},
    {id:'faq',label:'FAQ'}
  ];
  const warnBox=`<div style="display:flex;align-items:flex-start;gap:8px;background:#FEF2F2;border:1px solid #FCA5A5;border-radius:6px;padding:10px 14px;margin:14px 0;font-size:13px;color:#7F1D1D;font-weight:600"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="flex-shrink:0;margin-top:1px"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>Nur für wissenschaftliche Forschung — keine Anwendung am Menschen.</div>`;
  const ctx=rp?(rp.research_context||rp.evidence_summary||'').slice(0,500):''
  const contents={
    desc:`<p>${esc(p.desc)}</p>${rp?`<h4>Research Focus</h4><p>${esc(rp.research_focus||'')}</p><h4>Wissenschaftlicher Kontext</h4><p>${esc(ctx)}${ctx.length>=500?'…':''}</p>`:''}`,
    coa:`<p>Für jede Charge wird ein Certificate of Analysis (COA) erstellt, sobald alle Qualitätsgates bestanden wurden.</p>
<div style="background:#FFF3CD;border:1px solid #F0C040;border-radius:6px;padding:12px 16px;margin:16px 0;font-size:13px"><strong>Aktueller Status: NOT RELEASED</strong><br>Diese Charge hat noch keine externen Laborprüfungen abgeschlossen. Kein COA ist verfügbar. Berichte erscheinen automatisch nach Abschluss aller Gates.</div>
<h4>Was ein COA enthält</h4><p>Identitätstest (HPLC, MS) · Reinheitsanalyse (≥98 % Research-Grade) · Endotoxin-Test (LAL) · Mikrobiologische Reinheit · Restfeuchte · Appearance. Alle Werte werden ausschließlich nach echter, unabhängiger Laborprüfung veröffentlicht.</p>`,
    use:rp?`<p>Die nachfolgenden Bereiche beziehen sich ausschließlich auf wissenschaftliche Forschungskontexte. Keine Aussage bezieht sich auf eine Anwendung am Menschen.</p>
<h4>Forschungsbereiche</h4><p>${esc(rp.research_focus||'')}</p>
<h4>Mechanistischer Kontext</h4><p>${esc(rp.mechanism_summary||'')}</p>${warnBox}`
    :`<p>Forschungseinsatz ausschließlich in wissenschaftlichen Modellen (in vitro, in vivo, Zellkulturen). Keine Anwendungsempfehlungen für den Menschen.</p>${warnBox}`,
    storage:`<p>Peptid-Forschungsprodukte erfordern sachgemäße Lagerung zur Erhaltung von Integrität und Reinheit.</p>
<h4>Allgemeine Lagerhinweise</h4>
<ul><li>Lyophilisiert: bei −20 °C lagern, lichtgeschützt.</li><li>Kurzzeitlagerung (bis 4 Wochen): bei 4 °C möglich, trocken und lichtgeschützt.</li><li>Feuchtigkeit vermeiden: Kondenswasser beim Öffnen aus dem Kühlschrank vermeiden.</li><li>Erst unmittelbar vor Gebrauch im Forschungsprotokoll rekonstituieren.</li></ul>
<p style="font-size:12.5px;color:var(--muted)">Spezifische Stabilitätsdaten folgen im COA. Keine Dosierungs- oder Rekonstitutionsanleitungen für den Humangebrauch.</p>`,
    disclaimer:`<p>Alle auf dieser Website angebotenen Produkte sind ausschließlich für den Einsatz in der wissenschaftlichen Laborforschung bestimmt.</p>
<div style="display:flex;align-items:flex-start;gap:10px;background:#FEF2F2;border:1px solid #FCA5A5;border-radius:8px;padding:16px;margin:16px 0;font-size:13px;color:#7F1D1D">
<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="flex-shrink:0;margin-top:1px"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
<span><strong>Kein Humangebrauch.</strong> Nicht für den Verzehr durch Menschen oder Tiere, nicht für medizinische, diagnostische oder therapeutische Zwecke, nicht für klinische Anwendungen bestimmt. Der Käufer trägt die alleinige Verantwortung für die rechtskonforme Verwendung im Forschungskontext.</span>
</div>
<p>Elements Labs übernimmt keine Haftung für Schäden, die durch unsachgemäße Verwendung außerhalb des wissenschaftlichen Forschungskontexts entstehen.</p>`,
    shipping:`<p>Versand, Rückgabebedingungen und Lieferzeiten werden vor dem Go-Live vollständig dokumentiert.</p>
<div style="background:#FFF3CD;border:1px solid #F0C040;border-radius:6px;padding:12px 16px;margin:16px 0;font-size:13px">
<strong>PRE-LAUNCH STATUS</strong> — Versand- und Rückgabebedingungen sind noch nicht finalisiert. Bestellanfragen werden individuell bearbeitet. Keine erfundenen Lieferzeiten.
</div>
<p>Bei Fragen: <a href="#contact" style="color:var(--petrol)">Support kontaktieren</a>.</p>`,
    faq:`<div class="faq-list">
<details open><summary>Wie kann ich die Produktqualität prüfen?</summary><p>Jede Charge ist über die Batch-ID nachverfolgbar. Analyseberichte (COA) erscheinen nach Abschluss aller Qualitätsgates automatisch im Batch-Lookup-System. Aktueller Status aller Batches: NOT RELEASED.</p></details>
<details><summary>Wer trägt die Verantwortung für regelkonformen Einsatz?</summary><p>Der Käufer trägt die alleinige Verantwortung für die rechtskonforme Verwendung gemäß nationalen und EU-Regulierungen. Elements Labs liefert ausschließlich an verifizierte Forschungskontexte.</p></details>
<details><summary>Gibt es Dosierungsangaben oder Anwendungsempfehlungen?</summary><p>Nein — weder für Menschen noch für Tiere. Jede Entscheidung im Forschungskontext liegt beim Wissenschaftler und dem zuständigen Ethical Review Board.</p></details>
<details><summary>Wie nehme ich Kontakt auf?</summary><p>Über die <a href="#contact" style="color:var(--petrol)">Kontaktseite</a>. Elements Labs beantwortet Anfragen aus dem Forschungskontext individuell.</p></details>
</div>`
  };
  return `<div class="prod-tabs-container">
    <div class="prod-tabs" role="tablist">
      ${tabs.map((t,i)=>`<button class="prod-tab${i===0?' active':''}" role="tab" data-tab="${esc(t.id)}">${t.label}</button>`).join('')}
    </div>
    ${tabs.map((t,i)=>`<div class="prod-tab-content${i===0?' active':''}" data-tab="${esc(t.id)}" role="tabpanel">${contents[t.id]||''}</div>`).join('')}
  </div>`;
}

/* ===== STATIC BLOCKS ===== */
function report(p){return `<div class="report" data-coa="${p.id}"><div class="eyebrow">Batch Documentation</div><h3>${p.name}</h3><div class="report-grid"><div><span>Product Code</span><strong>${p.code}</strong></div><div><span>Batch</span><strong>${p.batch}</strong></div></div><p class="doc-note">Laboratory Analysis: No verified external report is currently linked to this batch. Certificates appear here automatically once issued.</p></div>`}

function home(){
  const featured=products.filter(p=>p.featured).slice(0,6);
  return `<section class="section hero" id="home-hero"><div><div class="eyebrow">European Research Brand</div><h1>ELEMENTS LABS.<br><span>Precision research</span> commerce.</h1><p class="lead">High-purity research compounds. Rigorous batch traceability. Engineered for serious research.</p><div class="cta-row"><a class="primary-btn" href="#products">Explore Products</a><a class="secondary-btn" href="#quality">Quality &amp; Documentation</a></div><div class="trust-row"><div><div class="trust-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3"/></svg></div><strong>Research Use</strong><span>For laboratory research purposes only.</span></div><div><div class="trust-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z"/></svg></div><strong>Quality Assured</strong><span>Strict sourcing and quality control.</span></div><div><div class="trust-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 2l8 4.5v9L12 20l-8-4.5v-9L12 2z"/></svg></div><strong>Batch Traceability</strong><span>Traceable batches and documentation for every lot.</span></div></div></div><figure class="hero-photo"><img src="assets/scenes/hero-studio-scene.png" alt="ELEMENTS LABS Produktfotografie mit Vials und Verpackung"></figure></section><section class="section"><div class="section-head"><div><div class="eyebrow">Featured Products</div><h2>13 Produkte, ein Standard.</h2></div><a class="secondary-btn" href="#products">Alle Produkte</a></div><div class="cards">${renderProductGrid(featured)}</div></section>${qualityBatchBlock()}${researchLibrarySection()}${familySection()}<section class="section"><div class="section-head"><div><div class="eyebrow">FAQ / Support</div><h2>Häufige Fragen.</h2></div><p>Antworten zu Bestellung, Dokumentation und Research-Einsatz.</p></div><div class="faq-list"><details open><summary>Wofür ist das Portfolio bestimmt?</summary><p>Für Research-Kontexte. Keine Einnahme, keine Anwendung, keine therapeutische oder diagnostische Kommunikation.</p></details><details><summary>Was zeigt die Batch-Suche?</summary><p>Sie verbindet Produkt, Charge, Code und Analysefelder in einer festen Struktur. Nur echte Prüfwerte werden veröffentlicht.</p></details></div></section>`;
}

function researchLibrarySection(){return `<section class="section"><div class="section-head"><div><div class="eyebrow">Research Library</div><h2>13 quellenbasierte Research Profiles.</h2></div><a class="secondary-btn" href="#quality">Zur Research Library</a></div><div class="cards">${products.slice(0,6).map(p=>{const rp=(window.__ELEMENTS_RESEARCH__||{})[p.id];return `<article class="product-card" style="min-height:190px"><div class="card-top"><span>${p.num}</span><span>${esc(p.category)}</span></div><h3>${p.name}</h3><p class="compound-meta">${rp?esc(rp.research_focus||''):esc(p.category)+' — Profil folgt.'}</p><div class="price-row" style="margin-top:auto;padding-top:14px"><a class="secondary-btn" href="#product=${p.id}">Research Profile</a></div></article>`;}).join('')}</div></section>`}

function familySection(){const cats=[{name:'Peptides',count:products.filter(p=>p.category.includes('Peptide')||p.category.includes('Tissue')).length,img:'assets/scenes/group-product-shot.png'},{name:'Regenerative',count:products.filter(p=>p.category.includes('Copper')||p.category.includes('Tripeptide')).length,img:'assets/scenes/packaging-shot.png'},{name:'Longevity',count:products.filter(p=>p.category.includes('Longevity')||p.category.includes('Cofactor')).length,img:'assets/scenes/macro-detail.png'},{name:'Metabolic',count:products.filter(p=>p.category.includes('Metabolic')||p.category.includes('Mitochondrial')||p.category.includes('Endocrine')||p.category.includes('Neuropeptide')).length,img:'assets/scenes/family-metabolic-shot.png'}];return `<section class="section family-section"><div class="section-head"><div><div class="eyebrow">Our Product Families</div><h2>Our Product Families.</h2></div><a class="secondary-btn" href="#products">View All Products</a></div><div class="family-grid">${cats.map(c=>`<figure><img src="${c.img}" alt="ELEMENTS LABS ${c.name}"><figcaption>${c.name}<span>${c.count} products</span></figcaption></figure>`).join('')}<div class="fg-brand"><svg class="fg-mark" viewBox="0 0 34 34"><defs><mask id="fgmark"><rect x="0" y="0" width="34.00" height="34.00" fill="white"/><polygon points="16.32,19.01 16.09,18.89 10.99,22.60 10.88,22.98 13.32,24.90 13.80,24.87 16.29,22.86" fill="black"/></mask></defs><polygon points="16.52,2.49 6.38,9.66 6.43,25.22 15.67,32.17 18.70,29.78 9.75,23.26 9.52,19.86 16.21,14.89 16.35,10.77 9.75,14.95 9.58,11.87 16.52,6.74" fill="#F7F7F8" mask="url(#fgmark)"/><polygon points="20.26,4.28 17.08,6.77 17.11,27.39 18.73,28.87 27.20,22.79 26.86,18.48 20.34,22.86" fill="#0D5B6B"/></svg><p>${products.length} precision compounds.<br>One standard: Excellence.</p><a href="#products">View All Products →</a></div></div></section>`}

/* ===== PAGES ===== */
function productsPage(){return `<section class="section"><div class="section-head"><div><div class="eyebrow">Catalog</div><h1 class="page-title">13 Research <span>Products.</span></h1></div><p>Alle verbindlichen Produkte mit korrekter Konzentration, Preis, Produktcode und Batch-ID.</p></div><div class="filters"><input id="searchInput" placeholder="Search compound, code or batch" aria-label="Produkt suchen"><select id="categoryFilter" aria-label="Kategorie filtern"><option value="">Alle Kategorien</option>${[...new Set(products.map(p=>p.category))].map(c=>`<option>${c}</option>`).join('')}</select><select id="sortFilter" aria-label="Sortierung wählen"><option value="featured">Featured zuerst</option><option value="price-asc">Preis aufsteigend</option><option value="price-desc">Preis absteigend</option></select></div><div class="cards" id="productGrid" aria-live="polite">${renderProductGrid(products)}</div></section>`}

function qualityBatchBlock(){return `<section class="section" id="quality-section"><div class="quality-batch-grid"><div class="quality-suite"><div class="quality-copy"><div class="eyebrow">Quality &amp; Analysis</div><h2>Uncompromising quality.<br>Complete transparency.</h2><p>Jede Charge folgt derselben Dokumentationsstruktur: Produktcode, Batch-ID, Analysefelder und QR-Zugriff sind konsistent verknüpft.</p><a class="link-arrow" href="#quality">Learn more about our quality →</a></div><div class="quality-photo"><img src="assets/scenes/quality-hand-vial.png" alt="ELEMENTS LABS Quality Verification"></div></div><div class="batch-suite"><div class="eyebrow">Batch Lookup</div><h2>Verify your batch.<br>Instantly.</h2><p>Enter your batch number to view documentation and product details.</p><div class="batch-input-row"><input id="batchInputHome" placeholder="Enter batch number" aria-label="Batch-ID eingeben"><button class="batch-submit" id="batchSubmitHome" aria-label="Batch prüfen">→</button></div><a class="link-arrow" href="#batch-lookup">How to find your batch →</a></div></div></section>`}
function qualityBlock(full=true){return qualityBatchBlock()}

function qualityPage(){return `<section class="section" style="padding-bottom:0"><div class="section-head"><div><div class="eyebrow">Quality & Analysis</div><h1 class="page-title">Quality <span>& Analysis Hub.</span></h1></div><p>Batch-Dokumentation, Zertifikats-Struktur, Produktspezifikation und Rückverfolgbarkeit an einem Ort.</p></div></section>${qualityBatchBlock()}<section class="section"><div class="section-head"><div><div class="eyebrow">Analysis Library</div><h2>13/13 Produkte dokumentiert.</h2></div><p>Jeder Eintrag folgt derselben Struktur; Laborwerte erscheinen, sobald sie extern verifiziert sind.</p></div><div class="cards">${products.map(p=>`<article class="product-card" style="min-height:220px"><div class="card-top"><span>${p.code}</span><span>${p.batch}</span></div><h3>${p.name}</h3><p class="compound-meta">${p.concentration}</p><div class="price-row"><span class="status">Dokumentation</span><a href="#product=${p.id}" class="secondary-btn">Öffnen</a></div></article>`).join('')}</div></section>`}

function batchPage(batch=''){const p=pByBatch(batch);return `<section class="section"><div class="section-head"><div><div class="eyebrow">Batch Lookup</div><h1 class="page-title">Batchnummer <span>prüfen.</span></h1></div><p>Produkt, Konzentration, Code und Analysefelder werden über die Batch-ID verbunden.</p></div><div class="batch-panel"><input id="batchInput" value="${esc(batch||'')}" placeholder="z. B. EL-BPC5-26001" aria-label="Batch-ID eingeben"><div class="cta-row"><button class="primary-btn" id="batchBtn">Batch prüfen</button><button class="secondary-btn" id="sampleBatch">Erste Batch-ID einsetzen</button></div><div id="batchResult" style="margin-top:22px">${p?batchResult(p):batchHint(batch)}</div></div></section>`}
function batchHint(batch){return batch?`<p class="compound-meta">Keine Batch-ID „${esc(batch)}" gefunden. Akzeptierte Start-Batches: ${products.slice(0,4).map(p=>p.batch).join(' · ')} · weitere im Katalog.</p>`:`<p class="compound-meta">Akzeptierte Start-Batches: ${products.slice(0,4).map(p=>p.batch).join(' · ')} · weitere im Katalog.</p>`}
function batchResult(p){return `<div class="detail-layout" style="padding:0;border:0;background:transparent"><div><img class="qr" src="${p.qr}" alt="QR zu ${p.batch}"><div class="product-img-wrap" style="max-width:260px;margin-top:16px"><img src="${p.image}" alt="${p.name} Vial"></div></div><div><div class="eyebrow">Batch Result</div><div class="not-released-banner" style="background:#FFF3CD;border:1px solid #F0C040;border-radius:6px;padding:10px 14px;margin-bottom:16px;font-size:13px"><strong>NOT RELEASED</strong> — This batch has not completed all release gates. No Certificate of Analysis is available. Certificates appear here automatically once all quality and compliance gates pass.</div><h2>${p.name}</h2><p>${p.concentration} · ${p.code} · ${p.batch}</p><div class="report-grid"><div><span>Product Code</span><strong>${p.code}</strong></div><div><span>Batch</span><strong>${p.batch}</strong></div><div><span>Release Status</span><strong style="color:#B45309">NOT RELEASED</strong></div><div><span>Certificate</span><strong>Not available</strong></div></div><p class="doc-note">Laboratory Analysis: No verified external report is linked to this batch. All batches are currently NOT RELEASED — no quality testing has been completed.</p><div class="cta-row"><a class="primary-btn" href="#product=${p.id}">Produktdetail</a><a class="secondary-btn" href="#certificates">Zertifikate</a></div></div></div>`}

function researchProfileBlock(p){const rp=(window.__ELEMENTS_RESEARCH__||{})[p.id];if(!rp)return '';const refs=(rp.references||[]).map(r=>`<div class="rp-ref">${esc(r.author||'')}${r.author?', ':''}<em>${esc(r.journal||'')}</em>${r.year?' ('+r.year+')':''}.${r.identifier?' '+esc(r.identifier)+'.':''}${r.url?` <a href="${esc(r.url)}" target="_blank" rel="noopener">Quelle ansehen</a>`:''}</div>`).join('');const topics=(rp.key_research_topics||[]).map(t=>`<span>${esc(t)}</span>`).join('');const statusMap={'preclinical':'Preclinical','early clinical':'Early Clinical','limited clinical':'Limited Clinical','investigational':'Investigational'};const statusRaw=String(rp.research_status||'');const statusShort=statusRaw.split(';')[0].split('.')[0];const statusLabel=statusMap[statusRaw.toLowerCase()]||esc(statusShort.length>60?statusShort.slice(0,57)+'…':statusShort);return `<div class="research-profile"><div class="rp-head"><div class="eyebrow">Research Profile</div><h2>Scientific Overview</h2><p>Quellenbasierte Zusammenfassung; keine Dosierungs- oder Anwendungsempfehlung.</p></div><div class="rp-status">${statusLabel}</div><div class="rp-grid"><div class="rp-block"><h4>Classification</h4><p>${esc(rp.research_class||'')} · ${esc(rp.molecular_type||'')}</p></div><div class="rp-block"><h4>Research Focus</h4><p>${esc(rp.research_focus||'')}</p></div><div class="rp-block"><h4>Mechanistic Context</h4><p>${esc(rp.mechanism_summary||'')}</p></div><div class="rp-block"><h4>Current Evidence</h4><p>${esc(rp.evidence_summary||'')}</p></div></div><div class="rp-block" style="margin-bottom:20px"><h4>Research Topics</h4><div class="rp-topics">${topics}</div></div><div class="rp-block" style="margin-bottom:20px"><h4>Limitations</h4><p>${esc(rp.limitations||'')}</p></div><div class="rp-block"><h4>References</h4><div class="rp-refs">${refs}</div></div><p class="rp-disclaimer">Wissenschaftliche Information aus öffentlich zugänglicher, überwiegend präklinischer Forschung. Keine Behandlungs-, Dosierungs- oder Anwendungsempfehlung. Research Use Only.</p></div>`}

/* ===== PRODUCT DETAIL (V7 — with tabs, trust badges, MOTS-C variants) ===== */
function productDetail(id){
  const p=pById(id);
  if(!p)return `<section class="section"><div class="section-head"><div><div class="eyebrow">Products</div><h1 class="page-title">Produkt <span>nicht gefunden.</span></h1></div><p>Dieses Produkt existiert nicht im aktuellen Katalog.</p></div><a class="primary-btn" href="#products">Zum Katalog</a></section>`;

  // MOTS-C variant selector on detail page
  const isMots=id.startsWith('mots-c-');
  const motsVariants=[
    {id:'mots-c-10',label:'10 mg',price:'39,90 €'},
    {id:'mots-c-20',label:'20 mg',price:'59,90 €'},
    {id:'mots-c-40',label:'40 mg',price:'89,90 €'}
  ];
  const variantSelector=isMots?`<div class="variant-btns" style="margin:8px 0 16px">${motsVariants.map(v=>`<button class="variant-btn${v.id===id?' active':''}" onclick="location.hash='product=${v.id}'">${v.label}</button>`).join('')}</div>`:'';

  // Research-only reminder + trust badges (inline styles to avoid CSS bloat)
  const researchReminder=`<div style="display:flex;align-items:center;gap:8px;background:#FFF8E1;border:1px solid #F0C040;border-radius:6px;padding:8px 12px;margin-top:10px;font-size:12px;color:#7A5C00;font-weight:600"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>Nur für Forschungszwecke — keine Anwendung am Menschen.</div>`;
  const trustBadges=`<div style="display:flex;gap:14px;flex-wrap:wrap;margin-top:16px;padding-top:14px;border-top:1px solid var(--line)"><div style="display:flex;align-items:center;gap:7px;font-size:12px;color:var(--muted);font-weight:600"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--petrol)" stroke-width="2"><path d="M5 12l5 5L20 7"/></svg>Versand aus Europa</div><div style="display:flex;align-items:center;gap:7px;font-size:12px;color:var(--muted);font-weight:600"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--petrol)" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-4 0v2"/></svg>Batch-verifiziert</div><div style="display:flex;align-items:center;gap:7px;font-size:12px;color:var(--muted);font-weight:600"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--petrol)" stroke-width="2"><path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z"/></svg>Qualitätskontrolle</div><div style="display:flex;align-items:center;gap:7px;font-size:12px;color:var(--muted);font-weight:600"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--petrol)" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>24/7 Kundendienst</div></div>`;

  return `<section class="section">
    <a href="#products" class="secondary-btn">← Zurück zum Katalog</a>
    <div class="detail-layout" style="margin-top:22px">
      <div class="gallery">
        <div class="gallery-main"><img src="${p.detailImage}" alt="${p.name} Elements Labs Produktbild"></div>
        <div class="thumbs">
          <img src="${p.image}" alt="${p.name} Vial">
          <img src="${p.packagingImage}" alt="Elements Labs Packaging">
          <img src="${p.macroImage}" alt="Elements Labs Macro Detail">
        </div>
      </div>
      <aside class="purchase">
        <div class="eyebrow">${p.num} · ${p.category}</div>
        <h1>${p.name}</h1>
        <p class="lead">${p.desc}</p>
        ${variantSelector}
        <div class="price" style="margin:10px 0 18px">${p.price}</div>
        <div class="spec-list">
          <div><span>Konzentration</span><strong>${p.concentration}</strong></div>
          <div><span>Einheit</span><strong>1 Vial</strong></div>
          <div><span>Product Code</span><strong>${p.code}</strong></div>
          <div><span>Batch</span><strong>${p.batch}</strong></div>
        </div>
        <div class="cta-row">
          <button class="primary-btn" data-add="${p.id}">Add to Cart</button>
          <a class="secondary-btn" href="#batch=${p.batch}">Batch anzeigen</a>
        </div>
        ${researchReminder}
        ${trustBadges}
      </aside>
    </div>
    ${productTabContent(p)}
    ${researchProfileBlock(p)}
    <div class="section-head" style="margin-top:56px;padding-top:40px;border-top:1px solid var(--line)">
      <div><div class="eyebrow">Product Documentation</div><h2>Batch &amp; Specifications</h2></div>
      <p>Produktdaten bleiben exakt; Analysewerte erscheinen ausschließlich nach echter Prüfung.</p>
    </div>
    ${report(p)}
  </section>`;
}

/* ===== CART ===== */
function cartPage(){const items=Object.entries(cart).map(([id,qty])=>({p:pById(id),qty})).filter(x=>x.p);const total=items.reduce((s,x)=>s+money(x.p.price)*x.qty,0);return `<section class="section"><div class="section-head"><div><div class="eyebrow">Cart</div><h1 class="page-title">Warenkorb <span>prüfen.</span></h1></div><p>Produktauswahl, Mengen und Summen im Überblick. Bestellanfragen werden individuell von Elements Labs bearbeitet.</p></div><div class="cart-panel">${items.length?items.map(x=>`<div class="cart-line"><strong>${x.p.name}<br><span class="compound-meta">${x.p.concentration} · ${x.p.batch}</span></strong><span>${x.p.price}</span><div class="qty"><button data-qty="${x.p.id}" data-delta="-1" aria-label="${x.p.name} Menge verringern">−</button><span>${x.qty}</span><button data-qty="${x.p.id}" data-delta="1" aria-label="${x.p.name} Menge erhöhen">+</button></div><button class="ghost-btn" data-remove="${x.p.id}" aria-label="${x.p.name} entfernen">Remove</button></div>`).join(''):'<p class="compound-meta">Der Warenkorb ist leer.</p>'}<p class="compound-meta">Anzeige inklusive Umsatzsteuer, zzgl. Versand nach Absprache.</p><div class="total" id="cartTotal">${fmt(total)}</div><div class="cta-row"><button class="primary-btn" id="checkoutBtn" ${items.length?'':'disabled'}>Bestellanfrage senden</button><a class="secondary-btn" href="#products">Weiter einkaufen</a></div><div id="checkoutDemo" class="hidden" style="margin-top:20px"><span class="internal-badge">Anfrage erfasst</span><p>Elements Labs bearbeitet Bestellanfragen individuell — Sie erhalten eine Rückmeldung mit Verfügbarkeit und Versandoptionen.</p></div></div></section>`}

/* ===== STATIC PAGES ===== */
function about(){return `<section class="section legal"><div class="eyebrow">About</div><h1 class="page-title">European Research Commerce, <span>präzise geführt.</span></h1><p class="lead">ELEMENTS LABS positioniert Research-Produkte über Materialklarheit, dokumentierte Batch-Struktur und zurückhaltendes Premium-Design.</p><p>Die Marke vermeidet Fitness-, Supplement- und Pharma-Anmutung. Der Fokus liegt auf reproduzierbaren Produktvisuals, systematischer Informationsarchitektur und einem ehrlichen Analyse-Framework.</p></section>`}
function faq(){return `<section class="section legal"><div class="eyebrow">FAQ</div><h1 class="page-title">Research-only <span>clarity.</span></h1><div class="faq-list"><details open><summary>Sind Bestellungen bereits aktiv?</summary><p>Bestellanfragen können bereits über den Warenkorb gestellt werden. Elements Labs bestätigt Verfügbarkeit und Versandoptionen individuell.</p></details><details><summary>Sind Laborberichte veröffentlicht?</summary><p>Nein. Die Seite zeigt die Dokumentationsstruktur. Nur echte, extern geprüfte Analysewerte werden veröffentlicht.</p></details><details><summary>Gibt es medizinische Aussagen?</summary><p>Nein. Keine Einnahme-, Dosierungs-, Therapie-, Diagnose- oder Human-Use-Anleitung.</p></details><details><summary>Warum Batch Lookup?</summary><p>Das System verbindet Produkt, Charge und Berichtszugriff eindeutig und nachvollziehbar.</p></details></div></section>`}
function contact(){return `<section class="section legal"><div class="eyebrow">Support</div><h1 class="page-title">Kontakt <span>Elements Labs.</span></h1><p class="lead">Für Bestellanfragen, Fachfragen und Kooperationen erreichen Sie Elements Labs direkt.</p><div class="batch-panel"><p><strong>ELEMENTS LABS</strong><br>Research-only commerce structure<br>Germany / EU market focus</p><p class="compound-meta">Keine medizinische Beratung. Keine Human-Use-Kommunikation.</p></div></section>`}
function certificates(){return `<section class="section legal"><div class="eyebrow">Quality Certificates</div><h1 class="page-title">Certificates of <span>Analysis.</span></h1><div style="background:#FFF3CD;border:1px solid #F0C040;border-radius:8px;padding:18px 22px;margin:22px 0"><strong>No batch currently released</strong><p style="margin:8px 0 0;font-size:14px;color:#555">Certificates appear here automatically once a batch completes all 11 release gates (Legal → Lab Pass → COA Upload → Price Approval → Website Release). No dummy certificates, no placeholder stamps. Current status: all batches NOT RELEASED.</p></div><div style="margin-top:30px"><div class="eyebrow">Release Gate Progress</div><p class="compound-meta">Each batch must pass 11 sequential gates before a COA is published. Gates include: Legal Check · Supplier Verified · Import Clearance · SDS/CLP OK · Sample Received · Lab Tested · Lab Pass · COA Uploaded · Product Data Verified · Price Approved · Website Released.</p><p class="compound-meta" style="margin-top:12px">Current status across all ${products.length} batches: <strong style="color:#B45309">NOT RELEASED</strong> (0 / ${products.length})</p></div></section>`}
function legal(kind){return `<section class="section legal"><div class="eyebrow">Legal</div><h1 class="page-title">${kind==='privacy'?'Datenschutz':'Impressum'}</h1><div style="background:#FFF3CD;border:1px solid #F0C040;border-radius:8px;padding:14px 18px;margin-bottom:24px;font-size:13px"><strong>PRE-LAUNCH STATUS</strong> — This legal notice is incomplete. The operating entity and full § 5 DDG / § 5 TMG required data will be published before the site goes live. No commercial transactions are active during pre-launch.</div><p class="compound-meta"><strong>Betreiberkennzeichnung nach § 5 DDG / § 5 TMG</strong><br>Vollständige Angaben folgen vor Go-Live. Betreiber: Elements Labs (in Gründung). Sitz: Deutschland / EU.</p><p>${kind==='privacy'?'Diese Website nutzt kein Tracking, keine Analyse-Cookies und keine Drittanbieter-Skripte (stand Pre-Launch). Datenschutzerklärung wird vor Go-Live vollständig veröffentlicht.':'Alle gesetzlich erforderlichen Pflichtangaben nach § 5 DDG werden vor dem Launch ergänzt. Interim-Status: PRE_LAUNCH.'}</p><p class="compound-meta">Research-use-only. No human consumption. No medical, therapeutic, diagnostic or veterinary claims.</p></section>`}

/* ===== RESEARCH HUB / INFO (V7) ===== */
function researchHubPage(){
  const hubs=[
    {
      icon:`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="28" height="28"><path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3"/></svg>`,
      title:'Was sind Peptide?',
      body:'Peptide sind kurze Ketten aus Aminosäuren — die Bausteine der Proteine. Sie kommen natürlich im menschlichen Körper vor und regulieren biologische Prozesse. In der Forschung werden synthetisch hergestellte Peptide als Werkzeuge eingesetzt, um Signalwege zu verstehen und zelluläre Mechanismen zu untersuchen.'
    },
    {
      icon:`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="28" height="28"><path d="M12 2l8 4.5v9L12 20l-8-4.5v-9L12 2z"/></svg>`,
      title:'Verwendungszweck & Abgrenzung',
      body:'Elements Labs-Produkte sind ausschließlich für wissenschaftliche Laborforschung bestimmt — in vitro (Zellkulturen), in vivo (Tiermodelle) und mechanistische Studien. Sie sind nicht für den Einsatz am menschlichen Körper vorgesehen, nicht als Arzneimittel klassifiziert und nicht für diagnostische oder therapeutische Zwecke geeignet.'
    },
    {
      icon:`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="28" height="28"><path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z"/></svg>`,
      title:'Qualität & Analytik: COA / HPLC / SDS',
      body:'Ein Certificate of Analysis (COA) dokumentiert Identitäts- und Reinheitstests (HPLC: Hochleistungsflüssigchromatographie; MS: Massenspektrometrie), Endotoxin-Tests und weitere Spezifikationen pro Charge. HPLC trennt Substanzen nach chemischen Eigenschaften und misst Reinheit präzise. SDS (Safety Data Sheet) enthält Sicherheitshinweise für den Laborumgang. Alle Analysen werden ausschließlich nach echter, unabhängiger Prüfung veröffentlicht.'
    },
    {
      icon:`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="28" height="28"><path d="M3 6l9-3 9 3v6c0 5.5-4 9.5-9 11C7 21.5 3 17.5 3 12V6z"/></svg>`,
      title:'Gesetzeslage & Verantwortung',
      body:'Die rechtliche Einordnung von Forschungspeptiden variiert nach Land und Substanz. Elements Labs befindet sich im PRE_LAUNCH-Status — keine kommerziellen Transaktionen sind aktiv. Der Käufer ist allein verantwortlich für die Prüfung nationaler Regulierungen, Einfuhrbestimmungen und ethischer Anforderungen. Keine Rechtsberatung durch Elements Labs.'
    },
    {
      icon:`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="28" height="28"><path d="M20 7H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z"/><path d="M12 12v.01"/><path d="M8 7V5"/><path d="M16 7V5"/></svg>`,
      title:'Sicherer Umgang & Lagerung',
      body:'Lyophilisierte Peptide bei −20 °C lagern, lichtgeschützt und trocken. Vor dem Öffnen auf Raumtemperatur equilibrieren, um Kondenswasser zu vermeiden. Kurzzeitlagerung bei 4 °C (max. 4 Wochen). Schutzausrüstung (Handschuhe, Schutzbrille) bei Laborarbeiten tragen. Spezifische Lager- und Handhabungsanforderungen finden sich im jeweiligen COA und SDS.'
    }
  ];
  return `<section class="section">
    <div class="section-head">
      <div><div class="eyebrow">Research Library</div><h1 class="page-title">Wissenschaftliche <span>Grundlagen.</span></h1></div>
      <p>Hintergrundinformationen zu Peptiden, Qualitätsdokumentation und Forschungskontext — ohne Anwendungsempfehlungen.</p>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:20px;margin-top:12px">
      ${hubs.map(h=>`<div style="background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:28px;transition:.2s ease" onmouseover="this.style.borderColor='var(--graphite)'" onmouseout="this.style.borderColor='var(--line)'">
        <div style="color:var(--petrol);margin-bottom:16px">${h.icon}</div>
        <h3 style="font-size:18px;font-weight:700;letter-spacing:-.014em;color:var(--near-black);margin:0 0 10px">${h.title}</h3>
        <p style="font-size:13.5px;color:var(--muted);line-height:1.65;margin:0">${h.body}</p>
      </div>`).join('')}
    </div>
    <div style="margin-top:48px;padding:32px;background:var(--near-black);border-radius:var(--radius-lg);color:#fff">
      <div class="eyebrow" style="color:#7FB3BE">Research Use Only</div>
      <h2 style="font-size:clamp(20px,2.4vw,26px);line-height:1.12;letter-spacing:-.025em;margin:8px 0 12px;font-weight:700">Wissenschaftliche Information — kein Ersatz für Fachberatung.</h2>
      <p style="color:rgba(247,247,248,.72);font-size:14px;line-height:1.65;max-width:680px;margin:0">Alle Inhalte basieren auf öffentlich zugänglicher wissenschaftlicher Literatur und dienen ausschließlich der Hintergrundinformation. Keine medizinische, therapeutische, diagnostische oder veterinäre Beratung. Die Verantwortung für rechtskonforme Verwendung liegt beim Forscher.</p>
    </div>
    <div style="margin-top:40px" class="section-head">
      <div><div class="eyebrow">Research Profiles</div><h2>13 Compound Profiles.</h2></div>
      <a class="secondary-btn" href="#products">Zum Katalog</a>
    </div>
    <div class="cards">${products.slice(0,6).map(p=>{const rp=(window.__ELEMENTS_RESEARCH__||{})[p.id];return `<article class="product-card" style="min-height:190px"><div class="card-top"><span>${p.num}</span><span>${esc(p.category)}</span></div><h3>${p.name}</h3><p class="compound-meta">${rp?esc(rp.research_focus||''):esc(p.category)+' — Profil folgt.'}</p><div class="price-row" style="margin-top:auto;padding-top:14px"><a class="secondary-btn" href="#product=${p.id}">Profil öffnen</a></div></article>`;}).join('')}</div>
  </section>`;
}

/* ===== ROUTER ===== */
function route(){
  const h=decodeURIComponent(location.hash.slice(1)||'home');
  if(h.startsWith('product='))return productDetail(h.split('=')[1]);
  if(h.startsWith('batch='))return batchPage(h.split('=')[1]);
  if(h==='products')return productsPage();
  if(h==='quality')return qualityPage();
  if(h==='batch-lookup')return batchPage();
  if(h==='about')return about();
  if(h==='faq')return faq();
  if(h==='contact')return contact();
  if(h==='cart')return cartPage();
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
  if(co)co.onclick=()=>document.getElementById('checkoutDemo').classList.remove('hidden');
  // Batch lookup
  const bb=document.getElementById('batchBtn');
  if(bb)bb.onclick=()=>{const v=document.getElementById('batchInput').value.trim();location.hash='batch='+encodeURIComponent(v)};
  const bbh=document.getElementById('batchSubmitHome');
  if(bbh)bbh.onclick=()=>{const v=document.getElementById('batchInputHome').value.trim();location.hash='batch='+encodeURIComponent(v)};
  const bih=document.getElementById('batchInputHome');
  if(bih)bih.addEventListener('keydown',e=>{if(e.key==='Enter'){location.hash='batch='+encodeURIComponent(bih.value.trim())}});
  const sb=document.getElementById('sampleBatch');
  if(sb)sb.onclick=()=>{document.getElementById('batchInput').value=products[0].batch};
  // Product search/filter
  const si=document.getElementById('searchInput');
  if(si){
    const cf=document.getElementById('categoryFilter'),sf=document.getElementById('sortFilter'),grid=document.getElementById('productGrid');
    const apply=()=>{
      let list=[...products];
      const q=si.value.toLowerCase();
      if(q)list=list.filter(p=>(p.name+p.code+p.batch+p.category).toLowerCase().includes(q));
      if(cf.value)list=list.filter(p=>p.category===cf.value);
      if(sf.value==='price-asc')list.sort((a,b)=>money(a.price)-money(b.price));
      if(sf.value==='price-desc')list.sort((a,b)=>money(b.price)-money(a.price));
      if(sf.value==='featured')list.sort((a,b)=>(b.featured?1:0)-(a.featured?1:0));
      grid.innerHTML=renderProductGrid(list);
      bind();
    };
    [si,cf,sf].forEach(x=>x.oninput=apply);
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
  // MOTS-C variant card switcher (V7)
  document.querySelectorAll('.mots-variant-btn').forEach(btn=>{
    btn.onclick=e=>{
      e.preventDefault();
      e.stopPropagation();
      const card=btn.closest('.product-card');
      card.querySelectorAll('.mots-variant-btn').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      const pr=card.querySelector('.price');
      if(pr)pr.textContent=btn.dataset.price;
      const addBtn=card.querySelector('[data-add]');
      if(addBtn){addBtn.dataset.add=btn.dataset.id;addBtn.onclick=()=>addToCart(btn.dataset.id);}
      const img=card.querySelector('.mots-card-img');
      if(img)img.src=btn.dataset.img;
      const lnk=card.querySelector('a.product-img-wrap');
      if(lnk)lnk.href='#product='+btn.dataset.id;
    };
  });
  // Nav active state
  document.querySelectorAll('.main-nav a').forEach(a=>a.classList.toggle('active',('#'+(location.hash.slice(1)||'home'))===a.getAttribute('href')));
}

/* ===== RENDER LOOP ===== */
function render(){app.innerHTML=route();bind();updateCartCount();app.focus({preventScroll:true});window.scrollTo({top:0,left:0,behavior:'instant'});}
window.addEventListener('hashchange',render);
render();

/* ===== MOBILE MENU ===== */
document.getElementById('menuToggle').onclick=()=>{const n=document.getElementById('mainNav');n.classList.toggle('open');document.getElementById('menuToggle').setAttribute('aria-expanded',n.classList.contains('open'))};
document.addEventListener('click',e=>{
  if(e.target.closest('#mainNav a')){document.getElementById('mainNav').classList.remove('open');document.getElementById('menuToggle').setAttribute('aria-expanded','false')}
  if(e.target.matches('[data-action="focus-search"]')){location.hash='products';setTimeout(()=>document.getElementById('searchInput')?.focus(),50)}
  const nav=document.getElementById('mainNav'),tog=document.getElementById('menuToggle');
  if(nav.classList.contains('open')&&!nav.contains(e.target)&&!tog.contains(e.target)){nav.classList.remove('open');tog.setAttribute('aria-expanded','false')}
});
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'){const nav=document.getElementById('mainNav');if(nav.classList.contains('open')){nav.classList.remove('open');document.getElementById('menuToggle').setAttribute('aria-expanded','false');document.getElementById('menuToggle').focus()}}
});
