#!/usr/bin/env python3
"""
Video structured-data pipeline.

Scans every .qmd file for {.video-figure} blocks containing a
{{< video ... >}} shortcode, and for each unique video file:

1. THUMBNAIL. Grabs a real frame from the file (ffmpeg) into
   assets/video/thumbs/<name>.jpg, if one doesn't already exist.

2. SCHEMA. Builds a VideoObject record (name + description taken verbatim
   from the caption under the video -- preferring the copy on videos.qmd,
   since that page carries one caption per video -- plus contentUrl,
   thumbnailUrl, creator, copyrightNotice, creditText, license and
   acquireLicensePage), and writes one JSON-LD <script> block per PAGE
   (covering just the videos that appear on that page) between
   `<!-- VIDEO-SCHEMA:START -->` / `<!-- VIDEO-SCHEMA:END -->` markers
   placed right after that page's front matter. Re-running this script
   replaces only the text between those markers, so it's always safe to
   run again after adding or editing a video.

Deliberately NOT included: uploadDate. There's no real capture/publish
date on file for these clips, and this script only fills in fields it can
get from something you actually wrote or a real frame of the file itself.

    python3 scripts/build_video_schema.py
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CREATOR = "Jackson Phillips"
THUMB_DIR = ROOT / "assets" / "video" / "thumbs"
START = "<!-- VIDEO-SCHEMA:START -->"
END = "<!-- VIDEO-SCHEMA:END -->"

SKIP_DIRS = {"_site", ".quarto", ".git", "photos-source", "_shots"}


def site_url():
    m = re.search(r'^\s*site-url:\s*"?([^"\n#]+)"?',
                  (ROOT / "_quarto.yml").read_text(encoding="utf-8"), re.M)
    return m.group(1).strip().rstrip("/") if m else ""


def qmd_files():
    for p in sorted(ROOT.rglob("*.qmd")):
        if not any(d in p.parts for d in SKIP_DIRS) and not p.name.startswith("_"):
            yield p


def strip_md(text):
    """Plain text for a JSON field: drop [text](url) links and every literal
    '*' (bold/italic markers, including nested combinations like
    **text *species* text**), then collapse whitespace."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("*", "")
    return re.sub(r"\s+", " ", text).strip()


BLOCK_RE = re.compile(
    r"::: *\{\.video-figure[^}]*\}\s*\n"
    r"\{\{<\s*video\s+([^\s>]+)\s*>\}\}\s*\n+"
    r"(.*?)\n:::",
    re.S,
)


def parse_blocks(path):
    """Yield (video_relpath_from_site_root, caption_name, description) for
    every video-figure block in a file."""
    text = path.read_text(encoding="utf-8")
    for m in BLOCK_RE.finditer(text):
        src, body = m.group(1), m.group(2).strip()
        # video src is relative to the qmd file; normalize to site-root-relative
        video_path = (path.parent / src).resolve().relative_to(ROOT)
        lines = [l for l in body.splitlines() if l.strip()]
        if not lines:
            continue
        name = strip_md(lines[0])
        desc = strip_md(" ".join(lines[1:])) if len(lines) > 1 else ""
        yield str(video_path).replace("\\", "/"), name, desc


def make_thumbnail(video_path):
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    out = THUMB_DIR / (Path(video_path).stem + ".jpg")
    if out.exists():
        return out
    src = ROOT / video_path
    subprocess.run(
        ["ffmpeg", "-y", "-ss", "1", "-i", str(src), "-vframes", "1",
         "-q:v", "4", str(out)],
        check=True, capture_output=True,
    )
    return out


def main():
    base = site_url()

    # Pass 1: collect every caption seen for every video, keyed by page,
    # preferring videos.qmd's wording as canonical when a video appears
    # on more than one page.
    per_page = {}   # page path -> [(video_path, name, desc), ...]
    canonical = {}  # video_path -> (name, desc)

    for qmd in qmd_files():
        blocks = list(parse_blocks(qmd))
        if not blocks:
            continue
        per_page[qmd] = blocks
        for video_path, name, desc in blocks:
            is_canonical_page = qmd.name == "videos.qmd"
            if video_path not in canonical or is_canonical_page:
                canonical[video_path] = (name, desc)

    if not canonical:
        print("No {.video-figure} blocks found.")
        return

    # Pass 2: thumbnails, once per unique video.
    for video_path in canonical:
        make_thumbnail(video_path)
        print(f"  thumbnail ok: {video_path}")

    # Pass 3: write one schema block per page.
    for qmd, blocks in per_page.items():
        seen = []
        for video_path, _, _ in blocks:
            if video_path not in seen:
                seen.append(video_path)

        videos = []
        for video_path in seen:
            name, desc = canonical[video_path]
            thumb_path = f"assets/video/thumbs/{Path(video_path).stem}.jpg"
            videos.append({
                "@context": "https://schema.org",
                "@type": "VideoObject",
                "name": name,
                "description": desc or name,
                "contentUrl": f"{base}/{video_path}" if base else video_path,
                "thumbnailUrl": f"{base}/{thumb_path}" if base else thumb_path,
                "creator": {"@type": "Person", "name": CREATOR},
                "copyrightNotice": f"© {CREATOR}",
                "creditText": CREATOR,
                "license": f"{base}/license.html" if base else "license.html",
                "acquireLicensePage": f"{base}/license.html" if base else "license.html",
            })

        block_text = (
            f"{START}\n```{{=html}}\n"
            + "\n".join(
                '<script type="application/ld+json">\n' + json.dumps(v, indent=1) + "\n</script>"
                for v in videos
            )
            + f"\n```\n{END}"
        )

        text = qmd.read_text(encoding="utf-8")
        if START in text and END in text:
            text = re.sub(
                re.escape(START) + r".*?" + re.escape(END),
                lambda _: block_text,
                text, flags=re.S,
            )
        else:
            # insert right after the front matter (second '---' line)
            parts = text.split("---", 2)
            if len(parts) == 3:
                text = "---" + parts[1] + "---\n\n" + block_text + "\n" + parts[2].lstrip("\n")
            else:
                text = block_text + "\n\n" + text
        qmd.write_text(text, encoding="utf-8")
        print(f"  schema written: {qmd.relative_to(ROOT)} ({len(videos)} video(s))")

    print(f"\n{len(canonical)} unique videos, {len(per_page)} page(s) updated.")


if __name__ == "__main__":
    main()
