#!/usr/bin/env python3
"""Build or verify data/prayers.json from USCCB's own prayer pages.

The text is parsed straight out of each usccb.org page (nothing is typed by
hand): paragraphs, line breaks, bold markers such as "V/." and "R/.", and
punctuation are kept exactly. A small-print notice on the page is stored
as `notice` and shown with the prayer.

Link-only prayers ('link' entries) store no text at all -- just the title, a
one-line label and the URL; the app shows a button to that page. --check also
re-opens each link and confirms the prayer is still there (`expect`).

  python3 tools/fetch-prayers.py           # fetch and write data/prayers.json
  python3 tools/fetch-prayers.py --check   # re-fetch and diff against the stored file
"""
import datetime, difflib, html, json, os, re, sys, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'prayers.json')
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
      'Accept': 'text/html'}
# In display order.
#   text:    copy the whole prayer from the page (no restrictive notice on it).
#   extract: copy only the paragraphs from the one starting `first` through the one
#            equal to `last` (a prayer printed inside a longer page).
#   link:    the page restricts copying, so store no text: title, button, label, URL.
PRAYERS = [
    # "Excerpted from Catholic Household Blessings and Prayers ... All rights reserved."
    {'kind': 'link', 'id': 'angelus', 'title': 'Angelus', 'label': 'Opens usccb.org',
     'url': 'https://www.usccb.org/prayers/angelus'},
    {'kind': 'text', 'id': 'regina-caeli', 'url': 'https://www.usccb.org/prayers/regina-caeli'},
    {'kind': 'text', 'id': 'our-father', 'url': 'https://www.usccb.org/prayers/our-father'},
    {'kind': 'text', 'id': 'hail-mary', 'url': 'https://www.usccb.org/prayers/hail-mary'},
    {'kind': 'text', 'id': 'apostles-creed', 'url': 'https://www.usccb.org/prayers/apostles-creed'},
    {'kind': 'text', 'id': 'nicene-creed', 'url': 'https://www.usccb.org/prayers/nicene-creed'},
    # cites "*From the Order of Penance, nos. 45 and 92." (ICEL ritual book)
    {'kind': 'link', 'id': 'act-contrition', 'title': 'Act of Contrition', 'label': 'Opens usccb.org',
     'url': 'https://www.usccb.org/prayers/act-contrition'},
    # USCCB has no prayer page; the Catechism for Adults (copyrighted book) prints it -> link only
    {'kind': 'link', 'id': 'spiritual-communion', 'title': 'Act of Spiritual Communion',
     'label': 'Opens usccb.org (Catechism for Adults)', 'expect': 'An Act of Spiritual Communion',
     'url': 'https://www.usccb.org/sites/default/files/flipbooks/uscca/files/assets/basic-html/page-562.html'},
    {'kind': 'text', 'id': 'hail-holy-queen-salve-regina', 'url': 'https://www.usccb.org/prayers/hail-holy-queen-salve-regina'},
    # page footer: "\u00a92020 Archdiocese of Toronto. All rights reserved." -> link only
    {'kind': 'link', 'id': 'st-michael', 'title': 'Prayer of St. Michael',
     'button': 'Pray the St. Michael prayer at the Archdiocese of Toronto', 'label': 'Opens archtoronto.org',
     'expect': 'Saint Michael the Archangel',
     'url': 'https://www.archtoronto.org/en/offices-and-ministries/sub-sites/feast-of-stmichael/home/prayer-of-st.-michael/'},
    {'kind': 'extract', 'id': 'st-francis', 'title': 'Prayer of St. Francis',
     'note': "From USCCB\u2019s Prayer for the New Year", 'url': 'https://www.usccb.org/prayers/prayer-new-year',
     'first': 'Lord, make me an instrument of your peace', 'last': '\u2014Attributed to St. Francis of Assisi'},
]

def fetch(url):
    # usccb.org's firewall returns 403 to rapid requests: go slowly and retry.
    for attempt in range(4):
        time.sleep(2 + 8 * attempt)
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode('utf-8')
        except urllib.error.HTTPError as e:
            if e.code != 403 or attempt == 3:
                raise

def segments(fragment):
    """Inline HTML -> [{"t": text, "b"?: bold, "i"?: italic}] (text unescaped, tags dropped).
    Source-code whitespace (newlines/indentation between tags) is collapsed the way a
    browser displays it; the words and punctuation are untouched."""
    out = []
    for m in re.finditer(r'<(strong|b|em|i)>(.*?)</\1>|([^<]+)|<[^>]+>', fragment, re.S):
        if m.group(3) is not None:
            seg = {'t': m.group(3)}
        elif m.group(1):
            seg = {'t': re.sub(r'<[^>]+>', '', m.group(2))}
            seg['b' if m.group(1) in ('strong', 'b') else 'i'] = True
        else:
            continue
        seg['t'] = html.unescape(re.sub(r'[ \t\r\n]+', ' ', seg['t']))
        out.append(seg)
    if out: out[0]['t'] = out[0]['t'].lstrip(' ')
    if out: out[-1]['t'] = out[-1]['t'].rstrip(' ')
    return [x for x in out if x['t']]

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
    prev = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    stored = prev if check else None
    out, bad = {'source': 'United States Conference of Catholic Bishops, usccb.org prayer pages', 'prayers': []}, 0
    for item in PRAYERS:
        pid, url = item['id'], item['url']
        if item['kind'] == 'link':
            rec = {'id': pid, 'title': item['title'], 'link_only': True, 'label': item['label'], 'source_url': url}
            if item.get('button'):
                rec['button'] = item['button']
            out['prayers'].append(rec)
            if check:
                s = next(p for p in stored['prayers'] if p['id'] == pid)
                ok = s == rec
                if ok and item.get('expect'):   # the linked page still shows this prayer
                    ok = item['expect'] in html.unescape(fetch(url))
                print(('LINK  ' if ok else 'DIFF  ') + pid, url)
                bad += 0 if ok else 1
            continue
        title, paras, notice = parse(fetch(url))
        if item['kind'] == 'extract':
            texts = [''.join(sg['t'] for sg in p[0]) for p in paras]
            i = next(n for n, t in enumerate(texts) if t.startswith(item['first']))
            j = next(n for n, t in enumerate(texts) if n >= i and ''.join(''.join(sg['t'] for sg in ln) for ln in paras[n]) == item['last'])
            paras, notice, title = paras[i:j + 1], None, item['title']
        if check:
            s = next(p for p in stored['prayers'] if p['id'] == pid)
            a, b = plain(s['paragraphs'], s.get('notice')), plain(paras, notice)
            same = a == b and s['title'] == title and json.dumps(s['paragraphs']) == json.dumps(paras)
            print(('MATCH ' if same else 'DIFF  ') + pid, url)
            if not same:
                bad += 1
                sys.stdout.writelines(difflib.unified_diff(a.splitlines(1), b.splitlines(1), 'stored', 'source'))
            continue
        old = next((p for p in prev.get('prayers', []) if p['id'] == pid), {})
        copied = old.get('copied') if old.get('paragraphs') == paras else None  # keep date if text unchanged
        rec = {'id': pid, 'title': title, 'source_url': url,
               'copied': copied or datetime.date.today().isoformat(), 'paragraphs': paras}
        if item.get('note'):
            rec['note'] = item['note']
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
