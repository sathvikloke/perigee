# Perigee resources and tool credits

These resources support the submitted application, technical report and demonstration deck. The investigation images are processed NASA SPHEREx observations. Generated artwork is decorative and labelled in the application.

## Scientific data and references

| Resource | Use | Public link |
| --- | --- | --- |
| SPHEREx DR1 spectral images | FITS observations and cutouts | https://www.ipac.caltech.edu/doi/10.26131/IRSA678 |
| SPHEREx QR3 spectral images | FITS observations and cutouts | https://www.ipac.caltech.edu/doi/10.26131/IRSA662 |
| NASA/IPAC IRSA | Image search, cutout access and release documentation | https://irsa.ipac.caltech.edu/Missions/spherex.html |
| SPHEREx data-access guide | Archive API and file conventions | https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/ |
| IRSA SPHEREx tutorial | FITS interpretation reference | https://caltech-ipac.github.io/irsa-tutorials/spherex-intro |
| JPL SPHEREx spacecraft overview | Mission and hardware reference during design | https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/spacecraft/ |
| CDS SIMBAD and Sesame | Catalog target information and object-name resolution | https://simbad.cfa.harvard.edu/simbad/ ; https://cds.unistra.fr/cgi-bin/Sesame |
| ESA Gaia DR3 | Independent field-star registration controls | https://www.cosmos.esa.int/web/gaia/dr3 |

The app uses the spectral-image datasets, not the DR1 all-sky cube. Frame records and case definitions retain the exact source URLs and hashes.

## Software

| Resource | Use | Public link |
| --- | --- | --- |
| React and React DOM | Browser interface | https://react.dev/ |
| TypeScript | Frontend types | https://www.typescriptlang.org/ |
| Vite and its React plugin | Frontend build | https://vite.dev/ |
| Node.js | Build tooling | https://nodejs.org/ |
| Python | API and scientific processing | https://www.python.org/ |
| FastAPI and Starlette | HTTP API | https://fastapi.tiangolo.com/ ; https://www.starlette.io/ |
| Uvicorn | Local ASGI service | https://www.uvicorn.org/ |
| Pydantic and pydantic-core | Data validation | https://docs.pydantic.dev/latest/ |
| HTTPX and AnyIO | HTTP requests and asynchronous execution | https://www.python-httpx.org/ ; https://anyio.readthedocs.io/ |
| certifi | Certificate trust bundle | https://github.com/certifi/python-certifi |
| Astropy and its WCS support | FITS files, coordinates, time and WCS | https://www.astropy.org/ |
| NumPy | Array processing and numerical checks | https://numpy.org/ |
| Pillow | Scientific image outputs and deterministic figure crops | https://python-pillow.org/ |
| Vitest | Frontend verification | https://vitest.dev/ |
| pytest | Backend and science verification | https://docs.pytest.org/en/stable/ |
| Sharp | Artwork file conversion | https://sharp.pixelplumbing.com/ |
| Cloudflare Workers and Wrangler | Public frontend hosting and deployment | https://developers.cloudflare.com/workers/ |
| Vercel | Python service hosting | https://vercel.com/docs |
| GitHub and GitHub Actions | Source sharing and CI | https://github.com/ |

Exact dependency versions are recorded in [backend/requirements.txt](../backend/requirements.txt), [frontend/package.json](../frontend/package.json) and [frontend/package-lock.json](../frontend/package-lock.json). Libraries pulled in by these dependencies retain their upstream license terms.

## Report, deck and design assistance

| Resource | Use | Public link |
| --- | --- | --- |
| Tectonic | LaTeX technical-report compilation | https://tectonic-typesetting.github.io/ |
| LaTeX, TikZ/PGF and PGFPlots | Report typography, schematic and validation plot | https://www.latex-project.org/ ; https://ctan.org/pkg/pgf ; https://ctan.org/pkg/pgfplots |
| TeX Gyre Pagella / New PX | Report body and mathematical type | https://ctan.org/pkg/newpx |
| ReportLab | Seven-slide PDF packaging and links | https://docs.reportlab.com/ |
| pypdf and Poppler | PDF checks and rendered-page review | https://pypdf.readthedocs.io/ ; https://poppler.freedesktop.org/ |
| Claude Code | Implementation, tests and scientific review assistance | https://code.claude.com/docs/en/overview |
| OpenAI Codex | Implementation, design, review scripts, writing and document authoring assistance | https://openai.com/codex/ |
| OpenAI image generation | Decorative cartoon telescope and rocket/exhaust | https://openai.com/index/introducing-4o-image-generation/ |
| Impeccable | Design instructions | https://github.com/pbakaus/impeccable |
| Avoid AI Writing | Editorial instructions | https://github.com/conorbronsdon/avoid-ai-writing |
| Stop Slop | Editorial instructions | https://github.com/hardikpandya/stop-slop |

Bloody Coconuts is the team's custom design-instruction skill. It informed UI design; its private source is not a scientific dataset or a required dependency for running the app. Codex's document-authoring tools supported the editable deck and PDF review. The report figures use observed data, an application screenshot and labelled diagrams.

The project [AI-use notes](AI_USE.md) describe where assistance was used. The running application does not call an AI model to interpret scientific observations. No recorded or edited submission video is claimed by this resource list.
