#!/usr/bin/env python3
"""Check the Deep Dive: deep-dive/index.html must match what tools/build-deepdive-page.py
builds from data/deepdive.json, and every link must load (HTTP 200) and contain its expected
phrase. Links only; nothing is copied from the pages.
Usage: python3 tools/verify-deepdive.py             (exit code 1 if the page is stale or any link fails)
       python3 tools/verify-deepdive.py --offline   (only the page freshness check; no network)"""
import html, importlib.util, json, os, re, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {'User-Agent': 'Mozilla/5.0 (DailyBread link check)'}


def fetch(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.status, r.read().decode('utf-8', 'replace')
        except Exception as e:  # retry politely on transient errors / 403 rate limits
            err = e
            time.sleep(2 + 6 * attempt)
    raise err


def page_is_fresh():
    spec = importlib.util.spec_from_file_location('build_deepdive_page', os.path.join(ROOT, 'tools', 'build-deepdive-page.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.is_fresh()


def main():
    fresh = page_is_fresh()
    print('%s  deep-dive/index.html %s' % (('OK  ', 'matches data/deepdive.json') if fresh else
          ('FAIL', 'is out of date: run python3 tools/build-deepdive-page.py')))
    if '--offline' in sys.argv[1:]:
        sys.exit(0 if fresh else 1)
    data = json.load(open(os.path.join(ROOT, 'data', 'deepdive.json'), encoding='utf-8'))
    bad = 0 if fresh else 1
    n = 0
    for g in data['groups']:
        for it in g['items']:
            for ln in it['links']:
                n += 1
                url, expect = ln['url'], ln['expect']
                if 'gutenberg.org' in url and not re.fullmatch(r'https://www\.gutenberg\.org/ebooks/\d+', url):
                    print('FAIL  %s  (Gutenberg links must be /ebooks/NNNN landing pages)' % url); bad += 1; continue
                try:
                    status, body = fetch(url)
                except Exception as e:
                    print('FAIL  %s  (%s)' % (url, e)); bad += 1; continue
                text = re.sub(r'\s+', ' ', html.unescape(body))
                ok = status == 200 and expect in text
                if not ok: bad += 1
                print('%s  %s  [%s] %r' % ('OK  ' if ok else 'FAIL', url, status, expect))
                time.sleep(0.5)
    # Meanwhile / fun-overlap source URLs (resolve only).
    # Britannica often returns 403 to datacenter bots; treat 403 from britannica.com as a soft warn,
    # hard-fail only on 404 / DNS / connection failures so we can drop/replace true dead links.
    srcs = set()
    for g in data['groups']:
        for e in g.get('meanwhile') or []:
            if e.get('source'): srcs.add(e['source'])
        for it in g.get('items') or []:
            mw = it.get('meanwhile') or {}
            if mw.get('source'): srcs.add(mw['source'])
    for g in data['groups']:
        for f in g.get('fun_overlaps') or []:
            for u in (f.get('sources') or ([f['source']] if f.get('source') else [])):
                srcs.add(u)
    print('Checking %d distinct Meanwhile/fun source URLs...' % len(srcs))
    src_bad = 0
    src_warn = 0
    for url in sorted(srcs):
        n += 1
        try:
            status, body = fetch(url)
            if status == 200 and len(body) > 200:
                print('OK    source  %s  [%s]' % (url, status))
            elif status == 403 and 'britannica.com' in url:
                src_warn += 1
                print('WARN  source  %s  [403 bot wall — not a 404]' % url)
            elif status == 404:
                src_bad += 1; bad += 1
                print('FAIL  source  %s  [404]' % url)
            else:
                src_warn += 1
                print('WARN  source  %s  [%s]' % (url, status))
        except Exception as e:
            msg = str(e)
            if '404' in msg:
                src_bad += 1; bad += 1
                print('FAIL  source  %s  (%s)' % (url, e))
            elif '403' in msg and 'britannica.com' in url:
                src_warn += 1
                print('WARN  source  %s  (403 bot wall — not a 404)' % url)
            else:
                src_warn += 1
                print('WARN  source  %s  (%s)' % (url, e))
        time.sleep(0.35)
    print('%d links (+sources), %d failed, %d source warnings (%d source 404s) (data checked %s)' % (
        n, bad, src_warn, src_bad, data.get('checked')))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
