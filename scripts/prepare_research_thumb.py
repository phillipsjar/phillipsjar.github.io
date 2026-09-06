#!/usr/bin/env python3
"""
Resize an image for use as a Research-post thumbnail.

Usage:
    python3 scripts/prepare_research_thumb.py path/to/source.jpg [output-name]

Drops a resized copy into assets/images/research-thumbs/, capped at 640px on
the long edge, so a thumbnail can never accidentally ship as a full-size
photo. Point a post's `image:` front matter at the result, e.g.:

    image: ../assets/images/research-thumbs/my-new-thumb.jpg

Run it again with the same output name to replace an existing thumbnail.
"""
import os
import sys

from PIL import Image, ImageOps

MAX_DIM = 640
QUALITY = 85
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "images", "research-thumbs")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    src = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(os.path.basename(src))[0]
    name = os.path.splitext(name)[0] + ".jpg"

    os.makedirs(OUT_DIR, exist_ok=True)

    img = Image.open(src)
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail((MAX_DIM, MAX_DIM), Image.LANCZOS)

    out_path = os.path.join(OUT_DIR, name)
    img.save(out_path, "JPEG", quality=QUALITY, optimize=True)
    print(f"Wrote {out_path} ({img.width}x{img.height}px, {os.path.getsize(out_path)//1024} KB)")


if __name__ == "__main__":
    main()
