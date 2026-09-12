"""
Asset fetcher: pulls openly-licensed field-ID photos from Wikimedia Commons
for every species in data/species.json, across multiple categories per
species (leaf, flower, fruit/cone, bark, trunk, full tree), saves them to
images/<species-id>/<category>.jpg, and records attribution (author, license,
source URL) in data/attributions.json, nested as {species_id: {category: {...}}}.

Strategy: pull from each species' own Commons category first (curated by that
taxon's contributors, more reliable for species-accuracy than free-text
search), falling back to search with a strict species-epithet match. Filters
out non-photo or non-ID-useful images (herbarium/microscope prints, galls,
disease damage, illustrations) via a blacklist, and requires a category-
appropriate keyword (e.g. "bark" for the bark photo) so a distant tree shot
doesn't get mistaken for a bark close-up, etc. The "tree" (whole-tree habit)
category is the exception: it *wants* the wide/landscape shots the other
categories reject, so it uses a different keyword set.

Only accepts CC0, Public Domain, or CC-BY / CC-BY-SA licensed files.
Uses only the Python standard library (no pip installs required).

Usage:
  python scripts/fetch_images.py                        fetch every missing (species, category)
  python scripts/fetch_images.py --category bark         fetch only the "bark" category, all species
  python scripts/fetch_images.py red-maple sassafras      re-fetch ALL categories for these species ids
  python scripts/fetch_images.py --category bark red-maple  re-fetch just bark for red-maple
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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

BASE_BAD_KEYWORDS = [
    "gall", "epidermis", "print", "microscope", "stoma", "stomata",
    "disease", "scorch", "canker", "rust", "mite", "aphid", "insect damage",
    "map", "distribution", "illustration", "drawing", "engraving", "plate",
    "diagram", "herbarium",
]

# Per-category keyword rules. `good` = at least one required in the title.
# `bad` = extra disqualifying words on top of BASE_BAD_KEYWORDS.
# `wide_shots_ok` = don't exclude canopy/landscape/street/suburban framing
# (used only by "tree", which wants exactly that).
CATEGORY_CONFIG = {
    "leaf": {
        "query": {"broadleaf": "leaf", "conifer": "needles"},
        "good": ["leaf", "leaves", "foliage", "needles", "frond"],
        "bad": ["flower", "fruit", "seed", "cone", "bark", "trunk"],
        "wide_shots_ok": False,
    },
    "flower": {
        "query": {"broadleaf": "flower"},
        "good": ["flower", "flowers", "blossom", "bloom", "inflorescence", "catkin"],
        "bad": ["leaf", "leaves", "bark", "trunk", "fruit", "seed"],
        "wide_shots_ok": False,
        "skip_group": "conifer",
    },
    "fruit": {
        "query": {"broadleaf": "fruit", "conifer": "cone"},
        "good": {
            "broadleaf": ["fruit", "seed", "seeds", "samara", "acorn", "nut", "drupe", "pod", "capsule", "achene", "berry"],
            "conifer": ["cone", "cones"],
        },
        "bad": ["leaf", "leaves", "bark", "trunk", "flower"],
        "wide_shots_ok": False,
    },
    "bark": {
        "query": {"broadleaf": "bark", "conifer": "bark"},
        "good": ["bark"],
        "bad": ["leaf", "leaves", "needle", "needles", "foliage", "flower", "fruit"],
        "wide_shots_ok": False,
        "skip_group": "palm",  # palms have no true bark
    },
    "trunk": {
        "query": {"broadleaf": "trunk", "conifer": "trunk"},
        "good": ["trunk"],
        "bad": ["leaf", "leaves", "needle", "needles", "foliage", "flower", "fruit"],
        "wide_shots_ok": False,
    },
    "tree": {
        "query": {"broadleaf": "habit", "conifer": "habit"},
        "good": ["habit", "specimen", "whole tree", "mature tree", "tree form", "growth form"],
        "bad": ["leaf", "leaves", "needle", "needles", "foliage", "bark", "trunk", "flower", "fruit", "cone", "seed"],
        "wide_shots_ok": True,
    },
}

CATEGORY_ORDER = ["leaf", "flower", "fruit", "bark", "trunk", "tree"]

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


def search_candidates(query, limit=25):
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


def pick_best(pages, good_keywords, bad_keywords, require_good, require_terms=None, wide_shots_ok=False):
    full_bad = list(BASE_BAD_KEYWORDS) + list(bad_keywords)
    if not wide_shots_ok:
        full_bad += ["suburban", "street", "map", "range map"]

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
        title_lower = title.lower()
        cats_lower = meta.get("Categories", {}).get("value", "").lower()
        text = title_lower + " " + cats_lower

        if require_terms and not any(t in text for t in require_terms):
            continue

        if any(bad in text for bad in full_bad):
            continue

        has_good = any(g in title_lower for g in good_keywords)
        if require_good and not has_good:
            continue

        score = (10 if has_good else 0) + min(width, 2000) / 2000
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


def fetch_one(sp, category, attributions):
    sid = sp["id"]
    cfg = CATEGORY_CONFIG[category]

    if cfg.get("skip_group") == sp["group"]:
        return "skipped"

    dest_dir = IMAGES_DIR / sid
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{category}.jpg"

    scientific = sp["scientific"]
    genus, epithet = scientific.split(" ", 1)
    require_terms = [scientific.lower(), epithet.lower()]

    good = cfg["good"]
    if isinstance(good, dict):
        good = good.get(sp["group"], good.get("broadleaf", []))
    bad = cfg["bad"]
    wide_ok = cfg.get("wide_shots_ok", False)

    query_word = cfg["query"].get(sp["group"], cfg["query"].get("broadleaf"))
    query = f"{scientific} {query_word}"

    print(f"[{category}] {sid}: category lookup 'Category:{scientific}'")
    try:
        pages = category_candidates(scientific)
        choice = pick_best(pages, good, bad, require_good=True, wide_shots_ok=wide_ok)

        if not choice:
            print(f"  -> search fallback: '{query}'")
            pages = search_candidates(query)
            choice = pick_best(pages, good, bad, require_good=True, require_terms=require_terms, wide_shots_ok=wide_ok)

        if not choice:
            pages = search_candidates(scientific + " " + query_word, limit=25)
            choice = pick_best(pages, good, bad, require_good=False, require_terms=require_terms, wide_shots_ok=wide_ok)

        if not choice:
            # Broadest fallback: search the bare scientific name (no qualifier
            # word), which surfaces the same generic whole-tree/street-tree
            # photos other categories' blacklist rejects but "tree" wants.
            pages = search_candidates(scientific, limit=30)
            choice = pick_best(pages, good, bad, require_good=False, require_terms=require_terms, wide_shots_ok=wide_ok)

        if not choice:
            print(f"[FAIL] {sid}/{category}: no acceptable image found")
            return "fail"

        page, info, license_short = choice
        img_url = info["thumburl"] if "thumburl" in info else info["url"]
        download(img_url, dest)

        meta = info.get("extmetadata", {})
        attributions.setdefault(sid, {})[category] = {
            "title": page.get("title", ""),
            "author": strip_tags(meta.get("Artist", {}).get("value", "Unknown")),
            "license": license_short,
            "licenseUrl": meta.get("LicenseUrl", {}).get("value", ""),
            "sourcePage": f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(page.get('title', ''))}",
        }
        print(f"[ok] {sid}/{category}: {license_short} — {page.get('title','')[:70]}")
        return "ok"

    except Exception as exc:
        print(f"[ERROR] {sid}/{category}: {exc}")
        return "fail"


def main():
    args = sys.argv[1:]
    only_category = None
    if "--category" in args:
        idx = args.index("--category")
        only_category = args[idx + 1]
        args = args[:idx] + args[idx + 2:]
    only_ids = set(args) or None

    species_list = json.loads(SPECIES_PATH.read_text(encoding="utf-8"))
    IMAGES_DIR.mkdir(exist_ok=True)

    attributions = {}
    if ATTRIBUTIONS_PATH.exists():
        attributions = json.loads(ATTRIBUTIONS_PATH.read_text(encoding="utf-8"))

    categories = [only_category] if only_category else CATEGORY_ORDER
    results = {"ok": 0, "fail": 0, "skipped": 0}

    for sp in species_list:
        sid = sp["id"]
        if only_ids and sid not in only_ids:
            continue
        for category in categories:
            dest = IMAGES_DIR / sid / f"{category}.jpg"
            force = bool(only_ids)  # explicit species ids means "re-fetch these"
            if dest.exists() and not force:
                continue
            outcome = fetch_one(sp, category, attributions)
            results[outcome] = results.get(outcome, 0) + 1
            ATTRIBUTIONS_PATH.write_text(json.dumps(attributions, indent=2, ensure_ascii=False), encoding="utf-8")
            time.sleep(1.5)

    print(f"\nDone. ok={results['ok']} fail={results['fail']} skipped={results['skipped']}")


if __name__ == "__main__":
    main()
