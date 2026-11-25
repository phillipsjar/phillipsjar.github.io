#!/usr/bin/env python3
"""Turn a folder of STLs segmented from one CT scan (skull, jaws, organs...)
into web models for the 3D anatomy viewer (assets/js/anatomy-viewer.js).

    pip install trimesh fast-simplification
    python scripts/make_anatomy_model.py path/to/scan-folder assets/models/scan-name

Point it at a folder holding one STL per structure, all exported from the
same segmentation, so they share coordinates and line up. Into the output
folder it writes:

  one .bin per structure  the same compact format as make_web_model.py
  organs.csv              one row per structure, which sets how it appears:
                            file     the .bin file (leave this alone)
                            label    its name in the menu
                            system   the heading it's grouped under
                            color    a hex colour, e.g. #ddd3bd
                            opacity  starting opacity, 0 to 100
                            show     yes or no: switched on at the start?
                          Rows appear in the menu in the order they're in
                          here, and systems in the order they first appear.

organs.csv is yours to edit (Excel, Numbers or a text editor). The viewer
reads it directly, so a new label or colour shows up as soon as the page
reloads, without running this script again. Run the script again only when
the STLs change or you add more: it keeps every edit you made to existing
rows and adds a row for each new structure.

Names: the start of the file name shared by every STL (for example
"Natalobatrachus_bonebergi_tadpole_JRP_058_") and a trailing "_simplified"
are dropped, so ..._JRP_058_upper_jaws_simplified.stl becomes upper-jaws.bin,
labelled "Upper jaws". The first guess at a system and colour comes from
words in the name (lung goes under Respiratory, brain under Nervous system
and senses, and so on), and it's only a guess: fix it in organs.csv.

Size: the scan shares a budget of 200,000 triangles (change it with
--budget 300000), split by surface area, with at least 5,000 for each
structure so small ones (nerves, the inner ear) keep their shape, and at most
120,000 for any one. That comes to about 9 bytes per triangle, so roughly
2 MB for a whole scan.
"""
import argparse
import csv
import os
import re
import struct
import sys
from pathlib import Path

import numpy as np
import trimesh
import fast_simplification

BUDGET = 200_000
FLOOR = 5_000
# Most triangles for any one structure. Above about 130,000 a mesh has more
# than 65,536 corners, the file has to store bigger numbers, and it grows by
# half for little visible gain.
CAP = 120_000
COLUMNS = ["file", "label", "system", "color", "opacity", "show",
           "triangles", "source_stl"]

# First guess at the system, from words in the structure's name. The first
# pattern that matches wins (so "ceratohyal body" is Skeleton, not Body).
SYSTEM_GUESSES = [
    (r"jaw|keratodont|beak|tooth|teeth|oral.?disc|labial", "Mouthparts"),
    (r"lung|trachea|glottis|larynx|gill", "Respiratory"),
    (r"chondrocran|cranium|skull|cartilage|bone|hyobranch|hyoid|meckel"
     r"|palatoquadrate|ceratohyal|rostral|vertebra|notochord|skeleton",
     "Skeleton"),
    (r"muscle|^m ", "Muscles"),
    (r"brain|nerve|spinal|ganglion|\beyes?\b|\blens\b|retina|\botic\b"
     r"|\bears?\b|labyrinth|olfactory|nasal", "Nervous system and senses"),
    (r"heart|aorta|arter|vein|vessel|ventricle|atrium|conus", "Circulatory"),
    (r"\bgut\b|intestin|stomach|liver|pancrea|esophag|oesophag|buccal|pharyn"
     r"|manicotto|gall|cloaca", "Digestive"),
    (r"kidney|gonad|nephr|bladder", "Urogenital"),
    (r"\bskin\b|\bbody\b|outline|\bsurface\b", "Body"),
]
# Order of the systems in a new organs.csv (anything else goes last).
SYSTEM_ORDER = ["Body", "Skeleton", "Mouthparts", "Muscles",
                "Nervous system and senses", "Respiratory", "Circulatory",
                "Digestive", "Urogenital", "Other"]
CARTILAGE = "#ddd3bd"  # the colour of the skulls in model-viewer.js
PALETTE = ["#e3a34f", "#d9776a", "#7fb0d6", "#93c47d", "#c792c9",
           "#e6cf6a", "#6fc2b6", "#b9a3e3", "#e08fb0", "#a8b86b"]


def structure_names(stls):
    """File stem -> structure name, minus the shared prefix and _simplified."""
    stems = [re.sub(r"[_\- ]simplified$", "", p.stem, flags=re.I) for p in stls]
    prefix = ""
    if len(stems) > 1:
        prefix = os.path.commonprefix(stems)
        cut = max(prefix.rfind(c) for c in "_- ")
        prefix = prefix[:cut + 1] if cut >= 0 else ""
    return [s[len(prefix):] or s for s in stems]


