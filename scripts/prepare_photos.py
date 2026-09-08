#!/usr/bin/env python3
"""
Photography pipeline.

FOLDERS IN                              PAGES OUT
------------------------------------    ---------------------------------
photos-source/Tadpoles/*.jpg            tadpoles.qmd    (one grid)
photos-source/Wildlife/Reptiles/*.jpg   wildlife.qmd    (one section each)
photos-source/Wildlife/Amphibians/
photos-source/Wildlife/Birds/
photos-source/Wildlife/Mammals/
photos-source/Wildlife/Other/

Two things happen when you run it:

1. IMPORT. Anything new in photos-source/ is resized into photography/ (an
   1800px version for the lightbox and a 700px thumbnail), with GPS
   coordinates and camera serial numbers stripped out. Filenames keep their
   original spelling.

2. REBUILD. The grids, captions files, banners and search-engine metadata are
   regenerated from whatever is currently in photography/.

Run it after adding photos, or after editing a captions.csv. Existing resized
files are never redone unless you pass --force.

    python3 scripts/prepare_photos.py

To add a new wildlife section, make a folder for it under
photos-source/Wildlife/ and add its name to SECTIONS below. Empty sections are
skipped, so Birds stays invisible until there is a bird in it.
"""

import csv
import json
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ModuleNotFoundError:                      # noqa: E722
    raise SystemExit(
        "\nThis script needs Pillow, and the python3 you just used doesn't have it.\n"
        "On this Mac, Pillow lives in Homebrew's python. Run it with the full path:\n\n"
        "    /opt/homebrew/bin/python3 " + " ".join(sys.argv) + "\n\n"
        "RStudio's Terminal tab uses a different PATH from your normal Terminal,\n"
        "which is why plain `python3` works in one and not the other.\n")

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "photos-source"
OUT = ROOT / "photography"

# The order sections appear on the Wildlife page. Anything found on disk but
# not listed here is appended at the end.
SECTIONS = ["Reptiles", "Amphibians", "Birds", "Mammals", "Other"]

# Sections whose files you name by common name ("Palm_tanager_1_...") rather
# than by binomial. Their captions go in the common_name column and are set in
# roman type; everything else is read as a scientific name and italicised.
COMMON_NAME_SECTIONS = {"birds", "mammals"}

FULL_MAX, THUMB_MAX, QUALITY = 1800, 1000, 82

# Burned across the middle of every full-size image. The thumbnails in the
# grid are left clean; the large version people can right-click and save is
# the one that carries your name. Set to "" to turn watermarking off.
WATERMARK = "\u00a9 Jackson R Phillips 2026"
WATERMARK_OPACITY = 64          # 0 invisible, 255 solid. 64 is a light wash.

# The first of these that exists on the machine is used for the watermark.
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "/Library/Fonts/Georgia.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
BANNER_COUNT = 8          # photos rotating in a page's banner

# The tadpole page uses one still image at the top instead of a rotating
# banner. Name the file here; it is taken out of the grid so it doesn't appear
# twice, and the cover copy is made from your original, so it carries no
# watermark.
TADPOLE_COVER = "Cover_collage_AW.jpg"
EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".gif"}

# Transparent PNGs get flattened onto this colour. Black, because the site is
# dark and most of these photos are already shot against black. If you switch
# to the light theme, change this to (255, 255, 255) and re-run with --force.
FLATTEN_TO = (0, 0, 0)

# Named as the photographer in the structured data that search engines read.
CREATOR = "Jackson Phillips"

FORCE = "--force" in sys.argv

# Words that look like species epithets but aren't, so the caption guesser
# doesn't turn "Ascaphus_tadpole" into a binomial. Add your own as needed.
NOT_A_NAME = {
    "cover", "collage", "tadpole", "tadpoles", "adult", "adults", "juvenile",
    "female", "male", "topdown", "lilypad", "green", "enhanced", "edited",
    "landscape", "yellow", "img", "med", "res", "portrait", "closeup",
    # views and orientations, which turn up in specimen filenames
    "side", "ventral", "dorsal", "lateral", "oral", "live", "tad", "sp",
    "spp", "larva", "larvae", "specimen",
    "zoom", "detail", "macro", "mouthparts", "mouth", "oral", "disc",
}


