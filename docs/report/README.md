# Perigee technical report

The report is supporting documentation for the project page and seven-slide deck. It contains eight US Letter pages, with methods, case evidence, validation scope, limitations, reproduction commands and references. It is not a peer-reviewed publication.

## Build

From the repository root, install the report-only dependencies in a Python environment:

```sh
python -m pip install -r docs/report/requirements-report.txt
python docs/report/build_report.py
```

The default output is `frontend/public/demo/perigee-technical-report.pdf`. To write a review copy elsewhere:

```sh
python docs/report/build_report.py --output /tmp/perigee-report-review.pdf
```

`TECHNICAL_REPORT.md` is the editable prose source. The page boundaries are intentional. The build fails if the result is not exactly eight pages. It uses the two original processed Barnard case PNGs in the repository, keeps them unchanged and draws the other figures as vector diagrams. It does not download data or rerun the scientific experiments.

## Review performed

- Built with ReportLab 4.4.9, Pillow 13.0.0 and pypdf 6.21.4.
- Rendered all eight pages with Poppler and inspected both four-page contact sheets. No clipped paragraphs, overlapping tables or missing images were found.
- Extracted text from every page and checked the eight page labels.
- Confirmed that all six team names appear and that the 183 unique-cutout / 189 historical-record distinction is preserved.
- The text-hygiene scan found zero suspicious invisible Unicode characters. The local stylometry gauge reported 0.0325, density tier low, and no phrase markers. This is a writing check, not an authorship verdict. The deterministic cleanup changed zero characters; no score-driven rewrite was performed.
- Reviewed the prose using the technical/documentation guidance in the installed writing skills. Counts, uncertainty, catalog dependence and reported experiment scope were retained.

Page renders are in `rendered/page-1.png` through `rendered/page-8.png`; `contact-1.png` and `contact-2.png` show all eight pages. They are review artifacts and do not need to be served by the app.

The release coordinator must verify the deployed PDF URL after publishing. Producing this local PDF does not establish that it is live.