def slug_of(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "part"


def label_of(name):
    words = re.sub(r"[_\-]+", " ", name).strip()
    return words[:1].upper() + words[1:]


def guess_system(name):
    words = re.sub(r"[_\-]+", " ", name.lower())
    for pattern, system in SYSTEM_GUESSES:
        if re.search(pattern, words):
            return system
    return "Other"


def triangle_targets(areas, counts, budget, floor):
    """Split the budget by surface area, at least `floor` each, never more
    triangles than a structure already has."""
    areas = np.asarray(areas, float)
    counts = np.minimum(np.asarray(counts, float), CAP)
    target = np.minimum(counts, floor)
    for _ in range(20):
        room = counts - target
        left = budget - target.sum()
        if left <= 1 or not (room > 0.5).any():
            break
        share = np.where(room > 0.5, areas, 0.0)
        target = np.minimum(counts, target + share / share.sum() * left)
    return target.astype(int)


def write_tmsh(mesh, dst):
    """Same file layout as make_web_model.py (see its notes)."""
    v = mesh.vertices.astype(np.float64)
    f = mesh.faces.astype(np.int64)
    lo, hi = v.min(0), v.max(0)
    span = np.where(hi - lo > 0, hi - lo, 1)
    q = np.round((v - lo) / span * 65535).astype("<u2")
    idx = f.reshape(-1)
    with open(dst, "wb") as out:
        out.write(b"TMSH")
        out.write(struct.pack("<III", 1, len(v), len(idx)))
        out.write(struct.pack("<6f", *lo, *hi))
        out.write(q.tobytes())
        out.write(idx.astype("<u2" if len(v) < 65536 else "<u4").tobytes())


def read_sheet(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = []
        for row in csv.DictReader(fh):
            row = {(k or "").strip().lower(): (v or "").strip()
                   for k, v in row.items()}
            if row.get("file"):
                rows.append(row)
        return rows


def main():
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run with no arguments to see the full notes.")
    ap.add_argument("scan_folder", help="folder of STLs from one scan")
    ap.add_argument("out_folder", help="e.g. assets/models/scan-name")
    ap.add_argument("--budget", type=int, default=BUDGET,
                    help=f"triangles for the whole scan (default {BUDGET:,})")
    if len(sys.argv) == 1:
        sys.exit(__doc__)
    args = ap.parse_args()

    src, out = Path(args.scan_folder), Path(args.out_folder)
    stls = sorted(p for p in src.iterdir() if p.suffix.lower() == ".stl")
    if not stls:
        sys.exit(f"No .stl files in {src}")
    out.mkdir(parents=True, exist_ok=True)

    names = structure_names(stls)
    slugs, seen = [], set()
    for name in names:
        s, n = slug_of(name), 2
        while s in seen:
            s, n = f"{slug_of(name)}-{n}", n + 1
        seen.add(s)
        slugs.append(s)

    print(f"Reading {len(stls)} STLs from {src} ...")
    meshes = [trimesh.load(p, force="mesh") for p in stls]
    targets = triangle_targets([m.area for m in meshes],
                               [len(m.faces) for m in meshes],
                               args.budget, FLOOR)

    # All parts of one scan must share coordinates. Warn if one sits far
    # outside the others, which usually means it was moved or exported from
    # a different scan.
    lo = np.min([m.bounds[0] for m in meshes], axis=0)
    hi = np.max([m.bounds[1] for m in meshes], axis=0)
    reach = np.linalg.norm(hi - lo)
    for p, m in zip(stls, meshes):
        others = [o for o in meshes if o is not m]
        if others:
            olo = np.min([o.bounds[0] for o in others], axis=0)
            ohi = np.max([o.bounds[1] for o in others], axis=0)
            gap = np.maximum(0, np.maximum(olo - m.bounds[1], m.bounds[0] - ohi))
            if np.linalg.norm(gap) > 0.25 * reach:
                print(f"  ? {p.name} sits well apart from the rest. Check it "
                      f"came from the same scan and wasn't moved.")

    total_bytes = 0
    built = []
    for p, mesh, slug, target in zip(stls, meshes, slugs, targets):
        faces = len(mesh.faces)
        if faces > target * 1.02:
            v, f = fast_simplification.simplify(
                mesh.vertices.astype(np.float32), mesh.faces.astype(np.int32),
                target_reduction=1 - target / faces)
            mesh = trimesh.Trimesh(v, f, process=True)
        dst = out / f"{slug}.bin"
        write_tmsh(mesh, dst)
        size = dst.stat().st_size
        total_bytes += size
        built.append((p, slug, len(mesh.faces)))
        print(f"  {dst.name:<28} {len(mesh.faces):>8,} triangles  "
              f"{size / 1024:>7,.0f} KB   (from {faces:,})")

    # organs.csv: keep what's there, refresh the numbers, add new parts.
    sheet = out / "organs.csv"
    rows = read_sheet(sheet)
    by_file = {r["file"]: r for r in rows}
    new_rows = []
    used = {r.get("color", "").lower() for r in rows}

    def next_color():
        for c in PALETTE:
            if c.lower() not in used:
                return c
        return PALETTE[len(used) % len(PALETTE)]

    for (p, slug, tris), name in zip(built, names):
        fname = f"{slug}.bin"
        if fname in by_file:
            by_file[fname].update(triangles=str(tris), source_stl=p.name)
            continue
        system = guess_system(name)
        if re.search(r"chondrocran|cranium|skull|cartilage", name, re.I):
            color = CARTILAGE
        else:
            color = next_color()
        used.add(color.lower())
        new_rows.append({
            "file": fname, "label": label_of(name), "system": system,
            "color": color, "opacity": "30" if system == "Body" else "100",
            "show": "yes", "triangles": str(tris), "source_stl": p.name})
    order = {s: i for i, s in enumerate(SYSTEM_ORDER)}
    new_rows.sort(key=lambda r: (order.get(r["system"], len(order)), r["label"]))
    rows += new_rows

    made = {f"{slug}.bin" for _, slug, _ in built}
    for r in rows:
        if r["file"] not in made and not (out / r["file"]).exists():
            print(f"  ? organs.csv lists {r['file']}, but there's no such "
                  f"file. The viewer will skip it.")

    with sheet.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLUMNS})

    print(f"\n{len(built)} models, {total_bytes / 1024 / 1024:.1f} MB in all.")
    if new_rows:
        print(f"Added {len(new_rows)} row(s) to {sheet}. Check the labels, "
              f"systems and colours there.")
    else:
        print(f"{sheet} kept as it was (triangle counts refreshed).")


if __name__ == "__main__":
    main()
