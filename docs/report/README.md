# Perigee technical report

The canonical source is `perigee-report.tex`. This supporting technical report uses a research-paper layout: TeX Gyre Pagella text, numbered sections, an abstract, equations, six figures, two tables and linked references. It is supporting project documentation, not a claim of peer-reviewed publication.

## Build

Install [Tectonic](https://tectonic-typesetting.github.io/en-US/install.html), the LaTeX compiler, and the report's small Python dependency set. The tested compiler is Tectonic 0.17.0. Tectonic downloads required TeX packages on its first build and caches them for subsequent builds.

```sh
python -m pip install -r docs/report/requirements-report.txt
python docs/report/build_report.py
```

An explicit compiler path or review destination can be supplied:

```sh
python docs/report/build_report.py --compiler /path/to/tectonic \
  --output /tmp/perigee-technical-report.pdf
```

The default destination is `frontend/public/demo/perigee-technical-report.pdf`. Compiler files and extracted text stay in the ignored `build/` directory. The build fails on unresolved citations/references, missing glyphs, overfull boxes, missing author names or implausible page counts. It verifies the retained scientific denominators before generating the registration figure. It does not download astronomical data or rerun experiments.

## Figures

1. Current application screenshot from `docs/presentation/standalone-assets/barnard-app.png`.
2. Vector processing schematic authored in LaTeX/TikZ.
3. Original Barnard case PNGs, full field, unchanged.
4. Original Epsilon case PNGs, full field, unchanged; dates and wavelengths come from the case JSON.
5. Matched WISE-field crops from the published case PNGs, with a second row using the existing problem-flag overlay. Both dates use crop bounds `(86,52,150,116)` on the 256-pixel grid. Enlargement uses nearest-neighbor sampling; it does not invent detail. Each crop spans 90 arcseconds.
6. Vector registration counts generated from `validator_real_frames.csv`; counts refer to 183 unique cutouts, not 189 product records.

`generated/figure-data.json` records source hashes and crop bounds. The manuscript identifies what each comparison supports and preserves the distinction between catalog predictions, visual proxies and independent field-star checks.

## Editorial and visual review

The prose was revised using the installed `avoid-ai-writing` skill and the original [stop-slop skill](https://github.com/hardikpandya/stop-slop). The review focuses on precise explanations, source fidelity and readable sentences, not an authorship-detector score. Scientific qualifications remain where they affect interpretation. `text-review.json` records the editorial passes and checks.

`verification.json` records the final PDF hash, compiler and layout checks. Page renders in `rendered/` support visual inspection. Rebuild, inspect all pages, then verify the public PDF after deployment; a local build alone does not establish publication.
