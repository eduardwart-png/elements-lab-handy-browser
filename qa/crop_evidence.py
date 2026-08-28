"""Post-process evidence/screenshots/*-rect.json produced by clipSnap() in the
CDP QA script: crop the matching -full.png to the recorded rect and save as
<name>.png (the final artifact clipSnap used to write directly)."""
import json
import sys
from pathlib import Path
from PIL import Image

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
shots = root / 'evidence' / 'screenshots'
count = 0
for rect_file in shots.glob('*-rect.json'):
    name = rect_file.stem[:-len('-rect')]
    full_file = shots / f'{name}-full.png'
    if not full_file.exists():
        print('MISSING full for', name)
        continue
    rect = json.loads(rect_file.read_text(encoding='utf-8'))
    im = Image.open(full_file)
    x, y, w, h = rect['x'], rect['y'], rect['width'], rect['height']
    if y >= im.height or x >= im.width:
        print(f'SKIP {name}: rect y={y} x={x} exceeds image {im.size} (stale scroll position)')
        full_file.unlink()
        rect_file.unlink()
        continue
    x2, y2 = min(im.width, x + w), min(im.height, y + h)
    crop = im.crop((x, y, x2, y2))
    crop.save(shots / f'{name}.png')
    full_file.unlink()
    rect_file.unlink()
    count += 1
    print(f'cropped {name}: {crop.size}')
print(f'done, {count} crops')
