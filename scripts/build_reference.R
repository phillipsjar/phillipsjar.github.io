#!/usr/bin/env Rscript
# ---------------------------------------------------------------------------
# Fills in the taxonomy columns of photography/tadpoles/reference.csv.
#
# You supply `scientific_name` (a genus, or a genus and species). This looks up
# genus, family, order, class and a common name and writes them back. Rows that
# already have a family are left completely alone, so anything you have
# corrected by hand is safe.
#
# Two ways to run it, both from the site folder:
#   In the RStudio console:   source("scripts/build_reference.R")
#   In a terminal:            Rscript scripts/build_reference.R
#
# First time only:
#   install.packages("taxize")
#
# A NOTE ON WHICH ANSWER IS RIGHT
# Amphibian family limits move around, and the general-purpose databases lag
# behind Amphibian Species of the World. Two in your current sheet are exactly
# this case: Agalychnis (Phyllomedusidae in ASW, often still Hylidae in GBIF)
# and Conraua (Conrauidae in ASW, sometimes Petropedetidae elsewhere). This
# script never overwrites a row you have already filled, so the way to handle
# disagreements is to type the answer you trust and set `source` to your own
# name. Yours wins from then on.
# ---------------------------------------------------------------------------

suppressPackageStartupMessages(library(taxize))

ref_path <- file.path("photography", "tadpoles", "reference.csv")
if (!file.exists(ref_path)) stop("Run this from the site folder; ", ref_path, " not found.")

ref <- read.csv(ref_path, stringsAsFactors = FALSE, colClasses = "character")

# Which rows need work: they name something, but have no family yet.
todo <- which(nzchar(trimws(ref$scientific_name)) & !nzchar(trimws(ref$family)))

if (!length(todo)) {
  cat("Nothing to look up. Every named row already has a family.\n")
}

# One lookup per distinct name rather than per photo, since several photographs
# are often the same species.
names_needed <- if (length(todo)) unique(trimws(ref$scientific_name[todo])) else character(0)
found <- list()

if (length(names_needed))
  cat("Looking up", length(names_needed),
      "name(s). This hits the internet, so give it a moment.\n\n")

for (nm in names_needed) {
  cat(" ", nm, "... ")
  cls <- tryCatch(
    classification(nm, db = "gbif", rows = 1, messages = FALSE)[[1]],
    error = function(e) NULL
  )
  if (is.null(cls) || !is.data.frame(cls)) {
    cat("no match\n")
    next
  }
  pick <- function(rank) {
    hit <- cls$name[cls$rank == rank]
    if (length(hit)) hit[1] else ""
  }
  common <- tryCatch({
    cc <- sci2comm(nm, db = "ncbi", simplify = TRUE)[[1]]
    if (length(cc) && nzchar(cc[1])) tools::toTitleCase(cc[1]) else ""
  }, error = function(e) "")

  found[[nm]] <- list(
    genus  = pick("genus"),
    family = pick("family"),
    order  = pick("order"),
    class  = pick("class"),
    common = common
  )
  cat(found[[nm]]$family, "/", found[[nm]]$order, "\n")
}

filled <- 0
for (i in todo) {
  hit <- found[[trimws(ref$scientific_name[i])]]
  if (is.null(hit)) next
  if (!nzchar(ref$genus[i]))       ref$genus[i]  <- hit$genus
  if (!nzchar(ref$family[i]))      ref$family[i] <- hit$family
  if (!nzchar(ref$order[i]))       ref$order[i]  <- hit$order
  if (!nzchar(ref$class[i]))       ref$class[i]  <- hit$class
  if (!nzchar(ref$common_name[i])) ref$common_name[i] <- hit$common
  ref$source[i] <- "gbif"
  filled <- filled + 1
}

write.csv(ref, ref_path, row.names = FALSE, na = "")

cat("\nFilled", filled, "row(s).",
    "Check them, correct anything wrong, and put your own name in `source`.\n")
cat("Then rebuild the page:\n  /opt/homebrew/bin/python3 scripts/prepare_photos.py\n")
