#!/usr/bin/env python3
"""Fetch daily Mass reading REFERENCES (citations only) from bible.usccb.org.

Saves ONLY each day's title and the reading headings + citations
(e.g. "Reading 1" -> "Exodus 22:20-26") to readings.json.
It never stores any reading text: the Lectionary text is copyrighted and
the app links out to bible.usccb.org for the readings themselves.

Usage (run from the repo root; Python 3 standard library only):
    python3 tools/fetch-references.py                # today (America/New_York) + 120 days
    python3 tools/fetch-references.py --days 60
    python3 tools/fetch-references.py --start 2026-12-01 --days 30
    python3 tools/fetch-references.py --missing-only   # only fill gaps

Polite: about 1 request per second, with backoff/retry on 403/429/5xx. Stops after a few consecutive 404s
(i.e. when USCCB has not published pages that far ahead yet).
Existing entries in readings.json are kept and refreshed/merged.
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

BASE = "https://bible.usccb.org/bible/readings/"
UA = "DailyBread/1.0 (personal reading-reference index; github.com/chrissieAI/daily-bread)"
DELAY = 1.0


def usccb_code(d):
    return d.strftime("%m%d%y")


def clean(fragment):
    fragment = re.sub(r"<br\s*/?>", " ", fragment, flags=re.I)
    # tags, allowing ">" / "<" inside quoted attribute values
    fragment = re.sub(r"""<(?:[^>"']|"[^"]*"|'[^']*')*>""", "", fragment)
    return re.sub(r"\s+", " ", html.unescape(fragment)).strip()


_last = [0.0]


def _get_once(url):
    wait = DELAY - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except (urllib.error.URLError, TimeoutError):
        return 0, ""


def get(url):
    """GET with backoff: the site sometimes answers 403/429/5xx to quick runs."""
    for backoff in (0, 5, 15, 30):
        if backoff:
            time.sleep(backoff)
        status, body = _get_once(url)
        if status == 200 or status == 404:
            return status, body
    return status, body


def parse_title(page):
    m = re.search(r'<div class="wr-block b-lectionary[^"]*"[^>]*>.*?<h2>(.*?)</h2>', page, re.S)
    if m:
        return clean(m.group(1))
    m = re.search(r"<title>(.*?)</title>", page, re.S)
    return clean(m.group(1)).replace("| USCCB", "").strip() if m else ""


# USCCB sometimes glues a non-verse reference onto the heading when the
# address block is empty, e.g. <h3>Alleluia See Te Deum</h3><div class="address">…</div>.
# Split those so the row stays label + reference.
_HEADING_BASE = (
    r"Reading\s+\d+"
    r"|Responsorial Psalm"
    r"|Alleluia"
    r"|Gospel"
    r"|Sequence"
    r"|Verse [Bb]efore the Gospel"
)
_HEADING_SPLIT = re.compile(r"^(" + _HEADING_BASE + r")\s+(.+)$", re.I)


def normalize_citation(citation):
    """Drop empty/junk address leftovers (broken USCCB <a> tags leave stray quotes)."""
    citation = (citation or "").strip()
    if not citation or re.fullmatch(r'[\s"\'>/\\]*', citation):
        return ""
    return citation


def split_heading_citation(heading, citation):
    """If USCCB put the reference in the heading, peel it into citation."""
    heading = (heading or "").strip()
    citation = normalize_citation(citation)
    m = _HEADING_SPLIT.match(heading)
    if not m:
        return heading, citation
    base, rest = m.group(1).strip(), m.group(2).strip()
    if not citation and rest:
        return base, rest
    # Prefer a real address citation; still restore the clean label.
    return base, citation or rest


def parse_readings(page):
    """Return [{heading, citation}] from the page's reading blocks (no text)."""
    out = []
    for m in re.finditer(
        r'<h3 class="name">(.*?)</h3>\s*<div class="address">(.*?)</div>', page, re.S
    ):
        heading, citation = split_heading_citation(clean(m.group(1)), clean(m.group(2)))
        if heading:
            # citation may be "" when USCCB lists none (e.g. some Alleluia verses)
            out.append({"heading": heading, "citation": citation})
    return out


def parse_subpages(page, code):
    """Days like Christmas split into several Masses on separate pages."""
    seen, subs = set(), []
    # Only look in the main content (after the day's title, before the footer
    # blocks), not in the pager at the top of the page.
    start = page.find('<div class="wr-block b-lectionary padding-bottom')
    end = page.find("b-button-container social", start)
    scope = page[start:end] if start != -1 and end != -1 else page
    for m in re.finditer(
        r'<a href="(https://bible\.usccb\.org/bible/readings/%s-[^"]+)"[^>]*>(.*?)</a>' % code,
        scope, re.S,
    ):
        url, name = m.group(1), clean(m.group(2))
        if url not in seen:
            seen.add(url)
            subs.append((name, url))
    return subs


def fetch_day(d):
    code = usccb_code(d)
    url = BASE + code + ".cfm"
    status, page = get(url)
    if status != 200:
        return status, None
    entry = {"title": parse_title(page), "url": url, "masses": []}
    readings = parse_readings(page)
    if readings:
        entry["masses"].append({"name": None, "url": url, "readings": readings})
    else:
        for name, sub in parse_subpages(page, code):
            s, p = get(sub)
            if s == 200:
                entry["masses"].append({"name": name, "url": sub, "readings": parse_readings(p)})
    return 200, entry


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", help="YYYY-MM-DD (default: today in America/New_York)")
    ap.add_argument("--days", type=int, default=120, help="max days to try (default 120)")
    ap.add_argument("--stop-after-404s", type=int, default=3)
    ap.add_argument("--missing-only", action="store_true", help="skip dates already in readings.json")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "readings.json"))
    a = ap.parse_args()

    if a.start:
        start = dt.date.fromisoformat(a.start)
    else:
        start = dt.datetime.now(ZoneInfo("America/New_York")).date() if ZoneInfo else dt.date.today()

    out = os.path.abspath(a.out)
    data = {"days": {}}
    if os.path.exists(out):
        with open(out, encoding="utf-8") as f:
            data = json.load(f)
    days = data.setdefault("days", {})

    misses = fetched = 0
    for i in range(a.days):
        d = start + dt.timedelta(days=i)
        if a.missing_only and d.isoformat() in days and all(m["readings"] for m in days[d.isoformat()]["masses"]) and days[d.isoformat()]["masses"]:
            continue
        status, entry = fetch_day(d)
        if status == 200:
            misses = 0
            fetched += 1
            days[d.isoformat()] = entry
            n = sum(len(m["readings"]) for m in entry["masses"])
            print(f"{d} ok  {entry['title']!r} ({n} refs)")
        elif status == 404:
            misses += 1
            print(f"{d} HTTP 404")
            if misses >= a.stop_after_404s:
                print("Stopping: USCCB has no pages this far ahead yet.")
                break
        else:
            print(f"{d} HTTP {status} (gave up after retries; existing entry kept)")

    data["source"] = "https://bible.usccb.org/bible/readings/ (references only; no reading text)"
    data["generated"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    data["days"] = dict(sorted(days.items()))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"Saved {fetched} day(s) this run; {len(days)} total in {out}")


if __name__ == "__main__":
    sys.exit(main())
