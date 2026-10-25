#!/usr/bin/env python3
"""Check every Deep Dive link in data/deepdive.json: it must load (HTTP 200) and
contain its expected phrase. Links only; nothing is copied from the pages.
Usage: python3 tools/verify-deepdive.py   (exit code 1 if any link fails)"""
import html, json, os, re, sys, time, urllib.request

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


def main():
    data = json.load(open(os.path.join(ROOT, 'data', 'deepdive.json'), encoding='utf-8'))
    bad = 0
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
    print('%d links, %d failed (data checked %s)' % (n, bad, data.get('checked')))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
