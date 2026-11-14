# Interactive design reference

Read [HANDOFF.md](HANDOFF.md) for the selected design and integration requirements. The reference lives in `prototype/`; the main functional app remains owned by the Claude implementation workers.

From the repo root:

```sh
python3 -m http.server 4175 --directory design/prototype
```

Then open http://localhost:4175 . No dependencies or raw FITS downloads are needed to view it. A + B and A + C, manual frame selection on phones, blink/pause, quality details, local saved notes, JSON export and print styling are implemented.

The three small image assets are real data, freshly rendered during this sprint. Their source URLs, source-file hashes, registration grid, processing and catalog marker provenance are in `prototype/assets/provenance.json`. `build_assets.py` needs the science checkout and research Python environment only to regenerate the reference PNGs. Sathvik and Sagar remain the raw-data owners.

The `.impeccable/mocks/` images are generated composition explorations. Do not use their starfields, metadata or invented controls in the functional app. The selected reference is A, with corrections recorded in HANDOFF.md.

This folder does not replace the live API, general coordinate search, five presets or second investigation. Claude should port the implemented composition and behavior into the frontend and preserve the integration contract.
