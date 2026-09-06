#!/usr/bin/env python3
"""
One-off pass over the photographs that are already in photography/.

For each full-size image it rebuilds the thumbnail at the new larger size from
the clean original, then burns the watermark into the full-size file in place.
Uses the copies already in photography/, so it does not need to re-read your
originals and takes seconds rather than minutes.

Safe to run twice: images that already carry the watermark are skipped, tracked
in photography/.watermarked so it can tell.

    python3 scripts/apply_watermarks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_photos import (OUT, QUALITY, THUMB_MAX, WATERMARK,  # noqa: E402
                            add_watermark)

from PIL import Image  # noqa: E402
# (prepare_photos, imported above, prints a helpful message if Pillow is absent)

STAMP = OUT / ".watermarked"


def main():
    done = set()
    if STAMP.exists():
        done = set(STAMP.read_text(encoding="utf-8").split("\n"))

    folders = [OUT / "tadpoles"] + sorted((OUT / "wildlife").glob("*")) \
        if (OUT / "wildlife").is_dir() else [OUT / "tadpoles"]

    changed = 0
    for folder in folders:
        if not folder.is_dir():
            continue
        for full in sorted(folder.glob("*.jpg")):
            key = str(full.relative_to(OUT))
            if key in done:
                continue
            with Image.open(full) as im:
                im = im.convert("RGB")
                # thumbnail first, from the clean image
                thumb = im.copy()
                thumb.thumbnail((THUMB_MAX, THUMB_MAX), Image.LANCZOS)
                (folder / "thumbs").mkdir(exist_ok=True)
                thumb.save(folder / "thumbs" / full.name, "JPEG",
                           quality=80, optimize=True)
                stamped = add_watermark(im)
            stamped.save(full, "JPEG", quality=QUALITY, optimize=True,
                         progressive=True)
            done.add(key)
            changed += 1
        print(f"  {folder.relative_to(OUT)}: done")

    STAMP.write_text("\n".join(sorted(x for x in done if x)), encoding="utf-8")
    print(f"\n{changed} image(s) watermarked with: {WATERMARK!r}")


if __name__ == "__main__":
    main()
