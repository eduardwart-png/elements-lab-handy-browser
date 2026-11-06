"""Dedicated, self-explanatory catalogue pages for Vials and Doppelkammer (patched into the template's app.js)."""


def apply(js, replace_once):
    js = replace_once(js, "let catalogForm='dual';", "let catalogForm='dual',catalogDedicated=false;")
    js = replace_once(
        js,
        "if(h==='dual-chamber'){catalogForm='dual';return productsPage();}",
        "if(h==='dual-chamber'||h==='products/dual'||h==='products/vial'){catalogForm=h==='products/vial'?'vial':'dual';catalogDedicated=true;return productsPage();}\n"
        "  if(h==='products'){catalogForm='dual';catalogDedicated=false;return productsPage();}",
    )
    js = replace_once(
        js,
        "history.replaceState(null,'','#products/'+catalogForm);window.ELMini.sync();",
        "if(!catalogDedicated){history.replaceState(null,'','#products/'+catalogForm);window.ELMini.sync();}",
    )
    js = replace_once(
        js,
        "grid.innerHTML=renderProductGrid(list);",
        "grid.innerHTML=renderProductGrid(list);const rc=document.getElementById('resultCount');if(rc)rc.textContent=resultText(list.length);",
    )
    js = replace_once(
        js,
        "function renderProductGrid(list){",
        r"""function resultText(n){return n+' '+t(n===1?'fmt.substance1':'fmt.substances')}
function formatHero(){const dual=catalogForm==='dual';return `<header class="format-hero"><div class="eyebrow">ELEMENTS LABS · ${esc(t('fmt.catalog'))}</div><h1 class="page-title">${esc(t(dual?'fmt.dualTitle':'fmt.vialTitle'))}</h1><p class="lead">${esc(t(dual?'fmt.dualLead':'fmt.vialLead'))}</p>${window.ELShop.navigation()}</header>`}
function renderProductGrid(list){""",
    )
    js = replace_once(
        js,
        '<section class="section catalog-section">${catalogEntrance()}<div class="filters"><select id="formatFilter"',
        '<section class="section catalog-section${catalogDedicated?\' catalog-dedicated\':\'\'}">${catalogDedicated?formatHero():catalogEntrance()}<div class="filters"><select id="formatFilter"${catalogDedicated?\' hidden\':\'\'}',
    )
    js = replace_once(
        js,
        '</div><div class="cards" id="productGrid" aria-live="polite">',
        '</div>${catalogDedicated?\'<p class="result-count" id="resultCount" aria-live="polite">\'+esc(resultText(groups.length))+\'</p>\':\'\'}<div class="cards" id="productGrid" aria-live="polite">',
    )
    js = replace_once(
        js,
        '<section class="section"><a class="secondary-btn" href="#products">${esc(t(\'detail.back\'))}</a><div class="detail-layout"><div class="gallery"><div class="gallery-main"><img src="assets/products/reusable-pen-wide.png"',
        '<section class="section pen-page"><header class="format-hero"><div class="eyebrow">ELEMENTS LABS · ${esc(t(\'fmt.catalog\'))}</div></header>${window.ELShop.navigation()}<div class="detail-layout"><div class="gallery"><div class="gallery-main"><img src="assets/products/reusable-pen-wide.png"',
    )
    js = replace_once(
        js,
        '<img src="${lead.image}" alt="${esc(lead.name)}',
        '<img src="${lead.image.replace(/\\.webp(\\?|$)/,\'-card.webp$1\')}" width="560" height="392" alt="${esc(lead.name)}',
    )
    return js
