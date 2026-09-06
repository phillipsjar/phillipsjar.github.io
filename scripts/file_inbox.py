#!/usr/bin/env python3
"""
Move photographs out of the drop folder and into the site's source folders.

    /opt/homebrew/bin/python3 scripts/file_inbox.py

It reads the drop folder next to the site:

    Website/jack_photo_adds/tadpoles/     ->  photos-source/Tadpoles/
    Website/jack_photo_adds/amphibians/   ->  photos-source/Wildlife/Amphibians/
    Website/jack_photo_adds/birds/        ->  photos-source/Wildlife/Birds/
    Website/jack_photo_adds/mammals/      ->  photos-source/Wildlife/Mammals/
    Website/jack_photo_adds/reptiles/     ->  photos-source/Wildlife/Reptiles/
    Website/jack_photo_adds/*.jpg         ->  asks you where it goes

NOTHING IS EVER OVERWRITTEN. If a photograph with that name is already there,
this adds _2, then _3, and so on, so a second shot of the same species never
replaces the first. Add --dry-run to see what it would do without moving
anything.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT.parent / "jack_photo_adds"          # sits beside the site folder
SOURCE = ROOT / "photos-source"

DESTINATIONS = {
    "tadpoles":   SOURCE / "Tadpoles",
    "amphibians": SOURCE / "Wildlife" / "Amphibians",
    "birds":      SOURCE / "Wildlife" / "Birds",
    "mammals":    SOURCE / "Wildlife" / "Mammals",
    "reptiles":   SOURCE / "Wildlife" / "Reptiles",
    "other":      SOURCE / "Wildlife" / "Other",
}
EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".gif"}
DRY = "--dry-run" in sys.argv


def free_name(folder, name):
    """A name that isn't taken yet: photo.png, then photo_2.png, photo_3.png."""
    target = folder / name
    if not target.exists():
        return target, False
    stem, suffix = Path(name).stem, Path(name).suffix
    n = 2
    while (folder / f"{stem}_{n}{suffix}").exists():
        n += 1
    return folder / f"{stem}_{n}{suffix}", True


def main():
    if not INBOX.is_dir():
        print(f"No drop folder at {INBOX}")
        return

    moved = renamed = 0
    loose = []
    for item in sorted(INBOX.iterdir()):
        if item.is_file() and item.suffix.lower() in EXTS:
            loose.append(item.name)
            continue
        if not item.is_dir():
            continue
        dest = DESTINATIONS.get(item.name.lower())
        if dest is None:
            print(f"  ? {item.name}/ is not a section I know; left alone")
            continue
        dest.mkdir(parents=True, exist_ok=True)
        for photo in sorted(p for p in item.iterdir() if p.suffix.lower() in EXTS):
            target, clashed = free_name(dest, photo.name)
            arrow = "->" if not clashed else "-> (renamed)"
            print(f"  {item.name}/{photo.name} {arrow} {target.name}")
            if not DRY:
                shutil.move(str(photo), str(target))
            moved += 1
            renamed += clashed

    if loose:
        print("\nLoose in the drop folder, not filed because I can't tell the "
              "section from the file alone. Put them in a subfolder:")
        for name in loose:
            print(f"  {name}")

    print(f"\n{'would move' if DRY else 'moved'} {moved} photograph(s)"
          + (f", {renamed} renamed to avoid replacing something" if renamed else ""))
    if moved and not DRY:
        print("Now run:  /opt/homebrew/bin/python3 scripts/prepare_photos.py")


if __name__ == "__main__":
    main()
