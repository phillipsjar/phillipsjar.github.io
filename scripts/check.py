#!/usr/bin/env python3
"""
Preflight check. Run before pushing:

    python3 scripts/check.py

Reports what is still unfinished and what would break on the live site. It
changes nothing.
"""

import re
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"_site", ".quarto", ".git", "photos-source", "_shots"}
MARKERS = ("TODO", "FILL IN", "PLACEHOLDER", "Placeholder")

problems = 0


def say(kind, msg):
    global problems
    if kind == "!":
        problems += 1
    print(f"  {kind} {msg}")


def qmd_files():
    for p in sorted(ROOT.rglob("*.qmd")):
        if not any(d in p.parts for d in SKIP_DIRS):
            yield p


print("\nPlaceholders still in the text")
found = False
for p in qmd_files():
    for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if any(m in line for m in MARKERS):
            say("!", f"{p.relative_to(ROOT)}:{n}  {line.strip()[:70]}")
            found = True
if not found:
    print("  none")

print("\nInternal links")
found = False
for p in qmd_files():
    text = p.read_text(encoding="utf-8")
    for target in re.findall(r"\]\((?!https?:|mailto:|#|\{\{)([^)#]+)", text):
        dest = (p.parent / target.strip()).resolve()
        if not dest.exists():
            say("!", f"{p.relative_to(ROOT)} points at missing {target.strip()}")
            found = True
if not found:
    print("  all resolve")

print("\nAssets")
for f, why in [("assets/portrait.jpg", "homepage portrait"),
               ("assets/jackson-phillips-cv.pdf", "CV download link"),
               ("assets/favicon.png", "browser tab icon")]:
    say("." if (ROOT / f).exists() else "!", f"{f}  ({why})")

print("\nPhotographs")


def described(folder, sheet, columns):
    """(number of photos, number with nothing written about them)."""
    photos = [f for f in sorted(folder.glob("*.jpg"))
              if f.name != "Cover_collage_AW.jpg"]  # the cover, not a library entry
    said = {}
    path = folder / sheet
    if path.exists():
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                said[row.get("file", "")] = any(
                    (row.get(c) or "").strip() for c in columns)
    return len(photos), sum(1 for f in photos if not said.get(f.name))


tads = ROOT / "photography" / "tadpoles"
if tads.is_dir():
    n, blank = described(tads, "reference.csv", ("scientific_name", "common_name"))
    say("." if not blank else "?",
        f"tadpoles: {n} photos, {blank} with no name in reference.csv")

wild = ROOT / "photography" / "wildlife"
if wild.is_dir():
    for section in sorted(d for d in wild.iterdir() if d.is_dir()):
        n, blank = described(section, "captions.csv", ("common_name", "species"))
        say("." if not blank else "?",
            f"wildlife/{section.name}: {n} photos, {blank} without a caption")

print("\n3D anatomy figures (assets/models/*/organs.csv)")
sheets = sorted((ROOT / "assets" / "models").glob("*/organs.csv"))
if not sheets:
    print("  none")
for sheet in sheets:
    where = sheet.relative_to(ROOT)
    with sheet.open(newline="", encoding="utf-8-sig") as fh:
        rows = [{(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
                for r in csv.DictReader(fh)]
    rows = [r for r in rows if r.get("file")]
    bad = 0
    for n, r in enumerate(rows, 2):
        name = r.get("label") or r["file"]
        if not (sheet.parent / r["file"]).exists():
            say("!", f"{where} row {n}: no model file {r['file']}")
            bad += 1
        if r.get("color") and not re.fullmatch(r"#?[0-9a-fA-F]{6}", r["color"]):
            say("!", f"{where} row {n} ({name}): colour {r['color']!r} isn't a "
                     f"6-digit hex like #ddd3bd")
            bad += 1
        op = r.get("opacity", "")
        if op and not (re.fullmatch(r"\d+(\.\d+)?", op) and float(op) <= 100):
            say("!", f"{where} row {n} ({name}): opacity {op!r} should be 0 to 100")
            bad += 1
    if not bad:
        say(".", f"{where}: {len(rows)} parts, all fine")

print("\nSize")
out = subprocess.run(["du", "-sh", "--exclude=_site", "--exclude=.quarto",
                      "--exclude=_shots", "--exclude=photos-source", str(ROOT)],
                     capture_output=True, text=True)
size = out.stdout.split()[0] if out.stdout else "?"
say(".", f"repo is {size} (GitHub is comfortable below about 1 GB)")

big = [p for p in ROOT.rglob("*") if p.is_file()
       and not any(d in p.parts for d in SKIP_DIRS)
       and p.stat().st_size > 50 * 1024 * 1024]
for p in big:
    say("!", f"{p.relative_to(ROOT)} is over 50 MB; GitHub refuses files over 100 MB")

print(f"\n{problems} thing(s) to fix.\n" if problems else "\nAll clear.\n")
sys.exit(0)
