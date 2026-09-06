# Where everything lives

A map from "the thing I want to change" to "the file I open". Nothing on this
site requires touching HTML or CSS to change words.

## Text you'll change often

| What you see on the site | File to edit |
|---|---|
| Your name in the navbar and page titles | `_variables.yml` |
| The one-line tagline under your name | `_variables.yml` |
| Your email address, anywhere it appears | `_variables.yml` |
| Google Scholar link, anywhere it appears | `_variables.yml` |
| The two bio paragraphs on the homepage | `index.qmd` |
| The four research summaries on the homepage | `index.qmd`, in the `.preview` block |
| The full text of a research post | `research/<name>.qmd` |
| Intro paragraph on the Research index | `research.qmd` |
| Everything on the CV page | `cv.qmd` |
| Intro on the tadpole page | `tadpoles.qmd` |
| Intro on the wildlife page | `wildlife.qmd` |
| Contact page | `contact.qmd` |
| Footer text | `_quarto.yml`, under `page-footer` |
| Which pages appear in the navbar | `_quarto.yml`, under `navbar` |

Anything in `_variables.yml` is used with `{{< var email >}}`. Change the value
once and every page updates.

## Text generated for you, don't hand-edit

| File | What regenerates it |
|---|---|
| `photography/_tadpoles.qmd` and `_tadpoles-banner.qmd` | `/opt/homebrew/bin/python3 scripts/prepare_photos.py` |
| `photography/_wildlife.qmd` and `_wildlife-banner.qmd` | same |

`captions.csv` inside each photo folder is the exception. That one is yours to
edit; the script fills in blanks but never overwrites what you've written.

## Adding things

**A research post.** Copy `research/_template.qmd` to `research/your-title.qmd`
and fill it in. It appears on the Research index automatically.

**Photographs.** There are two photo pages and they work slightly differently.

*Tadpole specimen library* is searchable and grouped by family. Drop files
into `photos-source/Tadpoles/` and run the script; each new photograph gets a
blank row added to the reference sheet for you to fill in.

**The reference sheet** is `photography/tadpoles/reference.csv`, one row per
photograph, with columns: `file`, `specimen_id`, `common_name`,
`scientific_name`, `genus`, `family`, `order`, `class`, `location`, `source`.

`specimen_id` is the museum catalogue number. It fills itself in when the
filename contains one: `Cardioglossa_sp_MCZ_A139946_dorsal.png` becomes
"MCZ A139946", and `Phrynobatrachus_natalensis_A139879_side.png` becomes
"A139879". An institution code immediately before the number is picked up with
it. Type it in by hand for anything the filename doesn't carry. It shows in the
caption and is searchable, so a curator can find a photograph by its number. Open it in Excel or Numbers,
fill it in, save as CSV, re-run the script. Nothing you write is ever
overwritten. Rows for photographs you have deleted are dropped automatically.

Everything in that sheet is searchable from the box on the page, and `family`
is what the grouping below the search uses. A photograph with no family lands
in "Not yet identified" rather than disappearing.

**Filling the taxonomy automatically.** Put a name in `scientific_name` (a
genus, or genus and species) and run:

    Rscript scripts/build_reference.R

That uses `taxize` to look up genus, family, order, class and a common name for
every row that names something but has no family yet. Install it once with
`install.packages("taxize")`. Rows that already have a family are skipped, so
your corrections are permanent.

Be warned that the general databases lag behind Amphibian Species of the World
on frog family limits. Two rows already in your sheet are exactly that case:
*Agalychnis* (Phyllomedusidae in ASW, often still Hylidae in GBIF) and
*Conraua* (Conrauidae in ASW, sometimes Petropedetidae elsewhere). When you
disagree with the lookup, type the answer you trust and put your own name in
the `source` column.

**The cover image** at the top of the page is set by `TADPOLE_COVER` near the
top of `scripts/prepare_photos.py`. Whichever file you name there is used as
the cover, taken out of the grid so it isn't shown twice, and copied from your
original so it carries no watermark. `.still-cover` in `_rules.scss` controls
its height, and `object-fit: contain` there shows the whole picture; change it
to `cover` to fill the band and crop.

*Wildlife photography* is divided into sections. Each section is a folder:

    photos-source/Wildlife/Reptiles/
    photos-source/Wildlife/Amphibians/
    photos-source/Wildlife/Birds/
    photos-source/Wildlife/Mammals/
    photos-source/Wildlife/Other/

Drop a photo into the folder for its group and re-run the script.

**To move a photo between sections, just drag it in Finder** from one
`photos-source/Wildlife/<Section>/` folder to another, then re-run
`/opt/homebrew/bin/python3 scripts/prepare_photos.py`. The script notices the source photo is
gone from the old section, deletes the web copy there, generates it in the new
one, and carries your caption across with it. Same for moving a photo between
Tadpoles and Wildlife.

Deleting a photo from the site works the same way: remove it from
`photos-source/` and re-run.

The one safety rule: the script only ever deletes a web copy when it can see
the matching source folder. On a machine with no `photos-source/` at all it
prunes nothing, so a fresh clone can never wipe your gallery.