def site_url():
    """Absolute URLs for the search-engine metadata, taken from _quarto.yml."""
    m = re.search(r'^\s*site-url:\s*"?([^"\n#]+)"?',
                  (ROOT / "_quarto.yml").read_text(encoding="utf-8"), re.M)
    return m.group(1).strip().rstrip("/") if m else ""


def slugify(name):
    """Folder names become URL slugs: 'Reptiles' -> 'reptiles'."""
    return re.sub(r"-+", "-", "".join(c.lower() if c.isalnum() else "-" for c in name)).strip("-")


def safe_name(stem):
    """Filenames keep their spelling and capitalisation, with only characters
    that would break a URL replaced. Your species names are the filenames, and
    they are worth preserving exactly."""
    return re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9._-]", "_", stem)).strip("._-")


def guess_caption(stem):
    """Best-effort species name from a filename. Fix wrong guesses in captions.csv."""
    parts = [p for p in re.split(r"[_\-\s]+", stem) if p]
    if not parts:
        return "", ""
    g = parts[0]
    if not (g[:1].isupper() and g.isalpha() and len(g) >= 4 and g.lower() not in NOT_A_NAME):
        return "", ""
    if (len(parts) >= 3 and parts[1].lower().rstrip(".") in ("cf", "aff")
            and parts[2].islower() and parts[2].isalpha()):
        # open nomenclature: Adhaerobufo_cf_nasicus -> Adhaerobufo cf. nasicus
        name, rest = f"{g} {parts[1].rstrip('.')}. {parts[2]}", parts[3:]
    elif (len(parts) >= 2 and parts[1].islower() and parts[1].isalpha()
            and len(parts[1]) >= 3 and parts[1] not in NOT_A_NAME):
        name, rest = f"{g} {parts[1]}", parts[2:]
    else:
        name, rest = g, parts[1:]
    where = " ".join(p for p in rest if not p.isdigit() or len(p) == 4)
    where = " ".join(w for w in where.split() if w.lower() not in NOT_A_NAME)
    return name, where.strip()


def guess_common(stem):
    """For files named by common name. Everything up to the first bare number
    is the animal; the rest is where it was taken."""
    parts = [x for x in re.split(r"[_\-\s]+", stem) if x]
    name, rest = [], []
    for i, part in enumerate(parts):
        if part.isdigit() and len(part) < 4:
            rest = parts[i + 1:]
            break
        name.append(part)
    else:
        rest = []
    common = " ".join(name).replace("_", " ").strip()
    where = " ".join(x for x in rest if not (x.isdigit() and len(x) < 4))
    return common[:1].upper() + common[1:], where.strip()


def resize(src, dst, max_edge):
    # Skip work already done, but redo it when the original is newer than the
    # copy. That is what makes "rotate the photo, save, re-run" just work: the
    # rotated file has a fresh timestamp, so only that one photograph is
    # rebuilt and everything else is left alone.
    if dst.exists() and not FORCE and dst.stat().st_mtime >= src.stat().st_mtime:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            im = im.convert("RGBA")
            flat = Image.new("RGB", im.size, FLATTEN_TO)
            flat.paste(im, mask=im.split()[-1])
            im = flat
        else:
            im = im.convert("RGB")
        im.thumbnail((max_edge, max_edge), Image.LANCZOS)
        if max_edge == FULL_MAX:
            im = add_watermark(im)
        # No exif= argument, so GPS coordinates and camera serials are dropped.
        im.save(dst, "JPEG", quality=QUALITY, optimize=True, progressive=True)


