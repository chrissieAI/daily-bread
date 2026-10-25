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

## Saint of the day

The "Saint of the day" card (below the liturgical day) shows the day's saint from
romcal (US calendar): the celebration itself on saint feasts/memorials, or the first
optional memorial on weekdays, with any others listed under "Also today". It is hidden
on Sundays, ferial weekdays, and non-saint celebrations (Christ the King, Christmas,
Marian feasts, etc.).

- **Excerpt**: a short word-for-word passage (whole sentences, ~60-120 words) from the
  start of the saint's entry in the public-domain *Catholic Encyclopedia* (1913), via the
  [New Advent](https://www.newadvent.org/cathen/) transcription (Wikisource for
  St. John Neumann, which New Advent lacks), credited and linked to the entry. Nothing is
  paraphrased or added. Saints with no 1913 entry (e.g. Cabrini, Juan Diego) get no excerpt.
- **Franciscan Media**: link only ("Read more at Franciscan Media"); each URL is checked
  for HTTP 200 and a page title naming the saint, otherwise the link is dropped.

Data: `data/saints.json`. To rebuild or extend: edit `tools/saints-picks.json`
(date -> name, CE entry id or Wikisource URL, optional starting paragraph, Franciscan
Media slug), then run `python3 tools/fetch-saints.py` and read every printed excerpt.

## Prayers

The header "Prayers" button opens a full-screen list of prayer titles; tap one to expand it.
Each prayer is either copied word for word (line breaks, V./R. markers, punctuation kept,
with a source link and the date copied) or, where the source restricts copying, shown as a
link card with no text stored:

| Prayer | How | Source / deciding notice |
|---|---|---|
| Angelus (Regina Caeli in Easter season) | link | usccb.org/prayers/angelus: "Excerpted from Catholic Household Blessings and Prayers ... All rights reserved." |
| Regina Caeli | text | usccb.org/prayers/regina-caeli (site footer only) |
| Our Father, Hail Mary, Apostles' Creed, Nicene Creed | text | their usccb.org/prayers pages (site footer only) |
| Act of Contrition | link | usccb.org/prayers/act-contrition cites the *Order of Penance* |
| Act of Spiritual Communion | link | USCCB *Catechism for Adults* p. 562 (no USCCB prayer page) |
| Hail, Holy Queen | text | usccb.org/prayers/hail-holy-queen-salve-regina (site footer only) |
| Prayer of St. Michael | link | Archdiocese of Toronto page: "©2020 Archdiocese of Toronto. All rights reserved." |
| Prayer of St. Francis | text (extract) | only the St. Francis prayer from usccb.org/prayers/prayer-new-year |

The Regina Caeli replaces the Angelus during romcal's Easter season (Easter Sunday through
Pentecost). The shortcut below the parish card reads "Pray the Angelus at USCCB" or, in the
Easter season, "Pray the Regina Caeli".

Data: `data/prayers.json`. The list (order, text/extract/link) is `PRAYERS` in
`tools/fetch-prayers.py`. Rebuild with `python3 tools/fetch-prayers.py`; verify stored text
against a fresh fetch (and that each link still shows its prayer) with
`python3 tools/fetch-prayers.py --check`.
