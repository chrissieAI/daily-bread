#!/usr/bin/env python3
"""Download / refresh art/discovery/*.jpg from tools/discovery-images.json.

Resizes to 800px max side, JPEG quality 82. Stdlib + Pillow.
Usage: python3 tools/fetch-discovery-images.py [--force] [--only id ...]
"""
import io, json, os, sys, time, urllib.request
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'tools', 'discovery-images.json')
OUT = os.path.join(ROOT, 'art', 'discovery')
UA = 'Mozilla/5.0 (compatible; DailyBreadDiscovery/1.0)'

def fetch(url):
    last = None
    for wait in (0, 2, 6):
        time.sleep(0.2 + wait)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception as e:
            last = e
    raise RuntimeError('%s: %s' % (url, last))

def main(argv):
    force = '--force' in argv
    only = [a for a in argv[1:] if not a.startswith('-')]
    with open(SRC, encoding='utf-8') as f:
        rows = json.load(f)
    os.makedirs(OUT, exist_ok=True)
    for row in rows:
        iid = row['id']
        if only and iid not in only:
            continue
        dest = os.path.join(OUT, iid + '.jpg')
        if os.path.exists(dest) and os.path.getsize(dest) > 2000 and not force:
            print('skip', iid)
            continue
        data = fetch(row['download_url'])
        im = Image.open(io.BytesIO(data)).convert('RGB')
        w, h = im.size
        m = 800
        if max(w, h) > m:
            if w >= h:
                im = im.resize((m, int(h * m / w)), Image.Resampling.LANCZOS)
            else:
                im = im.resize((int(w * m / h), m), Image.Resampling.LANCZOS)
        im.save(dest, 'JPEG', quality=82, optimize=True)
        print('wrote', dest, os.path.getsize(dest))
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
