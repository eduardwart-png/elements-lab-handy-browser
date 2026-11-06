/* Separate sales offers: the 25 approved Vial records remain untouched.
   New packaging never inherits a batch, QR, analysis or release claim. */
window.buildVariantCatalog = function(originals){
  const dual=originals.map(p=>({
    id:'dual-'+p.id,sourceId:p.id,form:'dual',num:p.num,name:p.name,
    concentration:p.concentration,price:window.ELShop.formatPrice('dual-'+p.id,p.price),category:p.category,
    featured:p.featured,group:p.group,descKey:p.descKey,
    image:'assets/products/dual-chamber/'+p.id+'.webp',
    detailImage:'assets/products/dual-chamber/'+p.id+'.webp'
  }));
  const pen={id:'mehrweg-pen',form:'accessory',num:'26',group:'reusable-pen',
    get name(){return t('format.pen');},concentration:'',price:'20,00 €',
    category:'Accessories',descKey:'format.penDescription',
    image:'assets/products/reusable-pen.webp',detailImage:'assets/products/reusable-pen.webp'};
  return {dual,pen};
};
