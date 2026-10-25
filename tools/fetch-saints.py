#!/usr/bin/env python3
"""Build data/saints.json for the "Saint of the day" card.

Input: tools/saints-picks.json -- hand-checked mapping of each saint day
(from romcal, US calendar) to a Catholic Encyclopedia (1913) entry and a
Franciscan Media "Saint of the Day" slug.

  "ce":   New Advent entry id (e.g. "16026a") or a full Wikisource CE13 URL.
          Omit for saints with no 1913 entry -> name + link only.
  "para": paragraph index where the biography starts (default 0).
  "skip": number of leading sentences to skip (default 0).
  "fm"/"fm2": Franciscan Media slugs. Each is checked (HTTP 200 and the
          page <title> mentions the saint); a failing link is dropped.

The excerpt is copied word for word: whole sentences from the start of the
biography, 2-4 sentences, ~60-120 words, footnote markers stripped. Nothing
is paraphrased or added. Review the printed output before committing.

Usage: python3 tools/fetch-saints.py   (cache in tools/.cache-saints/)
"""
import html, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'tools', '.cache-saints')
BROWSER_UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')
UA = {'User-Agent': 'DailyBread/1.0 (personal app)'}

def get(url, headers=UA, cache=True):
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, re.sub(r'[^A-Za-z0-9._-]', '_', url)[-150:])
    if cache and os.path.exists(f):
        return open(f, encoding='utf-8').read()
    time.sleep(1)
    t = urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30).read().decode('utf-8', 'replace')
    if cache:
        open(f, 'w', encoding='utf-8').write(t)
    return t

def clean(s):
    s = re.sub(r'<sup[^>]*>.*?</sup>', '', s, flags=re.S)
    s = html.unescape(re.sub(r'<[^>]+>', '', s))
    s = re.sub(r'\[\d+\]', '', s)               # footnote markers
    s = re.sub(r'\s+', ' ', s).strip()
    return re.sub(r'\s+([,.;:)])', r'\1', s)

def newadvent(eid):
    url = f'https://www.newadvent.org/cathen/{eid}.htm'
    t = get(url)
    title = clean(re.search(r'<title>CATHOLIC ENCYCLOPEDIA: ([^<]*)', t).group(1))
    body = t.split('id="springfield2"')[1]
    paras = [clean(p) for p in re.findall(r'<p>(.*?)</p>', body, re.S)]
    paras = [p for p in paras if p and 'help support the mission' not in p.lower()]
    return url, title, paras

def wikisource(url):
    page = urllib.parse.unquote(url.split('/wiki/', 1)[1])
    raw = get('https://en.wikisource.org/w/index.php?title=' + urllib.parse.quote(page) + '&action=raw')
    raw = re.sub(r'\{\{CE13.*?\n\}\}', '', raw, flags=re.S)
    raw = re.sub(r'<ref[^>]*?/>|<ref.*?</ref>', '', raw, flags=re.S)
    raw = re.sub(r'\{\{(?:sc|smallcaps|uc)\|([^}]*)\}\}', r'\1', raw)
    raw = re.sub(r'\{\{[^}]*\}\}', '', raw)
    raw = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', raw)
    raw = raw.replace("'''", '').replace("''", '')
    paras = [clean(p) for p in re.split(r'\n\s*\n', raw)]
    paras = [p for p in paras if p and not p.startswith(('=', '[[Category', 'Sources'))]
    title = page.split('/', 1)[1].replace('_', ' ')
    return url, title, paras

ABBR = set('St Sts b d c ca Dec Nov Oct Sept Jan Feb Aug Apr Mar Gr Lat ed eds sqq cf Ven Bl Fr Mgr Rev vol vols p pp ch etc A.D B.C i.e e.g viz Mt Dr Mr No'.split())

