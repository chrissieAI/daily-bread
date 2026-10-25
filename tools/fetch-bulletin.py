#!/usr/bin/env python3
"""Find the latest Our Lady of Guadalupe (Buckingham, PA) bulletin PDF link.

Reads the parish's bulletin listing page (https://www.olguadalupe.org/bulletin),
picks the most recent dated bulletin link, checks it responds, and saves only
its date + URL into data/parish.json ("bulletin" section). The bulletin's
contents are never downloaded into the repo or copied into the app.

Usage (from the repo root; Python 3 standard library only):
    python3 tools/fetch-bulletin.py
Then commit data/parish.json and push.
"""
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.request

LISTING = "https://www.olguadalupe.org/bulletin"
UA = {"User-Agent": "DailyBread/1.0 (personal app; latest-bulletin link check)"}
PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "parish.json")
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], 1)}


def get(url, method="GET"):
    req = urllib.request.Request(url, headers=UA, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, (r.read().decode("utf-8", "replace") if method == "GET" else "")


def parse_date(text):
    # "October 25, 2026" or "December 21 & 25, 2025" (first day is used)
    m = re.match(r"\s*([A-Za-z]+)\s+(\d{1,2})(?:\s*&\s*\d{1,2})?,\s*(\d{4})\s*$", text)
    if not m or m.group(1).lower() not in MONTHS:
        return None
    return dt.date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2)))


def main():
    status, page = get(LISTING)
    found = []
    for m in re.finditer(r'<a[^>]+href="(https://www\.olguadalupe\.org/_files/ugd/[^"]+\.pdf)"[^>]*>(.*?)</a>', page, re.S):
        label = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", m.group(2)))).strip()
        d = parse_date(label)
        if d:
            found.append((d, label, m.group(1)))
    if not found:
        print("No dated bulletin links found on", LISTING, "- leaving data/parish.json unchanged")
        return 1
    today = dt.date.today()
    # Bulletins are dated for the coming Sunday, so allow dates up to a week ahead.
    usable = [f for f in found if f[0] <= today + dt.timedelta(days=7)] or found
    d, label, url = max(usable, key=lambda f: f[0])
    try:
        ok = get(url, "HEAD")[0] == 200
    except Exception:
        ok = get(url)[0] == 200
    if not ok:
        print("Latest bulletin link did not respond:", url)
        return 1
    data = json.load(open(PATH, encoding="utf-8"))
    data["bulletin"].update({
        "latest_date": d.isoformat(),
        "latest_label": label,
        "latest_url": url,
        "checked": today.isoformat(),
    })
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"Latest bulletin: {label} -> {url} ({len(found)} dated links found)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
