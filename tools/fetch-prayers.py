#!/usr/bin/env python3
"""Build or verify data/prayers.json from USCCB's own prayer pages.

The text is parsed straight out of each usccb.org page (nothing is typed by
hand): paragraphs, line breaks, bold markers such as "V/." and "R/.", and
punctuation are kept exactly. A small-print notice on the page (e.g. the
copyright line) is stored as `notice` and shown with the prayer.

  python3 tools/fetch-prayers.py           # fetch and write data/prayers.json
  python3 tools/fetch-prayers.py --check   # re-fetch and diff against the stored file
"""
import datetime, difflib, html, json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'prayers.json')
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
      'Accept': 'text/html'}
PRAYERS = [
    ('angelus', 'https://www.usccb.org/prayers/angelus'),
    ('regina-caeli', 'https://www.usccb.org/prayers/regina-caeli'),
]

def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode('utf-8')

def segments(fragment):
    """Inline HTML -> [{"t": text, "b"?: bold, "i"?: italic}] (text unescaped, tags dropped)."""
    out = []
    for m in re.finditer(r'<(strong|b|em|i)>(.*?)</\1>|([^<]+)|<[^>]+>', fragment, re.S):
        if m.group(3) is not None:
            t = html.unescape(m.group(3))
            if t: out.append({'t': t})
        elif m.group(1):
            t = html.unescape(re.sub(r'<[^>]+>', '', m.group(2)))
            seg = {'t': t}
            seg['b' if m.group(1) in ('strong', 'b') else 'i'] = True
            out.append(seg)
    return out

def parse(page):
    title = html.unescape(re.search(r'<h1 class="title-page">(.*?)</h1>', page, re.S).group(1).strip())
    body = re.search(r'<div class="body b-prayer">(.*?)</div>', page, re.S).group(1)
    paras, notice = [], None
    for attrs, inner in re.findall(r'<p([^>]*)>(.*?)</p>', body, re.S):
        if 'small' in attrs:
            notice = segments(inner)
            continue
        paras.append([segments(line) for line in re.split(r'<br\s*/?>', inner)])
    return title, paras, notice

def plain(paras, notice):
    """Plain text used for the exact-match check (what a reader sees)."""
    txt = '\n\n'.join('\n'.join(''.join(s['t'] for s in line) for line in p) for p in paras)
    if notice:
        txt += '\n\n' + ''.join(s['t'] for s in notice)
    return txt

def main():
    check = '--check' in sys.argv
    stored = json.load(open(OUT, encoding='utf-8')) if check else None
    out, bad = {'source': 'United States Conference of Catholic Bishops, usccb.org prayer pages', 'prayers': []}, 0
    for pid, url in PRAYERS:
        title, paras, notice = parse(fetch(url))
        if check:
            s = next(p for p in stored['prayers'] if p['id'] == pid)
            a, b = plain(s['paragraphs'], s.get('notice')), plain(paras, notice)
            same = a == b and s['title'] == title and json.dumps(s['paragraphs']) == json.dumps(paras)
            print(('MATCH ' if same else 'DIFF  ') + pid, url)
            if not same:
                bad += 1
                sys.stdout.writelines(difflib.unified_diff(a.splitlines(1), b.splitlines(1), 'stored', 'usccb.org'))
            continue
        rec = {'id': pid, 'title': title, 'source_url': url,
               'copied': datetime.date.today().isoformat(), 'paragraphs': paras}
        if notice:
            rec['notice'] = notice
        out['prayers'].append(rec)
        print('=====', title, url); print(plain(paras, notice)); print()
    if check:
        sys.exit(1 if bad else 0)
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('wrote', OUT)

if __name__ == '__main__':
    main()
