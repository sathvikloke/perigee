# Concrete handoff recipes

These recipes describe how the six workstreams connect. They are examples of reviewable work, not a second feature backlog and not a claim that these artifacts already exist. Use the recipes relevant to your role. Keep one authoritative implementation of each interface. An owner can simplify an internal design as long as the observable contract and scientific meaning remain intact.

## Recipe 1: make the first cross-team example small

Start with one curated frame, one case, and one observable user action. Sagar supplies a freshly generated image and its metadata. Sathvik identifies the question that image can support. Suhrit serves the catalog and asset through the intended routes. Aditya ensures the shared model can represent the record without silently dropping fields. Akshobya renders the image, date, wavelength, quality state and source link, then lets the learner select it as evidence. Neeraj may inspect the resulting public flow after it exists.

The handoff should include the exact observation identifier, case identifier, asset identifier, and processing version. It should also include the expected quality state and any intentionally unavailable fields. If the supplied record has no verified bandwidth, retain null. If the image uses per-frame stretching, the record and interface should say so. One small record that survives every boundary accurately is more useful than a large directory of unexplained images.

Place the development example where its owner can maintain it. Do not copy six slightly different versions into unrelated packages. If a frontend fixture is temporarily needed, derive it from the agreed model and identify it as a development fixture. Once the real endpoint works, test that endpoint and remove any production fallback that could silently hide its failure.

## Recipe 2: agree a record through an example, not a label

An issue saying the frame model is finished is insufficient for integration. Provide a compact example with actual field names, units and representative values. Include a successful record, a record with unknown wavelength, and an error envelope only if those examples resolve a real consumer question. Use clearly fictional identifiers in synthetic examples. Never attach a real observation identifier to invented scientific values merely to make a fixture look realistic.

The receiving owner should read the example and describe the resulting behavior. For example, an unknown wavelength should produce an unavailable label and should not pass a numeric wavelength filter accidentally. A quality record with unknown counts should not render an all-clear badge. A partial metadata search should preserve useful observations and show that the searched scope was incomplete. This brief consumer review catches meaning errors that a JSON schema alone may miss.

Once the shape is agreed, put the type or model in its owned directory and link it from the issue. Record a schema version in serialized evidence. Versioning is useful only if it reflects a real compatibility boundary; do not create a migration framework before there is a second version. Additive optional fields should have documented fallback behavior. A changed unit or renamed stable identifier requires coordinated changes to saved content and consumers.

## Recipe 3: trace one displayed pixel region back to a source

For one representative output, record the original archive URL, collection, observation ID, retrieval timestamp and file hash. Identify the FITS extensions used for intensity, wavelength, flags and uncertainty where available. Describe which coordinate was sampled for wavelength and which aperture was examined for the displayed quality summary. Preserve enough information that Sathvik can reproduce the check without guessing which downloaded file produced the image.

The processing note should distinguish source pixel coordinates from output display coordinates. A target can land between pixels, outside a valid region, or near an edge. Interpolation may alter the output appearance, and a resampled flag image needs a method appropriate for categorical information. Do not smooth a bit mask as though it were an intensity field and then interpret fractional values as official flags. Record the actual chosen method and its limitations.

This trace does not need to be a polished notebook or an automated report generator. A short reproducible command, a small metadata record and an inspected image can be enough. Its purpose is to catch a coordinate, extension, unit or transformation mistake before the same mistake is replicated across every preset. Expand verification when a new data format or processing branch introduces a distinct risk.

## Recipe 4: test the public coordinate path independently

Choose a valid coordinate that is not one of the five preset centers and has a reasonable prospect of covered observations. Document why it was selected. Submit it through the same form and API a visitor will use. Inspect the normalized query returned by the backend, then confirm that the archive request used that coordinate. A successful response from a nearby hardcoded preset is a failure of this requirement even if the displayed sky looks plausible.

Record whether the result is complete, truncated, partial or empty. If the source returns many matches and the application limits them, preserve that scope in the user-facing result. Do not invent a total match count when the archive response does not supply one. If one collection fails, distinguish that failure from a complete search of all supported collections. If every upstream call fails, show an error rather than an empty universe.

Then process a small number of returned frames through the deployed API. Confirm chronological ordering by observation time rather than completion order. Check that changing the query while a slow frame is pending prevents the old result from appearing in the new view. This single integration exercise covers a consequential public requirement; it should not become an uncontrolled download of all available observations.

## Recipe 5: preserve a learner's work across failure

A learner may write a claim before all requested frames finish. Treat that text as their work. A failed frame, token expiry, route navigation or temporary archive outage should not erase it. Keep evidence selections tied to stable observation identifiers, and make the relationship visible when some selected data cannot currently be reloaded. A retry should recover the missing network result without silently resetting the entire investigation.

