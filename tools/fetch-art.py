#!/usr/bin/env python3
"""Build data/art.json and art/YYYY-MM-DD.jpg from tools/art-picks.json.

Each pick names one museum object (aic:<id>, cma:<id> or met:<id>). The script
re-reads the museum's own open-access API, refuses anything that is not marked
public domain / CC0, downloads the image, resizes it (1200px long side, plus a
360px thumbnail), and writes the caption metadata. Descriptions are copied word
for word (first N sentences) only from museums whose license allows reuse:
  - Art Institute of Chicago: `description` field is CC BY 4.0 (credited)
  - Cleveland Museum of Art: all open-access metadata is CC0 (credited anyway)
  - The Met: no description text in the API -> caption only
The Gospel citation comes from readings.json; the feast name from the pick.

Usage: python3 tools/fetch-art.py [--only 2026-12-12 ...] [--force]
"""
import html, io, json, os, re, sys, time, urllib.request, urllib.parse
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BROWSER_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
AIC_H = {"AIC-User-Agent": "DailyBread (personal app)", "User-Agent": "DailyBread/1.0"}

def get(url, headers=None, raw=False):
    last = None
    for wait in (0, 2, 6, 15):
        time.sleep(0.3 + wait)
        try:
            url = urllib.parse.quote(url, safe=":/?&=%,!~*'()+@#")
            req = urllib.request.Request(url, headers=headers or {"User-Agent": BROWSER_UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
                return data if raw else json.loads(data)
        except Exception as e:
            last = e
    raise RuntimeError(f"fetch failed {url}: {last}")

def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return re.sub(r"\s+([,.;:!?])", r"\1", s)

def sentences(text, n):
    raw = re.split(r"(?<=[.!?])\s+(?=[A-Z\u201c\"])", clean(text))
    parts = []
    for piece in raw:  # re-join splits after abbreviations such as "St."
        if parts and re.search(r"\b(St|Sts|Mt|Dr|Mr|Mrs|ca|c|no|No)\.$", parts[-1]):
            parts[-1] += " " + piece
        else:
            parts.append(piece)
    return " ".join(parts[:n]).strip()

def aic(oid):
    fields = "id,title,artist_display,artist_title,date_display,medium_display,image_id,is_public_domain,description,credit_line,place_of_origin"
    d = get(f"https://api.artic.edu/api/v1/artworks/{oid}?fields={fields}", AIC_H)
    x = d["data"]
    assert x.get("is_public_domain"), f"aic:{oid} not public domain"
    return {
        "title": x["title"], "artist": x.get("artist_title") or (x.get("artist_display") or "").split("\n")[0],
        "date": x.get("date_display"), "medium": x.get("medium_display"),
        "museum": "Art Institute of Chicago", "object_url": f"https://www.artic.edu/artworks/{oid}",
        "license": "Image: public domain (CC0), Art Institute of Chicago open access",
        "description": x.get("description") or "",
        "excerpt_credit": "Description: Art Institute of Chicago (CC BY 4.0)",
        "image_url": f"https://www.artic.edu/iiif/2/{x['image_id']}/full/1686,/0/default.jpg",
    }

def cma(oid):
    x = get(f"https://openaccess-api.clevelandart.org/api/artworks/{oid}")["data"]
    assert x.get("share_license_status") == "CC0", f"cma:{oid} not CC0"
    cr = (x.get("creators") or [{}])
    artist = cr[0].get("description", "") if cr else ""
    artist = re.sub(r"\s*\(.*\)$", "", artist) or ", ".join(x.get("culture") or [])
    imgs = x.get("images") or {}
    url = (imgs.get("print") or imgs.get("web") or {}).get("url")
    return {
        "title": x["title"], "artist": artist, "date": x.get("creation_date"),
        "medium": x.get("technique"), "museum": "Cleveland Museum of Art",
        "object_url": x.get("url") or f"https://www.clevelandart.org/art/{x.get('accession_number')}",
        "license": "Image and data: CC0, Cleveland Museum of Art open access",
        "description": x.get("wall_description") or x.get("description") or "",
        "excerpt_credit": "Description: Cleveland Museum of Art (CC0)",
        "image_url": url,
    }

def met(oid):
    x = get(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}")
    assert x.get("isPublicDomain"), f"met:{oid} not public domain"
    return {
        "title": x["title"], "artist": x.get("artistDisplayName") or (x.get("culture") or ""),
        "date": x.get("objectDate"), "medium": x.get("medium"),
        "museum": "The Metropolitan Museum of Art", "object_url": x.get("objectURL"),
        "license": "Image: public domain (CC0), The Met Open Access",
        "description": "", "excerpt_credit": "",
        "image_url": x.get("primaryImage") or x.get("primaryImageSmall"),
    }

def save_jpeg(im, path, long_side, hi, lo=60):
    im = im.copy()
    im.thumbnail((long_side, long_side), Image.LANCZOS)
    for q in range(88, lo - 1, -4):
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() <= hi:
            break
    open(path, "wb").write(buf.getvalue())
    return im.size

def gospel_for(readings, iso):
    day = (readings.get("days") or {}).get(iso) or {}
    for m in day.get("masses") or []:
        for r in m.get("readings") or []:
            if "gospel" in (r.get("heading") or "").lower() and r.get("citation"):
                return r["citation"]
    return None

def main():
    args = sys.argv[1:]
    force = "--force" in args
    only = [a for a in args if re.match(r"\d{4}-\d\d-\d\d$", a)]
    picks = json.load(open(os.path.join(ROOT, "tools", "art-picks.json")))
    readings = json.load(open(os.path.join(ROOT, "readings.json")))
    out_path = os.path.join(ROOT, "data", "art.json")
    old = json.load(open(out_path))["days"] if os.path.exists(out_path) else {}
    os.makedirs(os.path.join(ROOT, "art", "thumbs"), exist_ok=True)
    days = {}
    for iso in sorted(picks["days"]):
        p = picks["days"][iso]
        if only and iso not in only and iso in old:
            days[iso] = old[iso]; continue
        src, oid = p["source"].split(":")
        meta = {"aic": aic, "cma": cma, "met": met}[src](oid)
        img_path = f"art/{iso}.jpg"; th_path = f"art/thumbs/{iso}.jpg"
        full = os.path.join(ROOT, img_path)
        prev = (old.get(iso) or {}).get("source")
        if force or not os.path.exists(full) or (prev and prev != p["source"]):
            hdr = {"User-Agent": BROWSER_UA}
            if src == "aic":
                hdr["AIC-User-Agent"] = AIC_H["AIC-User-Agent"]
            try:
                data = get(meta["image_url"], hdr, raw=True)
            except RuntimeError:
                if "/full/1686," not in meta["image_url"]:
                    raise
                data = None
                for alt in ("/full/!1200,1200/", "/full/!843,843/"):
                    try:
                        data = get(meta["image_url"].replace("/full/1686,/", alt), hdr, raw=True); break
                    except RuntimeError:
                        pass
                if data is None:
                    raise
            im = Image.open(io.BytesIO(data)).convert("RGB")
            save_jpeg(im, full, 1200, 290_000)
            save_jpeg(im, os.path.join(ROOT, th_path), 360, 40_000)
        w, h = Image.open(full).size
        e = {
            "source": p["source"], "title": meta["title"], "artist": meta["artist"],
            "date": meta["date"], "medium": meta["medium"], "museum": meta["museum"],
            "object_url": meta["object_url"], "license": meta["license"],
            "image": img_path, "thumb": th_path, "width": w, "height": h,
            "match": p.get("match", "gospel"),
        }
        if p.get("chosen_for"): e["chosen_for"] = p["chosen_for"]
        g = p.get("gospel") or gospel_for(readings, iso)
        if g: e["gospel"] = g
        n = p.get("excerpt_sentences", 0)
        if n and meta["description"] and meta["excerpt_credit"]:
            e["excerpt"] = sentences(meta["description"], n)
            e["excerpt_credit"] = meta["excerpt_credit"]
        days[iso] = e
        print(iso, p["source"], "|", e["title"], "|", e["artist"], "|", w, "x", h, flush=True)
    json.dump({"note": "One public-domain artwork per day. Captions are museum metadata; excerpts are quoted word for word from openly licensed museum descriptions.",
               "days": days}, open(out_path, "w"), indent=1, ensure_ascii=False)
    print("wrote", len(days), "days")

if __name__ == "__main__":
    main()
