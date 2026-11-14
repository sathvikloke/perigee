# Data guide

## Owners

Only Sathvik and Sagar need the original dataset. Akshobya, Aditya and Suhrit do not need a full copy to develop their parts. Agree the JSON/API contract during the first hour, then connect to the shared backend as it becomes available.

## Retained local sources

The five-target collection is in research/build_data/ on Sathvik's laptop:

- raw/: 183 original multi-extension FITS cutouts.
- metadata/: original archive search and resolver responses.
- manifest.json: download ledger, source URLs, hashes and audit metadata.
- reference/: official SPHEREx explanatory supplement and its source record.

The older outburst/NEOWISE research files remain in research/data/. These large directories are excluded from Git. The raw data have not been uploaded to this repository.

The prior processing scripts, generated previews, frontend manifest, case files and starter ZIP have been removed. Create the processing pipeline, frontend fixtures and case content from scratch during the event.

## Audit scope

The five target queries returned 1,986 DR1/QR3 wide-survey metadata records. Of 188 selected cutout requests, 183 succeeded; five returned HTTP 503 after retries. This is a bounded sample, not an archive mirror.

| Target | Original cutouts |
|---|---:|
| Barnard's Star | 34 |
| Epsilon Indi B | 44 |
| WISE 0855 | 34 |
| RW Aurigae | 35 |
| R Draconis | 36 |

## Scientific requirements for the new implementation

- Keep observation date separate from wavelength; detector number alone does not define the wavelength.
- Align on a fixed celestial grid so motion is not erased by recentering the object.
- Show missing coverage, archive failure and adverse pixel flags distinctly.
- Label catalog-predicted positions separately from measured detections.
- Preserve original URLs, collection IDs, observation IDs and observation times.
- Do not infer reliable flux changes, proper motion or composition from display previews alone.
- Test the official WISE 0855 coordinate independently: RA 08h55m10.831s, Dec −07°14′42.53″.

## Sources and acknowledgments

Use [IRSA SPHEREx access documentation](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/), the [DR1 overview](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html), and the [quality/spectrophotometry guide](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html). Copy the appropriate official acknowledgment and release citation into the final submission; retain CDS/SIMBAD attribution for resolver information.

NASA/IRSA and third-party source material keep their respective terms and attribution requirements.
