"""
One-time asset fetcher: pulls openly-licensed tree/leaf photos from Wikimedia
Commons for every species in data/species.json, saves them to images/, and
records attribution (author, license, source URL) in data/attributions.json.

Strategy: pull directly from each species' own Commons category (curated by
that taxon's contributors) rather than free-text search, which is far more
reliable for species-accuracy. Falls back to search with a strict species-
epithet match if the category is missing or empty. Filters out non-photo or
non-ID-useful images (herbarium/microscope prints, galls, disease damage,
distant landscape shots, illustrations).

Only accepts CC0, Public Domain, or CC-BY / CC-BY-SA licensed files.
Uses only the Python standard library (no pip installs required).

Usage: python scripts/fetch_images.py [species_id ...]
  With no args, fetches every species missing an image.
  With args, re-fetches only the given species ids (deletes existing file first).
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECIES_PATH = ROOT / "data" / "species.json"
IMAGES_DIR = ROOT / "images"
ATTRIBUTIONS_PATH = ROOT / "data" / "attributions.json"

API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "TreeIDFlashcards/1.0 (educational flashcard project)"}

ACCEPTABLE_LICENSES = {
    "cc0", "pd", "public domain", "cc-by-1.0", "cc-by-2.0", "cc-by-2.5",
    "cc-by-3.0", "cc-by-4.0", "cc-by-sa-1.0", "cc-by-sa-2.0", "cc-by-sa-2.5",
    "cc-by-sa-3.0", "cc-by-sa-4.0",
}

GOOD_KEYWORDS = ["leaf", "leaves", "foliage", "needles", "frond"]
BAD_KEYWORDS = [
    "gall", "epidermis", "print", "microscope", "stoma", "stomata",
    "disease", "scorch", "canker", "rust", "mite", "aphid", "insect damage",
    "map", "distribution", "illustration", "drawing", "engraving", "plate",
    "diagram", "bark only", "seed ", "seedling", "flower only", "bud ",
    "buds", "bladknoppen", "suburban", "canopy", "street", "view up",
    "landscape", "range map", "herbarium",
]

TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(html):
    if not html:
        return ""
    return TAG_RE.sub("", html).strip()


def api_get(params, retries=6):
    params = {**params, "format": "json"}
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries - 1:
                wait = 5 * (attempt + 1)
                print(f"  [429] backing off {wait}s...")
                time.sleep(wait)
                continue
            raise


def category_candidates(scientific_name, limit=250):
    cat = "Category:" + scientific_name
    data = api_get({
        "action": "query",
        "generator": "categorymembers",
        "gcmtitle": cat,
        "gcmtype": "file",
        "gcmlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": 1024,
    })
    pages = data.get("query", {}).get("pages", {})
    return list(pages.values())


def search_candidates(query, limit=20):
    data = api_get({
        "action": "query",
        "generator": "search",
        "gsrnamespace": 6,
        "gsrsearch": query,
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": 1024,
    })
    pages = data.get("query", {}).get("pages", {})
    return list(pages.values())


def score_candidate(title, meta, require_good_keyword):
    t = title.lower()
    cats = meta.get("Categories", {}).get("value", "").lower()
    text = t + " " + cats
    for bad in BAD_KEYWORDS:
        if bad in text:
            return None  # disqualified
    score = 0
    has_good = False
    for good in GOOD_KEYWORDS:
        if good in t:
            score += 10
            has_good = True
    if require_good_keyword and not has_good:
        return None
    return score


def pick_best(pages, require_terms=None, require_good_keyword=True):
    candidates = []
    for page in pages:
        infos = page.get("imageinfo")
        if not infos:
            continue
        info = infos[0]
        mime = info.get("mime", "")
        if mime not in ("image/jpeg", "image/png"):
            continue
        width = info.get("width", 0)
        height = info.get("height", 0)
        if width < 400 or height < 300:
            continue
        meta = info.get("extmetadata", {})
        license_short = meta.get("LicenseShortName", {}).get("value", "").lower().strip()
        license_key = license_short.replace(" ", "-")
        if license_key not in ACCEPTABLE_LICENSES and license_short not in ACCEPTABLE_LICENSES:
            continue
        title = page.get("title", "")

        if require_terms:
            title_lower = title.lower()
            cats_lower = meta.get("Categories", {}).get("value", "").lower()
            if not any(term in title_lower or term in cats_lower for term in require_terms):
                continue

        score = score_candidate(title, meta, require_good_keyword)
        if score is None:
            continue
        # slight bonus for larger images
        score += min(width, 2000) / 2000
        candidates.append((score, page, info, license_short))

    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0], reverse=True)
    _, page, info, license_short = candidates[0]
    return page, info, license_short


def download(url, dest_path):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp, open(dest_path, "wb") as f:
        f.write(resp.read())


def fetch_one(sp, attributions):
    sid = sp["id"]
    dest = IMAGES_DIR / f"{sid}.jpg"

    scientific = sp["scientific"]
    genus, epithet = scientific.split(" ", 1)
    require_terms = [scientific.lower(), epithet.lower()]

    print(f"[category] {sid}: 'Category:{scientific}'")
    try:
        pages = category_candidates(scientific)
        # category is already species-scoped; still require a leaf/foliage keyword in the title
        choice = pick_best(pages, require_good_keyword=True)

        if not choice:
            print(f"  no leaf-labeled photo in category, trying search (strict)")
            query = sp.get("search", scientific)
            pages = search_candidates(query)
            choice = pick_best(pages, require_terms=require_terms, require_good_keyword=True)

        if not choice:
            pages = search_candidates(scientific)
            choice = pick_best(pages, require_terms=require_terms, require_good_keyword=True)

        if not choice:
            print(f"  relaxing keyword requirement (species-verified, but title may not say 'leaf')")
            pages = category_candidates(scientific)
            choice = pick_best(pages, require_good_keyword=False)

        if not choice:
            print(f"[FAIL] {sid}: no acceptable image found")
            return False

        page, info, license_short = choice
        img_url = info["thumburl"] if "thumburl" in info else info["url"]
        download(img_url, dest)

        meta = info.get("extmetadata", {})
        attributions[sid] = {
            "title": page.get("title", ""),
            "author": strip_tags(meta.get("Artist", {}).get("value", "Unknown")),
            "license": license_short,
            "licenseUrl": meta.get("LicenseUrl", {}).get("value", ""),
            "sourcePage": f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(page.get('title', ''))}",
        }
        print(f"[ok] {sid}: {license_short} — {page.get('title','')[:70]}")
        return True

    except Exception as exc:
        print(f"[ERROR] {sid}: {exc}")
        return False


def main():
    only_ids = set(sys.argv[1:]) or None

    species_list = json.loads(SPECIES_PATH.read_text(encoding="utf-8"))
    IMAGES_DIR.mkdir(exist_ok=True)

    attributions = {}
    if ATTRIBUTIONS_PATH.exists():
        attributions = json.loads(ATTRIBUTIONS_PATH.read_text(encoding="utf-8"))

    failures = []
    processed = 0

    for sp in species_list:
        sid = sp["id"]
        if only_ids and sid not in only_ids:
            continue

        dest = IMAGES_DIR / f"{sid}.jpg"
        if only_ids and sid in only_ids and dest.exists():
            dest.unlink()

        if dest.exists():
            print(f"[skip] {sid} already downloaded")
            continue

        processed += 1
        ok = fetch_one(sp, attributions)
        if not ok:
            failures.append(sid)
        time.sleep(2)

    ATTRIBUTIONS_PATH.write_text(json.dumps(attributions, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDone. Processed {processed}, {len(failures)} failures.")
    if failures:
        print("Failed species:", ", ".join(failures))


if __name__ == "__main__":
    main()
