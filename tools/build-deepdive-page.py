#!/usr/bin/env python3
"""Build the static, no-JavaScript Deep Dive page from data/deepdive.json.

Writes deep-dive/index.html (served at /daily-bread/deep-dive/). The page shows the same
periods, items and links as the in-app Deep Dive overlay, as plain HTML that crawlers and
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
html{scroll-behavior:smooth}
.wrap{max-width:560px;margin:0 auto;padding:max(14px,env(safe-area-inset-top)) 16px 40px}
.band{height:8px;background:var(--accent);border-radius:0 0 8px 8px;margin:-14px -16px 14px}
header{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px}
.brand{min-height:33px;display:flex;align-items:center;font:600 15px/1.2 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--mu);text-decoration:none}
.today-link{display:inline-block;font:600 14px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink);background:none;border:1px solid var(--bd);border-radius:999px;padding:6px 12px;text-decoration:none;white-space:nowrap}
@media (max-width:420px){.today-link{padding:6px 10px}}
h1{margin:18px 0 0;font-size:24px;line-height:1.25}
.review{display:inline-block;text-decoration:none;font:700 17px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink);border:2px solid var(--accent-ink);border-radius:12px;padding:10px 16px}
.dd-intro{margin:8px 0 4px;font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.dd-jump{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 4px}
.dd-chip{font:600 12px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink);text-decoration:none;border:1px solid var(--bd);background:#fff;border-radius:999px;padding:5px 10px;white-space:nowrap}
.dd-group{scroll-margin-top:12px}
.dd-group h2{font:700 16px/1.3 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--tx);text-transform:none;letter-spacing:0;margin:26px 0 6px;padding-bottom:6px;border-bottom:2px solid var(--accent)}
.dd-questions{margin:4px 0 8px;font:14px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.dd-questions summary{cursor:pointer;font-weight:600;color:var(--accent-ink)}
.dd-qlist{margin:6px 0 0;padding-left:18px}
.dd-qlist li{margin:2px 0}
.dd-gnote{margin:4px 0 0;font:14px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.dd-evidence{margin:8px 0 4px;padding:10px 12px;background:rgba(46,125,50,.06);border:1px solid var(--bd);border-radius:10px;font:13px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.dd-evidence p{margin:0 0 6px}
.dd-evidence p:last-child{margin:0}
.dd-evidence strong{color:var(--tx);font-weight:700}
.dd-item{margin-top:10px;background:var(--card);border:1px solid var(--bd);border-top:4px solid var(--accent);border-radius:14px;padding:12px 16px 14px}
.dd-item h3{margin:0;font:700 20px/1.25 Georgia,"Times New Roman",serif}
.dd-by{margin:2px 0 0;font:600 14px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink)}
.dd-meta{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 0;align-items:center}
.dd-date{font:600 12px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.dd-cat{font:600 11px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink);background:rgba(46,125,50,.08);border:1px solid var(--bd);border-radius:999px;padding:2px 8px;white-space:nowrap}
.dd-caution{margin:0;max-width:100%}
.dd-caution[open]{flex:1 1 100%}
.dd-caution summary{list-style:none;cursor:pointer;display:inline-flex;align-items:center;gap:3px;font:600 11px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#8a6a2f;background:rgba(184,134,11,.1);border:1px solid rgba(184,134,11,.35);border-radius:999px;padding:2px 8px;white-space:nowrap}
.dd-caution summary::-webkit-details-marker{display:none}
.dd-caution summary::marker{content:""}
.dd-caution-body{margin:6px 0 0;padding:8px 10px;font:13px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu);background:rgba(184,134,11,.07);border:1px solid rgba(184,134,11,.28);border-radius:8px}
.dd-line{margin:6px 0 8px;font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.dd-flag{margin:0 0 10px;font:12px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu);font-style:italic}
.dd-item .review{font-size:15px;padding:8px 12px}
.dd-ph{margin:0 0 6px;font:600 13px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.dd-parts{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 4px}
.dd-parts a{font:600 14px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink);text-decoration:none;border:1px solid var(--bd);background:#fff;border-radius:999px;padding:5px 10px}
.dd-item .dd-parts{margin-top:8px}
.dd-sec{display:table;margin-top:10px;font:600 14px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink)}

.dd-fun-in-strip{margin:8px 0 6px;padding:0}
.dd-fun-label{margin:0 0 6px;font:700 12px/1.3 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink);letter-spacing:.02em}
.dd-fun-card{margin:0 0 6px;padding:8px 10px;background:rgba(46,125,50,.07);border:1px solid rgba(46,125,50,.2);border-radius:10px}
.dd-fun-card:last-child{margin-bottom:8px}
.dd-fun-card-top{display:flex;flex-wrap:wrap;align-items:center;gap:5px;margin:0 0 3px}
.dd-fun-title{font:700 13px/1.35 Georgia,"Times New Roman",serif;color:var(--tx)}
.dd-fun-detail{margin:0;font:12px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.dd-fun-srcs{margin:4px 0 0;font:11px/1.3 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.dd-fun-srcs a{color:var(--accent-ink);text-decoration:none}
.dd-meanwhile{margin:8px 0 6px;padding:6px 10px 8px;background:rgba(46,125,50,.04);border:1px solid var(--bd);border-radius:10px;font:13px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu);max-width:100%;overflow:hidden}
.dd-meanwhile summary{cursor:pointer;font-weight:600;color:var(--accent-ink)}
.dd-meanwhile-scroll{display:flex;gap:8px;overflow-x:auto;overflow-y:hidden;-webkit-overflow-scrolling:touch;margin:8px 0 2px;padding-bottom:4px;scroll-snap-type:x proximity;max-width:100%}
.dd-meanwhile-card{flex:0 0 auto;width:min(220px,72vw);scroll-snap-align:start;background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:8px 10px}
.dd-meanwhile-top{display:flex;flex-wrap:wrap;align-items:center;gap:4px;margin:0 0 4px}
.dd-meanwhile-date{font:700 11px/1.2 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink);letter-spacing:.02em}
.dd-meanwhile-text{margin:0;font:12px/1.4 Georgia,"Times New Roman",serif;color:var(--tx)}
.dd-meanwhile-src{display:inline-block;margin-top:5px;font:600 11px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink);text-decoration:none}
.dd-item-mw{margin:2px 0 8px;font:12px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.dd-item-mw-ico{font-size:11px;opacity:.7}
.dd-item-mw-src{font:600 11px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink);text-decoration:none;white-space:nowrap}
.dd-legend{display:inline-block;font:600 10px/1 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#5a6b5c;background:rgba(46,125,50,.08);border:1px solid rgba(46,125,50,.22);border-radius:999px;padding:2px 6px;vertical-align:middle;letter-spacing:.03em;text-transform:lowercase}
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


def chip_label(title):
    return title.split('\u00b7')[0].strip() if '\u00b7' in title else title


def legend_badge():
    return '<span class="dd-legend" title="Legend — not verified history">legend</span>'


def render_meanwhile(entries, fun=None):
    entries = entries or []
    fun = fun or []
    if not entries and not fun:
        return []
    out = []
    w = out.append
    w('    <details class="dd-meanwhile">')
    w('      <summary>Meanwhile in the world</summary>')
    if fun:
        w('      <div class="dd-fun-in-strip">')
        w('        <p class="dd-fun-label">✦ Fun overlaps</p>')
        for f in fun:
            w('        <div class="dd-fun-card">')
            w('          <div class="dd-fun-card-top">')
            w('            <span class="dd-fun-title">%s</span>' % e(f.get('title') or ''))
            if f.get('legend'):
                w('            ' + legend_badge())
            w('          </div>')
            if f.get('detail'):
                w('          <p class="dd-fun-detail">%s</p>' % e(f['detail']))
            srcs = f.get('sources') or ([f['source']] if f.get('source') else [])
            if srcs:
                links = ' · '.join(
                    '<a href="%s" target="_blank" rel="noopener">source</a>' % e(u) for u in srcs)
                w('          <p class="dd-fun-srcs">%s</p>' % links)
            w('        </div>')
        w('      </div>')
    if entries:
        w('      <div class="dd-meanwhile-scroll">')
        for ent in entries:
            w('        <div class="dd-meanwhile-card">')
            w('          <div class="dd-meanwhile-top">')
            w('            <span class="dd-meanwhile-date">%s</span>' % e(ent.get('date') or ''))
            if ent.get('legend'):
                w('            ' + legend_badge())
            w('          </div>')
            w('          <p class="dd-meanwhile-text">%s</p>' % e(ent.get('text') or ''))
            if ent.get('source'):
                w('          <a class="dd-meanwhile-src" href="%s" target="_blank" rel="noopener">source</a>' % e(ent['source']))
            w('        </div>')
        w('      </div>')
    w('    </details>')
    return out


def render_item_meanwhile(mw):
    if not mw or not mw.get('text'):
        return []
    parts = ['    <p class="dd-item-mw"><span class="dd-item-mw-ico" aria-hidden="true">🌍</span> ',
             e(mw['text'])]
    line = ''.join(parts)
    if mw.get('legend'):
        line += ' ' + legend_badge()
    if mw.get('source'):
        line += ' <a class="dd-item-mw-src" href="%s" target="_blank" rel="noopener">source</a>' % e(mw['source'])
    line += '</p>'
    return [line]



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
    w('<title>Deep Dive: Chronological Reading Library | Daily Bread</title>')
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
    if data.get('groups'):
        w('  <nav class="dd-jump" aria-label="Jump to period">')
        for g in data['groups']:
            w('    <a class="dd-chip" href="#dd-%s">%s</a>' % (e(g['id']), e(chip_label(g['title']))))
        w('  </nav>')
    for g in data['groups']:
        w('  <section class="dd-group" id="dd-%s">' % e(g['id']))
        w('    <h2>%s</h2>' % e(g['title']))
        qs = g.get('questions') or []
        if qs:
            w('    <details class="dd-questions">')
            w('      <summary>Guiding questions</summary>')
            w('      <ul class="dd-qlist">')
            for q in qs:
                w('        <li>%s</li>' % e(q))
            w('      </ul>')
            w('    </details>')
        if g.get('note'):
            w('    <p class="dd-gnote">%s</p>' % e(g['note']))
        for line in render_meanwhile(g.get('meanwhile') or [], g.get('fun_overlaps') or []):
            w(line)
        ev = g.get('evidence') or {}
        if ev:
            w('    <div class="dd-evidence">')
            if ev.get('shows'):
                w('      <p><strong>Evidence shows:</strong> %s</p>' % e(ev['shows']))
            if ev.get('infer'):
                w('        <p><strong>Historians infer:</strong> %s</p>' % e(ev['infer']))
            if ev.get('unknown'):
                w('      <p><strong>Still unknown:</strong> %s</p>' % e(ev['unknown']))
            w('    </div>')
        for it in g['items']:
            links = it['links']
            w('    <article class="dd-item" id="dd-%s">' % e(it['id']))
            w('      <h3>%s</h3>' % e(it['title']))
            w('      <p class="dd-by">%s</p>' % e(it['author']))
            if it.get('date') or it.get('category') or it.get('caution'):
                w('      <div class="dd-meta">')
                if it.get('date'):
                    w('        <span class="dd-date">%s</span>' % e(it['date']))
                if it.get('category'):
                    w('        <span class="dd-cat">%s</span>' % e(it['category']))
                if it.get('caution'):
                    w('        <details class="dd-caution">')
                    w('          <summary>ⓘ Read with care</summary>')
                    w('          <p class="dd-caution-body">%s</p>' % e(it['caution']))
                    w('        </details>')
                w('      </div>')
            w('      <p class="dd-line">%s</p>' % e(it['line']))
            for line in render_item_meanwhile(it.get('meanwhile')):
                w(line)
            if it.get('flag'):
                w('      <p class="dd-flag">%s</p>' % e(it['flag']))
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
