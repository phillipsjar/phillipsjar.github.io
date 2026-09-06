#!/usr/bin/env python3
"""
One-off migration from the old two-album layout to the new one:

    photography/albums/tadpoles/   ->  photography/tadpoles/
    photography/albums/wildlife/   ->  photography/wildlife/<section>/
    photos-source/Wildlife/*.jpg   ->  photos-source/Wildlife/<Section>/

Existing captions are carried across into the right section's captions.csv.
Nothing is deleted; files are moved. Safe to run twice.
"""

import csv
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OLD = ROOT / "photography" / "albums"
NEW = ROOT / "photography"
SRC = ROOT / "photos-source"

# Which taxon each wildlife photograph belongs to, by filename stem.
# Anything not listed here lands in Other.
TAXA = {
    "Reptiles": [
        "Acontias_meleagris", "Agkistrodon_contortrix_PA_2023_2",
        "Alligator_mississippiensis_1", "Aplopeltura_boa_Sayap_Borneo_2",
        "Apolone_ferox_1", "Bitis_arietans_topdown", "Bitis_peringueyi_3",
        "Bradypodion_transvaalensis_woodbush_green",
        "Crotalus_lepidus_klauberi_SWRS_2", "Crotalus_pyrrhus_AZ_2026-10",
        "Stigmochelys_pardalis_adults_2",
        "Tropidolaemus_subannulatus_sarawak_female",
    ],
    "Amphibians": [
        "Ambystoma_maculatum_NY_2025_4", "Anaxyrus_americanus_CT_2020",
        "Ensatina_eschscholtzii_oregonensis_CA_2024_2",
        "Gyrinophilus_porphyriticus_Ithaca_2025",
        "Hadromophryne_natalensis_LIMP_2023", "Hemisus_marmoratus_LIMP_2023",
        "Leptopelis_natalensis_KZN_2022_2",
        "Pelophryne_minuta_Borneohighlands_2024_1", "Rana_klauberi_lilypad",
        "Staurois_latopalmatus_Sayap_Borneo_2024", "Tlalcohyla_picta_Belize_2025",
    ],
    "Birds": [],
    "Mammals": [
        "Giraffe_Namibia_2019_2", "Hyena_Kruger_2023_3", "Leo_Kruger_2023_6",
        "Orangutan_Sabah_2024", "Rhinos_siyafunda_2023_2",
    ],
}
SECTION_OF = {stem: sect for sect, stems in TAXA.items() for stem in stems}


def move(src, dst):
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return False
    shutil.move(str(src), str(dst))
    return True


def main():
    moved = 0

    # --- tadpoles: straight rename -----------------------------------------
    if (OLD / "tadpoles").is_dir():
        for p in sorted((OLD / "tadpoles").glob("*.jpg")):
            moved += move(p, NEW / "tadpoles" / p.name)
        for p in sorted((OLD / "tadpoles" / "thumbs").glob("*.jpg")):
            moved += move(p, NEW / "tadpoles" / "thumbs" / p.name)
        move(OLD / "tadpoles" / "captions.csv", NEW / "tadpoles" / "captions.csv")

    # --- wildlife: split into sections --------------------------------------
    old_caps = {}
    cap_file = OLD / "wildlife" / "captions.csv"
    if cap_file.exists():
        with cap_file.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                old_caps[r["file"]] = (r.get("species", ""), r.get("location", ""))

    per_section = {}
    if (OLD / "wildlife").is_dir():
        for p in sorted((OLD / "wildlife").glob("*.jpg")):
            sect = SECTION_OF.get(p.stem, "Other")
            slug = sect.lower()
            per_section.setdefault(slug, []).append(p.name)
            moved += move(p, NEW / "wildlife" / slug / p.name)
            moved += move(OLD / "wildlife" / "thumbs" / p.name,
                          NEW / "wildlife" / slug / "thumbs" / p.name)

    for slug, names in per_section.items():
        out = NEW / "wildlife" / slug / "captions.csv"
        if out.exists():
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["file", "species", "location"])
            for n in sorted(names):
                sp, loc = old_caps.get(n, ("", ""))
                w.writerow([n, sp, loc])
        print(f"  captions: wildlife/{slug} ({len(names)})")

    # --- source photos into taxon folders -----------------------------------
    wsrc = SRC / "Wildlife"
    if wsrc.is_dir():
        for p in sorted(wsrc.iterdir()):
            if not p.is_file() or p.name.startswith("."):
                continue
            sect = SECTION_OF.get(p.stem, "Other")
            moved += move(p, wsrc / sect / p.name)
        for sect in TAXA:
            (wsrc / sect).mkdir(parents=True, exist_ok=True)

    # --- tidy up the empty old folders --------------------------------------
    for leftover in [OLD / "tadpoles" / "thumbs", OLD / "tadpoles",
                     OLD / "wildlife" / "thumbs", OLD / "wildlife"]:
        try:
            if leftover.is_dir() and not any(leftover.iterdir()):
                leftover.rmdir()
        except OSError:
            pass

    print(f"\nmoved {moved} files")
    for slug in sorted(per_section):
        print(f"  wildlife/{slug}: {len(per_section[slug])}")


if __name__ == "__main__":
    main()
