
from pathlib import Path
import json, re, sys
root = Path(sys.argv[1])
html = (root / '_standalone.html').read_text(encoding='utf-8')
fail=[]
if re.search(r'<script\s+[^>]*src=', html, re.I): fail.append('script src remains')
if re.search(r'<link\s+[^>]*stylesheet', html, re.I): fail.append('stylesheet link remains')
if re.search(r'(C:\\Users|C:/Users)', html): fail.append('absolute Windows path remains')
outside = re.sub(r'<script\b.*?</script>', '', html, flags=re.I|re.S)
bad = re.findall(r'\b(?:src|href)=["\'](?!#|mailto:|tel:|https?:|data:)[^"\']+', outside, re.I)
if bad: fail.append('relative html dependency remains '+json.dumps(bad[:10]))
products = json.loads(re.search(r'<script id="productData" type="application/json">(.*?)</script>', html, re.S).group(1))
if len(products)!=13: fail.append('product data count !=13')
for key in ['name','concentration','price','batch','code','image','detailImage','qr']:
    if any(not p.get(key) for p in products): fail.append('missing '+key)
for p in products:
    for key in ['image','detailImage','macroImage','packagingImage','qr']:
        if not str(p.get(key,'')).startswith('data:image/'): fail.append(f'{p["id"]} {key} not inlined')
public_text = re.sub(r'<script\b.*?</script>', '', html, flags=re.I|re.S)
public_text = re.sub(r'<style\b.*?</style>', '', public_text, flags=re.I|re.S)
if re.search(r'\b(DEMO|SAMPLE|TEST|MOCKUP|PROTOTYPE)\b', public_text, re.I): fail.append('banned public marker remains in HTML shell')
if re.search(r'\bPLACEHOLDER\b(?!\s*[:{])', public_text, re.I): fail.append('banned public marker (placeholder) remains in HTML shell')
if fail:
    print('FAIL standalone static: '+ '; '.join(dict.fromkeys(fail))); sys.exit(1)
print('PASS standalone static: self-contained HTML, products=13, images/QR inlined, banned shell markers=0')
