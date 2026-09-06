# Jackson Phillips — personal site

A [Quarto](https://quarto.org) website. Five sections: home, research writing,
photography, CV, contact. Dark by default with a light toggle in the navbar.

**Read `EDITING.md` first.** It maps every piece of text on the site to the file
that produces it.

## One-time setup

You need [Quarto](https://quarto.org/docs/get-started/) and Python 3 with
Pillow (`pip install pillow`).

1. Create a repo on GitHub named exactly **`phillipsjar.github.io`**. Leave it
   empty, no README, no license.
2. In the repo: **Settings → Pages → Build and deployment → Source → GitHub
   Actions**. This is the step people forget; without it nothing publishes.
3. From this folder:

   ```bash
   git init
   git add -A
   git commit -m "initial site"
   git branch -M main
   git remote add origin https://github.com/phillipsjar/phillipsjar.github.io.git
   git push -u origin main
   ```

4. Watch the Actions tab. First build takes two or three minutes. The site then
   lives at **https://phillipsjar.github.io**.

After that, every `git push` rebuilds and republishes. There is no deploy
command to run.

### When you buy a domain

1. At your registrar, point the domain at GitHub Pages (four A records for the
   apex, or a CNAME to `phillipsjar.github.io` for `www`). GitHub's Pages
   settings screen lists the current IP addresses.
2. Repo **Settings → Pages → Custom domain**, enter it, tick **Enforce HTTPS**.
3. Change `site-url` in `_quarto.yml` to the new address and push.

Nothing else changes. Old links keep working.

## Day to day

```bash
quarto preview              # live-reloading local preview
python3 scripts/check.py    # what's still unfinished, before you push
```

### Which python3

The photo script needs Pillow, which is installed in Homebrew's Python. Your
normal Terminal finds it; RStudio's Terminal tab has a different PATH and
doesn't. Use the full path and it works from either:

```bash
/opt/homebrew/bin/python3 scripts/prepare_photos.py
```

## Adding a research post

Copy `research/_template.qmd`, rename it, fill it in. It appears on the Research
index by itself. `order:` in the front matter sets its position.

## Adding photographs

1. Make a folder in `photos-source/` named whatever the album should be called.
2. Copy full-resolution files in. Any size, any format.
3. `/opt/homebrew/bin/python3 scripts/prepare_photos.py`

It resizes to 1800px, builds thumbnails, flattens transparent PNGs onto black,
strips GPS coordinates and camera serial numbers, writes the album page, and
refreshes the banner.

`photos-source/` is gitignored. Your originals never enter the repo; only the
web-sized copies do. Re-running skips work already done, and `--force` redoes
everything.

Captions come from `captions.csv` inside each album folder. The script guesses
from filenames and fills blanks, but never overwrites what you have written.

## Adding video

See the commented block in `videos.qmd`. Files under about 20 MB can live in
`assets/video/`. Anything bigger belongs on YouTube or Vimeo as unlisted, with
the URL pasted in. GitHub rejects single files over 100 MB.

## Changing how it looks

Seven colour variables at the top of `theme-dark.scss` and `theme-light.scss`.
Layout in `_rules.scss`, shared by both. Site title, navigation and footer in
`_quarto.yml`.
