#!/usr/bin/env python3
"""Build the static, no-JavaScript Deep Dive page from data/deepdive.json.

Writes deep-dive/index.html (served at /daily-bread/deep-dive/). The page shows the same
groups, items and links as the in-app Deep Dive overlay, as plain HTML that crawlers and
readers without JavaScript can see. Links only: the 'expect' phrases are not included.

Usage:
  python3 tools/build-deepdive-page.py           write deep-dive/index.html
  python3 tools/build-deepdive-page.py --check   exit 1 if deep-dive/index.html is out of date
Stdlib only. Output is deterministic: the same JSON always gives the same file."""
import html, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'deepdive.json')
OUT = os.path.join(ROOT, 'deep-dive', 'index.html')
CANONICAL = 'https://chrissieai.github.io/daily-bread/deep-dive/'
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
          'September', 'October', 'November', 'December']
ARROW = ' \u2197'  # same "↗" suffix the app adds to every Deep Dive link label

# Styles copied from index.html (same variables, fonts, colors and card styles as the app's
# header pills and Deep Dive overlay). The app has no dark mode, so neither does this page.
CSS = """\
:root{--accent:#2e7d32;--accent-ink:#2e7d32;--bg:#f7f2e8;--card:#fffdf8;--tx:#2a2420;--mu:#6b6058;--bd:#e6dccb}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--tx);font:18px/1.5 Georgia,"Iowan Old Style","Palatino Linotype",Palatino,serif;-webkit-text-size-adjust:100%}
.wrap{max-width:560px;margin:0 auto;padding:max(14px,env(safe-area-inset-top)) 16px 40px}
.band{height:8px;background:var(--accent);border-radius:0 0 8px 8px;margin:-14px -16px 14px}
header{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px}
.brand{min-height:33px;display:flex;align-items:center;font:600 15px/1.2 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--mu);text-decoration:none}
.today-link{display:inline-block;font:600 14px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink);background:none;border:1px solid var(--bd);border-radius:999px;padding:6px 12px;text-decoration:none;white-space:nowrap}
@media (max-width:420px){.today-link{padding:6px 10px}}
h1{margin:18px 0 0;font-size:24px;line-height:1.25}
.review{display:inline-block;text-decoration:none;font:700 17px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink);border:2px solid var(--accent-ink);border-radius:12px;padding:10px 16px}
.dd-intro{margin:8px 0 4px;font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.dd-group h2{font:600 13px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu);text-transform:uppercase;letter-spacing:.08em;margin:22px 0 2px}
.dd-gnote{margin:2px 0 0;font:14px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.dd-item{margin-top:10px;background:var(--card);border:1px solid var(--bd);border-top:4px solid var(--accent);border-radius:14px;padding:12px 16px 14px}
.dd-item h3{margin:0;font:700 20px/1.25 Georgia,"Times New Roman",serif}
.dd-by{margin:2px 0 0;font:600 14px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink)}
.dd-line{margin:6px 0 10px;font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.dd-item .review{font-size:15px;padding:8px 12px}
.dd-ph{margin:0 0 6px;font:600 13px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.dd-parts{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 4px}
.dd-parts a{font:600 14px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink);text-decoration:none;border:1px solid var(--bd);background:#fff;border-radius:999px;padding:5px 10px}
.dd-item .dd-parts{margin-top:8px}
.dd-sec{display:table;margin-top:10px;font:600 14px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink)}
.dd-checked{margin:22px 0 0;font:13px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu);text-align:center}
.back-bottom{margin:18px 0 0;text-align:center}
"""


def e(s):
    return html.escape(str(s), quote=True)


def checked_text(iso):
    if not iso:
        return ''
    y, m, d = (int(x) for x in iso.split('-'))
    return 'Links checked %s %d, %d.' % (MONTHS[m - 1], d, y)