To add a section, make the folder and add its name to `SECTIONS` at the top of
`scripts/prepare_photos.py`. That list also sets the order they appear in.
Empty sections are skipped, which is why Birds isn't showing yet.

**A video.** Open `videos.qmd`, copy one of the commented blocks, and uncomment
the Video line in `_quarto.yml`.

**A video inside a research post.** Put the file in `assets/video/` and write:

```
::: {.video-figure}
{{< video ../assets/video/your-clip.mp4 >}}

**Bold lead-in** Then the caption.
:::
```

Clips wrapped this way start playing and looping when the reader scrolls them
into view, and pause when they scroll away. They are always silent, the player
controls still work, and readers whose system asks for reduced motion get
click-to-play instead. The whole behaviour is `assets/video-autoplay.html`;
delete its line from `include-in-header` in `_quarto.yml` to switch it off.

Keep clips small. H.264 mp4 is the format every browser plays, and the ones on
the site were made from the camera originals with:

```
ffmpeg -i original.mov -an -c:v libx264 -crf 26 -preset slow \
       -pix_fmt yuv420p -movflags +faststart web-copy.mp4
```

That turned 143 MB of raw footage into about 5 MB with no visible loss. Camera
originals do not belong in the repo; keep them on the drive.

To put two clips side by side, wrap both figures in a `.video-pair` div. See
`research/do-tadpoles-have-lungs.qmd` for a worked example, including how to
make two differently-shaped clips finish at the same height.

**A news item.** Uncomment the News block near the bottom of `index.qmd`.

## Changing how it looks

`theme-dark.scss` and `theme-light.scss` each start with seven colour variables
and two fonts. That is the entire palette. Change `$accent` in both and every
link, button and highlight on the site follows.

Dark is the default. The navbar has a toggle so visitors can switch. To drop the
toggle and commit to one look, replace the `theme:` block in `_quarto.yml` with:

    theme: [cosmo, theme-dark.scss]

Layout rules (spacing, grid columns, the photo grid, the banner) are in
`_rules.scss`, shared by both themes. Each section has a comment saying what it
controls.

## Moving things around

Four levers, in the order you'll reach for them.

**1. Vertical order on a page = order in the file.** Cut a paragraph and paste
it higher up and it moves higher up. This covers most rearranging. Blocks that
begin with `:::` end with a matching `:::`; move the whole block including both
fences.

**2. Which page something is on = which file it's in.** The order of the tabs in
the navbar is the order they're listed under `navbar:` in `_quarto.yml`.

**3. Side by side = a grid.** Quarto has a twelve-column grid built in:

    ::: {.grid}
    ::: {.g-col-8}
    The wide left-hand column goes here.
    :::
    ::: {.g-col-4}
    The narrow right-hand column goes here.
    :::
    :::

The numbers after `g-col-` add up to 12. Eight and four gives you two thirds and
one third; six and six gives equal halves. On a phone they stack automatically.

### The homepage banner

The photo is `assets/home-banner.jpg`. Replace that file with another one (any
wide crop, roughly 2.5:1 or wider works best) and the banner changes.

The text over it is the `.home-banner-text` block in `index.qmd`. It is now
plain text, so type straight over it:

    ::: {.home-banner-text}
    # Jackson Phillips

    How frogs breathe, feed, and change shape, and what that says about evolution.
    :::

The line beginning with `#` is the big heading. The line under it is the
smaller one. Leave the `:::` lines alone. Delete the smaller line entirely if
you want just the name.

In `_rules.scss`, under `.home-banner`:

| To change | Line |
|---|---|
| Banner height | `height: clamp(240px, 32vw, 440px)` |
| Which part of the photo shows | `object-position` on `.home-banner img` |
| Text nearer the bottom instead of centred | `top: 50%` on `.home-banner-text`, try `78%` |
| Text on the right instead of the left | swap `left:` for `right:`, and flip the gradient's `100deg` to `260deg` |
| Darkness of the wash behind the text | the `0.72` in `.home-banner::after` |

**4. Everything else is in `_rules.scss`**, and each section is commented. The
ones you're most likely to want:

| To change | Edit |
|---|---|
| Height of the strip at the top of every page | `.site-banner`, the `height: clamp(...)` line |
| Which slice of a photo the strip shows | `.site-banner img`, the `object-position` line |
| How many photos rotate in the strip | `SITE_BANNER_COUNT` in `scripts/prepare_photos.py`, then re-run it |
| Balance of text vs portrait on the homepage | `.hero`, the `grid-template-columns` line |
| Which side the portrait sits on | swap the two `:::` blocks inside `.hero` in `index.qmd` |
| Size of the photo thumbnails in an album | `.photo-grid`, the `minmax(260px, 1fr)` numbers |
| Space above and below a section | the `margin` line in that section's rule |

## The photo viewer

Clicking a photograph opens it full screen. The viewer is `assets/lightbox.html`,
about eighty lines of plain JavaScript and no library, pulled into every page by
`include-after-body` in `_quarto.yml`.

