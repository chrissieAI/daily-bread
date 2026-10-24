# Daily Bread

A small personal Catholic "Today" page: the date, the liturgical season, color and
celebration (General Roman Calendar as used in the USA), the day's Mass reading
**references**, and a big button that opens the readings on bible.usccb.org.

Live site: https://chrissieai.github.io/daily-bread/

## What's here

- `index.html`, `app.js` — the whole app (plain HTML/CSS/JS, no build step).
- `vendor/romcal/` — [romcal](https://github.com/romcal/romcal) `3.0.0-dev.141` (MIT) and
  `@romcal/calendar.united-states` `3.0.0-dev.141` (IIFE builds), bundled locally so
  the site has no CDN dependency. Computes season, color, celebration and rank in the browser.
- `readings.json` — reading headings + citations only (e.g. "Gospel — Matthew 22:34-40")
  and the USCCB day title, scraped from bible.usccb.org page headings.
- `tools/fetch-references.py` — refreshes `readings.json` (Python 3 stdlib only).

## Content rule

No scripture, prayer, or reflection text is stored or generated here. The Lectionary
text is © USCCB and may not be reproduced, so the app shows only citations and links out
to https://bible.usccb.org/bible/readings/MMDDYY.cfm .

## Refreshing reading references

Run from the repo root on any computer (not in the browser — USCCB sends no CORS headers):

```sh
python3 tools/fetch-references.py              # today + 120 days (~1 request/sec)
python3 tools/fetch-references.py --missing-only
git add readings.json && git commit -m "Refresh reading references" && git push
```

The "Read at USCCB" button works for any date even when `readings.json` has no entry.