Local persistence should have a bounded, versioned shape. Save text, query parameters and observation references; avoid retaining an unlimited collection of image data URLs. If browser storage is unavailable or full, keep the current in-memory text and offer a practical export or copy action. Do not report that an investigation was saved unless the storage write actually succeeded. A failed save should be understandable without developer tools.

For an export check, create a short claim containing punctuation and line breaks, select two observations, and include an uncertainty statement. Export the card, inspect the downloaded JSON, and verify that the text, IDs, dates, wavelengths and source links survived. Check the print view separately because CSS can hide useful context. The exported artifact should remain understandable after the browser tab is closed.

## Recipe 6: rehearse the scientific explanation

Ask a teammate to explain the difference between observation date and wavelength while looking at the actual viewer. Then ask what a flagged aperture means and what it does not mean. If they infer that every changing pixel is a changing star, the interface or case copy needs improvement. If they think a catalog marker is a measured detection, fix the label and nearby explanation before adding another visualization.

For the fair-comparison case, the desired outcome is a reasoned statement about whether initial checks support comparing the selected frames. It is not a guaranteed brightness-change claim. For Barnard's Star, externally established motion provides context, while the displayed frames and their flags determine what this particular comparison can show. If the expected visual effect is not clear in the regenerated products, rewrite the activity around the evidence that is actually visible.

Keep the explanation short enough to use during a live demonstration. The learner should encounter the important constraint at the decision point, not only in a source document. Additional technical detail can be expandable. A concise limitation attached to a specific observation is more useful than a generic warning repeated everywhere. The objective is informed interpretation, not making every screen feel like a legal notice.

## Recipe 7: make a deployment check reproducible

Record the Vercel project, deployment URL, commit and environment. First check the frontend document and a direct deep link. Then request the health endpoint and inspect both content type and body. An HTTP success containing the frontend HTML at an API route is a routing defect. Check a catalog route and a small asset route before attempting the more expensive live processing path.

The next check should cross the scientific boundary: submit a bounded search and process one resulting frame. This establishes whether the deployed Python package contains the required libraries, can reach the upstream service, can use temporary files correctly and can return a suitably small result. Measure actual elapsed time and response size. Do not infer deployed behavior from a successful local import or a dashboard reporting that a build completed.

Open the judge-facing URL in a session without team credentials. Confirm that deployment protection is configured appropriately for that intended audience. Do not disable protections on unrelated projects. If two-project hosting is used, record the frontend API origin and test cross-origin requests from the actual production frontend. A development server proxy can conceal a production CORS problem, so it is not a substitute for this check.

## Recipe 8: report a failure so the right owner can act

A useful report includes the user action, expected result, actual result, relevant query or case ID, deployment or commit, and a short reproduction. Add a screenshot for a visual defect and a sanitized response for an API defect. Avoid dumping full logs or raw files when a few lines show the problem. Remove tokens and personal notes before sharing diagnostic material.

Route the report by the failed boundary. A correctly returned unknown wavelength displayed as zero belongs to the frontend. An archive failure converted to empty belongs to API orchestration. A misregistered image with correct query metadata belongs to processing. A JSON route intercepted by the SPA belongs to deployment routing. Incorrect case interpretation belongs to science content. Ownership may change after diagnosis; start with evidence rather than blame.

State whether the defect blocks the core demonstration, affects a required secondary path, or is optional polish. The first category gets immediate coordination. The second gets a clear owner and checkpoint. The third can be deferred when the deadline is close. A report is resolved when the original reproduction succeeds against the intended build, not merely when a code change has been pushed.

## Recipe 9: prepare one trustworthy release handoff

Before rehearsal, identify the exact build that the team will present. Freeze optional additions while checking the required journey. Keep a concise list of known limitations and a fallback using the verified curated observations. The fallback must remain labeled as curated or cached; it must not masquerade as a successful live query when the archive is unavailable. Show both the working capability and the actual current state honestly.

The presentation should use screenshots and a demonstration from that build. A feature visible only on a developer branch should not appear as a released capability. If a later change fixes a blocking issue, repeat the affected checks and update the deployment reference. Preserve the last known working deployment until the replacement has been verified. Avoid a broad last-minute dependency upgrade without a concrete need.

The final handoff is brief: what works, where it is available, what was tested, what remains, and who owns the next action. Include source acknowledgments and the correct submission links. Sagar and Sathvik should coordinate the actual submission, with a second person checking links and content. A complete application can still be difficult to judge if the submitted URL requires login or the project description describes an older build.