def link(cls, ln):
    return '<a class="%s" href="%s" target="_blank" rel="noopener">%s</a>' % (
        cls, e(ln['url']), e(ln['label'] + ARROW))


def render(data):
    intro = data.get('intro') or ''
    out = []
    w = out.append
    w('<!DOCTYPE html>')
    w('<!-- Generated from data/deepdive.json by tools/build-deepdive-page.py. Do not edit by hand. -->')
    w('<html lang="en">')
    w('<head>')
    w('<meta charset="utf-8">')
    w('<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">')
    w('<meta name="theme-color" content="#f7f2e8">')
    w('<title>Deep Dive: Church Fathers and Saints Reading List | Daily Bread</title>')
    w('<meta name="description" content="%s">' % e(intro))
    w('<link rel="canonical" href="%s">' % CANONICAL)
    w('<link rel="manifest" href="../manifest.webmanifest">')
    w('<link rel="icon" href="../icon.svg" type="image/svg+xml">')
    w('<link rel="apple-touch-icon" href="../icon-192.png">')
    w('<style>')
    w(CSS.rstrip('\n'))
    w('</style>')
    w('</head>')
    w('<body>')
    w('<div class="wrap">')
    w('  <div class="band" aria-hidden="true"></div>')
    w('  <header>')
    w('    <a class="brand" href="../">Daily Bread</a>')
    w('    <a class="today-link" href="../">&lsaquo; Back to Daily Bread</a>')
    w('  </header>')
    w('  <main>')
    w('  <h1>Deep Dive</h1>')
    if intro:
        w('  <p class="dd-intro">%s</p>' % e(intro))
    for g in data['groups']:
        w('  <section class="dd-group" id="dd-%s">' % e(g['id']))
        w('    <h2>%s</h2>' % e(g['title']))
        if g.get('note'):
            w('    <p class="dd-gnote">%s</p>' % e(g['note']))
        for it in g['items']:
            links = it['links']
            w('    <article class="dd-item" id="dd-%s">' % e(it['id']))
            w('      <h3>%s</h3>' % e(it['title']))
            w('      <p class="dd-by">%s</p>' % e(it['author']))
            w('      <p class="dd-line">%s</p>' % e(it['line']))
            # Same order and grouping as app.js renderDeepDive: primary, then heading + parts, then secondary.
            for ln in links:
                if ln['kind'] == 'primary':
                    w('      ' + link('review dd-primary', ln))
            parts = [ln for ln in links if ln['kind'] == 'part']
            if parts:
                if it.get('links_heading'):
                    w('      <p class="dd-ph">%s</p>' % e(it['links_heading']))
                w('      <div class="dd-parts">')
                for ln in parts:
                    w('        ' + link('dd-part', ln))
                w('      </div>')
            for ln in links:
                if ln['kind'] == 'secondary':
                    w('      ' + link('dd-sec', ln))
            w('    </article>')
        w('  </section>')
    ct = checked_text(data.get('checked'))
    if ct:
        w('  <p class="dd-checked">%s</p>' % e(ct))
    w('  </main>')
    w('  <p class="back-bottom"><a class="today-link" href="../">&lsaquo; Back to Daily Bread</a></p>')
    w('</div>')
    w('</body>')
    w('</html>')
    return '\n'.join(out) + '\n'


def build():
    with open(SRC, encoding='utf-8') as f:
        return render(json.load(f))


def is_fresh():
    """True if deep-dive/index.html matches what build() would write from the current JSON."""
    try:
        with open(OUT, encoding='utf-8', newline='') as f:
            return f.read() == build()
    except FileNotFoundError:
        return False


def main(argv):
    if '--check' in argv:
        if is_fresh():
            print('deep-dive/index.html is up to date with data/deepdive.json')
            return 0
        print('FAIL  deep-dive/index.html is out of date: run python3 tools/build-deepdive-page.py')
        return 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write(build())
    print('wrote deep-dive/index.html')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
