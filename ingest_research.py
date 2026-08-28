"""Ingest 4 JSON arrays of research profiles (from delegated research subagents)
into a single RESEARCH_PROFILES dict keyed by product id, then inject it into
build_elements_site.py as the RESEARCH_PROFILES constant."""
import json
import re
import sys
from pathlib import Path

def main():
    combined = {}
    for arg in sys.argv[1:]:
        data = json.loads(Path(arg).read_text(encoding='utf-8'))
        for item in data:
            combined[item['id']] = item
    print(f'ingested {len(combined)} profiles: {sorted(combined.keys())}')

    py_path = Path('build_elements_site.py')
    content = py_path.read_text(encoding='utf-8')
    marker = "RESEARCH_PROFILES = {}  # populated below with verified scientific research profiles, keyed by product id"
    assert marker in content, "RESEARCH_PROFILES placeholder not found"
    new_const = "RESEARCH_PROFILES = " + json.dumps(combined, ensure_ascii=False, indent=4)
    content = content.replace(marker, new_const, 1)
    py_path.write_text(content, encoding='utf-8')
    print('RESEARCH_PROFILES constant written into build_elements_site.py')

if __name__ == '__main__':
    main()