def sentences(p):
    toks = p.split()
    out, cur = [], []
    for i, tok in enumerate(toks):
        cur.append(tok)
        nxt = toks[i + 1] if i + 1 < len(toks) else ''
        core = tok.rstrip('"\u201d\u2019)')
        if not re.search(r'[.!?]$', core):
            continue
        word = core[:-1].lstrip('("\u201c')
        if word in ABBR or re.fullmatch(r'[A-Z]', word) or re.fullmatch(r'(?:[A-Za-z]\.)+[A-Za-z]', word):
            continue
        if nxt and not re.match(r'["\u201c(]?[A-Z0-9]', nxt):
            continue
        out.append(' '.join(cur)); cur = []
    if cur:
        out.append(' '.join(cur))
    return out

def words(s):
    return len(s.split())

def excerpt(paras, para=0, skip=0):
    """Whole sentences from consecutive paragraphs, starting at `para`:
    stop at >= 60 words or 4 sentences, never passing ~120 words (unless the
    first sentence alone is longer). Returns a list of paragraph strings."""
    out, total, count = [], 0, 0
    for i in range(para, len(paras)):
        pt = paras[i]
        if re.fullmatch(r'\(.*\)\.?', pt):      # e.g. "(FABIANUS)" -- a name note, not biography
            continue
        sents = sentences(pt)[skip if i == para else 0:]
        cur = []
        for s in sents:
            if count and (total + words(s) > 120 or count >= 4):
                break
            cur.append(s); total += words(s); count += 1
            if total >= 60:
                break
        if cur:
            out.append(' '.join(cur))
        if total >= 60 or count >= 4 or len(cur) < len(sents):
            break
    return out

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z ]', ' ', s)

def fm_check(slug, name):
    url = f'https://www.franciscanmedia.org/saint-of-the-day/{slug}/'
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': BROWSER_UA}), timeout=30)
        t = r.read().decode('utf-8', 'replace')
        if r.status != 200 or r.geturl().rstrip('/') != url.rstrip('/'):
            return None, None
        title = html.unescape(re.search(r'<title>([^<|]*)', t).group(1)).strip()
    except Exception as e:
        print('   FM error', slug, e, file=sys.stderr)
        return None, None
    stop = {'saint', 'saints', 'and', 'the', 'of', 'i', 'companions', 'holy', 'order', 'a'}
    keys = [w for w in norm(title).split() if w not in stop and len(w) > 2]
    nm = norm(name)
    ok = bool(keys) and (keys[0] in nm or keys[0][:5] in nm)
    time.sleep(0.6)
    return (url, title) if ok else (None, title)

def main():
    picks = json.load(open(os.path.join(ROOT, 'tools', 'saints-picks.json'), encoding='utf-8'))['days']
    out = {}
    for iso, p in sorted(picks.items()):
        rec = {'name': p['name'], 'also': p.get('also', [])}
        ce = p.get('ce')
        if ce:
            url, title, paras = wikisource(ce) if ce.startswith('http') else newadvent(ce)
            ex = excerpt(paras, p.get('para', 0), p.get('skip', 0))
            rec.update(excerpt=ex, ce_url=url, ce_title=title,
                       credit='From the Catholic Encyclopedia (1913)')
        links = []
        for slug in [p.get('fm'), p.get('fm2')]:
            if not slug:
                continue
            url, title = fm_check(slug, p['name'])
            if url:
                links.append({'url': url, 'title': title})
            else:
                print(f'   !! {iso} FM link dropped: {slug} ({title})', file=sys.stderr)
        rec['fm'] = links
        out[iso] = rec
        print(f"{iso} {p['name']}\n   CE: {rec.get('ce_title','-')} | FM: {[l['title'] for l in links]}")
        if rec.get('excerpt'):
            txt = ' / '.join(rec['excerpt'])
            flag = '  <-- CHECK QUOTES' if re.search(r'["\u201c]', txt) else ''
            print(f"   [{words(txt)}w]{flag} {txt}")
    path = os.path.join(ROOT, 'data', 'saints.json')
    json.dump({'source_note': 'Excerpts are verbatim from the Catholic Encyclopedia (1913, public domain), '
               'via New Advent or Wikisource; Franciscan Media is linked only.',
               'days': out}, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('wrote', path, len(out), 'days;', sum(1 for r in out.values() if r.get('excerpt')), 'with excerpts')

if __name__ == '__main__':
    main()
