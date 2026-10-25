#!/usr/bin/env python3
"""Check every review link in data/movies.json: HTTP 200 and the page title matches.

Usage (from the repo root; Python 3 standard library only):
    python3 tools/verify-movies.py
Exits non-zero if any link fails. About 1 request per second.
"""
import html, json, os, re, sys, time, unicodedata, urllib.error, urllib.request

UA = {"User-Agent": "DailyBread/1.0 (personal app; review link check)"}
PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "movies.json")


def norm(s):
    s = unicodedata.normalize("NFKD", html.unescape(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def fetch(url):
    for backoff in (0, 5, 15):
        time.sleep(1 + backoff)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 404, ""
        except Exception:
            pass
    return 0, ""


def main():
    weeks = json.load(open(PATH, encoding="utf-8"))["weeks"]
    bad = 0
    for w in weeks:
        status, page = fetch(w["review_url"])
        m = re.search(r"<h1>(.*?)</h1>", page, re.S) or re.search(r"<title>(.*?)</title>", page, re.S)
        heading = re.sub(r"<[^>]+>", "", m.group(1)) if m else ""
        ok = status == 200 and norm(w["title"]) in norm(heading)
        bad += not ok
        print(("ok  " if ok else "FAIL"), w["week_start"], status, w["title"], "|", heading.strip()[:80])
    print(f"{len(weeks) - bad}/{len(weeks)} links ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
