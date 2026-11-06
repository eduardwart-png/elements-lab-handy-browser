"""Import current reference products and artwork; never generate substitute devices.
The reference snapshot is pinned in evidence/reference-current. Old Telegram IDs
remain stable; original website IDs are accepted as aliases by the frontend.
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'evidence/reference-current'


def pen_wide():
    from PIL import Image
    source = ROOT / 'asset-cache-current/assets/products/reusable-pen.png'
    target = ROOT / 'asset-cache-current/assets/products/reusable-pen-wide.png'
    if not source.is_file():
        return
    with Image.open(source) as im:
        # Same reference render, rotated and cropped so the slim pen is legible in cards and cart thumbnails.
        im.convert('RGB').crop((560, 150, 1490, 1960)).rotate(-90, expand=True).save(target)


def main():
    pen_wide()
    html = (SOURCE / 'index.html').read_text()
    match = re.search(r'id="productData"[^>]*>(.*?)</script>', html, re.S)
    if match is None:
        raise ValueError('Current reference productData is missing')
    originals = json.loads(match[1])
    script = "const fs=require('fs'),vm=require('vm');const c={window:{},t:k=>k};vm.createContext(c);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),c);console.log(JSON.stringify(c.window.buildVariantCatalog(JSON.parse(fs.readFileSync(process.argv[2],'utf8')))));"
    input_path = ROOT / 'runtime/reference-vials-input.json'
    input_path.parent.mkdir(exist_ok=True)
    input_path.write_text(json.dumps(originals))
    response = subprocess.run(['node', '-e', script, str(SOURCE / 'variants.js'), str(input_path)], capture_output=True, text=True, check=True)
    source_formats = json.loads(response.stdout)

    def cents(value):
        return int(value.replace(' €', '').replace('.', '').replace(',', ''))

    vials = [dict(p, price_cents=cents(p['price']), stock_status='UNCONFIRMED', format='vial') for p in originals]
    (ROOT / 'data/products.json').write_text(json.dumps(vials, ensure_ascii=False, indent=2) + '\n')
    items = []
    for p in source_formats['dual']:
        source_id = p['sourceId']
        items.append(dict(p, id='dual-' + source_id, source_reference_id=p['id'], base_product_id=source_id,
                          format='dual_chamber', price_cents=cents(p['price']), price_status='REFERENCE_PRICE',
                          image_type='REFERENCE_ARTWORK', stock_status='UNCONFIRMED'))
    p = source_formats['pen']
    items.append(dict(p, id='mehrweg-pen', thumb='assets/products/reusable-pen-wide.png', source_reference_id=p['id'], name='Mehrweg-Pen', concentration='Zubehör',
                      format='pen', price_cents=cents(p['price']), price_status='REFERENCE_PRICE',
                      image_type='REFERENCE_ARTWORK', stock_status='UNCONFIRMED'))
    (ROOT / 'data/shop-formats.json').write_text(json.dumps(items, ensure_ascii=False, indent=2) + '\n')
    evidence = {'source': 'https://elements-labs-flagship.vercel.app/', 'snapshot': str(SOURCE),
                'products': [{'id': p['id'], 'source_id': p.get('source_reference_id', p['id']), 'image': p['image'],
                              'price_cents': p['price_cents'], 'field_evidence': 'index.html#productData' if p['format'] == 'vial' else 'variants.js::buildVariantCatalog'} for p in vials + items],
                'note': 'Source prices, not independent availability or release confirmation. No batch/QR inherited by new formats.'}
    (ROOT / 'evidence/current-product-provenance.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2))
    print(json.dumps({'vials': len(vials), 'dual_chamber': len(items)-1, 'pens': 1, 'source': str(SOURCE)}))


if __name__ == '__main__':
    main()
