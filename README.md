# Great Scott's Tree & Leaf ID

**🌳 Live site: [jyounggsts.github.io/tree-id-flashcards](https://jyounggsts.github.io/tree-id-flashcards/)**

A free, browser-based flashcard app for practicing tree and leaf identification —
built for botany and arborist study, and mobile-friendly. Organized by **region**:

- **Eastern US** (48 species) — broadleaf trees and conifers commonly taught in
  North American dendrology/forestry courses.
- **Southern California** (321 species) — trees, palms, and conifers found in
  SoCal urban/landscape settings, sourced from the scientific-name index of
  *A Californian's Guide to the Trees Among Us* by Matt Ritter. Species that
  appear in both regions (e.g. Red Maple, Sweetgum, Tulip Tree) are shared,
  not duplicated.

Three quiz modes: **multiple choice**, **fill in the blank**, and **flashcard**
(a no-pressure learning mode — see the photo, try to identify it yourself, then
reveal the answer and family/leaf details before moving on), quizzing on
common or scientific names.

Each card has a scrollable photo gallery — leaf, flower, fruit/cone, bark,
trunk, and full tree — so you can practice identifying a species the way you'd
size it up in the field, from multiple angles and features rather than a
single leaf shot.

**SoCal photos are a work in progress** — species data for all 321 species is
in place, but photo fetching/verification (the labor-intensive part) is
ongoing. Until a species has photos, its card shows a "photos coming soon"
placeholder instead of a broken image.

No build step, no dependencies, no backend — plain HTML/CSS/JS, deployable
straight to GitHub Pages.

## Running locally

Any static file server works, e.g.:

```bash
python -m http.server 8080
```

Then open `http://localhost:8080`.

## Data & images

- `data/species.json` — curated species list (common name, scientific name,
  family, leaf type, arrangement, region) used to generate questions and
  multiple-choice distractors. `region` is an array (`["eastern-us"]`,
  `["socal"]`, or both) so a species relevant to multiple regions appears in
  each without duplicating its entry or photos. The SoCal species were added
  in bulk by `scripts/build_socal.py` from the source list; to add another
  region, add a similar script.
- `data/attributions.json` — photo credit metadata (author, license, source
  link) for every image, nested as `{species_id: {category: {...}}}`, generated
  by `scripts/fetch_images.py`.
- `images/<species-id>/<category>.jpg` — one photo per category per species
  (`leaf`, `flower`, `fruit`, `bark`, `trunk`, `tree`), pulled from Wikimedia
  Commons under open licenses (CC0, Public Domain, CC-BY, or CC-BY-SA).
  Conifers have no `flower` category (they don't have true flowers), and
  chestnut-oak is missing its `flower` photo specifically (see the accuracy
  note below) — the gallery just skips whatever's missing. Full credits are
  viewable in-app via the "View photo credits" link, as required by the
  CC-BY / CC-BY-SA licenses.

To re-fetch or replace images, run:

```bash
python scripts/fetch_images.py                          # fetch every missing (species, category)
python scripts/fetch_images.py --category bark            # (re-)fetch only bark photos, all species
python scripts/fetch_images.py red-maple sassafras         # force re-fetch ALL categories for these species
python scripts/fetch_images.py --category bark red-maple   # force re-fetch just bark for red-maple
```

## Accuracy note

Every photo (276 of 277 possible species/category slots — see below) was
manually reviewed for identification accuracy. Automated fetching got a
meaningful fraction wrong on the first pass — wrong species (genus-only
keyword matches), disease/gall close-ups, herbarium/microscope prints,
mislabeled content (a cooking-with-sassafras photo, a nursery catalog page,
a bushcraft-knife photo), and category mismatches (a close-up used where a
whole-tree "habit" shot was needed) — all caught by visual inspection and
replaced with verified photos.

The one unfilled slot: **chestnut-oak has no flower photo.** Its catkins
aren't showy, and every candidate found on Commons was either the wrong
species (one turned out to be a Valley Oak, *Quercus lobata*, from an
unrelated encyclopedia page) or actually showed acorns instead of flowers.
Rather than show something wrong, that slide is simply omitted for this one
species.
