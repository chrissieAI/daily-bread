#!/usr/bin/env python3
"""Build the static, no-JavaScript Archaeology Finds page from data/discovery.json.

Writes archaeology/index.html (served at /daily-bread/archaeology/). Same finds as the
in-app Archaeology overlay: groups in chronological order, local images under art/discovery/,
Read with care tags, evidence collapsibles, and cross-links into Deep Dive.

Usage:
  python3 tools/build-archaeology-page.py           write archaeology/index.html
  python3 tools/build-archaeology-page.py --check   exit 1 if out of date
Stdlib only. Output is deterministic."""
import html, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'discovery.json')
OUT = os.path.join(ROOT, 'archaeology', 'index.html')
CANONICAL = 'https://chrissieai.github.io/daily-bread/archaeology/'
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
          'September', 'October', 'November', 'December']

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
@media (max-width:420px){.today-link{padding:6px 10px;font-size:13px}}
h1{margin:18px 0 0;font-size:24px;line-height:1.25}
.dd-intro{margin:8px 0 4px;font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.dd-jump{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 4px}
.dd-chip{font:600 12px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink);text-decoration:none;border:1px solid var(--bd);background:#fff;border-radius:999px;padding:5px 10px;white-space:nowrap}
.dd-group{scroll-margin-top:12px}
.dd-group h2{font:700 16px/1.3 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--tx);text-transform:none;letter-spacing:0;margin:26px 0 6px;padding-bottom:6px;border-bottom:2px solid var(--accent)}
.dd-gnote{margin:4px 0 10px;font:14px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.arch-sub{margin:16px 0 8px;font:700 13px/1.3 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu);letter-spacing:.02em;text-transform:uppercase}
.dd-caution{margin:6px 0 0;max-width:100%}
.dd-caution summary{list-style:none;cursor:pointer;display:inline-flex;align-items:center;gap:3px;font:600 11px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#8a6a2f;background:rgba(184,134,11,.1);border:1px solid rgba(184,134,11,.35);border-radius:999px;padding:2px 8px;white-space:nowrap}
.dd-caution summary::-webkit-details-marker{display:none}
.dd-caution summary::marker{content:""}
.dd-caution-body{margin:6px 0 0;padding:8px 10px;font:13px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu);background:rgba(184,134,11,.07);border:1px solid rgba(184,134,11,.28);border-radius:8px}
.dd-disc-card{margin:0 0 12px;padding:10px;background:var(--card);border:1px solid var(--bd);border-radius:12px;scroll-margin-top:12px}
.dd-disc-fig{margin:0 0 6px}
.dd-disc-fig img{display:block;width:100%;max-width:100%;height:auto;border-radius:8px;background:#eee}
.dd-disc-credit{margin:4px 0 0;font:11px/1.35 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.dd-disc-credit a{color:var(--accent-ink);text-decoration:none;font-weight:600}
.dd-disc-name{margin:0;font:700 16px/1.25 Georgia,"Times New Roman",serif;color:var(--tx)}
.dd-disc-type{margin:2px 0 0;font:600 12px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink)}
.dd-disc-date{margin:2px 0 0;font:600 12px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.dd-disc-line{margin:6px 0 0;font:13px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.dd-disc-ev{margin:8px 0 0}
.dd-disc-ev summary{cursor:pointer;font:600 12px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink)}
.dd-disc-ev-body{margin:6px 0 0;padding:8px 10px;background:rgba(46,125,50,.06);border:1px solid var(--bd);border-radius:8px;font:12px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.dd-disc-ev-body p{margin:0 0 5px}
.dd-disc-ev-body p:last-child{margin:0}
.dd-disc-ev-body strong{color:var(--tx);font-weight:700}
.dd-disc-meta{margin:6px 0 0;font:12px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.dd-disc-refs{margin:6px 0 0;font:12px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu)}
.dd-disc-srcs{margin:6px 0 0;font:12px/1.35 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.dd-disc-srcs a{color:var(--accent-ink);text-decoration:none;font-weight:600;margin-right:8px}
.dd-writelink{display:inline-block;margin:8px 0 0;font:600 13px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink);text-decoration:none;border-bottom:1px dotted rgba(46,125,50,.45)}
.dd-checked{margin:22px 0 0;font:13px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--mu);text-align:center}
.dd-backtop{margin:14px 0 0;text-align:center}
.dd-backtop a{font:600 13px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--accent-ink);text-decoration:none}
.back-bottom{margin:28px 0 0;text-align:center}
"""


def e(s):
    return html.escape(s or '', quote=True)


def checked_text(checked):
    if not checked:
        return ''
    try:
        y, m, d = checked.split('-')
        return 'Links checked %s %s, %s.' % (MONTHS[int(m) - 1], int(d), y)
    except Exception:
        return 'Links checked %s.' % checked


def chip_label(title):
    # Short chip from group title
    t = (title or '').split('·')[0].strip()
    if t.startswith('Ancient Israel'):
        return 'Ancient Israel'
    if t.startswith('The world of the Gospels'):
        return 'Gospels world'
    return t


def items_for(disc, period):
    return [it for it in (disc.get('items') or []) if it.get('period') == period]


def render_card(it):
    lines = []
    w = lines.append
    w('    <article class="dd-disc-card" id="disc-%s">' % e(it['id']))
    im = it.get('image') or {}
    if im.get('src'):
        src = im['src']
        if src.startswith('art/'):
            src = '../' + src
        w('      <figure class="dd-disc-fig">')
        w('        <img src="%s" alt="%s" loading="lazy" decoding="async">' % (
            e(src), e(im.get('alt') or it.get('name') or '')))
        credit_bits = []
        if im.get('credit'):
            credit_bits.append(im['credit'])
        if im.get('license'):
            credit_bits.append(im['license'])
        credit = ' · '.join(credit_bits)
        if im.get('license_url'):
            w('        <figcaption class="dd-disc-credit">%s · <a href="%s" target="_blank" rel="noopener">license</a></figcaption>' % (
                e(credit), e(im['license_url'])))
        else:
            w('        <figcaption class="dd-disc-credit">%s</figcaption>' % e(credit))
        w('      </figure>')
    w('      <h3 class="dd-disc-name">%s</h3>' % e(it.get('name') or ''))
    if it.get('type'):
        w('      <p class="dd-disc-type">%s</p>' % e(it['type']))
    if it.get('date'):
        w('      <p class="dd-disc-date">%s</p>' % e(it['date']))
    if it.get('caution'):
        w('      <details class="dd-caution">')
        w('        <summary>ⓘ Read with care</summary>')
        w('        <p class="dd-caution-body">%s</p>' % e(it['caution']))
        w('      </details>')
    if it.get('line'):
        w('      <p class="dd-disc-line">%s</p>' % e(it['line']))
    if it.get('found') or it.get('now'):
        meta = []
        if it.get('found'):
            meta.append('Found: ' + it['found'])
        if it.get('now'):
            meta.append('Now: ' + it['now'])
        w('      <p class="dd-disc-meta">%s</p>' % e(' · '.join(meta)))
    refs = it.get('bible_refs') or []
    if refs:
        w('      <p class="dd-disc-refs">Bible: %s</p>' % e('; '.join(refs)))
    ev = it.get('evidence') or {}
    if ev.get('shows') or ev.get('infer') or ev.get('debated'):
        w('      <details class="dd-disc-ev">')
        w('        <summary>Evidence shows / Scholars infer / Still debated</summary>')
        w('        <div class="dd-disc-ev-body">')
        if ev.get('shows'):
            w('          <p><strong>Evidence shows:</strong> %s</p>' % e(ev['shows']))
        if ev.get('infer'):
            w('          <p><strong>Scholars infer:</strong> %s</p>' % e(ev['infer']))
        if ev.get('debated'):
            w('          <p><strong>Still debated:</strong> %s</p>' % e(ev['debated']))
        w('        </div>')
        w('      </details>')
    srcs = it.get('sources') or []
    if srcs:
        w('      <p class="dd-disc-srcs">')
        for s in srcs:
            w('        <a href="%s" target="_blank" rel="noopener">%s ↗</a>' % (
                e(s['url']), e(s.get('label') or 'Source')))
        w('      </p>')
    # Cross-link into Deep Dive
    connects = it.get('connects_to') or []
    dd_period = it.get('deepdive_period')
    if connects:
        wid = connects[0]
        w('      <a class="dd-writelink" href="../deep-dive/#dd-%s">Read the writings from this time</a>' % e(wid))
    elif dd_period:
        w('      <a class="dd-writelink" href="../deep-dive/#dd-%s">Read the writings from this time</a>' % e(dd_period))
    w('    </article>')
    return lines


def render(data):
    intro = data.get('intro') or ''
    label = data.get('label') or 'Archaeology Finds'
    out = []
    w = out.append
    w('<!DOCTYPE html>')
    w('<!-- Generated from data/discovery.json by tools/build-archaeology-page.py. Do not edit by hand. -->')
    w('<html lang="en">')
    w('<head>')
    w('<meta charset="utf-8">')
    w('<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">')
    w('<meta name="theme-color" content="#f7f2e8">')
    w('<title>%s | Daily Bread</title>' % e(label))
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
    w('<div class="wrap" id="top">')
    w('  <div class="band" aria-hidden="true"></div>')
    w('  <header>')
    w('    <a class="brand" href="../">Daily Bread</a>')
    w('    <span style="display:flex;flex-wrap:wrap;gap:8px;align-items:center">')
    w('      <a class="today-link" href="../">&lsaquo; Back to Daily Bread</a>')
    w('      <a class="today-link" href="../deep-dive/">Historic Writings</a>')
    w('    </span>')
    w('  </header>')
    w('  <main>')
    w('  <h1>%s</h1>' % e(label))
    if intro:
        w('  <p class="dd-intro">%s</p>' % e(intro))
    groups = data.get('groups') or []
    if groups:
        w('  <nav class="dd-jump" aria-label="Jump to group">')
        for g in groups:
            if items_for(data, g['id']):
                w('    <a class="dd-chip" href="#arch-%s">%s</a>' % (e(g['id']), e(chip_label(g['title']))))
        w('  </nav>')
    for g in groups:
        items = items_for(data, g['id'])
        if not items:
            continue
        w('  <section class="dd-group" id="arch-%s">' % e(g['id']))
        w('    <h2>%s</h2>' % e(g['title']))
        if g.get('note'):
            w('    <p class="dd-gnote">%s</p>' % e(g['note']))
        subgroups = g.get('subgroups') or []
        if subgroups:
            by_sub = {}
            for it in items:
                by_sub.setdefault(it.get('subgroup') or '', []).append(it)
            for sg in subgroups:
                sub_items = by_sub.get(sg['id']) or []
                if not sub_items:
                    continue
                w('    <p class="arch-sub" id="arch-sub-%s">%s</p>' % (e(sg['id']), e(sg['title'])))
                for it in sub_items:
                    for line in render_card(it):
                        w(line)
        else:
            for it in items:
                for line in render_card(it):
                    w(line)
        w('    <p class="dd-backtop"><a href="#top">Back to top</a></p>')
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
    try:
        with open(OUT, encoding='utf-8', newline='') as f:
            return f.read() == build()
    except FileNotFoundError:
        return False


def main(argv):
    if '--check' in argv:
        if is_fresh():
            print('archaeology/index.html is up to date with data/discovery.json')
            return 0
        print('FAIL  archaeology/index.html is out of date: run python3 tools/build-archaeology-page.py')
        return 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write(build())
    print('wrote archaeology/index.html')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