def watermark_font(size):
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    try:                                   # Pillow 10+ can scale its built-in
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def add_watermark(im):
    """One line of semi-transparent text across the middle of the image."""
    if not WATERMARK:
        return im
    im = im.convert("RGB")
    layer = Image.new("RGBA", im.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(layer)
    font = watermark_font(max(14, im.width // 26))
    box = draw.textbbox((0, 0), WATERMARK, font=font)
    x = (im.width - (box[2] - box[0])) // 2 - box[0]
    y = (im.height - (box[3] - box[1])) // 2 - box[1]
    # A darker copy underneath keeps it legible over pale images too.
    draw.text((x + 2, y + 2), WATERMARK, font=font,
              fill=(0, 0, 0, max(0, WATERMARK_OPACITY - 24)))
    draw.text((x, y), WATERMARK, font=font,
              fill=(255, 255, 255, WATERMARK_OPACITY))
    return Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")


def import_folder(src_dir, out_dir):
    """Resize every image in one source folder into one output folder."""
    if not src_dir.is_dir():
        return 0
    n = 0
    for src in sorted(p for p in src_dir.iterdir() if p.suffix.lower() in EXTS):
        stem = safe_name(src.stem)
        resize(src, out_dir / f"{stem}.jpg", FULL_MAX)
        resize(src, out_dir / "thumbs" / f"{stem}.jpg", THUMB_MAX)
        n += 1
    return n


def do_import():
    if not SOURCE.exists():
        return
    n = import_folder(SOURCE / "Tadpoles", OUT / "tadpoles")
    if n:
        print(f"  imported Tadpoles ({n})")
    wild = SOURCE / "Wildlife"
    if wild.is_dir():
        for folder in sorted(p for p in wild.iterdir()
                             if p.is_dir() and not p.name.startswith((".", "_"))):
            n = import_folder(folder, OUT / "wildlife" / slugify(folder.name))
            if n:
                print(f"  imported Wildlife/{folder.name} ({n})")


def all_captions():
    """Every caption anywhere on the site, so a photograph moved from one
    section to another keeps the caption you wrote for it."""
    found = {}
    for path in OUT.rglob("captions.csv"):
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("common_name") or r.get("species") or r.get("location"):
                    found[r["file"]] = (r.get("common_name", ""),
                                        r.get("species", ""), r.get("location", ""))
    return found


def prune(out_dir, src_dir):
    """Delete generated copies whose source photograph is gone, which is what
    happens when you move a file to a different section in Finder.

    Guarded: if the source folder is missing entirely (a fresh clone with no
    originals on the machine) nothing is deleted."""
    if not src_dir.is_dir() or not out_dir.is_dir():
        return []
    keep = {safe_name(p.stem) + ".jpg"
            for p in src_dir.iterdir() if p.suffix.lower() in EXTS}
    removed = []
    for photo in sorted(out_dir.glob("*.jpg")):
        if photo.name not in keep:
            photo.unlink()
            thumb = out_dir / "thumbs" / photo.name
            if thumb.exists():
                thumb.unlink()
            removed.append(photo.name)
    return removed


def do_prune():
    gone = []
    gone += [("tadpoles", n) for n in prune(OUT / "tadpoles", SOURCE / "Tadpoles")]
    wild = SOURCE / "Wildlife"
    if wild.is_dir():
        for folder in sorted(p for p in wild.iterdir()
                             if p.is_dir() and not p.name.startswith((".", "_"))):
            slug = slugify(folder.name)
            gone += [(slug, n) for n in prune(OUT / "wildlife" / slug, folder)]
    for where, name in gone:
        print(f"  removed from {where}: {name}")
    return gone


def load_captions(folder, fallback=None, by_common=False):
    """captions.csv is the source of truth. Missing rows get a caption carried
    over from elsewhere on the site, or a guess. Rows you have written are
    never overwritten."""
    path = folder / "captions.csv"
    rows = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows[r["file"]] = (r.get("common_name", ""),
                                   r.get("species", ""), r.get("location", ""))
    here = {p.name for p in folder.glob("*.jpg")}
    changed = False
    for stale in [k for k in rows if k not in here]:
        del rows[stale]                       # photo moved or was deleted
        changed = True
    for photo in sorted(folder.glob("*.jpg")):
        if photo.name not in rows:
            carried = (fallback or {}).get(photo.name)
            if carried:
                rows[photo.name] = carried
            elif by_common:
                common, where = guess_common(photo.stem)
                rows[photo.name] = (common, "", where)
            else:
                sci, where = guess_caption(photo.stem)
                rows[photo.name] = ("", sci, where)
            changed = True
    if changed or not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["file", "common_name", "species", "location"])
            for name in sorted(rows):
                w.writerow([name] + list(rows[name]))
    return rows


REF_COLS = ["file", "specimen_id", "common_name", "scientific_name", "genus",
            "family", "order", "class", "location", "source"]

# A catalogue number in a filename: "A139879", or an institution code in front
# of it as in "MCZ_A139946". Recognised so the ID fills itself in and doesn't
# end up in the locality field.
CATALOGUE = re.compile(r"^[A-Z]{1,2}\d{4,8}$")
INSTITUTION = re.compile(r"^[A-Z]{2,6}$")


def guess_specimen(stem):
    """Pull a museum catalogue number out of a filename, and say which tokens
    it used so they can be kept out of the locality."""
    parts = [x for x in re.split(r"[_\-\s]+", stem) if x]
    for i, part in enumerate(parts):
        if CATALOGUE.match(part):
            if i and INSTITUTION.match(parts[i - 1]):
                return f"{parts[i - 1]} {part}", {parts[i - 1], part}
            return part, {part}
    return "", set()


def load_reference(folder):
    """The tadpole library's spreadsheet: one row per photograph. Rows you have
    written are never touched; new photographs get a blank row added for you."""
    path = folder / "reference.csv"
    rows = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows[r["file"]] = {c: (r.get(c) or "").strip() for c in REF_COLS}
    # Taxonomy already known for a name, so that renaming a file, or adding
    # another photograph of a species you have already classified, doesn't make
    # you type it twice. Built before any pruning, so a rename carries over.
    known = {}
    for r in rows.values():
        for key in (r["scientific_name"].lower(), r["genus"].lower()):
            if key and r["family"] and key not in known:
                known[key] = r

    here = [p.name for p in sorted(folder.glob("*.jpg")) if p.name != TADPOLE_COVER]
    changed = False
    for name in here:
        if name not in rows:
            stem = Path(name).stem
            sci, where = guess_caption(stem)
            spec, used = guess_specimen(stem)
            where = " ".join(w for w in where.split() if w not in used)
            genus = sci.split(" ")[0] if sci else ""
            blank = dict.fromkeys(REF_COLS, "")
            blank.update(file=name, specimen_id=spec, scientific_name=sci,
                         genus=genus, location=where)
            match = known.get(sci.lower()) or known.get(genus.lower())
            if match:
                for col in ("common_name", "family", "order", "class"):
                    blank[col] = match[col]
                blank["source"] = match["source"] or "carried over"
            rows[name] = blank
            changed = True
    for stale in [k for k in rows if k not in here]:
        del rows[stale]
        changed = True
    if changed or not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, REF_COLS)
            w.writeheader()
            for name in here:
                w.writerow(rows[name])
    return rows


def make_cover(folder):
    """A clean, unwatermarked copy of the cover image, built from the original."""
    dst = ROOT / "assets" / "tadpole-cover.jpg"
    for src in (SOURCE / "Tadpoles").glob("*"):
        if src.suffix.lower() in EXTS and safe_name(src.stem) + ".jpg" == TADPOLE_COVER:
            if not dst.exists() or FORCE:
                global WATERMARK
                keep, WATERMARK = WATERMARK, ""      # cover is never watermarked
                resize(src, dst, 1800)
                WATERMARK = keep
            return "assets/tadpole-cover.jpg"
    # No original to hand (fresh clone): fall back to the clean thumbnail.
    thumb = folder / "thumbs" / TADPOLE_COVER
    return f"photography/tadpoles/thumbs/{TADPOLE_COVER}" if thumb.exists() else ""


def italicise(name):
    """Italicise the name, but not the open-nomenclature qualifiers. Convention
    is *Otophryne* sp. and *Adhaerobufo* cf. *nasicus*, with the qualifier
    upright and the names around it in italics."""
    parts = name.split()
    for i, part in enumerate(parts):
        if 0 < i < len(parts) - 1 and part.lower().rstrip(".") in ("cf", "aff"):
            head = " ".join(parts[:i])
            tail = " ".join(parts[i + 1:])
            mark = part if part.endswith(".") else part + "."
            return f"<em>{head}</em> {mark} <em>{tail}</em>"
    tail = []
    while parts and parts[-1].lower().rstrip(".") in ("sp", "spp", "cf", "aff", "indet"):
        tail.insert(0, parts.pop())
    out = f"<em>{' '.join(parts)}</em>" if parts else ""
    if tail:
        out += " " + " ".join(t if t.endswith(".") else t + "." for t in tail)
    return out


def tadpole_library(folder):
    """The searchable, family-grouped grid. Returns (html, images, families)."""
    ref = load_reference(folder)
    base = site_url()
    by_family, images = {}, []

    for name, r in sorted(ref.items(), key=lambda kv: (kv[1]["family"], kv[0])):
        if not (folder / name).exists():
            continue
        sci, common = r["scientific_name"], r["common_name"]
        alt = ", ".join(x for x in (sci or common, r["location"]) if x) or "Tadpole"
        haystack = " ".join(x for x in
                            (common, sci, r["genus"], r["family"], r["order"],
                             r["class"], r["location"], r["specimen_id"],
                             Path(name).stem) if x).lower()
        under = " · ".join(x for x in (common, r["location"]) if x)
        if r["specimen_id"]:
            under += (" · " if under else "") + \
                     f'<span class="cat">{r["specimen_id"]}</span>' 
        label = (italicise(sci) if sci else "") + \
                (f'<span class="where">{under}</span>' if under else "")
        tile = (
            f'<figure data-search="{haystack}">'
            f'<a href="photography/tadpoles/{name}" class="lightbox" data-gallery="tadpoles">'
            f'<img src="photography/tadpoles/thumbs/{name}" '
            f'srcset="photography/tadpoles/thumbs/{name} {THUMB_MAX}w, '
            f'photography/tadpoles/{name} {FULL_MAX}w" '
            f'sizes="(max-width: 700px) 100vw, 340px" loading="lazy" alt="{alt}">'
            f"</a><figcaption>{label}</figcaption></figure>"
        )
        by_family.setdefault(r["family"] or "Not yet identified", []).append(tile)
        images.append({
            "@type": "ImageObject",
            "contentUrl": f"{base}/photography/tadpoles/{name}" if base else name,
            "name": alt,
            "creator": {"@type": "Person", "name": CREATOR},
            "copyrightNotice": f"\u00a9 {CREATOR}",
            "creditText": CREATOR,
            "license": f"{base}/license.html" if base else "license.html",
            "acquireLicensePage": f"{base}/license.html" if base else "license.html",
        })

    families = sorted(k for k in by_family if k != "Not yet identified")
    if "Not yet identified" in by_family:
        families.append("Not yet identified")

    total = sum(len(v) for v in by_family.values())
    jump = "".join(f'<a href="#fam-{slugify(f)}">{f}</a>' for f in families)
    parts = [
        '<div class="tad-search">'
        '<input type="search" id="tad-q" autocomplete="off" spellcheck="false" '
        'placeholder="Search species, genus, family, order or place">'
        f'<span class="tad-count" id="tad-count">{total} photographs</span></div>',
        f'<nav class="section-nav fam-nav">{jump}</nav>',
    ]
    for fam in families:
        parts.append(
            f'<section class="photo-section fam" id="fam-{slugify(fam)}" data-family="{fam.lower()}">'
            f'<h2>{fam} <span class="n">{len(by_family[fam])}</span></h2>'
            f'<div class="photo-grid">' + "\n".join(by_family[fam]) + "</div></section>")

    parts.append('<p class="tad-empty" id="tad-empty" hidden>Nothing matches that. '
                 '<button type="button" id="tad-clear">Clear the search</button></p>')
    parts.append("""<script>
(function () {
  var q = document.getElementById("tad-q");
  if (!q) return;
  var figs = document.querySelectorAll(".fam figure");
  var count = document.getElementById("tad-count");
  var empty = document.getElementById("tad-empty");
  function run() {
    var term = q.value.trim().toLowerCase();
    var shown = 0;
    figs.forEach(function (f) {
      var hit = !term || f.dataset.search.indexOf(term) !== -1;
      f.hidden = !hit;
      if (hit) shown++;
    });
    document.querySelectorAll(".fam").forEach(function (sec) {
      var n = sec.querySelectorAll("figure:not([hidden])").length;
      sec.hidden = n === 0;
      var tag = sec.querySelector("h2 .n");
      if (tag) tag.textContent = n;
      var link = document.querySelector('.fam-nav a[href="#' + sec.id + '"]');
      if (link) link.hidden = n === 0;
    });
    count.textContent = shown + (shown === 1 ? " photograph" : " photographs")
                      + (term ? " matching \u201c" + q.value.trim() + "\u201d" : "");
    empty.hidden = shown !== 0;
  }
  q.addEventListener("input", run);
  document.getElementById("tad-clear").addEventListener("click", function () {
    q.value = ""; run(); q.focus();
  });
})();
</script>""")
    return "\n".join(parts), images, families


def tiles_for(folder, web_prefix, gallery, carried=None):
    """One <figure> per photo, plus the structured-data records for them."""
    caps = load_captions(folder, carried,
                         by_common=gallery in COMMON_NAME_SECTIONS)
    base = site_url()
    tiles, indexed, species = [], [], []
    for p in sorted(folder.glob("*.jpg")):
        common, sci, where = caps.get(p.name, ("", "", ""))
        # Alt text is what image search reads first, so make it descriptive
        # rather than a filename.
        alt = ", ".join(x for x in (sci or common, where) if x) or gallery.title()
        # A scientific name is italicised. A common name is not.
        label = italicise(sci) if sci else (common or "")
        under = " \u00b7 ".join(x for x in ((common if sci else ""), where) if x)
        if under:
            label += f'<span class="where">{under}</span>'
        tiles.append(
            f'<figure><a href="{web_prefix}/{p.name}" class="lightbox" data-gallery="{gallery}">'
            f'<img src="{web_prefix}/thumbs/{p.name}" '
            f'srcset="{web_prefix}/thumbs/{p.name} {THUMB_MAX}w, {web_prefix}/{p.name} {FULL_MAX}w" '
            f'sizes="(max-width: 700px) 100vw, 340px" '
            f'loading="lazy" alt="{alt}">'
            f"</a><figcaption>{label}</figcaption></figure>"
        )
        indexed.append({
            "@type": "ImageObject",
            "contentUrl": f"{base}/{web_prefix}/{p.name}" if base else f"{web_prefix}/{p.name}",
            "thumbnailUrl": f"{base}/{web_prefix}/thumbs/{p.name}" if base else f"{web_prefix}/thumbs/{p.name}",
            "name": alt,
            "creator": {"@type": "Person", "name": CREATOR},
            "copyrightNotice": f"© {CREATOR}",
            "creditText": CREATOR,
            "license": f"{base}/license.html" if base else "license.html",
            "acquireLicensePage": f"{base}/license.html" if base else "license.html",
        })
        keep = sci or common
        if keep and keep not in species:
            species.append(keep)
    return tiles, indexed, species


def ld_block(title, images):
    return ('<script type="application/ld+json">\n'
            + json.dumps({"@context": "https://schema.org", "@type": "ImageGallery",
                          "name": title,
                          "author": {"@type": "Person", "name": CREATOR},
                          "image": images}, indent=1)
            + "\n</script>")


def banner_block(paths, element_id):
    slides = "\n".join(
        f'<img src="{src}" alt="" class="{"active" if n == 0 else ""}"'
        f' loading="{"eager" if n == 0 else "lazy"}">'
        for n, src in enumerate(paths[:BANNER_COUNT])
    )
    return (f'<div class="banner" id="{element_id}">\n{slides}\n</div>\n'
            "<script>\n(function () {\n"
            f'  var s = document.querySelectorAll("#{element_id} img"), i = 0;\n'
            "  if (s.length < 2) return;\n"
            "  setInterval(function () {\n"
            '    s[i].classList.remove("active");\n'
            "    i = (i + 1) % s.length;\n"
            '    s[i].classList.add("active");\n'
            "  }, 5000);\n})();\n</script>")


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    carried = all_captions()          # read before anything is rewritten
    total = 0

    # ---- Tadpole specimen library ------------------------------------------
    tad = OUT / "tadpoles"
    if tad.is_dir() and any(tad.glob("*.jpg")):
        cover = make_cover(tad)
        (OUT / "_tadpoles-cover.qmd").write_text(
            "```{=html}\n"
            f'<div class="still-cover"><img src="{cover}" alt="A plate of anuran '
            'larvae from the reference collection"></div>\n```\n', encoding="utf-8")
        html, images, families = tadpole_library(tad)
        (OUT / "_tadpoles.qmd").write_text(
            "```{=html}\n" + html + "\n"
            + ld_block("Tadpole specimen library", images) + "\n```\n",
            encoding="utf-8")
        print(f"  Tadpoles: {len(images)} photos in {len(families)} group(s)")
        total += len(images)

    # ---- Wildlife: one section per subfolder --------------------------------
    wild = OUT / "wildlife"
    parts, all_images, all_species, all_covers, nav = [], [], [], [], []
    if wild.is_dir():
        found = {p.name: p for p in wild.iterdir() if p.is_dir()}
        ordered = [slugify(s) for s in SECTIONS if slugify(s) in found]
        ordered += [k for k in sorted(found) if k not in ordered]
        for slug in ordered:
            folder = found[slug]
            photos = sorted(folder.glob("*.jpg"))
            if not photos:
                continue                      # empty sections stay invisible
            title = next((s for s in SECTIONS if slugify(s) == slug), slug.title())
            tiles, images, species = tiles_for(
                folder, f"photography/wildlife/{slug}", slug, carried)
            nav.append(f'<a href="#{slug}">{title}</a>')
            parts.append(
                f'<section class="photo-section" id="{slug}">\n'
                f'<h2>{title} <span class="n">{len(tiles)}</span></h2>\n'
                f'<div class="photo-grid">\n' + "\n".join(tiles) + "\n</div>\n</section>")
            all_images += images
            all_species += [s for s in species if s not in all_species]
            all_covers += [f"photography/wildlife/{slug}/thumbs/{p.name}" for p in photos[:2]]
            print(f"  Wildlife / {title}: {len(tiles)} photos")
            total += len(tiles)
    if parts:
        (OUT / "_wildlife-banner.qmd").write_text(
            "```{=html}\n" + banner_block(all_covers, "wildlife-banner") + "\n```\n",
            encoding="utf-8")
        (OUT / "_wildlife.qmd").write_text(
            "```{=html}\n"
            + '<nav class="section-nav">' + "".join(nav) + "</nav>\n"
            + "\n".join(parts) + "\n"
            + ld_block("Wildlife photography", all_images) + "\n```\n",
            encoding="utf-8")
        (OUT / "_wildlife-meta.txt").write_text(
            "Wildlife photographs of " + ", ".join(all_species[:8])
            + (" and others" if len(all_species) > 8 else "") + ".", encoding="utf-8")

    print(f"\n{total} photographs. Run: quarto preview")


if __name__ == "__main__":
    do_import()
    do_prune()
    build()