Ways out, all of which work: the **Close** button top right, the **Esc** key, or
a click anywhere on the dark background. Left and right arrow keys move through
the section you opened from, and on a phone you swipe. The counter top left
tells you where you are.

Styling is `.lb`, `.lb-close`, `.lb-prev` and friends in `_rules.scss`.

## Watermarking

Every full-size image carries `© Jackson R Phillips 2026` across the middle at
low opacity. Thumbnails are left clean, and so are the page banners, which draw
on the thumbnails.

In `scripts/prepare_photos.py`:

| To change | Line |
|---|---|
| The words | `WATERMARK` |
| How visible it is | `WATERMARK_OPACITY`, 0 to 255. It is 64. |
| Turn it off | set `WATERMARK = ""` |
| Which font | `FONT_CANDIDATES`, first one found wins |

New photos are watermarked on import. To re-do the existing ones after changing
the wording or opacity, delete `photography/.watermarked` and run
`python3 scripts/apply_watermarks.py`, which works from the copies already in
`photography/` rather than re-reading your originals.

One honest limit: a watermark discourages casual reuse, it does not prevent it.
Your originals in `photos-source/` are untouched and unmarked.

## Captions on the wildlife pages

Each section folder has a `captions.csv` with four columns: `file`,
`common_name`, `species`, `location`. The scientific name is italicised on the
page; the common name and location sit under it in smaller grey type. Fill in
either, or both, or neither.

Birds and Mammals are listed in `COMMON_NAME_SECTIONS` at the top of
`scripts/prepare_photos.py`, which means new files there are read as common
names rather than as binomials, so `Palm_tanager_1_...` doesn't come out
italicised as though it were a species. Move a section in or out of that list
to change how its filenames are read.

## The drop folder

`Website/jack_photo_adds/` is the inbox. Put photographs into a subfolder named
for where they belong (`tadpoles`, `amphibians`, `birds`, `mammals`,
`reptiles`, `other`), then:

    /opt/homebrew/bin/python3 scripts/file_inbox.py
    /opt/homebrew/bin/python3 scripts/prepare_photos.py

**Nothing is ever overwritten.** If a photograph with that name is already in
the destination, the new one becomes `Name_2.png`, then `_3`, and so on. So a
second shot of a species you already have never replaces the first.

`--dry-run` shows what it would do without moving anything.

Loose files sitting at the top of the drop folder are left alone and listed,
because the section can't be worked out from the file by itself.

## Rotating a photograph

Rotate the original, then re-run the script. Nothing else.

1. In Finder, find the file in `photos-source/`.
2. Right-click it, and use **Quick Actions → Rotate Left** or **Rotate Right**.
   Repeat for 180 degrees. Or open it in Preview and use Cmd-L / Cmd-R, then
   Cmd-S.
3. `/opt/homebrew/bin/python3 scripts/prepare_photos.py`

The script rebuilds any web copy whose original has a newer timestamp, so only
the photograph you rotated is redone and the other eighty are untouched. This
also covers any other edit: recrop, relevel, redo the colour, and re-running
picks it up.

If a whole batch comes in sideways from the camera instead, select them all in
Finder and rotate in one go; the rule is the same.

## Captions, hover, and being found on Google

Captions now sit over the bottom of each photo and fade in when you hover.
On phones and tablets, where there is no hover, they sit underneath instead.
They are hidden with `opacity`, not `display: none`, so the text is still in the
page for screen readers and for search engines either way.

What makes the photographs findable in Google Images, in rough order of how
much each one matters:

1. **Filenames.** `Schismaderma_carens_LP_2023_1.jpg` is worth a great deal, and
   you already name files this way. Keep doing it. The script preserves your
   spelling and capitalisation exactly.
2. **Alt text**, built from `captions.csv` as "Species, location". Every blank
   row in a `captions.csv` is one photo Google cannot identify, which is the
   single most useful hour you could spend on this site.
3. **Visible captions** under or over the image, which the script also writes.
4. **Page descriptions.** Each album page lists its species in the meta
   description automatically.
5. **Structured data.** Each album page carries a schema.org `ImageGallery`
   block naming you as the photographer and describing every image.
6. **Two image sizes offered per photo**, so Google can index the 1800px
   version rather than the thumbnail.
7. **robots.txt and sitemap.xml**, both generated, pointing crawlers at
   everything.

Nothing here works until the site is actually live and Google has crawled it,
which usually takes a few weeks. You can speed up the first crawl by adding the
site to Google Search Console and submitting the sitemap.

## Working in RStudio

`phillips-website.Rproj` opens the site as its own RStudio project, with
workspace saving and restoring turned off so it never picks up `.RData` from
another project. RStudio reads `_quarto.yml` and adds a Build tab with Render
and Preview buttons.

Don't run RStudio's Preview and `quarto preview` in Terminal at the same time;
they both want the same port. Pick one.

## Before you push

    python3 scripts/check.py

Lists every unfinished placeholder, any broken internal link, and the repo size.
