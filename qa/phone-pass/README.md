# Phone pass on production — 2026-11-15 (Neeraj)

**URL:** https://perigee-liard.vercel.app (production, `ef29890`), logged out, with fresh browser storage.
**Device:** Claude desktop browser pane emulating a 390×844 phone (touch user-agent). This was **not a physical phone** and no screen reader was used.

## Results

| Check | Result |
|---|---|
| Public access | ✔ `/` 200 HTML; `/api/v1/health` 200 JSON with `status: ok`, `token_signing: env`. The repo is public and `docs/AI_USE.md` opens. Earlier blockers B1 and B2 are fixed. The live case sources now use the SIMBAD CfA mirror, so F2 is fixed too. |
| Epsilon Indi B, A+B → A+C | ✔ The switch works. The note "Same moment, a different infrared color … not evidence that time changed the object" is clear. No horizontal overflow at 390 px. Toggle labels are 44 px tall. ([02](02-epsindi-AC-390.jpg)) |
| Barnard's Star | ✔ Opens on A+C with the guide line and flag overlay on, as designed. Blink pair and Pause blink work. The timeline filter "Near 2.01 µm" plays 3 frames and Pause stops it. ([03](03-barnard-A-guide-390.jpg), [04](04-barnard-C-guide-390.jpg)) |
| Notebook → reload → export | ✔ Claim, observation and uncertainty (with apostrophes and `&`) came back after a reload. The 3 chosen frames (A, C and an extra timeline frame) were kept in date order, with dates, wavelengths, flags and IRSA URLs. The export now includes `title` and `case_limitations`, and My evidence shows a human title with **Reopen**, so the earlier F1 and F3 are fixed. |

**What I think the Barnard comparison shows:** with A (25 Aug 2025) and C (19 Aug 2026) on the same sky grid at nearly the same wavelength (2.006 and 2.028 µm), the field stars stay put while the star's glow and the catalog marker move north, from on the guide line to just above it. That matches the catalog motion of about 10″ per year. The core is saturated and flagged in every frame (0 usable pixels near the target), so it shows the shift but can't measure speed or brightness. The shift is real but subtle on a phone. Without the guide line I would probably have missed it.

## Issues

| # | Severity | Where / action | What happened | Owner |
|---|---|---|---|---|
| P1 | **High** | `https://perigee-liard.vercel.app/demo/perigee-demo.pdf` (linked from the README and the presentation notes as the public deck) | It returns the **app's HTML, not the PDF**. The PDF is on `main` (`0bcc55d`), but the Vercel deploy of the latest `main` failed: commit status says **"Deployment rate limited — retry in 24 hours."** Production is stuck on `ef29890`, so PRs merged after it (#40–#42, including the WISE 0855 label fix) aren't live. | Suhrit / Sathvik |
| P2 | Medium | Presentation script, step 3 ("19 and 18 usable pixels at the target") | Production shows **19 (A) and 20 (B)** in "What does flag screen passed mean?". A judge reading the screen will see a different number from the one spoken. | Sathvik |
| P3 | Low | Open `?preset=epsilon_indi_b`, change nothing, then go to My evidence | An empty card, "Epsilon Indi B · … · no claim yet", is saved even though I never wrote anything. A fresh visitor (or a judge) will see cards they didn't make. | Akshobya |
| P4 | Low | Barnard's Star pair toggle | **A+B** and **A+C** are both labelled "Different dates", so nothing tells you which pair to pick. Something like "7 months apart" and "1 year apart" would help. Step 1 says "Blink the three frames", but **Blink pair** only alternates two. | Akshobya / Sathvik (wording) |
| P5 | Low | Barnard → "What does flagged near target mean?" | It shows raw flag codes `BLOOM, OVERFLOW, SUR_ERROR, TRANSIENT` with no plain-language meaning. A short line such as "detector saturated by a very bright star" would help learners. | Akshobya / Sathvik |

## Demo script: sentences that are hard to say in plain words

1. *"SPHEREx's wavelength depends on where the object lands on the detector."* A judge won't follow this. Try: "Each part of SPHEREx's camera sees a slightly different color of infrared light, so the same star can be photographed in a different color on a different day."
2. *"Each frame here has its own contrast stretch, so brightness isn't comparable."* Try: "Each picture's brightness was adjusted separately so you can see it, so you can't compare brightness between them."
3. *"19 and 18 usable pixels at the target, none flagged."* The numbers are wrong (see P2) and too detailed. Try: "No bad pixels around the target in either picture."
4. Slide 6: *"189/189 processed records pass independent re-derivation from the original FITS files. Gaia DR3 field stars land a median 0.45 display px from their predicted positions."* That's two pieces of jargon in a row. Try: "We re-checked every processed image against NASA's original files, and the background stars line up to within half a pixel of where a separate star catalog says they should be."
5. Barnard: *"about seven display pixels, about ten arcseconds, under two SPHEREx pixels."* That's three units in one breath. Pick one: "about ten arcseconds, roughly the width of a coin seen from 500 meters" (check that comparison before using it), or just "about a year's worth of motion, matching what catalogs predict."
6. *"a pair of brown dwarfs"* needs three words of explanation: "brown dwarfs, objects too small to be stars but bigger than planets."

## Not tested

A physical phone, a screen reader, the native print dialog, a timed spoken rehearsal, and the live coordinate search on production (I checked it locally earlier, and the release smoke run covers it on production).
