#!/usr/bin/env python3
"""Build or verify data/rosary.json from USCCB's How to Pray the Rosary page.

Only the four set titles and the five mystery names in each set are stored.
How-to steps, scripture verses, fruits of the mystery, and other prayers are
left on the USCCB page and are not copied.

  python3 tools/fetch-rosary.py           # fetch and write data/rosary.json
  python3 tools/fetch-rosary.py --check   # re-fetch and diff against the stored file
"""
import datetime, json, os, re, sys, time, urllib.error, urllib.request, html, difflib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'rosary.json')
PAGE = 'https://www.usccb.org/how-to-pray-the-rosary'
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
      'Accept': 'text/html'}
SETS = [
    ('joyful', 'joyful-mysteries'),
    ('sorrowful', 'sorrowful-mysteries'),
    ('glorious', 'glorious-mysteries'),
    ('luminous', 'luminous-mysteries'),
]

def fetch(url):
    for attempt in range(4):
        time.sleep(2 + 8 * attempt)
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode('utf-8')
        except urllib.error.HTTPError as e:
            if e.code != 403 or attempt == 3:
                raise

def parse(page):
    sets = []
    for sid, anchor in SETS:
        m = re.search(r'<h2[^>]*id="%s"[^>]*>(.*?)</h2>(.*?)(?=<h2\b)' % re.escape(anchor), page, re.S | re.I)
        if not m:
            raise SystemExit('USCCB page is missing #' + anchor)
        name = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', m.group(1)))).strip()
        mysteries = [re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', hm.group(1)))).strip()
                     for hm in re.finditer(r'<h3[^>]*>(.*?)</h3>', m.group(2), re.S | re.I)]
        if len(mysteries) != 5:
            raise SystemExit('%s: expected 5 mystery titles, got %s' % (anchor, mysteries))
        sets.append({
            'id': sid,
            'name': name,
            'anchor': anchor,
            'url': PAGE + '#' + anchor,
            'mysteries': mysteries,
        })
    return sets

def main():
    check = '--check' in sys.argv
    prev = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    sets = parse(fetch(PAGE))
    rec = {
        'source': 'United States Conference of Catholic Bishops, How to Pray the Rosary',
        'source_url': PAGE,
        'copied': prev.get('copied') if prev.get('sets') == sets else datetime.date.today().isoformat(),
        'sets': sets,
    }
    if check:
        stored = {k: prev[k] for k in ('source', 'source_url', 'sets') if k in prev}
        fresh = {k: rec[k] for k in ('source', 'source_url', 'sets')}
        if stored == fresh:
            print('MATCH', PAGE)
            return
        print('DIFF', PAGE)
        a = json.dumps(stored, indent=2, ensure_ascii=False)
        b = json.dumps(fresh, indent=2, ensure_ascii=False)
        sys.stdout.writelines(difflib.unified_diff(a.splitlines(1), b.splitlines(1), 'stored', 'source'))
        sys.exit(1)
    json.dump(rec, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    open(OUT, 'a', encoding='utf-8').write('\n')
    print('wrote', OUT)
    for s in sets:
        print('====', s['name'])
        print('\n'.join(s['mysteries']))
        print()

if __name__ == '__main__':
    main()
