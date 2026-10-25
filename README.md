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
- `data/movies.json` — "Movie of the week" (weeks start Sunday): title, year, type, rating exactly
  as the source states it, source name and review URL. Picks come only from films featured or
  reviewed positively by [Formation Reimagined](https://formationreimagined.org/movie/) (Family
  Movie Night; USCCB ratings as listed there) and [Decent Films](https://decentfilms.com/)
  (Steven D. Greydanus). No review text, synopses or images are copied.
- `data/parish.json` — "My Parish": Our Lady of Guadalupe (Buckingham/Doylestown, PA) address, phone and
  Mass/Confession times copied word for word from https://www.olguadalupe.org/ (with the date checked),
  plus the latest bulletin link.
- `tools/fetch-bulletin.py` — finds the newest dated bulletin PDF on https://www.olguadalupe.org/bulletin
  and saves only its date + URL to `data/parish.json`. Rerun weekly, then commit and push. If the saved
  bulletin is more than a week old, the app's button falls back to the parish bulletin page.
- `tools/verify-movies.py` — re-checks every review link (HTTP 200 + title match).
- `art/YYYY-MM-DD.jpg` (+ `art/thumbs/`) and `data/art.json` — "Art for today": one public-domain
  artwork per day, matched to the day's feast/saint or Gospel. Images and captions come from museum
  open-access programs: The Met (CC0), Art Institute of Chicago (images/data CC0; `description`
  CC BY 4.0) and Cleveland Museum of Art (CC0). Captions are museum metadata only; the optional
  1–2 sentence excerpt is quoted word for word from the museum (AIC or Cleveland) and credited.
  `match` in `data/art.json` says how each pick relates to the day: `feast`, `gospel`, `partial`
  (related to the Gospel but not the exact scene), `theme` (liturgical day/season) or `general`
  (no close match found; a general image of Christ, shown with the Gospel citation only).
  Favorites are stored only in the browser (`localStorage`).
- `tools/art-picks.json` + `tools/fetch-art.py` — the chosen object per day, and the script that re-reads
  each museum API, refuses anything not marked public domain/CC0, downloads and resizes the image
  (1200px long side) and writes `data/art.json`. Add days to the picks file and rerun to extend.

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
