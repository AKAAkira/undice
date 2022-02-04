# undice
Reverses the the operation that reduced image set variants into unique blocks.

# Usage

usage: undice.py [-h] [-o OUTPUT_DIRECTORY] [--verbose] [--use-unitypack]
                 [fpath [fpath ...]]

Unscrambles diced textures found in assetbundle or MVL/JSON + image files.

positional arguments:
  fpath                 File paths to be passed along to script that needs
                        undicing (can be drag-and-dropped). Each fpath should
                        be a path to MVL, JSON, or assetbundle file; if MVL or
                        JSON, the relevant image files must be in same folder.
                        If MVL: the relevant image file is assumed to have the
                        same name except for extention and trailing underscore
                        (_) (e.g. "son_ba_.mvl" looks for "son_ba.png" or
                        "son_ba.jpg" in the same folder). If JSON: the image
                        file must be named the same as it is in the JSON file.
                        If assetbundle: need to use --use-unitypack switch.

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT_DIRECTORY, --output-directory OUTPUT_DIRECTORY
                        output directory to write extracted samples into
                        (default "out/")
  --verbose             be more verbose during extraction
  --use-unitypack       Use unitypack module for direct assetbundles
                        manipulation (https://github.com/HearthSim/UnityPack)
                        (false by default as it has problems extracting
                        certain images correctly)

usage: undice_afterprocess.py [-h] [-o OUTPUT_DIRECTORY] [--verbose]
                              [-t PROCESS_TYPE] [-w]
                              fpath

Some processing of images that may be needed after undicing for more natural
viewing.

positional arguments:
  fpath                 Path to folders that contain images needing processing
                        (can be drag-and-dropped)

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT_DIRECTORY, --output-directory OUTPUT_DIRECTORY
                        output directory to write results into (default
                        "processed/")
  --verbose             be more verbose during extraction
  -t PROCESS_TYPE, --process-type PROCESS_TYPE
                        1: Alpha composite + trim (e.g. for MO -Innocent
                        Fille) Layers base images together with their
                        respective part images to make variant image set.
                        Files must be PNG and be named in a pattern buildling
                        off from previous base images. E.g. AA.png will be
                        treated as base for AAA.png and AAB.png, while
                        AAAA.png and AAAB.png will treat the former as base
                        but not the latter. a: Applies edge fuzz transparency
                        (better trim, but may over-erase subtle art details
                        starting from the edges) b: Solid colour trim (rids
                        edges with any uniform colour, not just transparent
                        pixels; not for BG art, especially solid colour) Any
                        combination of valid number/letters works.
  -w, --overwrite       If output file already exists, don't skip and
                        overwrite it.

# Examples

With files found in `chara.mpk` from Memories Off -Innocent Fille-
`undice.py son_ba_.mvl -o out/` -> Image parts set placed in `out/son_ba/`
`undice_afterprocess.py out/son_ba/ -o processed/son_ba/ -t 1ab` -> Image varients set placed in `processed/son_ba/`
